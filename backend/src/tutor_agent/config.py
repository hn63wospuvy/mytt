"""Typed configuration loaded from environment variables (spec §13).

Pure stdlib: importing this module pulls in no third-party packages, so the
config unit suite runs with zero network access. Validation fails loud with a
message naming the offending variable.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from typing import Mapping, Optional

PROFILES = ("local", "cloud")
SEARCH_BACKENDS = ("tavily", "brave", "searxng")
WAKEWORD_ENGINES = ("openwakeword", "porcupine")

_TRUTHY = frozenset({"1", "true", "yes", "on"})


class ConfigError(ValueError):
    """Raised when an environment variable is missing or malformed."""


def _as_bool(value: str) -> bool:
    return value.strip().lower() in _TRUTHY


def _as_positive_int(name: str, value: str) -> int:
    try:
        n = int(value)
    except ValueError:
        raise ConfigError(f"{name} must be an integer, got {value!r}")
    if n <= 0:
        raise ConfigError(f"{name} must be a positive integer, got {n}")
    return n


def _as_int(value: str, *, default: int = 0) -> int:
    try:
        return int(value)
    except ValueError:
        return default


def _one_of(name: str, value: str, choices: tuple[str, ...]) -> str:
    if value not in choices:
        raise ConfigError(
            f"{name} must be one of {', '.join(choices)}; got {value!r}"
        )
    return value


@dataclass(frozen=True)
class Settings:
    """All §13 variables, parsed and validated."""

    profile: str = "local"

    # LiveKit transport
    livekit_url: str = "ws://localhost:7880"
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    # STT (Nemotron 3.5 ASR)
    stt_model: str = "nvidia/nemotron-3.5-asr-streaming-0.6b"
    stt_lang: str = "vi"
    stt_chunk_ms: int = 160
    stt_base_url: str = "http://localhost:8000/v1"

    # LLM (Qwen3-8B, OpenAI-compatible). Port 8082 — 8080 is the token server.
    llm_model: str = "mlx-community/Qwen3-8B-4bit"
    llm_max_tokens: int = 256
    llm_base_url: str = "http://localhost:8082/v1"
    llm_api_key: str = "local"

    # TTS (VieNeu-TTS-v2)
    tts_model: str = "pnnbao-ump/VieNeu-TTS"
    tts_voice: str = ""
    tts_base_url: str = "http://localhost:8001"

    # Web search (local profile)
    search_backend: str = "tavily"
    search_api_key: str = ""
    searxng_url: str = "http://localhost:8888"

    # Wake word (Phase 2)
    wakeword_engine: str = "openwakeword"
    wakeword_phrase: str = "hey tutor"

    # Cloud (Phase 3)
    gemini_api_key: str = ""
    gemini_live_model: str = ""
    # Language for Gemini Live. Empty = let the native-audio model stay
    # multilingual (best for VN/EN code-switch); the native-audio models reject
    # bare "vi", so do NOT default to stt_lang here.
    gemini_language: str = ""
    # "Thinking" budget for Gemini Live. 0 = disabled (lowest latency); a positive
    # number = tokens it may reason before replying; -1 = leave the model default.
    # Adjustable per session from the UI (token → room metadata → override).
    gemini_thinking_budget: int = 1

    # Learning session
    level: str = "B1"

    # When true, agent uses deterministic mock STT/LLM/TTS/search adapters so
    # the loop runs without model servers or downloads. The per-component flags
    # default to this, and can be overridden individually (e.g. real LLM + mock
    # STT/TTS) via MOCK_STT / MOCK_LLM / MOCK_TTS / MOCK_SEARCH.
    use_mock_adapters: bool = False
    use_mock_stt: bool = False
    use_mock_llm: bool = False
    use_mock_tts: bool = False
    use_mock_search: bool = False

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "Settings":
        e = os.environ if env is None else env

        def get(key: str, default: str) -> str:
            return e.get(key, default)

        mock_all = _as_bool(get("MOCK_ADAPTERS", ""))

        def mock_flag(key: str) -> bool:
            # Per-component override, defaulting to the global MOCK_ADAPTERS.
            return _as_bool(e[key]) if key in e else mock_all

        return cls(
            profile=_one_of("PROFILE", get("PROFILE", "local"), PROFILES),
            livekit_url=get("LIVEKIT_URL", "ws://localhost:7880"),
            livekit_api_key=get("LIVEKIT_API_KEY", ""),
            livekit_api_secret=get("LIVEKIT_API_SECRET", ""),
            stt_model=get("STT_MODEL", "nvidia/nemotron-3.5-asr-streaming-0.6b"),
            stt_lang=get("STT_LANG", "vi"),
            stt_chunk_ms=_as_positive_int("STT_CHUNK_MS", get("STT_CHUNK_MS", "160")),
            stt_base_url=get("STT_BASE_URL", "http://localhost:8000/v1"),
            llm_model=get("LLM_MODEL", "mlx-community/Qwen3-8B-4bit"),
            llm_max_tokens=_as_positive_int(
                "LLM_MAX_TOKENS", get("LLM_MAX_TOKENS", "256")
            ),
            llm_base_url=get("LLM_BASE_URL", "http://localhost:8082/v1"),
            llm_api_key=get("LLM_API_KEY", "local"),
            tts_model=get("TTS_MODEL", "pnnbao-ump/VieNeu-TTS"),
            tts_voice=get("TTS_VOICE", ""),
            tts_base_url=get("TTS_BASE_URL", "http://localhost:8001"),
            search_backend=_one_of(
                "SEARCH_BACKEND", get("SEARCH_BACKEND", "tavily"), SEARCH_BACKENDS
            ),
            search_api_key=get("SEARCH_API_KEY", ""),
            searxng_url=get("SEARXNG_URL", "http://localhost:8888"),
            wakeword_engine=_one_of(
                "WAKEWORD_ENGINE", get("WAKEWORD_ENGINE", "openwakeword"),
                WAKEWORD_ENGINES,
            ),
            wakeword_phrase=get("WAKEWORD_PHRASE", "hey tutor"),
            gemini_api_key=get("GEMINI_API_KEY", ""),
            gemini_live_model=get("GEMINI_LIVE_MODEL", ""),
            gemini_language=get("GEMINI_LANGUAGE", ""),
            gemini_thinking_budget=_as_int(get("GEMINI_THINKING_BUDGET", "1")),
            level=get("LEVEL", "B1"),
            use_mock_adapters=mock_all,
            use_mock_stt=mock_flag("MOCK_STT"),
            use_mock_llm=mock_flag("MOCK_LLM"),
            use_mock_tts=mock_flag("MOCK_TTS"),
            use_mock_search=mock_flag("MOCK_SEARCH"),
        )


def apply_session_overrides(settings: "Settings", metadata: Optional[str]) -> "Settings":
    """Override per-session settings from room metadata (JSON the token server
    embeds from the client UI). Currently: ``{"thinking": <int>}`` →
    ``gemini_thinking_budget``. Unknown/invalid metadata is ignored."""
    if not metadata:
        return settings
    try:
        data = json.loads(metadata)
    except (ValueError, TypeError):
        return settings
    if not isinstance(data, dict):
        return settings
    changes: dict = {}
    if "thinking" in data:
        try:
            changes["gemini_thinking_budget"] = int(data["thinking"])
        except (ValueError, TypeError):
            pass
    return replace(settings, **changes) if changes else settings


def user_id_from_metadata(metadata: Optional[str]) -> Optional[str]:
    """Extract ``user_id`` from room-metadata JSON (pure; None if absent/invalid)."""
    if not metadata:
        return None
    try:
        data = json.loads(metadata)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    uid = data.get("user_id")
    return uid if isinstance(uid, str) and uid else None


def gemini_key_from_metadata(metadata: Optional[str]) -> Optional[str]:
    """Extract the per-session Gemini key from room-metadata JSON.

    The stateless cloud path carries the user's key in the LiveKit join-token
    room metadata (the browser sends it per connect; nothing is stored
    server-side). Pure; returns None if absent/blank/invalid."""
    if not metadata:
        return None
    try:
        data = json.loads(metadata)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    key = data.get("key")
    return key if isinstance(key, str) and key else None
