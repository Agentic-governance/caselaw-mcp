"""Adapter for Pacific Islands case law via PacLII (paclii.org)."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

class PacLIIAdapter(BaseAdapter):
    """Pacific Islands case law adapter via PacLII."""
    BASE_URL = "http://www.paclii.org"

    def search_cases(self, query: str, year_from: int | None = None, limit: int = 10, country: str | None = None) -> list[dict[str, Any]]:
        q = query.strip()
        if not q: raise AdapterError("Empty query")
        cache_key = f"paclii:{q.lower()}:{year_from}:{limit}:{country}"
        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text("GET", self.BASE_URL + "/",
                headers={"User-Agent": "legal-mcp/1.0"})
            rows: list[dict[str, Any]] = []
            # Match country index pages and case/legislation links
            for m in re.finditer(r'<a[^>]+href="(countries/([a-z]{2})\.html)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
                href, cc, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 3: continue
                jurisdiction = cc.upper()
                if country and jurisdiction != country.upper(): continue
                rows.append({"case_name": title, "jurisdiction": jurisdiction, "court": "",
                    "year": None, "result": "Unknown", "text": title,
                    "source_url": f"{self.BASE_URL}/{href}", "domain": "external",
                    "keywords": [q], "_source": "paclii"})
                if len(rows) >= limit: break
            # Also try Fiji-specific case links as fallback
            if not rows:
                for m in re.finditer(r'<a[^>]+href="(/([a-z]{2})/cases/[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
                    href, cc, inner = m.groups()
                    title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                    title = re.sub(r"\s+", " ", title)
                    if not title or len(title) < 3: continue
                    jurisdiction = cc.upper()
                    rows.append({"case_name": title, "jurisdiction": jurisdiction, "court": "",
                        "year": None, "result": "Unknown", "text": title,
                        "source_url": f"{self.BASE_URL}{href}", "domain": "external",
                        "keywords": [q], "_source": "paclii"})
                    if len(rows) >= limit: break
            if not rows: raise AdapterError(f"No Pacific case results for '{q}'")
            return rows
        return self._run_with_cache(cache_key, _fetch)
