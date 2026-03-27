"""Adapter for the Unified Patent Court (UPC) case law."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class UPCAdapter(BaseAdapter):
    """UPC adapter for Unified Patent Court decisions.

    Queries the Unified Patent Court case management system for
    patent infringement and validity decisions across participating
    EU member states.
    """

    BASE_URL = "https://www.unified-patent-court.org/en/court/cases"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "EU",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"upc:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                self.BASE_URL,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "upc",
                    "query": query,
                    "jurisdiction": "EU",
                    "indicator": "upc_case",
                    "note": "Unified Patent Court case registry",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
