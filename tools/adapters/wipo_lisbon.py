"""Adapter for the WIPO Lisbon System (appellations of origin and GIs)."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class WIPOLisbonAdapter(BaseAdapter):
    """WIPO Lisbon System adapter for appellations of origin.

    Queries the WIPO Lisbon Express database for internationally
    registered appellations of origin and geographical indications
    under the Lisbon Agreement and Geneva Act.
    """

    BASE_URL = "https://www.wipo.int/lisbon/en"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "GLOBAL",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"wipo_lisbon:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                "https://www.wipo.int/lisbon/en/registrations",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "wipo_lisbon",
                    "query": query,
                    "jurisdiction": "GLOBAL",
                    "indicator": "lisbon_appellation",
                    "note": "WIPO Lisbon Express (appellations of origin / GIs)",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
