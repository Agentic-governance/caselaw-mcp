"""Cross-border IP enforcement playbook generator."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "playbook_db.json"
_db: dict | None = None

def _load_db() -> dict:
    global _db
    if _db is None:
        _db = json.loads(_db_path_resolved().read_text(encoding="utf-8"))
    return _db

def _db_path_resolved() -> Path:
    return _DB_PATH

def list_forums() -> list[dict]:
    return _load_db()["forums"]

def score_forum(forum: dict, profile: dict) -> int:
    score = forum.get("suitability_base_score", 0)
    app = forum.get("applicability", {})
    srv_locs = profile.get("target_server_locations") or []
    tld = (profile.get("target_domain_tld") or "").lower()
    ip_type = (profile.get("ip_right_type") or "").lower()
    svc_type = (profile.get("target_service_type") or "").lower()
    market = [m.upper() for m in (profile.get("user_market_focus") or [])]
    prior = [a.lower() for a in (profile.get("prior_actions") or [])]
    scale = (profile.get("evidence_of_scale") or "").lower()
    bonus = 0
    if app.get("server_locations") and any(s.upper() in app["server_locations"] for s in srv_locs):
        bonus += 2
    if tld and app.get("tlds") and tld in app["tlds"]:
        bonus += 1
    if ip_type and app.get("ip_types") and ip_type in app["ip_types"]:
        bonus += 2
    if svc_type and app.get("service_types") and svc_type in app["service_types"]:
        bonus += 1
    if market and app.get("server_locations") and any(m in app["server_locations"] for m in market):
        bonus += 1
    if any("dmca" in p for p in prior) and forum.get("forum_id") == "us_federal_court":
        bonus += 1
    if scale == "large_scale":
        bonus += 1
    return min(score + bonus, 10)

def _suitability_label(score: int) -> str:
    if score >= 7:
        return "High"
    if score >= 5:
        return "Medium"
    return "Low"

def generate_playbook(profile: dict) -> dict:
    forums = list_forums()
    scored = []
    for f in forums:
        s = score_forum(f, profile)
        if s >= 3:
            entry = {
                "forum": f["forum"],
                "legal_basis": f.get("legal_basis", []),
                "jurisdiction_and_applicable_law": {
                    "notes": f.get("jurisdiction_notes", ""),
                    "key_risks": f.get("key_risks", []),
                },
                "remedies_and_measures": f.get("remedies", {}),
                "pros_cons": {
                    "pros": f.get("pros", []),
                    "cons": f.get("cons", []),
                },
                "suitability_score": _suitability_label(s),
                "_score_int": s,
                "illustrative_cases": f.get("illustrative_cases", []),
            }
            scored.append(entry)
    scored.sort(key=lambda x: x["_score_int"], reverse=True)
    for e in scored:
        del e["_score_int"]
    high = [e for e in scored if e["suitability_score"] == "High"]
    mid = [e for e in scored if e["suitability_score"] == "Medium"]
    db = _load_db()
    vol = db.get("voluntary_schemes", {})
    short_term = [f"File action in {e['forum']}" for e in high]
    if vol.get("search_engines"):
        short_term.append(f"Send {vol['search_engines'][0]} notices immediately")
    mid_term = [f"Evaluate {e['forum']}" for e in mid]
    if vol.get("isp_voluntary"):
        mid_term.append(f"Pursue voluntary schemes: {', '.join(vol['isp_voluntary'][:2])}")
    return {
        "candidate_forums": scored,
        "recommended_strategy": {
            "short_term": short_term or ["File takedown notices and assess jurisdiction options"],
            "mid_term": mid_term or ["Evaluate administrative and voluntary enforcement options"],
            "notes": "クロスボーダー案件では複数フォーラム並行利用を検討。先行通知の送付記録を保持すること。",
        },
    }
