# `datosabiertos` — índice local de catálogos municipales

Implementa los TODOs **3.1** (índice local), **3.3** (cosecha cortés) y adelanta el **3.2**
(trazabilidad de procedencia). Sin dependencias externas: solo la biblioteca estándar de
Python 3.11+.

## Uso

```bash
python -m datosabiertos.index build                 # cosecha e indexa el corpus entero (idempotente)
python -m datosabiertos.index build --portal madrid --portal reus
python -m datosabiertos.index build --sin-crudo     # sin guardar el JSON original: índice mucho menor
python -m datosabiertos.index portales              # corpus y huecos pendientes de la fase 2.1
python -m datosabiertos.index buscar "calidad del aire" --portal malaga --anio 2025
python -m datosabiertos.index estado                # tamaño, recuentos y últimas cosechas
python -m datosabiertos.index errores --portal reus # errores registrados, consultables también por SQL
python -m unittest discover -s tests      # 21 tests, sin red
```

Configuración por entorno: `TFM_CORREO_CONTACTO`, `TFM_CONCURRENCIA_POR_HOST`,
`TFM_RUTA_INDICE`, `TFM_RESPETAR_DISALLOW`… todo en `configuracion.py`.

## Resultado de la construcción (25/07/2026)

Corpus completo, máquina doméstica (Raspberry Pi 5), red doméstica:

| Portal | Datasets | Peticiones | Reintentos | Tiempo | Sin licencia |
|---|---:|---:|---:|---:|---:|
| Málaga | 1.371 | 14 | 0 | 131 s | 0 |
| Madrid | 672 | 7 | 0 | 21 s | 0 |
| Barcelona | 555 | 6 | 0 | 52 s | 0 |
| Córdoba | 145 | 2 | 0 | 2 s | **145** |
| Reus | 119 | 3 | 1 (429) | 21 s | 0 |
| **Total** | **2.862** | **32** | **1** | **137 s** | **145** |

**23.390 distribuciones · 1.535 keywords · 63,4 MB** de índice con el JSON original incluido.
Con `--sin-crudo` baja a una fracción: el crudo solo hace falta para las fases 2.2 y 2.4.

137 segundos para 2.862 datasets con 32 peticiones totales. El tiempo es casi todo espera
de cortesía, no proceso: Málaga impone `Crawl-Delay: 10` y son 14 páginas.

## Hallazgos de la primera cosecha real

- **Córdoba: 145 de 145 datasets sin licencia declarada** (83 dicen `notspecified`, 62 no
  traen el campo). El análisis previo decía 43 %; era un error de cálculo que solo contaba
  los ausentes e ignoraba los `notspecified`. Córdoba aporta 145 de los 153 datasets sin
  licencia de todo el corpus de 16 portales: prácticamente toda la anomalía nacional está
  en un solo portal.
- **Reus también declara `Crawl-Delay: 10` y `Disallow: /api/`**, no solo Málaga, y devolvió
  un **429** en la primera petición. El backoff lo absorbió sin perder datos.
- Ningún portal del corpus necesitó el plan B (`package_list` + `package_show`).

## Decisiones que conviene conocer

**`Disallow` no aborta, `Crawl-Delay` sí se respeta.** Málaga y Reus declaran
`Disallow: /api/` a la vez que publican y documentan su API CKAN, y la Directiva (UE)
2019/1024 obliga al organismo a ofrecer justamente esa API. Se registra el conflicto como
aviso y se continúa, respetando siempre el `Crawl-Delay`. Para la lectura estricta:
`TFM_RESPETAR_DISALLOW=1`.

**La ausencia de licencia es un dato, no un hueco.** `licencia.declarada = 0` y el
identificador reservado `no-declarada`. Nunca se rellena con CC-BY. Dos tests lo blindan.

**La procedencia se sella en `ConectorCatalogo.cosechar()`, no en cada conector.** Un
conector nuevo no puede olvidarse de ella, y `Almacen.insertar()` lanza `ValueError` si
falta. Es lo que garantiza el criterio del TODO 3.2 cuando lleguen las herramientas MCP.

**Escritura en un solo hilo.** Los portales se cosechan en paralelo (3 a la vez) pero el
volcado a SQLite es secuencial: `sqlite3` no es seguro entre hilos y el cuello de botella
es la red, no el disco.

## Añadir un portal nuevo (fase 2.1: Gijón, Zaragoza)

Tres pasos, sin tocar nada más. Está documentado en `conectores/base.py`:

1. `datosabiertos/conectores/<familia>.py` con una subclase de `ConectorCatalogo` que implemente
   `listar_crudos()` y `normalizar(crudo)`.
2. Registrar la familia en `FAMILIAS`, en `conectores/__init__.py`.
3. Dar de alta el portal en `CORPUS`, en `configuracion.py`.

Cortesía, reintentos, esquema, FTS5, procedencia y CLI ya funcionan para el conector nuevo.

## Pendiente

- Programación semanal de la cosecha (criterio del TODO 3.3 aún sin cubrir).
- `num_distribuciones` en el resumen de cosecha se calcula en la CLI, no en el conector.
- Los conectores de Gijón y Zaragoza (TODO 2.1).
