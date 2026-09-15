"""Punto de entrada: `python -m datosabiertos.mcp`."""

import sys

from .servidor import principal

if __name__ == "__main__":
    sys.exit(principal())
