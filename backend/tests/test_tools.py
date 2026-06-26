"""Tests for tutor_agent.tools — web_search tool core + grounding (spec §8)."""

from typing import List

from tutor_agent.search.base import SearchResult
from tutor_agent.search.mock import MockSearch
from tutor_agent.tools import (
    SearchContext,
    make_web_search_tool,
    results_to_sources,
    run_web_search,
)


class _EmptyBackend:
    async def search(self, query: str, *, max_results: int = 5) -> List[SearchResult]:
        return []


async def test_run_web_search_returns_grounding_with_sources():
    out = await run_web_search(MockSearch(), "thời tiết Đà Nẵng")
    assert "[mock]" in out
    assert "https://example.com/mock" in out
    assert "[1]" in out


async def test_run_web_search_empty_results():
    assert await run_web_search(_EmptyBackend(), "no hits") == "(no results)"


def test_make_web_search_tool_builds_a_tool():
    tool = make_web_search_tool(MockSearch())
    assert tool is not None


async def test_run_web_search_invokes_on_search_callback():
    seen = {}

    def on_search(query, results):
        seen["query"] = query
        seen["results"] = results

    await run_web_search(MockSearch(), "thời tiết", on_search=on_search)
    assert seen["query"] == "thời tiết"
    assert len(seen["results"]) >= 1


def test_search_context_note_and_take():
    ctx = SearchContext()
    assert ctx.take() is None
    ctx.note("q", [SearchResult("t", "s", "u")])
    got = ctx.take()
    assert got[0] == "q" and got[1][0].title == "t"
    assert ctx.take() is None  # cleared after take


def test_results_to_sources():
    src = results_to_sources([SearchResult("BBC", "sunny", "https://bbc.com")])
    assert src == [{"title": "BBC", "snippet": "sunny", "url": "https://bbc.com"}]
