"""Brave Search API backend (spec §8)."""

from __future__ import annotations

from typing import List

from .base import SearchResult

_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


def parse_brave(payload: dict, *, max_results: int = 5) -> List[SearchResult]:
    out = []
    for r in payload.get("web", {}).get("results", [])[:max_results]:
        out.append(
            SearchResult(r.get("title", ""), r.get("description", ""), r.get("url", ""))
        )
    return out


class Brave:
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def search(self, query: str, *, max_results: int = 5) -> List[SearchResult]:
        import httpx  # lazy

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                _ENDPOINT,
                params={"q": query, "count": max_results},
                headers={"X-Subscription-Token": self._api_key},
            )
            resp.raise_for_status()
            return parse_brave(resp.json(), max_results=max_results)
