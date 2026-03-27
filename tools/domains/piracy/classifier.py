"""CDN host classifier for piracy-related legal analysis."""

from __future__ import annotations


LEGAL_CATEGORY_MAP = {
    "P1": "512(b)",
    "P2a": "512(b)",
    "P4": "512(b)",
    "P3": "512(c)",
    "E1": "direct_liability",
    "E2": "direct_liability",
}

ORIGIN_MAP = {
    "P1": "R2 Direct",
    "P2a": "R2+CDN",
    "P3": "Pages",
    "P4": "Workers",
    "E1": "S3 Direct",
    "E2": "S3+CDN",
}


def _signal(signals: dict, key: str) -> float:
    value = signals.get(key, 0.0)
    return float(value)


def classify_cdn_host(host: str, signals: dict) -> dict:
    """Classify host by deterministic decision tree and map to legal category."""
    if not isinstance(signals, dict):
        raise ValueError("signals must be a dict")

    referrer_policy_rate = _signal(signals, "referrer_policy_rate")
    cf_ray_rate = _signal(signals, "cf_ray_rate")
    cf_cache_status_rate = _signal(signals, "cf_cache_status_rate")
    range_206_rate = _signal(signals, "range_206_rate")
    x_amz_rate = _signal(signals, "x_amz_rate")

    if referrer_policy_rate > 0.5:
        node = "P3"
    elif cf_ray_rate <= 0.5:
        node = "E1"
    elif cf_cache_status_rate <= 0.5:
        if range_206_rate <= 0.5:
            node = "P4"
        else:
            node = "P1"
    elif x_amz_rate <= 0.5:
        node = "P2a"
    else:
        node = "E2"

    confidence = 0.9
    if abs(referrer_policy_rate - 0.5) < 0.05 or abs(cf_ray_rate - 0.5) < 0.05:
        confidence = 0.75

    return {
        "host": host,
        "origin_estimate": ORIGIN_MAP[node],
        "legal_category": LEGAL_CATEGORY_MAP[node],
        "confidence": round(confidence, 2),
    }
