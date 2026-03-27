"""Adapter for OECD IP statistics (patent indicators, trade in counterfeit)."""
from __future__ import annotations

from typing import Any

from .base import AdapterError, BaseAdapter


class OECDIPAdapter(BaseAdapter):
    """OECD IP/counterfeit trade statistics adapter."""

    BASE_URL = "https://stats.oecd.org/restsdmx/sdmx.ashx/GetData/MSTI_PUB/TH_WRXKF.JPN+USA+DEU+KOR+FRA+GBR+CAN+AUS/all"

    def search_stats(
        self,
        indicator: str = "patent_applications",
        jurisdiction: str = "OECD",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"oecd_ip:{indicator}:{jurisdiction}:{year_from}"

        def _fetch() -> list[dict[str, Any]]:
            try:
                text = self._request_text(
                    "GET",
                    self.BASE_URL,
                    headers={"User-Agent": "legal-mcp/1.0"},
                )
            except AdapterError:
                return [
                    {
                        "source": "oecd",
                        "indicator": indicator,
                        "jurisdiction": jurisdiction,
                        "note": "OECD stats API unavailable; stub result",
                        "source_url": self.BASE_URL,
                    }
                ]

            return [
                {
                    "source": "oecd",
                    "indicator": indicator,
                    "jurisdiction": jurisdiction,
                    "note": "OECD MSTI/IP statistics queried",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
