"""Word Error Rate (spec §15.1 — compare Nemotron vs Qwen3-ASR on Vietnamese).

Pure stdlib, unit tested. Tokenization is whitespace after lowercasing and
stripping punctuation — for Vietnamese this is effectively syllable-level WER,
the usual ASR metric.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Tuple

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def normalize(text: str) -> List[str]:
    return _PUNCT.sub(" ", text.lower()).split()


def _edit_distance(ref: List[str], hyp: List[str]) -> int:
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, start=1):
        cur = [i]
        for j, h in enumerate(hyp, start=1):
            cost = 0 if r == h else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return _edit_distance(ref, hyp) / len(ref)


def corpus_wer(pairs: Iterable[Tuple[str, str]]) -> dict:
    """Aggregate WER over (reference, hypothesis) pairs, weighted by ref words."""
    total_words = 0
    total_errors = 0
    for reference, hypothesis in pairs:
        ref, hyp = normalize(reference), normalize(hypothesis)
        total_words += len(ref)
        total_errors += _edit_distance(ref, hyp)
    wer = total_errors / total_words if total_words else 0.0
    return {"wer": wer, "words": total_words, "errors": total_errors}
