"""Pick a search backend from Settings (spec §13 SEARCH_BACKEND)."""

from __future__ import annotations

from ..config import ConfigError, Settings
from .base import WebSearch
from .brave import Brave
from .mock import MockSearch
from .searxng import SearXNG
from .tavily import Tavily


def build_search(settings: Settings) -> WebSearch:
    if settings.use_mock_search:
        return MockSearch()

    backend = settings.search_backend
    if backend == "tavily":
        if not settings.search_api_key:
            raise ConfigError("SEARCH_API_KEY is required for SEARCH_BACKEND=tavily")
        return Tavily(settings.search_api_key)
    if backend == "brave":
        if not settings.search_api_key:
            raise ConfigError("SEARCH_API_KEY is required for SEARCH_BACKEND=brave")
        return Brave(settings.search_api_key)
    if backend == "searxng":
        return SearXNG(settings.searxng_url)
    raise ConfigError(f"Unknown SEARCH_BACKEND {backend!r}")  # pragma: no cover
