"""Persistencia del índice local sobre SQLite.

El almacén solo conoce `DatasetNormalizado`: no sabe qué es CKAN ni ArcGIS. Esa frontera
es la que permite añadir Gijón o Zaragoza (fase 2.1) sin tocar este fichero.

Reconstrucción idempotente: `reemplazar_portal()` borra lo que hubiera de ese portal antes
de insertar, de modo que `python -m datosabiertos.index build` deja siempre el mismo resultado se
ejecute una vez o diez.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from .configuracion import Portal
from .esquema import DDL, VERSION_ESQUEMA, construir_consulta_fts
from .modelo import DatasetNormalizado, normalizar_texto
from .registro import ErrorPortal, ResumenPortal, ahora_utc


class Almacen:
    """Índice local de metadatos. Usar como gestor de contexto."""

    def __init__(self, ruta: Path, solo_lectura: bool = False) -> None:
        """Abre el índice. Con `solo_lectura`, ni crea el esquema ni escribe nada.

        El modo de solo lectura no es un lujo: `__init__` ejecuta el DDL y anota la versión
        del esquema, o sea que **escribe**. Un servidor HTTP con varios hilos abriendo el
        mismo fichero se bloquea entre sí (`database is locked`), y además un endpoint
        público no debe poder tocar el índice ni por accidente.
        """
        self.ruta = Path(ruta)
        self.solo_lectura = solo_lectura
        if solo_lectura:
            if not self.ruta.exists():
                raise FileNotFoundError(f"no existe el índice: {self.ruta}")
            self.conexion = sqlite3.connect(f"file:{self.ruta}?mode=ro", uri=True)
            self.conexion.row_factory = sqlite3.Row
            return
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.conexion = sqlite3.connect(self.ruta)
        self.conexion.row_factory = sqlite3.Row
        self.conexion.execute("PRAGMA foreign_keys = ON")
        self.conexion.executescript(DDL)
        self._anotar("version_esquema", str(VERSION_ESQUEMA))

    def __enter__(self) -> "Almacen":
        return self

    def __exit__(self, *_) -> None:
        self.cerrar()

    def cerrar(self) -> None:
        if not self.solo_lectura:
            self.conexion.commit()
        self.conexion.close()

    def _anotar(self, clave: str, valor: str) -> None:
        self.conexion.execute(
            "INSERT INTO metadatos_indice (clave, valor) VALUES (?, ?) "
            "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
            (clave, valor),
        )

    # -- catálogos auxiliares --------------------------------------------------------------
    def _id_licencia(self, licencia) -> int:
        fila = self.conexion.execute(
            "SELECT id FROM licencia WHERE identificador = ?", (licencia.identificador,)
        ).fetchone()
        if fila:
            return fila["id"]
        cursor = self.conexion.execute(
            "INSERT INTO licencia (identificador, titulo, url, declarada) VALUES (?, ?, ?, ?)",
            (licencia.identificador, licencia.titulo, licencia.url, int(licencia.declarada)),
        )
        return int(cursor.lastrowid)

    def _id_publicador(self, portal_id: str, publicador) -> int | None:
        if publicador is None:
            return None
        fila = self.conexion.execute(
            "SELECT id FROM publicador WHERE portal_id = ? AND nombre = ?",
            (portal_id, publicador.nombre),
        ).fetchone()
        if fila:
            return fila["id"]
        cursor = self.conexion.execute(
            "INSERT INTO publicador (portal_id, nombre, titulo, descripcion, url) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                portal_id,
                publicador.nombre,
                publicador.titulo,
                publicador.descripcion,
                publicador.url,
            ),
        )
        return int(cursor.lastrowid)

    def _id_tema(self, portal_id: str, tema) -> int:
        fila = self.conexion.execute(
            "SELECT id FROM tema WHERE portal_id = ? AND nombre = ?", (portal_id, tema.nombre)
        ).fetchone()
        if fila:
            return fila["id"]
        cursor = self.conexion.execute(
            "INSERT INTO tema (portal_id, nombre, titulo, normalizado) VALUES (?, ?, ?, ?)",
            (portal_id, tema.nombre, tema.titulo, normalizar_texto(tema.titulo or tema.nombre)),
        )
        return int(cursor.lastrowid)

    def _id_keyword(self, texto: str) -> int:
        normalizado = normalizar_texto(texto)
        fila = self.conexion.execute(
            "SELECT id FROM keyword WHERE normalizado = ?", (normalizado,)
        ).fetchone()
        if fila:
            return fila["id"]
        cursor = self.conexion.execute(
            "INSERT INTO keyword (texto, normalizado) VALUES (?, ?)", (texto, normalizado)
        )
        return int(cursor.lastrowid)

    # -- portales y datasets ---------------------------------------------------------------
    def registrar_portal(self, portal: Portal) -> None:
        self.conexion.execute(
            "INSERT INTO portal (id, municipio, familia, url_api, url_base, notas) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
            "municipio=excluded.municipio, familia=excluded.familia, "
            "url_api=excluded.url_api, url_base=excluded.url_base, notas=excluded.notas",
            (portal.id, portal.municipio, portal.familia, portal.url_api,
             portal.url_base, portal.notas),
        )

    def vaciar_portal(self, portal_id: str) -> int:
        """Borra los datasets de un portal (y su FTS) para poder reindexarlo limpio."""
        self.conexion.execute(
            "DELETE FROM dataset_fts WHERE dataset_id IN "
            "(SELECT id FROM dataset WHERE portal_id = ?)",
            (portal_id,),
        )
        cursor = self.conexion.execute("DELETE FROM dataset WHERE portal_id = ?", (portal_id,))
        return cursor.rowcount or 0

    def insertar(self, dataset: DatasetNormalizado, guardar_crudo: bool = True) -> int:
        """Inserta un dataset con sus distribuciones, temas, keywords y su fila FTS."""
        if not dataset.fecha_sincronizacion:
            raise ValueError(
                f"dataset sin fecha_sincronizacion: {dataset.identificador_origen}. "
                "La procedencia es obligatoria (TODO 3.2)."
            )
        if not dataset.url_origen:
            raise ValueError(
                f"dataset sin url_origen: {dataset.identificador_origen}. "
                "La procedencia es obligatoria (TODO 3.2)."
            )

        cursor = self.conexion.execute(
            """INSERT INTO dataset (
                   portal_id, identificador_origen, nombre, titulo, descripcion,
                   publicador_id, licencia_id, url_origen, url_recurso_api,
                   fecha_creacion_origen, fecha_modificacion_origen,
                   fecha_modificacion_metadatos, fecha_sincronizacion,
                   frecuencia_actualizacion, idioma, num_distribuciones)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(portal_id, identificador_origen) DO UPDATE SET
                   titulo=excluded.titulo, descripcion=excluded.descripcion,
                   licencia_id=excluded.licencia_id,
                   fecha_modificacion_origen=excluded.fecha_modificacion_origen,
                   fecha_sincronizacion=excluded.fecha_sincronizacion,
                   num_distribuciones=excluded.num_distribuciones""",
            (
                dataset.portal_id,
                dataset.identificador_origen,
                dataset.nombre,
                dataset.titulo,
                dataset.descripcion,
                self._id_publicador(dataset.portal_id, dataset.publicador),
                self._id_licencia(dataset.licencia),
                dataset.url_origen,
                dataset.url_recurso_api,
                dataset.fecha_creacion_origen,
                dataset.fecha_modificacion_origen,
                dataset.fecha_modificacion_metadatos,
                dataset.fecha_sincronizacion,
                dataset.frecuencia_actualizacion,
                dataset.idioma,
                len(dataset.distribuciones),
            ),
        )
        dataset_id = cursor.lastrowid
        if not dataset_id:  # hubo conflicto: recuperar el id existente
            dataset_id = self.conexion.execute(
                "SELECT id FROM dataset WHERE portal_id = ? AND identificador_origen = ?",
                (dataset.portal_id, dataset.identificador_origen),
            ).fetchone()["id"]

        self.conexion.execute("DELETE FROM distribucion WHERE dataset_id = ?", (dataset_id,))
        self.conexion.executemany(
            """INSERT INTO distribucion (
                   dataset_id, identificador_origen, nombre, descripcion, formato, mimetype,
                   url_acceso, url_descarga, tamano_bytes, fecha_creacion_origen,
                   fecha_modificacion_origen, estado, posicion)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    dataset_id, d.identificador_origen, d.nombre, d.descripcion, d.formato,
                    d.mimetype, d.url_acceso, d.url_descarga, d.tamano_bytes,
                    d.fecha_creacion_origen, d.fecha_modificacion_origen, d.estado, d.posicion,
                )
                for d in dataset.distribuciones
            ],
        )

        for tema in dataset.temas:
            self.conexion.execute(
                "INSERT OR IGNORE INTO dataset_tema (dataset_id, tema_id) VALUES (?, ?)",
                (dataset_id, self._id_tema(dataset.portal_id, tema)),
            )
        for palabra in dataset.palabras_clave:
            if palabra.strip():
                self.conexion.execute(
                    "INSERT OR IGNORE INTO dataset_keyword (dataset_id, keyword_id) VALUES (?, ?)",
                    (dataset_id, self._id_keyword(palabra)),
                )

        if guardar_crudo and dataset.crudo is not None:
            self.conexion.execute(
                "INSERT INTO dataset_crudo (dataset_id, json) VALUES (?, ?) "
                "ON CONFLICT(dataset_id) DO UPDATE SET json = excluded.json",
                (dataset_id, json.dumps(dataset.crudo, ensure_ascii=False)),
            )

        texto = dataset.texto_indexable()
        self.conexion.execute("DELETE FROM dataset_fts WHERE dataset_id = ?", (dataset_id,))
        self.conexion.execute(
            "INSERT INTO dataset_fts (titulo, descripcion, palabras_clave, temas, "
            "publicador, dataset_id) VALUES (?,?,?,?,?,?)",
            (
                texto["titulo"], texto["descripcion"], texto["palabras_clave"],
                texto["temas"], texto["publicador"], dataset_id,
            ),
        )
        return int(dataset_id)

    def reemplazar_portal(
        self, portal: Portal, datasets: Iterable[DatasetNormalizado], guardar_crudo: bool = True
    ) -> int:
        """Reindexa un portal entero de forma idempotente."""
        self.registrar_portal(portal)
        self.vaciar_portal(portal.id)
        total = 0
        for dataset in datasets:
            self.insertar(dataset, guardar_crudo=guardar_crudo)
            total += 1
            if total % 200 == 0:
                self.conexion.commit()
        self.conexion.commit()
        return total

    # -- bitácora ---------------------------------------------------------------------------
    def registrar_cosecha(self, resumen: ResumenPortal, errores: list[ErrorPortal]) -> None:
        cursor = self.conexion.execute(
            "INSERT INTO cosecha (portal_id, inicio, fin, estado, n_datasets, "
            "n_distribuciones, n_peticiones, n_reintentos, segundos, crawl_delay, error) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                resumen.portal_id, resumen.inicio, resumen.fin, resumen.estado,
                resumen.n_datasets, resumen.n_distribuciones, resumen.n_peticiones,
                resumen.n_reintentos, resumen.segundos, resumen.crawl_delay, resumen.error,
            ),
        )
        cosecha_id = cursor.lastrowid
        self.conexion.executemany(
            "INSERT INTO error_cosecha (cosecha_id, portal_id, momento, tipo, mensaje, "
            "url, codigo_http, intento, definitivo) VALUES (?,?,?,?,?,?,?,?,?)",
            [
                (cosecha_id, e.portal_id, e.momento, e.tipo, e.mensaje, e.url,
                 e.codigo_http, e.intento, int(e.definitivo))
                for e in errores
            ],
        )
        self._anotar("ultima_sincronizacion", ahora_utc())
        self.conexion.commit()

    # -- consulta ---------------------------------------------------------------------------
    def buscar(
        self,
        consulta: str = "",
        portal_id: str | None = None,
        tema: str | None = None,
        anio: int | None = None,
        limite: int = 10,
    ) -> list[sqlite3.Row]:
        """Búsqueda por texto con filtros. Es la base de `buscar_datasets` (fase 3.4).

        Devuelve siempre la procedencia (`url_origen`, fechas, licencia y si está
        declarada): ninguna herramienta MCP debe poder responder sin ella.
        """
        campos = """
            d.id, d.portal_id, p.municipio, d.identificador_origen, d.nombre, d.titulo,
            d.descripcion, d.url_origen, d.fecha_modificacion_origen, d.fecha_sincronizacion,
            d.num_distribuciones, l.identificador AS licencia, l.declarada AS licencia_declarada
        """
        union = """
            FROM dataset d
            JOIN portal p ON p.id = d.portal_id
            JOIN licencia l ON l.id = d.licencia_id
        """
        condiciones, parametros = [], []
        expresion = construir_consulta_fts(consulta)
        if expresion:
            union += " JOIN dataset_fts f ON f.dataset_id = d.id "
            condiciones.append("dataset_fts MATCH ?")
            parametros.append(expresion)
            orden = "ORDER BY bm25(dataset_fts, 8.0, 2.0, 4.0, 2.0, 1.0)"
        else:
            orden = "ORDER BY d.fecha_modificacion_origen DESC"
        if portal_id:
            condiciones.append("d.portal_id = ?")
            parametros.append(portal_id)
        if tema:
            union += (
                " JOIN dataset_tema dt ON dt.dataset_id = d.id "
                " JOIN tema t ON t.id = dt.tema_id "
            )
            condiciones.append("t.normalizado LIKE ?")
            parametros.append(f"%{normalizar_texto(tema)}%")
        if anio:
            condiciones.append("substr(d.fecha_modificacion_origen, 1, 4) = ?")
            parametros.append(str(anio))
        donde = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
        sql = f"SELECT {campos} {union} {donde} {orden} LIMIT ?"
        return self.conexion.execute(sql, (*parametros, limite)).fetchall()

    def estadisticas(self) -> dict:
        def escalar(sql: str, *args) -> int:
            fila = self.conexion.execute(sql, args).fetchone()
            return int(fila[0]) if fila and fila[0] is not None else 0

        por_portal = self.conexion.execute(
            "SELECT p.id, p.municipio, COUNT(d.id) AS n, "
            "  SUM(CASE WHEN l.declarada = 0 THEN 1 ELSE 0 END) AS sin_licencia "
            "FROM portal p LEFT JOIN dataset d ON d.portal_id = p.id "
            "LEFT JOIN licencia l ON l.id = d.licencia_id GROUP BY p.id ORDER BY n DESC"
        ).fetchall()
        return {
            "datasets": escalar("SELECT COUNT(*) FROM dataset"),
            "distribuciones": escalar("SELECT COUNT(*) FROM distribucion"),
            "keywords": escalar("SELECT COUNT(*) FROM keyword"),
            "sin_licencia": escalar("SELECT COUNT(*) FROM dataset d JOIN licencia l "
                                    "ON l.id = d.licencia_id WHERE l.declarada = 0"),
            "bytes_indice": self.ruta.stat().st_size if self.ruta.exists() else 0,
            "por_portal": [dict(f) for f in por_portal],
        }
