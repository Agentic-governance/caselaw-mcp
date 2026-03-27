"""Citation Resolver: resolves citation strings to case_ids in the DB."""
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


def normalize_citation(citation_string: str) -> str:
    """Normalize a citation string for fuzzy matching.
    Removes extra spaces, normalizes periods, lowercases."""
    s = citation_string.strip()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\.\s+', '.', s)  # "F. 3d" -> "F.3d"
    return s.lower()


def resolve_citation(citation_string: str, jurisdiction: str = None) -> str | None:
    """Resolve a citation string to a case_id in the DB. Returns None if not found."""
    conn = get_connection()

    # 1. Exact match in citation_index
    if jurisdiction:
        row = conn.execute(
            "SELECT case_id FROM citation_index WHERE citation_string = ? AND jurisdiction = ?",
            (citation_string, jurisdiction)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT case_id FROM citation_index WHERE citation_string = ?",
            (citation_string,)
        ).fetchone()
    if row:
        conn.close()
        return row["case_id"]

    # 2. Normalized match in citation_index
    normalized = normalize_citation(citation_string)
    row = conn.execute(
        "SELECT case_id FROM citation_index WHERE citation_string = ?",
        (normalized,)
    ).fetchone()
    if row:
        conn.close()
        return row["case_id"]

    # 3. Search cases table by case_name (for "X v. Y" style citations)
    #    Uses exact match first (instant with idx_cases_name), then LIKE fallback.
    if " v. " in citation_string or " v " in citation_string:
        name_part = re.split(r',\s*\d', citation_string)[0].strip()
        name_part = re.sub(r'\s+', ' ', name_part).strip()

        # 3a. Exact match on case_name (uses B-tree index, ~0.01s)
        if jurisdiction:
            row = conn.execute(
                "SELECT case_id FROM cases WHERE case_name = ? AND jurisdiction = ? LIMIT 1",
                (name_part, jurisdiction)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT case_id FROM cases WHERE case_name = ? LIMIT 1",
                (name_part,)
            ).fetchone()
        if row:
            conn.close()
            return row["case_id"]

        # 3b. LIKE fallback (slow on large jurisdictions, use with caution)
        if jurisdiction:
            row = conn.execute(
                "SELECT case_id FROM cases WHERE case_name LIKE ? AND jurisdiction = ? LIMIT 1",
                (f"%{name_part}%", jurisdiction)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT case_id FROM cases WHERE case_name LIKE ? LIMIT 1",
                (f"%{name_part}%",)
            ).fetchone()
        if row:
            conn.close()
            return row["case_id"]

    # 4. Search by source_url or case_number
    row = conn.execute(
        "SELECT case_id FROM cases WHERE case_number LIKE ? LIMIT 1",
        (f"%{citation_string}%",)
    ).fetchone()
    if row:
        conn.close()
        return row["case_id"]

    conn.close()
    return None


def build_citation_index():
    """Build the citation_index table from existing cases data.
    Generates common citation forms for each case."""
    conn = get_connection()
    cases = conn.execute(
        "SELECT case_id, jurisdiction, case_name, case_number, source_url FROM cases"
    ).fetchall()

    for case in cases:
        entries = []
        case_id = case["case_id"]
        jur = case["jurisdiction"]

        # Add case_number as citation
        if case["case_number"]:
            entries.append(case["case_number"])

        # Add case_name
        if case["case_name"]:
            entries.append(case["case_name"])
            # Normalized version
            entries.append(normalize_citation(case["case_name"]))

        for entry in entries:
            if entry and len(entry) > 2:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO citation_index (citation_string, case_id, jurisdiction) VALUES (?, ?, ?)",
                        (entry, case_id, jur)
                    )
                except Exception:
                    pass

    conn.commit()
    conn.close()
