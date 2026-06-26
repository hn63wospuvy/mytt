"""Tests for tutor_agent.session_factory — local vs cloud profile (spec §3, §5)."""

import pytest

from tutor_agent.config import ConfigError, Settings
from tutor_agent.session_factory import (
    build_realtime_model,
    build_tutor,
    realtime_kwargs,
    uses_realtime,
)
from tutor_agent.tutor import Tutor


def test_uses_realtime_only_for_cloud():
    assert uses_realtime(Settings.from_env({"PROFILE": "cloud"})) is True
    assert uses_realtime(Settings.from_env({"PROFILE": "local"})) is False


def test_build_realtime_model_requires_api_key():
    s = Settings.from_env({"PROFILE": "cloud"})
    with pytest.raises(ConfigError, match="GEMINI_API_KEY"):
        build_realtime_model(s)


def test_build_realtime_model_with_key():
    from livekit.plugins.google.realtime import RealtimeModel

    s = Settings.from_env({"PROFILE": "cloud", "GEMINI_API_KEY": "k"})
    assert isinstance(build_realtime_model(s), RealtimeModel)


def test_realtime_kwargs_omits_language_unless_set():
    # Native-audio Gemini rejects bare "vi"; default must NOT pin a language.
    base = Settings.from_env({"PROFILE": "cloud", "GEMINI_API_KEY": "k"})
    assert "language" not in realtime_kwargs(base)
    withlang = Settings.from_env(
        {"PROFILE": "cloud", "GEMINI_API_KEY": "k", "GEMINI_LANGUAGE": "en-US"}
    )
    assert realtime_kwargs(withlang)["language"] == "en-US"


def test_realtime_kwargs_tunes_for_latency():
    # Default thinking budget = 1, transcription both ways (streaming text).
    kw = realtime_kwargs(Settings.from_env({"PROFILE": "cloud", "GEMINI_API_KEY": "k"}))
    assert kw["thinking_config"].thinking_budget == 1
    assert "input_audio_transcription" in kw and "output_audio_transcription" in kw
    # An explicit budget flows through; -1 leaves the model default (omitted).
    kw0 = realtime_kwargs(
        Settings.from_env(
            {"PROFILE": "cloud", "GEMINI_API_KEY": "k", "GEMINI_THINKING_BUDGET": "0"}
        )
    )
    assert kw0["thinking_config"].thinking_budget == 0
    kw2 = realtime_kwargs(
        Settings.from_env(
            {"PROFILE": "cloud", "GEMINI_API_KEY": "k", "GEMINI_THINKING_BUDGET": "-1"}
        )
    )
    assert "thinking_config" not in kw2


def test_apply_session_overrides_thinking():
    from tutor_agent.config import apply_session_overrides

    base = Settings.from_env({"PROFILE": "cloud", "GEMINI_API_KEY": "k"})
    assert apply_session_overrides(base, '{"thinking": 5}').gemini_thinking_budget == 5
    assert apply_session_overrides(base, '{"thinking": 0}').gemini_thinking_budget == 0
    # absent / malformed / non-dict metadata leaves settings unchanged
    for meta in (None, "", "not json", "[1,2]", "{}"):
        assert apply_session_overrides(base, meta) is base or \
            apply_session_overrides(base, meta).gemini_thinking_budget == base.gemini_thinking_budget


def test_build_tutor_local_has_web_search():
    s = Settings.from_env({"PROFILE": "local", "SEARCH_API_KEY": "k"})
    assert len(build_tutor(s).tools) == 1


def test_build_tutor_cloud_omits_web_search():
    s = Settings.from_env({"PROFILE": "cloud", "GEMINI_API_KEY": "k"})
    tutor = build_tutor(s)
    assert isinstance(tutor, Tutor)
    assert len(tutor.tools) == 0
