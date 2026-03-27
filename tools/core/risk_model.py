"""Legal risk estimation tool."""

from __future__ import annotations


def estimate_legal_risk(
    jurisdiction: str,
    situation_description: str,
    factors: dict | None = None,
) -> dict:
    """Estimate legal risk using lightweight, explainable scoring."""
    factors = factors or {}

    notification_sent = bool(factors.get("notification_sent", False))
    response_received = bool(factors.get("response_received", False))
    knowledge_level = str(factors.get("knowledge_level", "none")).lower()

    score = 1
    reasons: list[str] = []

    if notification_sent:
        score += 1
        reasons.append("notification has been sent")
    if notification_sent and not response_received:
        score += 1
        reasons.append("no response after notification")

    knowledge_weights = {"none": -1, "constructive": 1, "actual": 2}
    score += knowledge_weights.get(knowledge_level, 0)
    reasons.append(f"knowledge level assessed as {knowledge_level}")

    if any(x in situation_description.lower() for x in ["repeat", "systemic", "ongoing"]):
        score += 1
        reasons.append("pattern suggests repeated conduct")

    if jurisdiction.upper() in {"JP", "EU"} and notification_sent and not response_received:
        score += 1
        reasons.append("jurisdiction tends to emphasize post-notice action")

    if score <= 1:
        risk_level = "Low"
    elif score <= 3:
        risk_level = "Medium"
    else:
        risk_level = "High"

    case_map = {
        "US": [
            "Mon Cheri Bridals v. Cloudflare (N.D.Cal., 2025)",
            "Viacom v. YouTube (2d Cir., 2012)",
        ],
        "JP": ["集英社他 v. Cloudflare (東京地裁, 2025)"],
        "EU": [
            "UMG v. Cloudflare (DE to CJEU, 2020-)",
            "AGCOM v. Cloudflare (IT administrative, 2026)",
        ],
    }

    actions = {
        "Low": [
            "continue monitoring and preserve logs",
            "keep notice workflow documented",
        ],
        "Medium": [
            "validate notice-and-action SLA",
            "perform targeted host review",
            "prepare counsel briefing memo",
        ],
        "High": [
            "escalate to external counsel immediately",
            "execute urgent takedown or access restriction",
            "preserve evidence and decision timeline",
        ],
    }

    basis = f"Risk estimated from {', '.join(reasons)}."
    return {
        "risk_level": risk_level,
        "basis": basis,
        "relevant_cases": case_map.get(jurisdiction.upper(), []),
        "recommended_actions": actions[risk_level],
    }
