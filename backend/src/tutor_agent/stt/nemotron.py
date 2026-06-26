"""Nemotron 3.5 ASR adapter over an OpenAI-compatible transcription endpoint.

Spec §4.1/§4.2: the STT server speaks the OpenAI ``/v1/audio/transcriptions``
contract (port 8000). This implements a non-streaming :class:`stt.STT`; wrap it
with :class:`stt.StreamAdapter` + Silero VAD (see :func:`make_streaming_stt`)
for the endpointing the live loop needs.

The pure helpers (``parse_transcription``, ``build_speech_event``) are unit
tested; the HTTP shell is exercised on-device with the model server running.
"""

from __future__ import annotations

from typing import Tuple

from livekit import rtc
from livekit.agents import (
    DEFAULT_API_CONNECT_OPTIONS,
    APIConnectOptions,
    stt,
    utils,
)


def parse_transcription(payload: dict, *, default_language: str = "en") -> Tuple[str, str]:
    """Pull ``(text, language)`` from an OpenAI-compatible transcription response."""
    text = (payload.get("text") or "").strip()
    language = payload.get("language") or default_language
    return text, language


def build_speech_event(text: str, language: str, *, request_id: str = "") -> stt.SpeechEvent:
    """Wrap a final transcript in a FINAL_TRANSCRIPT :class:`stt.SpeechEvent`."""
    return stt.SpeechEvent(
        type=stt.SpeechEventType.FINAL_TRANSCRIPT,
        request_id=request_id,
        alternatives=[stt.SpeechData(language=language, text=text)],
    )


class NemotronSTT(stt.STT):
    """Non-streaming STT calling the Nemotron OpenAI-compatible endpoint."""

    def __init__(self, *, base_url: str, model: str, language: str = "vi", api_key: str = "local"):
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=False, interim_results=False)
        )
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._language = language
        self._api_key = api_key

    async def _recognize_impl(
        self,
        buffer: "utils.AudioBuffer",
        *,
        language=None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> stt.SpeechEvent:
        import httpx  # lazy

        wav = rtc.combine_audio_frames(buffer).to_wav_bytes()
        async with httpx.AsyncClient(timeout=conn_options.timeout) as client:
            resp = await client.post(
                f"{self._base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                files={"file": ("audio.wav", wav, "audio/wav")},
                data={"model": self._model, "language": language or self._language},
            )
            resp.raise_for_status()
            text, lang = parse_transcription(resp.json(), default_language=self._language)
        return build_speech_event(text, lang, request_id=resp.headers.get("x-request-id", ""))


def make_streaming_stt(base: stt.STT, vad) -> stt.STT:
    """Give a non-streaming STT endpointing via VAD-driven buffering (spec §6)."""
    return stt.StreamAdapter(stt=base, vad=vad)
