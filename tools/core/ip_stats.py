"""IP statistics search tool — wraps all 10 IP stats adapters."""
from __future__ import annotations

from typing import Any

from tools.adapters import (
    CNIPAStatsAdapter,
    EPOStatsAdapter,
    EUIPOStatsAdapter,
    GIIStatsAdapter,
    JPOStatsAdapter,
    KIPOStatsAdapter,
    OECDIPAdapter,
    USPTOStatsAdapter,
    WIPOStatsAdapter,
    WorldBankIPAdapter,
)

IP_STATS_SOURCES = {
    "auto",
    "local",
    "wipo",
    "uspto",
    "epo",
    "worldbank",
    "oecd",
    "jpo",
    "euipo",
    "gii",
    "cnipa",
    "kipo",
}


def search_ip_stats(
    jurisdiction: str,
    indicator: str = "patent_applications",
    year_from: int | None = None,
    limit: int = 10,
    source: str = "auto",
) -> list[dict[str, Any]]:
    """Search IP statistics by jurisdiction, indicator and year range."""
    source_norm = source.strip().lower()
    if source_norm not in IP_STATS_SOURCES:
        raise ValueError(f"Unsupported source: {source}")
    jurisdiction_norm = jurisdiction.strip().upper()

    dispatch = {
        "wipo": (WIPOStatsAdapter, {"US", "JP", "CN", "KR", "DE", "FR", "GB", "IN", "BR", "CA", "GLOBAL"}),
        "uspto": (USPTOStatsAdapter, {"US"}),
        "epo": (EPOStatsAdapter, {"EP", "DE", "US", "JP", "CN", "GLOBAL"}),
        "worldbank": (WorldBankIPAdapter, set()),
        "oecd": (OECDIPAdapter, {"US", "JP", "DE", "KR", "FR", "GB", "CA", "AU", "OECD", "GLOBAL"}),
        "jpo": (JPOStatsAdapter, {"JP"}),
        "euipo": (EUIPOStatsAdapter, {"EU", "DE", "US", "CN", "GLOBAL"}),
        "gii": (GIIStatsAdapter, set()),
        "cnipa": (CNIPAStatsAdapter, {"CN"}),
        "kipo": (KIPOStatsAdapter, {"KR"}),
    }

    def _try(adapter_cls: type[Any]) -> list[dict[str, Any]]:
        return adapter_cls().search_stats(
            indicator=indicator,
            jurisdiction=jurisdiction_norm,
            year_from=year_from,
            limit=limit,
        )

    if source_norm != "auto":
        if source_norm in dispatch:
            return _try(dispatch[source_norm][0])
        return []

    jur_source = {
        "JP": "jpo",
        "CN": "cnipa",
        "KR": "kipo",
        "EU": "euipo",
        "EP": "epo",
        "US": "uspto",
        "GLOBAL": "wipo",
        "INTL": "wipo",
    }
    priority = []
    if jurisdiction_norm in jur_source:
        priority.append(jur_source[jurisdiction_norm])
    priority += ["wipo", "worldbank", "oecd", "gii"]

    tried: set[str] = set()
    for src in priority:
        if src in tried or src not in dispatch:
            continue
        tried.add(src)
        try:
            rows = _try(dispatch[src][0])
            if rows:
                return rows
        except Exception:
            pass

    return []
