# datosabiertos — un agente MCP sobre catálogos municipales españoles

[![Tests](https://github.com/sejas/datosabiertos/actions/workflows/tests.yml/badge.svg)](https://github.com/sejas/datosabiertos/actions/workflows/tests.yml)
[![Cliente web](https://img.shields.io/badge/demo-sejas.github.io%2Fdatosabiertos-1d5c8f)](https://sejas.github.io/datosabiertos/)
[![Licencia MIT](https://img.shields.io/badge/c%C3%B3digo-MIT-17614a)](LICENSE)

Preguntar en lenguaje natural —*«¿qué datos hay sobre calidad del aire en Málaga desde
2020?»*— sobre los catálogos de datos abiertos de varios ayuntamientos españoles, y que un
modelo conteste **citando el dataset real** en vez de inventárselo.

Este repositorio contiene tres piezas que funcionan hoy:

1. Un **índice local** de metadatos DCAT cosechado de cinco portales municipales: **2.862
   datasets** y **23.390 distribuciones**.
2. Un **servidor MCP** con cuatro herramientas sobre ese índice, con transporte *stdio* y
   HTTP. Cero dependencias: solo la biblioteca estándar de Python.
3. Un **cliente web** que abre el índice dentro del navegador con sql.js y, opcionalmente,
   ejecuta un modelo pequeño por WebGPU. Sin servidor y sin coste de inferencia.

> **Demo:** <https://sejas.github.io/datosabiertos/> — el índice (3,4 MB comprimidos) se
> descarga al navegador y se consulta ahí. El modo directo funciona en cualquier navegador
> moderno; el modo agente necesita WebGPU (Chrome o Edge).

## Estado

Trabajo de Fin de Máster en curso (MUIA, UPM). **Es un prototipo, no un producto**, y
conviene leerlo como tal:

| | |
|---|---|
| Portales indexados | Madrid, Barcelona, Málaga, Córdoba y Reus |
| Última sincronización del índice publicado | 25/07/2026 |
| Tests | 41, sin red |
| Banco de evaluación | 15 preguntas de las 80–120 previstas |
| Evaluación de modelos | **todavía no ejecutada** |

Los datos son **una copia** de los portales, no el portal en vivo. Toda respuesta incluye
`url_origen` y `fecha_sincronizacion` para que se pueda comprobar contra la fuente.

## Arranque rápido

```bash
git clone git@github.com:sejas/datosabiertos.git && cd datosabiertos
python -m tfm.index build          # cosecha los 5 portales (~2 min, respetando robots.txt)
python -m tfm.index buscar "calidad del aire" --portal malaga
python -m tfm.mcp                  # servidor MCP por stdio
python -m unittest discover -s tests
```

Python 3.11+. **No hay `pip install`**: nada fuera de la biblioteca estándar. La cosecha
completa tarda unos 137 s en una Raspberry Pi 5, casi todo esperando por cortesía.

### Como servidor HTTP o contenedor

```bash
python -m tfm.mcp.http --puerto 8080 --estaticos web   # MCP en POST /mcp + cliente en /
docker compose up -d --build                            # lo mismo, empaquetado
```

`GET /salud` devuelve recuentos y fecha de sincronización.

## Herramientas MCP

| Herramienta | Argumentos | Devuelve |
|---|---|---|
| `buscar_datasets` | `consulta`, `ciudad?`, `tema?`, `anio?`, `limite=10` | Fichas ordenadas por relevancia (bm25 sobre FTS5) |
| `detalle_dataset` | `id` (`ciudad:id`) | Ficha DCAT completa con temas y palabras clave |
| `listar_distribuciones` | `id` | Formatos, URLs y tamaños |
| `comparar_ciudades` | `tema`, `ciudades?`, `limite_por_ciudad=3` | Qué publica cada ciudad **y quién no publica nada** |

`consultar_sparql` se dejó fuera a propósito: el índice es SQLite, no un *triplestore*. El
razonamiento está en [`docs/03-prior-art.md`](docs/03-prior-art.md) §5.5.

Para usarlo desde Claude Desktop, Claude Code o cualquier cliente MCP, y para las decisiones
de diseño del servidor: [`tfm/mcp/README.md`](tfm/mcp/README.md).

## Lo que hemos aprendido midiendo

**Córdoba no declara licencia en 145 de sus 145 datasets.** Un análisis previo hablaba de un
43 %; era un error de cálculo que ignoraba los `notspecified`. Casi toda la anomalía del
corpus está en un único portal. Las herramientas **nunca rellenan el hueco**: devuelven
`licencia_declarada: false` y una advertencia explícita, porque suponer CC-BY sería inventar.

**El idioma parte el índice en dos.** Barcelona y Reus publican en catalán: `contaminacion`
devuelve 0 resultados en Barcelona y `contaminació` devuelve 2. Una pregunta en español
puede fallar aunque el modelo elija bien la herramienta — es el índice el que no puede
responder. Antes de arreglarlo hay que medirlo: cuántos fallos son de idioma y no del
modelo es en sí un resultado.

**`Disallow` y la ley se contradicen.** Málaga y Reus declaran `Disallow: /api/` mientras
publican y documentan esa misma API CKAN, que la Directiva (UE) 2019/1024 les obliga a
ofrecer. La cosecha registra el conflicto, respeta siempre el `Crawl-Delay` y continúa;
con `TFM_RESPETAR_DISALLOW=1` se aplica la lectura estricta.

## Estructura

```
tfm/            Índice local y servidor MCP (Python, sin dependencias)
  conectores/   Un módulo por familia de portal; añadir uno son 3 pasos
  mcp/          Herramientas, transporte stdio y transporte HTTP
web/            Cliente del navegador: sql.js + WebLLM, sin servidor
bench/          Banco de evaluación en español: esquema, validador y preguntas
docs/           Análisis de catálogos, prior art y notas de diseño
research/       Scripts exploratorios y datos de la fase de análisis
tests/          41 tests, sin red
```

Empieza por [`docs/README.md`](docs/README.md) para el hilo conductor de los documentos.

## Licencias

- **Código** — MIT ([`LICENSE`](LICENSE)).
- **Banco de evaluación** (`bench/`) — CC BY-SA 4.0, ver [`bench/README.md`](bench/README.md).
- **Metadatos indexados** — pertenecen a cada ayuntamiento y conservan su licencia de
  origen. Cuando el portal no la declara, aquí tampoco se declara.
- `web/vendor/sql-wasm.*` procede de [sql.js-fts5](https://www.npmjs.com/package/sql.js-fts5)
  (MIT), compilado **con FTS5**, que el build estándar de sql.js no incluye.

## Contacto

La cosecha se identifica ante los portales con `datosabiertos@sejas.es`. Si administras uno
de los portales indexados y quieres que se ajuste algo, escribe ahí.
