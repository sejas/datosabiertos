"""`ConectorCatalogo`: la interfaz que todo portal debe implementar.

# Punto de extensión (léelo antes de añadir un portal)

Añadir un portal nuevo —Gijón y Zaragoza son los que faltan, y son la tarea 2.1 del
`TODOS.md`— consiste **exactamente** en tres pasos, sin tocar nada más del paquete:

1. Crear `tfm/conectores/<familia>.py` con una subclase de `ConectorCatalogo` que
   implemente dos métodos:

   - `listar_crudos()`: genera los registros tal y como los devuelve el portal (dict).
     Aquí va la paginación, el `descargar.php` de Gijón o el REST propio de Zaragoza.
     Debe usar `self.cliente.obtener_json(...)` para heredar cortesía, reintentos y log.
   - `normalizar(crudo)`: traduce un registro crudo a `DatasetNormalizado`.

2. Registrar la familia en `tfm/conectores/__init__.py` (diccionario `FAMILIAS`).

3. Dar de alta el portal en `CORPUS` de `tfm/configuracion.py` con `familia="<familia>"`.

Todo lo demás —cortesía, `robots.txt`, *backoff*, esquema SQLite, FTS5, procedencia,
marcado de licencia no declarada, CLI— ya funciona para el conector nuevo. El método
plantilla `cosechar()` no se sobrescribe: es el que garantiza que ningún dataset entre en
el índice sin `fecha_sincronizacion` ni `url_origen`.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator

from ..configuracion import Portal
from ..cortesia import ClienteCortes, ErrorCosecha
from ..modelo import DatasetNormalizado
from ..registro import RegistroCosecha, ahora_utc


class ConectorCatalogo(ABC):
    """Interfaz común a todos los catálogos, sea cual sea su plataforma."""

    #: Identificador de familia; debe coincidir con la clave de `FAMILIAS`.
    familia: str = "abstracta"

    def __init__(self, portal: Portal, cliente: ClienteCortes, registro: RegistroCosecha) -> None:
        self.portal = portal
        self.cliente = cliente
        self.registro = registro

    # -- lo que cada plataforma tiene que implementar --------------------------------------
    @abstractmethod
    def listar_crudos(self) -> Iterator[dict]:
        """Genera los registros de dataset tal y como los devuelve el portal."""

    @abstractmethod
    def normalizar(self, crudo: dict) -> DatasetNormalizado | None:
        """Traduce un registro crudo a `DatasetNormalizado`, o `None` si hay que ignorarlo."""

    # -- opcional --------------------------------------------------------------------------
    def total_declarado(self) -> int | None:
        """Nº de datasets que el portal dice tener, si lo sabe decir antes de paginar."""
        return None

    # -- método plantilla: no sobrescribir ---------------------------------------------------
    def cosechar(self) -> Iterator[DatasetNormalizado]:
        """Prepara la cortesía, recorre el catálogo y garantiza la procedencia."""
        resumen = self.registro.resumen(self.portal.id)
        resumen.inicio = ahora_utc()
        comienzo = time.monotonic()

        crawl_delay = self.cliente.preparar_robots(self.portal.url_api, self.portal.id)
        resumen.crawl_delay = crawl_delay
        retardo_extra = self.portal.parametros.get("retardo_minimo")
        if retardo_extra:
            self.cliente.fijar_retardo_minimo(self.portal.url_api, float(retardo_extra))
            self.registro.info(
                self.portal.id, f"retardo mínimo específico del portal: {retardo_extra}s"
            )

        n_ok = n_fallo = 0
        try:
            for crudo in self.listar_crudos():
                try:
                    dataset = self.normalizar(crudo)
                except Exception as exc:  # noqa: BLE001 - un registro roto no tumba el portal
                    n_fallo += 1
                    self.registro.error(
                        self.portal.id,
                        "normalizacion",
                        f"{type(exc).__name__}: {exc} en {crudo.get('name') or crudo.get('id')}",
                    )
                    continue
                if dataset is None:
                    continue
                # Procedencia obligatoria (TODO 3.2): se sella aquí, no en el conector.
                dataset.fecha_sincronizacion = ahora_utc()
                if not dataset.url_origen:
                    dataset.url_origen = f"{self.portal.url_base}/dataset/{dataset.nombre}"
                n_ok += 1
                yield dataset
        except ErrorCosecha as exc:
            resumen.estado = "error" if n_ok == 0 else "parcial"
            resumen.error = str(exc)
            self.registro.error(
                self.portal.id,
                "cosecha",
                f"cosecha interrumpida tras {n_ok} datasets: {exc}",
                url=exc.url,
                codigo_http=exc.codigo_http,
                definitivo=True,
            )
        else:
            resumen.estado = "ok" if n_fallo == 0 else "parcial"
        finally:
            resumen.n_datasets = n_ok
            resumen.segundos = round(time.monotonic() - comienzo, 2)
            resumen.fin = ahora_utc()
            self.registro.info(
                self.portal.id,
                f"cosecha {resumen.estado}: {n_ok} datasets, {n_fallo} descartados, "
                f"{resumen.n_peticiones} peticiones, {resumen.n_reintentos} reintentos, "
                f"{resumen.segundos}s",
            )
