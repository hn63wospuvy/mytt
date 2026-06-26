# Bilingual Tutor — Cloud Profile

A stateless, browser-local Vietnamese ⇄ English speaking & chat tutor. The
**cloud profile** uses Google Gemini Live for STT + LLM + TTS server-side, so
the only things you run are a LiveKit SFU, a LiveKit agent worker, and a token
server that also serves the web client.

**Stateless by design:** no login, no accounts, no server-side database. Each
user enters a display name and **their own** Gemini API key in the browser; both
live only in the browser's `localStorage`. The key is forwarded to the agent
per connect inside the LiveKit room metadata and is **never persisted
server-side**.

```
browser ──ws/wss──▶ livekit (SFU) ◀──ws── agent (worker, Gemini Live)
   │
   └── http :8080 ──▶ token (mints LiveKit JWT + serves the web client)
```

## Layout

| Path                | What |
|---------------------|------|
| `frontend/`         | React + Vite + TypeScript web client (responsive, mobile-ready) |
| `backend/`          | Python `tutor_agent` package — the LiveKit agent worker + token server |
| `deployment/cloud/` | Docker Compose stack (LiveKit + agent + token), Dockerfile, config |

## Quick start

```bash
cd deployment/cloud
cp .env.example .env          # set LIVEKIT_API_KEY / LIVEKIT_API_SECRET
docker compose up --build -d
open http://localhost:8080    # enter your name + your own Gemini API key
```

Get a free Gemini API key at <https://aistudio.google.com/apikey>.

See [`deployment/cloud/README.md`](deployment/cloud/README.md) for production
hardening (TLS, domain, firewall, TURN) and configuration details.

## Develop

```bash
# frontend
cd frontend && npm install && npm run dev

# backend tests
cd backend && pip install -e ".[livekit,http,cloud]" && pytest
```
