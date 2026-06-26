"""Scripted mock LLM — streams a fixed bilingual reply with no model server.

The default script carries both ``<vi>`` and ``<en>`` spans plus a structured
``<fix>``/``<vocab>`` marker, so the full pipeline (bilingual split → TTS,
correction/vocab extraction) is exercised end-to-end against the mock.
"""

from __future__ import annotations

from livekit.agents import (
    DEFAULT_API_CONNECT_OPTIONS,
    APIConnectOptions,
    llm,
)

_DEFAULT_SCRIPT = (
    "<vi>Gần đúng rồi! Quá khứ dùng V2.</vi> "
    '<fix wrong="I go to Da Nang yesterday" correct="I went to Da Nang yesterday"/> '
    "<en>I went to Da Nang yesterday. Tell me more.</en> "
    '<vocab en="yesterday" vi="hôm qua"/>'
)


class MockLLM(llm.LLM):
    def __init__(self, *, script: str = _DEFAULT_SCRIPT):
        super().__init__()
        self._script = script

    def chat(
        self,
        *,
        chat_ctx: llm.ChatContext,
        tools=None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        parallel_tool_calls=None,
        tool_choice=None,
        extra_kwargs=None,
    ) -> llm.LLMStream:
        return _MockStream(
            self, chat_ctx=chat_ctx, tools=tools or [], conn_options=conn_options
        )


class _MockStream(llm.LLMStream):
    async def _run(self) -> None:
        engine: MockLLM = self._llm  # type: ignore[assignment]
        self._event_ch.send_nowait(
            llm.ChatChunk(
                id="mock",
                delta=llm.ChoiceDelta(role="assistant", content=engine._script),
            )
        )
