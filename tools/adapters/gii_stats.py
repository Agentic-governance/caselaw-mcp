"""Adapter for Global Innovation Index (WIPO GII) statistics."""
from __future__ import annotations

from typing import Any

from .base import AdapterError, BaseAdapter


class GIIStatsAdapter(BaseAdapter):
    """WIPO Global Innovation Index adapter (Optional source)."""

    BASE_URL = "https://www.wipo.int/global_innovation_index/en/"

    def search_stats(
        self,
        indicator: str = "gii_rank",
        jurisdiction: str = "GLOBAL",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"gii_stats:{indicator}:{jurisdiction}:{year_from}"

        def _fetch() -> list[dict[str, Any]]:
            try:
                html = self._request_text(
                    "GET",
                    self.BASE_URL,
                    headers={"User-Agent": "legal-mcp/1.0"},
                )
            except AdapterError:
                # GII is an Optional source; soft-fail is acceptable
                return [
                    {
                        "source": "gii",
                        "indicator": indicator,
                        "jurisdiction": jurisdiction,
                        "note": "GII stats page unavailable (optional source); stub result",
                        "source_url": self.BASE_URL,
                    }
                ]

            return [
                {
                    "source": "gii",
                    "indicator": indicator,
                    "jurisdiction": jurisdiction,
                    "note": "WIPO Global Innovation Index page scraped",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
