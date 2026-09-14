# Servidor MCP — prototipo v1 (TODO 3.4)

Expone las cuatro herramientas del catálogo (véase el [README](../../README.md#herramientas-mcp)) sobre el índice local.
**Cero dependencias**: JSON-RPC 2.0 sobre stdio con la biblioteca estándar.

```bash
python -m tfm.index build     # una vez: construye el índice
python -m tfm.mcp             # arranca el servidor (habla por stdin/stdout)
python -m unittest discover -s tests   # 59 tests, sin red
```

## Herramientas

| Herramienta | Argumentos | Devuelve |
|---|---|---|
| `buscar_datasets` | `consulta`, `ciudad?`, `tema?`, `anio?`, `limite=10` | Fichas ordenadas por relevancia (bm25) |
| `detalle_dataset` | `id` (`ciudad:id`) | Ficha completa con temas y palabras clave |
| `listar_distribuciones` | `id` | Formatos, URLs y tamaños |
| `comparar_ciudades` | `tema`, `ciudades?`, `limite_por_ciudad=3` | Qué publica cada ciudad, **y quién no publica nada** |

`consultar_sparql` no está, deliberadamente: el índice es SQLite, no un *triplestore*, y de
los tres proyectos del prior art que la exponen uno la desactivó por diseño y otro la
restringe con cuatro salvaguardas. El argumento completo está en
[docs/03-prior-art.md](../../docs/03-prior-art.md) §5.5, y cierra el TODO 3.5 para la v1.

## Dos transportes

```bash
python -m tfm.mcp                      # stdio: para un cliente local
python -m tfm.mcp.http --puerto 8080   # HTTP: para que lo use otra gente
```

El HTTP expone `POST /mcp` (JSON-RPC), `GET /salud`, `GET /` con el catálogo y, si hay
`OPENROUTER_API_KEY`, `POST /chat` (véase más abajo). CORS abierto para que una página web
pueda llamarlo sin pasarela. Abre el índice en **solo lectura**: un endpoint público no debe
poder escribir, y además sin eso los hilos se bloquean entre sí (`database is locked`).

Hay una instancia pública: **`https://datosabiertos.sejas.es/mcp`**.

## Conectarlo a un agente

### Por HTTP, contra el servidor público (sin instalar nada)

```bash
# Claude Code (probado con 2.1: conecta, lista y llama las cuatro herramientas)
claude mcp add --transport http --scope user datosabiertos https://datosabiertos.sejas.es/mcp
claude mcp list                                   # ✔ Connected

# Codex CLI (probado con 0.154; escribe [mcp_servers.datosabiertos] en ~/.codex/config.toml)
codex mcp add datosabiertos --url https://datosabiertos.sejas.es/mcp

# Gemini CLI
gemini mcp add --transport http datosabiertos https://datosabiertos.sejas.es/mcp
```

Cursor (`.cursor/mcp.json`) y VS Code (`.vscode/mcp.json`) aceptan la URL directamente:

```json
{ "mcpServers": { "datosabiertos": { "url": "https://datosabiertos.sejas.es/mcp" } } }
{ "servers":    { "datosabiertos": { "type": "http", "url": "https://datosabiertos.sejas.es/mcp" } } }
```

Claude Desktop solo habla *stdio*; el puente `mcp-remote` (Node ≥ 20) lo resuelve en
`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "datosabiertos": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://datosabiertos.sejas.es/mcp", "--transport", "http-only"]
    }
  }
}
```

### Por stdio, con el repositorio clonado

```json
{
  "mcpServers": {
    "datosabiertos": {
      "command": "python3",
      "args": ["-m", "tfm.mcp"],
      "cwd": "/ruta/a/datosabiertos"
    }
  }
}
```

Vale para Claude Desktop, Claude Code (`.mcp.json`) y cualquier cliente con transporte
stdio. Probado con una sesión JSON-RPC completa por subproceso: `initialize` →
`notifications/initialized` → `tools/list` → `tools/call`.

Un primer prompt que obliga a citar: *«Usa las herramientas de datosabiertos: ¿qué datos
abiertos publica Málaga sobre calidad del aire? Para cada dataset dame el título, la
url_origen tal cual la devuelve la herramienta, la fecha de modificación y si el portal
declara licencia. Si no hay resultados, dilo sin inventar nada.»*

## El chat alojado (`POST /chat`)

`chat.py` es el experimento A del plan: el bucle de agente corre en el servidor con un
modelo de OpenRouter y *tool calling* nativo, usando **los mismos `inputSchema`** que ve un
cliente MCP. Responde en SSE con un evento por paso (`paso`, `delta`, `fin`, `error`) para
que la página pinte la traza. El cliente solo manda mensajes `user`/`assistant`; el prompt
del sistema lo pone el servidor. Cuesta dinero, así que hay tope por IP y tope diario
(`TFM_CHAT_LIMITE_IP`, `TFM_CHAT_VENTANA`, `TFM_CHAT_LIMITE_DIA`); superado, responde 429 e
invita a conectar el MCP al propio agente del visitante.

## Las tres decisiones que importan

**1. La lógica no sabe qué es MCP.** `herramientas.py` son funciones Python que reciben un
`Almacen` y devuelven `dict`. `servidor.py` es solo transporte. Así los tests del §4 no
necesitan hablar JSON-RPC, y el cliente en el navegador de la fase 6 puede llamar a las
mismas funciones sin servidor por medio.

**2. A mano en vez del SDK oficial.** Son ~120 líneas y el precio de la dependencia no se
paga todavía: corre en la Raspberry Pi sin `pip install`, y los tests del protocolo van sin
red. Cuando hagan falta *resources*, *prompts*, *sampling* o HTTP *streamable*, se migra
tocando solo `servidor.py`.

**3. La ausencia viaja como instrucción, no como lista vacía.** Cuando no hay resultados, la
respuesta lleva un campo `sin_resultados` con el texto *"NO inventes uno: dilo
explícitamente"*. Igual con la licencia: si el portal no la declara, sale
`licencia_declarada: false` más una `advertencia` en prosa. Va en el *payload* de la
herramienta, no en el prompt del sistema, porque el prompt lo controla el cliente y el
payload lo controlamos nosotros. Es lo que hace medible la métrica de fidelidad de la fase 5.

## Limitación medida: el idioma parte el índice en dos

El prototipo busca con FTS5 sobre el texto del catálogo, y **los catálogos de Barcelona y
Reus están en catalán**. Medido contra el índice real:

| Consulta | Resultados en Barcelona |
|---|---:|
| `contaminacion` | **0** |
| `contaminació` | 2 |
| `aire` | 2 |
| `qualitat de l aire` | 2 |

Una pregunta en español sobre Barcelona falla salvo que la palabra coincida por casualidad
en las dos lenguas. No es un fallo del modelo: es el índice el que no puede responder. Y es
exactamente el tipo de confusión que el TFM quiere separar —cuánto de la dificultad es del
modelo y cuánto de los metadatos—, así que **conviene medirlo antes de arreglarlo**:

1. Ejecutar el banco de la fase 5 con el prototipo tal cual y contar cuántos fallos son de
   idioma. Ese número es un resultado publicable por sí solo.
2. Solo después decidir la mitigación (diccionario es↔ca de términos de dominio, expansión
   de consulta, o índice multilingüe), y volver a medir.

El banco ya tiene 6 preguntas etiquetadas `multilingue` para esto.

## Pendiente

- Paginación en `buscar_datasets`: ahora hay tope de 50 y no hay cursor.
- `comparar_ciudades` compara por coincidencia de texto, no por tema alineado. Depende del
  TODO 2.4 (alineación de vocabulario), que es donde está la investigación de verdad.
- Sin caché: cada llamada golpea SQLite. Para 2.862 datasets sobra; para los 107 municipios
  habrá que medirlo.
- Las URLs de distribución no se comprueban en la llamada. Madrid devuelve 403 a la descarga
  programática, así que un enlace puede fallar sin que el dataset haya desaparecido; la
  herramienta lo advierte en texto.
