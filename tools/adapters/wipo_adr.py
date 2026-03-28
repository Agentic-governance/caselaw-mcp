"""Adapter for WIPO AMC UDRP/domain dispute decisions."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import AdapterError, BaseAdapter


class WIPOADRAdapter(BaseAdapter):
    """WIPO ADR adapter via WIPO AMC decision search HTML."""

    SEARCH_URL = "https://www.wipo.int/amc/en/domains/search/"

    SEED = [
        {"indicator": "udrp_cases_filed", "description": "Total UDRP cases filed", "jurisdiction": "GLOBAL"},
        {"indicator": "udrp_cases_decided", "description": "UDRP cases with panel decision", "jurisdiction": "GLOBAL"},
        {"indicator": "udrp_transfer_rate", "description": "UDRP cases resulting in domain transfer (%)", "jurisdiction": "GLOBAL"},
        {"indicator": "udrp_denial_rate", "description": "UDRP complaints denied (%)", "jurisdiction": "GLOBAL"},
        {"indicator": "mediation_cases", "description": "WIPO mediation cases filed", "jurisdiction": "GLOBAL"},
        {"indicator": "expert_determination_cases", "description": "WIPO expert determination cases", "jurisdiction": "GLOBAL"},
        {"indicator": "arbitration_cases", "description": "WIPO arbitration cases filed", "jurisdiction": "GLOBAL"},
        {"indicator": "cctld_cases", "description": "ccTLD domain dispute cases", "jurisdiction": "GLOBAL"},
    ]

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

        cache_key = f"wipo_adr:{q}:{limit}"

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
                if not href:
                    continue
                if "/amc/en/domains/decisions/text/" not in href and "case no." not in anchor.get_text(" ", strip=True).lower():
                    continue

                case_name = self._clean(anchor.get_text(" ", strip=True))
                if not case_name:
                    continue
                parent = anchor.find_parent(["li", "tr", "div"])
                context = self._clean(parent.get_text(" ", strip=True) if parent else case_name)
                source_url = urljoin("https://www.wipo.int", href)
                if source_url in seen:
                    continue
                seen.add(source_url)

                rows.append(
                    {
                        "case_name": case_name,
                        "jurisdiction": "GLOBAL",
                        "court": "WIPO AMC",
                        "year": self._extract_year(context),
                        "text": context,
                        "source_url": source_url,
                        "_source": "wipo_adr",
                    }
                )
                if len(rows) >= limit:
                    break
            return rows

        return self._run_with_cache(cache_key, _fetch)
