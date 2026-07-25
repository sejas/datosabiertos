#!/usr/bin/env python3
"""¿Qué distrito de Madrid tiene más estaciones de BiciMad?

La pregunta la puso Óscar Corcho como ejemplo de "etapa 2": explorar el *contenido* de uno o
más datasets, no sus metadatos. Este script la responde de verdad, para medir qué hace falta.

Resultado (25/07/2026): Centro, con 59 de 631 estaciones. Las 631 se asignan a los 21
distritos sin ninguna huérfana.

Lo que hizo falta, que es el hallazgo:

1. `Estaciones de Bicimad` (datos.madrid.es) → distribución GeoJSON servida por
   `datos.emtmadrid.es`, otro host. **No trae el distrito**: solo coordenadas.
2. `Distritos municipales de Madrid` → KML con los 21 polígonos, pero **sin nombres**, solo
   códigos, y sin `ExtendedData`.
3. El mismo dataset, distribución CSV → tabla `COD_DIS` → `NOMBRE`, en latin-1 con BOM.
4. Cruce espacial punto-en-polígono (algoritmo de rayos) entre 1 y 2, y join por código
   con 3.

Dos datasets, tres distribuciones, tres formatos, un cruce espacial y un join. Ninguna de
las herramientas MCP de la fase 3 sabe hacer esto, y el datastore de CKAN tampoco: el
GeoJSON de BiciMad no está en el datastore. Véase `docs/04-etapa-2-exploracion-datos.md`.

Sin dependencias externas: el cruce espacial son 6 líneas de stdlib.
"""

from __future__ import annotations

import json
import sqlite3
import ssl
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tfm.configuracion import RUTA_INDICE, user_agent  # noqa: E402

KML_DISTRITOS = ("https://geoportal.madrid.es/fsdescargas/IDEAM_WBGEOPORTAL/"
                 "LIMITES_ADMINISTRATIVOS/Distritos/distritos.kml")
CSV_DISTRITOS = ("https://geoportal.madrid.es/fsdescargas/IDEAM_WBGEOPORTAL/"
                 "LIMITES_ADMINISTRATIVOS/Distritos/Distritos.csv")
NS = "{http://www.opengis.net/kml/2.2}"
_CTX = ssl.create_default_context()


def descargar(url: str) -> bytes:
    peticion = urllib.request.Request(url, headers={"User-Agent": user_agent()})
    with urllib.request.urlopen(peticion, timeout=90, context=_CTX) as respuesta:
        return respuesta.read()


def estaciones_bicimad() -> list[tuple[float, float]]:
    """Coordenadas de las estaciones, sacando la URL del índice local."""
    conexion = sqlite3.connect(RUTA_INDICE)
    conexion.row_factory = sqlite3.Row
    fila = conexion.execute(
        """SELECT di.url_descarga FROM distribucion di JOIN dataset d ON d.id = di.dataset_id
           WHERE d.titulo LIKE '%Estaciones de Bicimad%' AND di.formato = 'GEOJSON'"""
    ).fetchone()
    conexion.close()
    if not fila:
        raise SystemExit("No está el dataset en el índice. Ejecuta: python -m tfm.index build")
    # utf-8-sig + strip: el fichero llega con BOM y con un salto de línea por delante.
    geo = json.loads(descargar(fila[0]).decode("utf-8-sig").strip())
    return [(f["geometry"]["coordinates"][0], f["geometry"]["coordinates"][1])
            for f in geo["features"]]


def poligonos_distritos() -> list[tuple[str, list[list[tuple[float, float]]]]]:
    """Polígonos por código de distrito. El KML no trae nombres: solo el número."""
    raiz = ET.fromstring(descargar(KML_DISTRITOS))
    distritos = []
    for marca in raiz.iter(f"{NS}Placemark"):
        codigo = (marca.findtext(f"{NS}name") or "").strip()
        anillos = []
        for coordenadas in marca.iter(f"{NS}coordinates"):
            puntos = [
                (float(t.split(",")[0]), float(t.split(",")[1]))
                for t in (coordenadas.text or "").split()
                if len(t.split(",")) >= 2
            ]
            if len(puntos) > 3:
                anillos.append(puntos)
        if codigo and anillos:
            distritos.append((codigo, anillos))
    return distritos


def nombres_distritos() -> dict[str, str]:
    """`COD_DIS` -> `NOMBRE`, de la distribución CSV del mismo dataset."""
    texto = descargar(CSV_DISTRITOS).decode("utf-8-sig")
    nombres = {}
    for linea in texto.splitlines()[1:]:
        campos = linea.split(";")
        if len(campos) >= 3:
            nombres[campos[0].strip()] = campos[2].strip()
    return nombres


def dentro(x: float, y: float, anillo: list[tuple[float, float]]) -> bool:
    """Punto en polígono por lanzamiento de rayos."""
    interior = False
    for i in range(len(anillo)):
        x1, y1 = anillo[i]
        x2, y2 = anillo[(i + 1) % len(anillo)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1:
            interior = not interior
    return interior


def main() -> int:
    estaciones = estaciones_bicimad()
    distritos = poligonos_distritos()
    nombres = nombres_distritos()

    cuenta: Counter = Counter()
    huerfanas = 0
    for x, y in estaciones:
        for codigo, anillos in distritos:
            if any(dentro(x, y, anillo) for anillo in anillos):
                cuenta[nombres.get(codigo, f"distrito {codigo}")] += 1
                break
        else:
            huerfanas += 1

    print("¿Qué distrito de Madrid tiene más estaciones de BiciMad?\n")
    for puesto, (distrito, n) in enumerate(cuenta.most_common(), 1):
        print(f"  {puesto:>2}. {distrito:<24}{n:>4}")
    print(f"\n{len(estaciones)} estaciones · {sum(cuenta.values())} asignadas · "
          f"{huerfanas} sin distrito · {len(cuenta)}/{len(distritos)} distritos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
