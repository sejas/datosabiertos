---
type: note
title: Análisis de catálogos municipales de datos abiertos en España
date: 2026-07-25
tags: [tfm, datos-abiertos, dcat, ckan, mcp, analisis]
status: borrador — alimenta la fase 2 y el cap. 3 de la memoria
---

# Análisis de catálogos municipales de datos abiertos en España

Medición hecha el **25 de julio de 2026** contra las APIs en producción. Todo lo que se
afirma aquí con números procede de los scripts de `research/`, no de estimaciones a ojo.
Reproducible con `python3 research/harvest.py && python3 research/sample.py && python3 research/score.py`.

## 0. Resumen ejecutivo

1. **107 ayuntamientos** publican datos federados en datos.gob.es, con **9.492 datasets**.
   No son "4-6 ciudades": el censo real es mucho mayor, pero **86 de los 107 tienen menos de
   50 datasets** y 68 de ellos son municipios de la provincia de Córdoba sobre una plataforma
   compartida. La diversidad real de plataformas es ~10, no 107.
2. **Los metadatos son diminutos: 58 MB** de JSON en crudo para los 16 portales cosechados
   (5.131 datasets, 35.400 recursos). Extrapolado a los 107 municipios: **~100–150 MB, <30 MB
   comprimidos**. Los datos en sí son **~0,4–0,5 TB**. Son dos problemas distintos.
3. **Duplicar los metadatos no es opcional, es obligatorio.** Madrid devolvió **403 en 9 de 12**
   descargas programáticas incluso serializadas a 1,5 s; Barcelona devolvió **503 en 28 de 30**
   con 10 peticiones concurrentes (y 8/8 correctas al serializar a 3 s). Un agente que consulte
   en vivo fallará de forma no determinista.
4. **La licencia no es un obstáculo: el 93,7 % de los datasets es CC-BY o equivalente.** El
   problema no es el permiso, es la **procedencia**: hay que conservar fecha de actualización,
   fuente y licencia, y no presentar la copia como si fuera la fuente viva.
5. **Aviso serio sobre la novedad del TFM:** el "servidor MCP sobre catálogos españoles" **ya
   existe**, y al menos cuatro veces. Hay que rehacer el planteamiento del plan (§7 de este doc).

## 1. Método

| Paso | Cómo | Salida |
|---|---|---|
| Censo de municipios | SPARQL sobre `datos.gob.es/virtuoso/sparql`, filtrando publicadores con DIR3 `L01*` (código de entidad local) | 107 municipios + nº datasets |
| Identificación de portales | `SAMPLE(?accessURL)` por publicador → host real de cada portal | 10 familias de plataforma |
| Cosecha de catálogos | `package_search` paginado en 16 portales CKAN | 5.131 datasets, 35.400 recursos, 58 MB |
| Volumen de datos | Suma de `resource.size` declarado + validación por muestreo | 392 GB declarados |
| Fiabilidad y tamaño real | 30 recursos aleatorios por portal, `Range: bytes=0-0`, concurrente y serializado | % enlaces vivos, error del tamaño declarado |
| Licencias | Histograma de `license_id` sobre los 5.131 datasets | 93,7 % CC-BY o equivalente |

Sesgo conocido: solo se cosecharon a fondo los portales CKAN. Los ad-hoc (Zaragoza, Gijón,
Vitoria, Bilbao, Santander, Lorca, Cáceres) tienen puntuación **inferida** a partir del tipo de
API y del recuento federado, no medida. Están marcados como tales en §5.

## 2. Censo: quién publica y sobre qué plataforma

**107 municipios, 9.492 datasets.** Los 27 con portal propio identificable:

| # | Municipio | Datasets | Portal | Familia |
|---|---|---:|---|---|
| 1 | Málaga | 1.369 | datosabiertos.malaga.eu | CKAN |
| 2 | Arganda del Rey | 968 | datosabiertos.ayto-arganda.es | CKAN |
| 3 | Gijón | 783 | opendata.gijon.es | ad-hoc (`descargar.php`) |
| 4 | Madrid | 672 | datos.madrid.es | CKAN + DCAT |
| 5 | Barcelona | 555 | opendata-ajuntament.barcelona.cat | CKAN |
| 6 | Torrent | 342 | datosabiertos.torrent.es | CKAN |
| 7 | Bilbao | 341 | bilbao.eus | web/ad-hoc |
| 8 | Valencia | 296 | geoportal.valencia.es | ArcGIS REST |
| 9 | Zaragoza | 228 | zaragoza.es/sede/servicio | REST propio |
| 10 | Lorca | 204 | datos.lorca.es | ad-hoc |
| 11 | Vitoria-Gasteiz | 197 | vitoria-gasteiz.org | ficheros estáticos |
| 12 | Alcobendas | 177 | datos.alcobendas.org | CKAN |
| 13 | Vigo | 148 | (RSS/turismo) | web/ad-hoc |
| 14 | Córdoba | 145 | datosabiertos.cordoba.es | CKAN |
| 15 | Terrassa | 125 | opendata.terrassa.cat | CKAN |
| 16 | Reus | 119 | opendata.reus.cat | CKAN |
| 17 | Cáceres | 116 | opendata.caceres.es | **SPARQL propio** (`GetData`) |
| 18 | Donostia | 108 | donostia.eus/datosabiertos | ArcGIS MapServer |
| 19 | Avilés | 107 | datos.aviles.es | CKAN |
| 20 | Sta. Cruz de Tenerife | 86 | santacruzdetenerife.es/opendata | CKAN |
| 21 | S.S. de los Reyes | 73 | *(accessURL = `google.com`)* | roto |
| 22 | Santander | 58 | datos.santander.es | REST propio |
| 23 | Pozuelo de Alarcón | 58 | pozuelodealarcon.org | páginas HTML |
| 24 | San Lorenzo de El Escorial | 49 | datosabiertos.aytosanlorenzo.es | CKAN |
| 25 | Sant Boi | 45 | dadesobertes.santboi.cat | ArcGIS Hub |
| 26 | Alcoy | 32 | opendata.alcoi.org | CKAN |
| 27 | Ponferrada | 29 | opendata.ponferrada.org | CKAN |

**Plataformas agregadoras** (explican la cola larga):

- **eprinsa / `enlaza.eprinsa.es`** (Diputación de Córdoba): **68 municipios**, ~30-39 datasets
  cada uno, catálogos casi idénticos. Es el mayor bloque del censo y a la vez el menos informativo:
  son los mismos indicadores de transparencia replicados.
- **`dadesobertes.seu-e.cat`** (Consorci AOC, Cataluña): CKAN con **906 datasets y 82 organizaciones
  municipales**. Un solo endpoint CKAN da acceso a 82 ayuntamientos catalanes. Es el mejor
  ratio esfuerzo/cobertura de todo el ecosistema.
- **Ciudades Abiertas** (A Coruña, Madrid, Santiago, Zaragoza): API REST y ontologías comunes.

**Consecuencia de diseño:** integrar 4 conectores (CKAN genérico, AOC seu-e, eprinsa, ArcGIS)
cubre ~95 de los 107 municipios. Integrar "una ciudad a la vez" es la estrategia equivocada.

### Ausencias notables

Las Palmas de Gran Canaria aparece con solo **24 datasets** federados y vía **ArcGIS
(`sit.laspalmasgc.es`)**, no con un portal CKAN. Sevilla, Murcia, Palma, Alicante, Valladolid,
Granada, Elche y A Coruña **no aparecen entre los 107 publicadores municipales de datos.gob.es**
con volumen significativo. Ojo: eso significa "no federado o federado marginalmente", no
necesariamente "no tiene portal". Es un hallazgo publicable en sí mismo: **la federación
nacional tiene huecos grandes entre las 20 ciudades más pobladas**.

## 3. Volumen: metadatos vs datos

Cosecha de los 16 portales CKAN (5.131 datasets, 35.400 recursos):

| Portal | Datasets | Recursos | Metadatos | GB declarados | % con tamaño |
|---|---:|---:|---:|---:|---:|
| Madrid | 672 | 11.010 | 19,7 MB | **262,4** | 96 % |
| Barcelona | 555 | 6.753 | 12,9 MB | **61,7** | 100 % |
| Cabildo Tenerife | 285 | 5.437 | 5,9 MB | 56,2 | 97 % |
| Alcoy | 32 | 165 | 0,2 MB | 5,1 | 95 % |
| Málaga | 1.371 | 3.261 | 6,3 MB | 2,5 (→ ~10 real) | 31 % |
| Arganda | 1.003 | 3.511 | 4,9 MB | 1,0 | 67 % |
| Resto (10 portales) | 1.213 | 5.263 | 8,4 MB | 2,7 | 47-100 % |
| **Total** | **5.131** | **35.400** | **58,3 MB** | **~392** | |

Extrapolación al conjunto nacional municipal (9.492 datasets):
**metadatos ≈ 100–150 MB** (≈25 MB comprimidos), **datos ≈ 0,4–0,5 TB**.

Tres matices que cambian la decisión de arquitectura:

1. **Los tamaños declarados son fiables.** El error mediano entre `resource.size` y el
   `Content-Length` real medido fue **0,0 %** en todos los portales con tamaño declarado.
   Se puede planificar el almacenamiento sin descargar nada.
2. **La distribución es brutalmente asimétrica.** El **1 % de recursos más grandes concentra
   85,6 GB de los 392** (22 %). En Madrid, 3 ficheros suman 6,2 GB (`cita-previa-linea-madrid`
   en XML de 2,7 GB, el mismo en JSON de 2,0 GB, `entrada-registro-xml` de 1,6 GB). Excluyendo
   ese 1 %, todo el resto cabe en **~306 GB**, y excluyendo Madrid y Barcelona, en **68 GB**.
3. **La mediana de recurso es 27–530 KB.** El catálogo típico es pequeño; lo que pesa son
   unos pocos volcados históricos que un agente de búsqueda de datasets no necesita servir.

## 4. Duplicabilidad: ¿replicar o scrapear?

| Nivel | Coste | Facilidad |
|---|---|---|
| **Metadatos de portales CKAN** (16 portales) | 58 MB, ~6 min con 8 hilos | Trivial: `package_search` paginado |
| **Metadatos vía AOC seu-e** (82 municipios) | 1 endpoint CKAN | Trivial |
| **Metadatos vía datos.gob.es** (los 107) | SPARQL + API `apidata` | Fácil, pero metadatos empobrecidos respecto al origen |
| **Metadatos de portales ad-hoc** (Gijón, Bilbao, Vitoria, Lorca, Vigo, Pozuelo…) | 1 parser por portal | **Aquí sí hay que scrapear** |
| **Datos completos** | ~0,4-0,5 TB, días de descarga | Posible pero con fricción (§4.2) |

### 4.1 Lo que se replica sin esfuerzo

CKAN da todo el catálogo con paginación estándar. Madrid además publica DCAT completo en
`https://datos.madrid.es/catalog.rdf` (1,7 MB). Barcelona **no** responde en `/data/catalog.rdf`
(404), así que "todos exponen DCAT-AP-ES" es falso en la práctica y conviene verificarlo portal
a portal en la fase 2.

### 4.2 Lo que rompe: evidencia medida

Muestreo de 30 recursos por portal, 10 hilos concurrentes:

| Portal | Vivos (concurrente) | Vivos (serial, 3 s) | Diagnóstico |
|---|---:|---:|---|
| Barcelona | **7 %** (28× HTTP 503) | **100 %** (8/8) | Rate-limiting agresivo |
| Madrid | 47 % (16× HTTP 403) | **0 %** (8/8 → 403) | WAF/anti-bot, intermitente |
| Terrassa | 63 % | 75 % | 403 + 500 mezclados |
| Avilés | 20 % (24× timeout) | **100 %** | Servidor lento, no caído |
| Pamplona | 70 % | — | Timeouts + 500 |
| Málaga, Córdoba, Arganda, Alcobendas, SC Tenerife, San Lorenzo, Reus, Alcoy, Ponferrada | 100 % | — | Sanos |

Esto es exactamente el argumento que faltaba en el plan: **no es que duplicar "dé estabilidad",
es que sin duplicar el sistema no funciona**. Un agente que resuelva una pregunta con 5 llamadas
a herramientas contra Barcelona en vivo tiene una probabilidad alta de fallar por 503. Y el
fallo será no reproducible, lo que hace **imposible una evaluación científica**: sin índice local
no se puede distinguir un error del modelo de una caída del portal. El índice local no es una
optimización, es una **precondición de validez experimental**.

### 4.3 Recomendación

- **Metadatos: réplica completa y periódica.** Es lo único que consultan las herramientas MCP
  del plan (`buscar_datasets`, `detalle_dataset`, `listar_distribuciones`, `comparar_ciudades`).
  100-150 MB en SQLite/DuckDB. Cabe incluso en el navegador para el experimento B.
- **Datos: no replicar por defecto.** Cachear bajo demanda, con TTL, y solo lo que se
  consulte. Presupuesto de 50 GB cubre de sobra cualquier evaluación.
- **Excluir explícitamente el 1 % gigante** salvo que un caso de uso lo pida.
- **Respetar los límites declarados**: Málaga fija `Crawl-Delay: 10` y `Disallow: /api/` en su
  `robots.txt`. Aunque `robots.txt` gobierna crawlers y no clientes de API documentada, un TFM
  que se va a presentar en el Encuentro Nacional de Datos Abiertos debe cosechar con
  concurrencia baja, `User-Agent` identificable y contacto. Cosechar bien es parte de la
  contribución.

## 5. Puntuación de impacto y calidad (0-100)

Rúbrica: **Impacto 50** (población 20 · nº datasets 15 · volumen 8 · nº recursos 7, todos en
escala logarítmica) + **Calidad 50** (API estándar 15 · % formatos máquina 12 · frescura 12 ·
licencia 5 · completitud de metadatos 6 — dividido entre `%size` y `%descripción` · enlaces
vivos 6). Implementada en `research/score.py`.

**Población:** cifras oficiales del INE, operación *Cifras Oficiales de Población de los
Municipios Españoles: Revisión del Padrón Municipal* (DPOP, cód. IOE 30245), tabla **29005**
«Cifras oficiales del padrón por municipio», sexo = Total, **población a 1 de enero de 2025**
(última revisión publicada). Los 27 valores salen de la misma tabla y del mismo año, con el
código INE de cada municipio y la serie exacta en `research/data/poblacion_ine.json`.
Tabla: <https://www.ine.es/jaxiT3/Tabla.htm?t=29005> · API JSON:
`https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/29005?tv=19:{id}&tv=18:451&nult=1`.

| # | Ciudad | Pobl. (INE 2025) | DS | GB | API | Imp/50 | Cal/50 | **Total** | Base |
|---|---|---:|---:|---:|---|---:|---:|---:|---|
| 1 | **Madrid** | 3.506.730 | 672 | 262,4 | CKAN+DCAT | 48,5 | 49,7 | **98** | medido |
| 2 | **Barcelona** | 1.731.649 | 555 | 61,7 | CKAN+DCAT | 43,9 | 46,5 | **90** | medido |
| 3 | Málaga | 599.063 | 1.369 | ~10 | CKAN+DCAT | 39,5 | 38,9 | **78** | medido |
| 4 | Reus | 111.601 | 119 | 0,6 | CKAN+DCAT | 23,9 | 54,4 | **78** | medido |
| 5 | Alcobendas | 123.342 | 177 | 0,5 | CKAN+DCAT | 25,6 | 51,1 | **77** | medido |
| 6 | Terrassa | 233.270 | 125 | 0,1 | CKAN+DCAT | 24,9 | 48,7 | **74** | medido |
| 7 | Avilés | 75.517 | 107 | 0,1 | CKAN+DCAT | 21,0 | 51,4 | **72** | medido |
| 8 | Pamplona | 209.094 | 35 | n/d | CKAN+DCAT | 24,4 | 46,2 | **71** | medido |
| 9 | Sta. Cruz Tenerife | 211.957 | 86 | 0,7 | CKAN+DCAT | 26,4 | 42,1 | **69** | medido |
| 10 | Arganda del Rey | 60.419 | 968 | 1,0 | CKAN+DCAT | 28,2 | 40,5 | **69** | medido |
| 11 | Alcoy | 61.468 | 32 | 5,1 | CKAN+DCAT | 20,4 | 49,0 | **69** | medido |
| 12 | S. Lorenzo Escorial | 18.872 | 49 | 0,01 | CKAN+DCAT | 12,5 | 55,7 | **68** | medido |
| 13 | Torrent | 90.928 | 342 | 0,2 | CKAN+DCAT | 24,5 | 39,5 | **64** | medido |
| 14 | Córdoba | 323.262 | 145 | 0,7 | CKAN+DCAT | 29,8 | 31,0 | **61** | medido |
| 15 | Zaragoza | 693.091 | 228 | n/d | REST propio | 30,8 | 26,2 | **57** | inferido |
| 16 | Valencia | 840.792 | 296 | n/d | ArcGIS | 32,1 | 24,2 | **56** | inferido |
| 17 | Gijón | 269.894 | 783 | n/d | REST propio | 29,9 | 26,2 | **56** | inferido |
| 18 | Ponferrada | 63.186 | 29 | 0,01 | CKAN+DCAT | 15,1 | 40,2 | **55** | medido |
| 19 | Vitoria-Gasteiz | 260.699 | 197 | n/d | ficheros | 26,9 | 26,2 | **53** | inferido |
| 20 | Donostia | 189.866 | 108 | n/d | ArcGIS | 24,4 | 28,2 | **53** | inferido |
| 21 | Las Palmas GC | 381.868 | 24 | n/d | ArcGIS | 23,9 | 28,2 | **52** | inferido |
| 22 | Cáceres | 96.651 | 116 | n/d | SPARQL propio | 22,1 | 30,2 | **52** | inferido |
| 23 | Bilbao | 351.124 | 341 | n/d | web | 29,1 | 22,2 | **51** | inferido |
| 24 | Vigo | 294.489 | 148 | n/d | web | 26,7 | 22,2 | **49** | inferido |
| 25 | Santander | 175.425 | 58 | n/d | REST propio | 22,9 | 26,2 | **49** | inferido |
| 26 | Sant Boi | 85.610 | 45 | n/d | ArcGIS Hub | 19,7 | 29,2 | **49** | inferido |
| 27 | Lorca | 98.969 | 204 | n/d | ad-hoc | 23,3 | 24,2 | **48** | inferido |

### Por qué esas notas

**Madrid, 98.** Único portal que puntúa alto en las dos mitades. Impacto máximo por población
(3.506.730 hab.) y por volumen (262 GB, 11.010 recursos, el catálogo más profundo de España en
recursos por dataset: 16,4). Calidad casi máxima porque es el único con **100 % de datasets
actualizados en los últimos 12 meses** (antigüedad mediana de metadatos: **4 días**), 100 %
con descripción larga, 96 % con tamaño declarado, licencia CC-BY homogénea y DCAT completo
descargable. Pierde puntos solo por fiabilidad: el WAF bloquea la descarga programática.
No es un portal, es una infraestructura mantenida.

**Barcelona, 90.** 100 % de recursos con tamaño declarado y licencia CC-BY-4.0 uniforme en los
555 datasets — la higiene de metadatos más limpia del país. Penalizada frente a Madrid por
frescura (46 % actualizado en 12 meses, antigüedad mediana 472 días) y por el rate-limiting
más agresivo medido. Sigue siendo la mejor opción para trabajo semántico serio: es el único
con vocabulario y licencias sin excepciones.

**Málaga, 78.** El catálogo más grande en datasets (1.369) y el único que compite con
Madrid/Barcelona en tamaño, con 100 % de enlaces vivos. Baja a 78 por **frescura pésima:
solo el 16 % actualizado en 12 meses, antigüedad mediana 1.541 días (4,2 años)** y 31 % de
recursos con tamaño declarado. Además el 68 % de formatos son máquina-legibles porque
arrastra 932 PDFs. Mucho catálogo, poco mantenimiento.

**Reus, 78 / San Lorenzo de El Escorial, 68 (calidad 55,7, la más alta del país).** Aquí la
rúbrica hace lo que debe: municipios pequeños con **calidad ejemplar** (100 % formatos máquina,
97-100 % actualizado, 100 % enlaces vivos, licencia única) y **impacto bajo** por tamaño.
Un TFM que solo mire las capitales se los pierde, y son los mejores casos de prueba: catálogo
limpio, pequeño, y sin ruido para depurar herramientas.

**Arganda del Rey, 69.** Anomalía que merece un párrafo en la memoria: **968 datasets para
60.419 habitantes**, más que Madrid. La razón es que publica series desagregadas como datasets
independientes. Frescura: **16 % en 12 meses, antigüedad mediana 5,4 años**. Es el ejemplo
canónico de "inflación de catálogo": el recuento de datasets como métrica de éxito de un portal
está roto, y este dato lo demuestra. Úsalo en el cap. 3.

**Córdoba, 61.** Penalizada duramente en licencia (1,5/5): **ninguno de sus 145 datasets
declara licencia**: 83 dicen `notspecified` y 62 no traen el campo, y el **83 % de sus recursos son PDF** (1.674 de
2.013), con solo un 15 % de formatos máquina-legibles. Un portal de transparencia disfrazado
de portal de datos abiertos. Es el peor caso medido, y por eso es útil: si el agente MCP no
sirve aquí, sabemos por qué.

**Sta. Cruz de Tenerife, 69 y Torrent, 64.** Ambos con **0 % de datasets actualizados en 24
meses** (antigüedad mediana 7,2 años). Calidad estructural buena, catálogos congelados.
Son la prueba de que "formato correcto" ≠ "dato útil", una distinción que el banco de
evaluación debería capturar explícitamente.

**Zaragoza (57), Valencia (56), Gijón (56), Bilbao (51), Vigo (49).** Ciudades grandes con
puntuación mediocre **por la API, no por los datos**. Zaragoza y Gijón tienen catálogos
sustanciales (228 y 783 datasets) pero exigen un conector a medida. Bilbao y Vigo no exponen
API de catálogo utilizable: hay que scrapear HTML. Aquí la penalización es de *accesibilidad
para agentes*, que es precisamente el objeto del TFM. La brecha entre "ciudad grande" y "ciudad
consultable por un LLM" es el hallazgo central del capítulo 3.

**Las Palmas GC, 52.** Con 381.868 habitantes debería estar arriba; tiene 24 datasets federados
y sirve por ArcGIS/WFS, no por un catálogo DCAT. Si el TFM la incluye por proximidad
personal, hay que asumir que es un **caso de estudio de carencia**, no un catálogo de referencia.

### Limitaciones de la puntuación

- La población son las **cifras oficiales del INE a 1 de enero de 2025** (tabla 29005 de la
  revisión del padrón municipal), las 27 de la misma tabla y del mismo año, con código INE y
  serie por municipio en `research/data/poblacion_ine.json`. La cifra es oficial, pero está
  **desfasada ~19 meses** respecto a la medición de los catálogos (25/07/2026): la revisión a
  1 de enero de 2026 aún no estaba publicada. El desfase es homogéneo para todos y no altera
  el orden relativo.
- Las 13 filas "inferido" no tienen medición de frescura, formatos ni enlaces vivos: se les
  asignó un valor neutro. Su nota real puede moverse ±10.
- La rúbrica pondera 50/50 impacto y calidad porque así se pidió; eso hace que Reus (111.601 hab.)
  empate con Málaga (599.063 hab.). Si el objetivo es elegir ciudades para el TFM, mira las dos
  columnas por separado, no el total.

## 6. Licencias: ¿duplicar va contra la filosofía o la licencia?

**No.** Ni contra una ni contra otra. Evidencia y razonamiento:

**Lo que dicen las licencias reales** (histograma sobre 5.131 datasets):

| Licencia | Datasets | % |
|---|---:|---:|
| `cc-by` / `CC-BY-4.0` / `cc-by-4.0` | 3.360 | 65,5 % |
| `by-sa-40` / `by-sa` (Málaga) | 1.368 | 26,7 % |
| `odc-by` | 175 | 3,4 % |
| **Sin licencia o `notspecified`** | **153** | **3,0 %** |
| Licencias propias (`emt-madrid`, `other-at`, …) | 63 | 1,2 % |

**93,7 % permite explícitamente la redistribución**, incluida la de obras derivadas, a cambio de
atribución (y de compartir igual en el caso de Málaga y su `by-sa`).

**Lo que dice la norma.** La Ley 37/2007 de reutilización de la información del sector público
—modificada por la Ley 18/2015 y por el RDL 24/2021, que transpone la Directiva (UE) 2019/1024—
parte de que la información pública **es reutilizable, incluida su redistribución con ánimo
comercial**. Las condiciones generales del RD 1495/2011 (art. 8) son cuatro y ninguna prohíbe
copiar: no desnaturalizar el sentido de la información, citar la fuente, mencionar la fecha de
última actualización, y no dar a entender que el organismo patrocina la reutilización. La propia
Directiva **obliga** a los organismos a ofrecer APIs y descarga masiva (*bulk download*)
justamente para que terceros puedan replicar. Replicar no es una zona gris: es el
comportamiento que la norma pretende fomentar.

**Filosóficamente es lo contrario de un problema.** El movimiento de datos abiertos nació
para romper el monopolio de acceso del organismo publicador. Un espejo con atribución
**aumenta** la disponibilidad de lo que un ayuntamiento publicó. Lo que sí choca con la filosofía
es lo contrario: construir un agente que dependa de un portal privado, o que devuelva datos sin
decir de dónde salen.

**Dónde está el riesgo de verdad — y no es legal, es de integridad:**

1. **Datos rancios presentados como vivos.** El pecado real. Si tu MCP responde "Málaga tiene
   este dataset de calidad del aire" con una copia de hace seis meses y sin decirlo, has
   desnaturalizado la información — que es justo lo que prohíbe el art. 8. **Mitigación:** cada
   respuesta de herramienta lleva `fecha_sincronizacion`, `fecha_modificacion_origen` y `url_origen`.
2. **Pérdida de procedencia en la cadena LLM→usuario.** El modelo resume y se come la atribución.
   **Mitigación:** la atribución va en el *payload* de la herramienta, no en el prompt del sistema,
   y el banco de evaluación penaliza las respuestas sin fuente. Esto es una métrica más para el §6
   del plan.
3. **El 3 % sin licencia declarada** (Córdoba sobre todo). **Mitigación:** marcarlos en el índice
   con `licencia: no declarada` y que la herramienta lo diga. Es más honesto que asumir CC-BY, y
   además es un hallazgo del cap. 3.
4. **`by-sa` de Málaga (26,7 %).** Compartir-igual aplica a *obras derivadas*. Un índice de
   metadatos redistribuido debería llevar la misma licencia. Si publicas el banco de evaluación
   con metadatos de Málaga dentro, revísalo antes de subirlo a Zenodo.
5. **Cortesía técnica.** Concurrencia baja, `User-Agent` identificable con contacto, respetar
   `Crawl-Delay`. Tu director te presentará ante esta comunidad; que la cosecha no aparezca en
   los logs de nadie como un incidente.

**Veredicto:** duplica los metadatos sin dudarlo, y no lo escondas — documenta el espejo como
una contribución. Cachea los datos de forma selectiva y con TTL. Conserva procedencia en cada
respuesta. Publica el índice bajo la licencia más restrictiva de las que ingiere (`by-sa-40`).

## 7. Impacto en el plan del TFM: el problema de novedad

Esto es lo que hay que llevar a la reunión de septiembre con Óscar.

**Ya existe** (verificado el 25/07/2026):

| Proyecto | Qué es | Solapamiento |
|---|---|---|
| **Agente conversacional con servidor MCP de datos.gob.es** (publicado 12/01/2026, actualizado 09/04/2026, código en el repo `Admindatosgobes/Laboratorio-de-Datos`) | Servidor MCP oficial sobre datos.gob.es con FastMCP + Google ADK + FastAPI. Herramientas: `buscar_datasets`, `listar_tematicas`, `buscar_por_tematica`, `obtener_detalle_dataset` | **Casi total con el O1 del plan.** Tres de las cinco herramientas del §4 del plan son literalmente las mismas, con los mismos nombres |
| `AlbertoUAH/datos-gob-es-mcp` ("Open Data Spain MCP Server") | MCP comunitario sobre datos.gob.es, listado en mcpservers.org | Alto |
| `mjanez/ckan-mcp-server`, `ondata/ckan-mcp-server`, `ondics/ckan-mcp-server` | MCP genéricos sobre CKAN, con búsqueda semántica, SQL sobre DataStore y análisis geoespacial | Alto: cualquier portal CKAN español es consultable ya |
| `malkreide/zurich-opendata-mcp` | MCP municipal de Zúrich: 20 herramientas, CKAN + geodatos + SPARQL + tiempo real | **Es exactamente el TFM propuesto, para otra ciudad** |
| "Madrid Agentic City" y `cibelex-mcp` (org. GitHub del Ayuntamiento de Madrid) | Iniciativas de IA agéntica municipal | Por verificar, potencialmente alto |

**Lo que sigue siendo tuyo y nadie ha hecho:**

1. **El banco de evaluación en español.** Búsqueda hecha: no existe un benchmark en español de
   preguntas sobre catálogos de datos abiertos con respuestas de referencia y trazas de
   herramientas. Los benchmarks de tool-calling (ToolBench, API-Bank, FlowBench) son genéricos y
   en inglés. **Esta es ahora la contribución principal, no la secundaria.**
2. **La pregunta de investigación del modelo pequeño en el navegador.** Ningún proyecto de los
   anteriores la responde; todos asumen un modelo grande en la nube. Sigue intacta.
3. **La capa multiciudad municipal.** Lo existente es o nacional (datos.gob.es, que empobrece
   metadatos) o mono-ciudad (Zúrich). El eje **comparación entre municipios sobre metadatos
   heterogéneos** —con la evidencia de heterogeneidad de §2 y §5— no está cubierto.
4. **La caracterización empírica del ecosistema municipal español.** Los números de este
   documento (frescura, licencias, link rot, inflación de catálogo, huecos de federación) no
   están publicados en ningún sitio que haya encontrado.

**Reformulación sugerida del TFM.** De *"construyo un servidor MCP para catálogos DCAT"* a
*"¿cuánto de la dificultad de consultar datos abiertos municipales es del modelo y cuánto de
los metadatos? Y ¿basta un modelo pequeño local?"* — con el banco de evaluación y la
caracterización del ecosistema como contribuciones, y el servidor MCP como **instrumento**,
partiendo de los MCP CKAN existentes en lugar de reescribirlos. Es un TFM más defendible, más
honesto y bastante menos trabajo de fontanería.

**Primeros pasos revisados** (sustituyen a los del §11 del plan):

- [ ] Leer el código del MCP de datos.gob.es y el de `mjanez/ckan-mcp-server` **antes** de escribir línea propia
- [ ] Llevar a Óscar esta tabla de solapamiento y acordar la reformulación
- [ ] Confirmar qué es exactamente "Madrid Agentic City" — puede ser prior art directo o una colaboración
- [ ] Fijar el corpus: Madrid + Barcelona + Málaga (grandes, medidos) + Córdoba (peor caso) + Reus o San Lorenzo (mejor caso limpio) + Gijón o Zaragoza (sin API estándar). Seis ciudades que cubren todo el espectro de calidad medido
- [ ] Montar el índice local de metadatos como primer entregable de código, y publicarlo

## 8. Fuentes

- [Agente conversacional con servidor MCP en datos.gob.es](https://datos.gob.es/en/conocimiento/conversational-agent-mcp-server-datosgobes)
- [ondata/ckan-mcp-server](https://github.com/ondata/ckan-mcp-server) · [mjanez/ckan-mcp-server](https://github.com/mjanez/ckan-mcp-server) · [ondics/ckan-mcp-server](https://github.com/ondics/ckan-mcp-server)
- [malkreide/zurich-opendata-mcp](https://github.com/malkreide/zurich-opendata-mcp)
- [AlbertoUAH/datos-gob-es-mcp](https://github.com/AlbertoUAH/datos-gob-es-mcp) · [ficha en mcpservers.org](https://mcpservers.org/servers/albertouah/datos-gob-es-mcp)
- [CiudadesAbiertas/CiudadesAbiertas-API](https://github.com/CiudadesAbiertas/CiudadesAbiertas-API) · [org. GitHub del Ayuntamiento de Madrid](https://github.com/ayuntamientomadrid)
- [Estrategia de IA del Ayuntamiento de Barcelona](https://ajuntament.barcelona.cat/institut-innovacio-tecnologia/es/noticies/actualitat/barcelona-impulsa-una-estrategia-de-inteligencia-artificial-al-servicio-de-la-ciudadania-1610530)
- Endpoint SPARQL de datos.gob.es: `https://datos.gob.es/virtuoso/sparql` · APIs CKAN de los 16 portales listados en `research/harvest.py`
