"""Unified schema definitions for Legal MCP return types."""
from __future__ import annotations

from typing import NotRequired, TypedDict


class CaseLawRecord(TypedDict):
    """Normalized case law record returned by all case law adapters."""

    case_name: str
    jurisdiction: str
    court: str
    year: int | None
    result: str
    summary: str
    domain: str
    keywords: list[str]
    _source: str
    citation: NotRequired[str]
    parties: NotRequired[tuple[str, str]]
    full_text_url: NotRequired[str]
    raw_id: NotRequired[str]
    ecli: NotRequired[str]
    case_number: NotRequired[str]


class StatuteRecord(TypedDict):
    """Normalized statute record returned by all statute adapters."""

    law_name: str
    jurisdiction: str
    article: str | None
    text: str
    theme: str | None
    _source: str
    law_id: NotRequired[str]
    effective_date: NotRequired[str]
    url: NotRequired[str]


CASE_LAW_RETURN_KEYS = (
    "case_name",
    "jurisdiction",
    "court",
    "year",
    "result",
    "summary",
    "domain",
    "keywords",
)

STATUTE_RETURN_KEYS = (
    "law_name",
    "jurisdiction",
    "article",
    "text",
    "theme",
)


def normalize_case_law(row: dict) -> dict:
    """判例レコードを正規化スキーマに変換 (不足フィールドにデフォルト値を補完)"""

    normalized = {
        "case_name": str(row.get("case_name") or ""),
        "jurisdiction": str(row.get("jurisdiction") or "").upper(),
        "court": str(row.get("court") or ""),
        "year": row.get("year") if isinstance(row.get("year"), int) else None,
        "result": str(row.get("result") or "Unknown"),
        "summary": str(row.get("summary") or ""),
        "domain": str(row.get("domain") or "external"),
        "keywords": list(row.get("keywords") or []),
        "_source": str(row.get("_source") or "unknown"),
    }

    for opt_key in ("citation", "ecli", "case_number", "full_text_url", "raw_id"):
        if row.get(opt_key):
            normalized[opt_key] = str(row[opt_key])

    if row.get("parties") and isinstance(row["parties"], (list, tuple)) and len(row["parties"]) >= 2:
        normalized["parties"] = tuple(str(p) for p in row["parties"][:2])

    return normalized


def normalize_statute(row: dict) -> dict:
    """法令レコードを正規化スキーマに変換"""

    normalized = {
        "law_name": str(row.get("law_name") or ""),
        "jurisdiction": str(row.get("jurisdiction") or "").upper(),
        "article": row.get("article"),
        "text": str(row.get("text") or ""),
        "theme": row.get("theme"),
        "_source": str(row.get("_source") or "unknown"),
    }

    for opt_key in ("law_id", "effective_date", "url"):
        if row.get(opt_key):
            normalized[opt_key] = str(row[opt_key])

    return normalized
