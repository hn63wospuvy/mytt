"""Tests for tutor_agent.tutor — Agent subclass + system prompt (spec §7.3)."""

from livekit.agents import Agent

from tutor_agent.search.mock import MockSearch
from tutor_agent.tutor import Tutor, build_instructions


def test_instructions_cover_three_modes():
    text = build_instructions(None)
    assert "GIẢNG" in text
    assert "LUYỆN" in text
    assert "HỎI-ĐÁP" in text


def test_instructions_declare_tag_and_marker_rules():
    text = build_instructions(None)
    assert "<vi>" in text and "<en>" in text
    assert "web_search" in text
    assert "<fix" in text and "<vocab" in text


def test_instructions_inject_level():
    assert "B1" in build_instructions("B1")


def test_tutor_is_agent_with_web_search_tool():
    t = Tutor(search_backend=MockSearch(), level="B1")
    assert isinstance(t, Agent)
    assert len(t.tools) == 1


def test_cloud_instructions_are_tag_free():
    text = build_instructions("B1", tagged=False)
    assert "GIẢNG" in text and "LUYỆN" in text and "HỎI-ĐÁP" in text
    assert "<vi>" not in text and "<fix" not in text and "<vocab" not in text


def test_tutor_cloud_mode_has_no_tools():
    t = Tutor(level="B1", enable_web_search=False, tagged=False)
    assert len(t.tools) == 0
