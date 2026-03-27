"""Adapter for ICJ (International Court of Justice) case law."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

class ICJAdapter(BaseAdapter):
    """ICJ case law adapter with HTML scraping."""
    LIST_URL = "https://www.icj-cij.org/index.php/list-of-all-cases"
    BASE_URL = "https://www.icj-cij.org"

    def search_cases(self, query: str, year_from: int | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")
        cache_key = f"icj:{q.lower()}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text("GET", self.LIST_URL, headers={"User-Agent": "legal-mcp/1.0"})

            # Parse case entries from the list page - <td> elements with case names
            # and links like href="case/199"
            q_lower = q.lower()
            rows: list[dict[str, Any]] = []

            # ICJ list page: <a href="case/N"><p>Case Title</p></a> inside <td>
            for m in re.finditer(r'<a[^>]+href="(case/\d+)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
                href, inner = m.groups()
                title = unescape(re.sub(r'<[^>]+>', ' ', inner)).strip()
                title = re.sub(r'\s+', ' ', title)
                if not title or len(title) < 10:
                    continue
                if q_lower not in title.lower():
                    continue

                source_url = f"{self.BASE_URL}/{href}"

                # Look for year in surrounding context (date column next to case name)
                context = html[m.start():min(len(html), m.end() + 300)]
                year_m = re.search(r'\b(19|20)\d{2}\b', context)
                year = int(year_m.group(0)) if year_m else None
                if year_from is not None and isinstance(year, int) and year < year_from:
                    continue

                rows.append({
                    "case_name": title,
                    "jurisdiction": "ICJ",
                    "court": "International Court of Justice",
                    "year": year,
                    "result": "Unknown",
                    "text": title,
                    "source_url": source_url,
                    "summary": href,
                    "domain": "international law",
                    "keywords": [q],
                    "_source": "icj_html",
                })
                if len(rows) >= limit:
                    break

            if not rows:
                raise AdapterError("No ICJ results matching query")
            return rows

        return self._run_with_cache(cache_key, _fetch)
