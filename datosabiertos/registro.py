"""Registro de eventos y de errores por portal.

Dos destinos complementarios, tal y como exige el TODO 3.3:

1. Un fichero de log rotativo (`datos/cosecha.log`) legible por una persona.
2. La tabla `error_cosecha` del índice, consultable con SQL y con
   `python -m datosabiertos.index errores --portal madrid`.

El objeto `RegistroCosecha` es el que se pasa al cliente HTTP y a los conectores; acumula
los errores en memoria y el almacén los vuelca a SQLite al cerrar la cosecha.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

_configurado = False


def configurar_log(ruta: Path, verboso: bool = False) -> logging.Logger:
    """Configura el log a fichero y a consola. Idempotente."""
    global _configurado
    registrador = logging.getLogger("datosabiertos")
    if not _configurado:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        formato = logging.Formatter(
            "%(asctime)s %(levelname)-7s [%(portal)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

        class _RellenaPortal(logging.Filter):
            def filter(self, registro_log: logging.LogRecord) -> bool:
                if not hasattr(registro_log, "portal"):
                    registro_log.portal = "-"
                return True

        fichero = RotatingFileHandler(ruta, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
        fichero.setFormatter(formato)
        fichero.setLevel(logging.DEBUG)

        consola = logging.StreamHandler()
        consola.setFormatter(formato)
        consola.setLevel(logging.DEBUG if verboso else logging.INFO)

        registrador.addFilter(_RellenaPortal())
        registrador.addHandler(fichero)
        registrador.addHandler(consola)
        registrador.setLevel(logging.DEBUG)
        registrador.propagate = False
        _configurado = True
    return registrador


def ahora_utc() -> str:
    """Marca de tiempo ISO-8601 en UTC, la que se guarda en `fecha_sincronizacion`."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class ErrorPortal:
    """Un fallo concreto contra un portal, con lo necesario para reproducirlo."""

    portal_id: str
    momento: str
    tipo: str
    mensaje: str
    url: str = ""
    codigo_http: int | None = None
    intento: int = 1
    definitivo: bool = False


@dataclass
class ResumenPortal:
    """Resultado de cosechar un portal. Se persiste en la tabla `cosecha`."""

    portal_id: str
    inicio: str = ""
    fin: str = ""
    n_datasets: int = 0
    n_distribuciones: int = 0
    n_peticiones: int = 0
    n_reintentos: int = 0
    segundos: float = 0.0
    crawl_delay: float | None = None
    estado: str = "pendiente"  # pendiente | ok | parcial | error
    error: str = ""

    def como_dict(self) -> dict:
        return asdict(self)


class RegistroCosecha:
    """Acumulador de errores y resúmenes, seguro entre hilos."""

    def __init__(self, ruta_log: Path, verboso: bool = False) -> None:
        self.log = configurar_log(ruta_log, verboso)
        self.errores: list[ErrorPortal] = []
        self.resumenes: dict[str, ResumenPortal] = {}
        self._cerrojo = threading.Lock()

    # -- logging con portal en el prefijo ------------------------------------------------
    def info(self, portal_id: str, mensaje: str) -> None:
        self.log.info(mensaje, extra={"portal": portal_id})

    def aviso(self, portal_id: str, mensaje: str) -> None:
        self.log.warning(mensaje, extra={"portal": portal_id})

    def depuracion(self, portal_id: str, mensaje: str) -> None:
        self.log.debug(mensaje, extra={"portal": portal_id})

    # -- errores ------------------------------------------------------------------------
    def error(
        self,
        portal_id: str,
        tipo: str,
        mensaje: str,
        url: str = "",
        codigo_http: int | None = None,
        intento: int = 1,
        definitivo: bool = False,
    ) -> ErrorPortal:
        registro = ErrorPortal(
            portal_id=portal_id,
            momento=ahora_utc(),
            tipo=tipo,
            mensaje=mensaje[:2000],
            url=url,
            codigo_http=codigo_http,
            intento=intento,
            definitivo=definitivo,
        )
        with self._cerrojo:
            self.errores.append(registro)
        nivel = self.log.error if definitivo else self.log.warning
        nivel(
            f"{tipo}: {mensaje} (intento {intento}{', DEFINITIVO' if definitivo else ''})"
            + (f" url={url}" if url else ""),
            extra={"portal": portal_id},
        )
        return registro

    # -- resúmenes ----------------------------------------------------------------------
    def resumen(self, portal_id: str) -> ResumenPortal:
        with self._cerrojo:
            if portal_id not in self.resumenes:
                self.resumenes[portal_id] = ResumenPortal(portal_id=portal_id, inicio=ahora_utc())
            return self.resumenes[portal_id]

    def errores_de(self, portal_id: str) -> list[ErrorPortal]:
        with self._cerrojo:
            return [e for e in self.errores if e.portal_id == portal_id]
