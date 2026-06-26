"""LiveKit agent entrypoint (spec §4.1 step 6, design "agent.py").

Picks the profile from Settings (spec §2/§3 hybrid):
  * LOCAL  — Nemotron STT + Qwen3 LLM + VieNeu TTS pipeline + web_search tool,
             tag-based bilingual transcript.
  * CLOUD  — Gemini Live realtime block (STT+LLM+TTS + Google Search grounding),
             tag-free natural speech; the framework forwards transcripts.

The agent is fully stateless — nothing is persisted. Transcripts and the per-turn
mode are published live over the data channel; the browser keeps its own history.

The framework supplies VAD, endpointing, multilingual turn detection, barge-in
and streaming TTS (spec §6). With ``MOCK_ADAPTERS=1`` the local loop runs with no
model servers.

Run:  ``python -m tutor_agent.agent dev``  (or via ``start.sh``).
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import replace

from livekit import agents
from livekit.agents import AgentServer, room_io
from livekit.plugins import silero

from .config import (
    Settings,
    apply_session_overrides,
    gemini_key_from_metadata,
    user_id_from_metadata,
)
from .data_channel import DataChannel
from .session_factory import build_session, build_tutor, uses_realtime
from .tools import SearchContext
from .wiring import on_agent_turn, on_user_turn

log = logging.getLogger(__name__)

server = AgentServer()


def resolve_settings_for_room(
    settings: Settings, metadata: str | None
) -> tuple[Settings, str | None]:
    """Apply room-metadata overrides and, for cloud, read the per-session key.

    Returns ``(settings, user_id)``. For cloud, ``settings.gemini_api_key`` is the
    key the browser embedded in the room metadata (empty if absent — caller must
    reject); nothing is read from a database. For local, the env key is left
    untouched.
    """
    settings = apply_session_overrides(settings, metadata)
    user_id = user_id_from_metadata(metadata)
    if uses_realtime(settings):
        key = gemini_key_from_metadata(metadata)
        settings = replace(settings, gemini_api_key=key or "")
    return settings, user_id


@server.rtc_session(agent_name="tutor")
async def tutor_session(ctx: agents.JobContext) -> None:
    settings = Settings.from_env()
    cloud = uses_realtime(settings)

    # VAD only needed for the local pipeline (cloud realtime does turn-taking).
    vad = None if cloud else silero.VAD.load()

    # Join the room before touching ctx.room.local_participant (the data
    # channel) or starting the session — local_participant is unavailable until
    # the job has connected.
    await ctx.connect()

    # Apply room-metadata overrides + (cloud) read the per-session Gemini key the
    # browser embedded in the metadata. Done after connect, before building the
    # session (the realtime model bakes in key + thinking budget).
    settings, user_id = resolve_settings_for_room(settings, ctx.room.metadata)

    # local_participant is available only after ctx.connect().
    dc = DataChannel(ctx.room.local_participant)
    if cloud and not settings.gemini_api_key:
        # No usable key in the room metadata (stateless: the browser sends it per
        # connect). Tell the client and stop — don't crash the worker.
        log.info("Cloud client %r joined without a Gemini key", user_id)
        await dc.send_error(
            "no_key", "Bạn cần thêm Gemini API key trước khi bắt đầu."
        )
        return

    session = build_session(settings, vad=vad)

    # Stateless: nothing is persisted. The data channel publishes transcripts +
    # the per-turn mode live; search_ctx only tracks whether a web_search ran
    # this turn (it feeds the GIẢNG/HỎI-ĐÁP mode derivation).
    search_ctx = SearchContext()

    @session.on("user_input_transcribed")
    def _on_user(ev) -> None:
        if not ev.is_final:
            return
        asyncio.create_task(
            on_user_turn(
                dc,
                transcript=ev.transcript,
                language=ev.language,
                ts=int(time.time()),
                default_lang=settings.stt_lang,
                # Cloud streams transcripts natively (word-by-word); avoid the
                # duplicate item-level line over our data channel.
                publish_transcript=not cloud,
            )
        )

    @session.on("conversation_item_added")
    def _on_item(ev) -> None:
        item = ev.item
        if getattr(item, "role", None) != "assistant":
            return
        raw = getattr(item, "text_content", None) or ""
        if raw:
            used_search = search_ctx.take() is not None
            asyncio.create_task(
                on_agent_turn(
                    dc,
                    raw_text=raw,
                    ts=int(time.time()),
                    used_search=used_search,
                    publish_transcript=not cloud,  # cloud uses native streaming
                )
            )

    # LOCAL keeps the assistant chat item raw (markers drive the bilingual parse
    # + mode) and renders its own colored transcript, so the framework transcript
    # sync is off. CLOUD speaks naturally (no markers) → let the framework forward
    # transcripts for the app.
    await session.start(
        room=ctx.room,
        agent=build_tutor(settings, on_search=search_ctx.note),
        room_input_options=room_io.RoomInputOptions(text_enabled=True),
        room_output_options=room_io.RoomOutputOptions(transcription_enabled=cloud),
    )
    await dc.send_profile(settings.profile)
    await session.generate_reply(
        instructions="Chào học viên bằng tiếng Anh và mời họ bắt đầu luyện nói."
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
