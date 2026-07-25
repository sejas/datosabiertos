---
type: note
title: Esquema del banco de evaluación BDAM-es
date: 2026-07-25
tags: [tfm, banco-evaluacion, esquema, mcp, datos-abiertos]
status: v1 — cubre el TODO 4.1
---

# Esquema del banco de evaluación BDAM-es

**BDAM-es** = *Banco de preguntas sobre Datos Abiertos Municipales, en español*.

Documento normativo del formato. El esquema formal está en
[`esquema.json`](esquema.json) (JSON Schema 2020-12) y lo comprueba
[`validar.py`](validar.py); aquí se explica **por qué cada campo existe** y qué se pierde
si se quita. Un banco de evaluación es un instrumento de medida: si el formato no está
justificado, las métricas que salen de él tampoco lo están.

Metodología, licencia y limitaciones: [`README.md`](README.md).

---

## 1. De dónde sale este formato

El TFM se reformuló en julio de 2026 al descubrir que el servidor MCP sobre catálogos
españoles ya existe (§7 de [`../docs/02-analisis-catalogos.md`](../docs/02-analisis-catalogos.md)).
El banco pasa de contribución secundaria a **contribución principal**: no existe ningún
benchmark en español de preguntas sobre catálogos de datos abiertos con respuestas de
referencia y trazas de herramientas.

El formato toma tres decisiones de tres familias de trabajos previos:

| De dónde | Qué se toma | Campo resultante |
|---|---|---|
| Benchmarks de *tool-calling* (ToolBench, API-Bank, FlowBench, BFCL) | Evaluar la **secuencia de llamadas**, no solo la respuesta final | `traza_esperada` |
| QA con preguntas sin respuesta (SQuAD 2.0 y sucesores) | Marcar explícitamente las preguntas cuya respuesta correcta es «no existe» | `sin_respuesta`, `motivo_sin_respuesta`, `comprobaciones_vacias`, `datasets_proximos` |
| Recuperación de información (precision@k, MRR) | Separar «encontró el documento» de «lo explicó bien» | `datasets_referencia` con `rol`, frente a `criterios_respuesta` |

> **Aviso de estado.** La fase 1 (estado del arte) aún no está hecha: los TODO 1.1–1.4
> siguen abiertos. Las referencias anteriores son las que motivaron el diseño, no una
> revisión sistemática. Cuando se cierre el TODO 1.1 hay que volver aquí y **o bien citar
> con precisión de dónde sale cada decisión, o bien cambiarla**. Escribirlo ahora y no
> revisarlo después sería exactamente el pecado que el TODO 4.1 pide evitar.

Lo que **no** se copia de esos benchmarks, y por qué:

- **Nada de *simulated APIs*.** ToolBench evalúa contra APIs sintéticas. Aquí las cuatro
  herramientas consultan un índice real de 2.862 datasets municipales reales. Un fallo del
  agente es un fallo sobre metadatos que existen, con sus erratas y sus huecos.
- **Nada de respuesta única exacta.** El campo `respuesta_referencia` **no** se compara por
  igualdad de cadenas: se puntúa contra `criterios_respuesta`. Una respuesta correcta
  redactada de otra forma tiene que puntuar igual.
- **Nada de puntuación agregada única.** No hay un campo «puntos». Las métricas del §6 de
  [`../PLAN.md`](../PLAN.md) se calculan desde los campos, no se anotan a mano.

---

## 2. Estructura del fichero

```jsonc
{
  "version_esquema": 1,
  "identificador_banco": "bdam-es",
  "version_banco": "0.1.0",
  "fecha": "2026-07-25",
  "licencia": "CC-BY-SA-4.0",
  "doi": "",
  "instantanea_indice": { … },   // contra qué se verificó
  "preguntas": [ { … } ]
}
```

### Campos de cabecera

| Campo | Obligatorio | Por qué existe |
|---|---|---|
| `version_esquema` | sí | Un consumidor tiene que poder rechazar un fichero que no entiende. Cambia solo ante una incompatibilidad. |
| `identificador_banco` | sí | Prefijo de los ids de pregunta. El validador exige que coincidan: impide mezclar preguntas de dos bancos sin darse cuenta. |
| `version_banco` | sí | Versión semántica del **contenido**. Cada publicación en Zenodo es una versión distinta con su propio DOI. |
| `fecha` | sí | Fecha de la versión. |
| `licencia` | sí | Obligatoria por el §6 del análisis de catálogos: el banco incorpora metadatos de Málaga (`by-sa-40`) y hereda su cláusula de compartir igual. Ver [README §Licencia](README.md#licencia-y-por-qué-es-cc-by-sa-40). |
| `doi` | no | Vacío hasta la primera publicación (TODO 4.4). |
| `instantanea_indice` | sí | Ver abajo. |
| `preguntas` | sí | El contenido. |

### `instantanea_indice`

```jsonc
"instantanea_indice": {
  "ruta": "datos/indice.sqlite",
  "fecha_sincronizacion": "2026-07-25",
  "n_datasets": 2862,
  "n_distribuciones": 23390,
  "version_esquema_indice": 1,
  "portales": ["madrid", "barcelona", "malaga", "cordoba", "reus"]
}
```

**Es lo que hace reproducible al banco, y es lo que más se olvida en los benchmarks de
recuperación.** Las respuestas de referencia son ciertas *sobre una fotografía concreta de
unos portales que cambian todas las semanas*. Sin declarar contra qué instantánea se
verificaron, dentro de seis meses la mitad de las preguntas parecerán erróneas y no habrá
forma de distinguir «el banco estaba mal» de «el portal cambió».

`validar.py --indice` compara `n_datasets` con el índice real y avisa si no cuadran.

---

## 3. La pregunta, campo a campo

### `id` — obligatorio

Patrón `^[a-z0-9-]+-[0-9]{3}$`, con el prefijo del banco: `bdam-es-001`.

Estable y citable: un análisis de errores dice «falla `bdam-es-013`», no «falla la pregunta
de Córdoba». **Los identificadores no se reutilizan**: si una pregunta se retira porque el
portal cambió, su número muere con ella. Reutilizarlo haría que dos artículos que citan
`bdam-es-013` hablen de cosas distintas.

### `pregunta` — obligatorio

Enunciado en español, mínimo 15 caracteres. Redactado **como lo escribiría una persona no
técnica**, que es el usuario del §1 del plan: «¿Dónde puedo consultar…?», no
«dcat:Dataset WHERE theme=…». Se admiten preguntas con presuposición falsa
(`bdam-es-012` da por hecho que las cinco ciudades publican arbolado): son las que miden
si el agente corrige al usuario o le sigue la corriente.

### `dificultad` — obligatorio · `facil` | `media` | `dificil`

No es una opinión, es un criterio operativo:

| Nivel | Criterio |
|---|---|
| `facil` | Una sola llamada basta y el vocabulario de la pregunta aparece casi literal en el título del dataset. Es el suelo: fallar aquí señala a las herramientas, no al modelo. |
| `media` | Exige encadenar dos herramientas, o reformular la consulta (barrera de idioma), o agregar varios resultados en una respuesta. |
| `dificil` | Varias ciudades, o razonamiento sobre licencias/formatos/frescura, o la respuesta correcta contradice lo que la pregunta presupone. |

Sin los tres niveles no se puede distinguir «el modelo es malo» de «este subconjunto es
duro»: es lo que hace útil el análisis de errores del TODO 5.3.

### `tipo` — obligatorio · `monociudad` | `multiciudad`

El eje **comparación entre municipios** es una de las cuatro cosas que el prior art no
cubre (§7 del análisis). Marcarlo como campo, y no deducirlo de `len(ciudades)`, obliga al
anotador a declarar su intención; el esquema comprueba después que ambas cosas concuerden
(`multiciudad` ⇒ ≥2 ciudades, `monociudad` ⇒ exactamente 1).

### `ciudades` — obligatorio

Lista de identificadores de portal (`madrid`, `barcelona`, `malaga`, `cordoba`, `reus`),
los mismos de `tfm.configuracion.CORPUS`. Se usa para tres cosas: cortar los resultados por
ciudad, comprobar que los datasets citados pertenecen a las ciudades declaradas, y
comprobar que la traza no consulta portales que la pregunta no menciona.

En las preguntas sin respuesta indica **dónde se buscó**, que es justamente el dato que
hace falsable la afirmación «no existe».

### `sin_respuesta` — obligatorio · booleano

La marca de pregunta sin respuesta posible. Es **la métrica clave** del §6 del plan
(«sin alucinar datasets inexistentes») y no se puede medir sin ejemplos negativos: un banco
donde toda pregunta tiene respuesta premia al modelo que siempre contesta algo.

Cuando vale `true`, el esquema exige:

- `motivo_sin_respuesta` (ver abajo),
- `datasets_referencia` **vacío** —no hay respuesta de oro que recuperar—,
- al menos **dos** `comprobaciones_vacias`.

Y avisa si no hay ningún criterio negativo (`NO: …`) en `criterios_respuesta`, porque
entonces la pregunta no mide lo que dice medir.

### `motivo_sin_respuesta` — obligatorio si `sin_respuesta`

`tema_inexistente_en_la_ciudad` · `periodo_inexistente` · `formato_inexistente` ·
`granularidad_inexistente` · `fuera_del_corpus`

No todas las ausencias son iguales y no fallan igual. «Reus no publica arbolado»
(`tema_inexistente_en_la_ciudad`) exige descartar antes que el problema sea de idioma;
«Málaga no tiene calidad del aire de 2024» (`periodo_inexistente`) invita a fabricar una
URL cambiando el año, porque el patrón es evidente. Agrupar ambas bajo «alucinó» tiraría
la información más útil del análisis de errores.

### `datasets_referencia` — obligatorio (lista, vacía si `sin_respuesta`)

La respuesta de oro para precision@k y MRR. Cada entrada:

| Campo | Obligatorio | Por qué |
|---|---|---|
| `portal` | sí | Los ids de CKAN solo son únicos dentro de su portal. |
| `identificador` | sí | `dataset.identificador_origen` en el índice; es lo que devuelve la herramienta. |
| `url_origen` | sí | Exigido por el RD 1495/2011 art. 8 (citar la fuente). Es también la vía de verificación humana: se abre y se mira. |
| `titulo` | no | Para que un revisor reconozca el dataset sin abrir la URL, y para detectar cambios en origen (el validador avisa si el título ha cambiado). |
| `rol` | no | `principal` = hay que recuperarlo; `secundario` = coincidencia también válida. |

**Por qué los tres campos y no solo el identificador.** Un identificador suelto no es
verificable por una persona, no dice de qué ciudad es y no sobrevive a un cambio de
plataforma. Los tres juntos son la unidad mínima de procedencia que el TODO 3.2 exige a las
herramientas; el banco se la exige a sí mismo.

**Por qué `rol`.** Sin él, una pregunta con seis datasets correctos (`bdam-es-009`, los
seis presupuestos de Reus) y otra con uno principal más un cuasi-válido
(`bdam-es-001`) se puntuarían igual, y no son lo mismo. `principal` alimenta el acierto
exacto; `principal` + `secundario` alimentan precision@k.

### `datasets_proximos` — opcional, solo si `sin_respuesta`

Los cuasi-aciertos: lo más parecido que **sí** existe. En `bdam-es-015` son los conjuntos
de VIMCORSA, la empresa municipal de vivienda de Córdoba, que existen pero hablan de
subvenciones y no de precios de alquiler.

Existe como campo separado porque la distinción es el corazón de la medida de alucinación:
**ofrecerlos es correcto; presentarlos como la respuesta pedida es un fallo.** Si vivieran
en `datasets_referencia`, un evaluador automático marcaría el fallo como acierto.

### `traza_esperada` — obligatorio (≥1 llamada)

Secuencia mínima de llamadas a herramientas. Es la referencia de la métrica «corrección de
la traza» del §6 del plan.

```jsonc
{
  "herramienta": "buscar_datasets",
  "argumentos": { "consulta": "arbolado viario", "ciudad": "barcelona" },
  "obligatoria": false,
  "resultado_esperado": "vacio",
  "nota": "Callejón sin salida legítimo: la consulta en castellano no devuelve nada."
}
```

- **`herramienta`** — solo las cuatro del §4 de [`PLAN.md`](../PLAN.md):
  `buscar_datasets`, `detalle_dataset`, `listar_distribuciones`, `comparar_ciudades`.
  `consultar_sparql` queda **fuera** mientras el TODO 3.5 no se resuelva: incluirla en el
  banco sería comprometerse con una decisión de diseño que todavía está abierta.
- **`argumentos`** — un argumento ausente significa «no se exige», nunca «debe ir vacío».
  Exigir la ausencia haría fallar trazas correctas que además filtran por tema.
- **`obligatoria`** — distingue lo que hay que hacer de lo que es aceptable hacer. Sin este
  campo, cualquier llamada de más contaría como error y se penalizaría a un agente
  prudente que verifica antes de responder.
- **`resultado_esperado`** — `con_resultados` | `vacio`. Permite anotar **callejones sin
  salida legítimos**: en `bdam-es-006` y `bdam-es-009` buscar en castellano sobre un
  catálogo en catalán devuelve cero, y reformular es la conducta correcta. Sin este campo
  el banco castigaría el comportamiento que quiere premiar.
- **`nota`** — texto libre para el revisor humano.

**Firmas y una divergencia declarada.** El validador comprueba los nombres de argumento
contra estas firmas:

| Herramienta | Argumentos aceptados |
|---|---|
| `buscar_datasets` | `consulta`, `ciudad`, `tema`, `anio`, `limite` |
| `detalle_dataset` | `id` |
| `listar_distribuciones` | `id` |
| `comparar_ciudades` | `tema`, `ciudades` |

Dos diferencias respecto al §4 del plan, ambas deliberadas:

1. **`anio` y no `año`.** El argumento viaja en JSON y en línea de órdenes
   (`python -m tfm.index buscar --anio`), donde una eñe es una fuente inagotable de
   problemas de codificación. La CLI del índice ya usa `anio`; el banco no inventa una
   tercera forma.
2. **`comparar_ciudades` acepta `ciudades`**, que el plan no contempla. Sin ese argumento
   no se puede pedir «compara solo Málaga y Barcelona» (`bdam-es-008`). Es una **propuesta
   del banco al diseño de la herramienta** (TODO 3.4), anotada aquí para que no pase por
   descuido.

**El `id` de las herramientas es cualificado: `<portal>:<identificador_origen>`.** Los
identificadores de CKAN solo son únicos dentro de su portal, y el índice indexa cinco. Un
`detalle_dataset("calidad-del-aire")` es ambiguo entre Córdoba y Málaga; un
`detalle_dataset("cordoba:75add831-…")` no lo es. El validador exige además que ese id
corresponda a algún dataset de referencia o próximo de la propia pregunta: así una traza no
puede apuntar a un dataset que la pregunta nunca menciona.

### `comprobaciones_vacias` — obligatorio (≥2) si `sin_respuesta`

```jsonc
"comprobaciones_vacias": [
  { "consulta": "arbolado", "ciudad": "reus" },
  { "consulta": "arbrat",   "ciudad": "reus" }
]
```

**Es el campo que convierte «no existe» en una afirmación falsable.** `validar.py --indice`
reejecuta cada consulta contra el índice y **falla si alguna devuelve resultados**. Sin
esto, la marca `sin_respuesta` sería una opinión del anotador, y bastaría con que un portal
publicara el dataset que faltaba para que el banco quedara silenciosamente mal.

Se exigen **dos como mínimo** porque una sola consulta no distingue «no existe» de «no lo
encontré con esa palabra». En los catálogos en catalán hacen falta las dos lenguas.

### `respuesta_referencia` — obligatorio (≥30 caracteres)

Respuesta modelo en español, con procedencia (título, URL, licencia, fechas). **No es la
única redacción válida** y no se compara por igualdad: sirve para que un anotador humano
entienda a qué se aspira y como referencia para el juez de la fase 5.

Todas las respuestas de referencia del banco citan la fuente y la licencia. Es intencionado:
una respuesta que acierta el dataset pero se come la atribución **no es una respuesta
correcta** (riesgo 2 del §6 del análisis de catálogos).

### `criterios_respuesta` — obligatorio (≥1)

Lista de afirmaciones comprobables. Las que empiezan por `NO:` son prohibiciones.

```jsonc
"criterios_respuesta": [
  "Afirma que el dataset no declara licencia",
  "NO: afirma o insinúa que la licencia es CC-BY, CC0 u otra licencia concreta"
]
```

Es lo que hace **auditable** la métrica de fidelidad del TODO 5.2, que exige «una rúbrica o
un LLM-juez con sus prompts versionados, no "a ojo"». Con estos criterios el juez —humano o
modelo— responde sí/no a preguntas concretas en lugar de emitir una nota global, y dos
jueces pueden discrepar sobre un criterio identificable en vez de sobre una impresión.

Los criterios negativos son los que miden alucinación. Que existan también en preguntas
**con** respuesta es deliberado: en `bdam-es-007` el criterio
`NO: menciona formatos que el dataset no tiene, como JSON, SHP o GeoJSON` captura el error
más probable, que no es no encontrar el dataset sino adornarlo.

### `etiquetas` — opcional, vocabulario cerrado

`recuperacion-directa`, `procedencia`, `licencia`, `licencia-no-declarada`,
`licencia-compartir-igual`, `formatos`, `frescura`, `conteo`, `agregacion`, `comparacion`,
`multiciudad`, `multilingue`, `heterogeneidad`, `reintento-de-consulta`,
`ausencia-parcial`, `sin-respuesta`, `alucinacion`, `cordoba-peor-caso`.

Marcan **el fenómeno que la pregunta ejercita**, que es la unidad de análisis útil: no
interesa tanto «acertó 11 de 15» como «falla sistemáticamente cuando el catálogo está en
catalán». El vocabulario es cerrado (enum) a propósito: unas etiquetas libres se convierten
en cincuenta sinónimos y dejan de servir para agrupar.

### `notas_anotador` — obligatorio (≥20 caracteres)

Por qué la pregunta es así, qué la hace difícil y qué se comprobó. Es lo que permite al
**segundo anotador** del TODO 4.3 reproducir el criterio en vez de adivinarlo, y lo que
permite resolver una discrepancia discutiendo el criterio y no la intuición.

### `anotador` y `fecha_anotacion` — obligatorios

`anotador` es un identificador seudonimizado (`A1`, `A2`, …). Sin saber **quién** anotó
cada pregunta no se puede calcular el acuerdo entre anotadores (Cohen's κ) que exige el
TODO 4.3, y un banco anotado por una sola persona sin decirlo se presenta como una
referencia cuando es una opinión.

### `verificacion` — obligatorio

```jsonc
"verificacion": {
  "metodo": "indice-local",
  "fecha": "2026-07-25",
  "comandos": ["python3 -m tfm.index buscar 'arbolado' --portal reus --limite 5"]
}
```

- **`metodo`** — `indice-local` | `portal-en-vivo` | `ambos`. Que el TODO 4.2 pida
  verificar «a mano en el portal de origen» y aquí ponga `indice-local` **no se disimula**:
  el campo existe para que la diferencia sea visible y contable, no para taparla. Ver
  [README §Limitaciones](README.md#limitaciones-conocidas).
- **`comandos`** — la orden exacta que reproduce la comprobación. Es la diferencia entre
  «verificado» y «verificable».

---

## 4. Reglas que el esquema no puede expresar

`validar.py` añade estas comprobaciones semánticas, con el id de la pregunta y el campo
exacto en cada mensaje de error:

1. Identificadores únicos y con el prefijo del banco.
2. Toda ciudad citada pertenece a la instantánea del índice.
3. Todo dataset citado pertenece a una de las `ciudades` declaradas.
4. Toda pregunta con respuesta tiene al menos un dataset con `rol: principal`.
5. Los nombres de argumento existen en la firma de su herramienta.
6. Todo `ciudad` de la traza está en `ciudades`.
7. Todo `id` de `detalle_dataset` / `listar_distribuciones` es canónico y apunta a un
   dataset de la propia pregunta.
8. *(aviso)* Las preguntas `sin_respuesta` llevan la etiqueta `sin-respuesta` y al menos un
   criterio negativo.
9. Con `--indice`: los datasets existen, las URL coinciden y las `comprobaciones_vacias`
   siguen devolviendo cero.
10. Con `--composicion`: reparto del TODO 4.2 (≥15 % multiciudad, ≥10 % sin respuesta,
    las tres dificultades presentes, todas las ciudades cubiertas y Córdoba entre ellas).

---

## 5. Qué se dejó fuera y por qué

| Descartado | Motivo |
|---|---|
| Campo `puntuacion` / `peso` por pregunta | Mezcla el instrumento con el resultado. Los pesos son decisión del arnés de evaluación (TODO 5.1), no del banco, y así se pueden cambiar sin reeditar el banco. |
| Respuesta correcta como texto único a comparar | La igualdad de cadenas mide redacción, no comprensión. Se resuelve con `criterios_respuesta`. |
| Traza como grafo con dependencias entre llamadas | Complejidad que ninguna pregunta actual necesita. Se añadirá cuando exista una que la exija, no antes. |
| Preguntas con `consultar_sparql` | El TODO 3.5 no está decidido. Un banco no debe fijar una decisión de diseño abierta. |
| Campo de idioma de la pregunta | Todas son en español, por definición del banco. Si algún día hay preguntas en catalán o gallego, será un cambio de `version_esquema`. |
| Traducción al inglés de las preguntas | Tentador para difusión, pero convertiría el banco en otro benchmark bilingüe más. Su valor es ser **en español**. |

---

## 6. Cómo se valida

```bash
python3 bench/validar.py bench/preguntas.json                              # estructura + semántica
python3 bench/validar.py bench/preguntas.json --indice datos/indice.sqlite # + contra el índice
python3 bench/validar.py bench/preguntas.json --composicion                # + reparto del TODO 4.2
python3 bench/validar.py bench/preguntas.json --json                       # salida legible por máquina
```

Devuelve 0 si no hay errores y 1 si los hay. Los avisos no hacen fallar. Solo biblioteca
estándar de Python 3.11+: el banco se publica suelto en Zenodo y el validador tiene que
funcionar sin el resto del repositorio y sin `pip install`.
