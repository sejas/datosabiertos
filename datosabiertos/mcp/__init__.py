"""Servidor MCP del TFM: herramientas sobre el índice local de metadatos.

- `herramientas`: las cuatro herramientas del §4 del plan, como funciones Python.
- `servidor`: transporte MCP sobre stdio (JSON-RPC 2.0), sin dependencias.

`python -m datosabiertos.mcp` arranca el servidor.
"""

from .herramientas import CATALOGO

__all__ = ["CATALOGO"]
