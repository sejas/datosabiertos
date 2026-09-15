"""Cliente HTTP cortés: robots.txt, `Crawl-Delay`, concurrencia por host y *backoff*.

Implementa el TODO 3.3. Las cinco garantías que da esta clase:

1. **Concurrencia máxima por host** configurable (`CONCURRENCIA_POR_HOST`, por defecto 2).
   Un semáforo por host, no global: dos portales distintos no compiten entre sí.
2. **`Crawl-Delay` de robots.txt respetado** (`urllib.robotparser`). Si el portal no
   declara ninguno se aplica `RETARDO_POR_DEFECTO`. El retardo se mide entre el *final* de
   una petición y el *inicio* de la siguiente al mismo host.
3. **`User-Agent` identificable** con proyecto, versión, URL y correo de contacto.
4. **Reintentos con *backoff* exponencial** ante 429/503 (y 408/500/502/504/509/522/524) y
   ante *timeouts*, honrando `Retry-After` cuando el servidor lo envía.
5. **Todo fallo queda registrado** por portal en `RegistroCosecha`.

No usa `requests` ni ninguna otra dependencia externa: solo `urllib`.
"""

from __future__ import annotations

import gzip
import json
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import zlib
from dataclasses import dataclass

from . import configuracion as cfg
from .registro import RegistroCosecha


class ErrorCosecha(Exception):
    """Fallo definitivo contra un portal: se agotaron los reintentos."""

    def __init__(self, mensaje: str, url: str = "", codigo_http: int | None = None) -> None:
        super().__init__(mensaje)
        self.url = url
        self.codigo_http = codigo_http


@dataclass
class _EstadoHost:
    """Estado de cortesía de un host concreto."""

    semaforo: threading.Semaphore
    cerrojo: threading.Lock
    proximo_permitido: float = 0.0
    retardo: float = cfg.RETARDO_POR_DEFECTO
    crawl_delay_declarado: float | None = None
    robots_leido: bool = False
    robots: urllib.robotparser.RobotFileParser | None = None


class ClienteCortes:
    """Cliente HTTP que se porta bien con portales municipales pequeños."""

    def __init__(
        self,
        registro: RegistroCosecha,
        concurrencia_por_host: int = cfg.CONCURRENCIA_POR_HOST,
        retardo_por_defecto: float = cfg.RETARDO_POR_DEFECTO,
        intentos_maximos: int = cfg.INTENTOS_MAXIMOS,
        tiempo_espera: float = cfg.TIEMPO_ESPERA,
        respetar_disallow: bool = cfg.RESPETAR_DISALLOW,
        semilla: int | None = 42,
    ) -> None:
        if concurrencia_por_host < 1:
            raise ValueError("la concurrencia por host debe ser >= 1")
        self.registro = registro
        self.concurrencia_por_host = concurrencia_por_host
        self.retardo_por_defecto = retardo_por_defecto
        self.intentos_maximos = max(1, intentos_maximos)
        self.tiempo_espera = tiempo_espera
        self.respetar_disallow = respetar_disallow
        self.user_agent = cfg.user_agent()
        self._hosts: dict[str, _EstadoHost] = {}
        self._cerrojo_hosts = threading.Lock()
        self._azar = random.Random(semilla)
        self._cerrojo_azar = threading.Lock()

    # -- estado por host ------------------------------------------------------------------
    def _estado(self, host: str) -> _EstadoHost:
        with self._cerrojo_hosts:
            if host not in self._hosts:
                self._hosts[host] = _EstadoHost(
                    semaforo=threading.Semaphore(self.concurrencia_por_host),
                    cerrojo=threading.Lock(),
                    retardo=self.retardo_por_defecto,
                )
            return self._hosts[host]

    def fijar_retardo_minimo(self, url: str, retardo: float) -> None:
        """Impone un retardo mínimo adicional para un host (p. ej. Barcelona, 3 s)."""
        estado = self._estado(urllib.parse.urlsplit(url).netloc)
        with estado.cerrojo:
            estado.retardo = max(estado.retardo, retardo)

    # -- robots.txt -----------------------------------------------------------------------
    def preparar_robots(self, url: str, portal_id: str = "-") -> float | None:
        """Lee robots.txt del host de `url` y aplica su `Crawl-Delay`.

        Devuelve el `Crawl-Delay` declarado, o `None` si el portal no declara ninguno.
        Un robots.txt inaccesible no es un error fatal: se conserva el retardo por defecto
        y se anota como aviso.
        """
        partes = urllib.parse.urlsplit(url)
        host = partes.netloc
        estado = self._estado(host)
        with estado.cerrojo:
            if estado.robots_leido:
                return estado.crawl_delay_declarado
            estado.robots_leido = True

        url_robots = f"{partes.scheme}://{host}/robots.txt"
        analizador = urllib.robotparser.RobotFileParser()
        analizador.set_url(url_robots)
        try:
            peticion = urllib.request.Request(
                url_robots, headers={"User-Agent": self.user_agent}
            )
            with urllib.request.urlopen(peticion, timeout=min(30.0, self.tiempo_espera)) as resp:
                texto = resp.read().decode("utf-8", errors="replace")
            analizador.parse(texto.splitlines())
        except Exception as exc:  # noqa: BLE001 - robots.txt ausente es lo normal
            self.registro.aviso(
                portal_id, f"robots.txt no legible en {url_robots}: {type(exc).__name__}: {exc}"
            )
            return None

        declarado = None
        for agente in (cfg.NOMBRE_PROYECTO, self.user_agent, "*"):
            try:
                valor = analizador.crawl_delay(agente)
            except Exception:  # noqa: BLE001
                valor = None
            if valor is not None:
                declarado = float(valor)
                break

        with estado.cerrojo:
            estado.robots = analizador
            estado.crawl_delay_declarado = declarado
            if declarado is not None:
                efectivo = min(declarado, cfg.CRAWL_DELAY_MAXIMO)
                estado.retardo = max(estado.retardo, efectivo)
                if efectivo < declarado:
                    self.registro.aviso(
                        portal_id,
                        f"Crawl-Delay declarado {declarado}s recortado a "
                        f"{efectivo}s por TFM_CRAWL_DELAY_MAXIMO",
                    )
                else:
                    self.registro.info(
                        portal_id, f"robots.txt: Crawl-Delay {declarado}s respetado en {host}"
                    )
            else:
                self.registro.info(
                    portal_id,
                    f"robots.txt sin Crawl-Delay en {host}; se usa "
                    f"{estado.retardo}s por defecto",
                )
        return declarado

    def permitido_por_robots(self, url: str, portal_id: str = "-") -> bool:
        """¿Permite robots.txt esta URL para nuestro `User-Agent`?

        Un `Disallow` se registra siempre. Bloquea la petición solo si
        `respetar_disallow` está activo (véase la justificación en `configuracion.py`).
        """
        estado = self._estado(urllib.parse.urlsplit(url).netloc)
        analizador = estado.robots
        if analizador is None:
            return True
        try:
            permitido = analizador.can_fetch(self.user_agent, url)
        except Exception:  # noqa: BLE001
            return True
        if not permitido:
            self.registro.aviso(
                portal_id,
                f"robots.txt declara Disallow para {url}. "
                + (
                    "TFM_RESPETAR_DISALLOW activo: se omite."
                    if self.respetar_disallow
                    else "Se continúa por tratarse de la API JSON pública y documentada; "
                    "el Crawl-Delay sí se respeta."
                ),
            )
        return permitido or not self.respetar_disallow

    # -- espera de cortesía -----------------------------------------------------------------
    def _esperar_turno(self, host: str) -> None:
        estado = self._estado(host)
        while True:
            with estado.cerrojo:
                ahora = time.monotonic()
                if ahora >= estado.proximo_permitido:
                    estado.proximo_permitido = ahora + estado.retardo
                    return
                falta = estado.proximo_permitido - ahora
            time.sleep(min(falta, 5.0))

    def _dormir_backoff(self, intento: int, retry_after: float | None) -> float:
        """Espera exponencial con *jitter*; `Retry-After` manda si el servidor lo envía."""
        if retry_after is not None:
            espera = min(retry_after, cfg.BACKOFF_MAXIMO)
        else:
            with self._cerrojo_azar:
                jitter = self._azar.uniform(0, cfg.BACKOFF_BASE)
            espera = min(cfg.BACKOFF_BASE * (2 ** (intento - 1)) + jitter, cfg.BACKOFF_MAXIMO)
        time.sleep(espera)
        return espera

    @staticmethod
    def _retry_after(cabeceras) -> float | None:
        bruto = cabeceras.get("Retry-After") if cabeceras else None
        if not bruto:
            return None
        try:
            return float(bruto)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _descomprimir(datos: bytes, codificacion: str | None) -> bytes:
        if not codificacion:
            return datos
        codificacion = codificacion.lower()
        if codificacion == "gzip":
            return gzip.decompress(datos)
        if codificacion == "deflate":
            return zlib.decompress(datos)
        return datos

    # -- petición -----------------------------------------------------------------------
    def obtener(self, url: str, portal_id: str = "-", cabeceras: dict | None = None) -> bytes:
        """GET con cortesía y reintentos. Lanza `ErrorCosecha` si se agotan los intentos."""
        host = urllib.parse.urlsplit(url).netloc
        estado = self._estado(host)
        resumen = self.registro.resumen(portal_id)

        if not self.permitido_por_robots(url, portal_id):
            raise ErrorCosecha(f"robots.txt prohíbe {url} y TFM_RESPETAR_DISALLOW está activo", url)

        cabeceras_finales = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, */*;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "es,ca;q=0.8,en;q=0.5",
            "From": cfg.CORREO_CONTACTO,
        }
        cabeceras_finales.update(cabeceras or {})

        ultimo: Exception | None = None
        for intento in range(1, self.intentos_maximos + 1):
            with estado.semaforo:
                self._esperar_turno(host)
                resumen.n_peticiones += 1
                inicio = time.monotonic()
                try:
                    peticion = urllib.request.Request(url, headers=cabeceras_finales)
                    with urllib.request.urlopen(peticion, timeout=self.tiempo_espera) as resp:
                        datos = self._descomprimir(
                            resp.read(), resp.headers.get("Content-Encoding")
                        )
                    self.registro.depuracion(
                        portal_id,
                        f"200 {len(datos)}B en {time.monotonic() - inicio:.1f}s {url}",
                    )
                    return datos
                except urllib.error.HTTPError as exc:
                    ultimo = exc
                    reintentable = exc.code in cfg.CODIGOS_REINTENTABLES
                    espera_sugerida = self._retry_after(exc.headers)
                    self.registro.error(
                        portal_id,
                        "http",
                        f"HTTP {exc.code} {exc.reason}",
                        url=url,
                        codigo_http=exc.code,
                        intento=intento,
                        definitivo=not reintentable or intento == self.intentos_maximos,
                    )
                    if not reintentable:
                        raise ErrorCosecha(f"HTTP {exc.code} {exc.reason}", url, exc.code) from exc
                except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                    ultimo = exc
                    espera_sugerida = None
                    self.registro.error(
                        portal_id,
                        "red",
                        f"{type(exc).__name__}: {exc}",
                        url=url,
                        intento=intento,
                        definitivo=intento == self.intentos_maximos,
                    )

            # el backoff se duerme FUERA del semáforo: no se bloquea el host entero
            if intento < self.intentos_maximos:
                resumen.n_reintentos += 1
                espera = self._dormir_backoff(intento, espera_sugerida)
                self.registro.depuracion(
                    portal_id, f"reintento {intento + 1}/{self.intentos_maximos} tras {espera:.1f}s"
                )

        codigo = getattr(ultimo, "code", None)
        raise ErrorCosecha(
            f"agotados {self.intentos_maximos} intentos: {type(ultimo).__name__}: {ultimo}",
            url,
            codigo,
        )

    def obtener_json(self, url: str, portal_id: str = "-") -> dict:
        """GET que además decodifica JSON, con el error de parseo bien atribuido."""
        datos = self.obtener(url, portal_id)
        try:
            return json.loads(datos.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.registro.error(
                portal_id, "json", f"respuesta no es JSON válido: {exc}", url=url, definitivo=True
            )
            raise ErrorCosecha(f"respuesta no es JSON válido: {exc}", url) from exc
