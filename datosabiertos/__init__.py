"""Paquete del TFM: índice local de metadatos de catálogos municipales de datos abiertos.

Módulos:

- `configuracion`: corpus de portales, `User-Agent`, límites de cortesía.
- `cortesia`: cliente HTTP cortés (robots.txt, `Crawl-Delay`, concurrencia, *backoff*).
- `registro`: registro de eventos y de errores por portal.
- `modelo`: representación normalizada de dataset y distribución.
- `esquema`: DDL de SQLite (incluida la tabla FTS5 en español).
- `almacen`: capa de persistencia sobre SQLite.
- `conectores`: `ConectorCatalogo` (interfaz) y `ConectorCKAN` (implementación).
- `index`: interfaz de línea de órdenes (`python -m datosabiertos.index build`).

Sin dependencias externas: solo biblioteca estándar de Python 3.
"""

__version__ = "0.1.0"
