"""Tests for tutor_agent.search — backend factory, response parsing, grounding (spec §8)."""

import pytest

from tutor_agent.config import ConfigError, Settings
from tutor_agent.search.base import SearchResult, format_grounding
from tutor_agent.search.brave import parse_brave
from tutor_agent.search.factory import build_search
from tutor_agent.search.mock import MockSearch
from tutor_agent.search.searxng import SearXNG, parse_searxng
from tutor_agent.search.tavily import Tavily, parse_tavily


def test_parse_tavily():
    payload = {
        "results": [
            {"title": "Weather DN", "url": "https://w.com", "content": "sunny 30C"},
        ]
    }
    assert parse_tavily(payload) == [
        SearchResult("Weather DN", "sunny 30C", "https://w.com")
    ]


def test_parse_brave():
    payload = {
        "web": {
            "results": [
                {"title": "BBC", "url": "https://bbc.com", "description": "news"},
            ]
        }
    }
    assert parse_brave(payload) == [SearchResult("BBC", "news", "https://bbc.com")]


def test_parse_searxng():
    payload = {"results": [{"title": "Wiki", "url": "https://wiki.org", "content": "info"}]}
    assert parse_searxng(payload) == [SearchResult("Wiki", "info", "https://wiki.org")]


def test_parse_respects_max_results():
    payload = {"results": [{"title": f"t{i}", "url": "u", "content": "c"} for i in range(10)]}
    assert len(parse_tavily(payload, max_results=3)) == 3


def test_factory_returns_mock_when_mock_adapters():
    s = Settings.from_env({"MOCK_ADAPTERS": "1"})
    assert isinstance(build_search(s), MockSearch)


def test_factory_builds_tavily_with_key():
    s = Settings.from_env({"SEARCH_BACKEND": "tavily", "SEARCH_API_KEY": "k"})
    assert isinstance(build_search(s), Tavily)


def test_factory_tavily_without_key_raises():
    s = Settings.from_env({"SEARCH_BACKEND": "tavily"})
    with pytest.raises(ConfigError, match="SEARCH_API_KEY"):
        build_search(s)


def test_factory_searxng_needs_no_key():
    s = Settings.from_env({"SEARCH_BACKEND": "searxng"})
    assert isinstance(build_search(s), SearXNG)


def test_format_grounding_lists_each_result_with_source():
    results = [
        SearchResult("BBC", "sunny", "https://bbc.com"),
        SearchResult("VnExpress", "mưa", "https://vne.vn"),
    ]
    g = format_grounding(results)
    assert "BBC" in g and "https://bbc.com" in g and "sunny" in g
    assert "VnExpress" in g and "https://vne.vn" in g
    assert "[1]" in g and "[2]" in g


def test_format_grounding_empty():
    assert format_grounding([]) == "(no results)"


async def test_mock_search_returns_canned_results():
    results = await MockSearch().search("anything")
    assert len(results) >= 1
    assert all(isinstance(r, SearchResult) for r in results)
