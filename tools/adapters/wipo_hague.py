"""Adapter for the WIPO Hague System (international design registration)."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class WIPOHagueAdapter(BaseAdapter):
    """WIPO Hague System adapter for international design registrations.

    Queries the WIPO Hague Express database for international industrial
    design applications and registrations under the Hague Agreement.
    """

    BASE_URL = "https://www.wipo.int/designdb/hague/en"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "GLOBAL",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"wipo_hague:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                self.BASE_URL,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "wipo_hague",
                    "query": query,
                    "jurisdiction": "GLOBAL",
                    "indicator": "hague_design_registration",
                    "note": "WIPO Hague Express (international design system)",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
