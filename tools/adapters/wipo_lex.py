"""Adapter for WIPO Lex legislation database."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import AdapterError, BaseAdapter


class WIPOLexAdapter(BaseAdapter):
    """WIPO Lex adapter using HTML search results from legislation pages."""

    SEARCH_URL = "https://www.wipo.int/wipolex/en/legislation/"

    @staticmethod
    def _clean(text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    @staticmethod
    def _extract_jurisdiction(text: str) -> str:
        match = re.search(r"\b([A-Z]{2,3})\b", text)
        if match:
            return match.group(1)
        return "GLOBAL"

    def search_statutes(self, query: str, limit: int = 10, **kwargs: Any) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")

        cache_key = f"wipo_lex:{q}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                self.SEARCH_URL,
                params={"query": q},
                headers={"User-Agent": "legal-mcp/1.0"},
            )
            soup = BeautifulSoup(html, "lxml")

            rows: list[dict[str, Any]] = []
            seen: set[str] = set()

            for anchor in soup.select("a[href]"):
                href = anchor.get("href", "").strip()
                if "/wipolex/en/text/" not in href and "/wipolex/en/legislation/details/" not in href:
                    continue

                law_name = self._clean(anchor.get_text(" ", strip=True))
                if not law_name:
                    continue

                parent = anchor.find_parent(["li", "tr", "div", "article"])
                context = self._clean(parent.get_text(" ", strip=True) if parent else law_name)
                source_url = urljoin("https://www.wipo.int", href)
                if source_url in seen:
                    continue
                seen.add(source_url)

                rows.append(
                    {
                        "law_name": law_name,
                        "jurisdiction": self._extract_jurisdiction(context),
                        "text": context,
                        "source_url": source_url,
                        "_source": "wipo_lex",
                    }
                )
                if len(rows) >= limit:
                    break
            return rows

        return self._run_with_cache(cache_key, _fetch)
