"""Tests for the dev-only local STT/TTS substitute servers (pure helpers only).

The model/`say` paths run on-device; here we cover the deterministic helpers:
WAV decode+resample and the VN/EN voice picker.
"""

import io
import wave

import numpy as np
from aiohttp.test_utils import TestClient, TestServer

from local_servers import stt_server, tts_server


def _wav(pcm: bytes, *, rate: int, channels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def test_wav_to_float16k_resamples_to_16k_mono_float():
    # 0.5 s of 48 kHz mono int16 → expect ~0.5 s of 16 kHz float32.
    samples = np.zeros(48000 // 2, dtype=np.int16).tobytes()
    out = stt_server.wav_to_float16k(_wav(samples, rate=48000))
    assert out.dtype == np.float32
    assert abs(len(out) - 16000 // 2) <= 2  # 8000 samples, allow resampler rounding


def test_wav_to_float16k_downmixes_stereo():
    frames = 1600
    stereo = np.zeros(frames * 2, dtype=np.int16).tobytes()  # 2 ch interleaved
    out = stt_server.wav_to_float16k(_wav(stereo, rate=16000, channels=2))
    assert abs(len(out) - frames) <= 2  # already 16k → just downmixed to mono


def test_pick_voice_routes_by_language():
    assert tts_server.pick_voice("Let's practice English") == tts_server.EN_VOICE
    assert tts_server.pick_voice("Xin chào, hôm nay thế nào?") == tts_server.VI_VOICE
    # mixed text with VN diacritics is treated as Vietnamese
    assert tts_server.pick_voice("Quá khứ dùng V2 nhé") == tts_server.VI_VOICE


def test_build_say_cmd_separates_text_with_double_dash():
    # "--" must come right before the text so leading-"-" text is positional,
    # not a smuggled say flag (e.g. -o/-f). The output path stays before "--".
    cmd = tts_server.build_say_cmd("/tmp/out.wav", "-o /etc/passwd", "Linh")
    assert cmd[-2:] == ["--", "-o /etc/passwd"]
    assert "-o" in cmd and cmd[cmd.index("-o") + 1] == "/tmp/out.wav"


async def test_speech_rejects_voice_that_smuggles_a_flag():
    client = TestClient(TestServer(_tts_app()))
    await client.start_server()
    try:
        resp = await client.post("/speech", json={"text": "hi", "voice": "-x"})
        assert resp.status == 400
    finally:
        await client.close()


def _tts_app():
    from aiohttp import web

    app = web.Application()
    app.add_routes([web.post("/speech", tts_server.speech)])
    return app
