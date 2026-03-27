"""Safe harbor assessment tool."""

from __future__ import annotations

import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "jurisdiction_rules.json"

CATEGORY_BY_ORIGIN = {
    "R2 Direct": "512(b)",
    "R2+CDN": "512(b)",
    "Workers": "512(b)",
    "Pages": "512(c)",
    "S3 Direct": "direct_liability",
    "S3+CDN": "direct_liability",
    "P1": "512(b)",
    "P2a": "512(b)",
    "P4": "512(b)",
    "P3": "512(c)",
    "E1": "direct_liability",
    "E2": "direct_liability",
}


def _load_rules() -> dict:
    with DATA_PATH.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, dict):
        raise ValueError("jurisdiction_rules.json must contain a dict")
    return data


def assess_safe_harbor(origin_estimate: str, jurisdiction: str) -> dict:
    """Assess safe harbor applicability for a given delivery regime and jurisdiction."""
    rules = _load_rules()
    jurisdiction_norm = jurisdiction.strip().upper()
    if jurisdiction_norm not in rules:
        raise ValueError(f"Unsupported jurisdiction: {jurisdiction}")

    category = CATEGORY_BY_ORIGIN.get(origin_estimate)
    if category is None:
        category = "direct_liability"

    rule = rules[jurisdiction_norm]
    return {
        "applicable_provisions": rule["safe_harbor_provisions"].get(category, []),
        "requirements": rule["requirements"].get(category, []),
        "key_cases": rule["key_cases"].get(category, []),
        "recommended_actions": rule["recommended_actions"].get(category, []),
    }
