"""IP dispute and enforcement search tools — 4 tools."""
from __future__ import annotations

from typing import Any

from tools.adapters import (
    AUTMAdapter,
    CIPOAdapter,
    CourtStatsAdapter,
    DEIPCourtsAdapter,
    EUIPOOppositionAdapter,
    EPOOppositionAdapter,
    EnforcementAdapter,
    GIPCIndexAdapter,
    IEEESAAdapter,
    INPIBrazilAdapter,
    IPAustraliaAdapter,
    IPIndiaAdapter,
    IPOSSingaporeAdapter,
    ITC337Adapter,
    OECDCounterfeitAdapter,
    PTABAdapter,
    SEPFRANDAdapter,
    UPCAdapter,
    UPOVAdapter,
    USTR301Adapter,
    USCopyrightAdapter,
    WIPOADRAdapter,
    WIPOCopyrightTreatiesAdapter,
    WIPOHagueAdapter,
    WIPOLisbonAdapter,
    WIPOMadridAdapter,
    WIPOTechTrendsAdapter,
    WTOTRIPSAdapter,
)

IP_DISPUTE_SOURCES = {
    "auto",
    "all",
    "wipo_adr",
    "itc337",
    "epo_opposition",
    "ptab",
    "ustr301",
    "enforcement",
    "upc",
    "gipc_index",
    "euipo_opposition",
    "oecd_counterfeit",
    "wipo_madrid",
    "wipo_hague",
    "wipo_lisbon",
    "wto_trips",
    "court_stats",
    "sep_frand",
    "upov",
    "wipo_tech_trends",
    "ieee_sa",
    "wipo_copyright_treaties",
    "us_copyright",
    "autm",
    "ip_australia",
    "cipo",
    "inpi_brazil",
    "ip_india",
    "ipos_singapore",
    "de_ip_courts",
}

# Module-level ADAPTERS dict for import by server.py
ADAPTERS = {
    "wipo_adr": WIPOADRAdapter,
    "itc337": ITC337Adapter,
    "epo_opposition": EPOOppositionAdapter,
    "ptab": PTABAdapter,
    "ustr301": USTR301Adapter,
    "enforcement": EnforcementAdapter,
    "upc": UPCAdapter,
    "gipc_index": GIPCIndexAdapter,
    "euipo_opposition": EUIPOOppositionAdapter,
    "oecd_counterfeit": OECDCounterfeitAdapter,
    "wipo_madrid": WIPOMadridAdapter,
    "wipo_hague": WIPOHagueAdapter,
    "wipo_lisbon": WIPOLisbonAdapter,
    "wto_trips": WTOTRIPSAdapter,
    "court_stats": CourtStatsAdapter,
    "sep_frand": SEPFRANDAdapter,
    "upov": UPOVAdapter,
    "wipo_tech_trends": WIPOTechTrendsAdapter,
    "ieee_sa": IEEESAAdapter,
    "wipo_copyright_treaties": WIPOCopyrightTreatiesAdapter,
    "us_copyright": USCopyrightAdapter,
    "autm": AUTMAdapter,
    "ip_australia": IPAustraliaAdapter,
    "cipo": CIPOAdapter,
    "inpi_brazil": INPIBrazilAdapter,
    "ip_india": IPIndiaAdapter,
    "ipos_singapore": IPOSSingaporeAdapter,
    "de_ip_courts": DEIPCourtsAdapter,
}


def ip_dispute_search(
    query: str,
    jurisdiction: str = "GLOBAL",
    year_from: int | None = None,
    limit: int = 10,
    source: str = "auto",
) -> list[dict[str, Any]]:
    """Search IP disputes and enforcement data across 6 sources."""
    source_norm = source.strip().lower()
    if source_norm not in IP_DISPUTE_SOURCES:
        raise ValueError(f"Unsupported source: {source}")
    jur = jurisdiction.strip().upper()

    adapters = {
        "wipo_adr": WIPOADRAdapter,
        "itc337": ITC337Adapter,
        "epo_opposition": EPOOppositionAdapter,
        "ptab": PTABAdapter,
        "ustr301": USTR301Adapter,
        "enforcement": EnforcementAdapter,
        "upc": UPCAdapter,
        "gipc_index": GIPCIndexAdapter,
        "euipo_opposition": EUIPOOppositionAdapter,
        "oecd_counterfeit": OECDCounterfeitAdapter,
        "wipo_madrid": WIPOMadridAdapter,
        "wipo_hague": WIPOHagueAdapter,
        "wipo_lisbon": WIPOLisbonAdapter,
        "wto_trips": WTOTRIPSAdapter,
        "court_stats": CourtStatsAdapter,
        "sep_frand": SEPFRANDAdapter,
        "upov": UPOVAdapter,
        "wipo_tech_trends": WIPOTechTrendsAdapter,
        "ieee_sa": IEEESAAdapter,
        "wipo_copyright_treaties": WIPOCopyrightTreatiesAdapter,
        "us_copyright": USCopyrightAdapter,
        "autm": AUTMAdapter,
        "ip_australia": IPAustraliaAdapter,
        "cipo": CIPOAdapter,
        "inpi_brazil": INPIBrazilAdapter,
        "ip_india": IPIndiaAdapter,
        "ipos_singapore": IPOSSingaporeAdapter,
        "de_ip_courts": DEIPCourtsAdapter,
    }

    if source_norm not in ("auto", "all"):
        return adapters[source_norm]().search_disputes(
            query=query,
            jurisdiction=jur,
            year_from=year_from,
            limit=limit,
        )

    results: list[dict[str, Any]] = []
    jurisdiction_priority = {
        "US": [
            "ptab",
            "itc337",
            "ustr301",
            "enforcement",
            "us_copyright",
            "autm",
            "wipo_adr",
            "epo_opposition",
            "gipc_index",
            "wipo_madrid",
            "wipo_hague",
            "wipo_lisbon",
            "wto_trips",
            "court_stats",
            "sep_frand",
            "ieee_sa",
            "wipo_tech_trends",
            "wipo_copyright_treaties",
            "upov",
            "oecd_counterfeit",
            "upc",
            "euipo_opposition",
        ],
        "EP": [
            "epo_opposition",
            "wipo_adr",
            "enforcement",
            "upc",
            "euipo_opposition",
            "gipc_index",
            "wipo_madrid",
            "wipo_hague",
            "wipo_lisbon",
            "wto_trips",
            "court_stats",
            "sep_frand",
            "ieee_sa",
            "wipo_tech_trends",
            "wipo_copyright_treaties",
            "upov",
            "oecd_counterfeit",
        ],
        "EU": [
            "epo_opposition",
            "enforcement",
            "wipo_adr",
            "upc",
            "euipo_opposition",
            "gipc_index",
            "wipo_madrid",
            "wipo_hague",
            "wipo_lisbon",
            "wto_trips",
            "court_stats",
            "sep_frand",
            "ieee_sa",
            "wipo_tech_trends",
            "wipo_copyright_treaties",
            "upov",
            "oecd_counterfeit",
        ],
        "DE": [
            "de_ip_courts",
            "epo_opposition",
            "upc",
            "euipo_opposition",
            "wipo_adr",
            "enforcement",
            "sep_frand",
            "wipo_madrid",
            "wipo_hague",
            "wto_trips",
            "court_stats",
            "gipc_index",
            "oecd_counterfeit",
            "ieee_sa",
            "wipo_tech_trends",
        ],
        "AU": [
            "ip_australia",
            "upov",
            "wipo_adr",
            "enforcement",
            "gipc_index",
            "wipo_madrid",
            "wipo_hague",
            "wto_trips",
            "court_stats",
            "oecd_counterfeit",
            "wipo_tech_trends",
            "wipo_copyright_treaties",
        ],
        "CA": [
            "cipo",
            "autm",
            "upov",
            "wipo_adr",
            "enforcement",
            "gipc_index",
            "wipo_madrid",
            "wipo_hague",
            "wto_trips",
            "court_stats",
            "oecd_counterfeit",
            "wipo_tech_trends",
            "wipo_copyright_treaties",
        ],
        "BR": [
            "inpi_brazil",
            "upov",
            "wipo_adr",
            "enforcement",
            "ustr301",
            "gipc_index",
            "wipo_madrid",
            "wipo_hague",
            "wto_trips",
            "court_stats",
            "oecd_counterfeit",
            "wipo_tech_trends",
        ],
        "IN": [
            "ip_india",
            "upov",
            "wipo_adr",
            "enforcement",
            "ustr301",
            "gipc_index",
            "wipo_madrid",
            "wipo_hague",
            "wto_trips",
            "court_stats",
            "oecd_counterfeit",
            "wipo_tech_trends",
        ],
        "SG": [
            "ipos_singapore",
            "wipo_adr",
            "enforcement",
            "gipc_index",
            "wipo_madrid",
            "wipo_hague",
            "wto_trips",
            "court_stats",
            "oecd_counterfeit",
            "wipo_tech_trends",
            "wipo_copyright_treaties",
        ],
        "GLOBAL": [
            "wipo_adr",
            "ustr301",
            "enforcement",
            "ptab",
            "itc337",
            "epo_opposition",
            "upc",
            "gipc_index",
            "euipo_opposition",
            "oecd_counterfeit",
            "wipo_madrid",
            "wipo_hague",
            "wipo_lisbon",
            "wto_trips",
            "court_stats",
            "sep_frand",
            "upov",
            "wipo_tech_trends",
            "ieee_sa",
            "wipo_copyright_treaties",
            "us_copyright",
            "autm",
            "ip_australia",
            "cipo",
            "inpi_brazil",
            "ip_india",
            "ipos_singapore",
            "de_ip_courts",
        ],
    }
    priority = jurisdiction_priority.get(
        jur,
        [
            "wipo_adr",
            "ustr301",
            "enforcement",
            "ptab",
            "itc337",
            "epo_opposition",
            "upc",
            "gipc_index",
            "euipo_opposition",
            "oecd_counterfeit",
            "wipo_madrid",
            "wipo_hague",
            "wipo_lisbon",
            "wto_trips",
            "court_stats",
            "sep_frand",
            "upov",
            "wipo_tech_trends",
            "ieee_sa",
            "wipo_copyright_treaties",
        ],
    )
    if source_norm == "all":
        priority = list(adapters.keys())

    for src in priority:
        try:
            rows = adapters[src]().search_disputes(
                query=query,
                jurisdiction=jur,
                year_from=year_from,
                limit=limit,
            )
            results.extend(rows)
            if source_norm == "auto" and len(results) >= limit:
                break
        except Exception:
            continue

    return results[:limit] if source_norm == "auto" else results


def ip_enforcement_profile(
    jurisdiction: str,
    year: int | None = None,
) -> dict[str, Any]:
    """Return integrated IP enforcement profile for a country (301 + seizures + NML)."""
    jur = jurisdiction.strip().upper()
    year_from = year if year else 2020

    profile: dict[str, Any] = {
        "jurisdiction": jur,
        "year": year or 2024,
        "special_301_status": None,
        "notorious_market_count": None,
        "cbp_seizure_share": None,
        "eu_seizure_share": None,
        "raw": [],
    }

    try:
        r301 = USTR301Adapter().search_disputes(query="", jurisdiction=jur, year_from=year_from, limit=5)
    except Exception:
        r301 = []
    for row in r301:
        indicator = row.get("indicator", "")
        if "priority_watch" in indicator:
            profile["special_301_status"] = "Priority Watch List"
        elif "watch_list" in indicator and profile["special_301_status"] is None:
            profile["special_301_status"] = "Watch List"
    profile["raw"].extend(r301)

    try:
        cbp = EnforcementAdapter().search_disputes(query="share", jurisdiction=jur, year_from=year_from, limit=5)
    except Exception:
        cbp = []
    for row in cbp:
        indicator = row.get("indicator", "")
        if "cbp" in indicator and "share" in indicator:
            profile["cbp_seizure_share"] = row.get("value")
    profile["raw"].extend(cbp)

    try:
        eu = EnforcementAdapter().search_disputes(query="eu", jurisdiction=jur, year_from=year_from, limit=5)
    except Exception:
        eu = []
    for row in eu:
        indicator = row.get("indicator", "")
        if "eu" in indicator and "share" in indicator:
            profile["eu_seizure_share"] = row.get("value")

    if not profile["raw"]:
        profile["status"] = "no_data"
        profile["message"] = "Enforcement data currently unavailable for this jurisdiction"

    return profile


def ip_dispute_forum_comparison(
    year: int = 2023,
) -> list[dict[str, Any]]:
    """Compare IP dispute forums: UDRP vs Section 337 vs EPO Opposition vs PTAB."""
    forums = [
        {
            "forum": "WIPO UDRP",
            "adapter": WIPOADRAdapter,
            "indicator": "udrp_cases_filed",
            "jurisdiction": "GLOBAL",
        },
        {
            "forum": "WIPO Mediation",
            "adapter": WIPOADRAdapter,
            "indicator": "mediation_cases",
            "jurisdiction": "GLOBAL",
        },
        {
            "forum": "USITC Section 337",
            "adapter": ITC337Adapter,
            "indicator": "section337_investigations",
            "jurisdiction": "US",
        },
        {
            "forum": "EPO Opposition",
            "adapter": EPOOppositionAdapter,
            "indicator": "oppositions_filed",
            "jurisdiction": "EP",
        },
        {
            "forum": "USPTO PTAB IPR",
            "adapter": PTABAdapter,
            "indicator": "ipr_petitions_filed",
            "jurisdiction": "US",
        },
        {
            "forum": "USPTO PTAB PGR",
            "adapter": PTABAdapter,
            "indicator": "pgr_petitions_filed",
            "jurisdiction": "US",
        },
        {
            "forum": "UPC (Unified Patent Court)",
            "adapter": UPCAdapter,
            "indicator": "upc_cases_filed",
            "jurisdiction": "EU",
        },
        {
            "forum": "EUIPO TM Opposition",
            "adapter": EUIPOOppositionAdapter,
            "indicator": "tm_oppositions_filed",
            "jurisdiction": "EU",
        },
    ]

    results = []
    for forum in forums:
        try:
            rows = forum["adapter"]().search_disputes(
                query=forum["indicator"],
                jurisdiction=forum["jurisdiction"],
                year_from=year,
                limit=5,
            )
        except Exception:
            results.append({
                "forum": forum["forum"],
                "status": "unavailable",
                "message": f"Data source temporarily unavailable for {forum['forum']}",
                "indicator": forum["indicator"],
                "jurisdiction": forum["jurisdiction"],
            })
            continue
        matched = False
        for row in rows:
            if row.get("indicator") == forum["indicator"] and row.get("year") == year:
                results.append({"forum": forum["forum"], **row})
                matched = True
                break
        if not matched:
            for row in rows:
                if row.get("indicator") == forum["indicator"]:
                    results.append({"forum": forum["forum"], **row})
                    matched = True
                    break
        if not matched:
            results.append({
                "forum": forum["forum"],
                "status": "no_data",
                "indicator": forum["indicator"],
                "year": year,
            })

    return results


def ip_list_dispute_indicators() -> dict[str, list[str]]:
    """List all available dispute/enforcement indicators per source."""
    def _get_indicators(cls):
        seed = getattr(cls, "SEED", None)
        if seed:
            return [s["indicator"] for s in seed if isinstance(s, dict) and "indicator" in s]
        return []

    return {
        "wipo_adr": _get_indicators(WIPOADRAdapter),
        "itc337": _get_indicators(ITC337Adapter),
        "epo_opposition": _get_indicators(EPOOppositionAdapter),
        "ptab": _get_indicators(PTABAdapter),
        "ustr301": _get_indicators(USTR301Adapter),
        "enforcement": _get_indicators(EnforcementAdapter),
        "upc": _get_indicators(UPCAdapter),
        "gipc_index": _get_indicators(GIPCIndexAdapter),
        "euipo_opposition": _get_indicators(EUIPOOppositionAdapter),
        "oecd_counterfeit": _get_indicators(OECDCounterfeitAdapter),
        "wipo_madrid": _get_indicators(WIPOMadridAdapter),
        "wipo_hague": _get_indicators(WIPOHagueAdapter),
        "wipo_lisbon": _get_indicators(WIPOLisbonAdapter),
        "wto_trips": _get_indicators(WTOTRIPSAdapter),
        "court_stats": _get_indicators(CourtStatsAdapter),
        "sep_frand": _get_indicators(SEPFRANDAdapter),
        "upov": _get_indicators(UPOVAdapter),
        "wipo_tech_trends": _get_indicators(WIPOTechTrendsAdapter),
        "ieee_sa": _get_indicators(IEEESAAdapter),
        "wipo_copyright_treaties": _get_indicators(WIPOCopyrightTreatiesAdapter),
        "us_copyright": _get_indicators(USCopyrightAdapter),
        "autm": _get_indicators(AUTMAdapter),
        "ip_australia": _get_indicators(IPAustraliaAdapter),
        "cipo": _get_indicators(CIPOAdapter),
        "inpi_brazil": _get_indicators(INPIBrazilAdapter),
        "ip_india": _get_indicators(IPIndiaAdapter),
        "ipos_singapore": _get_indicators(IPOSSingaporeAdapter),
        "de_ip_courts": _get_indicators(DEIPCourtsAdapter),
    }
