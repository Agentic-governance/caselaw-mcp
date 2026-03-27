"""Adapter for Portuguese case law via DGSI (dgsi.pt) — Lotus Notes database."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from urllib.parse import quote
from .base import AdapterError, BaseAdapter

_BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# DGSI Lotus Notes view IDs per court
_COURTS = {
    "stj": ("jstj.nsf", "954f0ce6ad9dd8b980256b5f003fa814", "Supremo Tribunal de Justiça"),
    "trl": ("jtrl.nsf", "206d2be8f20e5ab680256b5f003fa814", "Tribunal da Relação de Lisboa"),
    "trc": ("jtrc.nsf", "c3fb530030ea1c61802568d9005ea5d6", "Tribunal da Relação de Coimbra"),
    "trp": ("jtrp.nsf", "56a6e7099657f91e80257cda00381fdf", "Tribunal da Relação do Porto"),
}


class PTLawAdapter(BaseAdapter):
    """Portuguese case law adapter via DGSI (dgsi.pt)."""
    BASE_URL = "https://www.dgsi.pt"

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
        cache_key = f"ptlaw:{q.lower()}:{year_from}:{limit}:{court}"

        def _fetch() -> list[dict[str, Any]]:
            rows: list[dict[str, Any]] = []
            courts_to_search = (
                {court.lower(): _COURTS[court.lower()]}
                if court and court.lower() in _COURTS
                else _COURTS
            )

            for court_key, (nsf, view_id, court_name) in courts_to_search.items():
                if len(rows) >= limit:
                    break
                q_encoded = quote(q, safe="")
                search_url = (
                    f"{self.BASE_URL}/{nsf}/{view_id}"
                    f"?SearchView&Query=FIELD+Descritores+CONTAINS+{q_encoded}"
                    f"&SearchMax={limit}"
                )
                try:
                    html = self._request_text(
                        "GET", search_url,
                        headers={"User-Agent": _BROWSER_UA},
                    )
                except AdapterError:
                    continue

                for m in re.finditer(
                    r'<a[^>]+href="(/[^"]+\?OpenDocument)"[^>]*>(.*?)</a>',
                    html, re.DOTALL | re.IGNORECASE,
                ):
                    href, inner = m.groups()
                    case_id = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                    case_id = re.sub(r"\s+", " ", case_id)
                    if not case_id or len(case_id) < 3:
                        continue

                    # Fetch detail page for metadata
                    detail_url = f"{self.BASE_URL}{href}"
                    try:
                        detail = self._request_text(
                            "GET", detail_url,
                            headers={"User-Agent": _BROWSER_UA},
                        )
                    except AdapterError:
                        detail = ""

                    # Parse metadata from table rows
                    meta: dict[str, str] = {}
                    for tr in re.finditer(r'<tr[^>]*>(.*?)</tr>', detail, re.DOTALL):
                        cells = re.findall(r'<td[^>]*>(.*?)</td>', tr.group(1), re.DOTALL)
                        if len(cells) >= 2:
                            label = re.sub(r'<[^>]+>', '', cells[0]).strip().rstrip(':')
                            value = re.sub(r'<[^>]+>', ' ', cells[1]).strip()
                            value = re.sub(r'\s+', ' ', value)
                            if label and value:
                                meta[label] = value

                    processo = meta.get("Processo", case_id)
                    descritores = meta.get("Descritores", "")
                    data_acordao = meta.get("Data do Acordão", meta.get("Data do Acórdão", ""))
                    decisao = meta.get("Decisão", meta.get("Decisão", "Unknown"))
                    relator = meta.get("Relator", "")
                    area = meta.get("Área Temática", "")
                    sumario = meta.get("Sumário", "")[:500]

                    # Extract year from date
                    year = None
                    ym = re.search(r'(\d{4})', data_acordao)
                    if ym:
                        year = int(ym.group(1))
                    if not year:
                        ym = re.search(r'(\d{4})', processo)
                        if ym:
                            year = int(ym.group(1))

                    if year_from and year and year < year_from:
                        continue

                    case_name = f"Acórdão {court_name} — {processo}"
                    text_parts = [case_name]
                    if descritores:
                        text_parts.append(f"Descritores: {descritores}")
                    if area:
                        text_parts.append(f"Área: {area}")
                    if sumario:
                        text_parts.append(f"Sumário: {sumario}")
                    text = " | ".join(text_parts)

                    rows.append({
                        "case_name": case_name,
                        "jurisdiction": "PT",
                        "court": court_name,
                        "year": year,
                        "result": decisao[:100] if decisao else "Unknown",
                        "text": text,
                        "source_url": detail_url,
                        "domain": "external",
                        "keywords": [q] + [d.strip() for d in descritores.split("\n") if d.strip()][:5],
                        "_source": "dgsi_pt",
                    })
                    if len(rows) >= limit:
                        break

            if not rows:
                raise AdapterError(f"No PT case results for '{q}'")
            return rows

        return self._run_with_cache(cache_key, _fetch)
