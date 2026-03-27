"""Adapter for Malaysian legislation via CommonLII (commonlii.org/my)."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

class MYLawAdapter(BaseAdapter):
    """Malaysian legislation adapter via CommonLII."""
    BASE_URL = "https://www.commonlii.org"

    def search_cases(self, query: str, year_from: int | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q: raise AdapterError("Empty query")
        cache_key = f"mylaw:{q.lower()}:{year_from}:{limit}"
        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text("GET", self.BASE_URL + "/my/",
                headers={"User-Agent": "legal-mcp/1.0"})
            rows: list[dict[str, Any]] = []
            # CommonLII uses /my/legis/{type}/ and /my/cases/{court}/ patterns
            for m in re.finditer(r'<a[^>]+href="(/my/(?:legis|cases|journals|other)/[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 3: continue
                rows.append({"case_name": title, "jurisdiction": "MY", "court": "",
                    "year": None, "result": "Unknown", "text": title,
                    "source_url": f"{self.BASE_URL}{href}", "domain": "external",
                    "keywords": [q], "_source": "commonlii"})
                if len(rows) >= limit: break
            if not rows: raise AdapterError(f"No MY case results for '{q}'")
            return rows
        return self._run_with_cache(cache_key, _fetch)
