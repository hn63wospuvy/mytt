"""Tests for the stateless token server — short-lived LiveKit access tokens.

No login, no database: the browser supplies a ``client_id`` + Gemini ``key`` per
connect; the key rides in the room metadata and is never persisted (spec §11).
"""

import json
from pathlib import Path

import jwt
import pytest
from aiohttp.test_utils import TestClient, TestServer

from tutor_agent.config import ConfigError, Settings
from tutor_agent.token_server.server import (
    _DEFAULT_WEB_DIR,
    _resolve_web_dir,
    BadRequestError,
    NoKeyError,
    WEB_DIR,
    make_app,
    mint_access_token,
    token_for_client,
    token_response,
)

_SECRET = "devsecret_0123456789_abcdef_0123456789"
_ENV = {
    "LIVEKIT_API_KEY": "devkey",
    "LIVEKIT_API_SECRET": _SECRET,
    "LIVEKIT_URL": "ws://mac:7880",
}


def _claims(token: str):
    return jwt.decode(
        token, _SECRET, algorithms=["HS256"], options={"verify_aud": False}
    )


def _meta(token: str) -> dict:
    return json.loads(_claims(token)["roomConfig"]["metadata"])


# --- mint_access_token / token_response ------------------------------------


def test_mint_token_carries_identity_and_room_grant():
    token = mint_access_token(
        api_key="devkey", api_secret=_SECRET, identity="dev1", room="r1", ttl_seconds=600
    )
    claims = _claims(token)
    assert claims["sub"] == "dev1"
    assert claims["video"]["room"] == "r1"
    assert claims["video"]["roomJoin"] is True


def test_token_dispatches_the_tutor_agent():
    # Named agent (@server.rtc_session(agent_name="tutor")) needs explicit
    # dispatch — the join token must carry a room-config agent dispatch or the
    # agent never joins the room.
    token = mint_access_token(
        api_key="devkey", api_secret=_SECRET, identity="web", room="tutor", ttl_seconds=600
    )
    claims = _claims(token)
    assert claims["roomConfig"]["agents"] == [{"agentName": "tutor"}]
    # Short empty-timeout: a lingering empty room would otherwise block the
    # next join from re-dispatching the agent (dispatch fires on room creation).
    assert claims["roomConfig"]["emptyTimeout"] == 10


def test_token_response_includes_url_and_metadata():
    s = Settings.from_env(_ENV)
    resp = token_response(s, identity="dev1", room="r1")
    assert resp["url"] == "ws://mac:7880"
    assert resp["identity"] == "dev1"
    assert resp["room"] == "r1"
    assert _claims(resp["token"])["sub"] == "dev1"


def test_token_response_requires_credentials():
    s = Settings.from_env({"LIVEKIT_API_KEY": "", "LIVEKIT_API_SECRET": ""})
    with pytest.raises(ConfigError, match="LIVEKIT_API"):
        token_response(s, identity="dev1", room="r1")


# --- token_for_client: stateless minting -----------------------------------


def test_token_for_client_derives_room_and_embeds_key():
    s = Settings.from_env(_ENV)
    resp = token_for_client(s, client_id="abc123", key="AIza-user", thinking="3")
    assert resp["identity"] == "abc123"
    assert resp["room"] == "tutor-abc123"  # room derived from the client_id
    assert _meta(resp["token"]) == {"user_id": "abc123", "key": "AIza-user", "thinking": 3}


def test_token_for_client_omits_thinking_when_absent():
    s = Settings.from_env(_ENV)
    resp = token_for_client(s, client_id="abc", key="AIza")
    assert _meta(resp["token"]) == {"user_id": "abc", "key": "AIza"}


def test_token_for_client_requires_key():
    s = Settings.from_env(_ENV)
    with pytest.raises(NoKeyError):
        token_for_client(s, client_id="abc", key="   ")


def test_token_for_client_requires_client_id():
    s = Settings.from_env(_ENV)
    with pytest.raises(BadRequestError):
        token_for_client(s, client_id="", key="AIza")


def test_token_for_client_strips_whitespace():
    s = Settings.from_env(_ENV)
    resp = token_for_client(s, client_id="  abc  ", key="  AIza  ")
    assert resp["identity"] == "abc"
    assert _meta(resp["token"]) == {"user_id": "abc", "key": "AIza"}


# --- POST /token route -----------------------------------------------------


async def _client(settings: Settings) -> TestClient:
    client = TestClient(TestServer(make_app(settings)))
    await client.start_server()
    return client


async def test_token_route_mints_with_key_in_metadata():
    client = await _client(Settings.from_env(_ENV))
    try:
        resp = await client.post(
            "/token", json={"client_id": "c1", "key": "AIza", "thinking": "2"}
        )
        assert resp.status == 200
        body = await resp.json()
        assert body["identity"] == "c1"
        assert body["room"] == "tutor-c1"
        assert _meta(body["token"]) == {"user_id": "c1", "key": "AIza", "thinking": 2}
    finally:
        await client.close()


async def test_token_route_400_without_key():
    client = await _client(Settings.from_env(_ENV))
    try:
        resp = await client.post("/token", json={"client_id": "c1", "key": ""})
        assert resp.status == 400
        assert (await resp.json())["error"] == "no_key"
    finally:
        await client.close()


async def test_token_route_400_without_client_id():
    client = await _client(Settings.from_env(_ENV))
    try:
        resp = await client.post("/token", json={"key": "AIza"})
        assert resp.status == 400
        assert (await resp.json())["error"] == "bad_request"
    finally:
        await client.close()


async def test_token_route_400_on_bad_json():
    client = await _client(Settings.from_env(_ENV))
    try:
        resp = await client.post(
            "/token", data="not json", headers={"Content-Type": "application/json"}
        )
        assert resp.status == 400
    finally:
        await client.close()


async def test_no_auth_routes_remain():
    # The stateless server exposes neither the old Google-auth endpoints nor a
    # GET /token. Exact status (404 vs 405) depends on whether the static mount
    # is present, so just assert none of them function (no 2xx).
    client = await _client(Settings.from_env(_ENV))
    try:
        assert (await client.get("/config")).status >= 400
        assert (await client.get("/me")).status >= 400
        assert (await client.post("/apikey", json={})).status >= 400
        assert (await client.get("/token")).status >= 400  # POST-only resource
    finally:
        await client.close()


# --- static web client serving ---------------------------------------------


def test_web_dir_default_is_repo_frontend_dist():
    repo_root = Path(__file__).resolve().parents[2]
    assert _DEFAULT_WEB_DIR == repo_root / "frontend" / "dist"
    assert _resolve_web_dir(None, _DEFAULT_WEB_DIR) == _DEFAULT_WEB_DIR
    assert _resolve_web_dir("", _DEFAULT_WEB_DIR) == _DEFAULT_WEB_DIR  # empty → default


def test_web_dir_honours_env_override():
    assert _resolve_web_dir("/app/frontend/dist", _DEFAULT_WEB_DIR) == Path(
        "/app/frontend/dist"
    )


# The web client is a Vite build artifact (frontend/dist), absent in a bare
# checkout / CI with no node build. Skip the serving tests when it's missing so
# the backend suite never requires a node build.
_no_web_build = pytest.mark.skipif(
    not (WEB_DIR / "index.html").is_file(),
    reason="no built web client (WEB_DIR/index.html absent — run `npm run build` in frontend/)",
)


@_no_web_build
async def test_root_serves_index_html():
    client = await _client(Settings.from_env(_ENV))
    try:
        resp = await client.get("/")
        assert resp.status == 200
        assert resp.content_type == "text/html"
        assert 'id="root"' in (await resp.text())
    finally:
        await client.close()


@_no_web_build
async def test_static_serves_files_under_web_dir():
    client = await _client(Settings.from_env(_ENV))
    try:
        resp = await client.get("/index.html")  # served by the static mount
        assert resp.status == 200
    finally:
        await client.close()


async def test_healthz_still_ok_after_static_mount():
    client = await _client(Settings.from_env(_ENV))
    try:
        resp = await client.get("/healthz")
        assert resp.status == 200
        assert (await resp.json())["status"] == "ok"
    finally:
        await client.close()


async def test_traversal_outside_web_dir_is_not_served():
    client = await _client(Settings.from_env(_ENV))
    try:
        resp = await client.get("/../config.py")
        assert resp.status != 200  # must not leak package source
    finally:
        await client.close()
