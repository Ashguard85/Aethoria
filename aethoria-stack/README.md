# AETHORIA — Companion App

> Weltmaschine für das Brettspiel AETHORIA.  
> Läuft als Docker-Container, Ollama auf dem Host.

## Voraussetzungen

- Docker + Docker Compose
- Portainer (optional, aber empfohlen)
- Ollama auf dem Host: `ollama serve` + `ollama pull llava`

---

## Schnellstart (ohne Portainer)

```bash
git clone <dein-repo-url>
cd aethoria-stack

cp .env.example .env
# .env bei Bedarf anpassen (Port, Modell)

docker compose up -d --build
```

App öffnen: **http://localhost:8080**  
(oder deinen konfigurierten Port)

---

## Portainer Stack — Schritt für Schritt

### 1. Repo auf GitHub/Gitea anlegen

```bash
git init
git add .
git commit -m "Initial: AETHORIA Companion Stack"
git remote add origin https://github.com/dein-user/aethoria-stack.git
git push -u origin main
```

### 2. In Portainer: Stack erstellen

1. **Stacks → Add Stack**
2. Name: `aethoria`
3. Build method: **Repository**
4. Repository URL: `https://github.com/dein-user/aethoria-stack`
5. Branch: `main`
6. Compose path: `docker-compose.yml`

### 3. Environment Variables in Portainer eintragen

| Variable | Wert | Beschreibung |
|---|---|---|
| `APP_PORT` | `8080` | Port der Web-App |
| `OLLAMA_URL` | `http://host-gateway:11434` | Ollama auf dem Host |
| `OLLAMA_MODEL` | `llava` | Ollama-Modell |

> **Tipp:** `host-gateway` ist der Docker-interne Hostname für den  
> Ubuntu-Host — funktioniert ohne weitere Konfiguration.

### 4. Deploy

Klick auf **Deploy the stack** — fertig.

---

## Updates deployen

```bash
# Änderungen pushen
git add . && git commit -m "Update" && git push

# In Portainer: Stack → Pull and redeploy
```

---

## Ollama auf Ubuntu einrichten (einmalig)

```bash
# Installieren
curl -fsSL https://ollama.ai/install.sh | sh

# Modell laden (einmalig, ~4 GB)
ollama pull llava

# Als Systemdienst (startet automatisch)
sudo systemctl enable ollama
sudo systemctl start ollama

# Testen
curl http://localhost:11434/api/tags
```

---

## Health Check

```
GET http://localhost:8080/health
→ {"status":"ok","app":"aethoria-companion"}
```

---

## Struktur

```
aethoria-stack/
├── docker-compose.yml     # Stack-Definition
├── Dockerfile             # nginx + env-injection
├── docker-entrypoint.sh   # Injiziert OLLAMA_URL/MODEL
├── .env.example           # Vorlage für Variablen
├── .gitignore
├── README.md
├── app/
│   └── index.html         # Companion App
└── nginx/
    └── default.conf       # nginx Konfiguration
```
