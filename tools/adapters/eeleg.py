"""Adapter for Estonian legislation via Riigi Teataja (riigiteataja.ee)."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

class EELegAdapter(BaseAdapter):
    """Estonian legislation adapter via Riigi Teataja."""
    BASE_URL = "https://www.riigiteataja.ee"

    def search_statutes(self, query: str, article: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q: raise AdapterError("Empty query")
        cache_key = f"eeleg:{q.lower()}:{article}:{limit}"
        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text("GET", self.BASE_URL + "/en/",
                headers={"User-Agent": "legal-mcp/1.0"})
            rows: list[dict[str, Any]] = []
            # Match full ELI URLs (absolute) on the page
            for m in re.finditer(
                r'<a[^>]+href="(https?://www\.riigiteataja\.ee/en/eli/[^"]+)"[^>]*>(.*?)</a>',
                html, re.DOTALL | re.IGNORECASE):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 5: continue
                rows.append({"law_name": title, "jurisdiction": "EE", "article": article,
                    "text": href, "theme": "legislation", "_source": "riigiteataja"})
                if len(rows) >= limit: break
            # Also try relative /en/eli/ paths
            if not rows:
                for m in re.finditer(
                    r'<a[^>]+href="(/en/eli/[^"]+)"[^>]*>(.*?)</a>',
                    html, re.DOTALL | re.IGNORECASE):
                    href, inner = m.groups()
                    title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                    title = re.sub(r"\s+", " ", title)
                    if not title or len(title) < 5: continue
                    rows.append({"law_name": title, "jurisdiction": "EE", "article": article,
                        "text": f"{self.BASE_URL}{href}", "theme": "legislation",
                        "_source": "riigiteataja"})
                    if len(rows) >= limit: break
            # Final fallback: any /en/ links that aren't utility pages
            if not rows:
                for m in re.finditer(r'<a[^>]+href="(/en/[^"]+)"[^>]*>(.*?)</a>',
                    html, re.DOTALL | re.IGNORECASE):
                    href, inner = m.groups()
                    if any(skip in href for skip in ["faq", "feedback", "register", "password", "statistics", "search", "embed"]): continue
                    title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                    title = re.sub(r"\s+", " ", title)
                    if not title or len(title) < 5: continue
                    rows.append({"law_name": title, "jurisdiction": "EE", "article": article,
                        "text": f"{self.BASE_URL}{href}", "theme": "legislation",
                        "_source": "riigiteataja"})
                    if len(rows) >= limit: break
            if not rows: raise AdapterError(f"No EE legislation results for '{q}'")
            return rows
        return self._run_with_cache(cache_key, _fetch)
