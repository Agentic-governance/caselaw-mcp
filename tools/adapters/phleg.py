"""Adapter for Philippine case law via LawPhil (lawphil.net)."""
from __future__ import annotations
import re
from typing import Any
from .base import AdapterError, BaseAdapter

_BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


class PHLegAdapter(BaseAdapter):
    """Philippine case law adapter via LawPhil."""
    BASE_URL = "https://lawphil.net"

    def search_cases(self, query: str, year_from: int | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")
        cache_key = f"phleg:{q.lower()}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text("GET", f"{self.BASE_URL}/",
                headers={"User-Agent": _BROWSER_UA})
            rows: list[dict[str, Any]] = []
            # Parse <area> tags — title comes before href in lawphil HTML
            for m in re.finditer(
                r'<area[^>]+title="([^"]*)"[^>]+href="(https?://lawphil\.net/(?:statutes|judjuris|executive|judicial)[^"]*)"',
                html, re.IGNORECASE):
                title, href = m.groups()
                title = title.strip()
                if not title or len(title) < 3:
                    continue
                rows.append({"case_name": title, "jurisdiction": "PH",
                    "court": "", "year": None, "result": "Unknown",
                    "text": title, "source_url": href,
                    "domain": "external", "keywords": [q], "_source": "lawphil"})
                if len(rows) >= limit:
                    break
            if not rows:
                raise AdapterError(f"No PH case results for '{q}'")
            return rows

        return self._run_with_cache(cache_key, _fetch)
