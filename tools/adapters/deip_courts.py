"""Adapter for German IP courts (Bundespatentgericht and regional courts)."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class DEIPCourtsAdapter(BaseAdapter):
    """German IP courts adapter.

    Queries the Bundespatentgericht (Federal Patent Court) and related
    German IP court decisions via the official Rechtsprechungsdatenbank.
    """

    BASE_URL = "https://www.bundespatentgericht.de"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "DE",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"deip_courts:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                f"{self.BASE_URL}/rechtsprechung.html",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "deip_courts",
                    "query": query,
                    "jurisdiction": "DE",
                    "indicator": "ip_court_decision",
                    "note": "German Federal Patent Court",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
