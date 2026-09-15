# datosabiertos — un agente MCP sobre catálogos municipales españoles

[![Tests](https://github.com/sejas/datosabiertos/actions/workflows/tests.yml/badge.svg)](https://github.com/sejas/datosabiertos/actions/workflows/tests.yml)
[![Demo](https://img.shields.io/badge/demo-datosabiertos.sejas.es-1d5c8f)](https://datosabiertos.sejas.es/)
[![MCP](https://img.shields.io/badge/MCP-datosabiertos.sejas.es%2Fmcp-17614a)](https://datosabiertos.sejas.es/mcp)
[![Licencia MIT](https://img.shields.io/badge/c%C3%B3digo-MIT-17614a)](LICENSE)

Preguntar en lenguaje natural —*«¿qué datos hay sobre calidad del aire en Málaga desde
2020?»*— sobre los catálogos de datos abiertos de varios ayuntamientos españoles, y que un
modelo conteste **citando el dataset real** en vez de inventárselo.

Este repositorio contiene tres piezas que funcionan hoy:

1. Un **índice local** de metadatos DCAT cosechado de cinco portales municipales: **2.862
   datasets** y **23.390 distribuciones**.
2. Un **servidor MCP** con cuatro herramientas sobre ese índice, con transporte *stdio* y
   HTTP. Cero dependencias: solo la biblioteca estándar de Python.
3. Un **cliente web** con chat y dos motores intercambiables: un modelo alojado (OpenRouter,
   *tool calling* nativo, bucle de agente en el servidor) o un modelo pequeño que corre en el
   propio navegador por WebGPU. La búsqueda directa, sin modelo, abre el índice en el
   navegador con sql.js y funciona siempre.

> **Demo:** <https://datosabiertos.sejas.es/> — chat, búsqueda directa y las instrucciones
> para conectar el MCP a Claude Code, Codex, Claude Desktop, Cursor o VS Code.
>
> **MCP público:** `https://datosabiertos.sejas.es/mcp` (Streamable HTTP, sin autenticación,
> solo lectura). Una línea en Claude Code:
> `claude mcp add --transport http datosabiertos https://datosabiertos.sejas.es/mcp`

## Estado

Trabajo de Fin de Máster en curso (MUIA, UPM). **Es un prototipo, no un producto**, y
conviene leerlo como tal:

| | |
|---|---|
| Portales indexados | Madrid, Barcelona, Málaga, Córdoba y Reus |
| Última sincronización del índice publicado | 25/07/2026 |
| Tests | 59, sin red |
| Banco de evaluación | 15 preguntas de las 80–120 previstas |
| Evaluación de modelos | **todavía no ejecutada** |

Los datos son **una copia** de los portales, no el portal en vivo. Toda respuesta incluye
`url_origen` y `fecha_sincronizacion` para que se pueda comprobar contra la fuente.

## Arranque rápido

```bash
git clone git@github.com:sejas/datosabiertos.git && cd datosabiertos
python -m datosabiertos.index build          # cosecha los 5 portales (~2 min, respetando robots.txt)
python -m datosabiertos.index buscar "calidad del aire" --portal malaga
python -m datosabiertos.mcp                  # servidor MCP por stdio
python -m unittest discover -s tests
```

Python 3.11+. **No hay `pip install`**: nada fuera de la biblioteca estándar. La cosecha
completa tarda unos 137 s en una Raspberry Pi 5, casi todo esperando por cortesía.

### Como servidor HTTP o contenedor

```bash
python -m datosabiertos.mcp.http --puerto 8080 --estaticos web   # MCP en POST /mcp + cliente en /
docker compose up -d --build                            # lo mismo, empaquetado
```

`GET /salud` devuelve recuentos, fecha de sincronización y si el chat alojado está activo.

El chat alojado (`POST /chat`) solo se activa si hay clave de OpenRouter; sin ella la página
ofrece únicamente el motor del navegador. Variables de entorno (todas opcionales):

| Variable | Por defecto | Para qué |
|---|---|---|
| `OPENROUTER_API_KEY` | — | Activa el chat alojado |
| `TFM_MODELO_CHAT` | `meta/muse-spark-1.3-contributor` | Modelo (cualquiera de OpenRouter con `tools`) |
| `TFM_URL_MODELO` | OpenRouter | Cualquier API compatible con OpenAI (Ollama, vLLM…) |
| `TFM_CHAT_LIMITE_IP` / `TFM_CHAT_VENTANA` | 20 / 600 s | Tope por dirección IP |
| `TFM_CHAT_LIMITE_DIA` | 500 | Tope diario global: es dinero de quien aloja |

`./deploy.sh` sincroniza el árbol de trabajo (índice incluido) con el servidor y reconstruye
el contenedor; el `.env` con estas variables vive solo en el servidor.

## Herramientas MCP

| Herramienta | Argumentos | Devuelve |
|---|---|---|
| `buscar_datasets` | `consulta`, `ciudad?`, `tema?`, `anio?`, `limite=10` | Fichas ordenadas por relevancia (bm25 sobre FTS5) |
| `detalle_dataset` | `id` (`ciudad:id`) | Ficha DCAT completa con temas y palabras clave |
| `listar_distribuciones` | `id` | Formatos, URLs y tamaños |
| `comparar_ciudades` | `tema`, `ciudades?`, `limite_por_ciudad=3` | Qué publica cada ciudad **y quién no publica nada** |

`consultar_sparql` se dejó fuera a propósito: el índice es SQLite, no un *triplestore*. El
razonamiento está en [`docs/03-prior-art.md`](docs/03-prior-art.md) §5.5.

Para conectarlo a Claude Code, Codex, Claude Desktop, Cursor o VS Code —por HTTP contra el
servidor público o por *stdio* en local— y para las decisiones de diseño del servidor:
[`datosabiertos/mcp/README.md`](datosabiertos/mcp/README.md). Las mismas instrucciones, con botones de copiar,
están en la sección «Conecta tu agente» de la [demo](https://datosabiertos.sejas.es/#conectar).

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
datosabiertos/            Índice local y servidor MCP (Python, sin dependencias)
  conectores/   Un módulo por familia de portal; añadir uno son 3 pasos
  mcp/          Herramientas, transporte stdio, transporte HTTP y chat con modelo alojado
web/            Cliente del navegador: chat (servidor o WebLLM), búsqueda directa y guía MCP
bench/          Banco de evaluación en español: esquema, validador y preguntas
docs/           Análisis de catálogos, prior art y notas de diseño
research/       Scripts exploratorios y datos de la fase de análisis
tests/          59 tests, sin red
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
