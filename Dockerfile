# Servidor MCP por HTTP + cliente del navegador, en un solo contenedor.
# Sin dependencias: solo la biblioteca estándar, así que no hay `pip install` ni ruedas que
# compilar. La imagen pesa lo que pesa python:slim más el código y el índice.
FROM python:3.12-slim

WORKDIR /app
COPY datosabiertos/ /app/datosabiertos/
COPY web/ /app/web/
COPY datos/indice.sqlite /app/datos/indice.sqlite

ENV PYTHONUNBUFFERED=1 \
    TFM_RUTA_INDICE=/app/datos/indice.sqlite

EXPOSE 8080

# El índice se abre en solo lectura (véase datosabiertos/almacen.py): el contenedor no lo modifica.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/salud',timeout=4).status==200 else 1)"

CMD ["python", "-m", "datosabiertos.mcp.http", "--host", "0.0.0.0", "--puerto", "8080", "--estaticos", "web"]
