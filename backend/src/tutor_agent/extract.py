"""Parse the tutor's structured markers from a turn (pure text, no storage).

Reliable free-text extraction from a Vietnamese explanation is not feasible with
pure rules, so the tutor emits explicit structured markers (see ``tutor.py``
system prompt) that are *not spoken*:

    <fix wrong="..." correct="..." note="..."/>     # note optional
    <vocab en="..." vi="..."/>

This module parses those markers (``extract_corrections`` feeds the GIẢNG/HỎI-ĐÁP
mode derivation) and provides :func:`remove_markers` to strip them before TTS /
bilingual parsing. Pure stdlib, fully unit-tested. Nothing is persisted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

_FIX = re.compile(r"<fix\b([^>]*?)/?>", re.DOTALL)
_VOCAB = re.compile(r"<vocab\b([^>]*?)/?>", re.DOTALL)
_ATTR = re.compile(r'(\w+)\s*=\s*"([^"]*)"')


@dataclass(frozen=True)
class Correction:
    wrong: str
    correct: str
    note_vi: Optional[str] = None


@dataclass(frozen=True)
class VocabItem:
    term_en: str
    meaning_vi: str


def _attrs(blob: str) -> dict:
    return {k: v for k, v in _ATTR.findall(blob)}


def extract_corrections(text: str) -> List[Correction]:
    out: List[Correction] = []
    for m in _FIX.finditer(text):
        a = _attrs(m.group(1))
        if "wrong" in a and "correct" in a:
            out.append(Correction(a["wrong"], a["correct"], a.get("note")))
    return out


def extract_vocab(text: str) -> List[VocabItem]:
    out: List[VocabItem] = []
    for m in _VOCAB.finditer(text):
        a = _attrs(m.group(1))
        if "en" in a:
            out.append(VocabItem(a["en"], a.get("vi", "")))
    return out


def remove_markers(text: str) -> str:
    """Strip ``<fix .../>`` / ``<vocab .../>`` markers, collapsing leftover spaces."""
    text = _FIX.sub("", text)
    text = _VOCAB.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()
