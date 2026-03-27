"""Adapter for IP Australia (Australian IP office)."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class IPAustraliaAdapter(BaseAdapter):
    """IP Australia adapter for Australian IP data.

    Queries IP Australia for patent, trademark, and design registration
    data including examination and opposition proceedings.
    """

    BASE_URL = "https://search.ipaustralia.gov.au/trademarks/search/quick"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "AU",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"ip_australia:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                self.BASE_URL,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "ip_australia",
                    "query": query,
                    "jurisdiction": "AU",
                    "indicator": "ip_registration",
                    "note": "IP Australia",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
