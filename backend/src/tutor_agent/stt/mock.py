"""Deterministic mock STT — runs the loop with no model server (design §"testing")."""

from __future__ import annotations

from livekit.agents import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions, stt, utils

from .nemotron import build_speech_event

_CANNED = "I go to Da Nang yesterday"


class MockSTT(stt.STT):
    def __init__(self, *, text: str = _CANNED, language: str = "en"):
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=False, interim_results=False)
        )
        self._text = text
        self._language = language

    async def _recognize_impl(
        self,
        buffer: "utils.AudioBuffer",
        *,
        language=None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> stt.SpeechEvent:
        return build_speech_event(self._text, language or self._language)
