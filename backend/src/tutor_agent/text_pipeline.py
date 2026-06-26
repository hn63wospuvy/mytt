"""Clean LLM output before it reaches TTS / display (spec §7.1).

The model emits ``<vi>``/``<en>`` spans plus unspoken ``<fix>``/``<vocab>``
markers. None of that should be spoken verbatim. :func:`clean_for_speech`
produces the plain spoken text; :func:`clean_text_stream` does the same over a
streamed text source (buffering the turn so tags split across chunks are handled
correctly), for use in an Agent ``tts_node`` override.
"""

from __future__ import annotations

from typing import AsyncIterable, AsyncIterator

from .bilingual import strip_tags
from .extract import remove_markers


def clean_for_speech(text: str) -> str:
    """Strip fix/vocab markers and bilingual tags, leaving plain spoken text."""
    return strip_tags(remove_markers(text))


async def clean_text_stream(stream: AsyncIterable[str]) -> AsyncIterator[str]:
    """Buffer a text stream, then yield the cleaned spoken text once.

    Buffering is required because tags can straddle chunk boundaries. For 1–3
    short sentences (spec §7.3) the added latency is small; per-sentence cleaning
    is a later refinement (spec §15.2).
    """
    buf = []
    async for chunk in stream:
        buf.append(chunk)
    cleaned = clean_for_speech("".join(buf))
    if cleaned:
        yield cleaned
