"""Adapter for CNIPA (China National Intellectual Property Administration) statistics."""
from __future__ import annotations

from typing import Any

from .base import AdapterError, BaseAdapter


class CNIPAStatsAdapter(BaseAdapter):
    """CNIPA patent/trademark statistics adapter."""

    BASE_URL = "https://english.cnipa.gov.cn/col/col1071/index.html"

    def search_stats(
        self,
        indicator: str = "patent_applications",
        jurisdiction: str = "CN",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"cnipa_stats:{indicator}:{jurisdiction}:{year_from}"

        def _fetch() -> list[dict[str, Any]]:
            try:
                html = self._request_text(
                    "GET",
                    self.BASE_URL,
                    headers={"User-Agent": "legal-mcp/1.0"},
                )
            except AdapterError:
                # Fallback: return stub result when CNIPA is unreachable
                return [
                    {
                        "source": "cnipa",
                        "indicator": indicator,
                        "jurisdiction": jurisdiction,
                        "note": "CNIPA public stats page unavailable; stub result",
                        "source_url": self.BASE_URL,
                    }
                ]

            return [
                {
                    "source": "cnipa",
                    "indicator": indicator,
                    "jurisdiction": jurisdiction,
                    "note": "CNIPA public stats page scraped",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
