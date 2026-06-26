#!/usr/bin/env bash
# Boot the LOCAL backend in spec order (§4.1) with health checks.
#
#   livekit-server → token server → [STT/LLM/TTS reachability] → LiveKit agent
#
# Model servers (STT/LLM/TTS) are external and started separately. This script
# probes them and prints what is missing rather than failing opaquely; with
# MOCK_ADAPTERS=1 the agent runs end-to-end without them (design §"testing").
set -euo pipefail

cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
PY="$(pwd)/.venv/bin/python"

# --- load .env ---------------------------------------------------------------
# A PROFILE set in the environment (e.g. by run_cloud.sh / run_local.sh) wins
# over the one in .env, so the run scripts can pick the profile explicitly.
_PROFILE_OVERRIDE="${PROFILE:-}"
if [[ -f .env ]]; then
  set -a; # shellcheck disable=SC1091
  source .env; set +a
else
  echo "⚠️  no .env (copy .env.example → .env). Using built-in defaults."
fi
[[ -n "$_PROFILE_OVERRIDE" ]] && export PROFILE="$_PROFILE_OVERRIDE"

# --- derive a >=32-byte LiveKit HMAC secret ----------------------------------
# Put ANY value in LIVEKIT_API_SECRET (even short, like "secret"): we SHA-256 it
# into a 64-hex key so PyJWT stops warning (RFC 7518 wants >=32 bytes), and hand
# the SAME derived key to livekit-server via LIVEKIT_KEYS — so token *signing*
# (token server / agent) and token *verification* (SFU) still use identical bytes.
LIVEKIT_API_KEY="${LIVEKIT_API_KEY:-devkey}"
if [[ -n "${LIVEKIT_API_SECRET:-}" ]]; then
  LIVEKIT_API_SECRET="$(printf %s "$LIVEKIT_API_SECRET" | shasum -a 256 | awk '{print $1}')"
  export LIVEKIT_API_KEY LIVEKIT_API_SECRET
  export LIVEKIT_KEYS="${LIVEKIT_API_KEY}: ${LIVEKIT_API_SECRET}"
fi

PIDS=()
cleanup() { for p in "${PIDS[@]:-}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM

probe() { # url name  → warn-only
  if curl -fsS --max-time 2 "$1" >/dev/null 2>&1; then
    echo "✅ $2 reachable ($1)"
  else
    echo "⚠️  $2 NOT reachable ($1) — start it, or set MOCK_ADAPTERS=1"
  fi
}

# --- 1. livekit-server (dev) -------------------------------------------------
if command -v livekit-server >/dev/null 2>&1; then
  echo "▶ livekit-server --dev"
  # Pass the derived keys explicitly so the SFU verifies with the same secret the
  # token server signs with (falls back to --dev's built-in keys if none set).
  if [[ -n "${LIVEKIT_KEYS:-}" ]]; then
    livekit-server --dev --bind 0.0.0.0 --keys "$LIVEKIT_KEYS" &
  else
    livekit-server --dev --bind 0.0.0.0 &
  fi
  PIDS+=($!)
  sleep 1
else
  echo "❌ livekit-server not on PATH. Install: https://docs.livekit.io/home/self-hosting/local/"
  echo "   (dev key/secret: devkey / secret)"
fi

# --- 2. token server ---------------------------------------------------------
echo "▶ token server :8080/token"
"$PY" -m tutor_agent.token_server.server &
PIDS+=($!)
sleep 1
probe "http://127.0.0.1:8080/healthz" "token server"

# --- 3–5. model servers (external) — reachability only -----------------------
probe "${STT_BASE_URL:-http://127.0.0.1:8000/v1}/models" "STT (Nemotron)"
probe "${LLM_BASE_URL:-http://127.0.0.1:8082/v1}/models" "LLM (Qwen3-8B)"
probe "${TTS_BASE_URL:-http://127.0.0.1:8001}/healthz"   "TTS (VieNeu)"

if [[ "${MOCK_ADAPTERS:-}" == "1" ]]; then
  echo "🧪 MOCK_ADAPTERS=1 — agent uses mock STT/LLM/TTS/search (no models needed)."
fi

# --- 6. LiveKit agent --------------------------------------------------------
echo "▶ tutor agent (dev). Ctrl-C to stop everything."
exec "$PY" -m tutor_agent.agent dev
