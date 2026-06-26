"""The ``web_search`` function tool for the local-profile hỏi-đáp flow (spec §8).

Grounding rule: the tool returns a numbered, source-bearing context block; the
system prompt tells the LLM to synthesize *only* from it and cite sources.
"""

from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from livekit.agents import function_tool

from .search.base import SearchResult, WebSearch, format_grounding

OnSearch = Callable[[str, List[SearchResult]], None]


class SearchContext:
    """Tracks whether a web_search ran this turn (feeds the HỎI-ĐÁP mode
    derivation). The tool calls :meth:`note`; the turn handler :meth:`take`
    reads-and-clears it."""

    def __init__(self) -> None:
        self._pending: Optional[Tuple[str, List[SearchResult]]] = None

    def note(self, query: str, results: List[SearchResult]) -> None:
        self._pending = (query, results)

    def take(self) -> Optional[Tuple[str, List[SearchResult]]]:
        p, self._pending = self._pending, None
        return p


def results_to_sources(results: List[SearchResult]) -> List[dict]:
    """SearchResult list → the {title, snippet, url} dicts stored in qa.sources."""
    return [{"title": r.title, "snippet": r.snippet, "url": r.url} for r in results]


async def run_web_search(
    backend: WebSearch, query: str, *, max_results: int = 5, on_search: Optional[OnSearch] = None
) -> str:
    """Search and render results as grounded context (pure of the framework)."""
    results = await backend.search(query, max_results=max_results)
    if on_search is not None:
        on_search(query, results)
    return format_grounding(results)


def make_web_search_tool(backend: WebSearch, on_search: Optional[OnSearch] = None):
    """Build a ``web_search`` FunctionTool bound to ``backend``.

    ``on_search(query, results)`` (if given) fires on each call so the QA log can
    capture the question + sources for the answer that follows."""

    @function_tool(
        name="web_search",
        description=(
            "Tìm thông tin cập nhật/sự kiện trên web. Trả về danh sách kết quả "
            "đánh số, mỗi kết quả có tiêu đề, URL và trích đoạn. Chỉ được tổng "
            "hợp câu trả lời từ các kết quả này và nêu nguồn."
        ),
    )
    async def web_search(query: str) -> str:
        return await run_web_search(backend, query, on_search=on_search)

    return web_search
