"""Adapter for ITC Section 337 investigations via USITC EDIS HTML pages."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import AdapterError, BaseAdapter


class ITC337Adapter(BaseAdapter):
    """ITC Section 337 adapter via EDIS search page scraping."""

    SEARCH_URL = "https://edis.usitc.gov/external/search"

    @staticmethod
    def _clean(text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    @staticmethod
    def _extract_year(text: str) -> int | None:
        match = re.search(r"\b(19|20)\d{2}\b", text)
        if match:
            return int(match.group(0))
        return None

    def search_disputes(self, query: str, limit: int = 10, **kwargs: Any) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")

        cache_key = f"itc337:{q}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                self.SEARCH_URL,
                params={"q": q},
                headers={"User-Agent": "legal-mcp/1.0"},
            )
            soup = BeautifulSoup(html, "lxml")

            rows: list[dict[str, Any]] = []
            seen: set[str] = set()

            for anchor in soup.select("a[href]"):
                href = anchor.get("href", "").strip()
                label = self._clean(anchor.get_text(" ", strip=True))
                if not href or not label:
                    continue
                if "337" not in label and "investigation" not in label.lower() and "337" not in href:
                    continue

                parent_text = self._clean(anchor.find_parent(["tr", "li", "div"]).get_text(" ", strip=True) if anchor.find_parent(["tr", "li", "div"]) else label)
                case_name = label if "inv." in label.lower() or "337" in label else parent_text
                source_url = urljoin("https://edis.usitc.gov", href)

                if source_url in seen:
                    continue
                seen.add(source_url)

                rows.append(
                    {
                        "case_name": case_name,
                        "jurisdiction": "US",
                        "court": "ITC",
                        "year": self._extract_year(parent_text),
                        "text": parent_text,
                        "source_url": source_url,
                        "_source": "itc337",
                    }
                )
                if len(rows) >= limit:
                    break

            return rows

        return self._run_with_cache(cache_key, _fetch)
