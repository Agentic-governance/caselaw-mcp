"""Adapter for Turkish legislation via Mevzuat (mevzuat.gov.tr)."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

class TRLegAdapter(BaseAdapter):
    """Turkish legislation adapter via Mevzuat."""
    BASE_URL = "https://www.mevzuat.gov.tr"

    def search_statutes(self, query: str, article: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q: raise AdapterError("Empty query")
        cache_key = f"trleg:{q.lower()}:{article}:{limit}"
        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text("GET", self.BASE_URL + "/",
                headers={"User-Agent": "legal-mcp/1.0"})
            rows: list[dict[str, Any]] = []
            # Match MevzuatMetin links and legislation links
            for m in re.finditer(r'<a[^>]+href="([^"]*(?:MevzuatMetin|mevzuat\?|Publications)[^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 3: continue
                full_url = href if href.startswith("http") else f"{self.BASE_URL}/{href.lstrip('/')}"
                rows.append({"law_name": title, "jurisdiction": "TR", "article": article,
                    "text": full_url, "theme": "legislation", "_source": "mevzuat"})
                if len(rows) >= limit: break
            if not rows: raise AdapterError(f"No TR legislation results for '{q}'")
            return rows
        return self._run_with_cache(cache_key, _fetch)
