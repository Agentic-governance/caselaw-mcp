"""Adapter for Australian federal legislation via legislation.gov.au search."""
from __future__ import annotations

import re
from html import unescape
from typing import Any

from .base import AdapterError, BaseAdapter


class AULegAdapter(BaseAdapter):
    """Australian federal legislation adapter via HTTP search."""

    BASE_URL = "https://www.legislation.gov.au"

    def search_statutes(
        self, query: str, article: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")
        cache_key = f"auleg:{q.lower()}:{article}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            from urllib.parse import quote

            search_url = f"{self.BASE_URL}/Search/{quote(q)}"
            html = self._request_text(
                "GET", search_url, headers={"User-Agent": "legal-mcp/1.0"}
            )

            rows: list[dict[str, Any]] = []
            for m in re.finditer(
                r'<a[^>]+href="(/[A-Z]\d[^"]*)"[^>]*>(.*?)</a>',
                html,
                re.DOTALL | re.IGNORECASE,
            ):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 5:
                    continue
                rows.append(
                    {
                        "law_name": title,
                        "jurisdiction": "AU",
                        "article": article,
                        "text": f"{self.BASE_URL}{href}",
                        "theme": "legislation",
                        "_source": "auleg_search",
                    }
                )
                if len(rows) >= limit:
                    break

            if not rows:
                raise AdapterError(
                    f"No AU legislation results for '{q}'"
                )
            return rows

        return self._run_with_cache(cache_key, _fetch)
