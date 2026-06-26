"""Tavily Search backend (spec §8). Clean RAG-oriented results."""

from __future__ import annotations

from typing import List

from .base import SearchResult

_ENDPOINT = "https://api.tavily.com/search"


def parse_tavily(payload: dict, *, max_results: int = 5) -> List[SearchResult]:
    out = []
    for r in payload.get("results", [])[:max_results]:
        out.append(SearchResult(r.get("title", ""), r.get("content", ""), r.get("url", "")))
    return out


class Tavily:
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def search(self, query: str, *, max_results: int = 5) -> List[SearchResult]:
        import httpx  # lazy: tests never hit the network

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                _ENDPOINT,
                json={
                    "api_key": self._api_key,
                    "query": query,
                    "max_results": max_results,
                },
            )
            resp.raise_for_status()
            return parse_tavily(resp.json(), max_results=max_results)
