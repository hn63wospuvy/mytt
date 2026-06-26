"""Local STT substitute — real speech recognition via mlx-whisper (Apple Silicon).

Stands in for the Nemotron model server. Speaks the same OpenAI-compatible
contract the agent's NemotronSTT adapter calls:

    POST /v1/audio/transcriptions   multipart: file=<wav>, language=<code>
        -> {"text": ..., "language": ...}
    GET  /v1/models                 (probe used by start.sh)

This is a dev substitute, not the production model. It decodes the incoming WAV
itself (resample to 16 kHz) so no ffmpeg is needed, then runs Whisper on the
Metal GPU. Language is auto-detected by default (best for a bilingual VN/EN
tutor where the student switches languages); set WHISPER_LANG to force one.

    python -m local_servers.stt_server      # :8000, model = $WHISPER_MODEL
"""

from __future__ import annotations

import asyncio
import audioop
import io
import os
import wave

import numpy as np
from aiohttp import web

MODEL = os.environ.get("WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo")
FORCE_LANG = os.environ.get("WHISPER_LANG", "").strip() or None
WHISPER_RATE = 16000


def wav_to_float16k(wav_bytes: bytes) -> np.ndarray:
    """Decode a WAV blob to mono float32 @ 16 kHz (Whisper's input rate)."""
    with wave.open(io.BytesIO(wav_bytes), "rb") as w:
        channels = w.getnchannels()
        rate = w.getframerate()
        width = w.getsampwidth()
        pcm = w.readframes(w.getnframes())
    if width != 2:  # normalise to 16-bit
        pcm = audioop.lin2lin(pcm, width, 2)
    if channels == 2:
        pcm = audioop.tomono(pcm, 2, 0.5, 0.5)
    if rate != WHISPER_RATE:
        pcm, _ = audioop.ratecv(pcm, 2, 1, rate, WHISPER_RATE, None)
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0


def transcribe(audio: np.ndarray, language: str | None) -> dict:
    import mlx_whisper  # lazy — heavy import

    return mlx_whisper.transcribe(audio, path_or_hf_repo=MODEL, language=language)


async def transcriptions(request: web.Request) -> web.Response:
    audio_bytes = b""
    req_lang = None
    reader = await request.multipart()
    async for part in reader:
        if part.name == "file":
            audio_bytes = await part.read(decode=False)
        elif part.name == "language":
            req_lang = (await part.text()).strip() or None
    if not audio_bytes:
        return web.json_response({"text": "", "language": req_lang or "en"})

    audio = wav_to_float16k(audio_bytes)
    lang = FORCE_LANG  # default: auto-detect (None) unless forced via env
    result = await asyncio.to_thread(transcribe, audio, lang)
    return web.json_response(
        {
            "text": (result.get("text") or "").strip(),
            "language": result.get("language") or (req_lang or "en"),
        }
    )


async def models(_request: web.Request) -> web.Response:
    return web.json_response({"object": "list", "data": [{"id": MODEL, "object": "model"}]})


async def healthz(_request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def main() -> None:
    # Warm the model (triggers the one-time download) before serving so the
    # first real turn isn't a multi-second stall.
    print(f"▶ STT (mlx-whisper {MODEL}) warming up…", flush=True)
    transcribe(np.zeros(WHISPER_RATE // 10, np.float32), FORCE_LANG)
    print("✅ STT ready on :8000", flush=True)

    app = web.Application(client_max_size=64 * 1024 * 1024)
    app.add_routes(
        [
            web.post("/v1/audio/transcriptions", transcriptions),
            web.get("/v1/models", models),
            web.get("/healthz", healthz),
        ]
    )
    # Local-only: the agent calls this on localhost; no need to expose on the LAN.
    web.run_app(app, host="127.0.0.1", port=8000, print=None)


if __name__ == "__main__":
    main()
