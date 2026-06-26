"""SearXNG self-hosted meta-search backend (spec §8). Keeps search self-hosted."""

from __future__ import annotations

from typing import List

from .base import SearchResult


def parse_searxng(payload: dict, *, max_results: int = 5) -> List[SearchResult]:
    out = []
    for r in payload.get("results", [])[:max_results]:
        out.append(SearchResult(r.get("title", ""), r.get("content", ""), r.get("url", "")))
    return out


class SearXNG:
    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")

    async def search(self, query: str, *, max_results: int = 5) -> List[SearchResult]:
        import httpx  # lazy

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self._base_url}/search",
                params={"q": query, "format": "json"},
            )
            resp.raise_for_status()
            return parse_searxng(resp.json(), max_results=max_results)
