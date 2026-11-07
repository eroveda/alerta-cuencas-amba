#!/usr/bin/env bash
# Fase 0: consulta las fuentes cada 5 minutos y sirve el mapa en http://127.0.0.1:8790
# Cada consulta corre con tope de memoria (512 MB) para no colgar la PC.
set -euo pipefail
cd "$(dirname "$0")/.."

INTERVALO_S="${INTERVALO_S:-300}"
PUERTO="${PUERTO:-8790}"

if ss -ltn "sport = :$PUERTO" | grep -q LISTEN; then
  echo "El puerto $PUERTO ya está en uso. Probá: PUERTO=8791 $0" >&2
  exit 1
fi

.venv/bin/python -m http.server "$PUERTO" --bind 127.0.0.1 --directory web >/dev/null 2>&1 &
SERVIDOR=$!
trap 'kill $SERVIDOR 2>/dev/null' EXIT
echo "Mapa en http://127.0.0.1:$PUERTO  (Ctrl+C para cortar)"

while true; do
  systemd-run --user --scope --quiet --collect -p MemoryMax=512M \
    .venv/bin/python -m alertas.cli poll || echo "poll falló (se reintenta en ${INTERVALO_S}s)" >&2
  sleep "$INTERVALO_S"
done
