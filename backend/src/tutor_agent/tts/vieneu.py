"""VieNeu-TTS-v2 adapter (spec §4.2): Vietnamese TTS with code-switch, 24 kHz.

Posts text to a VieNeu HTTP speech endpoint that returns raw PCM16 mono @ 24 kHz
and streams it out through the framework's :class:`tts.AudioEmitter`. Per-sentence
streaming to hide latency (spec §6) is handled by the agent / SentenceStreamPacer.

``build_vieneu_request`` is unit tested; the HTTP shell runs on-device.
"""

from __future__ import annotations

from livekit.agents import (
    DEFAULT_API_CONNECT_OPTIONS,
    APIConnectOptions,
    tts,
)

SAMPLE_RATE = 24000
NUM_CHANNELS = 1


def build_vieneu_request(text: str, *, voice: str = "") -> dict:
    """JSON body for the VieNeu speech endpoint."""
    return {"text": text, "voice": voice}


class VieNeuTTS(tts.TTS):
    def __init__(self, *, base_url: str, voice: str = ""):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
        )
        self._base_url = base_url.rstrip("/")
        self._voice = voice

    def synthesize(
        self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> "tts.ChunkedStream":
        return _VieNeuStream(tts=self, input_text=text, conn_options=conn_options)


class _VieNeuStream(tts.ChunkedStream):
    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        import httpx  # lazy

        engine: VieNeuTTS = self._tts  # type: ignore[assignment]
        output_emitter.initialize(
            request_id=utils_short_id(),
            sample_rate=engine.sample_rate,
            num_channels=engine.num_channels,
            mime_type="audio/pcm",
        )
        async with httpx.AsyncClient(timeout=self._conn_options.timeout) as client:
            async with client.stream(
                "POST",
                f"{engine._base_url}/speech",
                json=build_vieneu_request(self._input_text, voice=engine._voice),
            ) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes():
                    if chunk:
                        output_emitter.push(chunk)
        output_emitter.flush()


def utils_short_id() -> str:
    from livekit.agents import utils

    return utils.shortuuid()
