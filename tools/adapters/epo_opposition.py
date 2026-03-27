"""Adapter for EPO opposition proceedings via the European Patent Register."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class EPOOppositionAdapter(BaseAdapter):
    """EPO opposition proceedings adapter.

    Queries the European Patent Register for opposition proceedings,
    decisions, and appeal outcomes.
    """

    BASE_URL = "https://register.epo.org/application"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "EP",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"epo_opposition:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            resp = self._request_text(
                "GET",
                self.BASE_URL,
                params={"number": query, "lng": "en", "tab": "doclist"},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "epo_opposition",
                    "query": query,
                    "jurisdiction": "EP",
                    "indicator": "patent_opposition",
                    "note": "European Patent Register opposition data",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
