"""Deterministic mock TTS — emits silence so the loop runs with no model server."""

from __future__ import annotations

from livekit.agents import (
    DEFAULT_API_CONNECT_OPTIONS,
    APIConnectOptions,
    tts,
    utils,
)

SAMPLE_RATE = 24000
NUM_CHANNELS = 1


def pcm16_silence(*, duration_ms: int, sample_rate: int, num_channels: int = 1) -> bytes:
    """Raw PCM16 silence: ``sample_rate * duration_ms/1000`` samples per channel."""
    samples = int(sample_rate * duration_ms / 1000)
    return b"\x00\x00" * samples * num_channels


class MockTTS(tts.TTS):
    def __init__(self, *, duration_ms: int = 300):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
        )
        self._duration_ms = duration_ms

    def synthesize(
        self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> "tts.ChunkedStream":
        return _MockStream(tts=self, input_text=text, conn_options=conn_options)


class _MockStream(tts.ChunkedStream):
    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        engine: MockTTS = self._tts  # type: ignore[assignment]
        output_emitter.initialize(
            request_id=utils.shortuuid(),
            sample_rate=engine.sample_rate,
            num_channels=engine.num_channels,
            mime_type="audio/pcm",
        )
        output_emitter.push(
            pcm16_silence(
                duration_ms=engine._duration_ms,
                sample_rate=engine.sample_rate,
                num_channels=engine.num_channels,
            )
        )
        output_emitter.flush()
