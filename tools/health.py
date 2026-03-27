"""Health check for all Legal MCP adapters."""
from __future__ import annotations

import time
from typing import Any


def check_adapter_health(timeout: float = 3.0) -> dict[str, Any]:
    """全アダプターのヘルス状態を確認して辞書で返す。

    Returns:
        {
            "timestamp": ISO8601文字列,
            "adapters": {
                "adapter_name": {
                    "status": "ok" | "offline" | "error",
                    "latency_ms": float | None,
                    "error": str | None,
                }
            },
            "summary": {"ok": int, "offline": int, "error": int}
        }
    """

    from tools.adapters.austlii import AustLIIAdapter
    from tools.adapters.canlii import CanLIIAdapter
    from tools.adapters.courtlistener import CourtListenerAdapter
    from tools.adapters.destatis import DeStaatisAdapter
    from tools.adapters.egov import EGovAdapter
    from tools.adapters.eurlex import EurLexAdapter
    from tools.adapters.hudoc import HUDOCAdapter
    from tools.adapters.jpcourts import JPCourtsAdapter
    from tools.adapters.openjustice import OpenJusticeAdapter
    from tools.adapters.ukleg import UKLegAdapter

    adapter_checks = [
        (
            "courtlistener",
            lambda: CourtListenerAdapter(timeout_seconds=timeout).search_cases(
                query="copyright", filed_after=None
            ),
        ),
        (
            "eurlex_sparql",
            lambda: EurLexAdapter(timeout_seconds=timeout).search_legislation(query="copyright"),
        ),
        (
            "egov_jp",
            lambda: EGovAdapter(timeout_seconds=timeout).search_statutes(query="著作権"),
        ),
        (
            "openjustice_eu",
            lambda: OpenJusticeAdapter(timeout_seconds=timeout).search_eu_cases(query="copyright"),
        ),
        ("jpcourts", lambda: JPCourtsAdapter(timeout_seconds=timeout).search_cases(query="著作権")),
        ("hudoc_echr", lambda: HUDOCAdapter(timeout_seconds=timeout).search_cases(query="copyright")),
        (
            "austlii_au",
            lambda: AustLIIAdapter(timeout_seconds=timeout).search_cases(
                query="copyright", jurisdiction="AU"
            ),
        ),
        (
            "nzlii_nz",
            lambda: AustLIIAdapter(timeout_seconds=timeout).search_cases(
                query="copyright", jurisdiction="NZ"
            ),
        ),
        ("canlii_ca", lambda: CanLIIAdapter(timeout_seconds=timeout).search_cases(query="copyright")),
        ("destatis_de", lambda: DeStaatisAdapter(timeout_seconds=timeout).search_statutes("UrhG")),
        ("ukleg_uk", lambda: UKLegAdapter(timeout_seconds=timeout).search_statutes("CDPA")),
    ]

    try:
        from tools.adapters.indiankanoon import IndianKanoonAdapter

        adapter_checks.append(
            (
                "indiankanoon_in",
                lambda: IndianKanoonAdapter(timeout_seconds=timeout).search_cases("copyright"),
            )
        )
    except ImportError:
        pass

    try:
        from tools.adapters.uscode import USCodeAdapter

        adapter_checks.append(
            ("uscode_us", lambda: USCodeAdapter(timeout_seconds=timeout).search_statutes("copyright"))
        )
    except ImportError:
        pass

    results: dict[str, Any] = {}
    summary = {"ok": 0, "offline": 0, "error": 0}

    for name, check_fn in adapter_checks:
        t0 = time.time()
        try:
            rows = check_fn()
            latency = (time.time() - t0) * 1000
            status = "ok" if rows else "offline"
            results[name] = {
                "status": status,
                "latency_ms": round(latency, 1),
                "error": None,
                "result_count": len(rows),
            }
            summary[status] += 1
        except Exception as exc:
            latency = (time.time() - t0) * 1000
            err_str = str(exc)
            if (
                "offline" in err_str.lower()
                or "network" in err_str.lower()
                or "HTTP request failed" in err_str
            ):
                status = "offline"
            else:
                status = "offline"
            results[name] = {
                "status": status,
                "latency_ms": round(latency, 1),
                "error": err_str[:100],
            }
            summary[status] += 1

    from datetime import datetime, timezone

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "adapters": results,
        "summary": summary,
    }
