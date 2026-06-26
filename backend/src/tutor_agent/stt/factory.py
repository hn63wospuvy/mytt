"""Pick the STT adapter from Settings; wrap with VAD endpointing when a VAD given."""

from __future__ import annotations

from livekit.agents import stt

from ..config import Settings
from .mock import MockSTT
from .nemotron import NemotronSTT, make_streaming_stt


def build_stt(settings: Settings, *, vad=None) -> stt.STT:
    if settings.use_mock_stt:
        base: stt.STT = MockSTT(language=settings.stt_lang)
    else:
        base = NemotronSTT(
            base_url=settings.stt_base_url,
            model=settings.stt_model,
            language=settings.stt_lang,
        )
    return make_streaming_stt(base, vad) if vad is not None else base
