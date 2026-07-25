"""Esquema del índice local (SQLite + FTS5) y construcción de consultas de búsqueda.

Sin ORM y sin dependencias: `sqlite3` de la biblioteca estándar. El esquema cubre el
mínimo exigido por el TODO 3.1 —dataset, distribución, publicador, tema, keyword,
licencia, `fecha_modificacion_origen`, `fecha_sincronizacion`, `url_origen`— y adelanta el
TODO 3.2 con `licencia.declarada`.

Búsqueda en español: FTS5 con `tokenize='unicode61 remove_diacritics 2'`, que normaliza
acentos en el índice **y** en la consulta, de modo que "arboles" encuentra "árboles" y
"Calidad del Aire" se encuentra escribiendo "calidad del aire".
"""

from __future__ import annotations

import re
import unicodedata

VERSION_ESQUEMA = 1

#: `remove_diacritics 2` (frente a `1`) trata correctamente la ñ y las combinaciones
#: latinas extendidas: sin él, "año" y "ano" se confundirían de forma distinta según la
#: versión de SQLite. Requiere SQLite >= 3.27.
TOKENIZADOR_FTS = "unicode61 remove_diacritics 2"

DDL = f"""
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS metadatos_indice (
    clave  TEXT PRIMARY KEY,
    valor  TEXT
);

-- Portal de origen. Un portal = un municipio en el corpus actual, pero se modela aparte
-- porque los agregadores (AOC seu-e, eprinsa) sirven muchos municipios desde un endpoint.
CREATE TABLE IF NOT EXISTS portal (
    id        TEXT PRIMARY KEY,
    municipio TEXT NOT NULL,
    familia   TEXT NOT NULL,
    url_api   TEXT NOT NULL,
    url_base  TEXT NOT NULL,
    notas     TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS publicador (
    id          INTEGER PRIMARY KEY,
    portal_id   TEXT NOT NULL REFERENCES portal(id) ON DELETE CASCADE,
    nombre      TEXT NOT NULL,
    titulo      TEXT DEFAULT '',
    descripcion TEXT DEFAULT '',
    url         TEXT DEFAULT '',
    UNIQUE (portal_id, nombre)
);

-- `declarada = 0` marca los datasets sin licencia declarada en origen (TODO 3.2).
-- Nunca se sustituye por CC-BY: la ausencia es un dato, no un hueco que rellenar.
CREATE TABLE IF NOT EXISTS licencia (
    id                   INTEGER PRIMARY KEY,
    identificador        TEXT NOT NULL UNIQUE,
    titulo               TEXT DEFAULT '',
    url                  TEXT DEFAULT '',
    declarada            INTEGER NOT NULL DEFAULT 1 CHECK (declarada IN (0, 1))
);

CREATE TABLE IF NOT EXISTS tema (
    id           INTEGER PRIMARY KEY,
    portal_id    TEXT NOT NULL REFERENCES portal(id) ON DELETE CASCADE,
    nombre       TEXT NOT NULL,
    titulo       TEXT DEFAULT '',
    normalizado  TEXT DEFAULT '',
    UNIQUE (portal_id, nombre)
);

-- Las keywords se comparten entre portales a través de `normalizado` (minúsculas y sin
-- acentos): es lo que permitirá medir el solapamiento de vocabulario del TODO 2.4.
CREATE TABLE IF NOT EXISTS keyword (
    id          INTEGER PRIMARY KEY,
    texto       TEXT NOT NULL,
    normalizado TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dataset (
    id                            INTEGER PRIMARY KEY,
    portal_id                     TEXT NOT NULL REFERENCES portal(id) ON DELETE CASCADE,
    identificador_origen          TEXT NOT NULL,
    nombre                        TEXT NOT NULL,
    titulo                        TEXT NOT NULL,
    descripcion                   TEXT DEFAULT '',
    publicador_id                 INTEGER REFERENCES publicador(id),
    licencia_id                   INTEGER NOT NULL REFERENCES licencia(id),
    url_origen                    TEXT NOT NULL,
    url_recurso_api               TEXT DEFAULT '',
    fecha_creacion_origen         TEXT DEFAULT '',
    fecha_modificacion_origen     TEXT DEFAULT '',
    fecha_modificacion_metadatos  TEXT DEFAULT '',
    fecha_sincronizacion          TEXT NOT NULL,
    frecuencia_actualizacion      TEXT DEFAULT '',
    idioma                        TEXT DEFAULT '',
    num_distribuciones            INTEGER NOT NULL DEFAULT 0,
    UNIQUE (portal_id, identificador_origen)
);

CREATE TABLE IF NOT EXISTS distribucion (
    id                        INTEGER PRIMARY KEY,
    dataset_id                INTEGER NOT NULL REFERENCES dataset(id) ON DELETE CASCADE,
    identificador_origen      TEXT DEFAULT '',
    nombre                    TEXT DEFAULT '',
    descripcion               TEXT DEFAULT '',
    formato                   TEXT DEFAULT '',
    mimetype                  TEXT DEFAULT '',
    url_acceso                TEXT DEFAULT '',
    url_descarga              TEXT DEFAULT '',
    tamano_bytes              INTEGER,
    fecha_creacion_origen     TEXT DEFAULT '',
    fecha_modificacion_origen TEXT DEFAULT '',
    estado                    TEXT DEFAULT '',
    posicion                  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS dataset_tema (
    dataset_id INTEGER NOT NULL REFERENCES dataset(id) ON DELETE CASCADE,
    tema_id    INTEGER NOT NULL REFERENCES tema(id) ON DELETE CASCADE,
    PRIMARY KEY (dataset_id, tema_id)
);

CREATE TABLE IF NOT EXISTS dataset_keyword (
    dataset_id INTEGER NOT NULL REFERENCES dataset(id) ON DELETE CASCADE,
    keyword_id INTEGER NOT NULL REFERENCES keyword(id) ON DELETE CASCADE,
    PRIMARY KEY (dataset_id, keyword_id)
);

-- JSON tal y como lo devolvió el portal. Se guarda aparte para poder soltarlo
-- (`build --sin-crudo`) sin tocar el resto del índice. Sirve a las fases 2.2 y 2.4.
CREATE TABLE IF NOT EXISTS dataset_crudo (
    dataset_id INTEGER PRIMARY KEY REFERENCES dataset(id) ON DELETE CASCADE,
    json       TEXT NOT NULL
);

-- Bitácora de cosechas: una fila por portal y ejecución (TODO 3.3).
CREATE TABLE IF NOT EXISTS cosecha (
    id                INTEGER PRIMARY KEY,
    portal_id         TEXT NOT NULL,
    inicio            TEXT,
    fin               TEXT,
    estado            TEXT,
    n_datasets        INTEGER DEFAULT 0,
    n_distribuciones  INTEGER DEFAULT 0,
    n_peticiones      INTEGER DEFAULT 0,
    n_reintentos      INTEGER DEFAULT 0,
    segundos          REAL DEFAULT 0,
    crawl_delay       REAL,
    error             TEXT DEFAULT ''
);

-- Log de errores consultable con SQL, por portal (TODO 3.3).
CREATE TABLE IF NOT EXISTS error_cosecha (
    id          INTEGER PRIMARY KEY,
    cosecha_id  INTEGER REFERENCES cosecha(id) ON DELETE CASCADE,
    portal_id   TEXT NOT NULL,
    momento     TEXT NOT NULL,
    tipo        TEXT NOT NULL,
    mensaje     TEXT NOT NULL,
    url         TEXT DEFAULT '',
    codigo_http INTEGER,
    intento     INTEGER DEFAULT 1,
    definitivo  INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_dataset_portal        ON dataset(portal_id);
CREATE INDEX IF NOT EXISTS idx_dataset_licencia      ON dataset(licencia_id);
CREATE INDEX IF NOT EXISTS idx_dataset_modificacion  ON dataset(fecha_modificacion_origen);
CREATE INDEX IF NOT EXISTS idx_distribucion_dataset  ON distribucion(dataset_id);
CREATE INDEX IF NOT EXISTS idx_distribucion_formato  ON distribucion(formato);
CREATE INDEX IF NOT EXISTS idx_error_portal          ON error_cosecha(portal_id);
CREATE INDEX IF NOT EXISTS idx_keyword_normalizado   ON keyword(normalizado);

-- Búsqueda de texto completo en español, insensible a acentos y a mayúsculas.
CREATE VIRTUAL TABLE IF NOT EXISTS dataset_fts USING fts5(
    titulo,
    descripcion,
    palabras_clave,
    temas,
    publicador,
    dataset_id UNINDEXED,
    tokenize='{TOKENIZADOR_FTS}'
);
"""


# --------------------------------------------------------------------------------------
# Construcción de la consulta FTS
# --------------------------------------------------------------------------------------

#: Palabras vacías del español (y las catalanas más frecuentes, por Barcelona y Reus).
#: Se descartan de la consulta: si el usuario escribe "calidad del aire" y el título es
#: "Calidad de aire", exigir "del" haría fallar la búsqueda.
PALABRAS_VACIAS = frozenset(
    """
    a al ante bajo con contra de del desde durante e el en entre hacia hasta la las lo los
    mas mediante ni no o para pero por que se segun sin sobre su sus tras un una uno unos
    unas y ya
    els les dels amb per als la el les i o de d l
    """.split()
)

_SEPARADORES = re.compile(r"[^0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñÀÈÌÒÙàèìòùÇç·]+")


def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def singularizar(palabra: str) -> str:
    """Reducción de plurales muy conservadora para el español.

    No es un lematizador: recorta `-es` y `-s` solo cuando queda una raíz razonable.
    Combinado con la búsqueda por prefijo (`raiz*`) hace que "arboles" encuentre "árbol" y
    "árboles", y que "presupuestos" encuentre "presupuesto". Se prefiere quedarse corto a
    inventar raíces: un recorte agresivo produciría falsos positivos difíciles de explicar
    en la evaluación de la fase 5.
    """
    if len(palabra) >= 6 and palabra.endswith("es"):
        return palabra[:-2]
    if len(palabra) >= 5 and palabra.endswith("s") and not palabra.endswith("ss"):
        return palabra[:-1]
    return palabra


def construir_consulta_fts(texto: str, prefijo: bool = True) -> str:
    """Traduce texto libre en español a una expresión MATCH de FTS5.

    - Descarta palabras vacías (pero si *todo* eran palabras vacías, las conserva).
    - Singulariza y busca por prefijo, para cubrir plurales y derivados.
    - Escapa cada término entre comillas: así un `-`, un `:` o un `*` del usuario no se
      interpretan como sintaxis de FTS5 ni provocan un error de consulta.
    - Los acentos no se tocan: el tokenizador (`remove_diacritics 2`) ya los normaliza a
      ambos lados, en el índice y en la consulta.
    """
    if not texto or not texto.strip():
        return ""
    palabras = [p for p in _SEPARADORES.split(texto) if p]
    utiles = [p for p in palabras if _sin_acentos(p).lower() not in PALABRAS_VACIAS]
    if not utiles:
        utiles = palabras

    terminos = []
    for palabra in utiles:
        raiz = singularizar(palabra) if prefijo else palabra
        raiz = raiz.replace('"', '""')
        terminos.append(f'"{raiz}"*' if prefijo else f'"{raiz}"')
    return " ".join(terminos)
