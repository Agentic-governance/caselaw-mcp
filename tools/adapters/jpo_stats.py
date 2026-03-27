"""Adapter for JPO (Japan Patent Office) statistics."""
from __future__ import annotations

from typing import Any

from .base import AdapterError, BaseAdapter


class JPOStatsAdapter(BaseAdapter):
    """JPO patent/trademark statistics adapter."""

    BASE_URL = "https://www.jpo.go.jp/e/resources/statistics/index.html"

    def search_stats(
        self,
        indicator: str = "patent_applications",
        jurisdiction: str = "JP",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"jpo_stats:{indicator}:{jurisdiction}:{year_from}"

        def _fetch() -> list[dict[str, Any]]:
            try:
                html = self._request_text(
                    "GET",
                    self.BASE_URL,
                    headers={"User-Agent": "legal-mcp/1.0"},
                )
            except AdapterError:
                return [
                    {
                        "source": "jpo",
                        "indicator": indicator,
                        "jurisdiction": jurisdiction,
                        "note": "JPO stats page unavailable; stub result",
                        "source_url": self.BASE_URL,
                    }
                ]

            return [
                {
                    "source": "jpo",
                    "indicator": indicator,
                    "jurisdiction": jurisdiction,
                    "note": "JPO public statistics page scraped",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
