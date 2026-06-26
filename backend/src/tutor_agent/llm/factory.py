"""Pick an LLM from Settings: local Qwen3-8B (OpenAI-compatible) or mock."""

from __future__ import annotations

from livekit.agents import llm
from livekit.plugins import openai

from ..config import Settings
from .mock import MockLLM


def build_llm(settings: Settings) -> llm.LLM:
    if settings.use_mock_llm:
        return MockLLM()
    return openai.LLM(
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        max_completion_tokens=settings.llm_max_tokens,
    )
