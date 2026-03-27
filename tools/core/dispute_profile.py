"""Company/sector IP dispute profile aggregator."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
from typing import Any

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "case_law_db.json"
_cases: list | None = None

def _load_cases() -> list:
    global _cases
    if _cases is None:
        _cases = json.loads(_DB_PATH.read_text(encoding="utf-8"))
    return _cases

def _match_entity(case: dict, queries: list[str]) -> bool:
    text = " ".join([
        case.get("case_name", ""),
        case.get("summary", ""),
        " ".join(case.get("keywords", [])),
    ]).lower()
    return any(q.lower() in text for q in queries)

def _is_win(case: dict, role: str = "plaintiff") -> bool | None:
    result = (case.get("result") or "").lower()
    summary = (case.get("summary") or "").lower()
    combined = result + " " + summary
    win_signals = ["勝訴", "plaintiff win", "prevailed", "complainant win", "transfer ordered", "granted"]
    lose_signals = ["敗訴", "defendant win", "dismissed", "denied", "rejected"]
    if any(s in combined for s in win_signals):
        return True
    if any(s in combined for s in lose_signals):
        return False
    return None

def get_dispute_profile(
    target_entities: list[str],
    time_range: dict | None = None,
    filters: dict | None = None,
    group_by: list[str] | None = None,
) -> dict:
    cases = _load_cases()
    tr = time_range or {}
    year_from = int(tr["from"][:4]) if tr.get("from") else None
    year_to = int(tr["to"][:4]) if tr.get("to") else None

    matched = []
    for c in cases:
        if not _match_entity(c, target_entities):
            continue
        year = c.get("year")
        if year_from and year and year < year_from:
            continue
        if year_to and year and year > year_to:
            continue
        matched.append(c)

    n = len(matched)
    low_sample_note = "サンプルが限られているため傾向の信頼性は低い" if n < 10 else ""

    forum_counts: Counter = Counter()
    for c in matched:
        forum = c.get("court") or c.get("jurisdiction") or "unknown"
        forum_counts[forum] += 1

    wins = sum(1 for c in matched if _is_win(c) is True)
    losses = sum(1 for c in matched if _is_win(c) is False)
    partial = n - wins - losses

    sector_counts: Counter = Counter()
    for c in matched:
        topic = c.get("topic") or c.get("domain") or "unknown"
        sector_counts[topic] += 1

    years = [c.get("year") for c in matched if c.get("year")]
    time_effective = {}
    if years:
        time_effective = {"from": str(min(years)), "to": str(max(years))}

    return {
        "summary": {
            "n_cases_total": n,
            "time_range_effective": time_effective,
            "main_forums": [{"forum": f, "cases": cnt} for f, cnt in forum_counts.most_common(5)],
            "win_loss_overview": {
                "as_plaintiff": {"wins": wins, "losses": losses, "partial": partial},
            },
            "key_technical_sectors": [{"sector": s, "cases": cnt} for s, cnt in sector_counts.most_common(5)],
            "low_sample_note": low_sample_note,
        },
        "patterns": {
            "litigation_style": f"{n}件のケースを分析。主なフォーラムは{', '.join(f for f,_ in forum_counts.most_common(3))}。",
            "notable_counterparties": [],
            "geographical_focus": ", ".join(set(c.get("jurisdiction","") for c in matched if c.get("jurisdiction"))),
        },
        "risk_profile_for_counterparties": {
            "enforcement_likelihood": "High" if wins > losses else ("Medium" if wins == losses else "Low"),
            "typical_measures": list(set(c.get("topic","") for c in matched if c.get("topic")))[:5],
            "notes": low_sample_note,
        },
    }

def get_sector_profile(sector: str, time_range: dict | None = None) -> dict:
    cases = _load_cases()
    tr = time_range or {}
    year_from = int(tr["from"][:4]) if tr.get("from") else None
    year_to = int(tr["to"][:4]) if tr.get("to") else None
    sector_lower = sector.lower()
    matched = []
    for c in cases:
        text = " ".join([c.get("domain",""), c.get("topic",""), " ".join(c.get("keywords",[]))]).lower()
        if sector_lower not in text:
            continue
        year = c.get("year")
        if year_from and year and year < year_from:
            continue
        if year_to and year and year > year_to:
            continue
        matched.append(c)
    return get_dispute_profile(
        target_entities=[sector],
        time_range=time_range,
    )
