"""Adapter for GIPC (US Chamber) International IP Index.

Scrapes the US Chamber of Commerce GIPC landing page and the
latest IP Index page for edition information, report links,
and country IP framework assessment metadata.
"""
from __future__ import annotations

import re
from html import unescape
from typing import Any
from urllib.parse import urljoin

from .base import AdapterError, BaseAdapter


class GIPCIndexAdapter(BaseAdapter):
    """US Chamber GIPC International IP Index adapter.

    Fetches the GIPC program page to find IP Index edition links,
    then parses the latest edition page for report metadata.
    The IP Index evaluates 55 economies using 53 indicators.
    """

    # theglobalipcenter.com redirects to uschamber.com
    GIPC_URL = "https://www.uschamber.com/program/global-innovation-policy-center"
    LATEST_INDEX_URL = "https://www.uschamber.com/intellectual-property/2025-ip-index"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "GLOBAL",
        year_from: int | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        cache_key = f"gipc:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            rows: list[dict[str, Any]] = []
            q_norm = query.strip().lower()

            # Step 1: Fetch GIPC landing page for IP Index edition links
            try:
                gipc_html = self._request_text(
                    "GET",
                    self.GIPC_URL,
                    headers={"User-Agent": "legal-mcp/1.0"},
                )
            except AdapterError:
                gipc_html = ""

            # Extract IP Index edition URLs from the GIPC landing page
            # Pattern: href="https://www.uschamber.com/intellectual-property/YYYY-ip-index"
            index_link_re = re.compile(
                r'href="(https?://www\.uschamber\.com/intellectual-property/(\d{4})-ip-index)"',
                flags=re.IGNORECASE,
            )
            seen_years: set[int] = set()
            for match in index_link_re.finditer(gipc_html):
                url, year_str = match.groups()
                year = int(year_str)
                if year in seen_years:
                    continue
                seen_years.add(year)

                if year_from and year < year_from:
                    continue

                title = f"{year} International IP Index"
                if q_norm and q_norm not in title.lower():
                    continue

                rows.append(
                    {
                        "indicator": "gipc_ip_index_edition",
                        "jurisdiction": jurisdiction.upper(),
                        "year": year,
                        "value": 1.0,
                        "unit": "index_edition",
                        "source": "gipc_index",
                        "title": title,
                        "note": f"{title} | {url}",
                        "url": url,
                    }
                )

            # Step 2: Fetch the latest IP Index page for detailed metadata
            try:
                index_html = self._request_text(
                    "GET",
                    self.LATEST_INDEX_URL,
                    headers={"User-Agent": "legal-mcp/1.0"},
                )
            except AdapterError:
                index_html = ""

            if index_html:
                # Extract edition info from meta tags
                edition_match = re.search(
                    r'<title>(.*?)</title>',
                    index_html,
                    re.IGNORECASE | re.DOTALL,
                )
                edition_title = ""
                if edition_match:
                    edition_title = unescape(
                        re.sub(r"\s+", " ", edition_match.group(1))
                    ).strip()

                # Extract description from meta
                desc_match = re.search(
                    r'<meta\s+name="description"\s+content="(.*?)"',
                    index_html,
                    re.IGNORECASE,
                )
                description = ""
                if desc_match:
                    description = unescape(desc_match.group(1)).strip()

                # Add a detailed entry for the latest edition
                if edition_title:
                    if not q_norm or q_norm in edition_title.lower() or q_norm in description.lower():
                        # Avoid duplicate if we already have this year
                        latest_year_match = re.search(r"(20\d{2})", edition_title)
                        latest_year = int(latest_year_match.group(1)) if latest_year_match else 2025
                        if not (year_from and latest_year < year_from):
                            if latest_year not in seen_years:
                                rows.insert(
                                    0,
                                    {
                                        "indicator": "gipc_ip_index_edition",
                                        "jurisdiction": jurisdiction.upper(),
                                        "year": latest_year,
                                        "value": 1.0,
                                        "unit": "index_edition",
                                        "source": "gipc_index",
                                        "title": edition_title,
                                        "note": f"{description} | {self.LATEST_INDEX_URL}",
                                        "url": self.LATEST_INDEX_URL,
                                    },
                                )
                                seen_years.add(latest_year)

                # Extract any references to country data or indicators
                # Look for number patterns like "55 economies" or "53 indicators"
                stats_patterns = [
                    (r"(\d+)\s+econom", "economies_evaluated"),
                    (r"(\d+)\s+indicator", "indicators_used"),
                ]
                for pattern, stat_name in stats_patterns:
                    stat_match = re.search(pattern, index_html, re.IGNORECASE)
                    if stat_match:
                        stat_value = int(stat_match.group(1))
                        stat_title = f"GIPC IP Index - {stat_value} {stat_name.replace('_', ' ')}"
                        if not q_norm or q_norm in stat_title.lower():
                            rows.append(
                                {
                                    "indicator": f"gipc_{stat_name}",
                                    "jurisdiction": jurisdiction.upper(),
                                    "year": 2025,
                                    "value": float(stat_value),
                                    "unit": stat_name,
                                    "source": "gipc_index",
                                    "title": stat_title,
                                    "note": f"From {self.LATEST_INDEX_URL}",
                                    "url": self.LATEST_INDEX_URL,
                                },
                            )

            if not rows:
                raise AdapterError(
                    "No GIPC IP Index data found; both GIPC pages may be inaccessible"
                )
            return rows[:limit]

        return self._run_with_cache(cache_key, _fetch)
