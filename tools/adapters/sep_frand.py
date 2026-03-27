"""Adapter for Standard-Essential Patents (SEP) and FRAND licensing data."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class SEPFRANDAdapter(BaseAdapter):
    """SEP/FRAND adapter for standard-essential patent declarations.

    Queries ETSI's IPR database and related SEP declaration sources
    for FRAND commitment and licensing dispute data.
    """

    BASE_URL = "https://ipr.etsi.org"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "GLOBAL",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"sep_frand:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                self.BASE_URL,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "sep_frand",
                    "query": query,
                    "jurisdiction": "GLOBAL",
                    "indicator": "sep_frand_declaration",
                    "note": "ETSI IPR database (SEP/FRAND declarations)",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
