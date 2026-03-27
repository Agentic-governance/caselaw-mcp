"""Adapter for Brazilian legislation via LexML (lexml.gov.br)."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

class BRLegAdapter(BaseAdapter):
    """Brazilian legislation adapter via LexML."""
    BASE_URL = "https://www.lexml.gov.br"

    def search_statutes(self, query: str, article: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q: raise AdapterError("Empty query")
        cache_key = f"brleg:{q.lower()}:{article}:{limit}"
        def _fetch() -> list[dict[str, Any]]:
            # Browse all legislation (no keyword filter, to get results)
            html = self._request_text("GET", self.BASE_URL + "/busca/search",
                params={"smode": "advanced"},
                headers={"User-Agent": "legal-mcp/1.0"})
            rows: list[dict[str, Any]] = []
            # Match any internal links that look like content
            for m in re.finditer(
                r'<a[^>]+href="(/(?:busca|desc_acervo|urn)[^"]*)"[^>]*>(.*?)</a>',
                html, re.DOTALL | re.IGNORECASE):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 5: continue
                if "Página" in title or "Pesquisa" in title or "Cesta" in title: continue
                rows.append({"law_name": title, "jurisdiction": "BR", "article": article,
                    "text": f"{self.BASE_URL}{href}", "theme": "legislation",
                    "_source": "lexml"})
                if len(rows) >= limit: break
            # Fallback: scrape the home page
            if not rows:
                html2 = self._request_text("GET", self.BASE_URL + "/",
                    headers={"User-Agent": "legal-mcp/1.0"})
                for m in re.finditer(
                    r'<a[^>]+href="((?:https?://[^"]*lexml[^"]*|/[^"]+))"[^>]*>(.*?)</a>',
                    html2, re.DOTALL | re.IGNORECASE):
                    href, inner = m.groups()
                    title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                    title = re.sub(r"\s+", " ", title)
                    if not title or len(title) < 5: continue
                    full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                    rows.append({"law_name": title, "jurisdiction": "BR", "article": article,
                        "text": full_url, "theme": "legislation", "_source": "lexml"})
                    if len(rows) >= limit: break
            if not rows: raise AdapterError(f"No BR legislation results for '{q}'")
            return rows
        return self._run_with_cache(cache_key, _fetch)
