"""Adapter for Portuguese case law via DGSI (dgsi.pt)."""
from __future__ import annotations

import re
from html import unescape
from typing import Any

from .base import AdapterError, BaseAdapter

_BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


class PTLegAdapter(BaseAdapter):
    """Portuguese case law adapter via DGSI (Supreme Court)."""

    BASE_URL = "https://www.dgsi.pt"
    # Supreme Court (STJ) recent decisions
    LIST_URL = "https://www.dgsi.pt/jstj.nsf/954f0ce6ad9dd8b980256b5f003fa814"

    def search_cases(
        self, query: str, year_from: int | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")
        cache_key = f"ptleg:{q.lower()}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET", f"{self.LIST_URL}?OpenView",
                headers={"User-Agent": _BROWSER_UA},
            )
            rows: list[dict[str, Any]] = []

            # Parse case links: /jstj.nsf/{view}/{docid}?Open → case ref number
            for m in re.finditer(
                r'<a[^>]+href="(/jstj\.nsf/[^"]+\?Open[^"]*)"[^>]*>(.*?)</a>',
                html, re.DOTALL | re.IGNORECASE,
            ):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 3:
                    continue
                # Skip navigation links
                if title.lower() in ("anterior", "seguinte", "expand", "collapse"):
                    continue

                # Extract year from case reference (e.g., "259/25.0YREVR.S1")
                year_m = re.search(r"/(\d{2})\.", title)
                year = None
                if year_m:
                    yr2 = int(year_m.group(1))
                    year = 2000 + yr2 if yr2 < 50 else 1900 + yr2

                if year_from and year and year < year_from:
                    continue

                source_url = f"{self.BASE_URL}{href}"

                rows.append({
                    "case_name": title,
                    "jurisdiction": "PT",
                    "court": "Supremo Tribunal de Justiça",
                    "year": year,
                    "result": "Unknown",
                    "text": title,
                    "source_url": source_url,
                    "domain": "external",
                    "keywords": [q],
                    "_source": "dgsi_pt",
                })
                if len(rows) >= limit:
                    break

            if not rows:
                raise AdapterError(f"No PT case results for '{q}'")
            return rows

        return self._run_with_cache(cache_key, _fetch)
