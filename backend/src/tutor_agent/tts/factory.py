"""Pick the TTS adapter from Settings."""

from __future__ import annotations

from livekit.agents import tts

from ..config import Settings
from .mock import MockTTS
from .vieneu import VieNeuTTS


def build_tts(settings: Settings) -> tts.TTS:
    if settings.use_mock_tts:
        return MockTTS()
    return VieNeuTTS(base_url=settings.tts_base_url, voice=settings.tts_voice)
