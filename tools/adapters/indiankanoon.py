"""Adapter for Indian case law via Indian Kanoon web search.

OPERATIONAL NOTE:
- Primary: Web search at https://indiankanoon.org/search/ (no auth required)
- Secondary: API at https://api.indiankanoon.org/search/ (requires INDIAN_KANOON_TOKEN)
- robots.txt allows /search/ (only /cached/ and specific /doc/ pages disallowed)
"""
from __future__ import annotations

import os
import re
from html import unescape
from typing import Any

from .base import AdapterError, BaseAdapter


class IndianKanoonAdapter(BaseAdapter):
    """Indian case law adapter via Indian Kanoon web search / API.

    Primary path: HTML scraping of indiankanoon.org/search/
    Secondary path: API (if INDIAN_KANOON_TOKEN is set)
    """

    # Public web search (no auth required, returns HTML)
    WEB_SEARCH_URL = "https://indiankanoon.org/search/"
    # Official API (requires token auth)
    API_SEARCH_URL = "https://api.indiankanoon.org/search/"
    # Base URL for document links
    DOC_BASE_URL = "https://indiankanoon.org"

    def __init__(self, api_token: str = "", **kwargs):
        super().__init__(**kwargs)
        self.api_token = api_token or os.getenv("INDIAN_KANOON_TOKEN", "")

    # ------------------------------------------------------------------
    # HTML parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_html(text: str) -> str:
        """Strip HTML tags and normalize whitespace."""
        plain = re.sub(r"<[^>]+>", " ", text)
        plain = unescape(plain)
        return re.sub(r"\s+", " ", plain).strip()

    @staticmethod
    def _extract_year(text: str) -> int | None:
        """Extract a 4-digit year from text."""
        m = re.search(r"\b(19|20)\d{2}\b", text)
        return int(m.group(0)) if m else None

    @staticmethod
    def _extract_doc_id(href: str) -> str:
        """Extract numeric doc ID from /doc/XXXXX/ or /docfragment/XXXXX/ paths."""
        m = re.search(r"/(?:doc|docfragment)/(\d+)/", href)
        return m.group(1) if m else ""

    # ------------------------------------------------------------------
    # Document text fetching
    # ------------------------------------------------------------------

    def _fetch_doc_text(self, doc_url: str) -> str:
        """Fetch judgment text from an Indian Kanoon document page."""
        try:
            html = self._request_text(
                "GET", doc_url, headers={"User-Agent": "legal-mcp/1.0"},
            )
            # Judgment text is in <pre> tags
            parts: list[str] = []
            for m in re.finditer(r"<pre[^>]*>(.*?)</pre>", html, re.DOTALL):
                text = self._clean_html(m.group(1))
                if len(text) > 50:
                    parts.append(text)
            full = "\n".join(parts)
            if len(full) > 5000:
                full = full[:5000] + "..."
            return full
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Primary: Web search (HTML parsing)
    # ------------------------------------------------------------------

    def _parse_web_results(self, html: str, query: str) -> list[dict[str, Any]]:
        """Parse Indian Kanoon HTML search results into structured records.

        HTML structure per result:
            <article class="result">
              <h4 class="result_title">
                <a href="/docfragment/XXXXX/?formInput=...">Case Name on DD Month, YYYY</a>
              </h4>
              <div class="headline">Snippet text...</div>
              <div class="hlbottom">
                <span class="docsource">Court Name</span>
                ...
              </div>
            </article>
        """
        rows: list[dict[str, Any]] = []

        # Split on <article class="result"> boundaries
        articles = re.split(r'<article\s+class="result"', html)

        for article in articles[1:]:  # skip content before first article
            # Extract title link from <h4 class="result_title">
            title_match = re.search(
                r'<h4\s+class="result_title">\s*'
                r'(?:\[.*?\]\s*)?'  # optional [Section] prefix
                r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>',
                article,
                flags=re.DOTALL,
            )
            if not title_match:
                continue

            href = title_match.group(1)
            raw_title = title_match.group(2)
            title = self._clean_html(raw_title)
            if not title:
                continue

            doc_id = self._extract_doc_id(href)

            # Extract headline/snippet
            headline_match = re.search(
                r'<div\s+class="headline">(.*?)</div>',
                article,
                flags=re.DOTALL,
            )
            headline = ""
            if headline_match:
                headline = self._clean_html(headline_match.group(1))[:300]

            # Extract court from <span class="docsource">
            court_match = re.search(
                r'<span\s+class="docsource">(.*?)</span>',
                article,
                flags=re.DOTALL,
            )
            court = self._clean_html(court_match.group(1)) if court_match else ""

            # Extract year from title (e.g., "on 18 August, 1978")
            year = self._extract_year(title)

            # Build doc URL
            doc_url = f"{self.DOC_BASE_URL}/doc/{doc_id}/" if doc_id else ""

            rows.append({
                "case_name": title,
                "jurisdiction": "IN",
                "court": court,
                "year": year,
                "result": "Unknown",
                "summary": headline or f"Doc ID: {doc_id}",
                "url": doc_url,
                "domain": "external",
                "keywords": [t for t in query.lower().split() if t],
                "_source": "indiankanoon_web",
            })

        return rows

    def _fetch_web(self, query: str, year_from: int | None, limit: int) -> list[dict[str, Any]]:
        """Fetch results via web search (primary path)."""
        html = self._request_text(
            "GET",
            self.WEB_SEARCH_URL,
            params={"formInput": query},
            headers={"User-Agent": "legal-mcp/1.0"},
        )
        rows = self._parse_web_results(html, query)
        if year_from is not None:
            rows = [r for r in rows if r.get("year") is None or r["year"] >= year_from]
        rows = rows[:limit]

        # Fetch full text for first few results
        for row in rows[:3]:
            doc_url = row.get("url", "")
            if doc_url:
                row["text"] = self._fetch_doc_text(doc_url)
                row["source_url"] = doc_url

        return rows

    # ------------------------------------------------------------------
    # Secondary: API (requires INDIAN_KANOON_TOKEN)
    # ------------------------------------------------------------------

    def _parse_api_response(self, payload: dict) -> list[dict[str, Any]]:
        """Parse Indian Kanoon API JSON response."""
        docs = payload.get("docs", []) or []
        rows = []
        for doc in docs:
            title = doc.get("title", "") or ""
            title = unescape(re.sub(r"<[^>]+>", "", title)).strip()
            tid = doc.get("tid") or ""
            date = doc.get("publishdate") or doc.get("judgmentdate") or ""
            year = self._extract_year(date + " " + title)
            court = doc.get("docsource", "") or ""
            headline = doc.get("headline", "") or ""
            headline = unescape(re.sub(r"<[^>]+>", " ", headline)).strip()[:300]
            doc_url = f"{self.DOC_BASE_URL}/doc/{tid}/" if tid else ""
            rows.append({
                "case_name": title,
                "jurisdiction": "IN",
                "court": court,
                "year": year,
                "result": "Unknown",
                "summary": headline or f"Doc ID: {tid}",
                "url": doc_url,
                "domain": "external",
                "keywords": [],
                "_source": "indiankanoon_api",
            })
        return rows

    def _fetch_api(self, query: str, year_from: int | None, limit: int) -> list[dict[str, Any]]:
        """Fetch results via API (secondary path, requires token)."""
        headers = {
            "User-Agent": "legal-mcp/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Token {self.api_token}",
        }
        resp = self._request_json(
            "POST",
            self.API_SEARCH_URL,
            params={"formInput": query, "pagenum": "0"},
            headers=headers,
        )
        rows = self._parse_api_response(resp)
        if year_from is not None:
            rows = [r for r in rows if r.get("year") is None or r["year"] >= year_from]
        return rows[:limit]

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search_cases(
        self,
        query: str,
        year_from: int | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search Indian case law.

        Strategy:
            1. If INDIAN_KANOON_TOKEN is set, try the API first (richer metadata).
            2. Otherwise (or on API failure), use web search HTML parsing.
            3. If both fail, raise AdapterError.

        Args:
            query: Search keywords (e.g., 'copyright infringement')
            year_from: Filter cases from this year onwards
            limit: Maximum results to return

        Returns:
            List of case metadata dicts.
        """
        q = query.strip()
        cache_key = f"indiankanoon:{q.lower()}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            errors: list[str] = []

            # Strategy: API first if token available, then web fallback
            if self.api_token:
                try:
                    rows = self._fetch_api(q, year_from, limit)
                    if rows:
                        return rows
                except (AdapterError, Exception) as exc:
                    errors.append(f"API: {exc}")

            # Primary / fallback: web search
            try:
                rows = self._fetch_web(q, year_from, limit)
                if rows:
                    return rows
            except (AdapterError, Exception) as exc:
                errors.append(f"Web: {exc}")

            raise AdapterError(
                f"Indian Kanoon: no results. Errors: {'; '.join(errors) or 'empty results'}"
            )

        return self._run_with_cache(cache_key, _fetch)
