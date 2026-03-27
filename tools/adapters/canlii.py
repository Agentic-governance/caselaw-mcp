"""Case-law and legislation adapter for Canada via CanLII REST API.

OPERATIONAL NOTE:
- Official REST API documentation: https://github.com/canlii/API_documentation
- Requires API key from CanLII (request via feedback form: https://www.canlii.org/en/info/api.html)
- Authentication: x-api-key header
- Rate limits: Max 10MB per transfer, HTTPS required
"""

from __future__ import annotations

import os
import re
from typing import Any

from .base import AdapterError, BaseAdapter

class CanLIIAdapter(BaseAdapter):
    """Canadian case law and legislation adapter via CanLII REST API.

    Official API: https://api.canlii.org/v1/
    Supported operations:
    - Case browsing by database
    - Individual case metadata retrieval
    - Legislation browsing
    - Individual legislation retrieval

    Popular databases:
    - scc: Supreme Court of Canada
    - onca: Ontario Court of Appeal
    - fct: Federal Court (Trial Division)
    - bcca: British Columbia Court of Appeal
    """

    API_BASE = "https://api.canlii.org/v1"

    def __init__(self, api_key: str = "", **kwargs: Any):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("CANLII_API_KEY", "")

    def _get_headers(self) -> dict[str, str]:
        """Build request headers with API key if configured."""
        headers = {"User-Agent": "legal-mcp/1.0"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def list_databases(self, language: str = "en") -> list[dict[str, str]]:
        """List all available case law databases.

        Args:
            language: "en" or "fr"

        Returns:
            List of databases with databaseId and name.
        """
        if not self.api_key:
            raise AdapterError("CanLII API key not configured - set CANLII_API_KEY")

        url = f"{self.API_BASE}/caseBrowse/{language}/"
        try:
            resp = self._request_json("GET", url, headers=self._get_headers())
            databases = resp.get("databases", [])
            return [{"databaseId": db.get("databaseId"), "name": db.get("name")} for db in databases if db]
        except Exception as exc:
            raise AdapterError(f"Failed to list CanLII databases: {exc}")

    def search_cases(
        self,
        query: str = "",
        database_id: str | None = None,
        decision_date_from: str | None = None,
        decision_date_to: str | None = None,
        offset: int = 0,
        limit: int = 10,
        language: str = "en",
    ) -> list[dict[str, Any]]:
        """Search Canadian case law.

        Args:
            query: Search keyword (optional - can browse all if empty)
            database_id: Database to search (e.g., "scc", "onca"). If None, searches all.
            decision_date_from: Filter by decision date (ISO format YYYY-MM-DD)
            decision_date_to: Filter by decision date (ISO format YYYY-MM-DD)
            offset: Pagination offset
            limit: Max results (CanLII max: 200)
            language: "en" or "fr"

        Returns:
            List of case metadata.
        """
        cache_key = f"canlii_cases:{query.lower()}:{database_id}:{decision_date_from}:{offset}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            if not self.api_key:
                raise AdapterError("CanLII API key not configured - set CANLII_API_KEY")

            # Build URL: if database_id specified, use caseBrowse/{lang}/{db}, else use search
            if database_id:
                url = f"{self.API_BASE}/caseBrowse/{language}/{database_id}/"
            else:
                # Use first available database (scc)
                url = f"{self.API_BASE}/caseBrowse/{language}/scc/"

            params: dict[str, Any] = {
                "offset": offset,
                "resultCount": min(limit, 200),  # CanLII max
            }

            if decision_date_from:
                params["changedAfter"] = decision_date_from
            if decision_date_to:
                params["changedBefore"] = decision_date_to

            try:
                resp = self._request_json("GET", url, params=params, headers=self._get_headers())
            except Exception as exc:
                raise AdapterError(f"CanLII API request failed: {exc}")

            cases = resp.get("cases", [])
            rows: list[dict[str, Any]] = []

            for c in cases:
                if not isinstance(c, dict):
                    continue

                case_name = c.get("title") or c.get("caseName") or c.get("caseId", {}).get("en", "") or ""
                citation = c.get("citation") or ""
                docket = c.get("docketNumber") or ""
                date_str = c.get("decisionDate") or ""

                # Parse year
                year = None
                m = re.search(r"\b(19|20)\d{2}\b", str(date_str))
                if m:
                    year = int(m.group(0))

                # Filter by query if provided
                if query:
                    haystack = f"{case_name} {citation} {docket}".lower()
                    if query.lower() not in haystack:
                        continue

                rows.append(
                    {
                        "case_name": case_name,
                        "jurisdiction": "CA",
                        "court": database_id or "scc",
                        "year": year,
                        "result": "Unknown",
                        "summary": citation or docket or "",
                        "domain": "external",
                        "keywords": [query.lower()] if query else [],
                        "_source": "canlii_api",
                        "_canlii_case_id": c.get("caseId", {}),
                        "_canlii_url": c.get("url", ""),
                    }
                )

            if not rows and not query:
                # If no query and no results, might be API issue
                raise AdapterError("No CanLII results returned")

            return rows[:limit]

        return self._run_with_cache(cache_key, _fetch)

    def get_case_detail(
        self, database_id: str, case_id: str, language: str = "en"
    ) -> dict[str, Any] | None:
        """Retrieve detailed metadata for a specific case.

        Args:
            database_id: Database code (e.g., "scc", "onca")
            case_id: Case identifier (e.g., "2008scc9")
            language: "en" or "fr"

        Returns:
            Case metadata dict or None if failed.
        """
        if not self.api_key:
            return None

        url = f"{self.API_BASE}/caseBrowse/{language}/{database_id}/{case_id}/"

        try:
            resp = self._request_json("GET", url, headers=self._get_headers())
            return resp
        except Exception:
            return None

    def search_legislation(
        self,
        query: str = "",
        database_id: str | None = None,
        offset: int = 0,
        limit: int = 10,
        language: str = "en",
    ) -> list[dict[str, Any]]:
        """Search Canadian legislation.

        Args:
            query: Search keyword
            database_id: Legislation database (e.g., "ca", "on", "bc")
            offset: Pagination offset
            limit: Max results
            language: "en" or "fr"

        Returns:
            List of legislation metadata.
        """
        cache_key = f"canlii_legislation:{query.lower()}:{database_id}:{offset}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            if not self.api_key:
                raise AdapterError("CanLII API key not configured - set CANLII_API_KEY")

            # Use federal legislation as default
            db = database_id or "ca"
            url = f"{self.API_BASE}/legislationBrowse/{language}/{db}/"

            params: dict[str, Any] = {
                "offset": offset,
                "resultCount": min(limit, 200),
            }

            try:
                resp = self._request_json("GET", url, params=params, headers=self._get_headers())
            except Exception as exc:
                raise AdapterError(f"CanLII legislation API failed: {exc}")

            legislations = resp.get("legislations", [])
            rows: list[dict[str, Any]] = []

            for leg in legislations:
                if not isinstance(leg, dict):
                    continue

                title = leg.get("title") or leg.get("name") or ""
                citation = leg.get("citation") or ""

                # Filter by query if provided
                if query:
                    haystack = f"{title} {citation}".lower()
                    if query.lower() not in haystack:
                        continue

                rows.append(
                    {
                        "law_name": title,
                        "jurisdiction": "CA",
                        "citation": citation,
                        "type": leg.get("type", "statute"),
                        "_source": "canlii_api",
                        "_canlii_legislation_id": leg.get("legislationId", {}),
                        "_canlii_url": leg.get("url", ""),
                    }
                )

            return rows[:limit]

        return self._run_with_cache(cache_key, _fetch)

    def get_legislation_detail(
        self, database_id: str, legislation_id: str, language: str = "en"
    ) -> dict[str, Any] | None:
        """Retrieve detailed metadata for specific legislation.

        Args:
            database_id: Legislation database (e.g., "ca", "on")
            legislation_id: Legislation identifier
            language: "en" or "fr"

        Returns:
            Legislation metadata dict or None if failed.
        """
        if not self.api_key:
            return None

        url = f"{self.API_BASE}/legislationBrowse/{language}/{database_id}/{legislation_id}/"

        try:
            resp = self._request_json("GET", url, headers=self._get_headers())
            return resp
        except Exception:
            return None
