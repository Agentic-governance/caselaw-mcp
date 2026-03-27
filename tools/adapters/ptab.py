"""Adapter for USPTO PTAB proceedings API."""

from __future__ import annotations

from typing import Any

from .base import AdapterError, BaseAdapter


class PTABAdapter(BaseAdapter):
    """PTAB adapter backed by the USPTO developer proceedings API."""

    BASE_URL = "https://developer.uspto.gov/ptab-api/proceedings"

    @staticmethod
    def _extract_year(value: Any) -> int | None:
        text = str(value or "").strip()
        if len(text) >= 4 and text[:4].isdigit():
            return int(text[:4])
        return None

    @staticmethod
    def _pick(item: dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = item.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return ""

    def search_disputes(self, query: str, limit: int = 10, **kwargs: Any) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")

        patent_number = kwargs.get("patent_number")
        party_name = kwargs.get("party_name")
        filing_date = kwargs.get("filing_date")

        if not patent_number and not party_name:
            if any(ch.isdigit() for ch in q):
                patent_number = q
            else:
                party_name = q

        cache_key = f"ptab:{q}:{patent_number}:{party_name}:{filing_date}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            params: dict[str, Any] = {}
            if patent_number:
                params["patent_number"] = patent_number
            if party_name:
                params["party_name"] = party_name
            if filing_date:
                params["filing_date"] = filing_date

            payload = self._request_json(
                "GET",
                self.BASE_URL,
                params=params,
                headers={"User-Agent": "legal-mcp/1.0", "Accept": "application/json"},
            )

            if isinstance(payload, list):
                items = payload
            elif isinstance(payload, dict):
                items = (
                    payload.get("proceedings")
                    or payload.get("results")
                    or payload.get("items")
                    or payload.get("data")
                    or []
                )
            else:
                items = []

            rows: list[dict[str, Any]] = []
            for item in items:
                if not isinstance(item, dict):
                    continue

                case_name = self._pick(
                    item,
                    "case_name",
                    "proceeding_title",
                    "proceeding_number",
                    "application_number",
                )
                if not case_name:
                    proc_no = self._pick(item, "proceeding_number", "proceedingNumber", "trial_number")
                    patent_no = self._pick(item, "patent_number", "patentNumber")
                    case_name = " - ".join(part for part in (proc_no, patent_no) if part) or "PTAB Proceeding"

                status = self._pick(item, "result", "disposition", "status", "proceeding_status")
                decision = self._pick(item, "decision_type", "trial_type")
                filing = self._pick(item, "filing_date", "filingDate", "decision_date", "decisionDate")
                year = self._extract_year(filing)
                detail_url = self._pick(item, "url", "detail_url", "document_url", "proceeding_url") or self.BASE_URL

                text = " | ".join(part for part in (decision, status, filing) if part) or case_name

                rows.append(
                    {
                        "case_name": case_name,
                        "jurisdiction": "US",
                        "court": "PTAB",
                        "year": year,
                        "result": status or decision or "Unknown",
                        "text": text,
                        "source_url": detail_url,
                        "_source": "ptab",
                    }
                )
                if len(rows) >= limit:
                    break
            return rows

        return self._run_with_cache(cache_key, _fetch)
