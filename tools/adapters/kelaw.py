"""Adapter for Kenyan case law via Kenya Law (kenyalaw.org)."""
from __future__ import annotations

import re
from html import unescape
from typing import Any

from .base import AdapterError, BaseAdapter


class KELawAdapter(BaseAdapter):
    """Kenyan case law adapter via Kenya Law."""

    BASE_URL = "https://new.kenyalaw.org"
    SEARCH_URL = "https://new.kenyalaw.org/judgments/"

    def search_cases(
        self, query: str, year_from: int | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")
        cache_key = f"kelaw:{q.lower()}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET", self.SEARCH_URL,
                params={"q": q},
                headers={"User-Agent": "legal-mcp/1.0"},
            )
            rows: list[dict[str, Any]] = []
            for m in re.finditer(
                r'<a[^>]+href="(/judgments/[^"]+)"[^>]*>(.*?)</a>',
                html, re.DOTALL | re.IGNORECASE,
            ):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 5:
                    continue
                ctx = html[max(0, m.start()-200):min(len(html), m.end()+200)]
                year_m = re.search(r"\b(19|20)\d{2}\b", ctx)
                year = int(year_m.group(0)) if year_m else None
                if year_from and year and year < year_from:
                    continue
                rows.append({
                    "case_name": title, "jurisdiction": "KE",
                    "court": "", "year": year, "result": "Unknown",
                    "text": title, "source_url": f"{self.BASE_URL}{href}",
                    "domain": "external", "keywords": [q],
                    "_source": "kenyalaw",
                })
                if len(rows) >= limit:
                    break
            if not rows:
                raise AdapterError(f"No KE case results for '{q}'")
            return rows

        return self._run_with_cache(cache_key, _fetch)
