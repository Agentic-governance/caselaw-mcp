"""Statute search tool."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.adapters import DeStaatisAdapter, EGovAdapter, EurLexAdapter, UKLegAdapter
from tools.adapters import LegifranceAdapter, USCodeAdapter, WIPOLexAdapter
from tools.adapters import AULegAdapter, CALegAdapter, KRLegAdapter

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "statute_db.json"
RETURN_KEYS = ("law_name", "jurisdiction", "article", "text", "theme")
STATUTE_SOURCES = {"auto", "local", "egov", "eurlex", "destatis", "ukleg", "legifrance", "wipolex", "uscode", "auleg", "caleg", "krleg"}


def _load_statutes() -> list[dict[str, Any]]:
    with DATA_PATH.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, list):
        raise ValueError("statute_db.json must contain a list")
    return data


def _filter_local(
    jurisdiction: str,
    law_name: str | None = None,
    article: str | None = None,
    keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    jurisdiction_norm = jurisdiction.strip().upper()
    law_name_norm = (law_name or "").strip().lower()
    article_norm = (article or "").strip().lower()
    keyword_norm = [kw.strip().lower() for kw in (keywords or []) if kw and kw.strip()]

    matches: list[dict[str, Any]] = []
    for entry in _load_statutes():
        if str(entry.get("jurisdiction", "")).upper() != jurisdiction_norm:
            continue

        target_name = str(entry.get("law_name", "")).lower()
        target_article = str(entry.get("article", "")).lower()
        target_text = str(entry.get("text", "")).lower()
        target_theme = str(entry.get("theme", "")).lower()

        if law_name_norm and law_name_norm not in target_name:
            continue
        if article_norm and article_norm not in target_article:
            continue

        if keyword_norm:
            keyword_space = " ".join([target_name, target_article, target_text, target_theme])
            if not any(kw in keyword_space for kw in keyword_norm):
                continue

        row = {key: entry.get(key) for key in RETURN_KEYS}
        row["_source"] = "local"
        matches.append(row)

    return matches


def _search_egov(
    law_name: str | None,
    article: str | None,
    keywords: list[str] | None,
) -> list[dict[str, Any]]:
    adapter = EGovAdapter()
    query = (law_name or " ".join(keywords or [])).strip()
    law_num = adapter.lookup_law_num(query) if query else None
    if law_num:
        if article:
            detail = adapter.get_article(law_num=law_num, article=article)
            if detail:
                detail["_source"] = "egov"
                return [detail]
        else:
            rows = adapter.get_law_overview(law_num, max_articles=5)
            for row in rows:
                row["_source"] = "egov"
            if rows:
                return rows

    laws = adapter.search_statutes(query=query)
    rows: list[dict[str, Any]] = []
    for law in laws:
        rows.append(
            {
                "law_name": law.get("law_name"),
                "jurisdiction": "JP",
                "article": None,
                "text": "",
                "theme": None,
                "_source": "egov",
            }
        )
    return rows


def _search_eurlex(
    law_name: str | None,
    article: str | None,
    keywords: list[str] | None,
) -> list[dict[str, Any]]:
    adapter = EurLexAdapter()
    query = " ".join([law_name or "", " ".join(keywords or [])]).strip()
    laws = adapter.search_legislation(query=query or "law")

    rows: list[dict[str, Any]] = []
    if article:
        for law in laws:
            work = str(law.get("work", ""))
            if not work:
                continue
            detail = adapter.get_document(work)
            if not detail:
                continue
            detail["article"] = article
            detail["_source"] = "eurlex"
            rows.append({key: detail.get(key) for key in RETURN_KEYS + ("_source",)})
    else:
        for law in laws:
            rows.append(
                {
                    "law_name": law.get("title"),
                    "jurisdiction": "EU",
                    "article": None,
                    "text": law.get("work"),
                    "theme": "eurlex_document",
                    "_source": "eurlex",
                }
            )

    return rows


def _search_destatis(
    law_name: str | None,
    article: str | None,
    keywords: list[str] | None,
) -> list[dict[str, Any]]:
    adapter = DeStaatisAdapter()
    law_abbrev = (law_name or "").strip()
    if not law_abbrev:
        return []
    return adapter.search_statutes(law_abbrev=law_abbrev, article=article, keywords=keywords)


def _search_ukleg(
    law_name: str | None,
    article: str | None,
    keywords: list[str] | None,
) -> list[dict[str, Any]]:
    adapter = UKLegAdapter()
    law_abbrev = (law_name or "").strip()
    if not law_abbrev:
        return []

    section: int | str | None = None
    if article is not None:
        article_norm = article.strip()
        if article_norm.lower().startswith("section "):
            section = article_norm.split(" ", 1)[1].strip()
        else:
            section = article_norm
    return adapter.search_statutes(law_name=law_abbrev, section=section, keywords=keywords)


def _search_legifrance(
    law_name: str | None,
    year_from: int | None,
) -> list[dict[str, Any]]:
    query = (law_name or "").strip()
    if not query:
        return []
    return LegifranceAdapter().search_statutes(query=query, year_from=year_from)


def _search_wipolex(
    law_name: str | None,
    year_from: int | None,
) -> list[dict[str, Any]]:
    query = (law_name or "").strip()
    if not query:
        return []
    return WIPOLexAdapter().search_statutes(query=query, year_from=year_from)


def _search_uscode(
    law_name: str | None,
    article: str | None,
    keywords: list[str] | None,
) -> list[dict[str, Any]]:
    adapter = USCodeAdapter()
    query = law_name or " ".join(keywords or [])
    rows = adapter.search_statutes(query=query or "copyright", section=article)
    for row in rows:
        if isinstance(row.get("article"), str):
            row["article"] = row["article"].replace("§ ", "§")
    return rows


def _search_auleg(
    law_name: str | None,
    article: str | None,
    keywords: list[str] | None,
) -> list[dict[str, Any]]:
    query = law_name or " ".join(keywords or [])
    return AULegAdapter().search_statutes(query=query or "copyright", article=article)


def _search_caleg(
    law_name: str | None,
    article: str | None,
    keywords: list[str] | None,
) -> list[dict[str, Any]]:
    query = law_name or " ".join(keywords or [])
    return CALegAdapter().search_statutes(query=query or "copyright", article=article)


def _search_krleg(
    law_name: str | None,
    article: str | None,
    keywords: list[str] | None,
) -> list[dict[str, Any]]:
    query = law_name or " ".join(keywords or [])
    return KRLegAdapter().search_statutes(query=query or "저작권", article=article)


def search_statute(
    jurisdiction: str,
    law_name: str | None = None,
    article: str | None = None,
    keywords: list[str] | None = None,
    year_from: int | None = None,
    source: str = "auto",
) -> list[dict[str, Any]]:
    """Search statute articles by jurisdiction and optional filters."""
    source_norm = source.strip().lower()
    if source_norm not in STATUTE_SOURCES:
        raise ValueError(f"Unsupported source: {source}")

    jurisdiction_norm = jurisdiction.strip().upper()

    if source_norm == "local":
        return _filter_local(jurisdiction, law_name, article, keywords)

    if source_norm == "egov" or (source_norm == "auto" and jurisdiction_norm == "JP"):
        try:
            rows = _search_egov(law_name, article, keywords)
            if rows:
                return rows
        except Exception:
            if source_norm == "egov":
                raise

    if source_norm == "eurlex" or (source_norm == "auto" and jurisdiction_norm == "EU"):
        try:
            rows = _search_eurlex(law_name, article, keywords)
            if rows:
                return rows
        except Exception:
            if source_norm == "eurlex":
                raise

    if source_norm == "destatis" or (source_norm == "auto" and jurisdiction_norm == "DE"):
        try:
            rows = _search_destatis(law_name, article, keywords)
            if rows:
                return rows
        except Exception:
            if source_norm == "destatis":
                raise

    if source_norm == "ukleg" or (source_norm == "auto" and jurisdiction_norm == "UK"):
        try:
            rows = _search_ukleg(law_name, article, keywords)
            if rows:
                return rows
        except Exception:
            if source_norm == "ukleg":
                raise

    if source_norm == "legifrance" or (source_norm == "auto" and jurisdiction_norm == "FR"):
        try:
            rows = _search_legifrance(law_name, year_from)
            if rows:
                return rows
        except Exception:
            if source_norm == "legifrance":
                raise

    if source_norm == "wipolex" or (source_norm == "auto" and jurisdiction_norm == "WIPO"):
        try:
            rows = _search_wipolex(law_name, year_from)
            if rows:
                return rows
        except Exception:
            if source_norm == "wipolex":
                raise

    if source_norm == "uscode" or (source_norm == "auto" and jurisdiction_norm == "US"):
        try:
            rows = _search_uscode(law_name, article, keywords)
            if rows:
                return rows
        except Exception:
            if source_norm == "uscode":
                raise

    if source_norm == "auleg" or (source_norm == "auto" and jurisdiction_norm == "AU"):
        try:
            rows = _search_auleg(law_name, article, keywords)
            if rows:
                return rows
        except Exception:
            if source_norm == "auleg":
                raise

    if source_norm == "caleg" or (source_norm == "auto" and jurisdiction_norm == "CA"):
        try:
            rows = _search_caleg(law_name, article, keywords)
            if rows:
                return rows
        except Exception:
            if source_norm == "caleg":
                raise

    if source_norm == "krleg" or (source_norm == "auto" and jurisdiction_norm == "KR"):
        try:
            rows = _search_krleg(law_name, article, keywords)
            if rows:
                return rows
        except Exception:
            if source_norm == "krleg":
                raise

    return _filter_local(jurisdiction, law_name, article, keywords)
