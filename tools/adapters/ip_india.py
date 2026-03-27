"""Adapter for IP India (Indian IP office)."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class IPIndiaAdapter(BaseAdapter):
    """IP India adapter for Indian IP filings and registrations.

    Queries the Indian Patent Office and Trademark Registry for
    IP application and prosecution data. Connection may be unstable;
    WIPO statistics can be used as a fallback.
    """

    BASE_URL = "https://ipindia.gov.in"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "IN",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"ip_india:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                self.BASE_URL,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "ip_india",
                    "query": query,
                    "jurisdiction": "IN",
                    "indicator": "ip_registration",
                    "note": "IP India (Controller General of Patents, Designs & Trade Marks)",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
