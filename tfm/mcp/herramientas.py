"""Las herramientas del §4 del plan, como funciones Python sobre el índice local.

Separadas a propósito del transporte MCP (`servidor.py`): así se prueban sin hablar
JSON-RPC, y el día que se cambie de transporte —SDK oficial, HTTP, o el cliente en el
navegador de la fase 6— estas funciones no se tocan.

Contrato de procedencia (TODO 3.2), válido para las cuatro herramientas: **toda** ficha de
dataset que sale de aquí lleva `url_origen`, `fecha_modificacion_origen`,
`fecha_sincronizacion` y `licencia`. Cuando el portal no declara licencia, sale
`licencia_declarada: false` y una `advertencia` en texto para que el modelo no pueda
resumirla sin verla.

`consultar_sparql` no está: el índice es SQLite, no un triplestore. La decisión, con su
argumento, está en `docs/03-prior-art.md` §5.5 (TODO 3.5).
"""

from __future__ import annotations

from ..almacen import Almacen
from ..configuracion import CORPUS

AVISO_SIN_LICENCIA = (
    "El portal de origen NO declara licencia para este dataset. No se asume ninguna: "
    "antes de reutilizarlo hay que consultar las condiciones con el ayuntamiento."
)

#: El índice es una copia. Recordarlo en cada respuesta es lo que exige el art. 8 del
#: RD 1495/2011 (no desnaturalizar la información, indicar la fecha de actualización).
AVISO_COPIA = (
    "Datos procedentes de una copia local de los metadatos, no del portal en vivo. "
    "Comprueba `fecha_sincronizacion` y sigue `url_origen` para la versión autoritativa."
)


def _ficha(fila) -> dict:
    """Ficha resumida de un dataset, con la procedencia siempre incluida."""
    declarada = bool(fila["licencia_declarada"])
    ficha = {
        "id": f"{fila['portal_id']}:{fila['identificador_origen']}",
        "titulo": fila["titulo"],
        "ciudad": fila["municipio"],
        "descripcion": (fila["descripcion"] or "")[:500],
        "num_distribuciones": fila["num_distribuciones"],
        "licencia": fila["licencia"] if declarada else None,
        "licencia_declarada": declarada,
        "url_origen": fila["url_origen"],
        "fecha_modificacion_origen": fila["fecha_modificacion_origen"] or None,
        "fecha_sincronizacion": fila["fecha_sincronizacion"],
    }
    if not declarada:
        ficha["advertencia"] = AVISO_SIN_LICENCIA
    return ficha


def _buscar_fila(almacen: Almacen, identificador: str):
    """Localiza un dataset por `ciudad:id`. Devuelve `(fila, error)`; uno de los dos es `None`.

    No lanza excepciones a propósito: estas funciones se usan también sin el servidor MCP
    (el cliente en el navegador de la fase 6), y un `dict` de error es más fácil de
    encadenar que un `try`. Además, un mensaje de error que el LLM puede leer y corregir
    vale más que una traza.
    """
    if ":" not in identificador:
        return None, {
            "error": (
                f"identificador '{identificador}' mal formado: se espera 'ciudad:id', por "
                f"ejemplo 'madrid:300402-0-calidad-aire-episodios-ozono'."
            ),
            "ciudades_disponibles": sorted(CORPUS),
            "sugerencia": "Usa buscar_datasets primero y coge el campo `id` del resultado.",
        }
    portal, clave = (parte.strip() for parte in identificador.split(":", 1))
    portal = portal.lower()
    if portal not in CORPUS:
        return None, {
            "error": f"la ciudad '{portal}' no está en el índice",
            "ciudades_disponibles": sorted(CORPUS),
        }
    fila = almacen.conexion.execute(
        """SELECT d.*, p.municipio, l.identificador AS licencia, l.declarada AS licencia_declarada
           FROM dataset d JOIN portal p ON p.id = d.portal_id
           JOIN licencia l ON l.id = d.licencia_id
           WHERE d.portal_id = ? AND (d.identificador_origen = ? OR d.nombre = ?)""",
        (portal, clave, clave),
    ).fetchone()
    if fila is None:
        return None, {
            "error": f"no existe el dataset '{identificador}' en el índice",
            "sin_resultados": "No inventes un dataset: di que no está en el índice.",
        }
    return fila, None


# --------------------------------------------------------------------------------------
# Las cuatro herramientas
# --------------------------------------------------------------------------------------


def buscar_datasets(
    almacen: Almacen,
    consulta: str,
    ciudad: str | None = None,
    tema: str | None = None,
    anio: int | None = None,
    limite: int = 10,
) -> dict:
    """Busca datasets por texto libre en español, con filtros opcionales."""
    if ciudad and ciudad.strip().lower() not in CORPUS:
        return {
            "error": f"ciudad '{ciudad}' no está en el índice",
            "ciudades_disponibles": sorted(CORPUS),
        }
    filas = almacen.buscar(
        consulta=consulta,
        portal_id=ciudad.strip().lower() if ciudad else None,
        tema=tema,
        anio=anio,
        limite=max(1, min(limite, 50)),
    )
    resultado = {
        "consulta": consulta,
        "filtros": {"ciudad": ciudad, "tema": tema, "anio": anio},
        "n_resultados": len(filas),
        "resultados": [_ficha(f) for f in filas],
        "aviso": AVISO_COPIA,
    }
    if not filas:
        resultado["sin_resultados"] = (
            "El índice no contiene ningún dataset que encaje. NO inventes uno: dilo "
            "explícitamente y, si procede, sugiere reformular o probar otra ciudad."
        )
    return resultado


def detalle_dataset(almacen: Almacen, id: str) -> dict:
    """Devuelve la ficha completa de un dataset, con temas y palabras clave."""
    fila, error = _buscar_fila(almacen, id)
    if error:
        return error
    ficha = _ficha(fila)
    ficha["descripcion"] = fila["descripcion"] or ""
    ficha.update(
        {
            "nombre": fila["nombre"],
            "url_api_origen": fila["url_recurso_api"],
            "fecha_creacion_origen": fila["fecha_creacion_origen"] or None,
            "frecuencia_actualizacion": fila["frecuencia_actualizacion"] or None,
            "temas": [
                f["titulo"] or f["nombre"]
                for f in almacen.conexion.execute(
                    "SELECT t.nombre, t.titulo FROM tema t JOIN dataset_tema dt "
                    "ON dt.tema_id = t.id WHERE dt.dataset_id = ?",
                    (fila["id"],),
                )
            ],
            "palabras_clave": [
                f["texto"]
                for f in almacen.conexion.execute(
                    "SELECT k.texto FROM keyword k JOIN dataset_keyword dk "
                    "ON dk.keyword_id = k.id WHERE dk.dataset_id = ?",
                    (fila["id"],),
                )
            ],
            "aviso": AVISO_COPIA,
        }
    )
    return ficha


def listar_distribuciones(almacen: Almacen, id: str) -> dict:
    """Formatos, URLs y tamaños de las distribuciones de un dataset."""
    fila, error = _buscar_fila(almacen, id)
    if error:
        return {**error, "sin_resultados": "No inventes distribuciones ni URLs de descarga."}
    distribuciones = [
        {
            "nombre": d["nombre"] or None,
            "formato": d["formato"] or None,
            "url": d["url_descarga"] or d["url_acceso"],
            "tamano_bytes": d["tamano_bytes"],
            "tamano_declarado": d["tamano_bytes"] is not None,
            "fecha_modificacion_origen": d["fecha_modificacion_origen"] or None,
        }
        for d in almacen.conexion.execute(
            "SELECT * FROM distribucion WHERE dataset_id = ? ORDER BY posicion", (fila["id"],)
        )
    ]
    return {
        "id": f"{fila['portal_id']}:{fila['identificador_origen']}",
        "titulo": fila["titulo"],
        "ciudad": fila["municipio"],
        "licencia": fila["licencia"] if fila["licencia_declarada"] else None,
        "licencia_declarada": bool(fila["licencia_declarada"]),
        "n_distribuciones": len(distribuciones),
        "distribuciones": distribuciones,
        "url_origen": fila["url_origen"],
        "fecha_sincronizacion": fila["fecha_sincronizacion"],
        "aviso": (
            "Las URLs no se han comprobado en esta llamada. Madrid responde 403 a la descarga "
            "programática y Barcelona limita por concurrencia: un enlace puede fallar sin que "
            "el dataset haya desaparecido."
        ),
    }


def comparar_ciudades(
    almacen: Almacen, tema: str, ciudades: list[str] | None = None, limite_por_ciudad: int = 3
) -> dict:
    """Compara qué publica cada ciudad sobre un mismo tema.

    Devuelve `sin_datos` explícito para las ciudades sin resultados: la ausencia es la
    respuesta correcta a la mitad de las preguntas del banco, y hay que poder darla.
    """
    objetivo = [c.strip().lower() for c in (ciudades or sorted(CORPUS))]
    desconocidas = [c for c in objetivo if c not in CORPUS]
    if desconocidas:
        return {
            "error": f"ciudades no indexadas: {', '.join(desconocidas)}",
            "ciudades_disponibles": sorted(CORPUS),
        }
    por_ciudad, sin_datos = {}, []
    for ciudad in objetivo:
        filas = almacen.buscar(consulta=tema, portal_id=ciudad, limite=limite_por_ciudad)
        if filas:
            por_ciudad[ciudad] = {
                "municipio": filas[0]["municipio"],
                "n_encontrados": len(filas),
                "datasets": [_ficha(f) for f in filas],
            }
        else:
            sin_datos.append(ciudad)
    return {
        "tema": tema,
        "ciudades_consultadas": objetivo,
        "con_datos": por_ciudad,
        "sin_datos": sin_datos,
        "nota_sin_datos": (
            f"{len(sin_datos)} de {len(objetivo)} ciudades no publican nada sobre '{tema}' "
            "en el índice. Dilo en la respuesta: la ausencia es un resultado, no un hueco "
            "que rellenar."
        )
        if sin_datos
        else None,
        "aviso": AVISO_COPIA,
    }


#: Catálogo declarativo: nombre -> (función, descripción, esquema JSON de argumentos).
#: `servidor.py` lo traduce a `tools/list` sin saber nada de cada herramienta.
CATALOGO = {
    "buscar_datasets": (
        buscar_datasets,
        "Busca conjuntos de datos abiertos municipales por texto libre en español. "
        "Filtros opcionales por ciudad, tema y año de última modificación.",
        {
            "type": "object",
            "properties": {
                "consulta": {"type": "string", "description": "Qué buscar, en español."},
                "ciudad": {"type": "string", "enum": sorted(CORPUS),
                           "description": "Limita a una ciudad."},
                "tema": {"type": "string", "description": "Categoría temática del portal."},
                "anio": {"type": "integer", "description": "Año de última modificación."},
                "limite": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
            },
            "required": ["consulta"],
        },
    ),
    "detalle_dataset": (
        detalle_dataset,
        "Ficha completa de un dataset: descripción, temas, palabras clave, licencia y "
        "procedencia. El identificador tiene la forma 'ciudad:id'.",
        {
            "type": "object",
            "properties": {
                "id": {"type": "string",
                       "description": "Identificador 'ciudad:id', p. ej. 'madrid:300402-0-calidad-aire-episodios-ozono'."}
            },
            "required": ["id"],
        },
    ),
    "listar_distribuciones": (
        listar_distribuciones,
        "Formatos, URLs de descarga y tamaños de las distribuciones de un dataset.",
        {
            "type": "object",
            "properties": {"id": {"type": "string", "description": "Identificador 'ciudad:id'."}},
            "required": ["id"],
        },
    ),
    "comparar_ciudades": (
        comparar_ciudades,
        "Compara qué publica cada ciudad sobre un mismo tema. Indica explícitamente las "
        "ciudades que no publican nada.",
        {
            "type": "object",
            "properties": {
                "tema": {"type": "string", "description": "Tema a comparar, en español."},
                "ciudades": {"type": "array", "items": {"type": "string", "enum": sorted(CORPUS)},
                             "description": "Por omisión, todas las del índice."},
                "limite_por_ciudad": {"type": "integer", "default": 3, "minimum": 1, "maximum": 10},
            },
            "required": ["tema"],
        },
    ),
}
