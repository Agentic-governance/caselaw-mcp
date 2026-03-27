"""Adapter for South African case law via SAFLII (saflii.org)."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

class ZALawAdapter(BaseAdapter):
    """South African case law adapter via SAFLII."""
    BASE_URL = "https://www.saflii.org"

    def search_cases(self, query: str, year_from: int | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q: raise AdapterError("Empty query")
        cache_key = f"zalaw:{q.lower()}:{year_from}:{limit}"
        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text("GET", self.BASE_URL + "/",
                headers={"User-Agent": "legal-mcp/1.0"})
            rows: list[dict[str, Any]] = []
            # SAFLII uses classic LII format: /za/cases/{COURT}/{year}/{num}.html
            for m in re.finditer(r'<a[^>]+href="(/za/cases/[^"]+\.html)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 5: continue
                court_m = re.search(r'/cases/([^/]+)/', href)
                court = court_m.group(1) if court_m else ""
                ym = re.search(r'/(\d{4})/', href)
                year = int(ym.group(1)) if ym else None
                if year_from and year and year < year_from: continue
                rows.append({"case_name": title, "jurisdiction": "ZA", "court": court,
                    "year": year, "result": "Unknown", "text": title,
                    "source_url": f"{self.BASE_URL}{href}", "domain": "external",
                    "keywords": [q], "_source": "saflii"})
                if len(rows) >= limit: break
            if not rows: raise AdapterError(f"No ZA case results for '{q}'")
            return rows
        return self._run_with_cache(cache_key, _fetch)
