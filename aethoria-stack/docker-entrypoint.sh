#!/bin/sh
# ═══════════════════════════════════════════
#  AETHORIA — Docker Entrypoint
#  Injiziert Umgebungsvariablen in index.html
#  bevor nginx startet.
# ═══════════════════════════════════════════

set -e

HTML="/usr/share/nginx/html/index.html"

# Standard-URL: Ollama auf dem Host
OLLAMA_URL="${OLLAMA_URL:-http://host.docker.internal:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.1:8b}"

echo "[AETHORIA] Ollama URL  : ${OLLAMA_URL}"
echo "[AETHORIA] Ollama Model: ${OLLAMA_MODEL}"

# Ersetze Platzhalter im HTML
sed -i "s|__OLLAMA_URL__|${OLLAMA_URL}|g"   "${HTML}"
sed -i "s|__OLLAMA_MODEL__|${OLLAMA_MODEL}|g" "${HTML}"

# Starte nginx
exec nginx -g "daemon off;"
