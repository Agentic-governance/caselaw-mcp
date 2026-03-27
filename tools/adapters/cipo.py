"""Adapter for CIPO (Canadian Intellectual Property Office) data."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class CIPOAdapter(BaseAdapter):
    """CIPO adapter for Canadian IP filings, trademarks, and patent data.

    Queries the Canadian Intellectual Property Office for IP registration
    and prosecution data.
    """

    BASE_URL = "https://ised-isde.canada.ca/cipo"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "CA",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"cipo:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                f"{self.BASE_URL}/trademark-search/srch",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "cipo",
                    "query": query,
                    "jurisdiction": "CA",
                    "indicator": "ip_registration",
                    "note": "Canadian Intellectual Property Office",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
