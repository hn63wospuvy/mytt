#!/usr/bin/env python
"""STT WER benchmark (spec §15.1) — run on the Mac with a model server up.

Compares an STT server's transcripts against references over a folder of paired
files: ``<name>.wav`` + ``<name>.txt`` (the reference transcript).

    python scripts/bench_wer.py audio_dir/ --stt-base-url http://localhost:8000/v1

Point ``--stt-base-url`` at Nemotron vs a Qwen3-ASR server to pick the winner.
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from tutor_agent.eval.wer import corpus_wer, word_error_rate  # noqa: E402


def transcribe(base_url: str, wav_path: str, model: str, language: str) -> str:
    with open(wav_path, "rb") as f:
        resp = httpx.post(
            f"{base_url.rstrip('/')}/audio/transcriptions",
            files={"file": (os.path.basename(wav_path), f, "audio/wav")},
            data={"model": model, "language": language},
            timeout=60,
        )
    resp.raise_for_status()
    return (resp.json().get("text") or "").strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("audio_dir")
    ap.add_argument("--stt-base-url", default=os.environ.get("STT_BASE_URL", "http://localhost:8000/v1"))
    ap.add_argument("--model", default=os.environ.get("STT_MODEL", "nvidia/nemotron-3.5-asr-streaming-0.6b"))
    ap.add_argument("--language", default=os.environ.get("STT_LANG", "vi"))
    args = ap.parse_args()

    pairs = []
    for name in sorted(os.listdir(args.audio_dir)):
        if not name.endswith(".wav"):
            continue
        wav = os.path.join(args.audio_dir, name)
        ref_path = wav[:-4] + ".txt"
        if not os.path.exists(ref_path):
            print(f"!! no reference for {name}, skipping")
            continue
        with open(ref_path, encoding="utf-8") as f:
            reference = f.read().strip()
        hypothesis = transcribe(args.stt_base_url, wav, args.model, args.language)
        wer = word_error_rate(reference, hypothesis)
        print(f"{name}: WER={wer:.3f}")
        print(f"   ref: {reference}")
        print(f"   hyp: {hypothesis}")
        pairs.append((reference, hypothesis))

    if pairs:
        agg = corpus_wer(pairs)
        print(f"\nCORPUS WER={agg['wer']:.3f} ({agg['errors']}/{agg['words']} words, {len(pairs)} files)")
    else:
        print("No (.wav,.txt) pairs found.")


if __name__ == "__main__":
    main()
