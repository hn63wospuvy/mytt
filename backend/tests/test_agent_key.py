"""Cloud agent reads the per-session Gemini key from room metadata (stateless).

No database, no decryption: the browser embeds the key in the LiveKit room
metadata per connect; ``resolve_settings_for_room`` lifts it out.
"""

import json


def test_resolve_sets_gemini_key_for_cloud():
    from tutor_agent.agent import resolve_settings_for_room
    from tutor_agent.config import Settings

    s = Settings.from_env({"PROFILE": "cloud", "GEMINI_LIVE_MODEL": "m"})
    meta = json.dumps({"user_id": "c1", "key": "AIza-user"})
    out, uid = resolve_settings_for_room(s, meta)
    assert uid == "c1"
    assert out.gemini_api_key == "AIza-user"


def test_resolve_returns_empty_key_when_metadata_has_none():
    from tutor_agent.agent import resolve_settings_for_room
    from tutor_agent.config import Settings

    s = Settings.from_env({"PROFILE": "cloud"})
    out, uid = resolve_settings_for_room(s, json.dumps({"user_id": "c1"}))
    assert uid == "c1"
    assert out.gemini_api_key == ""  # nothing in metadata → caller must reject


def test_resolve_applies_thinking_override_from_metadata():
    from tutor_agent.agent import resolve_settings_for_room
    from tutor_agent.config import Settings

    s = Settings.from_env({"PROFILE": "cloud"})
    meta = json.dumps({"user_id": "c1", "key": "AIza", "thinking": 5})
    out, _ = resolve_settings_for_room(s, meta)
    assert out.gemini_thinking_budget == 5


def test_resolve_local_profile_keeps_env_key_and_ignores_metadata_key():
    from tutor_agent.agent import resolve_settings_for_room
    from tutor_agent.config import Settings

    s = Settings.from_env({"PROFILE": "local", "GEMINI_API_KEY": "env-key"})
    # A key in metadata must NOT override the local env key (local doesn't use it).
    out, uid = resolve_settings_for_room(s, json.dumps({"key": "AIza"}))
    assert out.gemini_api_key == "env-key"
    assert uid is None
