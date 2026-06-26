"""Profile-aware session assembly (spec §2/§3 hybrid).

LOCAL (Mac): Nemotron STT + Qwen3 LLM + VieNeu TTS + self-assembled web_search.
CLOUD (Phase 3): Gemini Live as one realtime block (STT+LLM+TTS) with Google
Search grounding built in — so no separate stt/tts and no web_search tool.

The agent code is shared; only the model tier and transport differ (spec §2
"đổi profile = đổi model + endpoint, không đổi app").
"""

from __future__ import annotations

from livekit.agents import AgentSession, TurnHandlingOptions
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from .config import ConfigError, Settings
from .llm.factory import build_llm
from .search.factory import build_search
from .stt.factory import build_stt
from .tts.factory import build_tts
from .tutor import Tutor


def uses_realtime(settings: Settings) -> bool:
    """Cloud profile uses a single realtime model (Gemini Live)."""
    return settings.profile == "cloud"


def build_realtime_model(settings: Settings):
    """Gemini Live realtime model for the CLOUD profile (spec §5)."""
    if not settings.gemini_api_key:
        raise ConfigError("GEMINI_API_KEY is required for PROFILE=cloud")
    from livekit.plugins.google.realtime import RealtimeModel

    return RealtimeModel(**realtime_kwargs(settings))


def realtime_kwargs(settings: Settings) -> dict:
    """RealtimeModel kwargs, tuned for a snappy tutor.

    ``language`` is passed only when explicitly configured (native-audio models
    reject bare ``vi`` and are multilingual by default). Thinking is disabled by
    default for lower latency, and audio transcription is enabled both ways so
    the on-screen text tracks the spoken audio."""
    from google.genai import types as gt

    kwargs = {"api_key": settings.gemini_api_key}
    if settings.gemini_live_model:
        kwargs["model"] = settings.gemini_live_model
    if settings.gemini_language:
        kwargs["language"] = settings.gemini_language
    if settings.gemini_thinking_budget >= 0:
        kwargs["thinking_config"] = gt.ThinkingConfig(
            thinking_budget=settings.gemini_thinking_budget
        )
    kwargs["input_audio_transcription"] = gt.AudioTranscriptionConfig()
    kwargs["output_audio_transcription"] = gt.AudioTranscriptionConfig()
    return kwargs


def build_tutor(settings: Settings, *, on_search=None) -> Tutor:
    """The Tutor agent; cloud relies on built-in grounding (no web_search tool).

    ``on_search`` (LOCAL only) lets the caller capture each web_search for QA
    logging (spec §12)."""
    if uses_realtime(settings):
        return Tutor(level=settings.level, enable_web_search=False, tagged=False)
    return Tutor(
        search_backend=build_search(settings), level=settings.level, on_search=on_search
    )


def build_session(settings: Settings, *, vad=None) -> AgentSession:
    """Assemble the AgentSession for the active profile."""
    if uses_realtime(settings):
        # One realtime block handles STT+LLM+TTS + barge-in + grounding.
        return AgentSession(llm=build_realtime_model(settings))
    return AgentSession(
        stt=build_stt(settings, vad=vad),
        llm=build_llm(settings),
        tts=build_tts(settings),
        vad=vad,
        turn_handling=TurnHandlingOptions(turn_detection=MultilingualModel()),
    )
