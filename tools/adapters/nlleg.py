"""Adapter for Dutch case law via Rechtspraak Open Data API."""
from __future__ import annotations

import re
from typing import Any
from xml.etree import ElementTree as ET

from .base import AdapterError, BaseAdapter


class NLLegAdapter(BaseAdapter):
    """Dutch case law adapter via Rechtspraak Open Data (Atom/XML API)."""

    API_URL = "https://data.rechtspraak.nl/uitspraken/zoeken"

    def search_cases(
        self, query: str, year_from: int | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")
        cache_key = f"nlleg:{q.lower()}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            params: dict[str, Any] = {
                "q": q,
                "max": str(min(limit, 50)),
                "return": "DOC",
            }
            if year_from:
                params["date"] = f"{year_from}-01-01"

            xml_text = self._request_text(
                "GET", self.API_URL,
                params=params,
                headers={"User-Agent": "legal-mcp/1.0"},
            )

            # Parse Atom XML
            try:
                root = ET.fromstring(xml_text.encode("utf-8"))
            except ET.ParseError as exc:
                raise AdapterError("Invalid XML from Rechtspraak API") from exc

            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", ns)

            if not entries:
                raise AdapterError(f"No NL case results for '{q}'")

            rows: list[dict[str, Any]] = []
            for entry in entries[:limit]:
                ecli = ""
                ecli_el = entry.find("atom:id", ns)
                if ecli_el is not None and ecli_el.text:
                    ecli = ecli_el.text.strip()

                title = ""
                title_el = entry.find("atom:title", ns)
                if title_el is not None and title_el.text:
                    title = title_el.text.strip()

                summary = ""
                summary_el = entry.find("atom:summary", ns)
                if summary_el is not None and summary_el.text:
                    summary = summary_el.text.strip()

                updated = ""
                updated_el = entry.find("atom:updated", ns)
                if updated_el is not None and updated_el.text:
                    updated = updated_el.text.strip()

                source_url = ""
                link_el = entry.find("atom:link[@rel='alternate']", ns)
                if link_el is not None:
                    source_url = link_el.get("href", "")

                # Extract year from ECLI or updated date
                year = None
                year_m = re.search(r"\b(19|20)\d{2}\b", ecli + " " + updated)
                if year_m:
                    year = int(year_m.group(0))

                # Extract court from title (format: "ECLI:NL:COURT:YEAR:ID, Court Name, ...")
                court = ""
                if ", " in title:
                    parts = title.split(", ")
                    if len(parts) >= 2:
                        court = parts[1].strip()

                rows.append({
                    "case_name": title,
                    "jurisdiction": "NL",
                    "court": court,
                    "year": year,
                    "result": "Unknown",
                    "text": summary if summary != "-" else title,
                    "source_url": source_url,
                    "summary": ecli,
                    "domain": "external",
                    "keywords": [q],
                    "_source": "rechtspraak_nl",
                })

            return rows

        return self._run_with_cache(cache_key, _fetch)
