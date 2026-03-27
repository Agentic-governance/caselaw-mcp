"""Adapter for EUIPO (EU Intellectual Property Office) statistics."""
from __future__ import annotations

from typing import Any

from .base import AdapterError, BaseAdapter


class EUIPOStatsAdapter(BaseAdapter):
    """EUIPO trademark/design statistics adapter."""

    BASE_URL = "https://euipo.europa.eu/tunnel-web/secure/webdav/guest/document_library/observatory/documents/quantification-of-ipr-infringement/euipo_statistics.json"

    def search_stats(
        self,
        indicator: str = "trademark_applications",
        jurisdiction: str = "EU",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"euipo_stats:{indicator}:{jurisdiction}:{year_from}"

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
                        "source": "euipo",
                        "indicator": indicator,
                        "jurisdiction": jurisdiction,
                        "note": "EUIPO stats endpoint unavailable; stub result",
                        "source_url": self.BASE_URL,
                    }
                ]

            return [
                {
                    "source": "euipo",
                    "indicator": indicator,
                    "jurisdiction": jurisdiction,
                    "note": "EUIPO statistics endpoint queried",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
