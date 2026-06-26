"""Deterministic mock search — lets the hỏi-đáp loop run with no API key."""

from __future__ import annotations

from typing import List

from .base import SearchResult


class MockSearch:
    async def search(self, query: str, *, max_results: int = 5) -> List[SearchResult]:
        return [
            SearchResult(
                title=f"[mock] result for {query!r}",
                snippet="This is a deterministic mock snippet used for tests/offline runs.",
                url="https://example.com/mock",
            )
        ][:max_results]
