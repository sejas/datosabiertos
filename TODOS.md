---
type: note
title: TODOs del TFM por fases, con criterios de aceptación
date: 2026-07-25
tags: [tfm, todos, plan, seguimiento]
---

# TODOs del TFM

Desglose ejecutable de las fases de [PLAN.md](PLAN.md), revisado con los hallazgos de
[docs/02-analisis-catalogos.md](docs/02-analisis-catalogos.md).

Cada tarea lleva un bloque **DONE IS:** con criterios verificables. Si no puedes comprobar
un criterio con un comando, un fichero o un correo enviado, no está hecho. "Casi hecho" es
"no hecho". No marques una fase completa hasta que todas sus tareas lo estén.

**Corpus de trabajo fijado** (elegido para cubrir todo el espectro de calidad medido):
Madrid (98) · Barcelona (90) · Málaga (78) · Córdoba (61, peor caso) · Reus (78, mejor caso
limpio) · Gijón o Zaragoza (sin API estándar).

---

## Fase 0 — Arranque · sep 2026

> Cerrar el alcance real del TFM antes de escribir código. El análisis de julio cambió el
> planteamiento: el servidor MCP ya no es la contribución, es el instrumento. Esta fase existe
> para que esa reformulación quede acordada por escrito con el director, no asumida.

- [x] **0.1 — Leer el prior art antes de escribir una línea propia** ✅ 25/07/2026
  Código del MCP de datos.gob.es (`Admindatosgobes/Laboratorio-de-Datos`), `mjanez/ckan-mcp-server`
  y `malkreide/zurich-opendata-mcp`. Interesa qué herramientas exponen, cómo modelan los
  argumentos y qué hacen cuando el portal falla.
  **DONE IS:**
  - `docs/03-prior-art.md` existe con una ficha por proyecto: herramientas expuestas, firma de
    cada una, stack, licencia y fecha del último commit.
  - Una tabla explícita de qué herramientas del §4 del plan quedan cubiertas por lo existente
    y cuáles no.
  - Una decisión escrita y justificada: *fork*, *dependencia*, o reimplementación.

- [x] **0.2 — Verificar qué es "Madrid Agentic City" y `cibelex-mcp`** ✅ 25/07/2026
  Aparecen en la organización GitHub del Ayuntamiento de Madrid. Puede ser prior art directo
  sobre la ciudad de mayor puntuación del corpus, o una vía de colaboración.
  **DONE IS:**
  - Sección en `docs/03-prior-art.md` que responde: ¿qué es, está vivo, es público, solapa?
  - Si solapa, alternativa de posicionamiento escrita antes de la reunión con Óscar.

- [ ] **0.3 — Reunión de alcance con Óscar Corcho**
  Llevar la tabla de solapamiento y la reformulación propuesta: de "construyo un MCP" a
  "¿cuánto de la dificultad es del modelo y cuánto de los metadatos, y basta un modelo pequeño
  local?".
  **DONE IS:**
  - Reunión celebrada; acta de una página en `docs/00-actas/2026-09-XX-alcance.md`.
  - Objetivos O1–O4 reescritos en `PLAN.md` y aceptados por el director por escrito (correo
    archivado en el acta).
  - Corpus de ciudades confirmado o modificado con justificación.
  - Preguntado explícitamente por trabajos previos del OEG sobre calidad de metadatos en
    portales españoles, y la respuesta anotada.

- [ ] **0.4 — Matrícula del TFM**
  Periodo ordinario julio–septiembre 2026, 15 ECTS.
  **DONE IS:** resguardo de matrícula guardado; TFM y director figuran en el expediente.

---

## Fase 1 — Estado del arte · 4 semanas · oct 2026

> Es el capítulo 2 de la memoria. No es una lista de referencias: es el argumento de por qué
> tu pregunta de investigación sigue abierta después de todo lo que ya existe.

- [ ] **1.1 — Revisión sobre agentes LLM con herramientas y tool-calling**
  Cubrir ReAct, Toolformer, function calling, y los benchmarks de referencia (ToolBench,
  API-Bank, FlowBench) señalando que son genéricos y en inglés.
  **DONE IS:**
  - ≥25 referencias con revisión por pares en `refs.bib`, cada una con una nota de una línea
    sobre por qué está.
  - Subsección escrita que termina justificando por qué hace falta un banco en español.

- [ ] **1.2 — Revisión sobre LLM + grafos de conocimiento y metadatos DCAT**
  Text-to-SPARQL, QA sobre KG, calidad de metadatos en portales de datos abiertos.
  **DONE IS:**
  - ≥20 referencias en `refs.bib`.
  - Tabla comparativa de trabajos previos sobre calidad de metadatos DCAT, con columna de qué
    métricas usan (para reutilizarlas en el cap. 3 en vez de inventar las tuyas).

- [ ] **1.3 — Revisión de MCP y del ecosistema de servidores MCP para datos abiertos**
  MCP es de nov. 2024: hay poca literatura académica y mucha ingeniería. Documenta ambas.
  **DONE IS:**
  - Especificación de MCP resumida en 1–2 páginas con las primitivas relevantes (tools,
    resources, prompts, transporte).
  - Inventario de ≥6 servidores MCP para datos abiertos con fecha de consulta.

- [ ] **1.4 — Revisión de modelos pequeños en el navegador**
  WebLLM, transformers.js, WebGPU, cuantización q4, y el estado del tool-calling en modelos
  de 1–3 B.
  **DONE IS:**
  - Tabla de modelos candidatos: tamaño en disco, RAM/VRAM necesaria, soporte declarado de
    function calling, licencia.
  - Al menos una fuente que documente tasas de acierto de tool-calling en modelos <4 B.

- [ ] **1.5 — Redactar el capítulo 2**
  **DONE IS:**
  - `memoria/cap2-estado-del-arte.tex` (o `.md`) completo, 15–25 páginas.
  - Termina con un párrafo de "hueco identificado" que enlaza directamente con la pregunta
    de investigación del §3 del plan.
  - Revisado por Óscar y con sus comentarios incorporados o rebatidos por escrito.

---

## Fase 2 — Análisis de catálogos · 3 semanas · nov 2026

> Parcialmente hecha: `docs/02-analisis-catalogos.md` ya tiene el censo, los volúmenes, las
> licencias y la rúbrica. Lo que falta es cerrar los huecos que quedaron marcados como
> "inferido" y convertirlo en capítulo.

- [ ] **2.1 — Medir los portales sin API estándar**
  Las 13 filas marcadas "inferido" en la rúbrica: Zaragoza, Gijón, Valencia, Vitoria, Bilbao,
  Vigo, Santander, Lorca, Cáceres, Donostia, Las Palmas GC, Sant Boi.
  **DONE IS:**
  - Un conector por portal del corpus que devuelva la lista de datasets con título, descripción,
    tema, fecha de modificación y distribuciones.
  - `research/score.py` reejecutado sin ninguna fila "inferido" para las ciudades del corpus.
  - Las que resulten imposibles de cosechar quedan documentadas con el motivo técnico exacto.

- [ ] **2.2 — Verificar la cobertura real de DCAT-AP-ES**
  El análisis mostró que Madrid publica `catalog.rdf` y Barcelona no. Hay que comprobarlo
  portal a portal en vez de asumirlo.
  **DONE IS:**
  - Tabla en el cap. 3: portal × (¿expone RDF/DCAT?, ¿qué perfil?, ¿valida contra el SHACL de
    DCAT-AP-ES?, ¿qué campos obligatorios faltan?).
  - Validación ejecutada con una herramienta reproducible, no a ojo.

- [x] **2.3 — Corregir los datos de población** ✅ 25/07/2026
  En la rúbrica están puestos de memoria.
  **DONE IS:** poblaciones tomadas del padrón INE con URL y año en `research/score.py`;
  puntuaciones recalculadas y la tabla del cap. 3 actualizada.

- [ ] **2.4 — Caracterizar la heterogeneidad semántica entre municipios**
  El mismo concepto ("calidad del aire", "padrón", "presupuesto") se llama distinto en cada
  portal. Esto es lo que hace difícil `comparar_ciudades`.
  **DONE IS:**
  - Para ≥8 temas comunes, tabla con cómo lo nombra y clasifica cada ciudad del corpus.
  - Cuantificado: % de solapamiento de vocabulario de `keywords` entre pares de ciudades.
  - Conclusión explícita sobre si la taxonomía de datos.gob.es basta para alinear o no.

- [ ] **2.5 — Redactar el capítulo 3**
  **DONE IS:**
  - `memoria/cap3-analisis-dominio.md` completo, con censo, rúbrica, heterogeneidad, link rot,
    inflación de catálogo (Arganda) y huecos de federación.
  - Todas las cifras trazables a un script de `research/`.

---

## Fase 3 — Índice local y servidor MCP v1 · 5 semanas · nov 2026–ene 2027

> El índice local va **primero**. La fase 4 no puede medirse contra portales que devuelven 503
> de forma aleatoria: sin índice, la evaluación no es reproducible y el TFM no se sostiene.

- [x] **3.1 — Índice local de metadatos** ✅ 25/07/2026
  Volcado periódico de los catálogos del corpus a un almacén propio (SQLite o DuckDB).
  ~100–150 MB para los 107 municipios, así que cabe entero.
  **DONE IS:**
  - `python -m tfm.index build` reconstruye el índice desde cero en una máquina limpia.
  - Esquema con, como mínimo: dataset, distribución, publicador, tema, keywords, licencia,
    `fecha_modificacion_origen`, `fecha_sincronizacion`, `url_origen`.
  - Búsqueda de texto completo en español funcionando (acentos y plurales incluidos).
  - Tamaño y tiempo de construcción registrados en el README.

- [~] **3.2 — Trazabilidad de procedencia extremo a extremo** — hecho en el índice; falta al exponerlo por MCP
  Exigencia legal (RD 1495/2011 art. 8) y de integridad, no un extra.
  **DONE IS:**
  - Toda respuesta de herramienta incluye `url_origen`, `licencia`,
    `fecha_modificacion_origen` y `fecha_sincronizacion`.
  - Los datasets sin licencia declarada (≈3 %) salen marcados como `licencia: no declarada`,
    nunca asumidos como CC-BY.
  - Test automático que falla si alguna herramienta devuelve un dataset sin procedencia.

- [~] **3.3 — Cosecha cortés y programada** — falta solo la programación semanal
  **DONE IS:**
  - Concurrencia máxima configurable, por defecto ≤2 por host; respeta `Crawl-Delay`
    (Málaga fija 10 s).
  - `User-Agent` identificable con proyecto y correo de contacto.
  - Reintentos con *backoff* exponencial ante 429/503.
  - Ejecución programada semanal y registro de errores por portal.

- [~] **3.4 — Servidor MCP v1** — prototipo con las 4 herramientas; falta probarlo desde un 2º cliente real
  Herramientas del §4 del plan, sobre el índice local. Reutilizando lo decidido en 0.1.
  **DONE IS:**
  - `buscar_datasets`, `detalle_dataset`, `listar_distribuciones`, `comparar_ciudades`
    implementadas, con esquema de argumentos tipado y documentado.
  - Instalable con un solo comando; README con la configuración para Claude Desktop y para
    un cliente propio.
  - Se conecta y lista herramientas correctamente desde ≥2 clientes MCP distintos.
  - Ninguna herramienta tarda más de 2 s en el p95 contra el índice local.

- [x] **3.5 — Decisión sobre `consultar_sparql`** ✅ no se implementa en la v1 (docs/03-prior-art.md §5.5)
  Exponer SPARQL libre a un LLM es potente y arriesgado (consultas que tumban el endpoint,
  inyección, resultados imposibles de verificar).
  **DONE IS:** decisión escrita y argumentada; si se implementa, con límite de tiempo, de
  filas y lista blanca de patrones; si no, justificada en el cap. 4 como alternativa descartada.

- [ ] **3.6 — Cliente de prueba**
  **DONE IS:**
  - Cliente que acepta una pregunta, ejecuta el bucle de herramientas y devuelve respuesta
    + traza completa de llamadas en JSON.
  - La traza es el formato que consumirá la evaluación de la fase 5. Documentado.

---

## Fase 4 — Banco de evaluación · 4 semanas · ene–feb 2027

> Con el prior art encontrado, **esta es la contribución principal del TFM**, no la secundaria.
> Trátala como tal: es lo que se publica con DOI y lo que otros reutilizarán.

- [x] **4.1 — Diseño del esquema del banco** ✅ 25/07/2026
  **DONE IS:**
  - Esquema JSON documentado con: pregunta, dificultad (fácil/media/difícil), tipo (mono o
    multiciudad), ciudad(es), dataset(s) de referencia, traza de herramientas esperada,
    respuesta de referencia y notas del anotador.
  - Validador que rechaza entradas mal formadas.
  - Justificado por qué esos campos y no otros, con apoyo en los benchmarks de la fase 1.

- [~] **4.2 — Redactar 80–120 preguntas en español** — 15 preguntas semilla verificadas; faltan 65+
  Distribuidas por dificultad y por ciudad del corpus, incluyendo casos que **deben fallar**
  (datos que no existen) para medir alucinación.
  **DONE IS:**
  - ≥80 preguntas validadas contra el esquema.
  - Cada una con dataset de referencia verificado a mano en el portal de origen.
  - ≥15 % multiciudad; ≥10 % sin respuesta posible (control de alucinación).
  - Cobertura de las 6 ciudades del corpus, incluida Córdoba como peor caso.

- [ ] **4.3 — Validación con un segundo anotador**
  Un banco anotado por una sola persona es una opinión, no una referencia.
  **DONE IS:**
  - ≥20 % de las preguntas reanotadas de forma independiente.
  - Acuerdo entre anotadores calculado y reportado (Cohen's κ o equivalente).
  - Discrepancias resueltas y el criterio documentado.

- [ ] **4.4 — Publicación del banco**
  **DONE IS:**
  - Publicado en Zenodo con DOI y en GitHub, con licencia explícita.
  - La licencia respeta la más restrictiva de las ingeridas (`by-sa-40` de Málaga) —
    revisado antes de publicar.
  - README con esquema, metodología, limitaciones conocidas y cómo citarlo.

---

## Fase 5 — Experimento A (baseline en la nube) · 2 semanas · feb–mar 2027

- [ ] **5.1 — Arnés de evaluación reproducible**
  **DONE IS:**
  - Un solo comando ejecuta el banco completo contra un modelo configurable y produce
    resultados en JSON.
  - Semilla fijada; dos ejecuciones seguidas dan el mismo resultado o la variación queda
    documentada y explicada.
  - Registra por pregunta: traza de herramientas, respuesta, latencia y tokens/coste.

- [ ] **5.2 — Implementar las métricas del §6 del plan**
  **DONE IS:**
  - precision@k y MRR de recuperación; corrección de la traza de herramientas
    (herramienta + argumentos); fidelidad de la respuesta; latencia (primera respuesta y
    total); coste por consulta.
  - La fidelidad se mide con un criterio documentado y auditable (rúbrica o LLM-juez con
    sus prompts versionados), no "a ojo".
  - Métricas validadas a mano sobre ≥10 preguntas para comprobar que miden lo que dicen.

- [ ] **5.3 — Ejecutar el baseline con ≥2 modelos grandes**
  **DONE IS:**
  - Resultados completos de ≥2 modelos sobre el banco entero, en `results/`.
  - Tabla comparativa con todas las métricas.
  - Análisis de errores: ≥30 fallos clasificados por causa (metadatos pobres, herramienta
    mal elegida, argumentos mal formados, alucinación, dato inexistente).

- [ ] **5.4 — Puerta de decisión**
  Si el baseline va mal, el problema son las herramientas, no el modelo.
  **DONE IS:**
  - Decisión escrita en `docs/04-puerta-fase5.md`: ¿se arregla el MCP o se pasa a la fase 6?
  - Umbral fijado **antes** de mirar los resultados y respetado.
  - Consensuada con Óscar.

---

## Fase 6 — Experimento B (modelo pequeño en el navegador) · 4 semanas · abr–may 2027 · OPCIONAL

> Opcional por diseño. El TFM se sostiene sin ella. Un resultado negativo bien medido
> también es publicable, pero tiene que estar bien medido.

- [ ] **6.1 — Cliente en el navegador con WebGPU**
  **DONE IS:**
  - Página que carga un modelo cuantizado q4 (Qwen2.5-1.5B/3B o el elegido en 1.4) y se
    conecta al servidor MCP.
  - Funciona en ≥2 navegadores; requisitos de RAM/VRAM medidos y documentados.
  - Comportamiento definido y probado cuando el dispositivo no llega.

- [ ] **6.2 — Ejecutar el banco en modo local**
  **DONE IS:**
  - Mismo banco, mismas métricas, resultados en `results/`.
  - Latencia y memoria medidas en ≥2 dispositivos reales, especificados.

- [ ] **6.3 — Plan de contingencia si el tool-calling falla**
  **DONE IS:**
  - Documentada la tasa de fallo de formato de llamada del modelo pequeño.
  - LoRA sobre las trazas del experimento A entrenada y evaluada, **o** justificación escrita
    de por qué no procede.

- [ ] **6.4 — Comparativa A vs B**
  **DONE IS:** tabla con calidad, latencia, coste (€/consulta vs 0 €) y memoria; respuesta
  explícita, con número, a la pregunta de investigación del §3 del plan.

---

## Fase 7 — Memoria · 5 semanas · may–jun 2027

> Se escribe en paralelo desde la fase 1. Esta fase es de cierre y coherencia, no de
> escribir 100 páginas desde cero.

- [ ] **7.1 — Capítulos 4 y 5 (diseño e implementación)**
  **DONE IS:** escritos, con las decisiones de arquitectura justificadas y las alternativas
  descartadas explicadas (incluida 3.5).

- [ ] **7.2 — Capítulo 6 (evaluación)**
  **DONE IS:** metodología, resultados A y B, y análisis de errores; toda figura y tabla
  regenerable desde `results/` con un script.

- [ ] **7.3 — Capítulos 1 y 7 (introducción y conclusiones)**
  **DONE IS:** la introducción anuncia exactamente las contribuciones que el cap. 7 confirma;
  la pregunta de investigación queda respondida con datos y las limitaciones dichas sin
  adornos.

- [ ] **7.4 — Revisión completa con el director**
  **DONE IS:** memoria entera revisada por Óscar; comentarios incorporados o rebatidos por
  escrito; versión final aprobada por él.

- [ ] **7.5 — Verificar los criterios de aceptación del §7 del plan**
  **DONE IS:** los 5 criterios del plan comprobados uno a uno con evidencia enlazada.

---

## Fase 8 — Difusión y defensa · 3 semanas · jun–sep 2027

- [ ] **8.1 — Envío al Encuentro Nacional de Datos Abiertos 2027**
  **DONE IS:** propuesta enviada dentro de plazo; acuse guardado.

- [ ] **8.2 — Paper de workshop (ESWC/ISWC) — opcional**
  El deadline de ESWC cae ~feb–mar 2027, **antes** de la fase 7. Si se va a intentar, hay que
  decidirlo en la fase 5.
  **DONE IS:** paper enviado con acuse, **o** decisión escrita de no enviarlo con su motivo.

- [ ] **8.3 — Repositorio público listo para terceros**
  **DONE IS:**
  - Licencia abierta, README con instalación en un comando, y CI que ejecuta los tests.
  - Una persona ajena al proyecto instala y ejecuta el servidor siguiendo solo el README —
    probado con alguien real.

- [ ] **8.4 — Defensa**
  **DONE IS:** presentación preparada, ensayada con tiempo cronometrado, y con respuestas
  preparadas para las tres preguntas incómodas previsibles: novedad frente al MCP de
  datos.gob.es, validez del banco anotado por una persona, y qué aporta el modelo pequeño
  si el grande ya funciona.

---

## Riesgos vivos

| Riesgo | Señal de alarma | Corte |
|---|---|---|
| Novedad insuficiente frente al prior art | Óscar no acepta la reformulación en 0.3 | Replantear tema en septiembre, no en enero |
| El banco se come el calendario | Menos de 40 preguntas a mitad de la fase 4 | Bajar a 80 preguntas y 4 ciudades |
| Fase 6 desborda | Fase 5 acaba después de abril | Cortar la 6; el TFM se sostiene sin ella |
| Portales que cambian bajo los pies | Falla la cosecha semanal | El índice local ya lo cubre; documentar el incidente como hallazgo |
| Tiempo (trabajo + familia) | Dos semanas sin avance | Núcleo mínimo: fases 3, 4, 5, 7 |
