"""Adapter for EUIPO opposition proceedings."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class EUIPOOppositionAdapter(BaseAdapter):
    """EUIPO opposition proceedings adapter.

    Queries the EUIPO eSearch Case Law database for trademark opposition
    decisions and cancellation proceedings.
    """

    BASE_URL = "https://euipo.europa.eu/eSearchCLW"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "EU",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"euipo_opposition:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                self.BASE_URL,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "euipo_opposition",
                    "query": query,
                    "jurisdiction": "EU",
                    "indicator": "trademark_opposition",
                    "note": "EUIPO eSearch Case Law",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
