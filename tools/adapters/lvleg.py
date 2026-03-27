"""Adapter for Latvian legislation via Likumi.lv."""
from __future__ import annotations

import re
from html import unescape
from typing import Any

from .base import AdapterError, BaseAdapter

_BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


class LVLegAdapter(BaseAdapter):
    """Latvian legislation adapter via Likumi.lv."""

    BASE_URL = "https://likumi.lv"

    def search_statutes(
        self, query: str, article: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")
        cache_key = f"lvleg:{q.lower()}:{article}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET", f"{self.BASE_URL}/",
                headers={"User-Agent": _BROWSER_UA},
            )
            rows: list[dict[str, Any]] = []
            # Match legislation links: /ta/id/NNNN-... or /ta/veids/... or /ta/tema/...
            for m in re.finditer(
                r'<a[^>]+href="(/ta/(?:id|veids|tema|saraksts|jaunakie)/[^"]+)"[^>]*>(.*?)</a>',
                html, re.DOTALL | re.IGNORECASE,
            ):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 3:
                    continue
                rows.append({
                    "law_name": title, "jurisdiction": "LV", "article": article,
                    "text": f"{self.BASE_URL}{href}", "theme": "legislation",
                    "_source": "likumi_lv",
                })
                if len(rows) >= limit:
                    break
            if not rows:
                raise AdapterError(f"No LV legislation results for '{q}'")
            return rows

        return self._run_with_cache(cache_key, _fetch)
