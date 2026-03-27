"""Adapter for Ethiopian legal information via ethiopianlaw.com (WordPress)."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

_BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


class ETLawAdapter(BaseAdapter):
    """Ethiopian law adapter via ethiopianlaw.com."""
    BASE_URL = "https://ethiopianlaw.com"

    def search_statutes(
        self,
        query: str,
        year_from: int | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")
        cache_key = f"etlaw:{q.lower()}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                f"{self.BASE_URL}/",
                params={"s": q},
                headers={"User-Agent": _BROWSER_UA},
            )
            rows: list[dict[str, Any]] = []

            # WordPress search results: h-tags wrapping links inside articles
            for m in re.finditer(
                r'<h\d[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                html,
                re.DOTALL | re.IGNORECASE,
            ):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 10:
                    continue
                if not href.startswith(self.BASE_URL):
                    continue
                # Skip non-article pages (practice areas, navigation, etc.)
                _skip = ("/practice-areas/", "/our-firm/", "/contact-us/",
                         "/insight/", "/news/", "/page/")
                if any(s in href for s in _skip):
                    continue

                # Extract year from proclamation references
                year = None
                ym = re.search(r'(?:Proclamation\s+No\.?\s*\d+/)(\d{4})', title, re.IGNORECASE)
                if ym:
                    year = int(ym.group(1))
                else:
                    ym = re.search(r'\b(20\d{2}|19\d{2})\b', title)
                    if ym:
                        year = int(ym.group(1))
                if year_from and year and year < year_from:
                    continue

                # Try to fetch a snippet from the article
                text = title
                try:
                    detail = self._request_text(
                        "GET", href,
                        headers={"User-Agent": _BROWSER_UA},
                    )
                    # Extract article content
                    entry = re.search(
                        r'<div[^>]*class="[^"]*entry-content[^"]*"[^>]*>(.*?)</div>',
                        detail,
                        re.DOTALL | re.IGNORECASE,
                    )
                    if entry:
                        snippet = re.sub(r"<[^>]+>", " ", entry.group(1)).strip()
                        snippet = re.sub(r"\s+", " ", snippet)[:400]
                        text = f"{title} — {snippet}"
                except AdapterError:
                    pass

                rows.append({
                    "law_name": title,
                    "jurisdiction": "ET",
                    "source": "ethiopianlaw.com",
                    "year": year,
                    "text": text,
                    "source_url": href,
                    "domain": "external",
                    "keywords": [q],
                    "_source": "ethiopianlaw",
                })
                if len(rows) >= limit:
                    break

            if not rows:
                raise AdapterError(f"No ET law results for '{q}'")
            return rows

        return self._run_with_cache(cache_key, _fetch)
