"""End-to-end smoke test of the backend with mock adapters (no models, no room).

Drives a full agent turn through the real Tutor agent + MockLLM via the
framework's text-mode ``run()`` harness, then feeds the captured raw assistant
text through the real wiring and asserts the data channel is populated correctly.
This is the design's "loop runs with mock adapters" guarantee, exercised in CI.
Nothing is persisted — the agent is stateless.
"""

import json

from livekit.agents import AgentSession

from tutor_agent.data_channel import DataChannel
from tutor_agent.llm.mock import MockLLM
from tutor_agent.search.mock import MockSearch
from tutor_agent.tutor import Tutor
from tutor_agent.wiring import on_agent_turn, on_user_turn


class _FakeParticipant:
    def __init__(self):
        self.sent = []

    async def publish_data(self, payload, *, reliable=True, topic=None):
        self.sent.append(json.loads(payload.decode("utf-8")))


def _assistant_text(result) -> str:
    for ev in result.events:
        item = getattr(ev, "item", None)
        if item is not None and getattr(item, "role", None) == "assistant":
            return getattr(item, "text_content", "") or ""
    return ""


async def test_full_mock_turn_publishes_transcript_and_mode():
    user_text = "I go to Da Nang yesterday"

    session = AgentSession(llm=MockLLM())
    async with session:
        await session.start(agent=Tutor(search_backend=MockSearch(), level="B1"))
        result = await session.run(user_input=user_text)

    raw = _assistant_text(result)
    # The stored assistant item keeps the raw markup the wiring parses.
    assert "<fix" in raw and "<vocab" in raw and "<vi>" in raw

    lp = _FakeParticipant()
    dc = DataChannel(lp)
    await on_user_turn(dc, transcript=user_text, language="en", ts=10)
    mode = await on_agent_turn(dc, raw_text=raw, ts=20)

    transcripts = [m for m in lp.sent if m["type"] == "transcript"]
    speakers = {t["speaker"] for t in transcripts}
    assert "user" in speakers and "tutor" in speakers

    assert mode == "giang"  # a correction was issued this turn
    assert {"type": "mode", "value": "giang"} in lp.sent
