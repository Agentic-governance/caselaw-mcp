"""Case law search tool — FTS5-primary with adapter supplement."""

from __future__ import annotations

import json
import sqlite3
import os
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
DB_PATH = os.environ.get(
    "CASELAW_DB_PATH",
    str(Path(__file__).resolve().parents[2] / "data" / "caselaw.db"),
)

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
    "fts5",
    "courtlistener",
    "eurlex",
    "jpcourts",
    "canlii",
    "hudoc",
    "indiankanoon",
    "icj",
}


def _get_db():
    """Get a connection to the case law SQLite DB."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _search_fts5(
    query_text: str,
    jurisdiction: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    """Search cases using FTS5 full-text index with BM25 ranking."""
    conn = _get_db()
    try:
        # Verify FTS5 is available
        conn.execute("SELECT 1 FROM cases_fts LIMIT 0")
    except Exception:
        conn.close()
        return []

    # Build FTS5 query from text
    safe_terms = []
    for t in query_text.strip().split():
        if t.strip():
            escaped = t.strip().replace('"', '""')
            safe_terms.append(f'"{escaped}"')
    if not safe_terms:
        conn.close()
        return []

    fts_query = " ".join(safe_terms)
    params: list = [fts_query]

    sql = """SELECT c.case_id, c.case_name, c.jurisdiction, c.court,
                    c.decision_date, c.case_type, c.subject_area,
                    c.outcome, c.importance_score, c.has_content,
                    c.summary,
                    bm25(cases_fts, 10.0, 1.0) as score
             FROM cases_fts f
             JOIN cases c ON c.rowid = f.rowid
             WHERE cases_fts MATCH ?"""

    if jurisdiction:
        sql += " AND c.jurisdiction = ?"
        params.append(jurisdiction.strip().upper())
    if year_from:
        sql += " AND c.decision_date >= ?"
        params.append(f"{year_from}-01-01")
    if year_to:
        sql += " AND c.decision_date <= ?"
        params.append(f"{year_to}-12-31")

    sql += " ORDER BY c.has_content DESC, score LIMIT ?"
    params.append(min(max_results, 50))

    try:
        rows = conn.execute(sql, params).fetchall()
    except Exception:
        conn.close()
        return []

    results = []
    for r in rows:
        year_val = None
        if r["decision_date"]:
            try:
                year_val = int(str(r["decision_date"])[:4])
            except (ValueError, TypeError):
                pass
        results.append({
            "case_id": r["case_id"],
            "case_name": r["case_name"],
            "jurisdiction": r["jurisdiction"],
            "court": r["court"],
            "year": year_val,
            "decision_date": r["decision_date"],
            "result": r["outcome"] or "",
            "summary": r["summary"] or "",
            "case_type": r["case_type"],
            "subject_area": r["subject_area"],
            "importance_score": r["importance_score"],
            "has_content": r["has_content"],
            "domain": "fts5",
            "keywords": [],
            "_source": "fts5",
        })
    conn.close()
    return results


def _load_case_law() -> list[dict[str, Any]]:
    try:
        with DATA_PATH.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        if not isinstance(data, list):
            raise ValueError("case_law_db.json must contain a list")
        return data
    except Exception:
        return []


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
        row["_source"] = "local_json"
        matches.append(row)

    return matches


def _search_courtlistener(topic: str, keywords: list[str] | None, year_from: int | None) -> list[dict[str, Any]]:
    query = " ".join([topic.strip(), " ".join(keywords or [])]).strip()
    rows = CourtListenerAdapter().search_cases(query=query or topic, year_from=year_from)
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


# Mapping: jurisdiction -> adapter search function
_ADAPTER_MAP = {
    "US": lambda t, kw, yf: _search_courtlistener(t, kw, yf),
    "JP": lambda t, kw, yf: _search_jpcourts(t, kw, yf),
    "CA": lambda t, kw, yf: _search_canlii(t, kw, yf),
    "ECHR": lambda t, kw, yf: _search_hudoc(t, kw, yf),
    "IN": lambda t, kw, yf: _search_indiankanoon(t, kw, yf),
    "ICJ": lambda t, kw, yf: _search_icj(t, kw, yf),
}


def search_case_law(
    jurisdiction: str,
    topic: str,
    keywords: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    source: str = "auto",
) -> list[dict[str, Any]]:
    """Search case law: FTS5 is PRIMARY, adapters supplement, local JSON is last resort."""
    source_norm = source.strip().lower()
    if source_norm not in CASE_LAW_SOURCES:
        raise ValueError(f"Unsupported source: {source}")

    jurisdiction_norm = jurisdiction.strip().upper()

    # Force-specific source requested
    if source_norm == "local":
        return _filter_local(jurisdiction, topic, keywords, year_from, year_to)

    if source_norm == "fts5":
        query_text = " ".join([topic] + (keywords or []))
        return _search_fts5(query_text, jurisdiction_norm, year_from, year_to)

    # Adapter-only sources
    adapter_only = {
        "courtlistener": lambda: _search_courtlistener(topic, keywords, year_from),
        "eurlex": lambda: _search_eurlex(topic, keywords),
        "jpcourts": lambda: _search_jpcourts(topic, keywords, year_from),
        "canlii": lambda: _search_canlii(topic, keywords, year_from),
        "hudoc": lambda: _search_hudoc(topic, keywords, year_from),
        "indiankanoon": lambda: _search_indiankanoon(topic, keywords, year_from),
        "icj": lambda: _search_icj(topic, keywords, year_from),
    }
    if source_norm in adapter_only:
        return adapter_only[source_norm]()

    # ── AUTO mode: FTS5 first, then adapter supplement, then local JSON ──

    results: list[dict[str, Any]] = []

    # 1) FTS5 search on the 85M+ case database (PRIMARY)
    query_text = " ".join([topic] + (keywords or []))
    fts5_results = _search_fts5(query_text, jurisdiction_norm, year_from, year_to)
    if fts5_results:
        results.extend(fts5_results)

    # 2) If FTS5 returned few results, try external adapter as supplement
    if len(results) < 5:
        adapter_fn = _ADAPTER_MAP.get(jurisdiction_norm)
        if adapter_fn:
            try:
                adapter_results = adapter_fn(topic, keywords, year_from)
                if adapter_results:
                    # Deduplicate by case_name
                    existing_names = {r.get("case_name", "").lower() for r in results}
                    for ar in adapter_results:
                        name = (ar.get("case_name") or "").lower()
                        if name and name not in existing_names:
                            results.append(ar)
                            existing_names.add(name)
            except Exception:
                pass  # Adapter failure is non-fatal

    # 3) If still no results, fall back to local JSON
    if not results:
        results = _filter_local(jurisdiction, topic, keywords, year_from, year_to)

    return results
