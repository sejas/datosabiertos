"""Conector para portales CKAN (`/api/3/action`).

Cubre los cinco portales del corpus: Madrid, Barcelona, Málaga, Córdoba y Reus. Lo que
parece un estándar no lo es del todo, y las diferencias medidas están tratadas aquí:

- **Barcelona** no devuelve `metadata_created`, llama `code`/`display_name` a lo que los
  demás llaman `name`/`title` en `organization`, y su `organization` es el *departamento*
  (Habitatge, Territori…), no el ayuntamiento.
- **Madrid** añade `modified` e `issued` (DCAT) además de `metadata_modified`.
- **Córdoba** declara `notspecified` en el 43 % de sus datasets: acaba en
  `licencia.declarada = False`, nunca en CC-BY.
- **Málaga** declara `by-sa-40`, la licencia más restrictiva del corpus.

Estrategia de paginación: `package_search` con `rows`/`start`. Si `package_search` falla
de forma definitiva, se cae a `package_list` + `package_show`, que es más lento pero
sobrevive a portales con el índice de búsqueda roto.
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Iterator

from ..cortesia import ErrorCosecha
from ..modelo import (
    DatasetNormalizado,
    Distribucion,
    Publicador,
    Tema,
    entero_o_none,
    normalizar_fecha,
    normalizar_licencia,
)
from .base import ConectorCatalogo

FILAS_POR_PAGINA = 100
MAXIMO_PAGINAS = 500


class ConectorCKAN(ConectorCatalogo):
    """Cosecha un catálogo CKAN completo a través de su API de acción."""

    familia = "ckan"

    # -- lectura -----------------------------------------------------------------------
    def _url(self, accion: str, **parametros) -> str:
        consulta = urllib.parse.urlencode(parametros)
        base = self.portal.url_api.rstrip("/")
        return f"{base}/{accion}" + (f"?{consulta}" if consulta else "")

    def total_declarado(self) -> int | None:
        try:
            respuesta = self.cliente.obtener_json(
                self._url("package_search", rows=0), self.portal.id
            )
            return int(respuesta["result"]["count"])
        except (ErrorCosecha, KeyError, TypeError, ValueError):
            return None

    def listar_crudos(self) -> Iterator[dict]:
        filas = int(self.portal.parametros.get("filas_por_pagina", FILAS_POR_PAGINA))
        inicio = 0
        total = None
        vistos: set[str] = set()
        for pagina in range(MAXIMO_PAGINAS):
            url = self._url("package_search", rows=filas, start=inicio)
            try:
                respuesta = self.cliente.obtener_json(url, self.portal.id)
            except ErrorCosecha:
                if pagina == 0:
                    self.registro.aviso(
                        self.portal.id,
                        "package_search falló en la primera página; se prueba "
                        "package_list + package_show",
                    )
                    yield from self._listar_por_package_show(vistos)
                    return
                raise
            resultado = respuesta.get("result") or {}
            paquetes = resultado.get("results") or []
            if total is None:
                total = resultado.get("count")
                self.registro.info(self.portal.id, f"package_search declara {total} datasets")
            for paquete in paquetes:
                identificador = paquete.get("id") or paquete.get("name")
                if identificador in vistos:
                    continue
                vistos.add(identificador)
                yield paquete
            inicio += filas
            if not paquetes or (total is not None and inicio >= total):
                break
        else:
            self.registro.aviso(
                self.portal.id, f"tope de {MAXIMO_PAGINAS} páginas alcanzado; catálogo truncado"
            )

    def _listar_por_package_show(self, vistos: set[str]) -> Iterator[dict]:
        """Plan B: listado de nombres y una llamada por dataset. Lento pero robusto."""
        respuesta = self.cliente.obtener_json(self._url("package_list"), self.portal.id)
        nombres = respuesta.get("result") or []
        self.registro.info(self.portal.id, f"package_list devuelve {len(nombres)} nombres")
        for nombre in nombres:
            if nombre in vistos:
                continue
            vistos.add(nombre)
            try:
                detalle = self.cliente.obtener_json(
                    self._url("package_show", id=nombre), self.portal.id
                )
            except ErrorCosecha as exc:
                self.registro.error(
                    self.portal.id, "package_show", f"{nombre}: {exc}", url=exc.url
                )
                continue
            paquete = detalle.get("result")
            if paquete:
                yield paquete

    # -- traducción --------------------------------------------------------------------
    @staticmethod
    def _primer_valor(origen: dict, *claves: str) -> str:
        for clave in claves:
            valor = origen.get(clave)
            if isinstance(valor, str) and valor.strip():
                return valor.strip()
            if isinstance(valor, (int, float)):
                return str(valor)
        return ""

    def _publicador(self, crudo: dict) -> Publicador | None:
        organizacion = crudo.get("organization")
        if not isinstance(organizacion, dict):
            return None
        nombre = self._primer_valor(organizacion, "name", "code", "id")
        titulo = self._primer_valor(organizacion, "title", "display_name", "name", "code")
        if not (nombre or titulo):
            return None
        return Publicador(
            nombre=nombre or titulo,
            titulo=titulo or nombre,
            descripcion=self._primer_valor(organizacion, "description"),
            url=self._primer_valor(organizacion, "url", "image_display_url"),
        )

    @staticmethod
    def _temas(crudo: dict) -> list[Tema]:
        temas: list[Tema] = []
        for grupo in crudo.get("groups") or []:
            if not isinstance(grupo, dict):
                continue
            nombre = (grupo.get("name") or grupo.get("id") or "").strip()
            titulo = (grupo.get("display_name") or grupo.get("title") or nombre).strip()
            if nombre or titulo:
                temas.append(Tema(nombre=nombre or titulo, titulo=titulo or nombre))
        return temas

    @staticmethod
    def _palabras_clave(crudo: dict) -> list[str]:
        palabras: list[str] = []
        etiquetas = crudo.get("tags") or []
        if isinstance(etiquetas, str):  # Barcelona expone además `tag` como cadena
            etiquetas = [e for e in etiquetas.split(",") if e.strip()]
        for etiqueta in etiquetas:
            if isinstance(etiqueta, dict):
                texto = (etiqueta.get("display_name") or etiqueta.get("name") or "").strip()
            else:
                texto = str(etiqueta).strip()
            if texto and texto not in palabras:
                palabras.append(texto)
        return palabras

    def _distribuciones(self, crudo: dict) -> list[Distribucion]:
        distribuciones = []
        for posicion, recurso in enumerate(crudo.get("resources") or []):
            if not isinstance(recurso, dict):
                continue
            url = self._primer_valor(recurso, "url")
            distribuciones.append(
                Distribucion(
                    identificador_origen=self._primer_valor(recurso, "id") or f"{posicion}",
                    nombre=self._primer_valor(recurso, "name"),
                    descripcion=self._primer_valor(recurso, "description"),
                    formato=self._primer_valor(recurso, "format").upper(),
                    mimetype=self._primer_valor(recurso, "mimetype", "mimetype_inner"),
                    url_acceso=url,
                    url_descarga=url,
                    tamano_bytes=entero_o_none(recurso.get("size")),
                    fecha_creacion_origen=normalizar_fecha(recurso.get("created")),
                    fecha_modificacion_origen=normalizar_fecha(
                        recurso.get("last_modified") or recurso.get("created")
                    ),
                    estado=self._primer_valor(recurso, "state"),
                    posicion=int(recurso.get("position") or posicion),
                )
            )
        return distribuciones

    def normalizar(self, crudo: dict) -> DatasetNormalizado | None:
        if not isinstance(crudo, dict):
            return None
        if crudo.get("state") not in (None, "", "active"):
            return None  # borradores y borrados no entran en el índice
        nombre = self._primer_valor(crudo, "name", "id")
        identificador = self._primer_valor(crudo, "id", "name")
        if not identificador:
            return None

        # Fecha de modificación en el origen: se prefiere la declarada por el publicador
        # (`modified`, DCAT `dct:modified`) sobre la del sistema de metadatos de CKAN.
        modificacion_declarada = normalizar_fecha(
            crudo.get("modified") or crudo.get("fecha_publicacion")
        )
        modificacion_metadatos = normalizar_fecha(crudo.get("metadata_modified"))
        fecha_modificacion = modificacion_declarada or modificacion_metadatos
        if not fecha_modificacion:
            fechas_recursos = [
                normalizar_fecha(r.get("last_modified") or r.get("created"))
                for r in (crudo.get("resources") or [])
                if isinstance(r, dict)
            ]
            fechas_recursos = [f for f in fechas_recursos if f]
            fecha_modificacion = max(fechas_recursos) if fechas_recursos else ""

        base = self.portal.url_base.rstrip("/")
        return DatasetNormalizado(
            portal_id=self.portal.id,
            identificador_origen=identificador,
            nombre=nombre,
            titulo=self._primer_valor(crudo, "title", "title_translated", "name") or nombre,
            descripcion=self._primer_valor(crudo, "notes", "description", "description_item"),
            url_origen=f"{base}/dataset/{nombre}",
            url_recurso_api=f"{self.portal.url_api.rstrip('/')}/package_show?id={nombre}",
            fecha_creacion_origen=normalizar_fecha(
                crudo.get("issued") or crudo.get("metadata_created")
            ),
            fecha_modificacion_origen=fecha_modificacion,
            fecha_modificacion_metadatos=modificacion_metadatos,
            publicador=self._publicador(crudo),
            licencia=normalizar_licencia(
                crudo.get("license_id"), crudo.get("license_title"), crudo.get("license_url")
            ),
            temas=self._temas(crudo),
            palabras_clave=self._palabras_clave(crudo),
            distribuciones=self._distribuciones(crudo),
            frecuencia_actualizacion=self._primer_valor(crudo, "frequency", "accrualPeriodicity"),
            idioma=self._primer_valor(crudo, "language"),
            crudo=crudo,
        )
