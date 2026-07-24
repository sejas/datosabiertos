---
type: note
title: Plan TFM — Agente MCP para catálogos de datos abiertos de ciudades
date: 2026-07-25
tags: [tfm, muia, upm, plan, mcp, datos-abiertos]
---

# Plan TFM — Agente MCP para explorar catálogos de datos abiertos de ciudades

**Director:** Óscar Corcho (OEG, DIA-UPM) · **Curso:** 2026/27 · **Créditos:** 15 ECTS
**Difusión prevista:** Encuentro Nacional de Datos Abiertos 2027 (+ workshop ESWC/ISWC opcional)

## 1. Problema

Los catálogos de datos abiertos municipales españoles (Madrid, Barcelona, Zaragoza, Las Palmas…) están federados en datos.gob.es y publican metadatos en **DCAT-AP-ES** vía CKAN y SPARQL. Aun así, encontrar un dataset concreto sigue siendo difícil: los buscadores son léxicos, los metadatos son heterogéneos entre ayuntamientos y el usuario no técnico no sabe qué vocabulario usar.

Un agente LLM con acceso a esos catálogos mediante **MCP (Model Context Protocol)** puede convertir preguntas en lenguaje natural ("¿qué datos hay sobre calidad del aire en Las Palmas desde 2020?") en consultas estructuradas sobre el grafo de metadatos, y explicar qué encontró.

## 2. Objetivos

**O1.** Diseñar e implementar un **servidor MCP** que exponga los catálogos DCAT de varias ciudades como herramientas consultables por un agente.
**O2.** Construir un **banco de evaluación** de preguntas en español con respuestas de referencia (dataset + traza de herramientas esperada).
**O3.** Evaluar el agente con distintos modelos y medir calidad, coste y latencia.
**O4 (opcional, decide en fase 4).** Verificar si un **modelo pequeño ejecutándose gratis en el navegador** (WebGPU) sirve como agente MCP con calidad aceptable.

## 3. Pregunta de investigación

> ¿Puede un modelo de lenguaje pequeño, ejecutado localmente en el navegador, actuar como agente MCP sobre catálogos DCAT de datos abiertos con calidad comparable a la de un modelo grande en la nube, y a qué coste en latencia y precisión?

Contribución medible = la respuesta a esa pregunta + el banco de evaluación público (que no existe en español). Eso es lo que convierte el TFM en investigación y no solo en demo.

## 4. Arquitectura

```
Usuario (navegador)
   │  pregunta en lenguaje natural
   ▼
Agente LLM  ──────────────┐
   │  tool calls           │  Modo A: modelo grande vía API (baseline)
   ▼                       │  Modo B: modelo pequeño en el navegador
Servidor MCP               │          (WebLLM / transformers.js + WebGPU)
   ├── buscar_datasets(consulta, ciudad, tema, año)
   ├── detalle_dataset(id)              → metadatos DCAT completos
   ├── listar_distribuciones(id)        → formatos, URLs, licencia
   ├── consultar_sparql(query)          → sobre el grafo de metadatos
   └── comparar_ciudades(tema)          → mismo tema en varios municipios
        │
        ▼
   Catálogos: datos.gob.es (SPARQL/DCAT-AP-ES) + APIs CKAN municipales
```

Decisiones de diseño (justificar en la memoria):
- **MCP y no plugin ad-hoc**: protocolo abierto, reutilizable desde cualquier cliente (Claude, VS Code, agente propio) — argumento de sostenibilidad para la comunidad de datos abiertos.
- **Índice local de metadatos**: volcado periódico de los catálogos a un almacén propio para evitar depender de la latencia y las caídas de las APIs municipales.
- **Sin RAG sobre texto libre**: las herramientas consultan el grafo de metadatos estructurado; el LLM decide qué herramienta usar, no recupera fragmentos.

## 5. Fases

| # | Fase | Contenido | Salida | Semanas |
|---|---|---|---|---|
| 0 | Arranque | Matrícula (jul–sep), reunión de alcance con Óscar, lectura dirigida | Alcance firmado | sep 2026 |
| 1 | Estado del arte | LLM+KG, agentes con herramientas, MCP, calidad de metadatos DCAT, portales españoles | Cap. 2 de la memoria | 4 |
| 2 | Análisis de catálogos | Inventario de 4–6 ciudades: APIs, cobertura DCAT-AP-ES, huecos y heterogeneidad | Cap. 3 + índice local | 3 |
| 3 | Servidor MCP v1 | Herramientas del §4, índice local, cliente de prueba | Software funcionando | 5 |
| 4 | Banco de evaluación | 80–120 preguntas en español (fácil/media/difícil, mono y multiciudad) con respuesta de referencia | Dataset publicado | 4 |
| 5 | Experimento A | Baseline: modelo grande en la nube. Métricas §6 | Resultados A | 2 |
| 6 | Experimento B (opcional) | Modelo pequeño en navegador (Qwen2.5-1.5B/3B cuantizado q4, WebGPU). Si falla el tool-calling: LoRA sobre trazas del experimento A | Resultados B + comparativa | 4 |
| 7 | Memoria | Redacción completa, revisión con el director | Memoria | 5 |
| 8 | Paper + defensa | Paper de workshop (ESWC/ISWC) y/o Encuentro Nacional de Datos Abiertos; preparación de defensa | Paper enviado + defensa | 3 |

**Puerta de decisión tras la fase 5:** si el baseline no funciona bien, el problema está en las herramientas, no en el modelo → arreglar MCP antes de tocar modelos pequeños. La fase 6 es opcional por diseño; el TFM se sostiene sin ella.

## 6. Métricas

- **Acierto de recuperación**: ¿el dataset correcto está en el top-k? (precision@k, MRR)
- **Corrección de la traza de herramientas**: ¿llamó a las herramientas correctas con los argumentos correctos?
- **Fidelidad de la respuesta**: ¿la respuesta en lenguaje natural se sostiene con los metadatos devueltos? (sin alucinar datasets inexistentes — métrica clave)
- **Latencia**: tiempo hasta la primera respuesta y tiempo total, por modo.
- **Coste**: € por consulta en la nube vs 0 € en navegador; consumo de memoria en el cliente.

## 7. Criterios de aceptación

Hecho significa:
1. Servidor MCP instalable con un comando, documentado, en repositorio público con licencia abierta.
2. Banco de evaluación publicado (Zenodo + GitHub) con DOI y licencia.
3. Experimento A completo y reproducible con un script.
4. Memoria con la estructura del §8, revisada por el director.
5. Al menos un envío: Encuentro Nacional de Datos Abiertos y/o workshop con revisión por pares.

## 8. Estructura de la memoria

1. **Introducción** — motivación, objetivos, contribuciones, estructura.
2. **Estado del arte** — datos abiertos y DCAT-AP-ES; agentes LLM con herramientas; MCP; modelos pequeños y ejecución en el navegador; trabajos previos de OEG.
3. **Análisis del dominio** — catálogos municipales estudiados, heterogeneidad de metadatos, limitaciones encontradas.
4. **Diseño** — arquitectura, catálogo de herramientas MCP, decisiones y alternativas descartadas.
5. **Implementación** — tecnologías, índice local, despliegue, cliente en el navegador.
6. **Evaluación** — banco de preguntas, metodología, métricas, resultados A y B, análisis de errores.
7. **Conclusiones y trabajo futuro** — respuesta a la pregunta de investigación, limitaciones, líneas abiertas.
8. **Bibliografía** · **Anexos** — catálogo de herramientas, ejemplos de preguntas, resultados completos.

Nota: la memoria se escribe **en paralelo**, no al final. Cada fase alimenta su capítulo (fase 1→cap. 2, fase 2→cap. 3, fase 3→cap. 4-5, fases 5-6→cap. 6).

## 9. Riesgos

| Riesgo | Mitigación |
|---|---|
| APIs municipales lentas, caídas o inconsistentes | Índice local con volcado periódico; documentar los fallos como hallazgo del cap. 3 |
| Modelos pequeños incapaces de hacer tool-calling fiable | Fase 6 es opcional; alternativa: LoRA sobre trazas del baseline; si aun así falla, ese resultado negativo también es publicable |
| WebGPU inmaduro o limitado por RAM del cliente | Medir y reportar el límite; ofrecer alternativa con modelo local fuera del navegador |
| Falta de tiempo (trabajo + familia) | Fases 5–8 son el núcleo mínimo; la 6 se corta sin romper el TFM |
| Alcance que crece | El §7 es el contrato; cualquier añadido va a "trabajo futuro" |

## 10. Calendario aproximado

- **jul–sep 2026** — matrícula (periodo ordinario) + reunión de alcance
- **oct–dic 2026** — fases 1–3 (estado del arte, análisis, servidor MCP v1)
- **ene–mar 2027** — fases 4–5 (banco de evaluación, baseline); deadline de workshop ESWC ~feb–mar
- **abr–jun 2027** — fase 6 (opcional) + fase 7 (memoria)
- **jun–sep 2027** — Encuentro Nacional de Datos Abiertos + defensa

La defensa puede ser en cualquier momento del curso; si se alarga, la rematrícula cuesta el 25%.

## 11. Primeros pasos concretos

- [ ] Responder a Óscar eligiendo el tema y proponiendo reunión en septiembre
- [ ] Matricularse del TFM en el periodo ordinario (julio–septiembre 2026)
- [ ] Explorar la API de datos.gob.es y el endpoint SPARQL; anotar qué ciudades tienen DCAT-AP-ES decente
- [ ] Prototipo mínimo: servidor MCP con una sola herramienta (`buscar_datasets`) sobre una ciudad
- [ ] Preguntar a Óscar por trabajos previos del grupo sobre calidad de metadatos en portales españoles
