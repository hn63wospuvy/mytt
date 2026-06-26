"""Tests for STT/TTS adapter factories — mock vs real selection from Settings."""

from tutor_agent.config import Settings
from tutor_agent.stt.factory import build_stt
from tutor_agent.stt.mock import MockSTT
from tutor_agent.stt.nemotron import NemotronSTT
from tutor_agent.tts.factory import build_tts
from tutor_agent.tts.mock import MockTTS
from tutor_agent.tts.vieneu import VieNeuTTS


def test_build_stt_mock():
    assert isinstance(build_stt(Settings.from_env({"MOCK_ADAPTERS": "1"}), vad=None), MockSTT)


def test_build_stt_real_is_nemotron():
    assert isinstance(build_stt(Settings.from_env({}), vad=None), NemotronSTT)


def test_build_tts_mock():
    assert isinstance(build_tts(Settings.from_env({"MOCK_ADAPTERS": "1"})), MockTTS)


def test_build_tts_real_is_vieneu():
    assert isinstance(build_tts(Settings.from_env({})), VieNeuTTS)
