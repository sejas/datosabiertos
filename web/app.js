/**
 * Cliente del navegador: chat con dos motores, búsqueda directa y guía de conexión MCP.
 *
 * Los tres bloques de la página, y el orden importa:
 *
 * 1. **Chat**. Dos motores intercambiables detrás de la misma interfaz:
 *    - *Servidor*: `POST /chat`. El modelo grande vive en OpenRouter y el bucle de agente
 *      corre en el servidor (`tfm/mcp/chat.py`), que nos manda un evento por paso. Es el
 *      experimento A del plan.
 *    - *Navegador*: WebLLM por WebGPU. El bucle corre aquí, contra el índice SQLite abierto
 *      en memoria con sql.js, y no sale nada de la máquina. Es el experimento B.
 *    Los dos producen los mismos eventos (`paso`, `delta`, `fin`, `error`), así que el chat
 *    se pinta igual y la única variable es el modelo.
 * 2. **Búsqueda directa**: las herramientas sin ningún modelo. Funciona siempre y es el
 *    patrón contra el que comparar: si esto encuentra el dataset y el agente no, el fallo es
 *    del modelo, no del índice.
 * 3. **Conectar**: instrucciones estáticas; aquí solo van las pestañas y los botones de copiar.
 *
 * La traza de llamadas se muestra siempre: es una métrica del TFM, no depuración.
 */

import { CATALOGO, ciudades, invocar } from './herramientas.js';

const $ = (id) => document.getElementById(id);
const RUTA_INDICE = 'datos/indice.sqlite.gz';
const MAX_PASOS_NAVEGADOR = 4;

let bd = null;          // índice SQLite en memoria (sql.js)
let motorLocal = null;  // motor WebLLM, si se ha cargado
let salud = null;       // respuesta de GET /salud
let historial = [];     // [{role, content}] que se manda al modelo
let ocupado = false;

// --------------------------------------------------------------------------------------
// Utilidades
// --------------------------------------------------------------------------------------

const escapar = (t) => String(t ?? '').replace(/[&<>"]/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

/** Markdown mínimo y seguro: se escapa todo y luego se reconocen unas pocas marcas. */
function renderizarMarkdown(texto) {
  const enLinea = (s) => escapar(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/(^|[^"'>])(https?:\/\/[^\s<]+[^\s<.,;:)])/g, '$1<a href="$2" target="_blank" rel="noopener">$2</a>');

  const bloques = [];
  let lista = null;
  const cerrarLista = () => { if (lista) { bloques.push(`<${lista.tipo}>${lista.items.join('')}</${lista.tipo}>`); lista = null; } };
  for (const parrafo of texto.split(/\n{2,}/)) {
    const lineas = parrafo.split('\n');
    const salida = [];
    for (const linea of lineas) {
      const item = linea.match(/^\s*(?:[-*•]|\d+[.)])\s+(.*)$/);
      if (item) {
        const tipo = /^\s*\d/.test(linea) ? 'ol' : 'ul';
        if (!lista || lista.tipo !== tipo) { cerrarLista(); lista = { tipo, items: [] }; }
        lista.items.push(`<li>${enLinea(item[1])}</li>`);
      } else {
        cerrarLista();
        if (linea.trim()) salida.push(enLinea(linea));
      }
    }
    cerrarLista();
    if (salida.length) bloques.push(`<p>${salida.join('<br>')}</p>`);
  }
  cerrarLista();
  return bloques.join('');
}

function fichaHTML(f) {
  const licencia = f.licencia_declarada
    ? `<span class="insignia ok">licencia ${escapar(f.licencia)}</span>`
    : '<span class="insignia">licencia NO declarada</span>';
  return `<article class="tarjeta${f.licencia_declarada ? '' : ' sin-licencia'}">
      <h3>${escapar(f.titulo)}</h3>
      <p>${escapar((f.descripcion || '').slice(0, 240))}</p>
      <div class="meta">
        <span>${escapar(f.ciudad)}</span>
        <span>${f.num_distribuciones} distribuciones</span>
        ${licencia}
        <span>modificado ${(f.fecha_modificacion_origen || 'sin fecha').slice(0, 10)}</span>
        <a href="${encodeURI(f.url_origen)}" target="_blank" rel="noopener">ver en el portal ↗</a>
      </div></article>`;
}

function pintarFichas(fichas, destino) {
  destino.innerHTML = fichas.length
    ? fichas.map(fichaHTML).join('')
    : '<p class="aviso">Sin resultados en el índice. Si la ciudad es Barcelona o Reus, ' +
      'prueba en catalán: sus catálogos están en catalán.</p>';
}

function formatearNumero(n) { return Number(n).toLocaleString('es-ES'); }

// --------------------------------------------------------------------------------------
// Índice y estado del servidor
// --------------------------------------------------------------------------------------

async function abrirIndice() {
  const SQL = await initSqlJs({ locateFile: (f) => `vendor/${f}` });
  const respuesta = await fetch(RUTA_INDICE);
  if (!respuesta.ok) throw new Error(`no se pudo descargar el índice (HTTP ${respuesta.status})`);

  // Progreso de descarga: son 3,4 MB comprimidos (21 al descomprimir) y sin barra parece colgado.
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
  const comprimido = new Uint8Array(recibido);
  let posicion = 0;
  for (const t of trozos) { comprimido.set(t, posicion); posicion += t.length; }

  // Solo se publica el índice comprimido. Se descomprime aquí con la API nativa del navegador.
  if (typeof DecompressionStream !== 'function') {
    throw new Error('este navegador no soporta DecompressionStream; usa Chrome/Edge 80+, ' +
                    'Firefox 113+ o Safari 16.4+');
  }
  const flujo = new Blob([comprimido]).stream().pipeThrough(new DecompressionStream('gzip'));
  const bytes = new Uint8Array(await new Response(flujo).arrayBuffer());

  bd = new SQL.Database(bytes);
  $('barra').classList.add('oculto');
  $('estado').textContent = `Índice listo (${(bytes.length / 1e6).toFixed(0)} MB en memoria). ` +
    'La búsqueda directa ocurre en tu navegador.';

  const selector = $('ciudad');
  for (const c of ciudades(bd)) {
    const opcion = document.createElement('option');
    opcion.value = c.id;
    opcion.textContent = c.municipio;
    selector.append(opcion);
  }
}

async function consultarSalud() {
  try {
    const r = await fetch('salud', { cache: 'no-store' });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    salud = await r.json();
  } catch {
    salud = null;
  }
  const cifras = $('cifras');
  if (salud) {
    cifras.innerHTML = [
      `<strong>${formatearNumero(salud.datasets)}</strong> datasets`,
      `<strong>${formatearNumero(salud.distribuciones)}</strong> distribuciones`,
      `<strong>${salud.ciudades.length}</strong> ciudades`,
      `<strong>${formatearNumero(salud.sin_licencia_declarada)}</strong> sin licencia declarada`,
      `sincronizado <strong>${(salud.ultima_sincronizacion || '?').slice(0, 10)}</strong>`,
    ].map((t) => `<span>${t}</span>`).join('');
  } else {
    cifras.innerHTML = '<span>servidor no disponible: solo búsqueda directa y modelo en el navegador</span>';
  }
  configurarMotores();
}

// --------------------------------------------------------------------------------------
// Chat: presentación
// --------------------------------------------------------------------------------------

const EJEMPLOS_CHAT = [
  '¿Qué datos hay sobre calidad del aire en Málaga?',
  '¿Publica Córdoba algo sobre presupuestos y con qué licencia?',
  '¿Qué ciudades publican datos de arbolado y cuáles no?',
  'Quins conjunts de dades té Barcelona sobre contaminació?',
  '¿En qué formatos se puede descargar el padrón de Madrid?',
];

function desplazarAlFinal() {
  const m = $('mensajes');
  m.scrollTop = m.scrollHeight;
}

function anadirMensajeUsuario(texto) {
  $('bienvenida')?.remove();
  const div = document.createElement('div');
  div.className = 'mensaje usuario';
  div.innerHTML = `<div class="burbuja"></div>`;
  div.firstElementChild.textContent = texto;
  $('mensajes').append(div);
  desplazarAlFinal();
}

/** Crea el contenedor de una respuesta y devuelve funciones para irla rellenando. */
function nuevaRespuesta() {
  const div = document.createElement('div');
  div.className = 'mensaje asistente';
  const pensando = document.createElement('span');
  pensando.className = 'pensando';
  pensando.textContent = 'pensando';
  div.append(pensando);
  $('mensajes').append(div);
  desplazarAlFinal();

  let texto = null;
  let acumulado = '';
  return {
    paso(e) {
      const detalles = document.createElement('details');
      detalles.className = 'paso';
      const r = e.resultado || {};
      const esError = Boolean(r.error);
      const conDatos = r.con_datos ? Object.values(r.con_datos) : null;
      const cuenta = esError ? 'error'
        : r.n_resultados !== undefined ? `${r.n_resultados} resultado${r.n_resultados === 1 ? '' : 's'}`
        : r.sin_resultados ? '0 resultados'
        : conDatos ? `${conDatos.length} con datos · ${(r.sin_datos || []).length} sin datos`
        : r.distribuciones ? `${r.distribuciones.length} distribuciones`
        : r.titulo ? 'ficha' : 'ok';
      const argumentos = Object.entries(e.argumentos || {})
        .map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(' ');
      detalles.innerHTML = `
        <summary>
          <span class="nombre">${escapar(e.herramienta)}</span>
          <span class="args">${escapar(argumentos)}</span>
          <span class="cuenta${esError ? ' error' : ''}">${escapar(cuenta)}${e.ms ? ` · ${(e.ms / 1000).toFixed(1)} s` : ''}</span>
        </summary>
        <div class="cuerpo"></div>`;
      const cuerpo = detalles.querySelector('.cuerpo');
      const fichas = r.resultados
        || (conDatos ? conDatos.flatMap((c) => c.datasets || []) : null)
        || (r.titulo && r.url_origen ? [r] : null);
      if (fichas?.length) {
        const nota = r.nota_sin_datos ? `<p class="aviso alerta">${escapar(r.nota_sin_datos)}</p>` : '';
        cuerpo.innerHTML = `${nota}<div class="fichas">${fichas.map(fichaHTML).join('')}</div>`;
        detalles.open = fichas.length <= 3; // las comparaciones largas, plegadas: el resumen ya dice cuántas
      } else {
        const pre = document.createElement('pre');
        pre.textContent = JSON.stringify(r, null, 1).slice(0, 4000);
        cuerpo.append(pre);
      }
      div.insertBefore(detalles, pensando);
      desplazarAlFinal();
    },
    delta(t) {
      if (!texto) {
        texto = document.createElement('div');
        texto.className = 'texto';
        div.insertBefore(texto, pensando);
      }
      acumulado += t;
      texto.innerHTML = renderizarMarkdown(acumulado);
      desplazarAlFinal();
    },
    error(mensaje) {
      const e = document.createElement('div');
      e.className = 'error-chat';
      e.textContent = mensaje;
      div.insertBefore(e, pensando);
      desplazarAlFinal();
    },
    fin() {
      pensando.remove();
      desplazarAlFinal();
      return acumulado;
    },
  };
}

// --------------------------------------------------------------------------------------
// Motor servidor: POST /chat con eventos SSE
// --------------------------------------------------------------------------------------

async function conversarServidor(mensajes, salida) {
  const r = await fetch('chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages: mensajes }),
  });
  if (!r.ok) {
    let detalle = `HTTP ${r.status}`;
    try { detalle = (await r.json()).error || detalle; } catch { /* sin cuerpo JSON */ }
    throw new Error(detalle);
  }
  // Se parsea el flujo SSE a mano: EventSource no admite POST.
  const lector = r.body.pipeThrough(new TextDecoderStream()).getReader();
  let resto = '';
  for (;;) {
    const { done, value } = await lector.read();
    if (done) break;
    resto += value;
    const partes = resto.split('\n\n');
    resto = partes.pop();
    for (const parte of partes) {
      const linea = parte.split('\n').find((l) => l.startsWith('data:'));
      if (!linea) continue;
      const evento = JSON.parse(linea.slice(5));
      if (evento.tipo === 'paso') salida.paso(evento);
      else if (evento.tipo === 'delta') salida.delta(evento.texto);
      else if (evento.tipo === 'error') salida.error(evento.mensaje);
    }
  }
}

// --------------------------------------------------------------------------------------
// Motor navegador: WebLLM con protocolo JSON (los modelos pequeños no traen tool-calling fiable)
// --------------------------------------------------------------------------------------

const SISTEMA_LOCAL = `Eres un asistente que consulta un índice de catálogos de datos abiertos de ayuntamientos españoles.

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

async function conversarNavegador(mensajesUsuario, salida) {
  if (!motorLocal) throw new Error('carga primero un modelo en tu navegador');
  const listaCiudades = ciudades(bd).map((c) => `${c.id} (${c.municipio})`).join(', ');
  const mensajes = [
    { role: 'system', content: SISTEMA_LOCAL.replace('CIUDADES', listaCiudades) },
    ...mensajesUsuario,
  ];
  for (let paso = 1; paso <= MAX_PASOS_NAVEGADOR; paso++) {
    const t0 = performance.now();
    const respuesta = await motorLocal.chat.completions.create({ messages: mensajes, temperature: 0, max_tokens: 400 });
    const texto = respuesta.choices[0].message.content ?? '';
    const ms = Math.round(performance.now() - t0);

    const orden = extraerJSON(texto);
    if (!orden) {
      salida.error('El modelo no ha devuelto una llamada de herramienta válida. Es el fallo ' +
        'típico de los modelos pequeños con tool-calling, y forma parte de lo que el TFM mide. ' +
        `Texto recibido: ${texto.slice(0, 200)}`);
      return;
    }
    if (orden.respuesta) { salida.delta(String(orden.respuesta)); return; }
    if (!orden.herramienta) {
      salida.error(`JSON sin campo "herramienta": ${JSON.stringify(orden).slice(0, 200)}`);
      return;
    }
    const resultado = invocar(bd, orden.herramienta, orden.argumentos || {});
    salida.paso({ herramienta: orden.herramienta, argumentos: orden.argumentos || {}, resultado, ms });
    mensajes.push({ role: 'assistant', content: texto });
    mensajes.push({
      role: 'user',
      content: `Resultado de ${orden.herramienta}:\n${JSON.stringify(resultado).slice(0, 3000)}\n\n` +
        'Si ya puedes responder, devuelve {"respuesta": "..."}.',
    });
  }
  salida.error(`se alcanzó el máximo de ${MAX_PASOS_NAVEGADOR} pasos sin respuesta final`);
}

async function prepararWebLLM() {
  const texto = $('texto-navegador');
  if (!navigator.gpu) {
    texto.innerHTML = '<strong>Tu navegador no expone WebGPU</strong>, así que este motor no ' +
      'puede funcionar aquí. Prueba con Chrome o Edge recientes, o Safari 18+. El motor ' +
      '«Servidor» y la búsqueda directa sí funcionan.';
    $('controles-modelo').classList.add('oculto');
    return;
  }
  texto.textContent = 'WebGPU disponible. Elige un modelo: se descarga una vez (cientos de MB) ' +
    'y queda en la caché del navegador. La inferencia es local y no sale nada de tu máquina.';

  let webllm;
  try {
    webllm = await import('https://esm.run/@mlc-ai/web-llm');
  } catch {
    texto.textContent = 'No se pudo cargar WebLLM desde la red. El motor «Servidor» sigue funcionando.';
    $('controles-modelo').classList.add('oculto');
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
      motorLocal = await webllm.CreateMLCEngine(selector.value, {
        initProgressCallback: (p) => {
          $('estado-modelo').textContent = p.text;
          if (typeof p.progress === 'number') $('barra-modelo').value = Math.round(p.progress * 100);
        },
      });
      $('estado-modelo').textContent = `Modelo ${selector.value} cargado. Inferencia local, 0 €.`;
      $('barra-modelo').classList.add('oculto');
      actualizarCompositor();
    } catch (e) {
      $('estado-modelo').textContent = `No se pudo cargar el modelo: ${e.message}`;
      $('btn-cargar').disabled = false;
    }
  };
}

// --------------------------------------------------------------------------------------
// Chat: control
// --------------------------------------------------------------------------------------

function motorActual() { return $('motor').value; }

function motorDisponible() {
  return motorActual() === 'servidor' ? Boolean(salud?.chat?.disponible) : Boolean(motorLocal);
}

function actualizarCompositor() {
  const listo = motorDisponible() && !ocupado;
  $('btn-enviar').disabled = !listo;
  $('pregunta').disabled = ocupado;
  $('pregunta').placeholder = motorActual() === 'servidor'
    ? (salud?.chat?.disponible ? '¿Qué datos hay sobre calidad del aire en Málaga?'
                               : 'El chat alojado no está disponible; usa tu navegador o la búsqueda directa')
    : (motorLocal ? '¿Qué datos hay sobre calidad del aire en Málaga?' : 'Carga primero un modelo');
}

function configurarMotores() {
  const chat = salud?.chat;
  const selector = $('motor');
  const opcionServidor = selector.querySelector('option[value=servidor]');
  if (chat?.disponible) {
    opcionServidor.textContent = `Servidor · ${chat.modelo}`;
    $('texto-servidor').innerHTML = `El bucle de agente corre en el servidor con <code>${escapar(chat.modelo)}</code> ` +
      'vía OpenRouter, con tool-calling nativo. Tu conversación sale de tu navegador hacia ese proveedor. ' +
      `Límite: ${chat.limite_por_ip} preguntas cada ${Math.round(chat.ventana_segundos / 60)} minutos por dirección; ` +
      'si lo agotas, conecta el MCP a tu propio agente (más abajo).';
  } else {
    opcionServidor.textContent = 'Servidor · no disponible';
    opcionServidor.disabled = true;
    selector.value = 'navegador';
    $('texto-servidor').textContent = 'El chat alojado no está configurado en este servidor.';
  }
  $('pie-chat').textContent = 'El modelo solo ve lo que devuelven las herramientas. Si dice que algo ' +
    'no está en el índice, compruébalo con la búsqueda directa: si ahí tampoco sale, es el índice; si sale, es el modelo.';
  cambiarMotor();
}

function cambiarMotor() {
  const servidor = motorActual() === 'servidor';
  $('motor-servidor').classList.toggle('oculto', !servidor);
  $('motor-navegador').classList.toggle('oculto', servidor);
  if (!servidor && !prepararWebLLM.iniciado) {
    prepararWebLLM.iniciado = true;
    prepararWebLLM();
  }
  actualizarCompositor();
}

async function enviar(texto) {
  texto = (texto ?? $('pregunta').value).trim();
  if (!texto || ocupado || !motorDisponible()) return;
  ocupado = true;
  actualizarCompositor();
  $('pregunta').value = '';
  ajustarAltura();
  anadirMensajeUsuario(texto);
  historial.push({ role: 'user', content: texto });

  const salida = nuevaRespuesta();
  try {
    if (motorActual() === 'servidor') await conversarServidor(historial, salida);
    else await conversarNavegador(historial, salida);
  } catch (e) {
    salida.error(e.message);
  } finally {
    const respuesta = salida.fin();
    if (respuesta) historial.push({ role: 'assistant', content: respuesta });
    else historial.pop(); // sin respuesta no hay turno que recordar
    ocupado = false;
    actualizarCompositor();
    $('pregunta').focus();
  }
}

function nuevaConversacion() {
  if (ocupado) return;
  historial = [];
  $('mensajes').innerHTML = '';
  const bienvenida = document.createElement('div');
  bienvenida.className = 'bienvenida';
  bienvenida.id = 'bienvenida';
  bienvenida.innerHTML = '<p>Conversación nueva. Prueba con una de estas:</p><div class="chips" id="ejemplos-chat"></div>';
  $('mensajes').append(bienvenida);
  pintarEjemplosChat();
  $('pregunta').focus();
}

function ajustarAltura() {
  const t = $('pregunta');
  t.style.height = 'auto';
  t.style.height = `${Math.min(t.scrollHeight, 160)}px`;
}

function pintarEjemplosChat() {
  const destino = $('ejemplos-chat');
  if (!destino) return;
  destino.innerHTML = '';
  for (const texto of EJEMPLOS_CHAT) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = texto;
    b.onclick = () => {
      if (motorDisponible()) enviar(texto);
      else { $('pregunta').value = texto; ajustarAltura(); $('pregunta').focus(); }
    };
    destino.append(b);
  }
}

// --------------------------------------------------------------------------------------
// Búsqueda directa
// --------------------------------------------------------------------------------------

const EJEMPLOS_DIRECTO = ['calidad del aire', 'bicimad', 'presupuesto', 'arbolado', 'contaminació'];

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

function pintarEjemplosDirecto() {
  for (const texto of EJEMPLOS_DIRECTO) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = texto;
    b.onclick = () => { $('q').value = texto; buscarDirecto(); };
    $('ejemplos-directo').append(b);
  }
}

// --------------------------------------------------------------------------------------
// Conectar: pestañas y botones de copiar
// --------------------------------------------------------------------------------------

function prepararConectar() {
  const pestanas = $('pestanas');
  pestanas.addEventListener('click', (e) => {
    const boton = e.target.closest('[role=tab]');
    if (!boton) return;
    for (const b of pestanas.querySelectorAll('[role=tab]')) b.setAttribute('aria-selected', String(b === boton));
    for (const p of document.querySelectorAll('.pestana')) {
      p.classList.toggle('oculto', p.dataset.pestana !== boton.dataset.pestana);
    }
  });

  for (const bloque of document.querySelectorAll('.codigo')) {
    const boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'copiar';
    boton.textContent = 'Copiar';
    boton.onclick = async () => {
      try {
        await navigator.clipboard.writeText(bloque.querySelector('pre').textContent);
        boton.textContent = 'Copiado';
      } catch {
        boton.textContent = 'No se pudo';
      }
      setTimeout(() => { boton.textContent = 'Copiar'; }, 1500);
    };
    bloque.append(boton);
  }

  // La URL del endpoint se toma de la página real, por si se sirve desde otro dominio.
  const url = new URL('mcp', location.href).href;
  if (url !== $('url-mcp').textContent) {
    for (const el of document.querySelectorAll('#conectar pre, #url-mcp')) {
      el.textContent = el.textContent.replaceAll('https://datosabiertos.sejas.es/mcp', url)
        .replaceAll('https://datosabiertos.sejas.es/salud', new URL('salud', location.href).href);
    }
  }
}

// --------------------------------------------------------------------------------------
// Arranque
// --------------------------------------------------------------------------------------

(async () => {
  pintarEjemplosChat();
  pintarEjemplosDirecto();
  prepararConectar();

  $('compositor').addEventListener('submit', (e) => { e.preventDefault(); enviar(); });
  $('pregunta').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviar(); }
  });
  $('pregunta').addEventListener('input', ajustarAltura);
  $('btn-nueva').onclick = nuevaConversacion;
  $('motor').onchange = cambiarMotor;
  $('btn-buscar').onclick = buscarDirecto;
  $('q').addEventListener('keydown', (e) => { if (e.key === 'Enter') buscarDirecto(); });

  actualizarCompositor();
  // En paralelo con el índice: el chat del servidor no necesita esperarlo. Con `?q=` en la
  // URL se manda esa pregunta en cuanto haya motor: sirve para compartir un enlace.
  consultarSalud().then(() => {
    const q = new URLSearchParams(location.search).get('q');
    if (q && motorDisponible()) enviar(q);
    else if (q) { $('pregunta').value = q; ajustarAltura(); }
  });

  try {
    await abrirIndice();
    $('q').value = 'calidad del aire';
    buscarDirecto();
  } catch (e) {
    $('estado').textContent = `No se pudo abrir el índice: ${e.message}`;
    $('estado').classList.add('alerta');
  }
})();
