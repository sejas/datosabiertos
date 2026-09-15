/**
 * Las cuatro herramientas, en el navegador y sobre el mismo índice SQLite.
 *
 * Es el puerto de `datosabiertos/mcp/herramientas.py`: mismos nombres, mismos argumentos y —lo que
 * importa— mismo contrato de procedencia. Toda ficha lleva `url_origen`,
 * `fecha_modificacion_origen`, `fecha_sincronizacion` y `licencia_declarada`, y la ausencia
 * viaja como instrucción (`sin_resultados`) en vez de como lista vacía.
 *
 * Que el mismo contrato valga en Python y en JavaScript es lo que permite comparar el
 * experimento A (modelo grande, servidor) con el B (modelo pequeño, navegador) sin cambiar
 * las herramientas: la única variable es el modelo.
 */

export const AVISO_SIN_LICENCIA =
  'El portal de origen NO declara licencia para este dataset. No se asume ninguna: ' +
  'antes de reutilizarlo hay que consultar las condiciones con el ayuntamiento.';

export const AVISO_COPIA =
  'Datos procedentes de una copia local de los metadatos, no del portal en vivo. ' +
  'Comprueba `fecha_sincronizacion` y sigue `url_origen` para la versión autoritativa.';

// Palabras vacías del español, y las catalanas frecuentes por Barcelona y Reus.
const PALABRAS_VACIAS = new Set(`a al ante bajo con contra de del desde durante e el en entre
  hacia hasta la las lo los mas mediante ni no o para pero por que se segun sin sobre su sus
  tras un una uno unos unas y ya els les dels amb per als i d l`.split(/\s+/));

const sinAcentos = (t) => t.normalize('NFKD').replace(/[̀-ͯ]/g, '');

/** Plural conservador: recorta -es / -s solo si queda una raíz razonable. */
function singularizar(palabra) {
  if (palabra.length >= 6 && palabra.endsWith('es')) return palabra.slice(0, -2);
  if (palabra.length >= 5 && palabra.endsWith('s') && !palabra.endsWith('ss')) return palabra.slice(0, -1);
  return palabra;
}

/** Traduce texto libre a una expresión MATCH de FTS5. Espejo de `construir_consulta_fts`. */
export function construirConsultaFTS(texto) {
  if (!texto || !texto.trim()) return '';
  const palabras = texto.split(/[^0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñÀÈÌÒÙàèìòùÇç·]+/).filter(Boolean);
  let utiles = palabras.filter((p) => !PALABRAS_VACIAS.has(sinAcentos(p).toLowerCase()));
  if (utiles.length === 0) utiles = palabras;
  return utiles.map((p) => `"${singularizar(p).replace(/"/g, '""')}"*`).join(' ');
}

const CAMPOS = `d.id, d.portal_id, p.municipio, d.identificador_origen, d.nombre, d.titulo,
  d.descripcion, d.url_origen, d.fecha_modificacion_origen, d.fecha_sincronizacion,
  d.num_distribuciones, l.identificador AS licencia, l.declarada AS licencia_declarada`;

const UNION = `FROM dataset d
  JOIN portal p ON p.id = d.portal_id
  JOIN licencia l ON l.id = d.licencia_id`;

/** Ejecuta SQL y devuelve filas como objetos. */
function filas(bd, sql, parametros = []) {
  const stmt = bd.prepare(sql);
  stmt.bind(parametros);
  const out = [];
  while (stmt.step()) out.push(stmt.getAsObject());
  stmt.free();
  return out;
}

function ficha(f) {
  const declarada = !!f.licencia_declarada;
  const salida = {
    id: `${f.portal_id}:${f.identificador_origen}`,
    titulo: f.titulo,
    ciudad: f.municipio,
    descripcion: (f.descripcion || '').slice(0, 500),
    num_distribuciones: f.num_distribuciones,
    licencia: declarada ? f.licencia : null,
    licencia_declarada: declarada,
    url_origen: f.url_origen,
    fecha_modificacion_origen: f.fecha_modificacion_origen || null,
    fecha_sincronizacion: f.fecha_sincronizacion,
  };
  if (!declarada) salida.advertencia = AVISO_SIN_LICENCIA;
  return salida;
}

export function ciudades(bd) {
  return filas(bd, 'SELECT id, municipio FROM portal ORDER BY municipio');
}

function localizar(bd, bd_id) {
  if (!bd_id || !bd_id.includes(':')) {
    return [null, {
      error: `identificador '${bd_id}' mal formado: se espera 'ciudad:id'`,
      sugerencia: 'Usa buscar_datasets primero y coge el campo `id` del resultado.',
    }];
  }
  const [portalBruto, ...resto] = bd_id.split(':');
  const portal = portalBruto.trim().toLowerCase();
  const clave = resto.join(':').trim();
  const r = filas(bd, `SELECT d.*, p.municipio, l.identificador AS licencia,
      l.declarada AS licencia_declarada ${UNION.replace('FROM dataset d', 'FROM dataset d')}
    WHERE d.portal_id = ? AND (d.identificador_origen = ? OR d.nombre = ?)`, [portal, clave, clave]);
  if (r.length === 0) {
    return [null, {
      error: `no existe el dataset '${bd_id}' en el índice`,
      sin_resultados: 'No inventes un dataset: di que no está en el índice.',
    }];
  }
  return [r[0], null];
}

// -- las cuatro herramientas ------------------------------------------------------------

export function buscar_datasets(bd, { consulta, ciudad = null, tema = null, anio = null, limite = 10 }) {
  const parametros = [];
  let union = UNION;
  const condiciones = [];
  const expresion = construirConsultaFTS(consulta);
  let orden;
  if (expresion) {
    union += ' JOIN dataset_fts f ON f.dataset_id = d.id ';
    condiciones.push('dataset_fts MATCH ?');
    parametros.push(expresion);
    orden = 'ORDER BY bm25(dataset_fts, 8.0, 2.0, 4.0, 2.0, 1.0)';
  } else {
    orden = 'ORDER BY d.fecha_modificacion_origen DESC';
  }
  if (ciudad) { condiciones.push('d.portal_id = ?'); parametros.push(ciudad.trim().toLowerCase()); }
  if (tema) {
    union += ' JOIN dataset_tema dt ON dt.dataset_id = d.id JOIN tema t ON t.id = dt.tema_id ';
    condiciones.push('t.normalizado LIKE ?');
    parametros.push(`%${sinAcentos(tema).toLowerCase()}%`);
  }
  if (anio) { condiciones.push("substr(d.fecha_modificacion_origen, 1, 4) = ?"); parametros.push(String(anio)); }
  const donde = condiciones.length ? `WHERE ${condiciones.join(' AND ')}` : '';
  const tope = Math.max(1, Math.min(Number(limite) || 10, 50));
  const r = filas(bd, `SELECT ${CAMPOS} ${union} ${donde} ${orden} LIMIT ?`, [...parametros, tope]);

  const salida = {
    consulta, filtros: { ciudad, tema, anio },
    n_resultados: r.length, resultados: r.map(ficha), aviso: AVISO_COPIA,
  };
  if (r.length === 0) {
    salida.sin_resultados = 'El índice no contiene ningún dataset que encaje. NO inventes uno: ' +
      'dilo explícitamente y, si procede, sugiere reformular o probar otra ciudad.';
  }
  return salida;
}

export function detalle_dataset(bd, { id }) {
  const [f, error] = localizar(bd, id);
  if (error) return error;
  const salida = ficha(f);
  salida.descripcion = f.descripcion || '';
  salida.nombre = f.nombre;
  salida.url_api_origen = f.url_recurso_api;
  salida.frecuencia_actualizacion = f.frecuencia_actualizacion || null;
  salida.temas = filas(bd, `SELECT t.nombre, t.titulo FROM tema t
    JOIN dataset_tema dt ON dt.tema_id = t.id WHERE dt.dataset_id = ?`, [f.id])
    .map((t) => t.titulo || t.nombre);
  salida.palabras_clave = filas(bd, `SELECT k.texto FROM keyword k
    JOIN dataset_keyword dk ON dk.keyword_id = k.id WHERE dk.dataset_id = ?`, [f.id])
    .map((k) => k.texto);
  salida.aviso = AVISO_COPIA;
  return salida;
}

export function listar_distribuciones(bd, { id }) {
  const [f, error] = localizar(bd, id);
  if (error) return { ...error, sin_resultados: 'No inventes distribuciones ni URLs de descarga.' };
  const d = filas(bd, 'SELECT * FROM distribucion WHERE dataset_id = ? ORDER BY posicion', [f.id]);
  return {
    id: `${f.portal_id}:${f.identificador_origen}`,
    titulo: f.titulo, ciudad: f.municipio,
    licencia: f.licencia_declarada ? f.licencia : null,
    licencia_declarada: !!f.licencia_declarada,
    n_distribuciones: d.length,
    distribuciones: d.map((x) => ({
      nombre: x.nombre || null, formato: x.formato || null,
      url: x.url_descarga || x.url_acceso,
      tamano_bytes: x.tamano_bytes, tamano_declarado: x.tamano_bytes !== null,
    })),
    url_origen: f.url_origen, fecha_sincronizacion: f.fecha_sincronizacion,
    aviso: 'Las URLs no se han comprobado en esta llamada. Madrid responde 403 a la descarga ' +
      'programática y Barcelona limita por concurrencia: un enlace puede fallar sin que el ' +
      'dataset haya desaparecido.',
  };
}

export function comparar_ciudades(bd, { tema, ciudades: pedidas = null, limite_por_ciudad = 3 }) {
  const todas = ciudades(bd).map((c) => c.id);
  const objetivo = (pedidas && pedidas.length ? pedidas : todas).map((c) => c.trim().toLowerCase());
  const desconocidas = objetivo.filter((c) => !todas.includes(c));
  if (desconocidas.length) {
    return { error: `ciudades no indexadas: ${desconocidas.join(', ')}`, ciudades_disponibles: todas };
  }
  const con_datos = {};
  const sin_datos = [];
  for (const c of objetivo) {
    const r = buscar_datasets(bd, { consulta: tema, ciudad: c, limite: limite_por_ciudad });
    if (r.n_resultados > 0) {
      con_datos[c] = { municipio: r.resultados[0].ciudad, n_encontrados: r.n_resultados, datasets: r.resultados };
    } else {
      sin_datos.push(c);
    }
  }
  return {
    tema, ciudades_consultadas: objetivo, con_datos, sin_datos,
    nota_sin_datos: sin_datos.length
      ? `${sin_datos.length} de ${objetivo.length} ciudades no publican nada sobre '${tema}' en ` +
        'el índice. Dilo en la respuesta: la ausencia es un resultado, no un hueco que rellenar.'
      : null,
    aviso: AVISO_COPIA,
  };
}

/** Catálogo declarativo, equivalente al `CATALOGO` de Python. */
export const CATALOGO = {
  buscar_datasets: {
    fn: buscar_datasets,
    descripcion: 'Busca datasets por texto libre. Argumentos: consulta (obligatorio), ciudad, tema, anio, limite.',
    obligatorios: ['consulta'],
  },
  detalle_dataset: {
    fn: detalle_dataset,
    descripcion: "Ficha completa de un dataset. Argumento: id con la forma 'ciudad:id'.",
    obligatorios: ['id'],
  },
  listar_distribuciones: {
    fn: listar_distribuciones,
    descripcion: "Formatos y URLs de descarga de un dataset. Argumento: id con la forma 'ciudad:id'.",
    obligatorios: ['id'],
  },
  comparar_ciudades: {
    fn: comparar_ciudades,
    descripcion: 'Compara qué publica cada ciudad sobre un tema. Argumentos: tema (obligatorio), ciudades, limite_por_ciudad.',
    obligatorios: ['tema'],
  },
};

/** Invoca una herramienta por nombre, validando los argumentos obligatorios. */
export function invocar(bd, nombre, argumentos = {}) {
  const entrada = CATALOGO[nombre];
  if (!entrada) {
    return { error: `herramienta desconocida: ${nombre}`, herramientas_disponibles: Object.keys(CATALOGO) };
  }
  const faltan = entrada.obligatorios.filter((a) => argumentos[a] === undefined || argumentos[a] === '');
  if (faltan.length) {
    return { error: `faltan argumentos obligatorios en ${nombre}: ${faltan.join(', ')}`, ayuda: entrada.descripcion };
  }
  try {
    return entrada.fn(bd, argumentos);
  } catch (e) {
    return { error: `fallo en ${nombre}: ${e.message}` };
  }
}
