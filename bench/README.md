# BDAM-es — Banco de preguntas sobre catálogos de datos abiertos municipales en español

**Estado: v0.2.0, 101 preguntas verificadas contra el índice.** Cubre el TODO 4.1 (esquema
y validador) y la cifra del TODO 4.2 (80–120). Las 15 primeras (`bdam-es-001` a `-015`) las
redactó y verificó a mano el autor; las 86 restantes se redactaron con asistencia de un
modelo de lenguaje y se verificaron mecánicamente contra el índice, pero **están pendientes
de revisión humana** (ver [Limitaciones](#limitaciones-conocidas)).

**Qué mide.** Cada pregunta pide un hecho que un modelo **no puede saber de memoria** —una
URL exacta, una licencia que no es la habitual, una fecha de 2026, un recuento, un título en
catalán, una ausencia— y que sí puede leer en el resultado de una a tres llamadas a las
herramientas MCP. La dificultad está en el conocimiento, no en el razonamiento: la hipótesis
es que con el MCP incluso un modelo pequeño acierta lo que uno grande falla sin él. El campo
`por_que_requiere_mcp` declara, pregunta a pregunta, por qué debería fallar un modelo sin
herramientas. La memoria lo desarrolla en el capítulo 6 (`memoria/cap6-evaluacion.md`).

Un agente LLM puede consultar catálogos de datos abiertos municipales españoles mediante
MCP. Lo que no había forma de saber es **si lo hace bien**: no existe ningún banco de
evaluación en español de preguntas sobre catálogos de datos abiertos con respuestas de
referencia y trazas de herramientas. Los benchmarks de *tool-calling* de referencia
(ToolBench, API-Bank, FlowBench) son genéricos y en inglés. Esto intenta llenar ese hueco.

| | |
|---|---|
| Preguntas | 101 (31 fáciles · 35 medias · 35 difíciles) |
| Multiciudad | 17 (16,8 %) |
| Sin respuesta posible | 18 (17,8 %) |
| Criterios de respuesta | 458, de ellos 168 negativos (`NO: …`) |
| Ámbitos temáticos | los 15 del vocabulario; el mayor, movilidad (14) |
| Ciudades | Madrid, Barcelona, Málaga, Córdoba, Reus |
| Verificadas contra | índice local de 2.862 datasets, sincronizado el 25/07/2026 |
| Licencia | CC BY-SA 4.0 |
| Formato | [`esquema.json`](esquema.json) · documentado en [`esquema.md`](esquema.md) |

## Ficheros

| Fichero | Qué es |
|---|---|
| [`preguntas.json`](preguntas.json) | El banco. |
| [`esquema.json`](esquema.json) | JSON Schema 2020-12 del formato. |
| [`esquema.md`](esquema.md) | Documentación del esquema, campo a campo, con la justificación de cada uno. |
| [`validar.py`](validar.py) | Validador ejecutable. Solo biblioteca estándar de Python 3.11+. |

```bash
python3 bench/validar.py bench/preguntas.json
python3 bench/validar.py bench/preguntas.json --indice datos/indice.sqlite --composicion
```

Salida esperada hoy (la CLI `python3 -m datosabiertos.index buscar` sale con código 1 cuando
no hay resultados: en los `verificacion.comandos` de las comprobaciones vacías eso es lo
esperado, no un fallo):

```
OK · 101 preguntas válidas contra esquema.json y verificadas contra indice.sqlite

Composición · 101 preguntas
  dificultad : dificil=35, facil=31, media=35
  ciudad     : barcelona=32, cordoba=27, madrid=35, malaga=34, reus=23
  multiciudad: 17
  sin respuesta posible: 18
  etiquetas  : agregacion=7, alucinacion=23, ausencia-parcial=12, comparacion=13, conteo=14, cordoba-peor-caso=13, formatos=22, frecuencia-actualizacion=6, frescura=38, heterogeneidad=6, licencia=25, licencia-compartir-igual=10, licencia-no-declarada=13, metadatos-inconsistentes=27, multiciudad=16, multilingue=36, presuposicion-falsa=17, procedencia=40, publicador=14, recuperacion-directa=32, reintento-de-consulta=27, sin-respuesta=18
  ámbito     : catalogo=4, comercio-empleo-economia=9, cultura-ocio-deporte=4, educacion=3, equipamientos-infraestructuras=6, hacienda-presupuestos=5, medio-ambiente=11, movilidad-transporte=14, poblacion-demografia=5, salud=5, sector-publico=9, seguridad-emergencias=6, servicios-sociales=5, turismo=7, urbanismo-vivienda=8
  requiere MCP por: ausencia-verificable=27, cola-larga=21, comparacion-entre-catalogos=14, conteo-exacto=14, contradice-lo-plausible=34, dato-posterior-al-entrenamiento=39, formato-concreto=17, identificador-no-adivinable=46, idioma-del-catalogo=28, licencia-concreta=20, publicador-concreto=12
```

## Metodología

### 1. Corpus

Cinco portales municipales, elegidos en el análisis de julio de 2026
([`../docs/02-analisis-catalogos.md`](../docs/02-analisis-catalogos.md)) para cubrir todo
el espectro de calidad medido, no para quedar bien:

| Portal | Datasets | Nota /100 | Por qué está |
|---|---:|---:|---|
| Madrid | 672 | 98 | El mejor caso: metadatos frescos, DCAT completo, licencia homogénea. |
| Barcelona | 555 | 90 | La higiene de metadatos más limpia del país… con los títulos en inglés. |
| Málaga | 1.371 | 78 | El catálogo más grande y el más rancio. Licencia `by-sa-40`. |
| Córdoba | 145 | 61 | **El peor caso**: 145 de 145 datasets sin licencia declarada, 83 % de recursos en PDF. |
| Reus | 119 | 78 | El mejor caso limpio y pequeño… íntegramente en catalán. |

Faltan Gijón o Zaragoza (portales sin API estándar, TODO 2.1). Cuando existan sus
conectores habrá que añadir preguntas suyas: hoy el banco no mide qué pasa con un portal
que hay que raspar.

### 2. Escritura de las preguntas

Cada pregunta se redacta **partiendo de una necesidad plausible**, no de un dataset. La
diferencia importa: si se parte del dataset salen preguntas cuyo enunciado es el título del
dataset con un «¿dónde está…?» delante, y eso mide búsqueda léxica, no comprensión.

Tres familias, todas presentes a propósito:

1. **Tiene respuesta directa** — el dato existe y se recupera. Suelo de la medida.
2. **Tiene respuesta, pero incómoda** — el dato existe y la respuesta correcta es una mala
   noticia: sin licencia (`bdam-es-004`), solo en HTML y alojado en otro organismo
   (`bdam-es-013`), o publicado solo por tres de las cinco ciudades (`bdam-es-012`).
3. **No tiene respuesta** — el dato no existe. Control de alucinación.

### 3. Verificación

Todas las preguntas se verificaron **contra el índice local**, no contra los portales en
vivo. Es una decisión deliberada y está medida: Madrid devolvió 403 en 9 de 12 descargas
programáticas y Barcelona 503 en 28 de 30 peticiones concurrentes (§4.2 del análisis). Sin
índice local no se puede distinguir un error del modelo de una caída del portal, y la
evaluación deja de ser reproducible.

Cada pregunta lleva en `verificacion.comandos` las órdenes exactas que la comprueban. Las
preguntas sin respuesta llevan además `comprobaciones_vacias`, que `validar.py --indice`
**reejecuta y hace fallar la validación si alguna devuelve resultados**: la afirmación «no
existe» es falsable y se comprueba con un comando, no con la palabra del anotador.

### 4. Qué mide cada campo

- `datasets_referencia` → acierto de recuperación (precision@k, MRR).
- `traza_esperada` → corrección de la traza de herramientas.
- `criterios_respuesta` → fidelidad de la respuesta, con criterios sí/no auditables en vez
  de una nota global.
- `sin_respuesta` + criterios `NO:` → tasa de alucinación.

Detalle y justificación de cada campo: [`esquema.md`](esquema.md).

## Hallazgos que el propio banco documenta

Escribir estas quince preguntas produjo evidencia utilizable en el capítulo 3 de la memoria:

- **Los títulos del catálogo de Barcelona están en inglés.** El CKAN de Barcelona rellena
  `title` en inglés y guarda catalán y castellano en `title_translated`. Buscar «arbolado
  viario» devuelve **cero** resultados; «arbrat viari» devuelve tres. Un agente que consulte
  en español concluirá que Barcelona no publica datos que sí publica.
- **En Reus la búsqueda en castellano falla casi siempre.** «presupuesto» → 0 resultados;
  «pressupost» → los seis. Pero «farmacias» **sí** encuentra «Farmàcies», porque la raíz
  coincide por prefijo tras quitar acentos. El éxito entre lenguas es azaroso, no
  sistemático, y eso es peor que un fallo consistente.
- **Córdoba enlaza en lugar de publicar.** Su conjunto «Calidad del aire» tiene una sola
  distribución, de formato HTML, que apunta a una página de la Junta de Andalucía. El
  dataset existe, el dato no.
- **La ausencia se reparte de forma desigual.** Madrid, Barcelona y Córdoba publican
  inventario de arbolado; Málaga y Reus no publican ninguno. Una pregunta multiciudad
  correcta tiene que decir quién falta.

## Cómo contribuir

Se aceptan preguntas nuevas, correcciones de respuestas de referencia y segundas
anotaciones. El listón es el mismo para todos, incluido el autor:

1. **Parte de una necesidad, no de un dataset.** Si el enunciado es el título del dataset
   con un signo de interrogación, la pregunta no sirve.
2. **Verifica contra el índice**, no contra tu memoria ni contra el buscador del portal.
   Reconstruye el índice si hace falta: `python -m datosabiertos.index build`.
3. **Rellena `verificacion.comandos`** con las órdenes exactas que has ejecutado. Una
   pregunta cuya verificación no se puede reejecutar no entra.
4. **Si marcas `sin_respuesta`, añade al menos dos `comprobaciones_vacias`**, y en catálogos
   catalanes una por lengua. El validador las reejecuta.
5. **Escribe criterios negativos (`NO: …`)** con el error que de verdad esperas, no con uno
   improbable. El criterio útil es el que un modelo fallaría.
6. **Pon tu identificador de anotador** (`A2`, `A3`…). No uses `A1`: es del autor y
   mezclarlo impide calcular el acuerdo entre anotadores.
7. **Ejecuta el validador antes de proponer nada:**
   ```bash
   python3 bench/validar.py bench/preguntas.json --indice datos/indice.sqlite --composicion
   ```
   Tiene que salir `OK`, sin errores.
8. **Si un portal ha cambiado y una pregunta ha dejado de ser correcta**, no la edites en
   silencio: retírala o corrígela subiendo `version_banco`, y **no reutilices su
   identificador**. Alguien puede haberla citado.

## Licencia, y por qué es CC BY-SA 4.0

El banco incorpora metadatos derivados de los cinco portales. El histograma de licencias
sobre los datasets ingeridos manda:

| Licencia en origen | Portal | Efecto |
|---|---|---|
| `cc-by` / `CC-BY-4.0` | Madrid, Barcelona, Reus | Atribución. |
| **`by-sa-40` / `by-sa`** | **Málaga (1.368 datasets)** | **Atribución + compartir igual.** |
| `no-declarada` | Córdoba (145) | Condiciones desconocidas. |

`by-sa-40` es una licencia de **compartir igual**: contamina la obra derivada. Un banco que
contiene títulos, identificadores y URL de datasets de Málaga es una obra derivada de
material `by-sa-40`, así que se publica bajo **CC BY-SA 4.0**, que es la licencia más
restrictiva de las ingeridas. No es una elección estética: es el criterio del TODO 4.4
(«la licencia respeta la más restrictiva de las ingeridas — revisado antes de publicar»).

Consecuencia práctica para quien lo reutilice: **cualquier obra derivada del banco debe
publicarse también como CC BY-SA 4.0**, con atribución a este trabajo y a los ayuntamientos
de origen. Si esto te impide usarlo, el problema no es el banco: es que la licencia de
Málaga funciona exactamente como está diseñada, y esa fricción es en sí misma un hallazgo
sobre el ecosistema español de datos abiertos.

**Los datos en sí no se redistribuyen.** El banco contiene metadatos —títulos,
identificadores, URL de ficha, licencia, formatos, fechas— y no ficheros de datos. Toda
respuesta de referencia cita la URL de origen: el banco es un índice hacia los portales,
nunca un sustituto suyo.

### Atribución de las fuentes

Ayuntamientos de Madrid ([datos.madrid.es](https://datos.madrid.es)), Barcelona
([opendata-ajuntament.barcelona.cat](https://opendata-ajuntament.barcelona.cat/data)),
Málaga ([datosabiertos.malaga.eu](https://datosabiertos.malaga.eu)), Córdoba
([datosabiertos.cordoba.es](https://datosabiertos.cordoba.es)) y Reus
([opendata.reus.cat](https://opendata.reus.cat)). Metadatos cosechados el 25/07/2026 con
concurrencia ≤2 por host, `User-Agent` identificable con contacto y respetando el
`Crawl-Delay` declarado (10 s en Málaga y en Reus).

## Limitaciones conocidas

Se enumeran aquí y no en una nota al pie porque son las preguntas que hará el tribunal.

1. **Tamaño.** 101 preguntas bastan para detectar diferencias grandes entre condiciones
   (20–30 puntos, prueba de McNemar pareada), no diferencias finas entre modelos parecidos.
2. **Redacción asistida y un solo anotador.** Las preguntas `bdam-es-016` a `-101` se
   redactaron con un modelo de lenguaje en cinco lotes y se verificaron con `validar.py
   --indice` y ejecutando sus trazas contra las herramientas reales; **falta la revisión
   humana pregunta a pregunta**. Riesgo de circularidad: preguntas escritas por un modelo
   para medir modelos. Mitigación: la verdad de referencia es el índice, y la condición de
   libro cerrado señala las preguntas memorizables. Todas son de `A1`. Un banco anotado por una sola
   persona es una opinión bien documentada, no una referencia. El TODO 4.3 exige reanotar
   ≥20 % de forma independiente y reportar el acuerdo (Cohen's κ). **Sin hacer.**
3. **Verificación sobre el índice, no sobre el portal en vivo.** El TODO 4.2 pide
   verificación «a mano en el portal de origen»; aquí el método es `indice-local` en las
   101. Es defendible —los portales devuelven 403 y 503 de forma no determinista— pero
   **no es lo que pide el criterio**, y el campo `verificacion.metodo` lo deja registrado
   en lugar de disimularlo. Pendiente: una pasada manual sobre las fichas.
4. **Instantánea única.** Las respuestas son ciertas sobre el índice del 25/07/2026. Los
   portales cambian: parte del banco caducará. `comprobaciones_vacias` y
   `validar.py --indice` sirven justamente para detectarlo pronto.
5. **Corpus incompleto.** Faltan Gijón y Zaragoza, los dos portales sin API estándar, y con
   ellos el caso de un catálogo que hay que raspar.
6. **Sesgo temático, corregido en parte.** En la v0.1.0, 10 de 15 preguntas eran de medio
   ambiente. Desde la v0.2.0 el campo `ambito` lo hace visible y los 15 ámbitos están
   cubiertos, pero educación (3) y cultura (4) siguen escasos.
7. **Sin preguntas conversacionales.** Todas son de un solo turno. El seguimiento
   («¿y en Barcelona?») no se mide.
8. **Las trazas son una referencia, no la única solución válida.** Un agente puede resolver
   `bdam-es-011` con cinco `buscar_datasets` en vez de un `comparar_ciudades`. El campo
   `obligatoria` acota qué es exigible, pero la métrica de traza seguirá penalizando
   caminos correctos poco convencionales. Es una limitación heredada de los benchmarks de
   *tool-calling*, no un descuido.
9. **El estado del arte está sin cerrar.** Las decisiones de diseño del esquema se apoyan en
   trabajos previos que aún no se han revisado sistemáticamente (TODO 1.1–1.4). Ver el aviso
   de estado en [`esquema.md`](esquema.md#1-de-dónde-sale-este-formato).

## Cómo citarlo

Pendiente de DOI (TODO 4.4). Hasta entonces:

> Sejas, A. (2026). *BDAM-es: banco de preguntas sobre catálogos de datos abiertos
> municipales españoles en español*, v0.2.0. Trabajo Fin de Máster, Máster Universitario en
> Inteligencia Artificial, Universidad Politécnica de Madrid. Director: Óscar Corcho.

Al citarlo, indica la `version_banco` y la `fecha_sincronizacion` de la instantánea: sin
ellas los resultados no son comparables.
