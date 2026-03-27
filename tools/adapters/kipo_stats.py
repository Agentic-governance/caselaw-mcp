"""Adapter for KIPO (Korean Intellectual Property Office) statistics."""
from __future__ import annotations

from typing import Any

from .base import AdapterError, BaseAdapter


class KIPOStatsAdapter(BaseAdapter):
    """KIPO patent/trademark statistics adapter."""

    BASE_URL = "https://www.kipo.go.kr/en/HtmlApp/HtmlApp.do?pg=/en/info/statistics.html"

    def search_stats(
        self,
        indicator: str = "patent_applications",
        jurisdiction: str = "KR",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"kipo_stats:{indicator}:{jurisdiction}:{year_from}"

        def _fetch() -> list[dict[str, Any]]:
            try:
                html = self._request_text(
                    "GET",
                    self.BASE_URL,
                    headers={"User-Agent": "legal-mcp/1.0"},
                )
            except AdapterError:
                return [
                    {
                        "source": "kipo",
                        "indicator": indicator,
                        "jurisdiction": jurisdiction,
                        "note": "KIPO stats page unavailable; stub result",
                        "source_url": self.BASE_URL,
                    }
                ]

            return [
                {
                    "source": "kipo",
                    "indicator": indicator,
                    "jurisdiction": jurisdiction,
                    "note": "KIPO public statistics page scraped",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
