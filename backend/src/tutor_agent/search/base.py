"""Web search protocol + grounding helper (spec §8).

Grounding rule: synthesis uses *only* the returned results. :func:`format_grounding`
renders them into a numbered context block the LLM is told to cite from and not
go beyond.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol, runtime_checkable


@dataclass(frozen=True)
class SearchResult:
    title: str
    snippet: str
    url: str


@runtime_checkable
class WebSearch(Protocol):
    async def search(self, query: str, *, max_results: int = 5) -> List[SearchResult]:
        ...


def format_grounding(results: List[SearchResult]) -> str:
    """Render results as a numbered, citable context block for the LLM."""
    if not results:
        return "(no results)"
    return "\n".join(
        f"[{i}] {r.title} — {r.url}\n{r.snippet}"
        for i, r in enumerate(results, start=1)
    )
