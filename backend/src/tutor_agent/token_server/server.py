"""Mint short-lived LiveKit access tokens over HTTP (spec §4.1 step 2, §11).

Stateless: no login, no database, no per-user storage. The browser holds the
user's name + Gemini key in localStorage and mints a random ``client_id`` once.
Routes:

- ``POST /token`` → mint a LiveKit join token. Body JSON
  ``{client_id, key, thinking?}``. Identity is the client-supplied
  ``client_id``; the room is derived server-side (``tutor-<client_id>``) so
  every browser gets its own room/agent. The Gemini ``key`` rides in the room
  metadata (the agent reads it on join) and is **never** persisted. Returns
  ``400`` when ``key`` or ``client_id`` is missing.
- ``GET  /healthz`` → liveness probe.
- ``GET  /`` + static → the built web client (Vite ``frontend/dist``).
"""

from __future__ import annotations

import json
import os
from datetime import timedelta
from pathlib import Path
from typing import Any, Optional

from livekit import api

from ..config import ConfigError, Settings

DEFAULT_TTL_SECONDS = 6 * 60 * 60  # 6h — long enough for a lesson, still bounded

# Must match the name on @server.rtc_session(agent_name=...) in agent.py. The
# agent is a *named* worker, so it is only dispatched to a room when the join
# token carries this explicit dispatch; without it the agent never joins.
AGENT_NAME = "tutor"

# Agent dispatch fires when the room is *created*. An empty room lingers for
# this many seconds after the last participant leaves; a stale empty room would
# block the next join from re-dispatching the agent. Short for snappy local
# dev/test reconnects.
ROOM_EMPTY_TIMEOUT_SECONDS = 10

# Where the built web client (Vite `frontend/dist`) lives. Override with the
# WEB_DIR env var; the default is the repo-root frontend/dist for local dev.
# This module is backend/src/tutor_agent/token_server/server.py, so parents[4]
# is the repo root and parents[4]/frontend/dist is the Vite build output.
# The path math does NOT survive the container: the runtime image flattens
# backend/ into /app, so server.py sits at /app/src/... and parents[4] is the
# filesystem root, not the repo root. The Docker image therefore sets
# WEB_DIR=/app/frontend/dist explicitly (see deployment/cloud/Dockerfile),
# where the node build stage's dist is copied. Anchored on the file path so the
# local default resolves regardless of the process CWD; dist is a build
# artifact and may be absent in a bare checkout (the index/static routes below
# are only registered when it exists).
_DEFAULT_WEB_DIR = Path(__file__).resolve().parents[4] / "frontend" / "dist"


def _resolve_web_dir(env_value: Optional[str], default: Path) -> Path:
    """WEB_DIR resolution: the env override wins when set & non-empty, else the
    local-dev default (repo-root frontend/dist). Pure for testability."""
    return Path(env_value) if env_value else default


WEB_DIR = _resolve_web_dir(os.environ.get("WEB_DIR"), _DEFAULT_WEB_DIR)


def mint_access_token(
    *,
    api_key: str,
    api_secret: str,
    identity: str,
    room: str,
    ttl_seconds: int,
    room_metadata: Optional[dict] = None,
) -> str:
    room_config = api.RoomConfiguration(
        agents=[api.RoomAgentDispatch(agent_name=AGENT_NAME)],
        empty_timeout=ROOM_EMPTY_TIMEOUT_SECONDS,
    )
    # Per-session knobs the client picks in the UI (thinking budget) and the
    # per-connect Gemini key ride along as room metadata; the agent reads
    # ctx.room.metadata on join.
    if room_metadata:
        room_config.metadata = json.dumps(room_metadata)
    return (
        api.AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_grants(api.VideoGrants(room_join=True, room=room))
        .with_room_config(room_config)
        .with_ttl(timedelta(seconds=ttl_seconds))
        .to_jwt()
    )


def token_response(
    settings: Settings,
    *,
    identity: str,
    room: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    room_metadata: Optional[dict] = None,
) -> dict:
    if not settings.livekit_api_key or not settings.livekit_api_secret:
        raise ConfigError(
            "LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set on the token server"
        )
    token = mint_access_token(
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
        identity=identity,
        room=room,
        ttl_seconds=ttl_seconds,
        room_metadata=room_metadata,
    )
    return {
        "token": token,
        "url": settings.livekit_url,
        "identity": identity,
        "room": room,
    }


class NoKeyError(Exception):
    """The request carried no Gemini key; the client must supply one."""


class BadRequestError(Exception):
    """The request is missing a required field (e.g. client_id)."""


def token_for_client(
    settings: Settings, *, client_id: str, key: str, thinking: Any = None
) -> dict:
    """Mint a join token for a stateless browser client.

    ``client_id`` (browser-generated, persisted only in the browser) is the
    identity AND the room seed — the room is ``tutor-<client_id>`` so each
    browser gets an isolated room/agent (no cross-billing, no shared session).
    The Gemini ``key`` is embedded in the room metadata for the agent to read on
    join; it is never stored server-side. Raises ``NoKeyError`` /
    ``BadRequestError`` on missing fields.
    """
    client_id = (client_id or "").strip()
    key = (key or "").strip()
    if not client_id:
        raise BadRequestError("client_id is required")
    if not key:
        raise NoKeyError("no_key")
    room = f"tutor-{client_id}"
    metadata: dict = {"user_id": client_id, "key": key}
    if thinking not in (None, ""):
        try:
            metadata["thinking"] = int(thinking)
        except (ValueError, TypeError):
            pass
    return token_response(settings, identity=client_id, room=room, room_metadata=metadata)


# --- HTTP wiring (aiohttp) -------------------------------------------------
def make_app(settings: Settings) -> Any:
    from aiohttp import web

    async def token(request: "web.Request") -> "web.Response":
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "bad_json"}, status=400)
        if not isinstance(body, dict):
            return web.json_response({"error": "bad_request"}, status=400)
        try:
            out = token_for_client(
                settings,
                client_id=body.get("client_id", ""),
                key=body.get("key", ""),
                thinking=body.get("thinking"),
            )
        except NoKeyError:
            return web.json_response({"error": "no_key"}, status=400)
        except BadRequestError:
            return web.json_response({"error": "bad_request"}, status=400)
        except ConfigError as e:
            return web.json_response({"error": str(e)}, status=500)
        return web.json_response(out)

    async def healthz(_request: "web.Request") -> "web.Response":
        return web.json_response({"status": "ok"})

    async def index(_request: "web.Request") -> "web.Response":
        # FileResponse so the .html suffix yields text/html automatically.
        # no-cache: without it browsers heuristic-cache the HTML (inline JS), so
        # client fixes don't show up until a hard refresh. Forces revalidation.
        resp = web.FileResponse(WEB_DIR / "index.html")
        resp.headers["Cache-Control"] = "no-cache, must-revalidate"
        return resp

    app = web.Application()
    # Order matters: aiohttp matches in registration order, so the explicit API
    # routes are resolved before the catch-all static mount and are never
    # shadowed. web.static rejects ".." traversal and (without follow_symlinks)
    # cannot escape WEB_DIR, so package source stays unreachable.
    app.add_routes(
        [
            web.post("/token", token),
            web.get("/healthz", healthz),
        ]
    )
    # The web client is a Vite build artifact (frontend/dist). It is absent in a
    # bare checkout / CI (no node build), and aiohttp's web.static raises at
    # registration if WEB_DIR does not exist — so only mount it when present.
    # The API still works without a built client. Registered LAST so the static
    # catch-all never shadows the API routes above.
    if WEB_DIR.is_dir():
        app.add_routes(
            [
                web.get("/", index),
                web.static("/", WEB_DIR),  # Vite hashed bundles; mounted LAST
            ]
        )
    return app


def main() -> None:  # pragma: no cover - process entrypoint
    from aiohttp import web

    settings = Settings.from_env()
    web.run_app(make_app(settings), host="0.0.0.0", port=8080)


if __name__ == "__main__":  # pragma: no cover
    main()
