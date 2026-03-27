"""Adapter for ECHR case-law via HUDOC API."""

from __future__ import annotations

import re
from html import unescape
from typing import Any

from .base import AdapterError, BaseAdapter


class HUDOCAdapter(BaseAdapter):
    """ECHR case law adapter via HUDOC API."""

    SEARCH_URL = "https://hudoc.echr.coe.int/app/query/results"
    DOC_URL = "https://hudoc.echr.coe.int/app/conversion/docx/html/body"
    SELECT_FIELDS = "itemid,docname,applicability,ecli,conclusion,judgementdate,kpdate,respondent,typedescription,appno"

    @staticmethod
    def _html_to_text(html: str) -> str:
        # Remove <style> blocks and their content
        text = re.sub(r'<style[^>]*>.*?</style>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
        # Remove CSS class definitions that appear as raw text (e.g. .sXXX { ... })
        text = re.sub(r'\.[a-zA-Z0-9_]+\s*\{[^}]*\}', ' ', text)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        text = unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _fetch_doc_text(self, item_id: str) -> str:
        """Fetch full judgment text from HUDOC."""
        try:
            html = self._request_text(
                "GET",
                self.DOC_URL,
                params={"library": "ECHR", "id": item_id},
                headers={"User-Agent": "legal-mcp/1.0"},
            )
            return self._html_to_text(html)
        except Exception:
            return ""

    def search_cases(
        self,
        query: str,
        year_from: int | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        return self.search_with_text(query, max_results=limit, year_from=year_from)

    def search_with_text(
        self,
        query: str,
        max_results: int = 10,
        year_from: int | None = None,
    ) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")
        cache_key = f"hudoc:{q.lower()}:{year_from}:{max_results}"

        def _fetch() -> list[dict[str, Any]]:
            hudoc_query = f'contentsitename:ECHR AND "{q}"'
            payload = self._request_json(
                "GET",
                self.SEARCH_URL,
                params={
                    "query": hudoc_query,
                    "select": self.SELECT_FIELDS,
                    "sort": "kpdate Descending",
                    "start": "0",
                    "length": str(max_results),
                },
                headers={"User-Agent": "legal-mcp/1.0"},
            )

            results = payload.get("results", [])
            if not results:
                raise AdapterError("No HUDOC results")

            rows: list[dict[str, Any]] = []
            for item in results:
                cols = item.get("columns", {}) if isinstance(item, dict) else {}
                docname = cols.get("docname", "") or ""
                item_id = cols.get("itemid", "") or ""
                ecli = cols.get("ecli", "") or ""
                date = cols.get("judgementdate", "") or cols.get("kpdate", "") or ""
                conclusion = cols.get("conclusion", "") or ""
                respondent = cols.get("respondent", "") or ""
                appno = cols.get("appno", "") or ""

                year_match = re.search(r"\b(19|20)\d{2}\b", date)
                year = int(year_match.group(0)) if year_match else None

                if year_from is not None and isinstance(year, int) and year < year_from:
                    continue

                source_url = f"https://hudoc.echr.coe.int/eng?i={item_id}" if item_id else ""

                # Fetch full text for first few results
                text = ""
                if item_id and len(rows) < 3:
                    text = self._fetch_doc_text(item_id)
                    if len(text) > 5000:
                        text = text[:5000] + "..."

                rows.append(
                    {
                        "case_name": docname,
                        "jurisdiction": "ECHR",
                        "court": "European Court of Human Rights",
                        "year": year,
                        "result": conclusion[:300] if conclusion else "Unknown",
                        "text": text,
                        "source_url": source_url,
                        "summary": f"Application no. {appno}" if appno else (f"ECLI: {ecli}" if ecli else date),
                        "domain": "external",
                        "keywords": [respondent] if respondent else [],
                        "_source": "hudoc",
                    }
                )
            return rows

        return self._run_with_cache(cache_key, _fetch)
