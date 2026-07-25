"""Punto de entrada: `python -m tfm.mcp`."""

import sys

from .servidor import principal

if __name__ == "__main__":
    sys.exit(principal())
