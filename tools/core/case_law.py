"""Case law search tool."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.adapters import (
    CanLIIAdapter,
    CourtListenerAdapter,
    EurLexAdapter,
    HUDOCAdapter,
    ICJAdapter,
    IndianKanoonAdapter,
    JPCourtsAdapter,
)

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "case_law_db.json"
RETURN_KEYS = (
    "case_name",
    "jurisdiction",
    "court",
    "year",
    "result",
    "summary",
    "domain",
    "keywords",
)
CASE_LAW_SOURCES = {
    "auto",
    "local",
    "courtlistener",
    "eurlex",
    "jpcourts",
    "canlii",
    "hudoc",
    "indiankanoon",
    "icj",
}


def _load_case_law() -> list[dict[str, Any]]:
    with DATA_PATH.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, list):
        raise ValueError("case_law_db.json must contain a list")
    return data


def _filter_local(
    jurisdiction: str,
    topic: str,
    keywords: list[str] | None,
    year_from: int | None,
    year_to: int | None,
) -> list[dict[str, Any]]:
    jurisdiction_norm = jurisdiction.strip().upper()
    topic_norm = topic.strip().lower()
    keyword_norm = [kw.strip().lower() for kw in (keywords or []) if kw and kw.strip()]

    matches: list[dict[str, Any]] = []
    for entry in _load_case_law():
        if str(entry.get("jurisdiction", "")).upper() != jurisdiction_norm:
            continue

        year = entry.get("year")
        if year_from is not None and isinstance(year, int) and year < year_from:
            continue
        if year_to is not None and isinstance(year, int) and year > year_to:
            continue

        combined_topic_space = " ".join(
            [
                str(entry.get("topic", "")),
                str(entry.get("summary", "")),
                str(entry.get("domain", "")),
                " ".join(str(x) for x in entry.get("keywords", []) if isinstance(x, str)),
            ]
        ).lower()
        if topic_norm and topic_norm not in combined_topic_space:
            continue

        if keyword_norm and not any(kw in combined_topic_space for kw in keyword_norm):
            continue

        row = {key: entry.get(key) for key in RETURN_KEYS}
        row["_source"] = "local"
        matches.append(row)

    return matches


def _search_courtlistener(topic: str, keywords: list[str] | None, year_from: int | None) -> list[dict[str, Any]]:
    query = " ".join([topic.strip(), " ".join(keywords or [])]).strip()
    filed_after = f"{year_from:04d}-01-01" if isinstance(year_from, int) else None
    rows = CourtListenerAdapter().search_cases(query=query or topic, filed_after=filed_after)
    for row in rows:
        row["_source"] = "courtlistener"
    return rows


def _search_eurlex(topic: str, keywords: list[str] | None) -> list[dict[str, Any]]:
    query = " ".join([topic.strip(), " ".join(keywords or [])]).strip()
    docs = EurLexAdapter().search_legislation(query=query or topic)
    rows: list[dict[str, Any]] = []
    for doc in docs:
        rows.append(
            {
                "case_name": doc.get("title"),
                "jurisdiction": "EU",
                "court": "EUR-Lex",
                "year": None,
                "result": "",
                "summary": doc.get("work"),
                "domain": "external",
                "keywords": [topic] + (keywords or []),
                "_source": "eurlex",
            }
        )
    return rows


def _search_jpcourts(topic: str, keywords: list[str] | None, year_from: int | None) -> list[dict[str, Any]]:
    query = " ".join([topic.strip(), " ".join(keywords or [])]).strip()
    return JPCourtsAdapter().search_cases(query=query or topic, year_from=year_from)


def _search_canlii(topic: str, keywords: list[str] | None, year_from: int | None) -> list[dict[str, Any]]:
    query = " ".join([topic.strip(), " ".join(keywords or [])]).strip()
    return CanLIIAdapter().search_cases(query=query or topic, year_from=year_from)


def _search_hudoc(topic: str, keywords: list[str] | None, year_from: int | None) -> list[dict[str, Any]]:
    query = " ".join([topic.strip(), " ".join(keywords or [])]).strip()
    return HUDOCAdapter().search_cases(query=query or topic, year_from=year_from)


def _search_indiankanoon(topic: str, keywords: list[str] | None, year_from: int | None) -> list[dict[str, Any]]:
    query = " ".join([topic.strip(), " ".join(keywords or [])]).strip()
    return IndianKanoonAdapter().search_cases(query=query or topic, year_from=year_from)


def _search_icj(topic: str, keywords: list[str] | None, year_from: int | None) -> list[dict[str, Any]]:
    query = " ".join([topic.strip(), " ".join(keywords or [])]).strip()
    return ICJAdapter().search_cases(query=query or topic, year_from=year_from)


def search_case_law(
    jurisdiction: str,
    topic: str,
    keywords: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    source: str = "auto",
) -> list[dict[str, Any]]:
    """Search case law entries by jurisdiction, topic, year range and keywords."""
    source_norm = source.strip().lower()
    if source_norm not in CASE_LAW_SOURCES:
        raise ValueError(f"Unsupported source: {source}")

    jurisdiction_norm = jurisdiction.strip().upper()

    if source_norm == "local":
        return _filter_local(jurisdiction, topic, keywords, year_from, year_to)

    if source_norm == "courtlistener" or (source_norm == "auto" and jurisdiction_norm == "US"):
        try:
            rows = _search_courtlistener(topic, keywords, year_from)
            if rows:
                return rows
        except Exception:
            if source_norm == "courtlistener":
                raise

    if source_norm == "jpcourts" or (source_norm == "auto" and jurisdiction_norm == "JP"):
        try:
            rows = _search_jpcourts(topic, keywords, year_from)
            if rows:
                return rows
        except Exception:
            if source_norm == "jpcourts":
                raise

    if source_norm == "canlii" or (source_norm == "auto" and jurisdiction_norm == "CA"):
        try:
            rows = _search_canlii(topic, keywords, year_from)
            if rows:
                return rows
        except Exception:
            if source_norm == "canlii":
                raise

    if source_norm == "hudoc" or (source_norm == "auto" and jurisdiction_norm == "ECHR"):
        try:
            rows = _search_hudoc(topic, keywords, year_from)
            if rows:
                return rows
        except Exception:
            if source_norm == "hudoc":
                raise

    if source_norm == "indiankanoon" or (source_norm == "auto" and jurisdiction_norm == "IN"):
        try:
            rows = _search_indiankanoon(topic, keywords, year_from)
            if rows:
                return rows
        except Exception:
            if source_norm == "indiankanoon":
                raise

    if source_norm == "eurlex":
        try:
            rows = _search_eurlex(topic, keywords)
            if rows:
                return rows
        except Exception:
            if source_norm == "eurlex":
                raise

    if source_norm == "icj" or (source_norm == "auto" and jurisdiction_norm == "ICJ"):
        try:
            rows = _search_icj(topic, keywords, year_from)
            if rows:
                return rows
        except Exception:
            if source_norm == "icj":
                raise

    return _filter_local(jurisdiction, topic, keywords, year_from, year_to)
