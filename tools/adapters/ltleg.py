"""Adapter for Lithuanian legislation via e-TAR (e-tar.lt)."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

class LTLegAdapter(BaseAdapter):
    """Lithuanian legislation adapter via e-TAR."""
    BASE_URL = "https://www.e-tar.lt"

    def search_statutes(self, query: str, article: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q: raise AdapterError("Empty query")
        cache_key = f"ltleg:{q.lower()}:{article}:{limit}"
        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text("GET", self.BASE_URL + "/portal/",
                headers={"User-Agent": "legal-mcp/1.0"})
            rows: list[dict[str, Any]] = []
            # Match legalAct links: /portal/lt/legalAct/TAR.{hash}/asr
            for m in re.finditer(r'<a[^>]+href="([^"]*legalAct[^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 5: continue
                full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                rows.append({"law_name": title, "jurisdiction": "LT", "article": article,
                    "text": full_url, "theme": "legislation", "_source": "etar"})
                if len(rows) >= limit: break
            # Fallback: any portal links
            if not rows:
                for m in re.finditer(r'<a[^>]+href="(/portal/[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
                    href, inner = m.groups()
                    title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                    title = re.sub(r"\s+", " ", title)
                    if not title or len(title) < 5: continue
                    if "static" in href or "resource" in href: continue
                    rows.append({"law_name": title, "jurisdiction": "LT", "article": article,
                        "text": f"{self.BASE_URL}{href}", "theme": "legislation", "_source": "etar"})
                    if len(rows) >= limit: break
            if not rows: raise AdapterError(f"No LT legislation results for '{q}'")
            return rows
        return self._run_with_cache(cache_key, _fetch)
