---
type: note
title: Etapa 2 — explorar el contenido de los datasets
date: 2026-07-25
tags: [tfm, mcp, datos-abiertos, alcance, datastore]
status: respuesta al correo de Óscar Corcho del 25/07/2026
---

# Etapa 2: explorar el contenido de los datasets

Óscar plantea dos etapas, y son dos problemas distintos:

> **Etapa 1** — *"dime qué datasets contienen información sobre municipios en España"*.
> **Etapa 2** — *"dime cuántos municipios tiene España basado en este dataset, o cuántos
> distritos tiene Madrid, o cuál es el distrito con más estaciones de BiciMad"*.

La etapa 1 está construida y funcionando (`datosabiertos/mcp/`, 4 herramientas sobre 2.862 datasets).
La etapa 2 **no está cubierta en absoluto** y no es una extensión menor: cambia el
almacenamiento, las herramientas, las métricas y una de las conclusiones del análisis de
julio. Este documento mide cuánto.

## 1. Lo que hicimos: responder de verdad a la pregunta de BiciMad

Antes de diseñar nada, respondimos el ejemplo más difícil de los tres.
Reproducible: `python3 research/etapa2_bicimad_distritos.py`.

**Respuesta: Centro, con 59 de 631 estaciones.** Le siguen Fuencarral-El Pardo (44),
Salamanca (42), Arganzuela (40) y Moncloa-Aravaca (39). Las 631 estaciones se asignan a los
21 distritos sin ninguna huérfana.

Lo interesante no es la respuesta, es lo que costó:

| Paso | Qué pasó |
|---|---|
| 1. Localizar el dataset | ✅ La etapa 1 lo encuentra: `buscar_datasets("estaciones bicimad", ciudad="madrid")` |
| 2. Descargar las estaciones | La distribución GeoJSON la sirve **`datos.emtmadrid.es`**, otro host. **El CSV y el KML del mismo dataset fallan**; solo vive el GeoJSON |
| 3. Ver si trae distrito | ❌ **No lo trae.** Campos: `OBJECTID, Activate, Address, PosicionSTR, Ligth, Name, NoAvailable, number, TotalBases, State, POINT_X, POINT_Y` |
| 4. Buscar los distritos | Segundo dataset: `Distritos municipales de Madrid`, 7 distribuciones |
| 5. Obtener los polígonos | KML de 387 KB con 21 polígonos, **sin nombres**: solo el código, y sin `ExtendedData` |
| 6. Obtener los nombres | Tercera distribución (CSV, latin-1 con BOM) con `COD_DIS → NOMBRE` |
| 7. Cruzar | Punto-en-polígono por lanzamiento de rayos, y join por código |

**Dos datasets, tres distribuciones, tres formatos, un cruce espacial y un join por código.**
Ninguna de las cuatro herramientas de la fase 3 sabe hacer los pasos 3 a 7, y —esto importa—
**el datastore de CKAN tampoco**: el GeoJSON de BiciMad no está cargado en él.

Los tres ejemplos de Óscar no son igual de difíciles, y esa escala es útil:

| Pregunta | Qué exige | ¿Cubierta hoy? |
|---|---|---|
| "¿Cuántos distritos tiene Madrid?" | Un `COUNT` sobre una tabla | No, pero es fácil: datastore |
| "¿Cuántos municipios tiene España según este dataset?" | `COUNT DISTINCT` + elegir bien el dataset | No; el riesgo es la elección, no el cálculo |
| "¿Qué distrito tiene más estaciones de BiciMad?" | Join espacial entre dos datasets y tres distribuciones | No, y ni el datastore ni la API tabular francesa lo cubren |

## 2. Prior art: cómo lo resuelve data.gouv.fr

El servidor MCP que sugiere Óscar existe y es oficial: **`datagouv/datagouv-mcp`**,
desarrollado por Etalab / data.gouv.fr, licencia MIT, transporte **Streamable HTTP** (sin
stdio ni SSE), con **instancia pública abierta en `https://mcp.data.gouv.fr/mcp`**. Hay
además uno comunitario anterior, `huextrat/data-gouv-mcp`.

Sus herramientas, separadas por etapa:

| Etapa | Herramientas |
|---|---|
| **1 · catálogo** | `search_datasets(query, page, page_size)`, `get_dataset_info`, `list_dataset_resources`, `get_resource_info` (indica **si la API tabular está disponible** para ese recurso), `search_organizations`, `search_dataservices`, `get_dataservice_info`, `get_dataservice_openapi_spec`, `get_metrics` |
| **2 · contenido** | **`query_resource_data(resource_id, page=1, page_size=20, max 200)`** — *"consulta datos de un recurso vía la API tabular. Trae filas para responder preguntas"* |

Tres decisiones suyas que conviene copiar y una que no:

- **Copiar: la etapa 2 es UNA herramienta, no diez.** Todo el acceso a contenido pasa por
  `query_resource_data`. Menos superficie para que el modelo se equivoque.
- **Copiar: `get_resource_info` dice si el recurso es consultable** antes de intentarlo. El
  agente sabe si puede preguntar por filas o si tiene que rendirse. En España esto es aún más
  necesario, porque la cobertura del datastore es irregular (§3).
- **Copiar: límites explícitos** (CSV ≤ 100 MB, XLSX ≤ 12,5 MB, ≤ 200 filas por página) y el
  consejo de paginar o bajarse el fichero crudo por encima de cierto tamaño.
- **No copiar tal cual: no hay nada geoespacial.** La API tabular devuelve filas. La pregunta
  de BiciMad no se responde con `query_resource_data`. Es un hueco real del estado del arte,
  no un descuido nuestro.

Que exista una instancia pública nacional en Francia y ninguna en España es, además, un
argumento de contribución para el Encuentro Nacional de Datos Abiertos.

## 3. El equivalente español existe, y funciona mejor de lo esperado

La API tabular francesa tiene análogo: **el datastore de CKAN**
(`datastore_search` y `datastore_search_sql`). Comprobado el 25/07/2026 con recursos reales
del corpus, 4 por portal:

| Portal | Datastore | Evidencia |
|---|---|---|
| **Madrid** | ✅ | 4/4 recursos con filas. Uno de ellos, 51.110 filas con campos tipados (`DISTRITO_COD`, `DISTRITO_DESC`…) |
| **Barcelona** | ✅ | 4/4. Campos `Codi_Districte`, `Nom_Districte`, `Codi_Barri` |
| **Córdoba** | ✅ | 4/4, en `/ckan/api/3/action` (ruta distinta al resto) |
| **Málaga** | ❌ | HTTP 409: la extensión no está activa |
| **Reus** | ❌ | No responde en esa ruta |

Esto cambia el cálculo de julio. **Para las preguntas tabulares no hay que duplicar ningún
dato**: se consultan en el portal, con filtros y agregación en el servidor, y sin
descargarse los 262 GB de Madrid. El datastore incluso acepta SQL.

Pero abre tres problemas nuevos, y son los interesantes:

1. **Cobertura irregular.** Dos de los cinco portales del corpus no lo tienen. Y de los que
   sí, no todos los recursos están cargados: el GeoJSON de BiciMad, sin ir más lejos, no
   está. Hay que **medir la cobertura real**, no suponerla.
2. **Consultar en vivo reintroduce el problema del §4.2 del análisis de julio.** Madrid
   devuelve 403 a la descarga programática y Barcelona limita por concurrencia. Si la
   etapa 2 consulta en vivo, la evaluación deja de ser reproducible — que es exactamente el
   argumento por el que existe el índice local. Habrá que cachear las respuestas del
   datastore, con su fecha de sincronización.
3. **Lo geoespacial no lo cubre nadie.** Ni el datastore, ni la API tabular francesa, ni
   ninguno de los diez proyectos de `docs/03-prior-art.md`.

## 4. Qué hay que cambiar

### 4.1 Herramientas nuevas (fase 3)

Siguiendo a data.gouv.fr, poca superficie:

- **`describir_distribucion(id_distribucion)`** — ¿es consultable? ¿Por datastore, por
  descarga directa, o por ninguna vía? ¿Qué columnas y de qué tipo? Es el
  `get_resource_info` francés y **debe ir antes** de cualquier intento de consulta.
- **`consultar_datos(id_distribucion, filtros?, columnas?, limite=50)`** — filas, vía
  datastore cuando existe y vía fichero cacheado cuando no. Una sola herramienta.
- **`agregar_datos(id_distribucion, operacion, columna, agrupar_por?)`** — `COUNT`,
  `COUNT DISTINCT`, `SUM`, `MAX`. Cubre los dos primeros ejemplos de Óscar sin que el
  modelo tenga que traerse las filas y contarlas él, que es donde alucina.
- **`cruzar_geografico(...)`** — punto-en-polígono. Es la que no tiene precedente. Antes de
  implementarla hay que decidir si entra en el TFM o se queda como trabajo futuro: es la
  más cara y la que más se aleja de la pregunta de investigación.

### 4.2 Almacenamiento

La conclusión de julio —*"metadatos sí, datos no"*— **necesita un matiz**, no una
rectificación:

- **Metadatos: réplica completa.** Sin cambios. 100-150 MB.
- **Datos tabulares: no replicar, consultar por datastore y cachear la respuesta.** Con
  `fecha_sincronizacion`, como todo lo demás.
- **Datos sin datastore: descarga bajo demanda con caché y tope de tamaño.** El GeoJSON de
  BiciMad son 255 KB; los polígonos de distritos, 387 KB. La geometría municipal es pequeña.
- **Sigue sin haber motivo para bajarse los 262 GB de Madrid.** El 1 % de recursos más
  grandes concentra 85 GB y ninguna pregunta de las de Óscar los toca.

### 4.3 Banco de evaluación

Es el cambio de más calado, porque afecta a la contribución principal. Las 15 preguntas
actuales son **todas de etapa 1**. La etapa 2 exige:

- Un campo nuevo en el esquema: `etapa` (1 = catálogo, 2 = contenido).
- **Respuesta de referencia numérica y verificable** ("Centro, 59 estaciones"), no textual.
  Esto es una ventaja: las preguntas de etapa 2 se corrigen solas, sin LLM-juez ni segundo
  anotador. La métrica de fidelidad del §6 del plan se vuelve mucho más dura.
- Fecha de corte: la respuesta a "cuántas estaciones" cambia con el tiempo. Hay que anclar
  cada respuesta a la `fecha_sincronizacion` del dato, o el banco caduca solo.

### 4.4 Y una ventaja inesperada para la pregunta de investigación

La etapa 2 **refuerza** la hipótesis del modelo pequeño. Si `agregar_datos` hace el `COUNT`
en el servidor, el modelo no tiene que contar: solo elegir la herramienta y leer un número.
Eso es justo lo que un modelo de 1-3 B puede hacer, y donde un modelo grande no debería
sacar ventaja. Si el experimento lo confirma, es un resultado con un mensaje claro:
*el trabajo va en las herramientas, no en el tamaño del modelo.*

## 5. Qué llevar a la reunión

1. **Enseñar la respuesta de BiciMad y lo que costó.** Es la mejor prueba de que la etapa 2
   se entiende, y el desglose de los 7 pasos vale más que cualquier diseño en abstracto.
2. **Preguntar hasta dónde llega el alcance.** Las preguntas tabulares son asumibles. El
   cruce geoespacial es otro TFM. Con 15 ECTS hay que elegir, y la elección es suya.
3. **Proponer que el banco cubra las dos etapas** con respuestas numéricas verificables en
   la etapa 2, y enseñar que eso quita de encima el LLM-juez.
4. **Contarle el hallazgo del datastore** (3 de 5 portales) y el del idioma (Barcelona y
   Reus publican en catalán, así que "contaminacion" da 0 resultados y "contaminació" da 2).
5. **Contarle también que la afirmación de novedad multiciudad se cayó** al verificar el
   prior art (`docs/03-prior-art.md` §4.3). Mejor decirlo uno mismo.

## 6. Fuentes

- [datagouv/datagouv-mcp](https://github.com/datagouv/datagouv-mcp) · [instancia pública](https://mcp.data.gouv.fr/mcp) · [experimentación de data.gouv.fr](https://www.data.gouv.fr/posts/experimentation-autour-dun-serveur-mcp-pour-datagouv) · [huextrat/data-gouv-mcp](https://github.com/huextrat/data-gouv-mcp)
- Datastore CKAN comprobado el 25/07/2026 en `datos.madrid.es`, `opendata-ajuntament.barcelona.cat` y `datosabiertos.cordoba.es`.
- Cruce espacial reproducible: `research/etapa2_bicimad_distritos.py`.
