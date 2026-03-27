"""Adapter for Malawian case law via MalawiLII (malawilii.org)."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

class MWLawAdapter(BaseAdapter):
    """Malawian case law adapter via MalawiLII."""
    BASE_URL = "https://malawilii.org"

    def search_cases(self, query: str, year_from: int | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q: raise AdapterError("Empty query")
        cache_key = f"mwlaw:{q.lower()}:{year_from}:{limit}"
        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text("GET", self.BASE_URL + "/", headers={"User-Agent": "legal-mcp/1.0"})
            rows: list[dict[str, Any]] = []
            for m in re.finditer(r'<a[^>]+href="(/akn/mw/judgment/[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 5: continue
                ym = re.search(r"(\d{4})", href)
                year = int(ym.group(1)) if ym else None
                if year_from and year and year < year_from: continue
                court = ""
                cm = re.search(r"/judgment/([a-z]+)/", href)
                if cm: court = cm.group(1).upper()
                rows.append({"case_name": title, "jurisdiction": "MW", "court": court,
                    "year": year, "result": "Unknown", "text": title,
                    "source_url": f"{self.BASE_URL}{href}", "domain": "external",
                    "keywords": [q], "_source": "malawilii"})
                if len(rows) >= limit: break
            if not rows: raise AdapterError(f"No MW case results for '{q}'")
            return rows
        return self._run_with_cache(cache_key, _fetch)
