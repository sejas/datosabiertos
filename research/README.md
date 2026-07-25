# Medición del ecosistema municipal de datos abiertos (25/07/2026)

Scripts que generan las cifras de `docs/02-analisis-catalogos.md`. Sin dependencias externas
(solo stdlib de Python 3).

```bash
python3 harvest.py   # cosecha 16 portales CKAN -> cat/*.json, summary.json
python3 sample.py    # muestrea 30 recursos/portal: enlaces vivos y tamaño real -> sample.json
python3 score.py     # rúbrica impacto+calidad 0-100 -> data/scores.json
```

`data/` guarda la salida de la ejecución del 25/07/2026. Los catálogos completos (`cat/`, 58 MB)
no se versionan: se regeneran con `harvest.py`.

`score.py` resuelve sus rutas respecto al propio script (lee `data/quality.json`,
`data/summary.json` y `data/poblacion_ine.json`, escribe `data/scores.json`), así que funciona
igual desde `research/` que desde la raíz del repo (`python3 research/score.py`).

`data/poblacion_ine.json` son las cifras oficiales de población del INE (operación DPOP,
tabla 29005 «Cifras oficiales del padrón por municipio», **1 de enero de 2025**, sexo Total),
descargadas de la API Tempus3 y con código INE, serie y URL de origen dentro del propio fichero:

```
https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/29005?tv=19:{id_ine}&tv=18:451&nult=1
```

El censo de municipios (`data/munis.json`) sale de una consulta SPARQL a datos.gob.es:

```sparql
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
SELECT ?id ?name (COUNT(DISTINCT ?d) AS ?n) WHERE {
  ?d a dcat:Dataset ; dct:publisher ?pub .
  ?pub dct:identifier ?id ; foaf:name ?name .
  FILTER(STRSTARTS(?id,"L01"))
} GROUP BY ?id ?name ORDER BY DESC(?n)
```

`L01` es el prefijo DIR3 de entidad local: filtra ayuntamientos entre todos los publicadores.

Cosechar con cortesía: concurrencia baja, User-Agent identificable, respetar `Crawl-Delay`.
