"""Adapter for New Zealand legislation via legislation.govt.nz."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class NZLegAdapter(BaseAdapter):
    """New Zealand legislation adapter."""
    BASE_URL = "https://www.legislation.govt.nz"

    def search_statutes(self, query: str, article: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q: raise AdapterError("Empty query")
        cache_key = f"nzleg:{q.lower()}:{article}:{limit}"
        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text("GET", self.BASE_URL + "/",
                headers={"User-Agent": BROWSER_UA})
            rows: list[dict[str, Any]] = []
            # Match act links: /act/public/{year}/{num}/latest/
            for m in re.finditer(r'<a[^>]+href="(/act/(?:public|imperial|local)/[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 5: continue
                rows.append({"law_name": title, "jurisdiction": "NZ", "article": article,
                    "text": f"{self.BASE_URL}{href}", "theme": "legislation", "_source": "nzleg"})
                if len(rows) >= limit: break
            if not rows: raise AdapterError(f"No NZ legislation results for '{q}'")
            return rows
        return self._run_with_cache(cache_key, _fetch)
