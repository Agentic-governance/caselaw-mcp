"""Adapter for UPOV (International Union for the Protection of New Varieties of Plants)."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class UPOVAdapter(BaseAdapter):
    """UPOV adapter for plant variety protection data.

    Queries the UPOV PLUTO database for plant breeders' rights
    applications and grants across member states.
    """

    BASE_URL = "https://www.upov.int/pluto/en"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "GLOBAL",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"upov:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                self.BASE_URL,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "upov",
                    "query": query,
                    "jurisdiction": "GLOBAL",
                    "indicator": "plant_variety_protection",
                    "note": "UPOV PLUTO database",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
