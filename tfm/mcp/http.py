"""Transporte HTTP para el servidor MCP, sin dependencias externas.

    python -m tfm.mcp.http --puerto 8080

Sirve el mismo `ServidorMCP` que `stdio`, pero por red, para que lo use gente que no tiene
el repositorio: es lo que hace data.gouv.fr con `mcp.data.gouv.fr`. Un cliente MCP se
conecta con una URL y **pone su propio modelo**, así que el coste de operación es solo el
alojamiento: un fichero SQLite de 21 MB en modo lectura.

Rutas:

- `POST /mcp` — JSON-RPC 2.0. Es el transporte *Streamable HTTP* en su forma mínima: se
  responde `application/json`, sin SSE ni sesiones. Suficiente para `initialize`,
  `tools/list` y `tools/call`, que es todo lo que este servidor implementa.
- `POST /chat` — chat con un modelo alojado (OpenRouter) que usa las herramientas; responde
  en SSE con un evento por paso. Solo existe si hay `OPENROUTER_API_KEY`; véase `chat.py`.
- `GET /salud` — estado, nº de datasets, fecha de la última sincronización y si hay chat.
- `GET /` — descripción legible con el catálogo de herramientas.

CORS abierto a propósito: los metadatos son públicos y reutilizables, y así una página web
—el cliente en el navegador de la fase 6— puede llamar al servidor sin pasarela.

# Límites conocidos de este prototipo

- Sin SSE ni `Mcp-Session-Id`: un cliente que exija *streaming* no funcionará.
- Sin autenticación ni cuota. Antes de exponerlo en internet de forma permanente hay que
  poner un límite de peticiones por IP delante (nginx, Cloudflare) o pasar al SDK oficial.
- `ThreadingHTTPServer` con SQLite en solo lectura: se abre una conexión por hilo, porque
  un objeto `sqlite3.Connection` no se comparte entre hilos.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .. import configuracion as cfg
from ..almacen import Almacen
from . import chat
from .herramientas import CATALOGO
from .servidor import INFO_SERVIDOR, VERSION_PROTOCOLO, ServidorMCP

TAMANO_MAXIMO = 1_000_000  # 1 MB de cuerpo: una petición JSON-RPC legítima no llega ni cerca

#: Directorio de ficheros estáticos (el cliente en el navegador). Si está, el mismo proceso
#: sirve el MCP y la página, así que comparten origen y no hace falta CORS entre ellos.
DIRECTORIO_ESTATICOS: Path | None = None

#: Modelo alojado para `POST /chat`. `None` si no hay clave: la ruta responde 503 y la página
#: solo ofrece el modelo del navegador. Se rellena en `principal()`.
CLIENTE_CHAT: chat.ClienteModelo | None = None
LIMITADOR_CHAT: chat.Limitador = chat.limitador_desde_entorno()

_local = threading.local()


def _servidor_del_hilo() -> ServidorMCP:
    """Un `Almacen` por hilo: `sqlite3` no permite compartir conexión entre hilos."""
    if not hasattr(_local, "servidor"):
        _local.servidor = ServidorMCP(Almacen(cfg.RUTA_INDICE, solo_lectura=True))
    return _local.servidor


class Manejador(BaseHTTPRequestHandler):
    server_version = f"tfm-mcp/{cfg.VERSION}"

    def log_message(self, formato, *args):  # noqa: A002 - firma de la stdlib
        print(f"[tfm.mcp.http] {self.address_string()} {formato % args}", file=sys.stderr)

    def _responder(self, codigo: int, cuerpo: dict | str, tipo="application/json") -> None:
        datos = (json.dumps(cuerpo, ensure_ascii=False) if isinstance(cuerpo, dict)
                 else cuerpo).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", f"{tipo}; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Mcp-Session-Id")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(datos)

    def do_OPTIONS(self):  # noqa: N802 - lo impone la stdlib
        self._responder(204, "")

    def do_GET(self):  # noqa: N802
        servidor = _servidor_del_hilo()
        if self.path.rstrip("/") in ("/salud", "/health"):
            estadisticas = servidor.almacen.estadisticas()
            ultima = servidor.almacen.conexion.execute(
                "SELECT valor FROM metadatos_indice WHERE clave = 'ultima_sincronizacion'"
            ).fetchone()
            self._responder(200, {
                "estado": "ok",
                "datasets": estadisticas["datasets"],
                "distribuciones": estadisticas["distribuciones"],
                "ciudades": [f["municipio"] for f in estadisticas["por_portal"]],
                "sin_licencia_declarada": estadisticas["sin_licencia"],
                "ultima_sincronizacion": ultima["valor"] if ultima else None,
                "chat": {"disponible": True, "modelo": CLIENTE_CHAT.modelo,
                         "limite_por_ip": LIMITADOR_CHAT.por_ip,
                         "ventana_segundos": int(LIMITADOR_CHAT.ventana)}
                if CLIENTE_CHAT else {"disponible": False},
            })
        elif self.path.rstrip("/") == "/mcp" or (
            self.path.rstrip("/") == "" and DIRECTORIO_ESTATICOS is None
        ):
            # Con `--estaticos`, la raíz es la página del navegador y la descripción de la
            # API vive solo en /mcp. Sin estáticos, la raíz describe la API.
            self._responder(200, {
                "servidor": INFO_SERVIDOR,
                "protocolo_mcp": VERSION_PROTOCOLO,
                "endpoint": "POST /mcp (JSON-RPC 2.0)",
                "herramientas": {n: d for n, (_, d, _) in CATALOGO.items()},
                "licencia_datos": (
                    "Metadatos reutilizados de portales municipales. La licencia de cada "
                    "dataset viaja en cada respuesta; los que no la declaran salen marcados."
                ),
            })
        elif self._servir_estatico():
            return
        else:
            self._responder(404, {"error": "no existe esa ruta",
                                  "rutas": ["/", "/mcp", "/salud", "POST /chat"]})

    def _servir_estatico(self) -> bool:
        """Sirve la página del navegador. Devuelve False si no hay nada que servir.

        Se resuelve la ruta y se comprueba que sigue dentro del directorio: sin eso, un
        `GET /../../etc/passwd` saldría del árbol.
        """
        if DIRECTORIO_ESTATICOS is None:
            return False
        relativa = self.path.split("?", 1)[0].lstrip("/") or "index.html"
        try:
            destino = (DIRECTORIO_ESTATICOS / relativa).resolve()
            destino.relative_to(DIRECTORIO_ESTATICOS.resolve())
        except (ValueError, OSError):
            return False
        if destino.is_dir():
            destino = destino / "index.html"
        if not destino.is_file():
            return False

        tipo = mimetypes.guess_type(destino.name)[0] or "application/octet-stream"
        datos = destino.read_bytes()
        cabeceras = {}
        # El índice se sirve comprimido si existe el .gz al lado: 21 MB -> 3,4 MB.
        comprimido = destino.with_suffix(destino.suffix + ".gz")
        if comprimido.is_file() and "gzip" in (self.headers.get("Accept-Encoding") or ""):
            datos = comprimido.read_bytes()
            cabeceras["Content-Encoding"] = "gzip"
        self.send_response(200)
        self.send_header("Content-Type", f"{tipo}; charset=utf-8" if tipo.startswith("text/")
                         else tipo)
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "public, max-age=3600")
        for clave, valor in cabeceras.items():
            self.send_header(clave, valor)
        self.end_headers()
        self.wfile.write(datos)
        return True

    def _leer_json(self) -> object | None:
        """Cuerpo JSON de la petición, o `None` tras haber respondido ya con el error."""
        longitud = int(self.headers.get("Content-Length") or 0)
        if longitud > TAMANO_MAXIMO:
            self._responder(413, {"jsonrpc": "2.0", "id": None,
                                  "error": {"code": -32600, "message": "cuerpo demasiado grande"}})
            return None
        try:
            return json.loads(self.rfile.read(longitud) or b"{}")
        except json.JSONDecodeError as exc:
            self._responder(400, {"jsonrpc": "2.0", "id": None,
                                  "error": {"code": -32700, "message": f"JSON mal formado: {exc}"}})
            return None

    def _ip_cliente(self) -> str:
        """Detrás de Traefik la IP real viene en X-Forwarded-For; en local, la del socket."""
        reenviada = self.headers.get("X-Forwarded-For")
        if reenviada:
            return reenviada.split(",")[0].strip()
        return self.client_address[0]

    def _chat(self) -> None:
        if CLIENTE_CHAT is None:
            self._responder(503, {"error": "el chat alojado no está configurado en este servidor; "
                                           "usa el modelo del navegador o conecta el MCP a tu agente"})
            return
        motivo = LIMITADOR_CHAT.permitir(self._ip_cliente())
        if motivo:
            self._responder(429, {"error": motivo})
            return
        cuerpo = self._leer_json()
        if cuerpo is None:
            return
        try:
            historial = chat.validar_mensajes((cuerpo or {}).get("messages")
                                              if isinstance(cuerpo, dict) else None)
        except ValueError as exc:
            self._responder(400, {"error": str(exc)})
            return

        # SSE: un `data:` por evento. Sin Content-Length; la conexión se cierra al terminar.
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        almacen = _servidor_del_hilo().almacen
        try:
            for evento in chat.conversar(almacen, historial, CLIENTE_CHAT):
                self.wfile.write(f"data: {json.dumps(evento, ensure_ascii=False)}\n\n".encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # el navegador cerró la pestaña a medias; no hay a quién avisar

    def do_POST(self):  # noqa: N802
        if self.path.rstrip("/") == "/chat":
            self._chat()
            return
        if self.path.rstrip("/") not in ("/mcp", ""):
            self._responder(404, {"error": "usa POST /mcp o POST /chat"})
            return
        peticion = self._leer_json()
        if peticion is None:
            return

        servidor = _servidor_del_hilo()
        if isinstance(peticion, list):  # lote JSON-RPC
            respuestas = [r for r in (servidor.atender(p) for p in peticion) if r is not None]
            self._responder(200, json.dumps(respuestas, ensure_ascii=False))
            return
        respuesta = servidor.atender(peticion)
        if respuesta is None:  # notificación: 202 sin cuerpo, como manda la especificación
            self._responder(202, "")
            return
        self._responder(200, respuesta)


def principal(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(prog="python -m tfm.mcp.http")
    analizador.add_argument("--puerto", type=int, default=8080)
    analizador.add_argument("--host", default="127.0.0.1",
                            help="0.0.0.0 para exponerlo fuera de la máquina")
    analizador.add_argument("--estaticos", default=None,
                            help="directorio con el cliente web (p. ej. web/)")
    args = analizador.parse_args(argv)

    global DIRECTORIO_ESTATICOS
    if args.estaticos:
        DIRECTORIO_ESTATICOS = Path(args.estaticos).resolve()
        if not DIRECTORIO_ESTATICOS.is_dir():
            print(f"No existe el directorio de estáticos: {DIRECTORIO_ESTATICOS}", file=sys.stderr)
            return 1

    global CLIENTE_CHAT
    CLIENTE_CHAT = chat.cliente_desde_entorno()

    if not cfg.RUTA_INDICE.exists():
        print(f"No hay índice en {cfg.RUTA_INDICE}. Ejecuta: python -m tfm.index build",
              file=sys.stderr)
        return 1

    servidor = ThreadingHTTPServer((args.host, args.puerto), Manejador)
    print(f"[tfm.mcp.http] http://{args.host}:{args.puerto}/mcp · "
          f"{len(CATALOGO)} herramientas · índice {cfg.RUTA_INDICE}"
          + (f" · web {DIRECTORIO_ESTATICOS}" if DIRECTORIO_ESTATICOS else "")
          + (f" · chat con {CLIENTE_CHAT.modelo}" if CLIENTE_CHAT else " · sin chat alojado"),
          file=sys.stderr)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("[tfm.mcp.http] cierre", file=sys.stderr)
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
