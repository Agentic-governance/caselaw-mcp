"""Adapter for EPO IP statistics with external API."""
from __future__ import annotations

from typing import Any

from .base import AdapterError, BaseAdapter

class EPOStatsAdapter(BaseAdapter):
    """EPO Open Patent Services statistics adapter."""

    def search_stats(
        self,
        metric: str = "patent_applications",
        jurisdiction: str = "EP",
        year_from: int | None = None,
        year_to: int | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        cache_key = f"epo_stats:{metric}:{jurisdiction}:{year_from}:{year_to}"

        def _fetch() -> list[dict[str, Any]]:
            raise AdapterError("EPO OPS requires OAuth token — not configured")

        return self._run_with_cache(cache_key, _fetch)
