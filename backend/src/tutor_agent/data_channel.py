"""Publish UI messages to the room data channel (spec §9.4).

The app subscribes and renders:
  {type:"transcript", lang, text, speaker}  ·  {type:"mode", value}  ·  {type:"profile", value}

Message builders are pure (unit tested); :class:`DataChannel` wraps the room's
local participant and JSON-encodes each message.
"""

from __future__ import annotations

import json
from typing import Any, Dict

TOPIC = "tutor"


def transcript_message(*, lang: str, text: str, speaker: str) -> Dict[str, Any]:
    return {"type": "transcript", "lang": lang, "text": text, "speaker": speaker}


def mode_message(value: str) -> Dict[str, Any]:
    return {"type": "mode", "value": value}


def profile_message(value: str) -> Dict[str, Any]:
    return {"type": "profile", "value": value}


def error_message(code: str, message: str) -> Dict[str, Any]:
    return {"type": "error", "code": code, "message": message}


class DataChannel:
    """Sends JSON messages over the LiveKit data channel to the app."""

    def __init__(self, local_participant: Any):
        self._lp = local_participant

    async def _send(self, message: Dict[str, Any]) -> None:
        payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
        await self._lp.publish_data(payload, reliable=True, topic=TOPIC)

    async def send_transcript(self, *, lang: str, text: str, speaker: str) -> None:
        await self._send(transcript_message(lang=lang, text=text, speaker=speaker))

    async def send_mode(self, value: str) -> None:
        await self._send(mode_message(value))

    async def send_profile(self, value: str) -> None:
        await self._send(profile_message(value))

    async def send_error(self, code: str, message: str) -> None:
        await self._send(error_message(code, message))
