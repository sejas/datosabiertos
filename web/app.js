/**
 * Cliente en el navegador: índice SQLite + agente con modelo pequeño por WebGPU.
 *
 * Dos modos, y el orden importa:
 *
 * 1. **Modo directo**: llama a las herramientas sin ningún modelo. Funciona en cualquier
 *    navegador, sin WebGPU y sin descargar pesos. Es la garantía de que la página sirve
 *    para algo aunque el experimento B falle, y además es el patrón de referencia contra el
 *    que comparar al agente: si el modo directo encuentra el dataset y el agente no, el
 *    fallo es del modelo, no del índice.
 * 2. **Modo agente**: modelo pequeño cuantizado vía WebLLM. Coste de inferencia: 0 €, porque
 *    corre en la máquina del usuario.
 *
 * La traza de llamadas se muestra siempre. Es una de las métricas del §6 del plan, y verla
 * es la única forma de distinguir "el modelo eligió mal la herramienta" de "la herramienta
 * no encontró nada".
 */

import { CATALOGO, ciudades, invocar } from './herramientas.js';

const $ = (id) => document.getElementById(id);
const RUTA_INDICE = 'datos/indice.sqlite';
const MAX_PASOS = 4;

let bd = null;
let motor = null;

// --------------------------------------------------------------------------------------
// Índice
// --------------------------------------------------------------------------------------

async function abrirIndice() {
  const SQL = await initSqlJs({ locateFile: (f) => `vendor/${f}` });
  const respuesta = await fetch(RUTA_INDICE);
  if (!respuesta.ok) throw new Error(`no se pudo descargar el índice (HTTP ${respuesta.status})`);

  // Progreso de descarga: el índice son 21 MB (3,4 comprimidos) y sin barra parece colgado.
  const total = Number(respuesta.headers.get('Content-Length')) || 0;
  const trozos = [];
  let recibido = 0;
  const lector = respuesta.body.getReader();
  for (;;) {
    const { done, value } = await lector.read();
    if (done) break;
    trozos.push(value);
    recibido += value.length;
    if (total) $('barra').value = Math.round((recibido / total) * 100);
  }
  const bytes = new Uint8Array(recibido);
  let posicion = 0;
  for (const t of trozos) { bytes.set(t, posicion); posicion += t.length; }

  bd = new SQL.Database(bytes);
  $('barra').classList.add('oculto');

  const [{ values }] = bd.exec(
    `SELECT (SELECT COUNT(*) FROM dataset), (SELECT COUNT(*) FROM distribucion),
            (SELECT COUNT(*) FROM portal),
            (SELECT valor FROM metadatos_indice WHERE clave='ultima_sincronizacion')`);
  const [nd, ndist, np, sinc] = values[0];
  $('resumen-indice').textContent =
    `${nd} datasets · ${ndist} distribuciones · ${np} ciudades · sincronizado ${(sinc || '?').slice(0, 10)}`;
  $('estado').textContent = `Índice listo (${(recibido / 1e6).toFixed(1)} MB en memoria). Todo ocurre en tu navegador.`;

  const selector = $('ciudad');
  for (const c of ciudades(bd)) {
    const opcion = document.createElement('option');
    opcion.value = c.id;
    opcion.textContent = c.municipio;
    selector.append(opcion);
  }
}

// --------------------------------------------------------------------------------------
// Presentación
// --------------------------------------------------------------------------------------

function pintarFichas(fichas, destino) {
  destino.innerHTML = '';
  if (!fichas.length) {
    destino.innerHTML = '<p class="aviso">Sin resultados en el índice. ' +
      'Si la ciudad es Barcelona o Reus, prueba en catalán: sus catálogos están en catalán.</p>';
    return;
  }
  for (const f of fichas) {
    const tarjeta = document.createElement('article');
    tarjeta.className = 'tarjeta' + (f.licencia_declarada ? '' : ' sin-licencia');
    const licencia = f.licencia_declarada
      ? `licencia ${f.licencia}`
      : '<span class="insignia">licencia NO declarada</span>';
    tarjeta.innerHTML = `
      <h3>${escapar(f.titulo)}</h3>
      <p>${escapar((f.descripcion || '').slice(0, 240))}</p>
      <div class="meta">
        <span>${escapar(f.ciudad)}</span>
        <span>${f.num_distribuciones} distribuciones</span>
        <span>${licencia}</span>
        <span>modificado ${(f.fecha_modificacion_origen || 'sin fecha').slice(0, 10)}</span>
        <a href="${encodeURI(f.url_origen)}" target="_blank" rel="noopener">ver en el portal ↗</a>
      </div>`;
    destino.append(tarjeta);
  }
}

const escapar = (t) => String(t ?? '').replace(/[&<>"]/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function anotarTraza(texto) {
  const linea = document.createElement('div');
  linea.className = 'traza';
  linea.textContent = texto;
  $('traza').append(linea);
}

// --------------------------------------------------------------------------------------
// Modo directo
// --------------------------------------------------------------------------------------

function buscarDirecto() {
  if (!bd) return;
  const r = invocar(bd, 'buscar_datasets', {
    consulta: $('q').value.trim(),
    ciudad: $('ciudad').value || null,
    limite: 10,
  });
  pintarFichas(r.resultados || [], $('resultados'));
  $('estado').textContent = r.sin_resultados
    ? 'El índice no contiene nada que encaje.'
    : `${r.n_resultados} resultados.`;
}

// --------------------------------------------------------------------------------------
// Modo agente
// --------------------------------------------------------------------------------------

const SISTEMA = `Eres un asistente que consulta un índice de catálogos de datos abiertos de ayuntamientos españoles.

Herramientas disponibles:
${Object.entries(CATALOGO).map(([n, e]) => `- ${n}: ${e.descripcion}`).join('\n')}

Ciudades del índice: CIUDADES.

Para usar una herramienta responde SOLO con un objeto JSON, sin texto alrededor:
{"herramienta": "buscar_datasets", "argumentos": {"consulta": "calidad del aire", "ciudad": "malaga"}}

Cuando ya tengas la información, responde SOLO con:
{"respuesta": "tu respuesta en español, citando el título del dataset y su url_origen"}

Reglas que no puedes romper:
- Si una herramienta devuelve "sin_resultados", di que no está en el índice. NUNCA inventes un dataset ni una URL.
- Si "licencia_declarada" es false, avisa de que el portal no declara licencia.
- Cita siempre la url_origen que te devuelva la herramienta, tal cual.`;

/** Extrae el primer objeto JSON del texto. Los modelos pequeños envuelven en prosa. */
function extraerJSON(texto) {
  const limpio = texto.replace(/```(?:json)?/g, '');
  const inicio = limpio.indexOf('{');
  if (inicio === -1) return null;
  let nivel = 0;
  for (let i = inicio; i < limpio.length; i++) {
    if (limpio[i] === '{') nivel++;
    else if (limpio[i] === '}') {
      nivel--;
      if (nivel === 0) {
        try { return JSON.parse(limpio.slice(inicio, i + 1)); } catch { return null; }
      }
    }
  }
  return null;
}

async function preguntar() {
  const pregunta = $('pregunta').value.trim();
  if (!pregunta || !motor) return;
  $('traza').innerHTML = '';
  $('respuesta').innerHTML = '';
  $('btn-preguntar').disabled = true;

  const listaCiudades = ciudades(bd).map((c) => `${c.id} (${c.municipio})`).join(', ');
  const mensajes = [
    { role: 'system', content: SISTEMA.replace('CIUDADES', listaCiudades) },
    { role: 'user', content: pregunta },
  ];

  try {
    for (let paso = 1; paso <= MAX_PASOS; paso++) {
      const t0 = performance.now();
      const salida = await motor.chat.completions.create({ messages: mensajes, temperature: 0, max_tokens: 400 });
      const texto = salida.choices[0].message.content ?? '';
      const ms = Math.round(performance.now() - t0);

      const orden = extraerJSON(texto);
      if (!orden) {
        anotarTraza(`paso ${paso} · ${ms} ms · el modelo no devolvió JSON válido:\n${texto.slice(0, 300)}`);
        $('respuesta').innerHTML = '<div class="respuesta">El modelo no ha conseguido emitir una ' +
          'llamada de herramienta válida. Es el fallo típico de los modelos pequeños con ' +
          'tool-calling, y forma parte de lo que el TFM mide. Usa el modo directo de arriba.</div>';
        break;
      }
      if (orden.respuesta) {
        anotarTraza(`paso ${paso} · ${ms} ms · respuesta final`);
        $('respuesta').innerHTML = `<div class="respuesta">${escapar(orden.respuesta)}</div>`;
        break;
      }
      if (!orden.herramienta) {
        anotarTraza(`paso ${paso} · ${ms} ms · JSON sin campo "herramienta": ${JSON.stringify(orden).slice(0, 200)}`);
        break;
      }

      const resultado = invocar(bd, orden.herramienta, orden.argumentos || {});
      anotarTraza(`paso ${paso} · ${ms} ms · ${orden.herramienta}(${JSON.stringify(orden.argumentos || {})})` +
        ` → ${resultado.n_resultados ?? (resultado.error ? 'error' : 'ok')}`);
      if (resultado.resultados) pintarFichas(resultado.resultados, $('respuesta'));

      mensajes.push({ role: 'assistant', content: texto });
      mensajes.push({
        role: 'user',
        content: `Resultado de ${orden.herramienta}:\n${JSON.stringify(resultado).slice(0, 3000)}\n\n` +
          'Si ya puedes responder, devuelve {"respuesta": "..."}.',
      });

      if (paso === MAX_PASOS) {
        anotarTraza(`se alcanzó el máximo de ${MAX_PASOS} pasos sin respuesta final`);
      }
    }
  } catch (e) {
    anotarTraza(`error: ${e.message}`);
  } finally {
    $('btn-preguntar').disabled = false;
  }
}

async function prepararModelo() {
  if (!navigator.gpu) {
    $('aviso-webgpu').innerHTML = '<strong>Tu navegador no expone WebGPU</strong>, así que el modo ' +
      'agente no puede funcionar aquí. El modo directo de arriba sí. Prueba con Chrome o Edge ' +
      'recientes, o Safari 18+. Esta limitación es justo uno de los riesgos que el TFM mide.';
    return;
  }
  $('aviso-webgpu').textContent = 'WebGPU disponible. Elige un modelo: se descarga una vez ' +
    '(cientos de MB) y queda en la caché del navegador. La inferencia es gratis y local.';

  let webllm;
  try {
    webllm = await import('https://esm.run/@mlc-ai/web-llm');
  } catch {
    $('aviso-webgpu').textContent = 'No se pudo cargar WebLLM desde la red. El modo directo sigue funcionando.';
    return;
  }

  // Se listan los modelos desde el catálogo de WebLLM en vez de fijar identificadores a
  // mano: los ids cambian entre versiones y un id inventado rompe la página.
  const pequenos = (webllm.prebuiltAppConfig?.model_list ?? [])
    .filter((m) => /q4/i.test(m.model_id) && /-(0\.5B|1B|1\.5B|2B|3B)-/i.test(m.model_id))
    .sort((a, b) => (a.vram_required_MB ?? 1e9) - (b.vram_required_MB ?? 1e9));

  const selector = $('modelo');
  selector.innerHTML = '';
  for (const m of (pequenos.length ? pequenos : webllm.prebuiltAppConfig.model_list).slice(0, 25)) {
    const o = document.createElement('option');
    o.value = m.model_id;
    o.textContent = m.vram_required_MB
      ? `${m.model_id} · ~${Math.round(m.vram_required_MB)} MB de VRAM`
      : m.model_id;
    selector.append(o);
  }
  $('btn-cargar').disabled = false;

  $('btn-cargar').onclick = async () => {
    $('btn-cargar').disabled = true;
    $('barra-modelo').classList.remove('oculto');
    try {
      motor = await webllm.CreateMLCEngine(selector.value, {
        initProgressCallback: (p) => {
          $('estado-modelo').textContent = p.text;
          if (typeof p.progress === 'number') $('barra-modelo').value = Math.round(p.progress * 100);
        },
      });
      $('estado-modelo').textContent = `Modelo ${selector.value} cargado. Inferencia local, 0 €.`;
      $('barra-modelo').classList.add('oculto');
      $('pregunta').disabled = false;
      $('btn-preguntar').disabled = false;
    } catch (e) {
      $('estado-modelo').textContent = `No se pudo cargar el modelo: ${e.message}`;
      $('btn-cargar').disabled = false;
    }
  };
}

// --------------------------------------------------------------------------------------
// Arranque
// --------------------------------------------------------------------------------------

const EJEMPLOS_DIRECTO = ['calidad del aire', 'bicimad', 'presupuesto', 'arbolado', 'contaminació'];
const EJEMPLOS_AGENTE = [
  '¿Qué datos hay sobre calidad del aire en Málaga?',
  '¿Publica Córdoba algo sobre presupuestos y con qué licencia?',
  '¿Qué ciudades publican datos de arbolado?',
  '¿Tiene Reus un inventario de arbolado urbano?',
];

function pintarEjemplos() {
  for (const [destino, ejemplos, campo, accion] of [
    ['ejemplos-directo', EJEMPLOS_DIRECTO, 'q', buscarDirecto],
    ['ejemplos-agente', EJEMPLOS_AGENTE, 'pregunta', preguntar],
  ]) {
    for (const texto of ejemplos) {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = texto;
      b.onclick = () => { $(campo).value = texto; if (!$(campo).disabled) accion(); };
      $(destino).append(b);
    }
  }
}

(async () => {
  pintarEjemplos();
  $('btn-buscar').onclick = buscarDirecto;
  $('q').addEventListener('keydown', (e) => { if (e.key === 'Enter') buscarDirecto(); });
  $('pregunta').addEventListener('keydown', (e) => { if (e.key === 'Enter') preguntar(); });
  $('btn-preguntar').onclick = preguntar;
  try {
    await abrirIndice();
    $('q').value = 'calidad del aire';
    buscarDirecto();
  } catch (e) {
    $('estado').textContent = `No se pudo abrir el índice: ${e.message}`;
  }
  prepararModelo();
})();
