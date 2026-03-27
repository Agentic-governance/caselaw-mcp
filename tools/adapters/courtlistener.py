"""Adapter for U.S. CourtListener search API (v4)."""

from __future__ import annotations

from typing import Any

from .base import AdapterError, BaseAdapter


class CourtListenerAdapter(BaseAdapter):
    """Fetch and normalize case-law data from CourtListener v4 API.

    Note: Full opinion text requires API authentication.
    Without auth, only search snippets (~350 chars) are available.
    """

    API_URL = "https://www.courtlistener.com/api/rest/v4/search/"
    BASE_URL = "https://www.courtlistener.com"

    @staticmethod
    def _to_year(date_text: str | None) -> int | None:
        if not date_text:
            return None
        if len(date_text) >= 4 and date_text[:4].isdigit():
            return int(date_text[:4])
        return None

    def search_cases(self, query: str, year_from: int | None = None, limit: int = 10) -> list[dict[str, Any]]:
        filed_after = f"{year_from:04d}-01-01" if year_from is not None else None
        return self.search_with_text(query, max_results=limit, filed_after=filed_after)

    def search_with_text(self, query: str, max_results: int = 10, filed_after: str | None = None) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")
        cache_key = f"courtlistener:search:{q}:{filed_after}:{max_results}"

        def _fetch() -> list[dict[str, Any]]:
            params: dict[str, Any] = {
                "type": "o",
                "q": q,
                "format": "json",
            }
            if filed_after:
                params["filed_after"] = filed_after

            payload = self._request_json("GET", self.API_URL, params=params)

            if not isinstance(payload, dict):
                raise AdapterError("Unexpected CourtListener response")

            results = payload.get("results", [])
            if not isinstance(results, list):
                raise AdapterError("Unexpected CourtListener results format")

            if not results:
                raise AdapterError("No CourtListener results")

            rows: list[dict[str, Any]] = []
            for item in results[:max_results]:
                if not isinstance(item, dict):
                    continue
                case_name = item.get("caseName") or item.get("caseNameFull") or ""
                court = item.get("court") or item.get("court_citation_string") or ""
                absolute_url = item.get("absolute_url", "")
                source_url = f"{self.BASE_URL}{absolute_url}" if absolute_url else ""
                filed = item.get("dateFiled")
                docket_number = item.get("docketNumber", "")

                # Extract all available text (without auth, only snippets are available)
                text_parts = []
                # Case metadata
                if case_name:
                    text_parts.append(case_name)
                if court:
                    text_parts.append(f"Court: {court}")
                if filed:
                    text_parts.append(f"Filed: {filed}")
                if docket_number:
                    text_parts.append(f"Docket: {docket_number}")
                # Opinion snippets (main content)
                opinions = item.get("opinions", [])
                for op in opinions:
                    snippet = op.get("snippet", "")
                    if snippet:
                        text_parts.append(snippet.strip())

                text = "\n".join(text_parts)

                rows.append(
                    {
                        "case_name": case_name,
                        "jurisdiction": "US",
                        "court": court,
                        "year": self._to_year(str(filed) if filed else None),
                        "result": docket_number,
                        "text": text,
                        "source_url": source_url,
                        "domain": "external",
                        "keywords": [token for token in q.lower().split() if token],
                        "_source": "courtlistener_search_api",
                    }
                )
            return rows

        return self._run_with_cache(cache_key, _fetch)
