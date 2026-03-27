"""Adapter for Austrian federal legislation via RIS (ris.bka.gv.at)."""
from __future__ import annotations

import re
from html import unescape
from typing import Any

from .base import AdapterError, BaseAdapter


class ATLegAdapter(BaseAdapter):
    """Austrian federal legislation adapter via RIS search."""

    BASE_URL = "https://www.ris.bka.gv.at"
    SEARCH_URL = "https://www.ris.bka.gv.at/Ergebnis.wxe"

    def search_statutes(
        self, query: str, article: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")
        cache_key = f"atleg:{q.lower()}:{article}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                self.SEARCH_URL,
                params={"Abfrage": "Bundesnormen", "Suchworte": q, "ResultPageSize": "100"},
                headers={"User-Agent": "legal-mcp/1.0"},
            )
            rows: list[dict[str, Any]] = []
            for m in re.finditer(
                r'<a[^>]+href="(/eli/[^"]+)"[^>]*title="([^"]*)"',
                html, re.DOTALL | re.IGNORECASE,
            ):
                href, title = m.groups()
                title = unescape(title).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 5:
                    continue
                rows.append({
                    "law_name": title, "jurisdiction": "AT", "article": article,
                    "text": f"{self.BASE_URL}{href}", "theme": "legislation",
                    "_source": "ris_bka",
                })
                if len(rows) >= limit:
                    break
            if not rows:
                raise AdapterError(f"No AT legislation results for '{q}'")
            return rows

        return self._run_with_cache(cache_key, _fetch)
