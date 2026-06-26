"""Tests for STT adapters — response parsing, SpeechEvent build, mock (spec §4.2)."""

from livekit.agents import stt

from tutor_agent.stt.mock import MockSTT
from tutor_agent.stt.nemotron import build_speech_event, parse_transcription


def test_parse_transcription_with_language():
    assert parse_transcription({"text": "xin chào", "language": "vi"}) == ("xin chào", "vi")


def test_parse_transcription_defaults_language_when_absent():
    assert parse_transcription({"text": "hello"}, default_language="vi") == ("hello", "vi")


def test_parse_transcription_strips_whitespace():
    assert parse_transcription({"text": "  hi  "}) == ("hi", "en")


def test_build_speech_event_is_final_transcript():
    ev = build_speech_event("I went there", "en")
    assert ev.type == stt.SpeechEventType.FINAL_TRANSCRIPT
    assert ev.alternatives[0].text == "I went there"
    assert ev.alternatives[0].language == "en"


def test_mock_stt_not_streaming():
    assert MockSTT().capabilities.streaming is False


async def test_mock_stt_recognize_returns_deterministic_text():
    ev = await MockSTT()._recognize_impl([])
    assert ev.type == stt.SpeechEventType.FINAL_TRANSCRIPT
    assert ev.alternatives[0].text  # non-empty canned transcript
