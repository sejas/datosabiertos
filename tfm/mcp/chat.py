"""Chat con un modelo alojado que usa las herramientas del catálogo. Sin dependencias.

Es el "experimento A" del plan —modelo grande en servidor— expuesto como `POST /chat` para la
página del navegador. El modelo vive en OpenRouter (API compatible con OpenAI) y se llama
con *tool calling* nativo, de modo que las herramientas se describen con los mismos
`inputSchema` que ve un cliente MCP: la única variable entre A y B sigue siendo el modelo.

El bucle es el de siempre: el modelo pide una herramienta, se ejecuta aquí sobre el índice
en solo lectura, se le devuelve el resultado y se repite hasta que responde en prosa. Cada
paso sale hacia el navegador como un evento, porque la traza de llamadas es una de las
métricas del TFM y no un detalle de depuración.

# Lo que hay que saber antes de exponerlo

- Cuesta dinero por consulta (poco, pero de quien aloja el servidor). `Limitador` pone un
  tope por IP y otro diario global; superado, se responde 429 y se invita a usar el MCP con
  el propio agente del visitante, que es gratis para nosotros.
- El prompt del sistema lo pone el servidor. El cliente solo manda mensajes `user` y
  `assistant`, y `validar_mensajes` rechaza cualquier otra cosa.
- Los mensajes van a un tercero (OpenRouter y el proveedor del modelo). La página lo dice.
"""

from __future__ import annotations

import json
import os
import threading
import time
import traceback
import urllib.error
import urllib.request
from collections import deque
from collections.abc import Callable, Iterable, Iterator

from ..almacen import Almacen
from .herramientas import CATALOGO
from .servidor import INSTRUCCIONES, ServidorMCP, _log

URL_OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"
MODELO_POR_DEFECTO = "meta/muse-spark-1.3-contributor"

#: Pasos de herramienta por pregunta. Cuatro bastan para comparar ciudades y pedir un detalle.
MAX_PASOS = 6
#: Mensajes del historial que se conservan (los más recientes). El resto se descarta.
MAX_MENSAJES = 12
#: Longitud máxima de un mensaje del usuario.
MAX_CARACTERES = 4_000
#: Recorte del resultado de una herramienta antes de dárselo al modelo.
MAX_CARACTERES_RESULTADO = 12_000
#: Tiempo de espera de una llamada al modelo, en segundos.
TIEMPO_ESPERA = 90

SISTEMA = INSTRUCCIONES + (
    "\n\nCiudades del índice: {ciudades}. Los catálogos de Barcelona y Reus están en catalán: "
    "si una búsqueda en español no devuelve nada en esas ciudades, repítela con el término en "
    "catalán y dilo. Responde en el idioma de la pregunta, en prosa breve, con el título de "
    "cada dataset citado y su url_origen tal cual. No inventes nada que no venga de una "
    "herramienta."
)


class ErrorDelModelo(RuntimeError):
    """El proveedor devolvió un error o un flujo que no se entiende."""


# --------------------------------------------------------------------------------------
# Herramientas en el formato de OpenAI
# --------------------------------------------------------------------------------------


def herramientas_para_el_modelo() -> list[dict]:
    """Las cuatro herramientas, con el mismo esquema que se anuncia en `tools/list`."""
    return [
        {"type": "function",
         "function": {"name": nombre, "description": descripcion, "parameters": esquema}}
        for nombre, (_, descripcion, esquema) in CATALOGO.items()
    ]


# --------------------------------------------------------------------------------------
# Cliente del modelo (OpenRouter, API compatible con OpenAI, en streaming)
# --------------------------------------------------------------------------------------


def _transporte_http(url: str, clave: str) -> Callable[[dict], Iterable[str]]:
    """Devuelve la función que envía la carga y produce las líneas SSE de la respuesta."""

    def enviar(carga: dict) -> Iterator[str]:
        peticion = urllib.request.Request(
            url,
            data=json.dumps(carga).encode(),
            headers={
                "Authorization": f"Bearer {clave}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://datosabiertos.sejas.es",
                "X-Title": "Datos abiertos municipales (TFM)",
            },
            method="POST",
        )
        try:
            respuesta = urllib.request.urlopen(peticion, timeout=TIEMPO_ESPERA)
        except urllib.error.HTTPError as exc:
            detalle = exc.read().decode(errors="replace")[:500]
            raise ErrorDelModelo(f"el proveedor respondió {exc.code}: {detalle}") from exc
        with respuesta:
            for linea in respuesta:
                yield linea.decode("utf-8", errors="replace").rstrip("\r\n")

    return enviar


def leer_respuesta(lineas: Iterable[str]) -> Iterator[tuple[str, object]]:
    """Recorre un flujo SSE de *chat completions* y reconstruye el mensaje del asistente.

    Produce `("delta", texto)` por cada trozo de prosa y, al final, `("mensaje", dict)` con
    `content` y `tool_calls` completos. Los `tool_calls` llegan partidos en varios deltas
    (el nombre en el primero, los argumentos a trozos) y se acumulan por `index`.
    """
    contenido: list[str] = []
    llamadas: dict[int, dict] = {}
    for linea in lineas:
        if not linea or linea.startswith(":"):  # línea en blanco o comentario keep-alive
            continue
        if not linea.startswith("data:"):
            continue
        datos = linea[5:].strip()
        if datos == "[DONE]":
            break
        try:
            trozo = json.loads(datos)
        except json.JSONDecodeError as exc:
            raise ErrorDelModelo(f"flujo ilegible del proveedor: {exc}") from exc
        if "error" in trozo:
            error = trozo["error"]
            mensaje = error.get("message") if isinstance(error, dict) else str(error)
            raise ErrorDelModelo(mensaje or "error sin detalle del proveedor")
        opciones = trozo.get("choices") or []
        if not opciones:
            continue
        delta = opciones[0].get("delta") or {}
        if delta.get("content"):
            contenido.append(delta["content"])
            yield ("delta", delta["content"])
        for parte in delta.get("tool_calls") or []:
            indice = parte.get("index", 0)
            acumulada = llamadas.setdefault(
                indice, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
            if parte.get("id"):
                acumulada["id"] = parte["id"]
            funcion = parte.get("function") or {}
            if funcion.get("name"):
                acumulada["function"]["name"] += funcion["name"]
            if funcion.get("arguments"):
                acumulada["function"]["arguments"] += funcion["arguments"]

    mensaje: dict = {"role": "assistant", "content": "".join(contenido)}
    if llamadas:
        mensaje["tool_calls"] = [llamadas[i] for i in sorted(llamadas)]
    yield ("mensaje", mensaje)


class ClienteModelo:
    """Llama al modelo. `transporte` se inyecta en los tests para no tocar la red."""

    def __init__(self, clave: str, modelo: str = MODELO_POR_DEFECTO, url: str = URL_OPENROUTER,
                 transporte: Callable[[dict], Iterable[str]] | None = None) -> None:
        self.modelo = modelo
        self.transporte = transporte or _transporte_http(url, clave)

    def completar(self, mensajes: list[dict], herramientas: list[dict]) -> Iterator[tuple[str, object]]:
        carga = {
            "model": self.modelo,
            "messages": mensajes,
            "tools": herramientas,
            "temperature": 0,
            "max_tokens": 1_200,
            "stream": True,
        }
        yield from leer_respuesta(self.transporte(carga))


# --------------------------------------------------------------------------------------
# Validación del historial y límites de uso
# --------------------------------------------------------------------------------------


def validar_mensajes(historial: object) -> list[dict]:
    """Deja solo mensajes `user`/`assistant` bien formados y recorta al tramo final."""
    if not isinstance(historial, list) or not historial:
        raise ValueError("se esperaba una lista de mensajes no vacía")
    limpio = []
    for mensaje in historial:
        if not isinstance(mensaje, dict):
            raise ValueError("cada mensaje debe ser un objeto")
        rol, contenido = mensaje.get("role"), mensaje.get("content")
        if rol not in ("user", "assistant"):
            raise ValueError(f"rol no permitido: {rol!r}")
        if not isinstance(contenido, str) or not contenido.strip():
            raise ValueError("el contenido debe ser texto no vacío")
        if len(contenido) > MAX_CARACTERES:
            raise ValueError(f"mensaje demasiado largo (máximo {MAX_CARACTERES} caracteres)")
        limpio.append({"role": rol, "content": contenido.strip()})
    limpio = limpio[-MAX_MENSAJES:]
    while limpio and limpio[0]["role"] != "user":
        limpio.pop(0)
    if not limpio or limpio[-1]["role"] != "user":
        raise ValueError("la conversación debe terminar con un mensaje del usuario")
    return limpio


class Limitador:
    """Tope de peticiones por IP en una ventana y tope diario global. Hilo-seguro."""

    def __init__(self, por_ip: int, ventana: float, por_dia: int,
                 reloj: Callable[[], float] = time.time) -> None:
        self.por_ip, self.ventana, self.por_dia, self.reloj = por_ip, ventana, por_dia, reloj
        self._por_ip: dict[str, deque[float]] = {}
        self._dia = (0, 0)  # (número de día, peticiones)
        self._cerrojo = threading.Lock()

    def permitir(self, ip: str) -> str | None:
        """Registra la petición y devuelve `None`, o el motivo si se ha superado un tope."""
        ahora = self.reloj()
        with self._cerrojo:
            dia = int(ahora // 86_400)
            if self._dia[0] != dia:
                self._dia = (dia, 0)
            if self._dia[1] >= self.por_dia:
                return (f"se alcanzó el tope diario de {self.por_dia} consultas del chat "
                        "alojado; vuelve mañana o conecta el MCP a tu propio agente")
            cola = self._por_ip.setdefault(ip, deque())
            while cola and ahora - cola[0] > self.ventana:
                cola.popleft()
            if len(cola) >= self.por_ip:
                return (f"máximo de {self.por_ip} consultas cada {int(self.ventana // 60)} "
                        "minutos por dirección; espera un poco o conecta el MCP a tu propio agente")
            cola.append(ahora)
            self._dia = (dia, self._dia[1] + 1)
            if len(self._por_ip) > 10_000:  # que no crezca sin límite con IPs de paso
                self._por_ip = {k: v for k, v in self._por_ip.items() if v and ahora - v[-1] <= self.ventana}
        return None


def limitador_desde_entorno() -> Limitador:
    return Limitador(
        por_ip=int(os.environ.get("TFM_CHAT_LIMITE_IP", "20")),
        ventana=float(os.environ.get("TFM_CHAT_VENTANA", "600")),
        por_dia=int(os.environ.get("TFM_CHAT_LIMITE_DIA", "500")),
    )


def cliente_desde_entorno() -> ClienteModelo | None:
    """`None` si no hay clave: la página oculta el motor alojado y el MCP sigue funcionando."""
    clave = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not clave:
        return None
    # TFM_URL_MODELO permite apuntar a cualquier API compatible con OpenAI (Ollama, vLLM...).
    return ClienteModelo(clave, modelo=os.environ.get("TFM_MODELO_CHAT", MODELO_POR_DEFECTO),
                         url=os.environ.get("TFM_URL_MODELO", URL_OPENROUTER))


# --------------------------------------------------------------------------------------
# El bucle de agente
# --------------------------------------------------------------------------------------


def _prompt_del_sistema(almacen: Almacen) -> str:
    ciudades = ", ".join(f"{p['id']} ({p['municipio']})"
                         for p in almacen.estadisticas()["por_portal"])
    return SISTEMA.format(ciudades=ciudades)


def _ejecutar(servidor: ServidorMCP, llamada: dict) -> tuple[str, dict, dict]:
    """Ejecuta un tool_call por la misma puerta que `tools/call`: mismos errores, mismo JSON."""
    nombre = llamada["function"]["name"]
    try:
        argumentos = json.loads(llamada["function"]["arguments"] or "{}")
        if not isinstance(argumentos, dict):
            raise ValueError("los argumentos deben ser un objeto")
    except ValueError as exc:
        return nombre, {}, {"error": f"argumentos ilegibles para {nombre}: {exc}"}
    respuesta = servidor.atender({"jsonrpc": "2.0", "id": 0, "method": "tools/call",
                                  "params": {"name": nombre, "arguments": argumentos}})
    return nombre, argumentos, respuesta["result"]["structuredContent"]


def conversar(almacen: Almacen, historial: list[dict], cliente: ClienteModelo,
              max_pasos: int = MAX_PASOS) -> Iterator[dict]:
    """Atiende una pregunta y va produciendo eventos: `paso`, `delta`, `fin` o `error`."""
    servidor = ServidorMCP(almacen)
    herramientas = herramientas_para_el_modelo()
    mensajes = [{"role": "system", "content": _prompt_del_sistema(almacen)}, *historial]

    try:
        for paso in range(1, max_pasos + 1):
            t0 = time.monotonic()
            mensaje: dict | None = None
            for tipo, valor in cliente.completar(mensajes, herramientas):
                if tipo == "delta":
                    yield {"tipo": "delta", "texto": valor}
                else:
                    mensaje = valor
            if mensaje is None:
                raise ErrorDelModelo("el proveedor cerró el flujo sin mensaje")
            ms = round((time.monotonic() - t0) * 1000)

            llamadas = mensaje.get("tool_calls") or []
            if not llamadas:
                yield {"tipo": "fin", "pasos": paso - 1, "ms": ms}
                return

            mensajes.append(mensaje)
            for llamada in llamadas:
                nombre, argumentos, resultado = _ejecutar(servidor, llamada)
                yield {"tipo": "paso", "paso": paso, "ms": ms, "herramienta": nombre,
                       "argumentos": argumentos, "resultado": resultado}
                mensajes.append({
                    "role": "tool",
                    "tool_call_id": llamada.get("id") or f"paso{paso}",
                    "content": json.dumps(resultado, ensure_ascii=False)[:MAX_CARACTERES_RESULTADO],
                })
        yield {"tipo": "error", "mensaje": f"se alcanzó el máximo de {max_pasos} pasos sin "
                                           "respuesta final; prueba a acotar la pregunta"}
    except ErrorDelModelo as exc:
        yield {"tipo": "error", "mensaje": f"el modelo falló: {exc}"}
    except Exception as exc:  # noqa: BLE001 - el flujo debe cerrarse con un mensaje, no a medias
        _log(f"fallo en el chat: {traceback.format_exc()}")
        yield {"tipo": "error", "mensaje": f"fallo inesperado: {type(exc).__name__}: {exc}"}


__all__ = ["ClienteModelo", "ErrorDelModelo", "Limitador", "MAX_CARACTERES", "MAX_MENSAJES",
           "MAX_PASOS", "MODELO_POR_DEFECTO", "cliente_desde_entorno", "conversar",
           "herramientas_para_el_modelo", "leer_respuesta", "limitador_desde_entorno",
           "validar_mensajes"]
