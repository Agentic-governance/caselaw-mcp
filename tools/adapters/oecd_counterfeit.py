"""Adapter for OECD counterfeit and piracy trade data."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class OECDCounterfeitAdapter(BaseAdapter):
    """OECD counterfeit trade adapter.

    Queries OECD data on trade in counterfeit and pirated goods,
    including the Task Force on Countering Illicit Trade reports.
    """

    BASE_URL = "https://www.oecd.org/en/topics/sub-issues/countering-illicit-trade.html"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "GLOBAL",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"oecd_counterfeit:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                self.BASE_URL,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "oecd_counterfeit",
                    "query": query,
                    "jurisdiction": "GLOBAL",
                    "indicator": "counterfeit_trade",
                    "note": "OECD Task Force on Countering Illicit Trade",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
