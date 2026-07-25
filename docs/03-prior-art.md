---
type: note
title: Prior art — servidores MCP sobre catálogos de datos abiertos
date: 2026-07-25
tags: [tfm, prior-art, mcp, datos-abiertos, novedad]
---

# Prior art: servidores MCP sobre catálogos de datos abiertos

Cumple los TODOs **0.1** y **0.2**. Fecha de consulta de todo lo que hay aquí: **25/07/2026**.
Es el documento que va a la reunión de septiembre con Óscar Corcho.

## 0. Lo que hay que saber antes de entrar a la reunión

Diez líneas, sin adornos:

1. **El servidor MCP ya no es una contribución.** Hay al menos ocho implementaciones públicas que
   cubren, entre todas, cuatro de las cinco herramientas del §4 del plan. Dos de ellas son
   mejores que lo que el TFM iba a construir.
2. **La ciudad no es el eje diferencial.** `Opendata.cat-MCP-Server` ya indexa 15 portales
   catalanes —**incluidos Barcelona y Reus, dos de las seis ciudades del corpus**— con cosecha
   semanal y una *skill* llamada `radar-municipal` cuyo objetivo literal es el retrato de un
   municipio cruzando portales.
3. **La pregunta del modelo pequeño ya tiene una respuesta parcial publicada.** `ondata/ckan-mcp-server`
   ha hecho LoRA sobre Qwen2.5-0.5B para selección de herramienta MCP sobre CKAN, con dataset en
   HuggingFace y comparativa contra Gemini 2.5 Flash planificada. En italiano, y sólo para elegir
   el *nombre* de la herramienta, no los argumentos.
4. **El banco de evaluación sigue siendo lo más defendible**, pero ya no por ser el primero: por
   ser el primero **anotado a mano, con argumentos y con casos sin respuesta**. El de ondata es
   sintético (generado con Gemini a partir de logs) y sólo mapea `pregunta → nombre de herramienta`.
5. **La caracterización del ecosistema tampoco es virgen**: hay literatura académica española
   previa sobre madurez de portales municipales (Royo-Montañés & Benítez-Gómez, 2019, *EPI*).
6. **"Madrid Agentic City" no es prior art**: el repositorio `AyuntamientoMadrid/AgenticCity`
   contiene **sólo un fichero LICENSE**, un commit, cero estrellas.
7. **`cibelex-mcp` sí es real** (`AyuntamientoMadrid/cibelex-mcp-fuseki`, MIT, mayo 2026, 22
   herramientas), pero es sobre **normativa municipal**, no sobre catálogos de datos. No solapa en
   dominio; sí en método. Es la mejor vía de colaboración disponible.
8. **Óscar Corcho es coautor de `CiudadesAbiertas/CiudadesAbiertas-API`.** Está en el README del
   repositorio. Empezar la reunión por ahí.
9. **Nadie mide.** De los ocho proyectos revisados, ninguno publica una evaluación de sus propias
   herramientas con métricas de recuperación. Ese es el hueco real.
10. **Recomendación: reimplementación** de la capa MCP sobre el índice local ya construido,
    tomando diseño explícito de `zurich-opendata-mcp` y `ondata/ckan-mcp-server`. Ni fork ni
    dependencia. Justificado en el §7.

## 1. Método y qué está verificado

Distinguir esto importa más que el resultado, porque en la defensa lo van a preguntar.

**Verificado leyendo el repositorio** (descarga del tarball de la rama por defecto, lectura del
código fuente, `pyproject.toml`/`package.json`, README, CHANGELOG y LICENSE):
`Admindatosgobes/Laboratorio-de-Datos` (notebook completo), `AlbertoUAH/datos-gob-es-mcp`,
`mjanez/ckan-mcp-server`, `ondata/ckan-mcp-server`, `ondics/ckan-mcp-server`,
`malkreide/zurich-opendata-mcp`, `CiudadesAbiertas/CiudadesAbiertas-API`,
`AyuntamientoMadrid/cibelex-mcp-fuseki`, `AyuntamientoMadrid/AgenticCity`,
`xaviviro/Opendata.cat-MCP-Server`.

Todas las **firmas de herramienta que aparecen en este documento están extraídas del código**, no
de los README. Cuando README y código discrepan, se dice.

**No verificado, sólo visto en resultados de búsqueda o en prensa** (marcado con ⚠ en el texto):
la iniciativa MAIA/Agentic City del Ayuntamiento de Madrid más allá de sus repositorios públicos;
`stucchi/italy-opendata-mcp`; `ceami/opendata-mcp`; `datagouv/datagouv-mcp`; el *fork* de AgID;
el artículo de la Revista del CLAD; los trabajos de calidad UNE 0077–0080.

**Limitación conocida:** la API de GitHub aplicó límite de tasa a mitad de la sesión, así que
algunas fechas de último commit vienen de la página web del repositorio y no del endpoint de
commits. Se indica en cada ficha cuál es cuál.

---

## 2. Fichas por proyecto

### A. Agente conversacional con servidor MCP de datos.gob.es (oficial)

| | |
|---|---|
| **Repositorio** | `Admindatosgobes/Laboratorio-de-Datos`, subcarpeta `Data Science/Agente Conversacional con MCP server` |
| **Artículo** | https://datos.gob.es/en/conocimiento/conversational-agent-mcp-server-datosgobes — publicado 12/01/2026, actualizado 09/04/2026 |
| **Qué es** | Un **ejercicio didáctico**, no un servicio. Un único notebook (687 KB) que escribe con `%%writefile` un `server.py` (FastMCP), un `agent.py` (Google ADK, `LlmAgent` + `MCPToolset` sobre Streamable HTTP), un `main.py` (FastAPI) y un `docker-compose.yml`. No hay paquete, ni tests, ni CI, ni despliegue. |
| **Stack** | FastMCP (`mcp<1.20.0`), Google ADK, Gemini (`gemini-3-flash-preview`), FastAPI, httpx, Docker Compose |
| **Fuente de datos** | `https://datos.gob.es/apidata` (Linked Data API sobre Virtuoso). Sin caché ni índice local |
| **Licencia** | ⚠ **No hay fichero LICENSE en el repositorio.** El README de la subcarpeta declara **CC BY 4.0** (Red.es). CC BY no es una licencia de software: sirve para citar y derivar, pero no resuelve patentes ni garantías |
| **Último commit en la subcarpeta** | **23/01/2026** ("Incorporar información para usar en GitHub Codespaces"). Sólo 4 commits en total en esa ruta, el primero el 19/12/2025 |
| **Estado** | **Congelado.** El repositorio padre sigue vivo (push 25/06/2026) pero el MCP no se ha tocado en seis meses |

**Herramientas expuestas (5), firma exacta del código:**

```python
buscar_datasets(titulo: str, ctx: Context = None) -> Dict
listar_tematicas(ctx: Context = None) -> Dict
buscar_por_tematica(tematica_id: str, ctx: Context = None) -> Dict
obtener_detalles_dataset(dataset_id: str, ctx: Context = None) -> Dict
obtener_estadisticas_catalogo(ctx: Context = None) -> Dict
```

Nota: el §7 de `02-analisis-catalogos.md` decía `obtener_detalle_dataset`; el nombre real es
**`obtener_detalles_dataset`**, y hay una quinta herramienta que no estaba en el inventario.

**Qué hace cuando el portal falla:** `try/except Exception` genérico en cada herramienta;
devuelve `{"exito": False, "mensaje": "Error al buscar: <str(e)>"}`. Sólo `obtener_detalles_dataset`
distingue `httpx.HTTPStatusError` y reporta el código. **Sin reintentos, sin backoff, sin timeout
configurable** (30 s fijos, 60 s en estadísticas).

**Defectos concretos leídos en el código** — son munición para la reunión, porque demuestran que
"lo que ya existe" no es sustituto de un instrumento de investigación:

- `buscar_datasets` pide `_pageSize: 5` y después itera `items[:20]`. **Nunca devuelve más de 5
  resultados**, aunque el código aparente 20. Con `precision@10` esto es directamente inservible.
- Trunca toda descripción a 150 caracteres **y añade `"..."` siempre**, incluso si no truncó.
- **La búsqueda no devuelve licencia, ni URL de origen, ni fecha de modificación.** Incumple de
  raíz el criterio de procedencia del TODO 3.2.
- A favor: `obtener_detalles_dataset` devuelve `"No especificada"` cuando falta la licencia. No
  la inventa. Ese criterio coincide con el del índice local del TFM.

---

### B. `AlbertoUAH/datos-gob-es-mcp` — "Hub de OpenData Español"

| | |
|---|---|
| **Repositorio** | https://github.com/AlbertoUAH/datos-gob-es-mcp |
| **Qué es** | Un hub que unifica cinco fuentes estatales: datos.gob.es, INE, AEMET, BOE y Eurostat. Cada una es un servidor MCP independiente, más un `aggregator` que los compone |
| **Stack** | Python ≥3.10, FastMCP ≥2.0, httpx[http2], Pydantic 2, structlog, aiolimiter, `sentence-transformers` + `intfloat/multilingual-e5-small` para re-ranking semántico |
| **Licencia** | **MIT** (Alberto Fernández Hernández, 2025) |
| **Último commit** | **15/03/2026** (`fix: use sys.executable as default PYTHON_CMD…`) |
| **Estado** | **Mantenido pero en pausa.** 4 meses sin commits; con CI, tests, releases y workflows de seguridad. 18 estrellas |

**Herramientas del servidor de datos.gob.es (2), firma exacta:**

```python
search(query=None, title=None, publisher=None, theme=None, themes=None, format=None,
       keyword=None, date_start=None, date_end=None, exact_match=False, page=0, sort=None,
       lang="es", fetch_all=False, max_results=MAX_SEARCH_RESULTS, include_preview=False,
       preview_rows=DEFAULT_PREVIEW_ROWS, semantic_min_score=SEMANTIC_MIN_SCORE,
       license=None, frequency=None) -> str
get(dataset_id: str, include_data=False, format=None, max_rows=None,
    max_mb=MAX_DOWNLOAD_MB, lang="es") -> str
```

Más `ine_search`, `ine_download`, `boe_search`, `boe_get_summary`, `boe_get_document`,
`aemet_get_forecast`, `aemet_get_observations`, `aemet_list_locations`, `eurostat_search`,
`eurostat_get`, `eurostat_download`. **Recursos MCP (5):** `dataset://{dataset_id}`,
`theme://{theme_id}`, `publisher://{publisher_id}`, `format://{format_id}`, `keyword://{keyword}`.
**Prompts MCP (6):** `prompt_buscar_datos_por_tema`, `prompt_datasets_recientes`,
`prompt_explorar_catalogo`, `prompt_analisis_dataset`, `prompt_guia_herramientas`,
`prompt_buscar_estadisticas`.

**Qué hace cuando el portal falla:** rate limiting por API (`aiolimiter`), reintentos con backoff
exponencial, caché de metadatos de 24 h persistida en disco, caché de búsqueda con TTL de 10 min,
paginación paralela. Es, con diferencia, la gestión de fallos más completa de los proyectos en
español.

**Lo relevante para el TFM:** es la prueba de que la búsqueda semántica sobre metadatos españoles
con un modelo multilingüe pequeño (`multilingual-e5-small`) ya está hecha y funciona. Si el TFM
quiere argumentar que su `buscar_datasets` aporta algo, tiene que ser **midiendo**, no
implementando. Y es un competidor directo del baseline: `search` es un superconjunto estricto de
`buscar_datasets(consulta, ciudad, tema, año)` salvo por la dimensión municipal.

**Limitación clave:** es **nacional**, no municipal. `publisher` es un ID de organismo
(`EA0010587` para el INE), no un nombre de ciudad, y hereda el empobrecimiento de metadatos de la
federación de datos.gob.es que ya documenta el §2 de `02-analisis-catalogos.md`.

---

### C. `mjanez/ckan-mcp-server`

| | |
|---|---|
| **Repositorio** | https://github.com/mjanez/ckan-mcp-server |
| **Qué es** | MCP genérico sobre un portal CKAN, con i18n (gettext, es/en) y detección de datasets geoespaciales. Portal de prueba recomendado: el catálogo del MITECO |
| **Stack** | Python ≥3.10, FastMCP ≥2.13, ckanapi ≥4.7, Pydantic 2, gettext, `uv` |
| **Licencia** | **MIT** |
| **Último commit en `main`** | **25/11/2025** (merge del PR #1 desde `develop`). El repositorio registra un push posterior el 07/12/2025 en otra rama |
| **Estado** | **Prácticamente abandonado.** 3 commits, 0 estrellas, 0 forks, sin tests ni CI (están en el *roadmap*), 8 meses sin actividad en `main` |

**Herramientas (5), firma exacta:**

```python
search_datasets(query: str = "*:*", formats: List[str] = [], organization: Optional[str] = None,
                only_geospatial: bool = False, limit: int = 10, ctx: Context = None) -> str
get_datasets(dataset_id: str, ctx: Context = None) -> str
query_datastore(resource_id: str, sql_query: Optional[str] = None, limit: int = 10,
                ctx: Context = None) -> str
list_organizations(limit: int = 20, ctx: Context = None) -> str
get_capabilities(ctx: Context = None) -> str
```

**Recursos (3):** `ckan://dataset/{dataset_id}`, `ckan://dataset/{dataset_id}/schema`, `ckan://info`.

**Qué hace cuando el portal falla:** middleware de caché de respuestas y reintentos automáticos
declarados en el README; el manejo por herramienta es `try/except` con mensaje formateado y
`ctx.error()`.

**Detalle importante:** el portal es **una variable de entorno** (`CKAN_URL`), no un argumento. El
multiciudad se resuelve declarando **una entrada distinta en `claude_desktop_config.json` por
portal** — el propio README lo hace con MITECO y datos.gob.es. Eso significa que el modelo ve dos
servidores con las mismas cinco herramientas y tiene que elegir por el nombre del servidor. Es un
antipatrón para el tool-calling y **conviene medirlo**: es exactamente el tipo de hallazgo que
justifica la reformulación del TFM.

En el *roadmap*, sin implementar: "Full DCAT-AP support and SPARQL queries".

---

### D. `ondata/ckan-mcp-server` — el más avanzado, y el más peligroso para la novedad

| | |
|---|---|
| **Repositorio** | https://github.com/ondata/ckan-mcp-server · npm `@aborruso/ckan-mcp-server` · endpoint alojado en Cloudflare Workers |
| **Qué es** | MCP genérico sobre **cualquier** portal CKAN, con `server_url` como argumento por llamada. 20 herramientas, prompts, recursos, UI embebida para tablas del DataStore, telemetría pública y un programa de evaluación con *fine-tuning* |
| **Stack** | TypeScript, `@modelcontextprotocol/sdk` ^1.27, zod, axios, express, Cloudflare Workers, vitest (443 tests) |
| **Licencia** | **MIT** |
| **Versión / último push** | v0.4.112 · **25/07/2026** (mismo día de la consulta) |
| **Estado** | **Muy activo.** 57 estrellas, 14 forks. **Reutilizado por AgID**, la agencia digital italiana ⚠ (no verificado el fork). Ritmo de release casi diario |

**Herramientas (20), nombres exactos:**

`ckan_package_search`, `ckan_find_relevant_datasets`, `ckan_package_show`, `ckan_list_resources`,
`ckan_datastore_search`, `ckan_datastore_search_sql`, `ckan_analyze_datasets`,
`ckan_catalog_stats`, `ckan_group_list`, `ckan_group_show`, `ckan_group_search`,
`ckan_organization_list`, `ckan_organization_show`, `ckan_organization_search`, `ckan_tag_list`,
`ckan_status_show`, `ckan_find_portals`, `ckan_get_mqa_quality`, `ckan_get_mqa_quality_details`,
`sparql_query`.

Firmas relevantes, extraídas de los esquemas zod:

```ts
ckan_package_search({ server_url, q, fq, rows, start, page, page_size, sort,
                      facet_field, facet_limit, include_drafts, query_parser, response_format })
ckan_find_relevant_datasets({ server_url, query, limit,
                              weights: { title, notes, tags, organization, holder, publisher },
                              query_parser, response_format })
ckan_package_show({ server_url, id, include_tracking, response_format })
ckan_list_resources({ server_url, id, format_filter, response_format })
ckan_find_portals({ country, query, min_datasets, language, has_datastore, limit })
sparql_query({ endpoint_url, query, limit, response_format })
ckan_get_mqa_quality({ server_url, dataset_id, response_format })
```

**Qué hace cuando el portal falla:** `formatCkanError` por herramienta con `isError: true`; caché
con clave canónica tipada; límite de tamaño de respuesta y de descompresión configurable
(`CKAN_MAX_RESPONSE_BYTES`, `CKAN_MAX_DECOMPRESSED_BYTES`); *allowlist* de host anclada por
`URL.parse`; contención de *prompt injection* envolviendo las descripciones no fiables en bloques
`wrapUntrusted`. El `LOG.md` documenta tres rondas de *hardening* de seguridad en julio de 2026.

**Salvaguardas de SPARQL** (relevantes para el TODO 3.5): sólo HTTPS, sólo `SELECT`
(`validateSelectQuery`), *timeout* de 15 s, `LIMIT` inyectado automáticamente si falta, truncado de
salida por `CHARACTER_LIMIT`. Es el modelo a copiar si el TFM decide implementar `consultar_sparql`.

**Lo que hace de este proyecto un problema para el TFM** — la carpeta `evals/`:

- `data/worker_events_flat.jsonl`: **5.766 eventos reales** de llamadas de herramienta capturados
  del despliegue en Cloudflare, con herramienta, portal, consulta y resultado.
- `data/nl_eval_queries.jsonl`: **1.583 pares `pregunta en lenguaje natural → herramienta`**
  generados con Gemini 2.5 Flash por traducción inversa desde los logs reales.
- `data/train.jsonl` (1.270) + `data/eval.jsonl` (313), partición estratificada por herramienta,
  **publicados en HuggingFace** como `aborruso/ckan-tool-selection`, con licencia **CC BY-SA 4.0**.
- `evals/tool-selection/colab_finetune.py`: **LoRA sobre Qwen2.5-0.5B-Instruct** con Unsloth,
  rango 16, 3 épocas, 8,8 M de 502 M parámetros entrenados. Modelo publicado como
  `aborruso/ckan-tool-selector`.
- `evals/tool-selection/eval_tool_selection.py` existe; la fase 4 del README —comparar el modelo
  pequeño contra Gemini 2.5 Flash sobre los 313 ejemplos— **está marcada como "upcoming" y no hay
  resultados publicados a 25/07/2026**.

Y en "future directions" del mismo README: *"Serve locally: convert the fine-tuned model to GGUF
format and run via Ollama for zero-cost, zero-latency tool routing"*.

Traducción directa: el §3 del plan del TFM —*¿basta un modelo pequeño para hacer de agente sobre
catálogos?*— ya lo está respondiendo otro equipo, en abierto, con datos reales y no simulados.
El detalle del §6 se analiza en el §6 de este documento.

---

### E. `ondics/ckan-mcp-server`

| | |
|---|---|
| **Repositorio** | https://github.com/ondics/ckan-mcp-server |
| **Qué es** | MCP mínimo sobre CKAN, un único fichero de 23 KB, con Docker y transporte stdio + SSE |
| **Stack** | Python ≥3.13, SDK MCP de bajo nivel (`types.Tool` a mano, sin FastMCP), Docker |
| **Licencia** | **MPL-2.0** — copyleft *por fichero*. Copiar código de aquí obliga a mantener MPL en el fichero destino. Es la única licencia del inventario que restringe |
| **Último commit** | **24/04/2026**; merge el 27/04/2026. v1.1.2 |
| **Estado** | **Mantenimiento mínimo.** 14 estrellas, 9 forks. CHANGELOG con cuatro entradas en un año, todas correcciones (`CTRL+C` cuelga, crash al reconectar SSE) |

**Herramientas activas (11), nombres exactos:** `ckan_package_list`, `ckan_package_show`,
`ckan_package_search`, `ckan_organization_list`, `ckan_organization_show`, `ckan_group_list`,
`ckan_tag_list`, `ckan_resource_show`, `ckan_site_read`, `ckan_status_show`,
`ckan_datastore_search`. Hay seis más de escritura (`datastore_create`, `upsert`, `delete`,
`commit`, `table_create`, `table_delete`) **comentadas en el código con la nota `# @TODO Untested`**.

```jsonc
ckan_package_search  { q="*:*", fq, sort, rows=10, start=0 }
ckan_package_show    { id }                       // requerido: id
ckan_resource_show   { id }                       // id de recurso, no de dataset
ckan_datastore_search{ resource_id, limit, offset, q, sort, fields }  // requerido: resource_id
```

**Qué hace cuando el portal falla:** poco. El CHANGELOG revela que hasta abril de 2026 las
respuestas de error de la API de CKAN se registraban a nivel WARNING. Portal por variable de
entorno (`CKAN_URL`), igual que mjanez.

**Veredicto:** el menos interesante de los cinco CKAN. Aporta un dato útil, eso sí: es el único
con licencia copyleft, y por tanto el único del que **no** conviene copiar código.

---

### F. `malkreide/zurich-opendata-mcp` — el gemelo del TFM, para otra ciudad

| | |
|---|---|
| **Repositorio** | https://github.com/malkreide/zurich-opendata-mcp · PyPI `zurich-opendata-mcp` |
| **Qué es** | MCP municipal completo de la ciudad de Zúrich sobre 6 APIs: CKAN, ParkenDD, Geoportal WFS, API del Gemeinderat, turismo y SPARQL. Parte de un "Swiss Public Data MCP Portfolio" |
| **Stack** | Python ≥3.11, FastMCP (`mcp[cli]` ≥1.28.1), httpx, Pydantic 2, hatchling, `uv`, CI en GitHub Actions, 14 ficheros de test |
| **Licencia** | **MIT** |
| **Versión / último commit** | v0.5.1 · **24/07/2026** |
| **Estado** | **Muy activo y con proceso.** 8 estrellas, 5 forks. `CHANGELOG.md` de 22 KB, tres auditorías de seguridad en `audits/`, `SECURITY.md`, `docs/SECURITY-BASELINE.md`. La v0.5.0 cierra "los 13 hallazgos de la revisión de julio de 2026 (F-1–F-13)" |

**Herramientas: 26 registradas por defecto** (el README dice "23 tools (+3 deprecated aliases)",
lo que cuadra) **+1 opcional**. Las del catálogo, con firma exacta:

```python
zurich_search_datasets(params: SearchDatasetsInput)
#   query: str (1..500, sintaxis Solr) · rows: int = 10 (1..50) · offset: int = 0
#   sort: str|None · filter_group: ZurichGroup|None
zurich_get_dataset(params: GetDatasetInput)          # dataset_id: str (min_length=1)
zurich_list_categories(params: ListGroupInput)       # group_id: ZurichGroup|None
zurich_list_tags(params: TagSearchInput)             # query: str|None · limit: int = 30 (1..100)
zurich_analyze_datasets(params: AnalyzeDatasetInput)
#   query: str · max_datasets: int = 5 (1..20) · include_structure: bool · include_freshness: bool
zurich_catalog_stats()                               # sin argumentos
zurich_find_school_data(params: FindSchoolDataInput)  # topic: str|None
zurich_datastore_query(params: DatastoreQueryInput)
#   resource_id: str · filters: str|None · query: str|None · sort: str|None
#   limit: int = 20 (1..100) · offset: int = 0
zurich_datastore_sql(params: DatastoreSqlInput)      # sql: str
zurich_geo_layers / zurich_geo_features / zurich_parliament_* / zurich_strb_* /
zurich_tourism / zurich_parking_live / zurich_weather_live / zurich_air_quality /
zurich_water_weather / zurich_pedestrian_traffic / zurich_vbz_passengers
```

**Recursos MCP (5):** `zurich://dataset/{name}`, `zurich://category/{group_id}`,
`zurich://parking`, `zurich://geo/{layer_id}`, `zurich://tourism/categories`.

**El caso SPARQL merece atención.** `zurich_sparql(params: SparqlQueryInput)` existe, pero:

- **no se registra por defecto**: hace falta `ZURICH_OPENDATA_ENABLE_SPARQL=1`;
- cuando se registra, **devuelve un aviso estático**, no ejecuta nada;
- el comentario del código explica por qué: el endpoint `ld.stadt-zuerich.ch` está accesible pero
  sin datos productivos, y dejar la herramienta registrada *"ocuparía contexto en la lista de
  herramientas de todos los clientes MCP e invitaría a llamadas inútiles"*.

Ese razonamiento —el coste de contexto de una herramienta que no sirve— es un argumento de diseño
citable y directamente aplicable al TODO 3.5.

**Qué hace cuando el portal falla** — es el mejor del inventario y el patrón a copiar:

- un único `httpx.AsyncClient` por proceso, cerrado en el *lifespan* de FastMCP;
- `AsyncHTTPTransport(retries=2)` para fallos de conexión;
- reintento único con 1 s de espera **sólo** ante 502/503/504, con la justificación escrita de por
  qué no ante 4xx/500 (*"son respuestas deterministas, no hipos transitorios de pasarela"*);
- `handle_api_error(e, context)` traduce el código HTTP a un mensaje accionable (404 → "comprueba
  el ID", 429 → "espera"), registra con `exc_info` y devuelve `is_error=True` en el
  `CallToolResult`;
- todos los modelos de entrada llevan `extra="forbid"` y `str_strip_whitespace=True`, con `ge`/`le`
  en cada numérico;
- todas las herramientas declaran `ToolAnnotations(readOnlyHint=True, destructiveHint=False,
  idempotentHint=True, openWorldHint=...)`;
- las herramientas relevantes devuelven `Annotated[CallToolResult, ModeloPydantic]`, es decir,
  markdown para el humano y JSON estructurado para el programa **en la misma respuesta**.

**Dónde no llega:** es mono-ciudad por construcción (el grupo temático es un `Enum` de las 19
categorías de Zúrich); **no tiene índice local**, cada llamada golpea la API; y todas las
descripciones de herramienta están **en alemán**, lo que lo hace inservible como baseline en
español sin traducirlo.

---

### G. `xaviviro/Opendata.cat-MCP-Server` — el hallazgo incómodo

Este proyecto **no estaba en el inventario del §7 de `02-analisis-catalogos.md`** y es el que más
directamente amenaza la contribución nº 3 del TFM.

| | |
|---|---|
| **Repositorio** | https://github.com/xaviviro/Opendata.cat-MCP-Server · npm `@opendata.cat/mcp-server` · endpoint HTTP `https://opendata.cat/api/mcp` |
| **Qué es** | MCP **multi-portal** sobre las datos abiertos de Cataluña. **15 portales, +3.044 datasets.** De opendata.cat, asociación sin ánimo de lucro fundada en 2012. Inspirado en `datagouv/datagouv-mcp` del gobierno francés ⚠ |
| **Stack** | TypeScript, SDK MCP, zod, clientes por familia de API: CKAN, Socrata, Opendatasoft, DIBA REST, CIDO JSON:API, Idescat, GTFS-RT |
| **Licencia** | **MIT** |
| **Versión** | v0.6.0, **15/07/2026** (según CHANGELOG del README). 21 estrellas, 61 commits |
| **Estado** | **Activo.** v0.5.0 el 06/06/2026, v0.6.0 el 15/07/2026 |

**Portales indexados que solapan con el corpus del TFM:** **Ajuntament de Barcelona (555
datasets) y Ajuntament de Reus (119 datasets)** — las mismas cifras exactas que midió la cosecha
del índice local del TFM el 25/07/2026. Más Generalitat (1.059), Consorci AOC (~887, con datos de
+1.000 municipios), Girona (53), Diputació de Barcelona (90), FGC, Idescat, Renfe, INE, REE, SEPE,
CNMC, CORA.

**Herramientas (8), firma exacta:**

```ts
search_datasets({ query: string, portal?: string, category?: string, limit?: number = 20 })
get_dataset_info({ dataset_id: string })          // metadatos completos: campos, tipos, licencia, endpoint
list_dataset_fields({ dataset_id: string })
query_dataset({ dataset_id: string, filters?: Record<string,string>, search?: string,
                limit?: number = 20, offset?: number = 0 })
list_portals({})
list_categories({})
related_datasets({ dataset_id: string })          // "Find related datasets from OTHER portals"
search_radioteca({ query, year, ... })
```

**Y cuatro *skills*** servidas como recursos MCP (`skill://<nombre>/SKILL.md`) y como prompts-puente
invocables como slash-command: `consulta-dades-obertes`, `contractacio-publica`,
**`radar-municipal`** ("retrat complet d'un municipi creuant portals: pressupost, deute,
contractes, població") y `patrimoni-i-hemeroteca`.

En los ejemplos de uso del README, literalmente: ***"Compara Girona i Tarragona en dades obertes"***.

**Arquitectura:** catálogo centralizado en `opendata.cat` con **crawling incremental semanal**;
el MCP consulta ese catálogo para descubrir y va al portal de origen para los datos. Es decir,
**la misma decisión de diseño que el TFM tomó con el índice local**, ya implementada y desplegada.

**Dónde no llega** —y aquí está lo que el TFM puede reclamar—:

- **No hay herramienta de comparación entre municipios.** La comparación la orquesta el LLM
  guiado por la *skill* `radar-municipal`. Nadie ha medido si eso funciona.
- **No mide nada.** No hay banco de preguntas, ni métricas, ni evaluación publicada.
- Ámbito **catalán**, no estatal. Córdoba, Málaga, Madrid, Gijón y Zaragoza quedan fuera.
- **No trabaja sobre DCAT-AP-ES ni sobre el grafo de metadatos**: normaliza a un esquema propio
  por familia de API. La heterogeneidad semántica entre municipios que documenta el §2 del análisis
  de catálogos queda oculta, no caracterizada.

---

### H. `CiudadesAbiertas/CiudadesAbiertas-API`

| | |
|---|---|
| **Repositorio** | https://github.com/CiudadesAbiertas/CiudadesAbiertas-API |
| **Qué es** | API REST de datos abiertos del proyecto **Ciudades Abiertas** (A Coruña, Madrid, Santiago de Compostela, Zaragoza + Red.es). Un módulo Java por dominio temático: `API_CALIDADAIRE`, `API_PRESUPUESTO`, `API_CONTRATOS`, `API_PADRON`, `API_TERRITORIO`, `API_TRAFICO`, `API_CALLEJERO`, `API_SUBVENCION`, `API_ORGANIGRAMA`… ~30 módulos, más `rdfGeneratorZ` para serialización RDF |
| **Autores** | Juan Carlos Ballesteros (Localidata), Carlos Martínez de la Casa (Localidata) y **Óscar Corcho (UPM, Localidata)** — figura textualmente en el README |
| **Stack** | Java, Spring, Liquibase (Oracle 11G / SQL Server 2017 / MySQL 5.7) |
| **Licencia** | **EUPL-1.2** |
| **Último push** | **21/06/2022** |
| **Estado** | **Abandonado como código**, cuatro años sin tocar. Vivo como **antecedente conceptual** |

**No es prior art de MCP** — es anterior a MCP por cinco años. Es prior art de otra cosa, y más
importante: es **la respuesta pre-LLM al mismo problema que el TFM ataca**. Ciudades Abiertas
resolvió la interoperabilidad municipal **estandarizando el modelo por adelantado**: un vocabulario
y una API idénticos en las cuatro ciudades. El TFM propone lo contrario: **aceptar la
heterogeneidad y hacer que el modelo la salve en tiempo de consulta**.

Esa oposición es un buen marco para la memoria y, sobre todo, es el terreno del director. La
pregunta que hay que llevarle es directa: *¿por qué Ciudades Abiertas no escaló más allá de cuatro
ayuntamientos, y qué de eso explica lo que mido en el §2 del análisis de catálogos?*

---

### I. `AyuntamientoMadrid/AgenticCity` — TODO 0.2, parte 1

| | |
|---|---|
| **Repositorio** | https://github.com/AyuntamientoMadrid/AgenticCity |
| **Descripción declarada** | "Madrid Agentic City, The City at your service, thanks to Gen AI" |
| **Contenido real** | **Un único fichero: `LICENSE`.** Un commit. Sin README, sin código, sin ramas adicionales, sin tags |
| **Licencia** | Apache-2.0 |
| **Última actividad** | 24/04/2025 · 0 estrellas, 0 forks, 1 watcher |

**Respuesta a las cuatro preguntas del TODO 0.2:**

- **¿Qué es?** Un marcador de posición. Reserva del nombre.
- **¿Está vivo?** No. Quince meses sin un segundo commit.
- **¿Es público?** El repositorio sí; el proyecto que anuncia, no.
- **¿Solapa?** **No.** No hay nada con lo que solapar.

⚠ **No verificado, sólo prensa:** la iniciativa que hay detrás sí existe. Bajo el paraguas **MAIA
(Madrid Inteligencia Artificial)** se describe el paso de *smart city* a *agentic city*, con agentes
para servicios sociales, reservas deportivas, citas y padrón, y un MVP agéntico aplicado al
mantenimiento viario que integra el 010, la app Línea Madrid y el portal web; con RAG, LLMs y
LangChain sobre infraestructura *multicloud*, y con Atos adjudicataria del mantenimiento de la
plataforma desde marzo de 2025. **Nada de esto está en GitHub y nada de esto toca catálogos de
datos abiertos.**

**Posicionamiento para la reunión:** ninguno necesario. Si sale el tema, la respuesta es que el
repositorio está vacío y que lo publicado por Madrid en abierto va por otro camino — el de la
ficha siguiente.

---

### J. `AyuntamientoMadrid/cibelex-mcp-fuseki` — TODO 0.2, parte 2

| | |
|---|---|
| **Repositorio** | https://github.com/AyuntamientoMadrid/cibelex-mcp-fuseki |
| **Qué es** | Servidor MCP que expone el **Cibelex Knowledge Graph** (normativa municipal de Madrid) sobre un endpoint SPARQL de Apache Jena Fuseki. Dos paquetes: `cibelex-retrieval` (librería pura de estrategias de recuperación) y `cibelex-mcp` (el servidor) |
| **Stack** | Python ≥3.11, FastMCP, `uv` workspace, Docker Compose, transporte stdio o SSE |
| **Licencia** | **MIT** el código. La ontología **LoRO** y el grafo Cibelex, **CC-BY 4.0** |
| **Última actividad** | **Mayo de 2026.** 3 commits, 0 estrellas |
| **Mantenedor** | **Equipo MAIA del IAM (Informática Ayuntamiento de Madrid)**, explícitamente en el README: *"Issues, suggestions and pull requests are welcome"* |
| **Estado** | Publicado y funcional, pero recién nacido y sin tracción externa |

**Herramientas: el README dice 21; el código registra 22.** La discrepancia es
`subdivision_lookup_tool`, que está implementada y registrada pero no aparece en las tablas del
README. Firmas exactas:

```python
# Búsqueda de entidades (7)
search_norms_tool(text: str, limit: int = 20)
lookup_norm_by_id_tool(identifier: str, limit: int = 10)
search_orgs_tool(text: str, limit: int = 20)
search_persons_tool(text: str, limit: int = 20)
search_places_tool(text: str, limit: int = 20)
search_events_tool(text: str, limit: int = 20)
search_taxonomy_tool(text: str, scheme: str = "", limit: int = 20)
# Joins entre grafos (5)
norms_by_topic_tool(topic_text: str, limit: int = 20)
norms_by_org_tool(org_text: str, limit: int = 20)
norms_by_place_tool(place_text: str, limit: int = 20)
norms_by_person_tool(person_text: str, limit: int = 20)
norms_by_event_tool(event_text: str, limit: int = 20)
# Recorrido del grafo (4)
amendment_chain_tool(norm_uri: str, limit: int = 50)
taxonomy_hierarchy_tool(text: str, limit: int = 50)
competence_lookup_tool(text: str, limit: int = 20)
neighbors_tool(uri: str, graph: str = "", depth: int = 1, limit: int = 100)
# Contexto completo (3)
norm_detail_tool(norm_uri: str)
subdivision_lookup_tool(norm_uri: str, path: list[str], include_text: bool = True, limit: int = 10)
person_context_tool(person_text: str)
# Introspección (3)
list_graphs_tool()
describe_graph_tool(graph_name: str)
sparql_query_tool(query: str, graph: str = "")
```

**Respuesta a las cuatro preguntas del TODO 0.2:**

- **¿Qué es?** Un MCP municipal real, del ayuntamiento de la ciudad mejor puntuada del corpus,
  sobre un grafo RDF propio con ontología propia (LoRO, DOI 10.5281/zenodo.20076577, v1.0 de
  07/05/2026, CC BY 4.0, extensión de ELI a documentos municipales).
- **¿Está vivo?** Sí, pero apenas. Publicado en mayo de 2026, 3 commits, sin comunidad.
- **¿Es público?** Sí. Código MIT, ontología con DOI, grafo con *dataset card* en HuggingFace
  (`MAIA-Madrid-IA/cibelex-graph-core-sampler`).
- **¿Solapa?** **No en dominio.** Cibelex es normativa (ordenanzas, decretos, competencias,
  cadenas de modificación), no catálogos de datos abiertos. Cero solapamiento con las cinco
  herramientas del §4. **Sí en método**, y mucho: mismo protocolo, mismo patrón de "grafo
  municipal + herramientas de recuperación + SPARQL crudo como último recurso", misma ciudad.

**Posicionamiento, escrito antes de la reunión como exige el TODO 0.2:**

No hace falta defenderse: hace falta **usarlo**.

1. **Como precedente de diseño citable.** 22 herramientas organizadas en cinco familias
   (búsqueda / *join* / recorrido / contexto / introspección) es una taxonomía mejor que la lista
   plana de cinco del §4 del plan. Merece aparecer en el capítulo 4 como alternativa considerada.
2. **Como validación institucional del planteamiento.** Que el IAM publique un MCP sobre un grafo
   municipal en abierto es el mejor argumento de que el problema del TFM le importa a alguien
   fuera de la universidad.
3. **Como vía de colaboración concreta.** El README pide *issues* y *pull requests*. Una pregunta
   a MAIA sobre si les interesa el mismo tratamiento para el catálogo de datos abiertos de Madrid
   es barata y puede desbloquear un caso de uso real y una carta de apoyo para la difusión.
4. **Como pregunta para Óscar.** LoRO está firmada por trece personas del Ayuntamiento y de
   Informática del Ayuntamiento de Madrid; **no aparece ninguna afiliación al OEG ni a la UPM**.
   Dado que Óscar sí firmó CiudadesAbiertas-API con Madrid, conviene preguntarle directamente si
   hay relación con MAIA. Si la hay, es un canal; si no la hay, es un dato sobre cómo se está
   moviendo el ecosistema sin la academia.

---

## 3. Tabla de solapamiento con el §4 del plan

Columnas, por orden: **[A]** MCP oficial datos.gob.es · **[B]** AlbertoUAH · **[C]** mjanez ·
**[D]** ondata · **[E]** ondics · **[F]** zurich · **[G]** Opendata.cat · **[J]** cibelex.

Leyenda: **✅ cubierto** (existe herramienta equivalente con argumentos suficientes) ·
**🟡 parcial** (existe pero le falta una dimensión, o hay que emularla desde otra herramienta) ·
**❌ no cubierto**.

| Herramienta del §4 | A | B | C | D | E | F | G | J |
|---|---|---|---|---|---|---|---|---|
| `buscar_datasets(consulta, ciudad, tema, año)` | 🟡 | ✅ | 🟡 | ✅ | 🟡 | 🟡 | ✅ | ❌ |
| `detalle_dataset(id)` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `listar_distribuciones(id)` | 🟡 | 🟡 | 🟡 | ✅ | 🟡 | 🟡 | 🟡 | ❌ |
| `consultar_sparql(query)` | ❌ | ❌ | ❌ | ✅ | ❌ | 🟡 | ❌ | ✅ |
| `comparar_ciudades(tema)` | ❌ | ❌ | ❌ | 🟡 | ❌ | ❌ | 🟡 | ❌ |

### Detalle por fila, con la firma equivalente

**`buscar_datasets(consulta, ciudad, tema, año)`**

| | Equivalente | Qué falta |
|---|---|---|
| A | `buscar_datasets(titulo)` + `buscar_por_tematica(tematica_id)` | Sin `ciudad`, sin `año`. Además el bug de `_pageSize: 5` |
| B | `search(query, title, publisher, theme, themes, format, keyword, date_start, date_end, exact_match, page, sort, lang, fetch_all, max_results, include_preview, preview_rows, semantic_min_score, license, frequency)` | Superconjunto. `ciudad` sólo como `publisher` (ID de organismo). Ámbito nacional |
| C | `search_datasets(query, formats, organization, only_geospatial, limit)` | Sin `año`. Portal fijado por `CKAN_URL` en el entorno |
| D | `ckan_package_search(server_url, q, fq, rows, start, page, page_size, sort, facet_field, facet_limit, include_drafts, query_parser, response_format)` y `ckan_find_relevant_datasets(server_url, query, limit, weights, query_parser, response_format)` | Nada esencial: `ciudad` = `server_url`, `año` = rango Solr en `fq`, `tema` = faceta |
| E | `ckan_package_search(q, fq, sort, rows, start)` | Sin `año` ni `ciudad`. Portal por entorno |
| F | `zurich_search_datasets(query, rows, offset, sort, filter_group)` | Sin `año`. `ciudad` imposible: es mono-ciudad por diseño |
| G | `search_datasets(query, portal, category, limit)` | Sin `año`. `portal` ≈ `ciudad` para los 15 portales catalanes |
| J | — | Otro dominio |

**`detalle_dataset(id)`** — la única fila donde todo el mundo llega.

| | Equivalente |
|---|---|
| A | `obtener_detalles_dataset(dataset_id)` — devuelve título, descripción, publisher, temáticas, keywords, fechas, licencia, cobertura temporal y espacial, distribuciones (máx. 10) |
| B | `get(dataset_id, include_data, format, max_rows, max_mb, lang)` — con descarga opcional de los datos |
| C | `get_datasets(dataset_id)` |
| D | `ckan_package_show(server_url, id, include_tracking, response_format)` — documenta la semántica `issued`/`modified` vs `metadata_created`/`metadata_modified` |
| E | `ckan_package_show(id)` |
| F | `zurich_get_dataset(dataset_id)` |
| G | `get_dataset_info(dataset_id)` — incluye licencia y endpoint de API |

**`listar_distribuciones(id)`** — sólo uno tiene herramienta dedicada.

| | Equivalente |
|---|---|
| A · B · C · F | 🟡 Sin herramienta propia: las distribuciones viajan dentro del detalle. En A, truncadas a 10 |
| D | ✅ `ckan_list_resources(server_url, id, format_filter, response_format)` — devuelve nombre, id, formato, tamaño, bandera de DataStore y URL de descarga |
| E | 🟡 `ckan_resource_show(id)` es por recurso individual y exige conocer su id de antemano; no lista |
| G | 🟡 `list_dataset_fields(dataset_id)` lista **campos**, no distribuciones. Los formatos están en `get_dataset_info` |

**`consultar_sparql(query)`**

| | Equivalente |
|---|---|
| A · B · C · E · G | ❌ Ninguno lo expone. B documenta el endpoint de datos.gob.es en `MANUAL_API_DATOS.md` pero no lo envuelve. C lo tiene en el *roadmap* |
| D | ✅ `sparql_query(endpoint_url, query, limit, response_format)`. Sólo HTTPS, sólo `SELECT`, 15 s de timeout, `LIMIT` inyectado, salida truncada. **Es el modelo de referencia para el TODO 3.5** |
| F | 🟡 `zurich_sparql(query)` existe pero es un *stub* que devuelve un aviso; sólo se registra con `ZURICH_OPENDATA_ENABLE_SPARQL=1`, con la justificación escrita de no gastar contexto |
| J | ✅ `sparql_query_tool(query, graph)` sobre Fuseki, con prefijos auto-inyectados. Documentado como "último recurso cuando ninguna herramienta preconstruida cubre la consulta". **Sin límite de filas ni de tiempo en la firma** |

**`comparar_ciudades(tema)`** — nadie tiene la herramienta. Es la fila que salva el §4.

| | Situación |
|---|---|
| A · B · C · E · F · J | ❌ |
| D | 🟡 No hay herramienta de comparación, pero `server_url` por llamada más `ckan_find_portals(country, query, min_datasets, language, has_datastore, limit)` permiten que el **LLM** compare portales por sí mismo. La comparación no está en el esquema: está en el bucle del agente |
| G | 🟡 `related_datasets(dataset_id)` devuelve "datasets relacionados de **otros** portales"; la *skill* `radar-municipal` guía al modelo para retratar un municipio cruzando portales; `query_dataset(dataset_id, filters={"NOM_ENS": …})` filtra por ente municipal. De nuevo: lo orquesta el LLM, no la herramienta |

**Conclusión de la tabla.** De las cinco herramientas, **cuatro están cubiertas por al menos un
proyecto público**, y `ondata/ckan-mcp-server` cubre cuatro de las cinco él solo. La única que
nadie ha convertido en herramienta es `comparar_ciudades`, y dos proyectos ya la resuelven de
facto delegándola en el modelo. **Construir el §4 tal cual está escrito no produce novedad.**

Lo que sí produce novedad es la observación que emerge de la propia tabla: **cuando la comparación
se delega en el LLM, nadie ha medido si funciona.** Eso es una pregunta de investigación, no una
tarea de ingeniería.

---

## 4. ¿Qué queda realmente sin cubrir? Verificación de las cuatro afirmaciones

El §7 de `02-analisis-catalogos.md` sostenía cuatro cosas. Verificadas una a una, **ninguna se
sostiene en su formulación original** y dos hay que reescribirlas antes de la reunión.

### 4.1 "El banco de evaluación en español" — 🟡 sobrevive, pero hay que reformularlo

**Lo que se afirmaba:** *"no existe un benchmark en español de preguntas sobre catálogos de datos
abiertos con respuestas de referencia y trazas de herramientas"*.

**Lo verificado:** en español, sigue siendo cierto — no he encontrado ninguno. **Pero existe el
equivalente italiano**, publicado y con DOI de facto en HuggingFace: `aborruso/ckan-tool-selection`,
1.583 pares pregunta→herramienta, partición 1.270/313, CC BY-SA 4.0.

**Lo que sigue siendo del TFM, y hay que decirlo así:**

| Dimensión | ondata (italiano) | Banco del TFM |
|---|---|---|
| Origen de las preguntas | Sintéticas, generadas con Gemini 2.5 Flash por traducción inversa desde logs | Redactadas y verificadas a mano |
| Etiqueta | Nombre de la herramienta, y sólo el nombre | Herramienta **+ argumentos** + dataset de referencia + respuesta de referencia |
| Verificación del dataset correcto | No existe | Verificado a mano en el portal de origen (TODO 4.2) |
| Control de alucinación | No existe | ≥10 % de preguntas **sin respuesta posible** |
| Fiabilidad de la anotación | Una sola pasada automática | ≥20 % reanotado, κ reportado (TODO 4.3) |
| Cobertura de herramientas | Top-8 por frecuencia, el resto descartado | Las cinco del §4, incluidas las poco frecuentes |
| Idioma / ámbito | Italiano, portales CKAN cualesquiera | Español, seis municipios caracterizados |

Los propios autores reconocen el riesgo en su README: *"las preguntas 'inventadas' por Gemini
pueden no coincidir con cómo se expresan los usuarios reales — esto hay que validarlo en la fase
4"*. **Esa validación es exactamente lo que un banco anotado a mano aporta.**

**Cómo defenderlo:** el argumento ya no es *"soy el primero"*. Es *"el único método existente es
destilación sintética de un modelo grande, con las etiquetas empobrecidas a un nombre de
herramienta; yo aporto la referencia humana contra la que ese método se puede validar"*. Es un
argumento **mejor**, porque tiene un comparador.

### 4.2 "La pregunta del modelo pequeño en el navegador" — 🟡 sobrevive a medias

**Lo que se afirmaba:** *"Ningún proyecto de los anteriores la responde; todos asumen un modelo
grande en la nube. Sigue intacta."*

**Lo verificado:** falso en su segunda mitad. `ondata` ya entrenó un Qwen2.5-0.5B con LoRA
(Unsloth, rango 16, 3 épocas, 8,8 M de 502 M parámetros) para selección de herramienta MCP sobre
CKAN, con el modelo publicado y la comparativa contra Gemini 2.5 Flash escrita como fase 4. Su
hipótesis declarada: *"el modelo diminuto ajustado puede igualar o superar al modelo general
grande en esta tarea concreta"*. Y su dirección futura declarada es servirlo local vía GGUF/Ollama
a coste cero.

Esto es, casi literalmente, el plan de contingencia del TODO 6.3 del TFM.

**Lo que sigue intacto, verificado:**

- **La fase 4 de ondata no tiene resultados publicados a 25/07/2026.** El script existe, los
  números no. La pregunta sigue formalmente abierta, pero puede cerrarse en cualquier momento y
  por otros.
- **Ellos clasifican, no ejecutan.** Su modelo predice *un nombre de herramienta* entre ocho. No
  genera argumentos, no encadena llamadas, no cierra el bucle del agente. La métrica es
  `Accuracy@1` sobre una clasificación de 8 clases; la del TFM es corrección de traza **con
  argumentos** más fidelidad de la respuesta.
- **Nadie lo ha hecho en el navegador.** GGUF/Ollama no es WebGPU. El eje "cero instalación, cero
  coste, cero envío de datos a terceros, ejecutándose en la pestaña del ciudadano" no está tocado
  por ninguno de los ocho proyectos.
- **Nadie lo ha medido en español.**

**Cómo defenderlo:** dejar de vender "¿sirve un modelo pequeño?" —eso ya se está respondiendo— y
vender **"¿sirve un modelo pequeño *sin fine-tuning previo* y *en el navegador del usuario*, y
cuánto del fallo es del modelo y cuánto de los metadatos?"**. Y citar a ondata como trabajo
relacionado en vez de dejar que lo saque el tribunal.

### 4.3 "La capa multiciudad municipal" — ❌ **refutada. Este es el golpe.**

**Lo que se afirmaba:** *"Lo existente es o nacional (datos.gob.es, que empobrece metadatos) o
mono-ciudad (Zúrich). El eje comparación entre municipios sobre metadatos heterogéneos no está
cubierto."*

**Lo verificado:** falso. `Opendata.cat-MCP-Server` es multi-portal municipal, está desplegado,
tiene 15 portales con más de 3.044 datasets, cosecha semanal, catálogo centralizado, endpoint HTTP
público, paquete npm, y **cubre Barcelona y Reus, dos de las seis ciudades del corpus del TFM**.
Trae además una *skill* dedicada al retrato multi-portal de un municipio y un ejemplo de uso que
dice *"Compara Girona i Tarragona en dades obertes"*.

Y `ondata` resuelve el eje multi-portal de forma genérica y mejor argumentada: `server_url` como
argumento por llamada más `ckan_find_portals` sobre un registro de ~950 portales CKAN mundiales.

**Lo que sigue sin cubrir, y hay que ser preciso porque es poco:**

- **La comparación como objeto medido.** Ninguno de los dos evalúa si el LLM compara bien. No hay
  banco, ni métricas, ni análisis de errores.
- **La heterogeneidad semántica como hallazgo.** Opendata.cat **oculta** la heterogeneidad
  normalizando a un esquema propio por familia de API. El TFM propone **caracterizarla**: el
  TODO 2.4 (solapamiento de vocabulario de `keywords` entre pares de ciudades, ≥8 temas comunes)
  no lo hace nadie. Esa es la diferencia real entre construir un producto y hacer investigación.
- **Ámbito estatal.** Fuera de Cataluña no hay nada: Madrid, Málaga, Córdoba, Gijón y Zaragoza
  siguen sin capa multiciudad.
- **DCAT-AP-ES.** Ninguno valida contra el perfil ni trabaja sobre el grafo de metadatos. El
  TODO 2.2 sigue virgen.

**Cómo defenderlo:** esta afirmación **no se puede llevar tal cual a la reunión**. Hay que llevarla
corregida y con la corrección hecha por uno mismo, que es lo que separa a un alumno que lee el
prior art de uno que lo esquiva. La versión honesta: *"la capa multiciudad ya existe para Cataluña
y está bien hecha; lo que no existe es la evidencia de si funciona, y ese es mi objeto de estudio"*.

### 4.4 "La caracterización empírica del ecosistema municipal español" — 🟡 hay que estrechar la afirmación

**Lo que se afirmaba:** *"Los números de este documento (frescura, licencias, link rot, inflación
de catálogo, huecos de federación) no están publicados en ningún sitio que haya encontrado."*

**Lo verificado:** existe literatura académica española previa sobre portales municipales de datos
abiertos. En concreto **Royo-Montañés, S. & Benítez-Gómez, A. (2019). "Portales de datos abiertos.
Metodología de análisis y aplicación a municipios españoles". *Profesional de la Información*,
28(6). https://doi.org/10.3145/epi.2019.nov.09** — que propone una metodología de evaluación y
reporta que sólo el 40 % de las ciudades analizadas tiene portal, que la nota media no llega a 50,
que menos del 30 % define sus metadatos y que menos del 50 % ofrece descarga por API. ⚠ También hay
un trabajo en la *Revista del CLAD* sobre madurez de los portales locales españoles (no verificado)
y trabajos de evaluación de calidad de datos y metadatos basados en las especificaciones UNE
0077–0080:2023 (no verificado).

Además, hay **infraestructura de medición ya operativa**: el **MQA de data.europa.eu** puntúa
accesibilidad, reutilizabilidad, interoperabilidad, encontrabilidad y contextualidad de los
metadatos federados, y `ondata` ya lo expone como herramienta MCP (`ckan_get_mqa_quality`), aunque
restringido a `dati.gov.it`.

**Lo que sigue sin cubrir:**

- Los estudios previos son **de ciencias de la información**: rúbricas aplicadas a mano, orientadas
  a transparencia y rendición de cuentas. **No cosechan programáticamente** ni publican script.
- Ninguno mide lo que mide el índice local del TFM: **link rot**, **inflación de catálogo**,
  **licencia no declarada contada sobre la cosecha real** (los 145 de 145 de Córdoba), frescura por
  `fecha_modificacion_origen`, huecos de federación. Son métricas orientadas a *si una máquina
  puede consumir el catálogo*, no a *si un ciudadano puede leerlo*.
- El más citado es de **2019**. El ecosistema ha cambiado: DCAT-AP-ES es posterior.
- El MQA **no cubre lo municipal español** con granularidad de portal de origen.

**Cómo defenderlo:** la afirmación correcta es *"hay caracterización desde la ciencia de la
información y desde el MQA europeo, pero no hay una caracterización orientada a consumo automático,
reproducible con un script, y actualizada a DCAT-AP-ES, del nivel municipal español"*. Y hay que
citar a Royo-Montañés en el capítulo 3, no descubrirla en la defensa.

### 4.5 El hueco que sí es un hueco, y que no estaba en la lista

De los ocho proyectos revisados a fondo, **ninguno publica una evaluación de sus propias
herramientas con métricas de recuperación**. Ni precision@k, ni MRR, ni corrección de traza, ni
fidelidad. Lo más cerca es ondata, y sólo mide `Accuracy@1` sobre clasificación de herramienta.

Traducido: **hay ocho instrumentos y cero mediciones.** Nadie sabe si estas herramientas funcionan,
para qué preguntas fallan, ni cuánto del fallo es del modelo y cuánto de los metadatos.

Esa frase es la contribución del TFM, y es más fuerte que cualquiera de las cuatro originales.

---

## 5. Decisión: fork, dependencia o reimplementación

**Contexto que cambia el problema.** El índice local ya está implementado (`tfm/README.md`,
25/07/2026): 2.862 datasets, 23.390 distribuciones, 5 portales, 63,4 MB, FTS5 en español,
procedencia sellada en `ConectorCatalogo.cosechar()` con `ValueError` si falta, cosecha cortés con
`Crawl-Delay` y backoff. **La cosecha y el almacenamiento ya no se compran fuera.** Lo único que se
decide aquí es la capa de herramientas MCP.

Esto elimina de entrada la mayor parte del valor de reutilizar cualquiera de estos proyectos: **los
ocho son clientes de API remota.** Ninguno consulta un almacén local. Su código está estructurado
alrededor de `httpx`/`axios`, caché con TTL, reintentos y manejo de 503 — precisamente la
complejidad que el índice local hace innecesaria.

### 5.1 Fork — descartado

| Candidato | Por qué no |
|---|---|
| `ondata/ckan-mcp-server` | Es el mejor código del inventario, pero es **TypeScript** y el índice es Python con `sqlite3` de la biblioteca estándar. Un fork obligaría a reescribir el acceso a datos o a montar un puente entre procesos, y a mantener sincronía con un proyecto que publica varias versiones por semana (v0.4.112 el mismo día de la consulta). Divergiría en un mes |
| `malkreide/zurich-opendata-mcp` | El más cercano en stack (Python 3.11, FastMCP, Pydantic 2) y el mejor en calidad de errores. Pero está atado a Zúrich en la configuración, en los `Enum` de categorías, en los nombres de las 26 herramientas y **en el idioma: todas las descripciones están en alemán**. Un fork implicaría traducir y renombrar todo, con lo que se pierde la capacidad de recibir sus mejoras — que es lo único que justifica un fork |
| `AlbertoUAH/datos-gob-es-mcp` | MIT y en español, pero es un **hub nacional** de cinco APIs estatales. Su modelo de datos es la respuesta de `apidata`, no un índice propio. Forkearlo sería quedarse con la parte que sobra y tirar la que importa |
| `ondics/ckan-mcp-server` | **MPL-2.0.** Copiar un fichero arrastra la licencia a ese fichero. Es el único obstáculo legal real del inventario, y no compensa: es también el proyecto más pobre |
| MCP oficial de datos.gob.es | **Sin fichero LICENSE.** El README declara CC BY 4.0, que no es una licencia de software: no concede permisos de patente ni excluye garantías, y su compatibilidad con licencias de software es discutida. Además el código tiene el bug de paginación descrito en la ficha A. No forkeable en la práctica |

### 5.2 Dependencia — descartada para el núcleo, útil en un caso

**Descartada para las cinco herramientas del §4.** Depender de cualquiera de estos servidores
significa que cada evaluación del banco golpea las APIs municipales en vivo. Eso reintroduce
exactamente el riesgo que el TODO 3.1 eliminó: portales que devuelven 503 aleatoriamente, Málaga
con `Crawl-Delay: 10`, Reus devolviendo 429 en la primera petición. **Sin índice local la
evaluación no es reproducible**, y sin reproducibilidad no hay fase 5.

**Un caso donde sí conviene una dependencia:** `consultar_sparql`, si se implementa. Ninguno de los
mecanismos de salvaguarda de ondata (sólo `SELECT`, sólo HTTPS, timeout, `LIMIT` inyectado,
truncado) merece reescribirse desde cero, y su implementación es MIT.

**Un caso donde conviene una dependencia de otro tipo:** usar los proyectos existentes **como
baselines del experimento A**. Ejecutar el banco de evaluación contra `ondata/ckan-mcp-server`
apuntando a Barcelona y contra el MCP del TFM sobre el mismo Barcelona, con el mismo modelo, es un
experimento barato, publicable y desarma de golpe la pregunta incómoda del TODO 8.4 ("¿qué aporta
lo tuyo frente al MCP de datos.gob.es?"). Esto no es una dependencia de código: es una dependencia
experimental, y es la mejor idea que sale de este documento.

### 5.3 Reimplementación — **recomendada**

Reimplementar la capa MCP en Python sobre el índice local, **con préstamo explícito y citado de
diseño**. Justificación por los cuatro criterios pedidos:

**Licencia.** Los proyectos de los que interesa tomar diseño —zurich, ondata, AlbertoUAH, mjanez,
Opendata.cat, cibelex— son todos **MIT**. Tomar patrones y fragmentos con atribución es limpio y no
contamina la licencia del TFM. Se evita `ondics` (MPL-2.0) y el notebook oficial (CC BY, sin
LICENSE). El repositorio del TFM puede salir MIT o Apache-2.0 sin conflicto; el **banco de
evaluación**, en cambio, sigue atado a `by-sa-40` de Málaga (TODO 4.4), que es asunto aparte.

**Calidad del código.** El código a copiar existe y es bueno, pero es *de acceso remoto*. Los
patrones que valen —modelos Pydantic con `extra="forbid"`, `ToolAnnotations`, salida dual
markdown/JSON, mensajes de error accionables por código HTTP— se transcriben en cien líneas. Lo que
no vale es el 70 % restante: pools de conexiones, caché con TTL, backoff, límites de
descompresión. El índice local ya resolvió ese problema.

**Mantenimiento.** Cuatro de los ocho proyectos están congelados o abandonados (MCP oficial,
mjanez, ondics a medias, CiudadesAbiertas). De los activos, ondata se mueve demasiado rápido para
seguirlo y zurich es mono-ciudad. **Ninguno ofrece la estabilidad que un TFM de 15 ECTS necesita
durante 12 meses.** Un fork mal mantenido es peor que código propio: en la defensa hay que
responder por él igual, sin haberlo escrito.

**Ajuste al caso municipal.** Es el criterio decisivo. Los tres ejes del TFM —índice local,
multiciudad española con metadatos heterogéneos, y procedencia obligatoria en cada respuesta
(TODO 3.2, RD 1495/2011 art. 8)— **no los cumple ninguno**. El requisito de que toda respuesta
lleve `url_origen`, `licencia`, `fecha_modificacion_origen` y `fecha_sincronizacion`, con un test
que falle si falta, no está en ningún proyecto revisado: el MCP oficial ni siquiera devuelve
licencia en la búsqueda. Ese requisito atraviesa todos los modelos de salida, así que adaptarlo
sobre código ajeno cuesta más que escribirlo bien desde el principio.

### 5.4 Qué se copia exactamente, y de quién

Esto va al capítulo 4 de la memoria como decisiones de diseño con su procedencia.

**De `zurich-opendata-mcp` (MIT):**

- Estructura: `app.py` con la instancia FastMCP compartida, `tools/<familia>.py` que se registran
  por efecto lateral del decorador al importarse, `server.py` como punto de entrada. Es lo más
  limpio que hay para 5–10 herramientas.
- Un modelo Pydantic de entrada por herramienta, con `ConfigDict(str_strip_whitespace=True,
  extra="forbid")` y `ge`/`le`/`min_length`/`max_length` en cada campo. `extra="forbid"` es
  especialmente valioso para el TFM: **convierte un argumento inventado por el modelo en un error
  de validación observable**, que es justo lo que hay que contar en la métrica de corrección de
  traza del §6.
- `ToolAnnotations(readOnlyHint, destructiveHint, idempotentHint, openWorldHint)` en todas.
- `Annotated[CallToolResult, ModeloDeSalida]`: markdown para el humano, JSON estructurado para el
  arnés de evaluación, en la misma respuesta. Resuelve de un golpe el formato de traza del TODO 3.6.
- `handle_api_error(e, context)`: traducción del fallo a mensaje accionable, log con `exc_info`,
  `is_error=True`. Aquí los fallos serán del índice, no de la red, pero el patrón sirve igual.

**De `ondata/ckan-mcp-server` (MIT):**

- **La ciudad como argumento de cada herramienta**, no como servidor separado ni variable de
  entorno. Es la decisión que hace posible `comparar_ciudades` sin herramienta dedicada, y la que
  mjanez y ondics no tomaron. Documentarla como alternativa elegida frente al patrón "un servidor
  por portal".
- Las salvaguardas de `sparql_query` completas, si se implementa el TODO 3.5.
- `response_format: 'markdown' | 'json'` como argumento explícito.
- La documentación de la **semántica de fechas** en la descripción de la herramienta
  (`issued`/`modified` del publicador vs `metadata_created`/`metadata_modified` del registro CKAN,
  y qué significa cada una en un agregador frente a un portal de origen). Esto es directamente
  aprovechable para el criterio de procedencia del TODO 3.2 y es un detalle que sólo se aprende
  leyendo código ajeno.

**De `Opendata.cat-MCP-Server` (MIT):**

- Las *skills* como recursos MCP (`skill://<nombre>/SKILL.md`) más prompts-puente. Es una vía
  barata de guiar al modelo en las consultas multiciudad **sin** meter la lógica en la herramienta,
  y por tanto **medible como variable experimental**: ejecutar el banco con y sin la skill es un
  ablation study gratis.
- `related_datasets(dataset_id)` entre portales como precedente de `comparar_ciudades`.

**De `cibelex-mcp-fuseki` (MIT):**

- La taxonomía de familias de herramienta (búsqueda / *join* / recorrido / contexto /
  introspección) como alternativa considerada a la lista plana del §4.
- `sparql_query_tool` documentada como *"último recurso cuando ninguna herramienta preconstruida
  cubre la consulta"*. Buena redacción para la descripción de la herramienta: reduce llamadas
  espurias.

**Qué NO se copia y por qué:** nada de `ondics` (MPL-2.0); nada del MCP oficial (sin LICENSE, y con
el bug de paginación); ninguna capa de caché/reintento/pool (el índice local la hace innecesaria);
y no se implementa `consultar_sparql` como herramienta libre en la v1 — ver abajo.

### 5.5 Consecuencia directa para el TODO 3.5 (`consultar_sparql`)

El prior art da un argumento que no estaba disponible cuando se escribió el TODO:

- **De tres proyectos que exponen SPARQL, uno lo tiene desactivado por decisión de diseño** (zurich,
  por coste de contexto y endpoint sin datos), uno lo restringe con cuatro salvaguardas (ondata) y
  uno lo deja crudo pero sobre un grafo propio y controlado (cibelex, Fuseki local).
- El índice local del TFM es **SQLite, no un triplestore**. Exponer `consultar_sparql` sobre él
  obligaría a materializar un grafo RDF sólo para esa herramienta.

**Recomendación para el TODO 3.5:** no implementar `consultar_sparql` sobre el índice local en la
v1. Si se implementa, que sea como **pasarela al endpoint SPARQL de datos.gob.es**, con las cuatro
salvaguardas de ondata, y **medida**: comparar la tasa de acierto del agente con y sin ella. Un
resultado del tipo *"exponer SPARQL libre a un LLM empeora la precisión y multiplica la latencia"*
es publicable y responde a una pregunta que el ecosistema tiene abierta.

---

## 6. Reformulación propuesta, actualizada con lo que se ha encontrado

La del §7 de `02-analisis-catalogos.md` sigue siendo correcta en dirección, pero ahora se puede
formular con más filo porque hay evidencia:

> Existen al menos ocho servidores MCP públicos sobre catálogos de datos abiertos. Entre todos
> cubren cuatro de las cinco herramientas que este plan proponía construir. **Ninguno publica una
> sola métrica de si funcionan.**
>
> El TFM deja de construir un instrumento y pasa a construir **la primera medición**: un banco de
> evaluación en español anotado a mano, con argumentos de herramienta y con casos sin respuesta, y
> un experimento que separe **cuánta de la dificultad de consultar datos abiertos municipales viene
> del modelo y cuánta de la calidad de los metadatos** — con la caracterización empírica del corpus
> como variable independiente, no como anécdota.
>
> El servidor MCP se reimplementa sobre el índice local porque hace falta un instrumento
> controlado, y los ocho existentes se usan como **baselines del experimento**.

Tres consecuencias operativas:

1. **La fase 4 (banco) sube a contribución principal** — ya estaba escrito en el TODOS.md; ahora
   está justificado con evidencia.
2. **La fase 5 gana un experimento**: además de comparar modelos, comparar **servidores MCP** sobre
   el mismo banco y el mismo modelo (el del TFM vs `ondata` vs el MCP oficial de datos.gob.es,
   sobre Barcelona y Madrid). Es barato y es lo que convierte el prior art en resultado.
3. **La fase 6 se reformula**: no "¿sirve un modelo pequeño?", sino "¿sirve **en el navegador, sin
   fine-tuning previo**, y dónde está el límite?" — citando a ondata como el trabajo que responde
   la versión con fine-tuning.

### 6.1 Las tres preguntas incómodas del TODO 8.4, con respuesta preparada

**"¿Qué aporta esto frente al MCP de datos.gob.es?"** — Que aquel es un notebook didáctico,
congelado desde enero de 2026, cuya herramienta de búsqueda devuelve como mucho 5 resultados por un
error de paginación y no reporta ni licencia ni procedencia. Y que este trabajo **lo mide**, en vez
de suponerlo. La cifra concreta de su precision@k sobre el banco va en el capítulo 6.

**"¿Y frente a Opendata.cat, que ya hace multiciudad?"** — Que Opendata.cat es un producto
excelente y sin evaluación publicada, que normaliza la heterogeneidad de metadatos en lugar de
caracterizarla, y que cubre 2 de las 6 ciudades del corpus. Este trabajo mide si esa aproximación
funciona y cuantifica la heterogeneidad que aquella oculta.

**"¿Y frente al modelo pequeño ajustado de ondata?"** — Que ellos clasifican el nombre de la
herramienta entre ocho clases, en italiano, con datos sintéticos, y con los resultados aún sin
publicar a fecha de este documento. Este trabajo evalúa el bucle completo del agente —herramienta
**más argumentos**, más fidelidad de la respuesta— en español, con referencia humana, y en el
navegador.

---

## 7. Fuentes

Todas consultadas el **25/07/2026**. ✅ = verificado leyendo el repositorio o el documento.
⚠ = sólo resultado de búsqueda o página divulgativa, no verificado en la fuente primaria.

**Repositorios de código**

- ✅ https://github.com/Admindatosgobes/Laboratorio-de-Datos — subcarpeta `Data Science/Agente Conversacional con MCP server`; notebook y README leídos íntegros; historial de commits de esa ruta
- ✅ https://datos.gob.es/en/conocimiento/conversational-agent-mcp-server-datosgobes — publicado 12/01/2026, actualizado 09/04/2026
- ✅ https://github.com/AlbertoUAH/datos-gob-es-mcp — MIT, último commit 15/03/2026
- ✅ https://github.com/mjanez/ckan-mcp-server — MIT, último commit en `main` 25/11/2025
- ✅ https://github.com/ondata/ckan-mcp-server — MIT, v0.4.112, push 25/07/2026; carpetas `evals/` y `data/` leídas
- ✅ https://github.com/ondics/ckan-mcp-server — MPL-2.0, v1.1.2, último commit 24/04/2026
- ✅ https://github.com/malkreide/zurich-opendata-mcp — MIT, v0.5.1, 24/07/2026
- ✅ https://github.com/xaviviro/Opendata.cat-MCP-Server — MIT, v0.6.0 (15/07/2026), 21 estrellas, 61 commits
- ✅ https://github.com/CiudadesAbiertas/CiudadesAbiertas-API — EUPL-1.2, último push 21/06/2022; autoría de Óscar Corcho en el README
- ✅ https://github.com/AyuntamientoMadrid/AgenticCity — Apache-2.0, sólo LICENSE, 1 commit, 24/04/2025
- ✅ https://github.com/AyuntamientoMadrid/cibelex-mcp-fuseki — MIT, mayo 2026, 3 commits, 22 herramientas en código
- ✅ https://github.com/orgs/ayuntamientomadrid/repositories — inventario completo de los 9 repositorios públicos

**Datasets y modelos**

- ✅ `aborruso/ckan-tool-selection` en HuggingFace — referenciado desde `evals/README.md`, licencia CC BY-SA 4.0 según `data/LICENSE`
- ✅ `aborruso/ckan-tool-selector` en HuggingFace — Qwen2.5-0.5B-Instruct + LoRA, referenciado desde `evals/README.md`
- ✅ LoRO (Local Regulations Ontology) v1.0, 07/05/2026, CC BY 4.0 — https://doi.org/10.5281/zenodo.20076577 · sin afiliación UPM/OEG entre los 13 autores
- ⚠ `MAIA-Madrid-IA/cibelex-graph-core-sampler` en HuggingFace — citado en el README de cibelex, no consultado

**Literatura**

- ✅ Royo-Montañés, S. & Benítez-Gómez, A. (2019). "Portales de datos abiertos. Metodología de
  análisis y aplicación a municipios españoles". *Profesional de la Información*, 28(6).
  https://doi.org/10.3145/epi.2019.nov.09 — ficha del artículo consultada; texto completo no leído
- ⚠ "Hacia la madurez de los portales de datos públicos abiertos en el sector público. Un análisis
  comparado del nivel local de gobierno en España", *Revista del CLAD Reforma y Democracia* — sólo
  resultado de búsqueda
- ⚠ Trabajos de evaluación de calidad de datos y metadatos con UNE 0077/0078/0079/0080:2023 — sólo
  resultado de búsqueda

**No verificado, pendiente de revisar si se amplía el inventario (TODO 1.3 pide ≥6 servidores MCP)**

- ⚠ https://github.com/stucchi/italy-opendata-mcp — 7 herramientas sobre la jerarquía administrativa italiana
- ⚠ https://github.com/ceami/opendata-mcp — portal de datos públicos de Corea
- ⚠ https://github.com/datagouv/datagouv-mcp — MCP del gobierno francés; citado como inspiración por Opendata.cat
- ⚠ https://github.com/agID/ckan-mcp-server — reutilización de ondata por la agencia digital italiana
- ⚠ MAIA / "Agentic City" del Ayuntamiento de Madrid en madrid.es y prensa (Computing, Computer
  Weekly, Revista Cloud Computing): adjudicación a Atos en marzo de 2025, RAG/LLM/LangChain sobre
  multicloud, MVP agéntico de mantenimiento viario. **Ninguna fuente primaria municipal verificada
  y ningún código público asociado**

---

## 8. Estado de los criterios DONE IS

**TODO 0.1**

- [x] `docs/03-prior-art.md` existe, con ficha por proyecto: herramientas expuestas, **firma exacta
      extraída del código**, stack, licencia y fecha del último commit — §2, fichas A–J. Se amplió
      el alcance de 3 a 10 proyectos porque la búsqueda destapó dos que no estaban en el inventario
      (`Opendata.cat-MCP-Server` y `cibelex-mcp-fuseki`).
- [x] Tabla explícita de qué herramientas del §4 quedan cubiertas y cuáles no — §3, con detalle por
      fila y firma equivalente.
- [x] Decisión escrita y justificada: **reimplementación** con préstamo de diseño citado — §5, con
      los cuatro criterios (licencia, calidad, mantenimiento, ajuste al caso municipal) y el
      inventario de qué se copia de quién.

**TODO 0.2**

- [x] Sección que responde qué es, si está vivo, si es público y si solapa, para "Madrid Agentic
      City" (§2.I) y `cibelex-mcp` (§2.J).
- [x] Alternativa de posicionamiento escrita antes de la reunión — §2.J, cuatro puntos.

**Pendiente y no cubierto por este documento:** el TODO 0.3 (reunión con Óscar) y la corrección del
§7 de `docs/02-analisis-catalogos.md`, cuyas afirmaciones 3 y 4 quedan **refutadas en parte** por el
§4 de este documento y deberían actualizarse antes de que ese texto alimente el capítulo 3.
