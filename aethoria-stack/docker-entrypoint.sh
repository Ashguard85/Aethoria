#!/bin/sh
set -e
HTML="/usr/share/nginx/html/index.html"

OLLAMA_URL="${OLLAMA_URL:-http://host.docker.internal:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.1:8b}"
ENABLE_API="${ENABLE_API:-false}"
API_URL="${API_URL:-http://localhost:8001}"

echo "[AETHORIA] Ollama URL   : ${OLLAMA_URL}"
echo "[AETHORIA] Ollama Model : ${OLLAMA_MODEL}"
echo "[AETHORIA] API Mode     : ${ENABLE_API} (${API_URL})"

sed -i "s|__OLLAMA_URL__|${OLLAMA_URL}|g"     "${HTML}"
sed -i "s|__OLLAMA_MODEL__|${OLLAMA_MODEL}|g" "${HTML}"
sed -i "s|__ENABLE_API__|${ENABLE_API}|g"     "${HTML}"
sed -i "s|__API_URL__|${API_URL}|g"           "${HTML}"

exec nginx -g "daemon off;"
