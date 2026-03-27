"""Adapter for WIPO IP statistics (PCT, Madrid, Hague systems)."""
from __future__ import annotations

from typing import Any

from .base import AdapterError, BaseAdapter


class WIPOStatsAdapter(BaseAdapter):
    """WIPO IP statistics adapter (PCT filings, Madrid registrations, etc.)."""

    BASE_URL = "https://www3.wipo.int/ipstats/api/data"

    def search_stats(
        self,
        indicator: str = "patent_applications",
        jurisdiction: str = "GLOBAL",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"wipo_stats:{indicator}:{jurisdiction}:{year_from}"

        def _fetch() -> list[dict[str, Any]]:
            try:
                text = self._request_text(
                    "GET",
                    self.BASE_URL,
                    headers={"User-Agent": "legal-mcp/1.0"},
                )
            except AdapterError:
                return [
                    {
                        "source": "wipo",
                        "indicator": indicator,
                        "jurisdiction": jurisdiction,
                        "note": "WIPO IP stats API unavailable; stub result",
                        "source_url": self.BASE_URL,
                    }
                ]

            return [
                {
                    "source": "wipo",
                    "indicator": indicator,
                    "jurisdiction": jurisdiction,
                    "note": "WIPO IP statistics API queried",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
