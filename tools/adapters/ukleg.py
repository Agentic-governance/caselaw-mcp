"""Adapter for UK legislation via legislation.gov.uk."""
from __future__ import annotations

import re
from html import unescape
from typing import Any

from .base import AdapterError, BaseAdapter

_BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


class UKLegAdapter(BaseAdapter):
    """UK legislation adapter via legislation.gov.uk."""

    BASE_URL = "https://www.legislation.gov.uk"

    def search_statutes(
        self, query: str, article: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")
        cache_key = f"ukleg:{q.lower()}:{article}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            # Fetch recent years' Act index (2020-2025)
            rows: list[dict[str, Any]] = []
            q_lower = q.lower()

            for year in range(2025, 2019, -1):
                if len(rows) >= limit:
                    break
                try:
                    html = self._request_text(
                        "GET", f"{self.BASE_URL}/ukpga/{year}",
                        headers={"User-Agent": _BROWSER_UA},
                    )
                except AdapterError:
                    continue

                for m in re.finditer(
                    r'<a[^>]+href="(/ukpga/\d+/\d+/contents)"[^>]*>(.*?)</a>',
                    html, re.DOTALL | re.IGNORECASE,
                ):
                    href, inner = m.groups()
                    title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                    title = re.sub(r"\s+", " ", title)
                    if not title or len(title) < 5:
                        continue
                    # Skip chapter number duplicates (e.g., "2024 c. 25")
                    if re.match(r"^\d{4}\s+c\.\s+\d+$", title):
                        continue
                    if q_lower not in title.lower():
                        continue
                    rows.append({
                        "law_name": title,
                        "jurisdiction": "GB",
                        "article": article,
                        "text": title,
                        "source_url": f"{self.BASE_URL}{href}",
                        "theme": "legislation",
                        "_source": "legislation_gov_uk",
                    })
                    if len(rows) >= limit:
                        break

            if not rows:
                # Fallback: fetch latest year index without query filter
                html = self._request_text(
                    "GET", f"{self.BASE_URL}/ukpga/2025",
                    headers={"User-Agent": _BROWSER_UA},
                )
                for m in re.finditer(
                    r'<a[^>]+href="(/ukpga/\d+/\d+/contents)"[^>]*>(.*?)</a>',
                    html, re.DOTALL | re.IGNORECASE,
                ):
                    href, inner = m.groups()
                    title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                    title = re.sub(r"\s+", " ", title)
                    if not title or len(title) < 5:
                        continue
                    if re.match(r"^\d{4}\s+c\.\s+\d+$", title):
                        continue
                    rows.append({
                        "law_name": title,
                        "jurisdiction": "GB",
                        "article": article,
                        "text": title,
                        "source_url": f"{self.BASE_URL}{href}",
                        "theme": "legislation",
                        "_source": "legislation_gov_uk",
                    })
                    if len(rows) >= limit:
                        break

            if not rows:
                raise AdapterError(f"No UK legislation results for '{q}'")
            return rows

        return self._run_with_cache(cache_key, _fetch)
