"""Local TTS substitute — real speech via the macOS ``say`` engine.

Stands in for the VieNeu model server. Speaks the contract the agent's
VieNeuTTS adapter calls:

    POST /speech   {"text": ..., "voice": ...}
        -> raw PCM16 mono @ 24 kHz (headerless, streamed)

This is a dev substitute, not the production VN voice. ``say`` writes a WAV at
exactly LEI16@24000; we strip the header and return the raw frames. The voice is
chosen per request: Vietnamese text (diacritics) -> a vi_VN voice, otherwise the
default English voice — a single voice can't do both well. Override the picks
with TTS_VI_VOICE / TTS_EN_VOICE.

    python -m local_servers.tts_server       # :8001
"""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import tempfile
import wave

from aiohttp import web

VI_VOICE = os.environ.get("TTS_VI_VOICE", "Linh")  # vi_VN voice (present on this Mac)
EN_VOICE = os.environ.get("TTS_EN_VOICE", "")       # "" = system default English voice
TTS_RATE = 24000

# Vietnamese-specific lowercase letters — a cheap "is this Vietnamese?" test.
_VI_CHARS = re.compile(r"[ăâđêôơưàáảãạèéẻẽẹìíỉĩịòóỏõọùúủũụỳýỷỹỵ]", re.IGNORECASE)


def pick_voice(text: str) -> str:
    return VI_VOICE if _VI_CHARS.search(text) else EN_VOICE


def build_say_cmd(path: str, text: str, voice: str) -> list[str]:
    """Argv for ``say``. ``--`` keeps text that begins with ``-`` positional, so
    it can't smuggle a say flag (e.g. -o/-f file write/read). No shell is used."""
    cmd = ["say"]
    if voice:
        cmd += ["-v", voice]
    cmd += ["--file-format=WAVE", "--data-format=LEI16@24000", "-o", path, "--", text]
    return cmd


def synth_pcm(text: str, voice: str) -> bytes:
    """Run ``say`` to a WAV, return raw PCM16 mono @ 24 kHz (no header)."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    try:
        subprocess.run(build_say_cmd(path, text, voice), check=True, capture_output=True)
        with wave.open(path, "rb") as w:
            channels = w.getnchannels()
            pcm = w.readframes(w.getnframes())
        if channels == 2:  # say is normally mono, but be safe
            import audioop

            pcm = audioop.tomono(pcm, 2, 0.5, 0.5)
        return pcm
    finally:
        os.unlink(path)


async def speech(request: web.Request) -> web.StreamResponse:
    body = await request.json()
    text = (body.get("text") or "").strip()
    req_voice = (body.get("voice") or "").strip()
    if req_voice.startswith("-"):  # don't let a voice value smuggle a say flag
        raise web.HTTPBadRequest(reason="invalid voice")
    resp = web.StreamResponse(headers={"Content-Type": "application/octet-stream"})
    await resp.prepare(request)
    if text:
        voice = req_voice or pick_voice(text)
        pcm = await asyncio.to_thread(synth_pcm, text, voice)
        await resp.write(pcm)
    await resp.write_eof()
    return resp


async def healthz(_request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def main() -> None:
    print("✅ TTS (macOS say) ready on :8001", flush=True)
    app = web.Application()
    app.add_routes([web.post("/speech", speech), web.get("/healthz", healthz)])
    # Local-only: the agent calls this on localhost; no need to expose on the LAN.
    web.run_app(app, host="127.0.0.1", port=8001, print=None)


if __name__ == "__main__":
    main()
