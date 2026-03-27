"""
SQLite storage for crawled case law data.
Phase 1: cases + case_citations + citation_index.
"""
import sqlite3
import json
import os
from datetime import datetime, timezone

DB_PATH = os.environ.get(
    "CASELAW_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "data", "caselaw.db"),
)


def get_connection():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db():
    conn = get_connection()
    schema_path = os.path.join(os.path.dirname(__file__), "..", "data", "schema.sql")
    with open(schema_path) as f:
        conn.executescript(f.read())
    conn.close()


def store_case(case: dict, jurisdiction: str, adapter_name: str) -> str:
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()

    source_id = str(
        case.get("id")
        or case.get("case_id")
        or case.get("source_url")
        or hash(json.dumps(case, default=str))
    )
    case_id = f"{jurisdiction}:{source_id}"

    standard_fields = {
        "id", "case_id", "case_name", "case_number", "court",
        "decision_date", "text", "full_text", "plain_text",
        "summary", "source_url", "language",
    }
    raw = {k: v for k, v in case.items() if k not in standard_fields and v}

    text = case.get("text") or case.get("full_text") or case.get("plain_text") or ""

    conn.execute(
        """
        INSERT INTO cases (case_id, jurisdiction, court, case_name, case_number,
                          decision_date, full_text, summary, source_url,
                          source_adapter, language, raw_metadata, crawled_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(case_id) DO UPDATE SET
            full_text = CASE WHEN length(excluded.full_text) > length(cases.full_text)
                        THEN excluded.full_text ELSE cases.full_text END,
            raw_metadata = excluded.raw_metadata,
            updated_at = excluded.updated_at
        """,
        (
            case_id,
            jurisdiction,
            case.get("court", ""),
            case.get("case_name", ""),
            case.get("case_number", ""),
            case.get("decision_date", ""),
            text,
            case.get("summary", ""),
            case.get("source_url", ""),
            adapter_name,
            case.get("language", ""),
            json.dumps(raw, ensure_ascii=False) if raw else "{}",
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()
    return case_id


def store_citation(
    citing_case_id: str,
    cited_reference: str,
    cited_case_id: str = None,
    context: str = None,
):
    conn = get_connection()
    conn.execute(
        """
        INSERT OR IGNORE INTO case_citations
            (citing_case_id, cited_case_id, cited_reference, citation_context)
        VALUES (?, ?, ?, ?)
        """,
        (citing_case_id, cited_case_id, cited_reference, context),
    )
    conn.commit()
    conn.close()


def store_citation_index(citation_string: str, case_id: str, jurisdiction: str):
    conn = get_connection()
    conn.execute(
        """
        INSERT OR IGNORE INTO citation_index (citation_string, case_id, jurisdiction)
        VALUES (?, ?, ?)
        """,
        (citation_string, case_id, jurisdiction),
    )
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    by_jur = conn.execute(
        "SELECT jurisdiction, COUNT(*) as cnt FROM cases GROUP BY jurisdiction ORDER BY cnt DESC"
    ).fetchall()
    citations = conn.execute("SELECT COUNT(*) FROM case_citations").fetchone()[0]
    conn.close()
    return {
        "total_cases": total,
        "total_citations": citations,
        "by_jurisdiction": {row["jurisdiction"]: row["cnt"] for row in by_jur},
    }
