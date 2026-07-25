"""Servidor MCP sobre stdio, sin dependencias externas.

    python -m tfm.mcp

Habla JSON-RPC 2.0 por entrada/salida estándar, que es el transporte `stdio` de MCP. Se
implementan los métodos que un cliente necesita de verdad: `initialize`,
`notifications/initialized`, `tools/list`, `tools/call` y `ping`.

# ¿Por qué a mano y no con el SDK oficial?

Porque es un prototipo y el precio de la dependencia no se paga todavía:

- El paquete es instalable y ejecutable en cualquier máquina con Python 3.11, incluida la
  Raspberry Pi donde se construye el índice, sin `pip install` ni entorno virtual.
- Los tests del protocolo corren sin red y sin instalar nada.
- Son ~120 líneas: `initialize`, `tools/list`, `tools/call`.

Cuando haga falta lo que el SDK sí aporta —*resources*, *prompts*, *sampling*, SSE/HTTP
*streamable*, cancelación— se migra. La lógica no se toca: vive en `herramientas.py`, que no
sabe nada de JSON-RPC. Ese es el motivo real de la separación.

Registro: a `stderr`, nunca a `stdout`. `stdout` es el canal del protocolo; un `print` de
depuración ahí rompe la sesión del cliente.
"""

from __future__ import annotations

import json
import sys
import traceback

from .. import configuracion as cfg
from ..almacen import Almacen
from .herramientas import CATALOGO

#: Revisión del protocolo que se anuncia. Si el cliente pide otra, se responde con la
#: propia y es él quien decide si sigue, como manda la especificación.
VERSION_PROTOCOLO = "2025-06-18"

INFO_SERVIDOR = {"name": "tfm-datos-abiertos", "title": "Datos abiertos municipales (TFM)",
                 "version": cfg.VERSION}

INSTRUCCIONES = (
    "Consulta metadatos de catálogos municipales españoles de datos abiertos desde una copia "
    "local. Reglas: (1) no inventes datasets — si una herramienta no devuelve resultados, dilo; "
    "(2) cita siempre `url_origen`; (3) si `licencia_declarada` es false, di que el portal no "
    "declara licencia, no supongas que es abierta; (4) menciona `fecha_sincronizacion` cuando "
    "la actualidad importe, porque los datos son una copia y no el portal en vivo."
)


def _log(mensaje: str) -> None:
    print(f"[tfm.mcp] {mensaje}", file=sys.stderr, flush=True)


def _contenido(datos: dict) -> dict:
    """Resultado de `tools/call`: JSON legible como texto, más `structuredContent`."""
    return {
        "content": [{"type": "text", "text": json.dumps(datos, ensure_ascii=False, indent=1)}],
        "structuredContent": datos,
        "isError": bool(datos.get("error")),
    }


class ServidorMCP:
    """Encaminador de peticiones JSON-RPC hacia el catálogo de herramientas."""

    def __init__(self, almacen: Almacen) -> None:
        self.almacen = almacen
        self.iniciado = False

    # -- métodos del protocolo ------------------------------------------------------------
    def _initialize(self, parametros: dict) -> dict:
        pedida = parametros.get("protocolVersion")
        if pedida and pedida != VERSION_PROTOCOLO:
            _log(f"el cliente pide el protocolo {pedida}; se responde {VERSION_PROTOCOLO}")
        return {
            "protocolVersion": VERSION_PROTOCOLO,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": INFO_SERVIDOR,
            "instructions": INSTRUCCIONES,
        }

    def _tools_list(self, _parametros: dict) -> dict:
        return {
            "tools": [
                {"name": nombre, "description": descripcion, "inputSchema": esquema}
                for nombre, (_, descripcion, esquema) in CATALOGO.items()
            ]
        }

    def _tools_call(self, parametros: dict) -> dict:
        nombre = parametros.get("name")
        argumentos = parametros.get("arguments") or {}
        if nombre not in CATALOGO:
            disponibles = ", ".join(CATALOGO)
            return _contenido({"error": f"herramienta desconocida: {nombre}",
                               "herramientas_disponibles": disponibles})
        funcion = CATALOGO[nombre][0]
        try:
            return _contenido(funcion(self.almacen, **argumentos))
        except TypeError as exc:  # argumentos que no encajan con la firma
            return _contenido({"error": f"argumentos inválidos para {nombre}: {exc}"})
        except ValueError as exc:  # identificador mal formado, etc.
            return _contenido({"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - un fallo no debe tumbar la sesión
            _log(f"fallo en {nombre}: {traceback.format_exc()}")
            return _contenido({"error": f"fallo interno en {nombre}: {type(exc).__name__}: {exc}"})

    # -- bucle ----------------------------------------------------------------------------
    def atender(self, peticion: dict) -> dict | None:
        """Procesa un mensaje. Devuelve la respuesta, o `None` si era una notificación."""
        metodo = peticion.get("method")
        identificador = peticion.get("id")
        parametros = peticion.get("params") or {}

        if metodo == "notifications/initialized":
            self.iniciado = True
            _log("cliente inicializado")
            return None
        if metodo and metodo.startswith("notifications/"):
            return None

        manejadores = {
            "initialize": self._initialize,
            "tools/list": self._tools_list,
            "tools/call": self._tools_call,
            "ping": lambda _p: {},
        }
        if metodo not in manejadores:
            return {
                "jsonrpc": "2.0",
                "id": identificador,
                "error": {"code": -32601, "message": f"método no implementado: {metodo}"},
            }
        return {"jsonrpc": "2.0", "id": identificador, "result": manejadores[metodo](parametros)}

    def servir(self, entrada=sys.stdin, salida=sys.stdout) -> None:
        _log(f"escuchando en stdio · índice {cfg.RUTA_INDICE} · "
             f"{len(CATALOGO)} herramientas: {', '.join(CATALOGO)}")
        for linea in entrada:
            linea = linea.strip()
            if not linea:
                continue
            try:
                peticion = json.loads(linea)
            except json.JSONDecodeError as exc:
                salida.write(json.dumps({"jsonrpc": "2.0", "id": None,
                                         "error": {"code": -32700,
                                                   "message": f"JSON mal formado: {exc}"}}) + "\n")
                salida.flush()
                continue
            respuesta = self.atender(peticion)
            if respuesta is not None:
                salida.write(json.dumps(respuesta, ensure_ascii=False) + "\n")
                salida.flush()


def principal() -> int:
    if not cfg.RUTA_INDICE.exists():
        _log(f"no hay índice en {cfg.RUTA_INDICE}. Constrúyelo con: python -m tfm.index build")
        return 1
    with Almacen(cfg.RUTA_INDICE) as almacen:
        try:
            ServidorMCP(almacen).servir()
        except (KeyboardInterrupt, BrokenPipeError):
            _log("cierre")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
