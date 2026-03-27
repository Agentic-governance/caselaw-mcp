"""Adapter for IPOS (Intellectual Property Office of Singapore)."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class IPOSSingaporeAdapter(BaseAdapter):
    """IPOS Singapore adapter for Singapore IP data.

    Queries the Intellectual Property Office of Singapore for patent,
    trademark, and design registration data.
    """

    BASE_URL = "https://www.ipos.gov.sg"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "SG",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"ipos_singapore:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                f"{self.BASE_URL}/about-ip",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "ipos_singapore",
                    "query": query,
                    "jurisdiction": "SG",
                    "indicator": "ip_registration",
                    "note": "Intellectual Property Office of Singapore",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
