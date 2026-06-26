"""Tests for tutor_agent.llm — factory + scripted mock (spec §4.2, design llm/factory)."""

from livekit.agents import llm
from livekit.plugins import openai

from tutor_agent.config import Settings
from tutor_agent.llm.factory import build_llm
from tutor_agent.llm.mock import MockLLM


def test_factory_returns_mock_when_mock_adapters():
    assert isinstance(build_llm(Settings.from_env({"MOCK_ADAPTERS": "1"})), MockLLM)


def test_factory_builds_openai_llm_against_local_server():
    s = Settings.from_env({"LLM_BASE_URL": "http://localhost:8080/v1"})
    built = build_llm(s)
    assert isinstance(built, openai.LLM)


async def test_mock_llm_streams_scripted_completion():
    script = "<vi>Tốt lắm!</vi> <en>Tell me more.</en>"
    stream = MockLLM(script=script).chat(chat_ctx=llm.ChatContext.empty())
    out = ""
    async for chunk in stream:
        if chunk.delta and chunk.delta.content:
            out += chunk.delta.content
    assert out == script
