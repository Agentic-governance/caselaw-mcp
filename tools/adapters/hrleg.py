"""Adapter for Croatian legislation via Zakon.hr."""
from __future__ import annotations

import re
from html import unescape
from typing import Any

from .base import AdapterError, BaseAdapter

_BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


class HRLegAdapter(BaseAdapter):
    """Croatian legislation adapter."""

    BASE_URL = "https://www.zakon.hr"

    def search_statutes(
        self, query: str, article: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")
        cache_key = f"hrleg:{q.lower()}:{article}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET", f"{self.BASE_URL}/",
                headers={"User-Agent": _BROWSER_UA},
            )
            rows: list[dict[str, Any]] = []
            # Match law links: /z/NNNN/law-name
            for m in re.finditer(
                r'<a[^>]+href="((?:https?://www\.zakon\.hr)?/z/\d+/[^"]+)"[^>]*>(.*?)</a>',
                html, re.DOTALL | re.IGNORECASE,
            ):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 5:
                    continue
                full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                rows.append({
                    "law_name": title, "jurisdiction": "HR", "article": article,
                    "text": full_url, "theme": "legislation",
                    "_source": "zakon_hr",
                })
                if len(rows) >= limit:
                    break
            if not rows:
                raise AdapterError(f"No HR legislation results for '{q}'")
            return rows

        return self._run_with_cache(cache_key, _fetch)
