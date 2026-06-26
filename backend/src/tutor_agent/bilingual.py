"""Bilingual inline-tag handling (spec §7.1).

The LLM is instructed to wrap every span in ``<vi>…</vi>`` or ``<en>…</en>``.
This module turns that tagged string into:

  * ``parse_segments`` — ordered segments for transcript display / TTS routing,
  * ``strip_tags`` — plain spoken text for the TTS engine,
  * ``derive_mode`` — the active tutor mode for the data channel (spec §7.2).

Pure stdlib, fully unit-tested. Robust to a model that emits untagged text or
leaves a trailing tag unclosed (lang ``None`` for unknown spans).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

# Mode values pushed over the data channel ({type:"mode", value}); the app maps
# these to the chips Giảng / Luyện / Hỏi-đáp.
GIANG = "giang"
LUYEN = "luyen"
HOI_DAP = "hoi_dap"

_TAG = re.compile(r"<(vi|en)>(.*?)</\1>", re.DOTALL)
# A tag that opens but is never closed before end-of-string.
_UNCLOSED = re.compile(r"<(vi|en)>(.*)$", re.DOTALL)


@dataclass(frozen=True)
class Segment:
    """One contiguous span of text. ``lang`` is ``"vi"``, ``"en"`` or ``None``."""

    lang: Optional[str]
    text: str


def _push(segments: List[Segment], lang: Optional[str], text: str) -> None:
    text = text.strip()
    if text:
        segments.append(Segment(lang, text))


def parse_segments(raw: str) -> List[Segment]:
    """Split a tagged string into ordered :class:`Segment`s.

    Well-formed ``<vi>``/``<en>`` blocks become tagged segments; non-whitespace
    text between or around them becomes ``lang=None`` segments; a final unclosed
    tag is captured to end-of-string.
    """
    segments: List[Segment] = []
    pos = 0
    for m in _TAG.finditer(raw):
        _push(segments, None, raw[pos : m.start()])
        _push(segments, m.group(1), m.group(2))
        pos = m.end()

    tail = raw[pos:]
    unclosed = _UNCLOSED.search(tail)
    if unclosed:
        _push(segments, None, tail[: unclosed.start()])
        _push(segments, unclosed.group(1), unclosed.group(2))
    else:
        _push(segments, None, tail)
    return segments


def strip_tags(raw: str) -> str:
    """Plain spoken text: segment texts joined by single spaces, no tags."""
    return " ".join(seg.text for seg in parse_segments(raw))


def derive_mode(
    segments: List[Segment], used_search: bool = False, corrected: bool = False
) -> str:
    """Active tutor mode for the data channel (spec §7.2).

    Priority: ``used_search`` (a web_search ran this turn) → HỎI-ĐÁP; else a
    correction this turn → GIẢNG (correcting is teaching, regardless of how long
    the English example is); else weigh Vietnamese vs English by character count:
    VI-dominant → GIẢNG, else LUYỆN (the default, incl. the empty/tie case).
    """
    if used_search:
        return HOI_DAP
    if corrected:
        return GIANG

    vi = sum(len(s.text) for s in segments if s.lang == "vi")
    en = sum(len(s.text) for s in segments if s.lang == "en")
    return GIANG if vi > en else LUYEN
