#!/usr/bin/env bash
# Despliega el proyecto en forge (datosabiertos.sejas.es): sincroniza el árbol de trabajo,
# incluido el índice local (datos/indice.sqlite, no versionado), y reconstruye el contenedor.
# El .env del servidor (SITE y DOMAIN) se crea a mano una vez y no se toca aquí.
set -euo pipefail

SERVER=forge
REMOTE_DIR=/opt/docker/other-sites/datosabiertos

cd "$(dirname "$0")"

echo "==> Sincronizando con $SERVER:$REMOTE_DIR"
rsync -az --delete \
  --exclude .git --exclude .claude --exclude __pycache__ --exclude '*.pyc' \
  --exclude research --exclude 'datos/cosecha.log' --exclude 'datos/*.sqlite-*' \
  --include 'web/datos/indice.sqlite.gz' --exclude 'web/datos/*' \
  --exclude .env --exclude PLAN.md --exclude TODOS.md --exclude docs/00-actas \
  ./ "$SERVER:$REMOTE_DIR/"

echo "==> Reconstruyendo el contenedor"
ssh "$SERVER" "cd $REMOTE_DIR && docker compose up -d --build"

echo "==> Estado"
ssh "$SERVER" "docker ps --filter name=datosabiertos_ --format 'table {{.Names}}\t{{.Status}}'"
curl -s "https://datosabiertos.sejas.es/salud"; echo
