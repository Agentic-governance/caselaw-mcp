"""Adapter for WTO TRIPS Agreement data and dispute settlements."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class WTOTRIPSAdapter(BaseAdapter):
    """WTO TRIPS adapter for IP-related trade disputes.

    Queries WTO dispute settlement data for TRIPS Agreement
    (Trade-Related Aspects of Intellectual Property Rights)
    cases and related documents.
    """

    BASE_URL = "https://www.wto.org/english/tratop_e/dispu_e/dispu_agreements_index_e.htm"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "GLOBAL",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"wto_trips:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                self.BASE_URL,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "wto_trips",
                    "query": query,
                    "jurisdiction": "GLOBAL",
                    "indicator": "trips_dispute",
                    "note": "WTO TRIPS dispute settlement",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
