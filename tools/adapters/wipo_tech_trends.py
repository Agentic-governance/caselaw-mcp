"""Adapter for WIPO Technology Trends reports."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class WIPOTechTrendsAdapter(BaseAdapter):
    """WIPO Technology Trends adapter for patent landscape analysis.

    Queries WIPO Technology Trends publications for patent landscape
    reports on emerging technologies (AI, blockchain, etc.) and
    innovation trend data.
    """

    BASE_URL = "https://www.wipo.int/tech_trends/en"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "GLOBAL",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"wipo_tech_trends:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                self.BASE_URL,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "wipo_tech_trends",
                    "query": query,
                    "jurisdiction": "GLOBAL",
                    "indicator": "patent_landscape",
                    "note": "WIPO Technology Trends",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
