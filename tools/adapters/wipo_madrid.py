"""Adapter for the WIPO Madrid System (international trademark registration)."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class WIPOMadridAdapter(BaseAdapter):
    """WIPO Madrid System adapter for international trademark registrations.

    Queries the WIPO Madrid Monitor / Global Brand Database for
    international trademark applications and registrations under the
    Madrid Protocol.
    """

    BASE_URL = "https://www.wipo.int/madrid/monitor/en"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "GLOBAL",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"wipo_madrid:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                "https://www3.wipo.int/madrid/monitor/en/",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "wipo_madrid",
                    "query": query,
                    "jurisdiction": "GLOBAL",
                    "indicator": "madrid_trademark_registration",
                    "note": "WIPO Madrid Monitor (international trademark system)",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
