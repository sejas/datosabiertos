"""Configuración del corpus de portales y de los límites de cosecha cortés.

Todo lo configurable vive aquí o en variables de entorno, para que la cosecha se pueda
ajustar sin tocar el código de los conectores.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------------------
# Identidad del proyecto (obligatoria para una cosecha cortés: TODO 3.3)
# --------------------------------------------------------------------------------------

NOMBRE_PROYECTO = "TFM-MCP-datos-abiertos"
VERSION = "0.1.0"
URL_PROYECTO = "https://github.com/sejas/datosabiertos"

#: Correo de contacto que se anuncia en el `User-Agent`. Sustituible por entorno para que
#: quien reejecute la cosecha ponga el suyo y no el del autor.
CORREO_CONTACTO = os.environ.get("TFM_CORREO_CONTACTO", "datosabiertos@sejas.es")


def user_agent() -> str:
    """`User-Agent` identificable: proyecto, versión, URL del repositorio y contacto.

    Un administrador que vea esta cadena en sus logs sabe quién le está cosechando y a
    quién escribir. Es el mínimo exigible por §4.3 y §6.5 de `docs/02-analisis-catalogos.md`.
    """
    return (
        f"{NOMBRE_PROYECTO}/{VERSION} "
        f"(+{URL_PROYECTO}; contacto: {CORREO_CONTACTO}) "
        f"Python-urllib"
    )


# --------------------------------------------------------------------------------------
# Límites de cortesía
# --------------------------------------------------------------------------------------

#: Peticiones simultáneas como máximo contra un mismo host. Barcelona devolvió 503 en 28 de
#: 30 peticiones con 10 hilos y 200 en 8 de 8 serializando a 3 s (§4.2 del análisis).
CONCURRENCIA_POR_HOST = int(os.environ.get("TFM_CONCURRENCIA_POR_HOST", "2"))

#: Portales cosechados en paralelo (hosts distintos). No afecta a la carga de cada portal.
CONCURRENCIA_PORTALES = int(os.environ.get("TFM_CONCURRENCIA_PORTALES", "3"))

#: Retardo mínimo entre dos peticiones al mismo host cuando robots.txt no dice nada.
RETARDO_POR_DEFECTO = float(os.environ.get("TFM_RETARDO_POR_DEFECTO", "1.0"))

#: Tope al `Crawl-Delay` que se acepta de un robots.txt. Protege de un valor absurdo que
#: dejaría la cosecha corriendo días. Málaga declara 10 s y se respeta íntegro.
CRAWL_DELAY_MAXIMO = float(os.environ.get("TFM_CRAWL_DELAY_MAXIMO", "30"))

#: Intentos totales por petición (1 original + reintentos).
INTENTOS_MAXIMOS = int(os.environ.get("TFM_INTENTOS_MAXIMOS", "5"))

#: Base del *backoff* exponencial: espera = BACKOFF_BASE * 2**(intento-1) + jitter.
BACKOFF_BASE = float(os.environ.get("TFM_BACKOFF_BASE", "2.0"))
BACKOFF_MAXIMO = float(os.environ.get("TFM_BACKOFF_MAXIMO", "120.0"))

#: Tiempo de espera de una petición HTTP, en segundos.
TIEMPO_ESPERA = float(os.environ.get("TFM_TIEMPO_ESPERA", "60"))

#: Códigos HTTP que merecen reintento con espera creciente.
CODIGOS_REINTENTABLES = frozenset({408, 429, 500, 502, 503, 504, 509, 522, 524})

#: Si es cierto, un `Disallow` en robots.txt aborta la cosecha de ese portal.
#: Por defecto es falso y el conflicto se registra como aviso: `robots.txt` gobierna
#: *crawlers* de contenido, no clientes de una API JSON documentada y pública, y la
#: Directiva (UE) 2019/1024 obliga al organismo a ofrecer justamente esa API. Málaga
#: declara `Disallow: /api/` a la vez que publica su API CKAN. El `Crawl-Delay` sí se
#: respeta siempre. Quien quiera la lectura estricta, exporta TFM_RESPETAR_DISALLOW=1.
RESPETAR_DISALLOW = os.environ.get("TFM_RESPETAR_DISALLOW", "0") not in ("0", "", "no")


# --------------------------------------------------------------------------------------
# Rutas
# --------------------------------------------------------------------------------------

RAIZ = Path(__file__).resolve().parent.parent
DIRECTORIO_DATOS = Path(os.environ.get("TFM_DIRECTORIO_DATOS", RAIZ / "datos"))
RUTA_INDICE = Path(os.environ.get("TFM_RUTA_INDICE", DIRECTORIO_DATOS / "indice.sqlite"))
RUTA_LOG = Path(os.environ.get("TFM_RUTA_LOG", DIRECTORIO_DATOS / "cosecha.log"))


# --------------------------------------------------------------------------------------
# Corpus de portales
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Portal:
    """Un portal municipal cosechable.

    `familia` selecciona el conector (véase `tfm.conectores.crear_conector`). Añadir Gijón
    o Zaragoza en la fase 2.1 es añadir una familia nueva y su subclase de
    `ConectorCatalogo`, sin tocar nada más.
    """

    id: str
    municipio: str
    familia: str
    url_api: str
    url_base: str
    notas: str = ""
    parametros: dict = field(default_factory=dict)


CORPUS: dict[str, Portal] = {
    "madrid": Portal(
        id="madrid",
        municipio="Madrid",
        familia="ckan",
        url_api="https://datos.madrid.es/api/3/action",
        url_base="https://datos.madrid.es",
        notas=(
            "98/100 en la rúbrica. WAF/anti-bot bloquea la descarga programática de "
            "recursos (403), no la API de catálogo. Publica catalog.rdf."
        ),
    ),
    "barcelona": Portal(
        id="barcelona",
        municipio="Barcelona",
        familia="ckan",
        url_api="https://opendata-ajuntament.barcelona.cat/data/api/3/action",
        url_base="https://opendata-ajuntament.barcelona.cat/data",
        notas=(
            "90/100. Rate-limiting agresivo: 503 con 10 peticiones concurrentes, 200 "
            "serializando a 3 s. Su `organization` es el departamento, no el ayuntamiento."
        ),
        parametros={"retardo_minimo": 3.0, "filas_por_pagina": 100},
    ),
    "malaga": Portal(
        id="malaga",
        municipio="Málaga",
        familia="ckan",
        url_api="https://datosabiertos.malaga.eu/api/3/action",
        url_base="https://datosabiertos.malaga.eu",
        notas=(
            "78/100. robots.txt fija Crawl-Delay: 10 y Disallow: /api/. Licencia by-sa-40, "
            "la más restrictiva del corpus: condiciona la licencia del índice publicado."
        ),
    ),
    "cordoba": Portal(
        id="cordoba",
        municipio="Córdoba",
        familia="ckan",
        url_api="https://datosabiertos.cordoba.es/api/3/action",
        url_base="https://datosabiertos.cordoba.es",
        notas=(
            "61/100, peor caso del corpus: 145 de 145 datasets sin licencia declarada "
            "y 83 % de recursos en PDF."
        ),
    ),
    "reus": Portal(
        id="reus",
        municipio="Reus",
        familia="ckan",
        url_api="https://opendata.reus.cat/api/3/action",
        url_base="https://opendata.reus.cat",
        notas="78/100, mejor caso limpio: catálogo pequeño, fresco y con licencia única.",
    ),
}

#: Portales previstos para la fase 2.1 y todavía no implementados. Se listan para que
#: `python -m tfm.index portales` deje explícito el hueco en lugar de ocultarlo.
PENDIENTES_FASE_2_1 = {
    "gijon": "opendata.gijon.es — REST ad-hoc (`descargar.php`), sin API CKAN",
    "zaragoza": "zaragoza.es/sede/servicio — REST propio, sin API CKAN",
}


def portales(ids: list[str] | None = None) -> list[Portal]:
    """Devuelve los portales pedidos, o el corpus entero si no se pide ninguno."""
    if not ids:
        return list(CORPUS.values())
    seleccion = []
    for identificador in ids:
        clave = identificador.strip().lower()
        if clave not in CORPUS:
            disponibles = ", ".join(sorted(CORPUS))
            pendiente = PENDIENTES_FASE_2_1.get(clave)
            extra = f" (pendiente de la fase 2.1: {pendiente})" if pendiente else ""
            raise KeyError(f"portal desconocido: {identificador}{extra}. Disponibles: {disponibles}")
        seleccion.append(CORPUS[clave])
    return seleccion
