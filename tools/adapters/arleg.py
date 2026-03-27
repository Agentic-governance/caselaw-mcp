"""Adapter for Argentine legislation via InfoLEG (infoleg.gob.ar)."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

class ARLegAdapter(BaseAdapter):
    """Argentine legislation adapter via InfoLEG."""
    BASE_URL = "https://www.infoleg.gob.ar"

    def search_statutes(self, query: str, article: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q: raise AdapterError("Empty query")
        cache_key = f"arleg:{q.lower()}:{article}:{limit}"
        def _fetch() -> list[dict[str, Any]]:
            # Try the WordPress home page
            html = self._request_text("GET", self.BASE_URL + "/",
                headers={"User-Agent": "legal-mcp/1.0"})
            rows: list[dict[str, Any]] = []
            # Match any legislation-related links
            for m in re.finditer(
                r'<a[^>]+href="([^"]*(?:infolegInternet|norma|ley|decreto|resolucion|page_id)[^"]*)"[^>]*>(.*?)</a>',
                html, re.DOTALL | re.IGNORECASE):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 5: continue
                full_url = href if href.startswith("http") else f"{self.BASE_URL}/{href.lstrip('/')}"
                rows.append({"law_name": title, "jurisdiction": "AR", "article": article,
                    "text": full_url, "theme": "legislation", "_source": "infoleg_ar"})
                if len(rows) >= limit: break
            if not rows: raise AdapterError(f"No AR legislation results for '{q}'")
            return rows
        return self._run_with_cache(cache_key, _fetch)
