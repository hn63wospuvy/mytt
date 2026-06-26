"""Tests for tutor_agent.config — env → typed Settings (spec §13)."""

import pytest

from tutor_agent.config import ConfigError, Settings


def test_defaults_applied_when_env_empty():
    s = Settings.from_env({})
    assert s.profile == "local"
    assert s.stt_lang == "vi"
    assert s.stt_chunk_ms == 160
    assert s.llm_max_tokens == 256
    assert s.search_backend == "tavily"
    assert s.wakeword_engine == "openwakeword"


def test_reads_values_from_env():
    s = Settings.from_env(
        {
            "PROFILE": "cloud",
            "LIVEKIT_URL": "ws://10.0.0.1:7880",
            "STT_MODEL": "custom/model",
            "STT_CHUNK_MS": "320",
            "LLM_MAX_TOKENS": "512",
            "SEARCH_BACKEND": "brave",
        }
    )
    assert s.profile == "cloud"
    assert s.livekit_url == "ws://10.0.0.1:7880"
    assert s.stt_model == "custom/model"
    assert s.stt_chunk_ms == 320
    assert s.llm_max_tokens == 512
    assert s.search_backend == "brave"


def test_invalid_profile_raises():
    with pytest.raises(ConfigError, match="PROFILE"):
        Settings.from_env({"PROFILE": "banana"})


def test_invalid_search_backend_raises():
    with pytest.raises(ConfigError, match="SEARCH_BACKEND"):
        Settings.from_env({"SEARCH_BACKEND": "duckduckgo"})


def test_non_integer_chunk_ms_raises():
    with pytest.raises(ConfigError, match="STT_CHUNK_MS"):
        Settings.from_env({"STT_CHUNK_MS": "fast"})


def test_non_positive_max_tokens_raises():
    with pytest.raises(ConfigError, match="LLM_MAX_TOKENS"):
        Settings.from_env({"LLM_MAX_TOKENS": "0"})


def test_tts_base_url_default_and_override():
    assert Settings.from_env({}).tts_base_url == "http://localhost:8001"
    assert Settings.from_env({"TTS_BASE_URL": "http://x:9"}).tts_base_url == "http://x:9"


def test_level_default_and_override():
    assert Settings.from_env({}).level == "B1"
    assert Settings.from_env({"LEVEL": "A2"}).level == "A2"


def test_use_mock_adapters_flag_defaults_false():
    assert Settings.from_env({}).use_mock_adapters is False


def test_use_mock_adapters_flag_truthy_values():
    for v in ("1", "true", "TRUE", "yes", "on"):
        assert Settings.from_env({"MOCK_ADAPTERS": v}).use_mock_adapters is True
    for v in ("0", "false", "no", "off", ""):
        assert Settings.from_env({"MOCK_ADAPTERS": v}).use_mock_adapters is False


def test_mock_all_enables_every_component():
    s = Settings.from_env({"MOCK_ADAPTERS": "1"})
    assert (s.use_mock_stt, s.use_mock_llm, s.use_mock_tts, s.use_mock_search) == (
        True, True, True, True,
    )


def test_per_component_mock_override_alone():
    s = Settings.from_env({"MOCK_LLM": "1"})
    assert s.use_mock_llm is True
    assert s.use_mock_stt is False and s.use_mock_tts is False and s.use_mock_search is False


def test_per_component_mock_can_opt_out_of_global():
    # real LLM while everything else mocked
    s = Settings.from_env({"MOCK_ADAPTERS": "1", "MOCK_LLM": "0"})
    assert s.use_mock_llm is False
    assert s.use_mock_stt is True and s.use_mock_tts is True and s.use_mock_search is True


def test_llm_base_url_default_port_is_8082():
    assert Settings.from_env({}).llm_base_url == "http://localhost:8082/v1"


def test_user_id_from_metadata():
    from tutor_agent.config import user_id_from_metadata
    assert user_id_from_metadata('{"user_id": "g1", "thinking": 2}') == "g1"
    assert user_id_from_metadata('{"thinking": 2}') is None
    assert user_id_from_metadata(None) is None
    assert user_id_from_metadata("not json") is None
    assert user_id_from_metadata('{"user_id": ""}') is None


def test_gemini_key_from_metadata():
    from tutor_agent.config import gemini_key_from_metadata
    assert gemini_key_from_metadata('{"user_id": "c1", "key": "AIza"}') == "AIza"
    assert gemini_key_from_metadata('{"user_id": "c1"}') is None
    assert gemini_key_from_metadata('{"key": ""}') is None
    assert gemini_key_from_metadata(None) is None
    assert gemini_key_from_metadata("not json") is None
    assert gemini_key_from_metadata('{"key": 123}') is None  # non-str ignored
