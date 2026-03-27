"""Adapter for Polish legislation via ISAP (isap.sejm.gov.pl)."""
from __future__ import annotations

import re
from html import unescape
from typing import Any

from .base import AdapterError, BaseAdapter


class PLLegAdapter(BaseAdapter):
    """Polish legislation adapter via ISAP."""

    BASE_URL = "https://isap.sejm.gov.pl"
    SEARCH_URL = "https://isap.sejm.gov.pl/isap.nsf/ByKeyword.xsp"

    def search_statutes(
        self, query: str, article: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")
        cache_key = f"plleg:{q.lower()}:{article}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                self.SEARCH_URL,
                params={"keyword": q},
                headers={"User-Agent": "legal-mcp/1.0"},
            )
            rows: list[dict[str, Any]] = []
            for m in re.finditer(
                r'<a[^>]+href="(/isap.nsf/[^"]+)"[^>]*>(.*?)</a>',
                html, re.DOTALL | re.IGNORECASE,
            ):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 5:
                    continue
                rows.append({
                    "law_name": title, "jurisdiction": "PL", "article": article,
                    "text": f"{self.BASE_URL}{href}", "theme": "legislation",
                    "_source": "isap_pl",
                })
                if len(rows) >= limit:
                    break
            if not rows:
                raise AdapterError(f"No PL legislation results for '{q}'")
            return rows

        return self._run_with_cache(cache_key, _fetch)
