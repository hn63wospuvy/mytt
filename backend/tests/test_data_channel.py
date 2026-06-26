"""Tests for tutor_agent.data_channel — UI messages over the room (spec §9.4)."""

import json

from tutor_agent.data_channel import (
    DataChannel,
    mode_message,
    profile_message,
    transcript_message,
)


def test_transcript_message_shape():
    assert transcript_message(lang="vi", text="chào", speaker="tutor") == {
        "type": "transcript",
        "lang": "vi",
        "text": "chào",
        "speaker": "tutor",
    }


def test_mode_message_shape():
    assert mode_message("giang") == {"type": "mode", "value": "giang"}


def test_profile_message_shape():
    assert profile_message("local") == {"type": "profile", "value": "local"}


class _FakeParticipant:
    def __init__(self):
        self.sent = []

    async def publish_data(self, payload, *, reliable=True, topic=None):
        self.sent.append((payload, reliable, topic))


async def test_data_channel_publishes_json_bytes():
    lp = _FakeParticipant()
    dc = DataChannel(lp)
    await dc.send_transcript(lang="en", text="hello", speaker="user")
    payload, reliable, topic = lp.sent[0]
    assert json.loads(payload.decode("utf-8")) == {
        "type": "transcript",
        "lang": "en",
        "text": "hello",
        "speaker": "user",
    }
    assert reliable is True


async def test_data_channel_sends_mode_and_profile():
    lp = _FakeParticipant()
    dc = DataChannel(lp)
    await dc.send_mode("hoi_dap")
    await dc.send_profile("local")
    types = [json.loads(p.decode())["type"] for p, _, _ in lp.sent]
    assert types == ["mode", "profile"]


def test_error_message_shape():
    from tutor_agent.data_channel import error_message
    assert error_message("no_key", "need key") == {
        "type": "error", "code": "no_key", "message": "need key"
    }
