"""Adapter for German case law via dejure.org."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from urllib.parse import quote
from .base import AdapterError, BaseAdapter

_BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# Dejure.org court codes → full names
_COURT_NAMES = {
    "BGH": "Bundesgerichtshof",
    "BVerfG": "Bundesverfassungsgericht",
    "BVerwG": "Bundesverwaltungsgericht",
    "BAG": "Bundesarbeitsgericht",
    "BFH": "Bundesfinanzhof",
    "BSG": "Bundessozialgericht",
    "BPatG": "Bundespatentgericht",
    "OLG": "Oberlandesgericht",
    "LG": "Landgericht",
    "AG": "Amtsgericht",
    "EuGH": "Europäischer Gerichtshof",
}


class DELawAdapter(BaseAdapter):
    """German case law adapter via dejure.org."""
    BASE_URL = "https://dejure.org"

    def search_cases(
        self,
        query: str,
        year_from: int | None = None,
        limit: int = 10,
        court: str | None = None,
    ) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")
        cache_key = f"delaw:{q.lower()}:{year_from}:{limit}:{court}"

        def _fetch() -> list[dict[str, Any]]:
            params = f"Text={quote(q, safe='')}"
            if court:
                params += f"&Gericht={quote(court, safe='')}"
            search_url = f"{self.BASE_URL}/dienste/rechtsprechung?{params}"

            html = self._request_text(
                "GET", search_url,
                headers={"User-Agent": _BROWSER_UA},
            )

            rows: list[dict[str, Any]] = []

            # Parse judgment links: /dienste/vernetzung/rechtsprechung?Gericht=...&Datum=...&Aktenzeichen=...
            for m in re.finditer(
                r'<a[^>]+href="(/dienste/vernetzung/rechtsprechung\?[^"]+)"[^>]*>(.*?)</a>',
                html,
                re.DOTALL | re.IGNORECASE,
            ):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 5:
                    continue

                # Parse court, date, case number from the title
                # Format: "BGH, 19.02.2026 - IX ZR 226/22"
                parts = re.match(
                    r'([A-Za-z]+),?\s+(\d{2}\.\d{2}\.\d{4})\s*-\s*(.*)',
                    title,
                )
                ct = ""
                date_str = ""
                case_nr = ""
                year = None
                if parts:
                    ct = parts.group(1)
                    date_str = parts.group(2)
                    case_nr = parts.group(3).strip()
                    ym = re.search(r'(\d{4})', date_str)
                    if ym:
                        year = int(ym.group(1))

                if year_from and year and year < year_from:
                    continue

                court_name = _COURT_NAMES.get(ct, ct)
                source_url = f"{self.BASE_URL}{unescape(href)}"

                rows.append({
                    "case_name": title,
                    "jurisdiction": "DE",
                    "court": court_name,
                    "year": year,
                    "date": date_str,
                    "case_number": case_nr,
                    "result": "Unknown",
                    "text": title,
                    "source_url": source_url,
                    "domain": "external",
                    "keywords": [q],
                    "_source": "dejure_org",
                })
                if len(rows) >= limit:
                    break

            if not rows:
                raise AdapterError(f"No DE case results for '{q}'")
            return rows

        return self._run_with_cache(cache_key, _fetch)
