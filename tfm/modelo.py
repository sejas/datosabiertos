"""Representación normalizada de un dataset, independiente de la plataforma de origen.

Un conector traduce el JSON crudo del portal a estas estructuras; el almacén solo sabe de
estas estructuras. Es la frontera que permite añadir Gijón o Zaragoza (fase 2.1) sin tocar
el esquema de SQLite ni las herramientas MCP de la fase 3.4.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime

# --------------------------------------------------------------------------------------
# Licencias
# --------------------------------------------------------------------------------------

#: Identificador reservado para los datasets sin licencia declarada (TODO 3.2).
#: **Nunca** se asume CC-BY: si el portal no lo dice, el índice dice que no lo dice.
LICENCIA_NO_DECLARADA = "no-declarada"
TITULO_NO_DECLARADA = "No declarada por el portal de origen"

#: Valores que los portales usan para decir "no hay licencia". Córdoba usa `notspecified`
#: en el 43 % de sus datasets. Comparados en minúsculas y sin acentos.
#: Se comparan tras pasar por `clave_licencia()`, que unifica guiones y guiones bajos con
#: espacios: así "notspecified", "not-specified", "not_specified" y "Not Specified" —las
#: cuatro formas que aparecen en los portales del corpus— colapsan en la misma clave.
VALORES_SIN_LICENCIA = frozenset(
    {
        "",
        "-",
        "none",
        "null",
        "notspecified",
        "not specified",
        "license not specified",
        "no especificada",
        "no se especifico la licencia",
        "sin licencia",
        "unspecified",
        "desconocida",
        "unknown",
    }
)

#: Los `other-*` de CKAN (`other-at`, `other-open`, `other-nc`…) **sí** son una licencia
#: declarada, solo que sin identificador estándar. Se conservan como declaradas y sin
#: reinterpretar: convertirlas en "no declarada" inflaría la cifra del 3 % del §6 del
#: análisis, y convertirlas en CC-BY sería exactamente lo que el TODO 3.2 prohíbe.


@dataclass
class Licencia:
    """Licencia tal y como la declara el portal, más el veredicto del índice.

    `declarada` es el campo que consumen las herramientas MCP: si es `False`, la respuesta
    debe decir literalmente "licencia no declarada".
    """

    identificador: str
    titulo: str = ""
    url: str = ""
    declarada: bool = True
    identificador_origen: str = ""


def normalizar_texto(texto: str | None) -> str:
    """Minúsculas, sin acentos y con espacios colapsados. Para comparar, no para mostrar."""
    if not texto:
        return ""
    sin_acentos = unicodedata.normalize("NFKD", str(texto))
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin_acentos).strip().lower()


def clave_licencia(texto: str | None) -> str:
    """Clave comparable de una licencia: sin acentos, sin mayúsculas y con los separadores
    unificados. `notspecified`, `not-specified`, `not_specified` y "Not Specified" —las
    cuatro formas presentes en los portales del corpus— dan la misma clave."""
    return re.sub(r"[\s_-]+", " ", normalizar_texto(texto)).strip()


def normalizar_licencia(
    identificador: str | None, titulo: str | None = None, url: str | None = None
) -> Licencia:
    """Traduce la licencia del portal a una `Licencia`, marcando la ausencia como tal.

    Regla dura del TODO 3.2: ausencia, cadena vacía o `notspecified` ⇒ `declarada=False`
    con identificador `no-declarada`. Jamás se rellena con CC-BY.
    """
    bruto = (identificador or "").strip()
    clave = normalizar_texto(bruto)
    clave_comparable = clave_licencia(bruto)
    titulo_normalizado = clave_licencia(titulo)

    no_declarada = Licencia(
        identificador=LICENCIA_NO_DECLARADA,
        titulo=TITULO_NO_DECLARADA,
        url="",
        declarada=False,
        identificador_origen=bruto,
    )

    # El identificador manda: si el portal dice explícitamente `notspecified`, la licencia
    # no está declarada por mucho que CKAN rellene un título genérico.
    if clave_comparable and clave_comparable in VALORES_SIN_LICENCIA:
        return no_declarada

    # Sin identificador, decide el título. Ojo: un `license_title` vacío NO significa
    # ausencia de licencia si hay identificador — muchos portales solo mandan `license_id`.
    if not clave_comparable:
        if titulo_normalizado in VALORES_SIN_LICENCIA:
            return no_declarada
        return Licencia(
            identificador=titulo_normalizado,
            titulo=(titulo or "").strip(),
            url=(url or "").strip(),
            declarada=True,
            identificador_origen=bruto,
        )

    return Licencia(
        identificador=clave,
        titulo=(titulo or bruto).strip(),
        url=(url or "").strip(),
        declarada=True,
        identificador_origen=bruto,
    )


# --------------------------------------------------------------------------------------
# Fechas
# --------------------------------------------------------------------------------------

_FORMATOS_FECHA = (
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
)


def normalizar_fecha(valor) -> str:
    """Devuelve la fecha en ISO-8601 `YYYY-MM-DDTHH:MM:SS`, o "" si no se puede leer.

    Los portales mezclan formatos: Madrid manda `2026-07-24T00:00:00`, Reus manda
    microsegundos, Barcelona a veces manda solo la fecha. Guardar todo con el mismo
    formato es lo que permite ordenar por frescura sin sorpresas.
    """
    if valor in (None, ""):
        return ""
    texto = str(valor).strip()
    if texto.endswith("Z"):
        texto = texto[:-1]
    texto = re.sub(r"([+-]\d{2}:?\d{2})$", "", texto)
    for formato in _FORMATOS_FECHA:
        try:
            return datetime.strptime(texto, formato).replace(microsecond=0).isoformat()
        except ValueError:
            continue
    try:  # último recurso: el parser de la stdlib
        return datetime.fromisoformat(texto).replace(microsecond=0, tzinfo=None).isoformat()
    except ValueError:
        return ""


def entero_o_none(valor) -> int | None:
    """`resource.size` llega como int, como str, como "" o como None según el portal."""
    if valor in (None, ""):
        return None
    try:
        numero = int(float(str(valor).strip()))
    except (TypeError, ValueError):
        return None
    return numero if numero >= 0 else None


# --------------------------------------------------------------------------------------
# Entidades
# --------------------------------------------------------------------------------------


@dataclass
class Publicador:
    """Organismo que publica el dataset (`dct:publisher`)."""

    nombre: str
    titulo: str = ""
    descripcion: str = ""
    url: str = ""


@dataclass
class Tema:
    """Categoría temática del portal (`dcat:theme`); en CKAN, un `group`."""

    nombre: str
    titulo: str = ""


@dataclass
class Distribucion:
    """Recurso descargable de un dataset (`dcat:Distribution`)."""

    identificador_origen: str
    nombre: str = ""
    descripcion: str = ""
    formato: str = ""
    mimetype: str = ""
    url_acceso: str = ""
    url_descarga: str = ""
    tamano_bytes: int | None = None
    fecha_creacion_origen: str = ""
    fecha_modificacion_origen: str = ""
    estado: str = ""
    posicion: int = 0


@dataclass
class DatasetNormalizado:
    """Un dataset con toda la procedencia que exige el TODO 3.2.

    `url_origen`, `fecha_modificacion_origen` y `fecha_sincronizacion` son obligatorios:
    sin ellos el dataset no debería llegar a ninguna respuesta de herramienta.
    """

    portal_id: str
    identificador_origen: str
    nombre: str
    titulo: str
    descripcion: str = ""
    url_origen: str = ""
    url_recurso_api: str = ""
    fecha_creacion_origen: str = ""
    fecha_modificacion_origen: str = ""
    fecha_modificacion_metadatos: str = ""
    fecha_sincronizacion: str = ""
    publicador: Publicador | None = None
    licencia: Licencia = field(
        default_factory=lambda: normalizar_licencia(None)
    )
    temas: list[Tema] = field(default_factory=list)
    palabras_clave: list[str] = field(default_factory=list)
    distribuciones: list[Distribucion] = field(default_factory=list)
    frecuencia_actualizacion: str = ""
    idioma: str = ""
    crudo: dict | None = None

    def texto_indexable(self) -> dict[str, str]:
        """Campos que alimentan la tabla FTS5."""
        return {
            "titulo": self.titulo or "",
            "descripcion": self.descripcion or "",
            "palabras_clave": " ".join(self.palabras_clave),
            "temas": " ".join(t.titulo or t.nombre for t in self.temas),
            "publicador": (self.publicador.titulo or self.publicador.nombre)
            if self.publicador
            else "",
        }
