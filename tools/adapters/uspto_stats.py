"""Adapter for USPTO (US Patent and Trademark Office) statistics."""
from __future__ import annotations

from typing import Any

from .base import AdapterError, BaseAdapter


class USPTOStatsAdapter(BaseAdapter):
    """USPTO patent/trademark statistics adapter."""

    BASE_URL = "https://developer.uspto.gov/api/patent/search"

    def search_stats(
        self,
        indicator: str = "patent_applications",
        jurisdiction: str = "US",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"uspto_stats:{indicator}:{jurisdiction}:{year_from}"

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
                        "source": "uspto",
                        "indicator": indicator,
                        "jurisdiction": jurisdiction,
                        "note": "USPTO API unavailable; stub result",
                        "source_url": self.BASE_URL,
                    }
                ]

            return [
                {
                    "source": "uspto",
                    "indicator": indicator,
                    "jurisdiction": jurisdiction,
                    "note": "USPTO patent search API queried",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
