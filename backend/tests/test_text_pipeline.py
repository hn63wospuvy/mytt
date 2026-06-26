"""Tests for tutor_agent.text_pipeline — clean LLM text before TTS/display."""

from typing import AsyncIterator, List

from tutor_agent.text_pipeline import clean_for_speech, clean_text_stream


async def _aiter(chunks: List[str]) -> AsyncIterator[str]:
    for c in chunks:
        yield c


def test_clean_for_speech_strips_bilingual_tags_and_markers():
    raw = (
        '<vi>Gần đúng!</vi> <fix wrong="I go" correct="I went"/> '
        '<en>I went there.</en> <vocab en="go" vi="đi"/>'
    )
    assert clean_for_speech(raw) == "Gần đúng! I went there."


def test_clean_for_speech_no_tags_unchanged():
    assert clean_for_speech("plain text") == "plain text"


async def test_clean_text_stream_handles_tags_split_across_chunks():
    # The same tagged text, fragmented mid-tag across chunks.
    chunks = ["<v", "i>Chào</vi> <e", "n>Hello</en>"]
    out = []
    async for piece in clean_text_stream(_aiter(chunks)):
        out.append(piece)
    assert "".join(out) == "Chào Hello"
