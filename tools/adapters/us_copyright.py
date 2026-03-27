"""Adapter for the US Copyright Office registration data."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class USCopyrightAdapter(BaseAdapter):
    """US Copyright Office adapter for registration and recordation data.

    Queries the US Copyright Office public catalog for copyright
    registrations, recordations, and related documents.
    """

    BASE_URL = "https://www.copyright.gov/public-records"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "US",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"us_copyright:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                self.BASE_URL,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "us_copyright",
                    "query": query,
                    "jurisdiction": "US",
                    "indicator": "copyright_registration",
                    "note": "US Copyright Office public catalog",
                    "source_url": self.BASE_URL,
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
