"""Adapter for Canadian federal legislation via laws-lois.justice.gc.ca."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

class CALegAdapter(BaseAdapter):
    """Canadian federal legislation adapter via HTTP fetch."""
    BASE_URL = "https://laws-lois.justice.gc.ca"

    def search_statutes(self, query: str, article: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q: raise AdapterError("Empty query")
        cache_key = f"caleg:{q.lower()}:{article}:{limit}"
        def _fetch() -> list[dict[str, Any]]:
            # Fetch the main English page which links to acts/regulations
            html = self._request_text("GET", f"{self.BASE_URL}/eng/",
                headers={"User-Agent": "legal-mcp/1.0"})
            all_rows: list[dict[str, Any]] = []
            q_lower = q.lower()
            # Match act links
            for m in re.finditer(
                r'<a[^>]+href="(/eng/(?:acts|regulations|Const|AnnualStatutes)/[^"]+)"[^>]*>(.*?)</a>',
                html, re.IGNORECASE | re.DOTALL):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 3 or title.startswith("PDF"): continue
                all_rows.append({"law_name": title, "jurisdiction": "CA", "article": article,
                    "text": f"{self.BASE_URL}{href}", "theme": "legislation",
                    "_source": "caleg_index"})
            # Filter by query if possible
            matched = [r for r in all_rows if q_lower in r["law_name"].lower()]
            result = matched[:limit] if matched else all_rows[:limit]
            if not result: raise AdapterError(f"No CA legislation results for '{q}'")
            return result
        return self._run_with_cache(cache_key, _fetch)
