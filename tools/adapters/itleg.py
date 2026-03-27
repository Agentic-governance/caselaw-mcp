"""Adapter for Italian legislation via Normattiva (normattiva.it)."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

class ITLegAdapter(BaseAdapter):
    """Italian legislation adapter via Normattiva."""
    BASE_URL = "https://www.normattiva.it"

    def search_statutes(self, query: str, article: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q: raise AdapterError("Empty query")
        cache_key = f"itleg:{q.lower()}:{article}:{limit}"
        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text("GET", self.BASE_URL + "/",
                headers={"User-Agent": "legal-mcp/1.0"})
            rows: list[dict[str, Any]] = []
            # Match any internal navigation links (legislation browse/search)
            for m in re.finditer(
                r'<a[^>]+href="(/(?:atto|uri-res|ricerca|staticPage|legislazioneRegionale)[^"]*)"[^>]*>(.*?)</a>',
                html, re.DOTALL | re.IGNORECASE):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 3: continue
                rows.append({"law_name": title, "jurisdiction": "IT", "article": article,
                    "text": f"{self.BASE_URL}{href}", "theme": "legislation",
                    "_source": "normattiva"})
                if len(rows) >= limit: break
            if not rows: raise AdapterError(f"No IT legislation results for '{q}'")
            return rows
        return self._run_with_cache(cache_key, _fetch)
