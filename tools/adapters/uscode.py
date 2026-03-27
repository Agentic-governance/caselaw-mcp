"""Adapter for United States Code search."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from .base import AdapterError, BaseAdapter


class USCodeAdapter(BaseAdapter):
    """US Code adapter via uscode.house.gov search pages."""

    HOUSE_BASE = "https://uscode.house.gov"
    HOUSE_SEARCH = "https://uscode.house.gov/search.xhtml"
    HOUSE_QUICKSEARCH = "https://uscode.house.gov/quicksearch/get.plx"
    CORNELL_BASE = "https://www.law.cornell.edu"

    @staticmethod
    def _clean(text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    @staticmethod
    def _extract_article(text: str) -> str | None:
        match = re.search(r"(§+\s*\d+[A-Za-z0-9\-]*)", text)
        if match:
            return match.group(1)
        match = re.search(r"\bsection\s+(\d+[A-Za-z0-9\-]*)", text, re.IGNORECASE)
        if match:
            return f"Section {match.group(1)}"
        return None

    def _parse_html_results(self, html: str, limit: int) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()

        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "").strip()
            if not href:
                continue
            if "/view.xhtml" not in href and "/uscode/text/" not in href:
                continue

            law_name = self._clean(anchor.get_text(" ", strip=True))
            if not law_name:
                continue

            parent = anchor.find_parent(["li", "tr", "div"])
            context = self._clean(parent.get_text(" ", strip=True) if parent else law_name)
            article = self._extract_article(context) or self._extract_article(law_name)
            source_url = urljoin(self.HOUSE_BASE, href)

            if source_url in seen:
                continue
            seen.add(source_url)

            rows.append(
                {
                    "law_name": law_name,
                    "jurisdiction": "US",
                    "article": article,
                    "text": context,
                    "source_url": source_url,
                    "_source": "uscode",
                }
            )
            if len(rows) >= limit:
                break

        return rows

    def search_statutes(self, query: str, limit: int = 10, **kwargs: Any) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")

        cache_key = f"uscode:{q}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            headers = {"User-Agent": "legal-mcp/1.0"}

            # Primary: uscode.house.gov search endpoint.
            try:
                html = self._request_text(
                    "GET",
                    self.HOUSE_SEARCH,
                    params={"query": q},
                    headers=headers,
                )
                rows = self._parse_html_results(html, limit)
                if rows:
                    return rows
            except AdapterError:
                pass

            # Fallback: older quicksearch endpoint.
            try:
                html = self._request_text(
                    "GET",
                    self.HOUSE_QUICKSEARCH,
                    params={"query": q},
                    headers=headers,
                )
                rows = self._parse_html_results(html, limit)
                if rows:
                    return rows
            except AdapterError:
                pass

            # Last fallback: Cornell direct search URL.
            source_url = f"{self.CORNELL_BASE}/search/site/{quote_plus(q)}"
            return [
                {
                    "law_name": f"US Code search for {q}",
                    "jurisdiction": "US",
                    "article": None,
                    "text": f"Search results page for query: {q}",
                    "source_url": source_url,
                    "_source": "uscode",
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
