"""Tests for tutor_agent.wiring — event → data-channel publish (no persistence)."""

import json

import pytest

from tutor_agent.bilingual import GIANG
from tutor_agent.data_channel import DataChannel
from tutor_agent.wiring import normalize_lang, on_agent_turn, on_user_turn


class _FakeParticipant:
    def __init__(self):
        self.sent = []

    async def publish_data(self, payload, *, reliable=True, topic=None):
        self.sent.append(json.loads(payload.decode("utf-8")))


@pytest.fixture
def ctx():
    lp = _FakeParticipant()
    return DataChannel(lp), lp


def test_normalize_lang():
    assert normalize_lang("vi") == "vi"
    assert normalize_lang("en-US") == "en"
    assert normalize_lang(None, default="vi") == "vi"
    assert normalize_lang("fr", default="en") == "en"


async def test_on_user_turn_publishes(ctx):
    dc, lp = ctx
    await on_user_turn(dc, transcript="I go yesterday", language="en", ts=10)
    assert lp.sent[0] == {
        "type": "transcript",
        "lang": "en",
        "text": "I go yesterday",
        "speaker": "user",
    }


async def test_on_agent_turn_publishes_per_segment_and_mode(ctx):
    dc, lp = ctx
    raw = (
        "<vi>Sai thì rồi.</vi> "
        '<fix wrong="I go" correct="I went"/> '
        "<en>I went there.</en>"
    )
    mode = await on_agent_turn(dc, raw_text=raw, ts=20)

    transcripts = [m for m in lp.sent if m["type"] == "transcript"]
    assert [(t["lang"], t["speaker"]) for t in transcripts] == [
        ("vi", "tutor"),
        ("en", "tutor"),
    ]
    modes = [m for m in lp.sent if m["type"] == "mode"]
    assert modes == [{"type": "mode", "value": GIANG}]
    assert mode == GIANG  # a correction this turn → GIẢNG


async def test_publish_transcript_false_skips_data_channel_but_sends_mode(ctx):
    # Cloud streams transcripts natively → agent passes publish_transcript=False;
    # the line must NOT go on our data channel, but the mode badge still does.
    dc, lp = ctx
    await on_user_turn(dc, transcript="hello", language="en", ts=10, publish_transcript=False)
    await on_agent_turn(dc, raw_text="<vi>Chào</vi>", ts=20, publish_transcript=False)
    assert not [m for m in lp.sent if m["type"] == "transcript"]  # none published
    assert [m["type"] for m in lp.sent if m["type"] == "mode"]    # mode still sent


async def test_on_agent_turn_guesses_lang_for_untagged_cloud_text(ctx):
    # Gemini Live (cloud) emits no <vi>/<en> tags — the span lang must be guessed
    # so the tutor line still renders (regression: was dropped when lang=None).
    dc, lp = ctx
    await on_agent_turn(dc, raw_text="Hi there! Ready to practice English?", ts=20)
    await on_agent_turn(dc, raw_text="Chào bạn, hôm nay học gì nào?", ts=21)
    transcripts = [m for m in lp.sent if m["type"] == "transcript"]
    assert (transcripts[0]["lang"], transcripts[0]["speaker"]) == ("en", "tutor")
    assert (transcripts[1]["lang"], transcripts[1]["speaker"]) == ("vi", "tutor")
