# Cloud deployment (Docker Compose)

Runs the tutor in the **CLOUD profile**: Gemini Live handles STT + LLM + TTS
server-side, so there are **no on-device model servers**. Only three containers
run — lowest latency, smallest image.

The deployment is **stateless**: no user accounts, no server-side API-key
storage, no learning database. The user enters a display name and their own
Gemini API key in the browser; both are stored in the browser's localStorage.
The Gemini key is forwarded to the agent inside the LiveKit join-token room
metadata and is never persisted on the server.

```
browser ──ws/wss──▶ livekit (SFU) ◀──ws── agent (worker, Gemini Live)
   │
   └── http :8080 ──▶ token (mints JWT + serves the web client)
```

| Service   | Image                        | Port(s)              | Role |
|-----------|------------------------------|----------------------|------|
| `livekit` | `livekit/livekit-server`     | 7880, 7881, 7882/udp | WebRTC SFU |
| `agent`   | `tutor-backend:cloud`        | —                    | LiveKit worker (`PROFILE=cloud`) |
| `token`   | `tutor-backend:cloud`        | 8080                 | mints LiveKit JWTs + serves `web/` |

`agent` and `token` share one image (`Dockerfile`); the role is the `command`.

## Quick start

```bash
cd deployment/cloud
cp .env.example .env          # set LIVEKIT_API_KEY / LIVEKIT_API_SECRET
docker compose up --build -d
open http://localhost:8080     # web client — enter your name + Gemini API key
```

Stop / logs:

```bash
docker compose logs -f agent
docker compose down
```

## Configuration

All knobs live in `.env` (see `.env.example`):

- **`LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET`** — shared by the SFU, the agent and
  the token server. **Change the secret** (`openssl rand -hex 32`) before any
  non-local deploy.
- **`PUBLIC_LIVEKIT_URL`** — the WS/WSS URL the **browser** uses. This differs
  from the agent's internal `ws://livekit:7880`: the browser can't resolve the
  compose-internal name, so the token server hands it this public URL.
- `GEMINI_LIVE_MODEL`, `GEMINI_LANGUAGE`, `GEMINI_THINKING_BUDGET`, `LEVEL` —
  optional model/session tuning.

The Gemini API key is **not** configured here — each user supplies their own
key in the browser UI. It is passed to the agent via LiveKit room metadata
and is never stored server-side.

## Production hardening

The defaults run on `localhost` for a quick smoke. For a real deploy on a Linux
VM with a public IP:

1. **TLS + domain.** Put a reverse proxy (Caddy/nginx) in front of `:8080`
   (web/token) and the LiveKit signaling `:7880`. Then set
   `PUBLIC_LIVEKIT_URL=wss://livekit.your-domain.tld`. Browsers on an HTTPS page
   require `wss://` (mixed-content blocks plain `ws://`).
2. **Firewall.** Open `7880/tcp` (signaling), `7881/tcp` and `7882/udp` (media).
   The agent/Gemini traffic is all outbound.
3. **Secret.** Never ship the example `LIVEKIT_API_SECRET`.
4. **TURN.** `use_external_ip: true` (in `livekit.yaml`) covers most VMs. Clients
   behind strict NAT/firewalls also need a TURN server — see
   <https://docs.livekit.io/home/self-hosting/deployment/>.

## macOS / local note

On macOS, Docker runs in a VM and container IPs aren't host-reachable, so the
SFU's media candidates may not reach a browser on the same Mac. For local cloud-
profile testing on a Mac, run the dev stack instead
(`PROFILE=cloud scripts/run_cloud.sh`, which uses `livekit-server --dev`). This
compose stack targets a **Linux host** (cloud VM). On Linux it works as-is; for a
purely-local Linux box you can set `use_external_ip: false` in `livekit.yaml`.

## Notes / trade-offs

- Cloud profile speaks naturally (no `<vi>/<en>` markers), so learning-data
  extraction is reduced vs LOCAL — a documented Phase-3 trade-off (see backend
  README). Transcripts stream to the UI via LiveKit's native transcription and
  are stored only in the browser's localStorage; there is no server-side history
  database.
- The image installs `.[livekit,http,cloud]` only — no `mlx`/`whisper`.
- The token server resolves the web client relative to the source tree
  (`PYTHONPATH=/app/src`, `web/` sibling at `/app/web`); the Dockerfile preserves
  that layout. Don't "optimize" it to a bare `pip install` of just the package.
