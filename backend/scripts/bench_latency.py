#!/usr/bin/env python
"""Component latency probe (spec §15.2) — run on the Mac with model servers up.

Measures the latencies that add up to voice-to-voice: LLM time-to-first-token
and TTS time-to-first-audio-byte (and STT round-trip if a sample wav is given).
Helps tune chunk size / model size / streaming toward ~1–2s (LOCAL).

    python scripts/bench_latency.py --wav sample.wav
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from tutor_agent.config import Settings  # noqa: E402


def time_llm_first_token(s: Settings) -> float:
    t0 = time.perf_counter()
    with httpx.stream(
        "POST",
        f"{s.llm_base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {s.llm_api_key}"},
        json={
            "model": s.llm_model,
            "messages": [{"role": "user", "content": "Say hi in one word."}],
            "stream": True,
            "max_tokens": 8,
        },
        timeout=60,
    ) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line and line.strip() not in ("data: [DONE]", ""):
                return (time.perf_counter() - t0) * 1000
    return float("nan")


def time_tts_first_byte(s: Settings) -> float:
    t0 = time.perf_counter()
    with httpx.stream(
        "POST",
        f"{s.tts_base_url.rstrip('/')}/speech",
        json={"text": "Xin chào, đây là bài kiểm tra độ trễ.", "voice": s.tts_voice},
        timeout=60,
    ) as r:
        r.raise_for_status()
        for chunk in r.iter_bytes():
            if chunk:
                return (time.perf_counter() - t0) * 1000
    return float("nan")


def time_stt(s: Settings, wav: str) -> float:
    t0 = time.perf_counter()
    with open(wav, "rb") as f:
        resp = httpx.post(
            f"{s.stt_base_url.rstrip('/')}/audio/transcriptions",
            files={"file": (os.path.basename(wav), f, "audio/wav")},
            data={"model": s.stt_model, "language": s.stt_lang},
            timeout=60,
        )
    resp.raise_for_status()
    return (time.perf_counter() - t0) * 1000


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", help="optional sample wav for STT round-trip timing")
    args = ap.parse_args()
    s = Settings.from_env()

    def report(name, fn):
        try:
            print(f"{name}: {fn():.0f} ms")
        except Exception as e:  # noqa: BLE001
            print(f"{name}: ERROR {e}")

    if args.wav:
        report("STT round-trip", lambda: time_stt(s, args.wav))
    report("LLM time-to-first-token", lambda: time_llm_first_token(s))
    report("TTS time-to-first-byte", lambda: time_tts_first_byte(s))


if __name__ == "__main__":
    main()
