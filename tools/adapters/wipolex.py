"""Adapter for WIPO Lex statute/treaty search via external API."""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import urljoin

from .base import AdapterError, BaseAdapter


class WIPOLexAdapter(BaseAdapter):
    """IP statutes and treaties adapter via WIPO Lex via external API."""

    SEARCH_URL = "https://www.wipo.int/wipolex/en/results.jsp"

    def _parse_wipo_html(self, html: str, query: str) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        matches = list(
            re.finditer(
                r'<a[^>]+(?:class="[^"]*(?:result|resultTitle|title)[^"]*"[^>]*href="([^"]+)"|href="([^"]+)"[^>]*class="[^"]*(?:result|resultTitle|title)[^"]*")[^>]*>(.*?)</a>',
                html,
                re.IGNORECASE | re.DOTALL,
            )
        )
        if not matches:
            matches = list(
                re.finditer(
                    r'<h[23][^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?</h[23]>',
                    html,
                    re.IGNORECASE | re.DOTALL,
                )
            )

        for match in matches:
            groups = match.groups()
            href = groups[0] or (groups[1] if len(groups) > 2 else "")
            inner = groups[-1]
            title = unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", inner))).strip()
            if not title:
                continue

            full_url = urljoin("https://www.wipo.int", href)
            country_match = re.search(r"/([A-Z]{2})/", full_url.upper())
            country = country_match.group(1) if country_match else "WIPO"
            year_match = re.search(r"\b(19|20)\d{2}\b", html[match.start() : match.start() + 500])
            year = int(year_match.group(0)) if year_match else None

            rows.append(
                {
                    "case_name": title,
                    "jurisdiction": "WIPO",
                    "court": "WIPO Lex",
                    "year": year,
                    "result": "Treaty/Statute",
                    "summary": full_url,
                    "domain": "external",
                    "keywords": [query.lower(), country],
                    "_source": "wipolex",
                }
            )
        return rows

    def search_statutes(
        self,
        query: str,
        year_from: int | None = None,
        limit: int = 10,
        article: str | None = None,
    ) -> list[dict[str, object]]:
        q = query.strip()
        article_q = (article or "").strip().lower()
        cache_key = f"wipolex:{q.lower()}:{year_from}:{article_q}:{limit}"

        def _fetch() -> list[dict[str, object]]:
            html = self._request_text(
                "GET",
                self.SEARCH_URL,
                params={
                    "task": "search",
                    "search_text": q,
                    "search_lang": "en",
                },
                headers={"User-Agent": "legal-mcp/1.0"},
            )
            rows = self._parse_wipo_html(html, q)
            if year_from is not None:
                rows = [row for row in rows if row.get("year") is None or int(row["year"]) >= year_from]
            if article_q:
                rows = [
                    row
                    for row in rows
                    if article_q in str(row.get("case_name", "")).lower()
                    or article_q in str(row.get("summary", "")).lower()
                ]
            if not rows:
                raise AdapterError("No WIPO Lex results")
            return rows[:limit]

        return self._run_with_cache(cache_key, _fetch)
