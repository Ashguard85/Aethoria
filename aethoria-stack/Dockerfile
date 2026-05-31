# ═══════════════════════════════════════════
#  AETHORIA Companion App — Dockerfile
#  nginx:alpine + env-variable injection
# ═══════════════════════════════════════════
FROM nginx:alpine

# Konfiguration kopieren
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# App-Dateien kopieren
COPY app/ /usr/share/nginx/html/

# Startup-Skript: injiziert OLLAMA_URL zur Laufzeit in die HTML
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
