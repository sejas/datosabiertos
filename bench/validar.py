#!/usr/bin/env python3
"""Validador del banco de evaluación BDAM-es (TODO 4.1).

Sin dependencias externas: solo la biblioteca estándar de Python 3.11+. Se publica junto
al banco en Zenodo, así que tiene que funcionar en una carpeta suelta, sin el resto del
repositorio y sin `pip install` de nada.

Hace tres cosas, en este orden:

1. **Validación estructural** contra `esquema.json`, con un intérprete del subconjunto de
   JSON Schema que ese esquema usa (§"Subconjunto soportado" más abajo). No se usa
   `jsonschema` porque es una dependencia externa, y no se usa un validador escrito a mano
   sin esquema porque entonces el esquema formal sería decorativo.
2. **Reglas semánticas** que un JSON Schema no puede expresar de forma legible: coherencia
   entre `ciudades` y los portales citados, argumentos válidos por herramienta, ids
   canónicos que apunten de verdad a un dataset de referencia…
3. **Verificación contra el índice local** (opcional, `--indice`): que los datasets de
   referencia existan de verdad y que las preguntas marcadas `sin_respuesta` devuelvan
   cero resultados. Es lo que impide que "verificado a mano" sea un acto de fe.

Uso:

    python3 bench/validar.py bench/preguntas.json
    python3 bench/validar.py bench/preguntas.json --indice datos/indice.sqlite
    python3 bench/validar.py bench/preguntas.json --composicion
    python3 bench/validar.py bench/preguntas.json --esquema otro/esquema.json --json

Código de salida: 0 si no hay errores, 1 si los hay. Los avisos no hacen fallar.

Subconjunto de JSON Schema soportado
------------------------------------
`type`, `properties`, `required`, `additionalProperties` (booleano), `items`, `minItems`,
`maxItems`, `uniqueItems`, `enum`, `const`, `pattern`, `minLength`, `maxLength`,
`minimum`, `maximum`, `allOf`, `if`/`then`/`else`, `$ref` local a `#/$defs/...` y `$defs`.
Cualquier otra palabra clave se ignora **con un aviso**, para que nadie escriba una
restricción en el esquema creyendo que se comprueba y no se compruebe.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

# --------------------------------------------------------------------------------------
# Firmas de las herramientas MCP (§4 de PLAN.md)
# --------------------------------------------------------------------------------------
#
# `anio` en vez de `año`: PLAN.md escribe `año`, pero el argumento viaja en JSON y en la
# CLI (`python -m datosabiertos.index buscar --anio`), donde una eñe es una fuente inagotable de
# problemas de codificación. La divergencia está documentada en esquema.md §3.
#
# `comparar_ciudades` acepta `ciudades` además de `tema`, que es lo único que pide el plan:
# sin ese argumento no se puede pedir "compara solo Madrid y Barcelona". Es una propuesta
# del banco al diseño de la herramienta (TODO 3.4), no una desviación accidental.
FIRMAS: dict[str, dict[str, str]] = {
    "buscar_datasets": {
        "consulta": "str",
        "ciudad": "portal",
        "tema": "str",
        "anio": "int",
        "limite": "int",
    },
    "detalle_dataset": {"id": "id_canonico"},
    "listar_distribuciones": {"id": "id_canonico"},
    "comparar_ciudades": {"tema": "str", "ciudades": "lista_portales"},
}

#: Argumentos sin los que la llamada no tiene sentido.
ARGUMENTOS_MINIMOS: dict[str, tuple[str, ...]] = {
    "buscar_datasets": (),  # una búsqueda solo por `tema` o solo por `ciudad` es legítima
    "detalle_dataset": ("id",),
    "listar_distribuciones": ("id",),
    "comparar_ciudades": ("tema",),
}


# --------------------------------------------------------------------------------------
# Recolección de problemas
# --------------------------------------------------------------------------------------


class Diagnostico:
    """Acumula errores y avisos con la pregunta y el campo exactos."""

    def __init__(self) -> None:
        self.errores: list[dict] = []
        self.avisos: list[dict] = []

    def error(self, ruta: str, mensaje: str, pregunta: str | None = None) -> None:
        self.errores.append({"pregunta": pregunta, "campo": ruta, "mensaje": mensaje})

    def aviso(self, ruta: str, mensaje: str, pregunta: str | None = None) -> None:
        self.avisos.append({"pregunta": pregunta, "campo": ruta, "mensaje": mensaje})

    @property
    def ok(self) -> bool:
        return not self.errores

    def imprimir(self, flujo=sys.stdout) -> None:
        for item in self.errores:
            etiqueta = f"[{item['pregunta']}] " if item["pregunta"] else ""
            print(f"ERROR  {etiqueta}{item['campo']}: {item['mensaje']}", file=flujo)
        for item in self.avisos:
            etiqueta = f"[{item['pregunta']}] " if item["pregunta"] else ""
            print(f"AVISO  {etiqueta}{item['campo']}: {item['mensaje']}", file=flujo)


# --------------------------------------------------------------------------------------
# 1. Validación estructural: intérprete del subconjunto de JSON Schema
# --------------------------------------------------------------------------------------

PALABRAS_SOPORTADAS = frozenset(
    """
    $schema $id $ref $defs title description type properties required additionalProperties
    items minItems maxItems uniqueItems enum const pattern minLength maxLength minimum
    maximum allOf if then else
    """.split()
)

TIPOS = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _es_tipo(valor, nombre: str) -> bool:
    if nombre == "integer":
        return isinstance(valor, int) and not isinstance(valor, bool)
    if nombre == "number":
        return isinstance(valor, (int, float)) and not isinstance(valor, bool)
    if nombre == "boolean":
        return isinstance(valor, bool)
    esperado = TIPOS.get(nombre)
    if esperado is None:
        return True
    if esperado is str and isinstance(valor, bool):
        return False
    return isinstance(valor, esperado)


class ValidadorEsquema:
    """Valida un documento contra el subconjunto de JSON Schema descrito en el módulo."""

    def __init__(self, esquema: dict, diagnostico: Diagnostico) -> None:
        self.raiz = esquema
        self.diag = diagnostico
        self._palabras_avisadas: set[str] = set()

    # -- utilidades ---------------------------------------------------------------------
    def _resolver(self, esquema: dict) -> dict:
        referencia = esquema.get("$ref")
        if not referencia:
            return esquema
        if not referencia.startswith("#/"):
            raise ValueError(f"$ref no local no soportado: {referencia}")
        nodo = self.raiz
        for parte in referencia[2:].split("/"):
            nodo = nodo[parte]
        combinado = {k: v for k, v in esquema.items() if k != "$ref"}
        return {**nodo, **combinado}

    def _avisar_palabras(self, esquema: dict, ruta: str) -> None:
        for palabra in esquema:
            if palabra in PALABRAS_SOPORTADAS or palabra in self._palabras_avisadas:
                continue
            self._palabras_avisadas.add(palabra)
            self.diag.aviso(
                ruta or "(raíz)",
                f"palabra clave de JSON Schema no soportada por este validador: '{palabra}'. "
                "No se comprueba: o la implementas en validar.py o la quitas del esquema.",
            )

    # -- validación ---------------------------------------------------------------------
    def validar(self, dato, esquema: dict, ruta: str = "", pregunta: str | None = None) -> bool:
        esquema = self._resolver(esquema)
        self._avisar_palabras(esquema, ruta)
        limpio = True
        etiqueta = ruta or "(raíz)"

        tipos = esquema.get("type")
        if tipos is not None:
            candidatos = tipos if isinstance(tipos, list) else [tipos]
            if not any(_es_tipo(dato, t) for t in candidatos):
                self.diag.error(
                    etiqueta,
                    f"se esperaba tipo {'|'.join(candidatos)} y llegó "
                    f"{type(dato).__name__} ({json.dumps(dato, ensure_ascii=False)[:60]})",
                    pregunta,
                )
                return False  # sin el tipo correcto, el resto de comprobaciones no aplica

        if "const" in esquema and dato != esquema["const"]:
            self.diag.error(
                etiqueta, f"debe valer exactamente {esquema['const']!r}, no {dato!r}", pregunta
            )
            limpio = False

        if "enum" in esquema and dato not in esquema["enum"]:
            self.diag.error(
                etiqueta,
                f"valor {dato!r} fuera de los permitidos: {esquema['enum']}",
                pregunta,
            )
            limpio = False

        if isinstance(dato, str):
            limpio &= self._validar_cadena(dato, esquema, etiqueta, pregunta)
        if isinstance(dato, (int, float)) and not isinstance(dato, bool):
            limpio &= self._validar_numero(dato, esquema, etiqueta, pregunta)
        if isinstance(dato, list):
            limpio &= self._validar_lista(dato, esquema, ruta, etiqueta, pregunta)
        if isinstance(dato, dict):
            limpio &= self._validar_objeto(dato, esquema, ruta, etiqueta, pregunta)

        for i, sub in enumerate(esquema.get("allOf", [])):
            limpio &= self.validar(dato, sub, ruta, pregunta)
            _ = i

        if "if" in esquema:
            silencioso = Diagnostico()
            cumple = ValidadorEsquema(self.raiz, silencioso).validar(dato, esquema["if"], ruta)
            rama = esquema.get("then") if cumple else esquema.get("else")
            if rama is not None:
                limpio &= self.validar(dato, rama, ruta, pregunta)

        return limpio

    def _validar_cadena(self, dato: str, esquema: dict, etiqueta: str, pregunta) -> bool:
        limpio = True
        if "minLength" in esquema and len(dato) < esquema["minLength"]:
            self.diag.error(
                etiqueta,
                f"cadena demasiado corta ({len(dato)} caracteres, mínimo "
                f"{esquema['minLength']}): {dato!r}",
                pregunta,
            )
            limpio = False
        if "maxLength" in esquema and len(dato) > esquema["maxLength"]:
            self.diag.error(
                etiqueta,
                f"cadena demasiado larga ({len(dato)} caracteres, máximo {esquema['maxLength']})",
                pregunta,
            )
            limpio = False
        patron = esquema.get("pattern")
        if patron and not re.search(patron, dato):
            self.diag.error(
                etiqueta, f"valor {dato!r} no cumple el patrón /{patron}/", pregunta
            )
            limpio = False
        return limpio

    def _validar_numero(self, dato, esquema: dict, etiqueta: str, pregunta) -> bool:
        limpio = True
        if "minimum" in esquema and dato < esquema["minimum"]:
            self.diag.error(etiqueta, f"{dato} < mínimo {esquema['minimum']}", pregunta)
            limpio = False
        if "maximum" in esquema and dato > esquema["maximum"]:
            self.diag.error(etiqueta, f"{dato} > máximo {esquema['maximum']}", pregunta)
            limpio = False
        return limpio

    def _validar_lista(self, dato: list, esquema: dict, ruta: str, etiqueta: str, pregunta) -> bool:
        limpio = True
        if "minItems" in esquema and len(dato) < esquema["minItems"]:
            self.diag.error(
                etiqueta,
                f"la lista tiene {len(dato)} elementos y el mínimo es {esquema['minItems']}",
                pregunta,
            )
            limpio = False
        if "maxItems" in esquema and len(dato) > esquema["maxItems"]:
            self.diag.error(
                etiqueta,
                f"la lista tiene {len(dato)} elementos y el máximo es {esquema['maxItems']}",
                pregunta,
            )
            limpio = False
        if esquema.get("uniqueItems"):
            vistos, repetidos = [], []
            for elemento in dato:
                clave = json.dumps(elemento, sort_keys=True, ensure_ascii=False)
                (repetidos if clave in vistos else vistos).append(clave)
            if repetidos:
                self.diag.error(
                    etiqueta, f"elementos repetidos: {sorted(set(repetidos))}", pregunta
                )
                limpio = False
        sub = esquema.get("items")
        if sub is not None:
            for i, elemento in enumerate(dato):
                # Si el elemento es una pregunta, sus errores se etiquetan con su id: sin
                # esto, un error dentro de `preguntas[7].traza_esperada[2]` obliga a contar
                # elementos a mano para saber de qué pregunta habla.
                etiqueta_hija = pregunta
                if isinstance(elemento, dict) and isinstance(elemento.get("id"), str):
                    etiqueta_hija = elemento["id"]
                limpio &= self.validar(elemento, sub, f"{ruta}[{i}]", etiqueta_hija)
        return limpio

    def _validar_objeto(self, dato: dict, esquema: dict, ruta: str, etiqueta: str, pregunta) -> bool:
        limpio = True
        propiedades = esquema.get("properties", {})
        for obligatoria in esquema.get("required", []):
            if obligatoria not in dato:
                self.diag.error(etiqueta, f"falta el campo obligatorio '{obligatoria}'", pregunta)
                limpio = False
        if esquema.get("additionalProperties") is False and propiedades:
            for clave in dato:
                if clave not in propiedades:
                    self.diag.error(
                        etiqueta,
                        f"campo no reconocido '{clave}'. Permitidos: "
                        f"{', '.join(sorted(propiedades))}",
                        pregunta,
                    )
                    limpio = False
        for clave, sub in propiedades.items():
            if clave in dato:
                prefijo = f"{ruta}.{clave}" if ruta else clave
                limpio &= self.validar(dato[clave], sub, prefijo, pregunta)
        return limpio


# --------------------------------------------------------------------------------------
# 2. Reglas semánticas
# --------------------------------------------------------------------------------------


def validar_semantica(banco: dict, esquema: dict, diag: Diagnostico) -> None:
    portales_validos = set(esquema["$defs"]["portal"]["enum"])
    prefijo = banco.get("identificador_banco", "")
    portales_indice = set(banco.get("instantanea_indice", {}).get("portales", []))
    vistos: dict[str, int] = {}

    for indice, p in enumerate(banco.get("preguntas", [])):
        if not isinstance(p, dict):
            continue
        pid = p.get("id", f"(sin id, posición {indice})")
        base = f"preguntas[{indice}]"

        # -- identificadores únicos y con el prefijo del banco --------------------------
        if p.get("id"):
            if p["id"] in vistos:
                diag.error(
                    f"{base}.id",
                    f"identificador repetido (ya usado en preguntas[{vistos[p['id']]}])",
                    pid,
                )
            vistos[p["id"]] = indice
            if prefijo and not p["id"].startswith(f"{prefijo}-"):
                diag.error(
                    f"{base}.id",
                    f"debe empezar por el prefijo del banco '{prefijo}-'",
                    pid,
                )

        ciudades = set(p.get("ciudades", []))
        if ciudades - portales_indice and portales_indice:
            diag.error(
                f"{base}.ciudades",
                f"ciudades fuera de la instantánea del índice: "
                f"{sorted(ciudades - portales_indice)}",
                pid,
            )

        # -- los datasets citados pertenecen a las ciudades declaradas ------------------
        for grupo in ("datasets_referencia", "datasets_proximos"):
            for j, ref in enumerate(p.get(grupo, [])):
                if not isinstance(ref, dict):
                    continue
                portal = ref.get("portal")
                if portal and portal not in ciudades:
                    diag.error(
                        f"{base}.{grupo}[{j}].portal",
                        f"'{portal}' no está en `ciudades` ({sorted(ciudades)})",
                        pid,
                    )
                url = ref.get("url_origen", "")
                if portal == "madrid" and url and "datos.madrid.es" not in url:
                    diag.aviso(
                        f"{base}.{grupo}[{j}].url_origen",
                        f"url que no parece del portal declarado ('{portal}'): {url}",
                        pid,
                    )

        principales = [
            r for r in p.get("datasets_referencia", []) if r.get("rol", "principal") == "principal"
        ]
        if not p.get("sin_respuesta") and not principales:
            diag.error(
                f"{base}.datasets_referencia",
                "una pregunta con respuesta necesita al menos un dataset con rol 'principal'",
                pid,
            )

        ids_canonicos = {
            f"{r.get('portal')}:{r.get('identificador')}"
            for grupo in ("datasets_referencia", "datasets_proximos")
            for r in p.get(grupo, [])
            if isinstance(r, dict)
        }

        # -- la traza usa herramientas y argumentos que existen -------------------------
        for j, llamada in enumerate(p.get("traza_esperada", [])):
            if not isinstance(llamada, dict):
                continue
            herramienta = llamada.get("herramienta")
            firma = FIRMAS.get(herramienta)
            ruta = f"{base}.traza_esperada[{j}]"
            if firma is None:
                continue  # el esquema ya ha marcado el enum
            argumentos = llamada.get("argumentos", {})
            if not isinstance(argumentos, dict):
                continue
            for falta in ARGUMENTOS_MINIMOS[herramienta]:
                if falta not in argumentos:
                    diag.error(
                        f"{ruta}.argumentos",
                        f"{herramienta} necesita el argumento '{falta}'",
                        pid,
                    )
            for nombre, valor in argumentos.items():
                if nombre not in firma:
                    diag.error(
                        f"{ruta}.argumentos.{nombre}",
                        f"{herramienta} no acepta el argumento '{nombre}'. "
                        f"Acepta: {', '.join(sorted(firma))}",
                        pid,
                    )
                    continue
                clase = firma[nombre]
                if clase == "str" and not isinstance(valor, str):
                    diag.error(f"{ruta}.argumentos.{nombre}", "debe ser una cadena", pid)
                elif clase == "int" and not isinstance(valor, int):
                    diag.error(f"{ruta}.argumentos.{nombre}", "debe ser un entero", pid)
                elif clase == "portal":
                    if valor not in portales_validos:
                        diag.error(
                            f"{ruta}.argumentos.{nombre}",
                            f"'{valor}' no es un portal del corpus: {sorted(portales_validos)}",
                            pid,
                        )
                    elif valor not in ciudades:
                        diag.error(
                            f"{ruta}.argumentos.{nombre}",
                            f"la traza consulta '{valor}' pero no está en `ciudades`",
                            pid,
                        )
                elif clase == "lista_portales":
                    if not isinstance(valor, list) or not all(
                        v in portales_validos for v in valor
                    ):
                        diag.error(
                            f"{ruta}.argumentos.{nombre}",
                            f"debe ser una lista de portales del corpus, y llegó {valor!r}",
                            pid,
                        )
                elif clase == "id_canonico":
                    if not isinstance(valor, str) or ":" not in valor:
                        diag.error(
                            f"{ruta}.argumentos.{nombre}",
                            f"debe ser un id canónico <portal>:<identificador>, y llegó {valor!r}",
                            pid,
                        )
                    elif valor not in ids_canonicos:
                        diag.error(
                            f"{ruta}.argumentos.{nombre}",
                            f"'{valor}' no corresponde a ningún dataset de referencia "
                            "ni próximo de esta pregunta",
                            pid,
                        )

        # -- coherencia de la marca sin_respuesta ---------------------------------------
        if p.get("sin_respuesta"):
            if "sin-respuesta" not in p.get("etiquetas", []):
                diag.aviso(
                    f"{base}.etiquetas",
                    "una pregunta sin respuesta posible debería llevar la etiqueta "
                    "'sin-respuesta' para poder filtrarla en el análisis",
                    pid,
                )
            for j, comprobacion in enumerate(p.get("comprobaciones_vacias", [])):
                ciudad = comprobacion.get("ciudad") if isinstance(comprobacion, dict) else None
                if ciudad and ciudad not in ciudades:
                    diag.error(
                        f"{base}.comprobaciones_vacias[{j}].ciudad",
                        f"'{ciudad}' no está en `ciudades`",
                        pid,
                    )
            if not any(
                c.strip().upper().startswith("NO:") for c in p.get("criterios_respuesta", [])
            ):
                diag.aviso(
                    f"{base}.criterios_respuesta",
                    "sin al menos un criterio negativo (prefijo 'NO:') no se puede medir "
                    "la alucinación, que es justo para lo que existe esta pregunta",
                    pid,
                )


# --------------------------------------------------------------------------------------
# 3. Verificación contra el índice local (opcional)
# --------------------------------------------------------------------------------------

#: Copia deliberada de `datosabiertos.esquema`: el banco se publica suelto en Zenodo y este fichero
#: tiene que seguir funcionando sin el paquete `datosabiertos` al lado. Si cambia allí, cambia aquí,
#: y el aviso de la comprobación lo delata (los recuentos dejarían de cuadrar).
_VACIAS = frozenset(
    """
    a al ante bajo con contra de del desde durante e el en entre hacia hasta la las lo los
    mas mediante ni no o para pero por que se segun sin sobre su sus tras un una uno unos
    unas y ya els les dels amb per als i d l
    """.split()
)
_SEPARADORES = re.compile(r"[^0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñÀÈÌÒÙàèìòùÇç·]+")


def _sin_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )


def _singularizar(palabra: str) -> str:
    if len(palabra) >= 6 and palabra.endswith("es"):
        return palabra[:-2]
    if len(palabra) >= 5 and palabra.endswith("s") and not palabra.endswith("ss"):
        return palabra[:-1]
    return palabra


def _consulta_fts(texto: str) -> str:
    palabras = [p for p in _SEPARADORES.split(texto) if p]
    utiles = [p for p in palabras if _sin_acentos(p).lower() not in _VACIAS] or palabras
    return " ".join(f'"{_singularizar(p).replace(chr(34), chr(34) * 2)}"*' for p in utiles)


def verificar_contra_indice(banco: dict, ruta_indice: Path, diag: Diagnostico) -> None:
    if not ruta_indice.exists():
        diag.error("--indice", f"no existe el índice {ruta_indice}")
        return
    conexion = sqlite3.connect(f"file:{ruta_indice}?mode=ro", uri=True)
    conexion.row_factory = sqlite3.Row
    try:
        for indice, p in enumerate(banco.get("preguntas", [])):
            pid = p.get("id", f"posición {indice}")
            base = f"preguntas[{indice}]"

            for grupo in ("datasets_referencia", "datasets_proximos"):
                for j, ref in enumerate(p.get(grupo, [])):
                    fila = conexion.execute(
                        "SELECT titulo, url_origen FROM dataset "
                        "WHERE portal_id = ? AND identificador_origen = ?",
                        (ref.get("portal"), ref.get("identificador")),
                    ).fetchone()
                    campo = f"{base}.{grupo}[{j}]"
                    if fila is None:
                        diag.error(
                            f"{campo}.identificador",
                            f"'{ref.get('portal')}:{ref.get('identificador')}' no existe en "
                            f"el índice {ruta_indice.name}",
                            pid,
                        )
                        continue
                    if ref.get("url_origen") and ref["url_origen"] != fila["url_origen"]:
                        diag.error(
                            f"{campo}.url_origen",
                            f"no coincide con el índice. Banco: {ref['url_origen']} · "
                            f"Índice: {fila['url_origen']}",
                            pid,
                        )
                    if ref.get("titulo") and ref["titulo"] != fila["titulo"]:
                        diag.aviso(
                            f"{campo}.titulo",
                            f"el título ha cambiado en origen. Banco: {ref['titulo']!r} · "
                            f"Índice: {fila['titulo']!r}",
                            pid,
                        )

            for j, comprobacion in enumerate(p.get("comprobaciones_vacias", [])):
                expresion = _consulta_fts(comprobacion.get("consulta", ""))
                sql = (
                    "SELECT count(*) FROM dataset d "
                    "JOIN dataset_fts f ON f.dataset_id = d.id WHERE dataset_fts MATCH ?"
                )
                parametros: list = [expresion]
                if comprobacion.get("ciudad"):
                    sql += " AND d.portal_id = ?"
                    parametros.append(comprobacion["ciudad"])
                total = conexion.execute(sql, parametros).fetchone()[0]
                if total:
                    diag.error(
                        f"{base}.comprobaciones_vacias[{j}]",
                        f"la consulta {comprobacion.get('consulta')!r} sobre "
                        f"{comprobacion.get('ciudad', 'todo el corpus')} devuelve {total} "
                        "resultados: la pregunta no está sin respuesta en esta instantánea",
                        pid,
                    )

        instantanea = banco.get("instantanea_indice", {})
        real = conexion.execute("SELECT count(*) FROM dataset").fetchone()[0]
        if instantanea.get("n_datasets") and instantanea["n_datasets"] != real:
            diag.aviso(
                "instantanea_indice.n_datasets",
                f"el banco dice {instantanea['n_datasets']} datasets y el índice tiene {real}: "
                "el banco se verificó contra otra instantánea",
            )
    finally:
        conexion.close()


# --------------------------------------------------------------------------------------
# 4. Composición del banco (criterios del TODO 4.2)
# --------------------------------------------------------------------------------------

MINIMOS_COMPOSICION = {
    "multiciudad": 0.15,   # ≥15 % multiciudad
    "sin_respuesta": 0.10,  # ≥10 % sin respuesta posible
}


def resumen_composicion(banco: dict) -> dict:
    preguntas = banco.get("preguntas", [])
    total = len(preguntas)
    por_dificultad: dict[str, int] = {}
    por_ciudad: dict[str, int] = {}
    por_etiqueta: dict[str, int] = {}
    for p in preguntas:
        por_dificultad[p.get("dificultad", "?")] = por_dificultad.get(p.get("dificultad", "?"), 0) + 1
        for ciudad in p.get("ciudades", []):
            por_ciudad[ciudad] = por_ciudad.get(ciudad, 0) + 1
        for etiqueta in p.get("etiquetas", []):
            por_etiqueta[etiqueta] = por_etiqueta.get(etiqueta, 0) + 1
    return {
        "total": total,
        "por_dificultad": por_dificultad,
        "por_ciudad": por_ciudad,
        "por_etiqueta": por_etiqueta,
        "multiciudad": sum(1 for p in preguntas if p.get("tipo") == "multiciudad"),
        "sin_respuesta": sum(1 for p in preguntas if p.get("sin_respuesta")),
    }


def validar_composicion(banco: dict, resumen: dict, diag: Diagnostico) -> None:
    total = resumen["total"] or 1
    for clave, minimo in MINIMOS_COMPOSICION.items():
        proporcion = resumen[clave] / total
        if proporcion < minimo:
            diag.error(
                f"composicion.{clave}",
                f"{resumen[clave]} de {total} ({proporcion:.0%}); el mínimo del TODO 4.2 "
                f"es {minimo:.0%}",
            )
    faltan = set(banco.get("instantanea_indice", {}).get("portales", [])) - set(
        resumen["por_ciudad"]
    )
    if faltan:
        diag.error(
            "composicion.por_ciudad",
            f"sin ninguna pregunta: {sorted(faltan)}. El TODO 4.2 exige cubrir el corpus",
        )
    for dificultad in ("facil", "media", "dificil"):
        if not resumen["por_dificultad"].get(dificultad):
            diag.error(
                "composicion.por_dificultad",
                f"ninguna pregunta de dificultad '{dificultad}'",
            )
    if not resumen["por_ciudad"].get("cordoba"):
        diag.error(
            "composicion.por_ciudad",
            "sin preguntas sobre Córdoba: es el peor caso medido (145/145 datasets sin "
            "licencia declarada) y el TODO 4.2 lo exige explícitamente",
        )


def imprimir_composicion(resumen: dict) -> None:
    print(f"\nComposición · {resumen['total']} preguntas")
    print("  dificultad :", ", ".join(f"{k}={v}" for k, v in sorted(resumen["por_dificultad"].items())))
    print("  ciudad     :", ", ".join(f"{k}={v}" for k, v in sorted(resumen["por_ciudad"].items())))
    print(f"  multiciudad: {resumen['multiciudad']}")
    print(f"  sin respuesta posible: {resumen['sin_respuesta']}")
    print("  etiquetas  :", ", ".join(f"{k}={v}" for k, v in sorted(resumen["por_etiqueta"].items())))


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    aqui = Path(__file__).resolve().parent
    analizador = argparse.ArgumentParser(
        description="Valida el banco de evaluación BDAM-es contra su esquema.",
        epilog="Devuelve 0 si no hay errores y 1 si los hay. Los avisos no hacen fallar.",
    )
    analizador.add_argument("preguntas", type=Path, help="fichero de preguntas (JSON)")
    analizador.add_argument(
        "--esquema", type=Path, default=aqui / "esquema.json", help="JSON Schema a aplicar"
    )
    analizador.add_argument(
        "--indice",
        type=Path,
        default=None,
        help="índice SQLite contra el que comprobar que los datasets existen y que las "
        "preguntas sin respuesta siguen sin tenerla",
    )
    analizador.add_argument(
        "--composicion",
        action="store_true",
        help="además, exige el reparto del TODO 4.2 (≥15 %% multiciudad, ≥10 %% sin "
        "respuesta, cobertura del corpus, Córdoba presente)",
    )
    analizador.add_argument("--json", action="store_true", help="salida en JSON")
    args = analizador.parse_args(argv)

    diag = Diagnostico()
    try:
        esquema = json.loads(args.esquema.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"ERROR  --esquema: no se pudo leer {args.esquema}: {error}", file=sys.stderr)
        return 1
    try:
        banco = json.loads(args.preguntas.read_text(encoding="utf-8"))
    except OSError as error:
        print(f"ERROR  {args.preguntas}: no se pudo leer: {error}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as error:
        print(
            f"ERROR  {args.preguntas}: JSON mal formado en la línea {error.lineno}, "
            f"columna {error.colno}: {error.msg}",
            file=sys.stderr,
        )
        return 1

    ValidadorEsquema(esquema, diag).validar(banco, esquema)
    if isinstance(banco, dict):
        validar_semantica(banco, esquema, diag)
        resumen = resumen_composicion(banco)
        if args.composicion:
            validar_composicion(banco, resumen, diag)
        if args.indice:
            verificar_contra_indice(banco, args.indice, diag)
    else:
        resumen = {"total": 0}

    if args.json:
        print(
            json.dumps(
                {
                    "ok": diag.ok,
                    "errores": diag.errores,
                    "avisos": diag.avisos,
                    "composicion": resumen,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if diag.ok else 1

    diag.imprimir()
    if diag.ok:
        print(
            f"OK · {resumen['total']} preguntas válidas contra {args.esquema.name}"
            + (f" y verificadas contra {args.indice.name}" if args.indice else "")
            + (f" · {len(diag.avisos)} aviso(s)" if diag.avisos else "")
        )
        imprimir_composicion(resumen)
        return 0
    print(f"\nFALLO · {len(diag.errores)} error(es), {len(diag.avisos)} aviso(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
