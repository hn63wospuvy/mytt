"""Bridge AgentSession events → data-channel UI updates (no persistence).

Kept free of the framework (plain args) so the turn-handling logic is unit
tested; ``agent.py`` adapts the actual event objects to these calls. Nothing is
stored — transcripts and the per-turn mode are published live over the data
channel, and the browser keeps its own history.
"""

from __future__ import annotations

import re
from typing import List, Optional

from .bilingual import derive_mode, parse_segments
from .data_channel import DataChannel
from .extract import extract_corrections, remove_markers

# Vietnamese-specific letters — used to guess the language of an untagged span.
_VI_CHARS = re.compile(r"[ăâđêôơưàáảãạèéẻẽẹìíỉĩịòóỏõọùúủũụỳýỷỹỵ]", re.IGNORECASE)


def guess_lang(text: str) -> str:
    """Best-effort vi/en for an untagged span (cloud realtime emits no tags)."""
    return "vi" if _VI_CHARS.search(text) else "en"


def normalize_lang(code: Optional[str], *, default: str = "vi") -> str:
    """Map a STT/LLM language code to the ``'vi'``/``'en'`` enum."""
    if not code:
        return default
    c = code.lower()
    if c.startswith("en"):
        return "en"
    if c.startswith("vi"):
        return "vi"
    return default


async def on_user_turn(
    dc: DataChannel,
    *,
    transcript: str,
    language: Optional[str],
    ts: int,
    default_lang: str = "vi",
    publish_transcript: bool = True,
) -> None:
    lang = normalize_lang(language, default=default_lang)
    if publish_transcript:
        await dc.send_transcript(lang=lang, text=transcript, speaker="user")


async def on_agent_turn(
    dc: DataChannel,
    *,
    raw_text: str,
    ts: int,
    used_search: bool = False,
    sources: Optional[List[dict]] = None,
    publish_transcript: bool = True,
) -> str:
    """Publish the tutor turn's transcript + derived mode; return the mode."""
    segments = parse_segments(remove_markers(raw_text))
    corrected = bool(extract_corrections(raw_text))
    if publish_transcript:
        for seg in segments:
            # Tagged spans carry vi/en; untagged spans (cloud realtime) are guessed.
            lang = seg.lang if seg.lang in ("vi", "en") else guess_lang(seg.text)
            await dc.send_transcript(lang=lang, text=seg.text, speaker="tutor")
    mode = derive_mode(segments, used_search=used_search, corrected=corrected)
    await dc.send_mode(mode)
    return mode
