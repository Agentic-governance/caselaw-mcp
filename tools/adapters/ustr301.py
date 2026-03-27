"""Adapter for USTR Special 301 reports on IP protection."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class USTR301Adapter(BaseAdapter):
    """USTR Special 301 adapter for IP protection assessments.

    Queries the Office of the United States Trade Representative for
    Special 301 reports identifying countries with inadequate IP
    protection (Watch List, Priority Watch List, etc.).
    """

    BASE_URL = "https://ustr.gov/issue-areas/intellectual-property/special-301"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "GLOBAL",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"ustr301:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                self.BASE_URL,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "ustr301",
                    "query": query,
                    "jurisdiction": "GLOBAL",
                    "indicator": "special_301_report",
                    "note": "USTR Special 301 Report",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
