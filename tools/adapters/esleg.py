"""Adapter for Spanish legislation via BOE codigos (boe.es)."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

class ESLegAdapter(BaseAdapter):
    """Spanish legislation adapter via BOE."""
    BASE_URL = "https://www.boe.es"

    def search_statutes(self, query: str, article: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q: raise AdapterError("Empty query")
        cache_key = f"esleg:{q.lower()}:{article}:{limit}"
        def _fetch() -> list[dict[str, Any]]:
            # BOE codigos page has legislation categories
            html = self._request_text("GET",
                self.BASE_URL + "/biblioteca_juridica/codigos/abrir_pdf.php",
                headers={"User-Agent": "legal-mcp/1.0"})
            rows: list[dict[str, Any]] = []
            # Try codigos listing first
            for m in re.finditer(
                r'<a[^>]+href="([^"]*(?:codigo|abrir_pdf|act\.php|buscar/doc)[^"]*)"[^>]*>(.*?)</a>',
                html, re.DOTALL | re.IGNORECASE):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 5: continue
                full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                rows.append({"law_name": title, "jurisdiction": "ES", "article": article,
                    "text": full_url, "theme": "legislation", "_source": "boe"})
                if len(rows) >= limit: break
            # Fallback: try the main BOE page
            if not rows:
                html2 = self._request_text("GET", self.BASE_URL + "/",
                    headers={"User-Agent": "legal-mcp/1.0"})
                for m in re.finditer(
                    r'<a[^>]+href="(/(?:diario_boe|buscar|eli|biblioteca_juridica)/[^"]+)"[^>]*>(.*?)</a>',
                    html2, re.DOTALL | re.IGNORECASE):
                    href, inner = m.groups()
                    title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                    title = re.sub(r"\s+", " ", title)
                    if not title or len(title) < 5: continue
                    rows.append({"law_name": title, "jurisdiction": "ES", "article": article,
                        "text": f"{self.BASE_URL}{href}", "theme": "legislation", "_source": "boe"})
                    if len(rows) >= limit: break
            if not rows: raise AdapterError(f"No ES legislation results for '{q}'")
            return rows
        return self._run_with_cache(cache_key, _fetch)
