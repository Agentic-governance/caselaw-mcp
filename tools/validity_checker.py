"""Validity Checker: checks if a case has been overruled/distinguished by analyzing citation contexts."""
from __future__ import annotations

import re
import sqlite3
import os

DB_PATH = os.environ.get(
    "CASELAW_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "data", "caselaw.db"),
)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Citation Signal constants
# ---------------------------------------------------------------------------

class CitationSignal:
    """Traffic-light signal for case validity."""
    GREEN = "green"      # No negative treatment found
    YELLOW = "yellow"    # Distinguished or questioned but not overruled
    RED = "red"          # Overruled or reversed
    UNKNOWN = "unknown"  # Case not found or no citing cases


# ---------------------------------------------------------------------------
# Keyword dictionaries for detecting negative treatment
# ---------------------------------------------------------------------------

OVERRULING_KEYWORDS: dict[str, list[str]] = {
    "en": [
        "overruled", "overrule", "overrules", "overruling",
        "reversed", "reverse", "reverses", "reversing",
        "vacated", "vacate", "vacates", "vacating",
        "abrogated", "abrogate", "abrogates", "abrogating",
        "no longer good law", "superseded", "supersede",
        "overturned", "overturn", "overturns", "overturning",
    ],
    "ja": [
        "変更", "破棄", "取消", "取り消し", "廃棄",
        "判例変更", "先例変更", "覆す", "覆した",
    ],
    "de": [
        "aufgehoben", "aufheben", "aufhebung",
        "überholt", "geändert", "abweichung",
        "nicht mehr anwendbar",
    ],
    "fr": [
        "infirmé", "infirmer", "cassé", "casser",
        "annulé", "annuler", "renversé", "renverser",
        "abrogé", "abroger", "réformé", "réformer",
    ],
    "pl": [
        "uchylony", "uchylić", "uchylenie",
        "zmieniony", "zmienić", "zmiana",
        "nieważny", "unieważnić",
    ],
    "it": [
        "annullato", "annullare", "cassato", "cassare",
        "riformato", "riformare", "revocato", "revocare",
    ],
}

DISTINGUISHING_KEYWORDS: dict[str, list[str]] = {
    "en": [
        "distinguished", "distinguish", "distinguishes", "distinguishing",
        "limited", "limiting", "narrowed", "narrowing",
        "questioned", "questioning", "doubted", "doubting",
        "criticized", "criticised", "criticizing", "criticising",
        "declined to follow", "declined to extend",
        "not followed", "not binding",
    ],
    "ja": [
        "区別", "射程外", "射程を限定", "限定解釈",
        "本件と事案を異にする", "事案が異なる",
        "疑問を呈", "批判",
    ],
    "de": [
        "eingeschränkt", "einschränken", "einschränkung",
        "abweichend", "abweichung",
        "nicht anwendbar", "nicht einschlägig",
    ],
    "fr": [
        "distingué", "distinguer", "limité", "limiter",
        "critiqué", "critiquer", "nuancé", "nuancer",
    ],
}


# ---------------------------------------------------------------------------
# Court hierarchy for determining overruling weight
# ---------------------------------------------------------------------------

COURT_HIERARCHY: dict[str, list[str]] = {
    # Lists from highest to lowest court
    "US": [
        "Supreme Court",
        "Circuit Court",       # Federal Courts of Appeals
        "Court of Appeals",
        "District Court",
        "Bankruptcy Court",
    ],
    "JP": [
        "最高裁判所",           # Supreme Court
        "高等裁判所",           # High Court
        "地方裁判所",           # District Court
        "簡易裁判所",           # Summary Court
        "家庭裁判所",           # Family Court
    ],
    "UK": [
        "Supreme Court",
        "Court of Appeal",
        "High Court",
        "Crown Court",
        "County Court",
    ],
    "EU": [
        "Court of Justice",     # CJEU Grand Chamber
        "General Court",        # formerly CFI
        "Board of Appeal",      # e.g. EUIPO BoA
    ],
    "DE": [
        "Bundesverfassungsgericht",    # Federal Constitutional Court
        "Bundesgerichtshof",           # Federal Court of Justice
        "Oberlandesgericht",           # Higher Regional Court
        "Landgericht",                 # Regional Court
        "Amtsgericht",                 # Local Court
    ],
    "FR": [
        "Cour de cassation",           # Supreme Court (civil/criminal)
        "Conseil d'État",              # Supreme Administrative Court
        "Conseil constitutionnel",     # Constitutional Council
        "Cour d'appel",                # Court of Appeal
        "Tribunal judiciaire",         # First instance
    ],
    "CH": [
        "Bundesgericht",              # Swiss Federal Supreme Court
        "Tribunal fédéral",
        "Bundesverwaltungsgericht",   # Federal Administrative Court
        "Bundesstrafgericht",         # Federal Criminal Court
        "Kantonsgericht",             # Cantonal Court
        "Obergericht",                # Higher Cantonal Court
        "Bezirksgericht",             # District Court
    ],
    "AU": [
        "High Court",                  # High Court of Australia
        "Federal Court",               # Federal Court
        "Supreme Court",               # State Supreme Courts
        "District Court",
        "Magistrates Court",
    ],
    "CA": [
        "Supreme Court",               # SCC
        "Federal Court of Appeal",
        "Court of Appeal",             # Provincial CA
        "Superior Court",
        "Federal Court",
    ],
    "IN": [
        "Supreme Court",               # SCI
        "High Court",                  # State High Courts
        "District Court",
    ],
    "PL": [
        "Sąd Najwyższy",              # Supreme Court
        "Trybunał Konstytucyjny",     # Constitutional Tribunal
        "Naczelny Sąd Administracyjny", # Supreme Administrative Court
        "Sąd Apelacyjny",             # Appellate Court
        "Sąd Okręgowy",               # Regional Court
        "Sąd Rejonowy",               # District Court
    ],
    "AT": [
        "Verfassungsgerichtshof",      # Constitutional Court
        "Verwaltungsgerichtshof",      # Administrative Court
        "Oberster Gerichtshof",        # Supreme Court
        "Oberlandesgericht",           # Higher Regional Court
        "Landesgericht",               # Regional Court
        "Bezirksgericht",              # District Court
    ],
}


def _court_rank(court: str | None, jurisdiction: str | None) -> int:
    """Return numeric rank of a court (lower = higher authority).
    Returns 999 if unknown."""
    if not court or not jurisdiction:
        return 999
    hierarchy = COURT_HIERARCHY.get(jurisdiction, [])
    for i, level in enumerate(hierarchy):
        if level.lower() in court.lower():
            return i
    return 999


def _detect_treatment(context: str | None) -> tuple[str, str | None]:
    """Detect whether a citation context indicates overruling or distinguishing.

    Returns:
        (treatment_type, matched_keyword)
        treatment_type is one of: "overruling", "distinguishing", "neutral"
    """
    if not context:
        return ("neutral", None)

    context_lower = context.lower()

    # Check overruling keywords across all languages
    for lang, keywords in OVERRULING_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in context_lower:
                return ("overruling", kw)

    # Check distinguishing keywords across all languages
    for lang, keywords in DISTINGUISHING_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in context_lower:
                return ("distinguishing", kw)

    return ("neutral", None)


def check_validity(case_id: str) -> dict:
    """Check whether a case has been overruled or distinguished.

    Args:
        case_id: The case_id to check validity for.

    Returns:
        dict with keys:
            - signal: CitationSignal value (green/yellow/red/unknown)
            - reason: Human-readable explanation
            - citing_count: Number of cases citing this case
            - overruling_cases: List of dicts with citing case info
    """
    conn = get_connection()

    # Verify the case exists
    case_row = conn.execute(
        "SELECT case_id, jurisdiction, court, case_name FROM cases WHERE case_id = ?",
        (case_id,)
    ).fetchone()

    if not case_row:
        conn.close()
        return {
            "signal": CitationSignal.UNKNOWN,
            "reason": f"Case '{case_id}' not found in database.",
            "citing_count": 0,
            "overruling_cases": [],
        }

    target_jurisdiction = case_row["jurisdiction"]
    target_court = case_row["court"]
    target_rank = _court_rank(target_court, target_jurisdiction)

    # Get all cases that cite this case_id
    citing_rows = conn.execute(
        """SELECT cc.citing_case_id, cc.citation_context,
                  c.court, c.jurisdiction, c.case_name, c.decision_date
           FROM case_citations cc
           JOIN cases c ON c.case_id = cc.citing_case_id
           WHERE cc.cited_case_id = ?""",
        (case_id,)
    ).fetchall()

    citing_count = len(citing_rows)

    if citing_count == 0:
        conn.close()
        return {
            "signal": CitationSignal.UNKNOWN,
            "reason": f"No citing cases found for '{case_id}'.",
            "citing_count": 0,
            "overruling_cases": [],
        }

    overruling_cases = []
    distinguishing_cases = []

    for row in citing_rows:
        treatment, keyword = _detect_treatment(row["citation_context"])

        if treatment == "overruling":
            citing_rank = _court_rank(row["court"], row["jurisdiction"])
            overruling_cases.append({
                "case_id": row["citing_case_id"],
                "case_name": row["case_name"],
                "court": row["court"],
                "jurisdiction": row["jurisdiction"],
                "decision_date": row["decision_date"],
                "keyword": keyword,
                "higher_court": citing_rank < target_rank,
            })
        elif treatment == "distinguishing":
            distinguishing_cases.append({
                "case_id": row["citing_case_id"],
                "case_name": row["case_name"],
                "court": row["court"],
                "jurisdiction": row["jurisdiction"],
                "decision_date": row["decision_date"],
                "keyword": keyword,
            })

    conn.close()

    # Determine signal
    if overruling_cases:
        # Check if any overruling is from a higher court
        higher_court_overrule = any(c["higher_court"] for c in overruling_cases)
        if higher_court_overrule:
            signal = CitationSignal.RED
            reason = (
                f"Overruled by higher court. "
                f"{len(overruling_cases)} overruling citation(s) found."
            )
        else:
            # Same-level or unknown-level overruling -> YELLOW (potentially RED)
            signal = CitationSignal.YELLOW
            reason = (
                f"Overruling language found in {len(overruling_cases)} citation(s), "
                f"but not from a clearly higher court. Manual review recommended."
            )
    elif distinguishing_cases:
        signal = CitationSignal.YELLOW
        reason = (
            f"Distinguished or questioned in {len(distinguishing_cases)} citation(s). "
            f"Not overruled, but authority may be limited."
        )
    else:
        signal = CitationSignal.GREEN
        reason = (
            f"No negative treatment found among {citing_count} citing case(s)."
        )

    return {
        "signal": signal,
        "reason": reason,
        "citing_count": citing_count,
        "overruling_cases": overruling_cases,
    }


def get_citing_cases(case_id: str, limit: int = 20) -> list[dict]:
    """Get cases that cite the given case_id.

    Args:
        case_id: The cited case's ID.
        limit: Maximum number of results (default 20).

    Returns:
        List of dicts with citing case info and citation context.
    """
    conn = get_connection()
    rows = conn.execute(
        """SELECT cc.citing_case_id, cc.citation_context, cc.cited_reference,
                  c.case_name, c.court, c.jurisdiction, c.decision_date
           FROM case_citations cc
           JOIN cases c ON c.case_id = cc.citing_case_id
           WHERE cc.cited_case_id = ?
           ORDER BY c.decision_date DESC
           LIMIT ?""",
        (case_id, limit)
    ).fetchall()
    conn.close()

    results = []
    for row in rows:
        treatment, keyword = _detect_treatment(row["citation_context"])
        results.append({
            "case_id": row["citing_case_id"],
            "case_name": row["case_name"],
            "court": row["court"],
            "jurisdiction": row["jurisdiction"],
            "decision_date": row["decision_date"],
            "citation_context": row["citation_context"],
            "cited_reference": row["cited_reference"],
            "treatment": treatment,
            "treatment_keyword": keyword,
        })

    return results


def get_cited_cases(case_id: str) -> list[dict]:
    """Get cases cited by the given case_id.

    Args:
        case_id: The citing case's ID.

    Returns:
        List of dicts with cited case info and citation context.
    """
    conn = get_connection()
    rows = conn.execute(
        """SELECT cc.cited_case_id, cc.cited_reference, cc.citation_context,
                  c.case_name, c.court, c.jurisdiction, c.decision_date
           FROM case_citations cc
           LEFT JOIN cases c ON c.case_id = cc.cited_case_id
           WHERE cc.citing_case_id = ?
           ORDER BY c.decision_date DESC""",
        (case_id,)
    ).fetchall()
    conn.close()

    results = []
    for row in rows:
        results.append({
            "case_id": row["cited_case_id"],
            "case_name": row["case_name"],
            "court": row["court"],
            "jurisdiction": row["jurisdiction"],
            "decision_date": row["decision_date"],
            "citation_context": row["citation_context"],
            "cited_reference": row["cited_reference"],
        })

    return results
