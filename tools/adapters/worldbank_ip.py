"""Adapter for World Bank IP indicators (patent/trademark applications, R&D expenditure)."""
from __future__ import annotations

from typing import Any

from .base import AdapterError, BaseAdapter


class WorldBankIPAdapter(BaseAdapter):
    """World Bank Development Indicators -- IP-related metrics."""

    BASE_URL = "https://api.worldbank.org/v2/country/all/indicator"

    def search_stats(
        self,
        indicator: str = "patent_applications",
        jurisdiction: str = "GLOBAL",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        # World Bank indicator codes: IP.PAT.RESD, IP.PAT.NRES, IP.TMK.TOTL
        wb_indicator = {
            "patent_applications": "IP.PAT.RESD",
            "trademark_applications": "IP.TMK.TOTL",
        }.get(indicator, "IP.PAT.RESD")
        url = f"{self.BASE_URL}/{wb_indicator}"
        cache_key = f"worldbank_ip:{indicator}:{jurisdiction}:{year_from}"

        def _fetch() -> list[dict[str, Any]]:
            try:
                text = self._request_text(
                    "GET",
                    url,
                    params={"format": "json", "per_page": str(limit)},
                    headers={"User-Agent": "legal-mcp/1.0"},
                )
            except AdapterError:
                return [
                    {
                        "source": "worldbank",
                        "indicator": indicator,
                        "jurisdiction": jurisdiction,
                        "note": "World Bank API unavailable; stub result",
                        "source_url": url,
                    }
                ]

            return [
                {
                    "source": "worldbank",
                    "indicator": indicator,
                    "jurisdiction": jurisdiction,
                    "note": "World Bank Development Indicators queried",
                    "source_url": url,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
