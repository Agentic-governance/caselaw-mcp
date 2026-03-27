"""Legal MCP server entrypoint for Phase A."""

from __future__ import annotations

import argparse

from fastmcp import FastMCP

from tools.core.case_law import search_case_law
from tools.core.doc_gen import generate_legal_draft
from tools.core.ip_stats import search_ip_stats
from tools.core.ip_disputes import (
    ip_dispute_forum_comparison,
    ip_dispute_search,
    ip_enforcement_profile,
    ip_list_dispute_indicators,
)
from tools.core.risk_model import estimate_legal_risk
from tools.core.statute import search_statute
from tools.core.metadata_extractor import partial_extract, normalize_metadata, validate_schema, build_empty_schema
from tools.analytics import PartyAnalyzer, generate_recommendations
from tools.benchmarks import SECTOR_BENCHMARKS
from entity.registry import EntityRegistry
from entity.resolver import EntityResolver
from entity.data.entities_seed import SEED_ENTITIES
from events.snapshot import SnapshotStore
from events.rules import BUILTIN_RULES
from events.detector import EventDetector

mcp = FastMCP("legal-mcp")

# ── Entity registry (initialized once at startup) ──
_entity_registry = EntityRegistry()
for _e in SEED_ENTITIES:
    _entity_registry.register(_e)
_entity_resolver = EntityResolver(_entity_registry)

# ── Snapshot store (persists between calls) ──
_snapshot_store = SnapshotStore()
_event_detector = EventDetector(_snapshot_store, BUILTIN_RULES)


@mcp.tool()
def tool_search_case_law(
    jurisdiction: str,
    topic: str,
    keywords: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
):
    """Search case law across jurisdiction/topic/keywords/year range."""
    return search_case_law(
        jurisdiction=jurisdiction,
        topic=topic,
        keywords=keywords,
        year_from=year_from,
        year_to=year_to,
    )


@mcp.tool()
def tool_search_statute(
    jurisdiction: str,
    law_name: str | None = None,
    article: str | None = None,
    keywords: list[str] | None = None,
):
    """Search statute texts by jurisdiction and optional filters."""
    return search_statute(
        jurisdiction=jurisdiction,
        law_name=law_name,
        article=article,
        keywords=keywords,
    )


@mcp.tool()
def tool_generate_legal_draft(doc_type: str, jurisdiction: str, context: dict):
    """Generate legal markdown draft for common document types."""
    return generate_legal_draft(doc_type=doc_type, jurisdiction=jurisdiction, context=context)


@mcp.tool()
def tool_estimate_legal_risk(
    jurisdiction: str,
    situation_description: str,
    factors: dict | None = None,
):
    """Estimate legal risk for a provided situation."""
    return estimate_legal_risk(
        jurisdiction=jurisdiction,
        situation_description=situation_description,
        factors=factors,
    )


# ═══════════════════════════════════════════════════════════════
# Generic Caselaw Tools (汎用判例検索ツール)
# ═══════════════════════════════════════════════════════════════

@mcp.tool()
async def search_cases(
    query: str,
    jurisdiction: str = "US",
    max_results: int = 10,
    legal_area: str | None = None,
) -> dict:
    """
    任意の管轄で判例をフルテキスト付きで検索する。

    Args:
        query: 検索クエリ（事案の記述、キーワード、当事者名など）
        jurisdiction: 管轄（US, GB, EU, JP, AU, CA, DE, FR, IN, BR, KR, etc.）
        max_results: 最大取得件数
        legal_area: 法分野フィルタ（contract, tort, ip, criminal, etc.）

    Returns:
        dict: {
            "results": [{"case_id": str, "title": str, "text": str,
                        "date": str, "court": str, "source_url": str}],
            "count": int,
            "jurisdiction": str
        }
    """
    # Delegate to existing core function (returns list[dict])
    results = search_case_law(
        jurisdiction=jurisdiction,
        topic=legal_area or query,
        keywords=[query] if query else None,
    )
    cases = results if isinstance(results, list) else results.get("cases", [])
    return {
        "results": cases[:max_results],
        "count": len(cases),
        "jurisdiction": jurisdiction,
    }


@mcp.tool()
async def search_cases_global(
    query: str,
    jurisdictions: list[str] = None,
    max_results_per_jurisdiction: int = 5,
) -> dict:
    """
    複数管轄を横断して判例を検索する。

    Args:
        query: 検索クエリ
        jurisdictions: 検索対象管轄リスト（デフォルト: ["US", "GB", "EU", "JP", "AU"]）
        max_results_per_jurisdiction: 各管轄での最大取得件数

    Returns:
        dict: {
            "results": {<jurisdiction>: [cases...]},
            "total_count": int,
            "jurisdictions_searched": list[str]
        }
    """
    if jurisdictions is None:
        jurisdictions = ["US", "GB", "EU", "JP", "AU"]

    all_results = {}
    total = 0

    for jur in jurisdictions:
        try:
            result = await search_cases(
                query=query,
                jurisdiction=jur,
                max_results=max_results_per_jurisdiction,
            )
            cases = result.get("results", [])
            all_results[jur] = cases
            total += len(cases)
        except Exception as e:
            all_results[jur] = {"error": str(e)}

    return {
        "results": all_results,
        "total_count": total,
        "jurisdictions_searched": jurisdictions,
    }


@mcp.tool()
async def get_case_detail(
    case_id: str,
    jurisdiction: str,
) -> dict:
    """
    特定の判例のフルテキストと要旨を取得する。

    Args:
        case_id: 判例ID（各管轄固有のID）
        jurisdiction: 管轄コード

    Returns:
        dict: {
            "case_id": str,
            "title": str,
            "full_text": str,
            "summary": str,
            "date": str,
            "court": str,
            "parties": list[str],
            "citations": list[str],
            "source_url": str
        }
    """
    # Use search with case_id as query to retrieve specific case
    results = search_case_law(
        jurisdiction=jurisdiction,
        topic=case_id,
        keywords=[case_id],
    )

    cases = results if isinstance(results, list) else results.get("cases", [])
    if not cases:
        return {"error": f"Case {case_id} not found in {jurisdiction}"}

    # Return first match with full details
    case = cases[0]
    return {
        "case_id": case.get("case_id", case_id),
        "title": case.get("title", ""),
        "full_text": case.get("text", ""),
        "summary": case.get("summary", case.get("text", "")[:500]),
        "date": case.get("date", ""),
        "court": case.get("court", ""),
        "parties": case.get("parties", []),
        "citations": case.get("citations", []),
        "source_url": case.get("source_url", ""),
    }


@mcp.tool()
async def find_similar_cases(
    text: str,
    jurisdiction: str = "ALL",
    max_results: int = 10,
) -> dict:
    """
    事案の記述から類似判例を検索する。

    Args:
        text: 事案の記述（事実関係、争点、法的問題など）
        jurisdiction: 管轄（"ALL"で全管轄を検索）
        max_results: 最大取得件数

    Returns:
        dict: {
            "similar_cases": [{"case_id": str, "title": str, "relevance": float,
                              "text": str, "jurisdiction": str}],
            "query_text": str,
            "search_jurisdiction": str
        }
    """
    if jurisdiction == "ALL":
        # Search across multiple major jurisdictions
        return await search_cases_global(
            query=text,
            jurisdictions=["US", "GB", "EU", "JP", "AU", "CA"],
            max_results_per_jurisdiction=max_results // 6,
        )
    else:
        # Single jurisdiction search
        result = await search_cases(
            query=text,
            jurisdiction=jurisdiction,
            max_results=max_results,
        )
        return {
            "similar_cases": result.get("results", []),
            "query_text": text[:200],
            "search_jurisdiction": jurisdiction,
        }


@mcp.tool()
async def analyze_legal_trend(
    legal_area: str,
    jurisdiction: str,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """
    特定の法分野における判例トレンドを分析する。

    Args:
        legal_area: 法分野（contract, tort, ip, criminal, administrative, etc.）
        jurisdiction: 管轄コード
        date_from: 開始日（YYYY-MM-DD形式）
        date_to: 終了日（YYYY-MM-DD形式）

    Returns:
        dict: {
            "trend_summary": str,
            "case_count": int,
            "time_period": {"from": str, "to": str},
            "key_developments": list[str],
            "landmark_cases": list[dict],
            "legal_area": str,
            "jurisdiction": str
        }
    """
    year_from = int(date_from[:4]) if date_from else None
    year_to = int(date_to[:4]) if date_to else None

    # Search cases in the specified area and time period
    results = search_case_law(
        jurisdiction=jurisdiction,
        topic=legal_area,
        year_from=year_from,
        year_to=year_to,
    )

    cases = results if isinstance(results, list) else results.get("cases", [])

    return {
        "trend_summary": f"Found {len(cases)} cases in {legal_area} "
                        f"({jurisdiction}, {year_from or 'all'}-{year_to or 'present'})",
        "case_count": len(cases),
        "time_period": {"from": date_from or "all", "to": date_to or "present"},
        "key_developments": [c.get("title", "") for c in cases[:5]],
        "landmark_cases": cases[:10],
        "legal_area": legal_area,
        "jurisdiction": jurisdiction,
    }


@mcp.tool()
def tool_search_ip_stats(
    jurisdiction: str,
    indicator: str = "patent_applications",
    year_from: int | None = None,
    limit: int = 10,
    source: str = "auto",
):
    """Search IP statistics (patents, trademarks, GII rankings) by jurisdiction and indicator."""
    return search_ip_stats(
        jurisdiction=jurisdiction,
        indicator=indicator,
        year_from=year_from,
        limit=limit,
        source=source,
    )


@mcp.tool()
def tool_ip_dispute_search(
    query: str,
    jurisdiction: str = "GLOBAL",
    year_from: int | None = None,
    limit: int = 10,
    source: str = "auto",
):
    """Search IP disputes and enforcement data (UDRP/Section337/EPO Opposition/PTAB/Special301/CBP)."""
    return ip_dispute_search(
        query=query,
        jurisdiction=jurisdiction,
        year_from=year_from,
        limit=limit,
        source=source,
    )


@mcp.tool()
def tool_ip_enforcement_profile(jurisdiction: str, year: int | None = None):
    """Return integrated IP enforcement profile (Special 301 + seizures + Notorious Markets)."""
    return ip_enforcement_profile(jurisdiction=jurisdiction, year=year)


@mcp.tool()
def tool_ip_dispute_forum_comparison(year: int = 2023):
    """Compare IP dispute forum volumes: UDRP vs Section 337 vs EPO Opposition vs PTAB."""
    return ip_dispute_forum_comparison(year=year)


@mcp.tool()
def tool_ip_list_dispute_indicators():
    """List all available IP dispute and enforcement indicators by source."""
    return ip_list_dispute_indicators()


# ─────────────────────────────────────────────────────────
# Judgment Metadata Extraction Tool
# ─────────────────────────────────────────────────────────

@mcp.tool()
def extract_case_metadata(
    text: str,
    hint_source: str | None = None,
    llm_filled: dict | None = None,
):
    """
    Extract structured metadata from a judgment / decision / UDRP / opposition text.

    Workflow:
      1. Call with text + hint_source → get partially-extracted JSON schema (dates,
         case numbers, damages, provisions extracted by regex).
      2. The calling LLM fills in the remaining fields (parties, liability,
         technical_sector, notes, etc.) using its language understanding.
      3. Call again with llm_filled=<your completed dict> to normalize dates,
         resolve entity names, validate schema, and get the final clean JSON.

    Args:
      text:        Raw judgment text (any language).
      hint_source: Source hint for procedure/ip_field defaults.
                   Values: "PTAB", "ITC337", "EPO-Opposition", "WIPO-UDRP",
                           "UPC", "JP-Court", "CN-Court", "CourtListener", etc.
      llm_filled:  If provided, skip extraction and normalize/validate this dict instead.

    Returns:
      dict with:
        "schema"      – the (partial or complete) metadata JSON
        "valid"       – True if schema passes validation
        "issues"      – list of validation issues (empty if valid)
        "instructions"– guidance for the LLM on which fields still need filling
    """
    import json

    if llm_filled is not None:
        # Phase 2: normalize + validate LLM-completed metadata
        normalized = normalize_metadata(llm_filled)
        valid, issues = validate_schema(normalized)
        return {
            "schema": normalized,
            "valid": valid,
            "issues": issues,
            "instructions": "Metadata normalized and validated. Review 'issues' for any remaining problems.",
        }

    # Phase 1: deterministic extraction
    extracted = partial_extract(text, hint_source=hint_source)
    valid, issues = validate_schema(extracted)

    # Build instructions for LLM
    null_fields = []
    ci = extracted.get("case_id", {})
    if not ci.get("court_name"):   null_fields.append("case_id.court_name")
    if not ci.get("country_or_region"): null_fields.append("case_id.country_or_region")
    if not ci.get("source"):       null_fields.append("case_id.source")
    if not extracted.get("procedure", {}).get("technical_sector"):
        null_fields.append("procedure.technical_sector")
    if not extracted.get("parties", {}).get("plaintiffs"):
        null_fields.append("parties.plaintiffs[]")
    if not extracted.get("parties", {}).get("defendants"):
        null_fields.append("parties.defendants[]")
    if not extracted.get("outcome", {}).get("liability"):
        null_fields.append("outcome.liability")
    if not extracted.get("outcome", {}).get("injunction"):
        null_fields.append("outcome.injunction")
    if not extracted.get("citations", {}).get("case_law"):
        null_fields.append("citations.case_law[]")
    if not extracted.get("notes"):
        null_fields.append("notes")

    instructions = (
        f"Regex extraction complete. The following {len(null_fields)} fields still need "
        f"LLM completion: {', '.join(null_fields)}. "
        "Fill them in the 'schema', then call extract_case_metadata(llm_filled=<completed_schema>) "
        "to normalize and validate."
    )

    return {
        "schema": extracted,
        "valid": valid,
        "issues": issues,
        "instructions": instructions,
    }


@mcp.tool()
def case_metadata_schema() -> dict:
    """
    Return the empty case metadata schema template.
    Use this to understand the required JSON structure before filling manually.
    """
    return build_empty_schema()


# ─────────────────────────────────────────────────────────
# Entity Resolution Tools
# ─────────────────────────────────────────────────────────

@mcp.tool()
def ip_entity_resolve(query: str, limit: int = 5):
    """
    Resolve a company/organization name to its canonical form.
    Returns canonical name, ID, country, known aliases, and confidence score.
    Useful before running ip_entity_profile to verify the correct entity.
    Accepts any language and format (English, Japanese, Chinese, etc.).
    """
    results = []
    # Try exact/normalized/fuzzy resolution
    result = _entity_resolver.resolve(query)
    if result:
        e = result.entity
        results.append({
            "canonical_id": e.canonical_id,
            "canonical_name": e.canonical_name,
            "country_code": e.country_code,
            "entity_type": e.entity_type,
            "industry": e.industry,
            "parent_id": e.parent_id,
            "confidence": round(result.confidence, 3),
            "match_level": result.match_level,
            "aliases_sample": sorted(e.aliases)[:5],
        })
    # Also search for similar names
    search_hits = _entity_registry.search(query, limit=limit)
    seen_ids = {result.entity.canonical_id} if result else set()
    for e in search_hits:
        if e.canonical_id not in seen_ids:
            seen_ids.add(e.canonical_id)
            results.append({
                "canonical_id": e.canonical_id,
                "canonical_name": e.canonical_name,
                "country_code": e.country_code,
                "entity_type": e.entity_type,
                "industry": e.industry,
                "parent_id": e.parent_id,
                "confidence": None,
                "match_level": None,
                "aliases_sample": sorted(e.aliases)[:5],
            })
    return results[:limit]


@mcp.tool()
def ip_entity_profile(entity: str, year: int | None = None, group: bool = False):
    """
    Cross-source IP activity profile for a company/organization.
    Searches available data sources for the entity's IP footprint.

    Returns:
      - Resolved canonical entity info
      - Patent filing activity (PCT, national offices if data available)
      - SEP/FRAND involvement
      - Dispute involvement (PTAB, ITC, EPO opposition, UPC)
      - Enforcement issues (USTR 301 mention if any)
      - Technology trends
    """
    from tools.core.ip_disputes import ADAPTERS as DISPUTE_ADAPTERS
    result = _entity_resolver.resolve(entity)
    if result is None:
        return {"error": f"Entity not found: '{entity}'. Use ip_entity_resolve to search.", "query": entity}

    e = result.entity
    # Collect all aliases for search
    search_terms = list(e.aliases | {e.canonical_name, e.canonical_id})
    if group and e.parent_id:
        parent = _entity_registry.get(e.parent_id)
        if parent:
            search_terms += list(parent.aliases | {parent.canonical_name})
    # Also get subsidiaries if group=True
    if group:
        children = [c for c in _entity_registry.all_entities() if c.parent_id == e.canonical_id]
        for child in children:
            search_terms += list(child.aliases | {child.canonical_name})

    profile: dict = {
        "entity": {
            "canonical_id": e.canonical_id,
            "canonical_name": e.canonical_name,
            "country_code": e.country_code,
            "entity_type": e.entity_type,
            "industry": e.industry,
        },
        "resolution": {"confidence": result.confidence, "match_level": result.match_level},
        "ip_data": {},
    }

    # Search each dispute/stats adapter for entity mentions
    for source_id, adapter_cls in DISPUTE_ADAPTERS.items():
        try:
            adapter = adapter_cls()
            for term in search_terms[:3]:  # limit search terms to avoid slowness
                rows = adapter.search_disputes(
                    query=term.lower(),
                    jurisdiction=e.country_code,
                    year_from=year,
                    limit=5,
                )
                if rows:
                    if source_id not in profile["ip_data"]:
                        profile["ip_data"][source_id] = []
                    profile["ip_data"][source_id].extend(rows)
        except Exception:
            continue

    profile["sources_with_data"] = [k for k, v in profile["ip_data"].items() if v]
    profile["total_data_points"] = sum(len(v) for v in profile["ip_data"].values())
    return profile


@mcp.tool()
def ip_entity_search(
    query: str | None = None,
    country_code: str | None = None,
    entity_type: str | None = None,
    industry: str | None = None,
    limit: int = 20,
):
    """
    Search the entity registry by name, country, type, or industry.
    entity_type: "corporation", "npe", "university", "government", "individual"
    industry: "telecommunications", "semiconductors", "pharmaceuticals", "automotive", etc.
    """
    results = _entity_registry.all_entities()
    if query:
        q = query.lower()
        results = [e for e in results
                   if q in e.canonical_id or q in e.canonical_name.lower()
                   or any(q in a.lower() for a in e.aliases)]
    if country_code:
        results = [e for e in results if e.country_code == country_code.upper()]
    if entity_type:
        results = [e for e in results if e.entity_type == entity_type.lower()]
    if industry:
        results = [e for e in results if e.industry and industry.lower() in e.industry.lower()]
    return [
        {
            "canonical_id": e.canonical_id,
            "canonical_name": e.canonical_name,
            "country_code": e.country_code,
            "entity_type": e.entity_type,
            "industry": e.industry,
            "parent_id": e.parent_id,
            "alias_count": len(e.aliases),
        }
        for e in results[:limit]
    ]


# ─────────────────────────────────────────────────────────
# Event Detection Tools
# ─────────────────────────────────────────────────────────

@mcp.tool()
def ip_events_detect(
    severity: str | None = None,
    source_id: str | None = None,
    country_code: str | None = None,
    limit: int = 20,
):
    """
    Detect changes and notable events across all IP data sources.
    Compares current values against previous snapshots.

    Args:
      severity: Filter by "critical", "warning", or "info" (None = all)
      source_id: Filter by specific data source ID
      country_code: Filter by country (e.g., "US", "CN", "DE")
      limit: Max events to return

    Returns list of detected events sorted by severity then recency.
    Emoji indicators: 🔴 CRITICAL, 🟡 WARNING, 🔵 INFO
    """
    if source_id:
        events = _event_detector.detect_for_source(source_id)
    elif country_code:
        events = _event_detector.detect_for_country(country_code)
    else:
        events = _event_detector.detect_all(severity_filter=severity, limit=limit)
    if severity and not source_id:
        events = [e for e in events if e.severity == severity]
    formatted = _event_detector.format_events(events[:limit])
    return {
        "events_detected": len(events[:limit]),
        "formatted": formatted,
        "raw": [
            {
                "rule_id": e.rule_id,
                "severity": e.severity,
                "title": e.title,
                "description": e.description,
                "source_id": e.source_id,
                "indicator": e.indicator,
                "country_code": e.country_code,
                "old_value": e.old_value,
                "new_value": e.new_value,
                "change_pct": e.change_pct,
                "detected_at": e.detected_at,
            }
            for e in events[:limit]
        ],
    }


@mcp.tool()
def ip_events_snapshot(source_id: str | None = None):
    """
    Take a snapshot of current IP statistics for future change detection.
    Run periodically to enable ip_events_detect to find changes.

    Args:
      source_id: Snapshot specific source only (None = all sources)

    Returns summary: number of indicators captured, timestamp.
    """
    from tools.core.ip_disputes import ADAPTERS as DISPUTE_ADAPTERS
    from datetime import datetime, timezone

    if source_id:
        adapters = {source_id: DISPUTE_ADAPTERS[source_id]} if source_id in DISPUTE_ADAPTERS else {}
    else:
        adapters = DISPUTE_ADAPTERS

    count = _snapshot_store.take_full_snapshot(adapters)
    return {
        "snapshots_saved": count,
        "sources_processed": len(adapters),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": f"Snapshot complete: {count} indicators saved from {len(adapters)} sources.",
    }


@mcp.tool()
def ip_events_history(
    days_back: int = 30,
    severity: str | None = None,
    country_code: str | None = None,
    limit: int = 20,
):
    """
    View previously detected and recorded IP events.

    Args:
      days_back: Look back this many days (default 30)
      severity: Filter by "critical", "warning", or "info"
      country_code: Filter by country
      limit: Max events to return
    """
    history = _snapshot_store.get_event_history(
        days_back=days_back,
        severity=severity,
        country_code=country_code,
        limit=limit,
    )
    return {
        "events_found": len(history),
        "days_back": days_back,
        "events": history,
    }


from tools.core.playbook import generate_playbook as _generate_playbook, list_forums as _list_forums_db
from tools.core.dispute_profile import get_dispute_profile as _get_dispute_profile, get_sector_profile as _get_sector_profile

# ── Citation chain imports (Phase 4/5) ──
from tools.citation_extractor import extract_citations as _extract_citations
from tools.citation_resolver import resolve_citation as _resolve_citation
from tools.validity_checker import check_validity as _check_validity, get_citing_cases as _get_citing_cases, get_cited_cases as _get_cited_cases
from tools.storage import get_stats as _get_db_stats, get_connection as _get_db


@mcp.tool()
def assess_forum_and_risk(
    right_holder_country: str,
    target_service_type: str,
    target_server_locations: list[str],
    target_domain_tld: str | None = None,
    ip_right_type: str = "copyright",
    user_market_focus: list[str] | None = None,
    evidence_of_scale: str = "medium",
    prior_actions: list[str] | None = None,
) -> dict:
    """Generate a cross-border IP enforcement playbook with candidate forums and recommended strategy."""
    profile = {
        "right_holder_country": right_holder_country,
        "target_service_type": target_service_type,
        "target_server_locations": target_server_locations,
        "target_domain_tld": target_domain_tld,
        "ip_right_type": ip_right_type,
        "user_market_focus": user_market_focus or [],
        "evidence_of_scale": evidence_of_scale,
        "prior_actions": prior_actions or [],
    }
    return _generate_playbook(profile)


@mcp.tool()
def get_ip_dispute_profile(
    target_entities: list[str],
    year_from: int | None = None,
    year_to: int | None = None,
    ip_field: list[str] | None = None,
    role: list[str] | None = None,
) -> dict:
    """Get IP litigation analytics for specified entities. Returns case counts, win/loss ratio, key counterparties."""
    time_range: dict = {}
    if year_from:
        time_range["from"] = f"{year_from}-01-01"
    if year_to:
        time_range["to"] = f"{year_to}-12-31"
    filters: dict = {}
    if ip_field:
        filters["ip_field"] = ip_field
    if role:
        filters["role"] = role
    return _get_dispute_profile(
        target_entities=target_entities,
        time_range=time_range,
        filters=filters,
        group_by=["country_or_region", "forum", "technical_sector"],
    )


@mcp.tool()
def tool_analyze_party_performance(
    entity: str,
    sector: str = "cdn_provider",
    cases: list[dict] | None = None,
) -> dict:
    """
    Analyze litigation party performance with quality-controlled statistical analysis.

    Returns standardized analytics output including:
    - Win rate with Bayesian confidence intervals
    - Benchmark comparison vs sector average
    - Temporal trend analysis (improving/declining/stable)
    - Geographic segmentation & weakest segment identification
    - Statistical outlier detection (3σ threshold)
    - Red flags and priority-ranked strategic recommendations

    Args:
        entity: Party name to analyze (e.g., "Cloudflare", "Google")
        sector: Industry sector for benchmarking, one of:
            - "cdn_provider" (default): CDN/hosting providers
            - "streaming_platform": Video/audio streaming services
            - "ecommerce_marketplace": E-commerce platforms
        cases: Optional list of case dicts. If None, searches case law database.
            Each case should have: case_id, case_name, parties, defendants,
            jurisdiction, year, result.

    Returns:
        dict with AnalyticsOutput schema (15 mandatory fields):
        - metric_value: float (e.g., 0.68 for 68% win rate)
        - metric_name: str (e.g., "defendant_win_rate")
        - n_cases: int (sample size)
        - confidence_interval: [float, float] (95% Bayesian CI)
        - sample_quality: "reliable" | "limited" | "unreliable"
        - sector_benchmark: float (industry average)
        - benchmark_delta: float (difference from benchmark)
        - timeline: [[year, rate], ...] (temporal trend data)
        - trend: "improving" | "declining" | "stable"
        - trend_rate: float | null (percentage change per year)
        - segments: {jurisdiction: rate, ...}
        - weakest_segment: [jurisdiction, rate] | null
        - outliers: [str, ...] (3σ outliers)
        - red_flags: [str, ...] (warnings)
        - supporting_cases: [case_id, ...]

    Example:
        >>> tool_analyze_party_performance("Cloudflare", "cdn_provider")
        {
          "metric_value": 0.68,
          "n_cases": 73,
          "sample_quality": "reliable",
          "confidence_interval": [0.57, 0.77],
          "sector_benchmark": 0.55,
          "benchmark_delta": 0.13,
          "trend": "declining",
          "weakest_segment": ["France", 0.25],
          "red_flags": ["Critical weakness in France: 25% vs overall 68%"],
          ...
        }

    Quality Guarantees:
    - ALL numbers computed in Python (zero hallucination risk)
    - Mandatory confidence interval disclosure
    - Mandatory benchmark comparison
    - Mandatory sample size disclosure
    - Sample quality assessment (reliable: N≥30, limited: N≥10, unreliable: N<10)
    """
    # If no cases provided, search case law database
    if cases is None:
        # Search for cases involving this entity
        # TODO: Integrate with search_case_law() when case DB is populated
        # For now, return instructive error
        return {
            "error": "Case database integration pending",
            "message": (
                f"To analyze {entity}, please provide 'cases' parameter with case list. "
                "Automatic case DB search will be available after case ingestion."
            ),
            "required_case_format": {
                "case_id": "str (unique identifier)",
                "case_name": "str (e.g., 'Plaintiff v. Defendant')",
                "parties": ["str", "..."],
                "defendants": ["str", "..."],
                "jurisdiction": "str (e.g., 'US', 'FR', 'JP')",
                "year": "int (e.g., 2023)",
                "result": "str ('defendant_win', 'plaintiff_win', 'dismissed', 'settled')"
            },
            "example_usage": {
                "tool": "tool_analyze_party_performance",
                "args": {
                    "entity": entity,
                    "sector": sector,
                    "cases": [
                        {
                            "case_id": "example_1",
                            "case_name": "Plaintiff v. " + entity,
                            "parties": ["Plaintiff", entity],
                            "defendants": [entity],
                            "jurisdiction": "US",
                            "year": 2023,
                            "result": "defendant_win"
                        }
                    ]
                }
            }
        }

    # Analyze with quality guardrails
    analyzer = PartyAnalyzer(cases, SECTOR_BENCHMARKS)
    try:
        result = analyzer.analyze_defendant_performance(entity, sector)
        return result.to_dict()
    except ValueError as e:
        return {
            "error": str(e),
            "entity": entity,
            "n_cases_provided": len(cases),
            "hint": "Ensure cases contain the entity as defendant and have required fields"
        }


@mcp.tool()
def tool_generate_strategic_recommendations(analytics_output: dict) -> list[dict]:
    """
    Generate priority-ranked strategic recommendations from analytics output.

    Takes AnalyticsOutput dict (from tool_analyze_party_performance) and applies
    decision tree logic to generate priority-ranked recommendations.

    Priority levels:
    - URGENT (🔴): sample_quality="unreliable" OR critical geographic weakness
    - SHORT_TERM (🟡): declining trend OR below benchmark by >10pt
    - MID_TERM (🟢): optimization opportunities
    - LONG_TERM (🔵): strategic positioning

    Args:
        analytics_output: dict returned from tool_analyze_party_performance

    Returns:
        list of Recommendation dicts, each containing:
        - priority: "URGENT" | "SHORT_TERM" | "MID_TERM" | "LONG_TERM"
        - icon: str (emoji indicator)
        - action: str (1-sentence action item)
        - rationale: str (2-3 sentence quantitative justification)

    Example:
        >>> recs = tool_generate_strategic_recommendations(analytics_result)
        >>> recs[0]
        {
          "priority": "URGENT",
          "icon": "🔴",
          "action": "Challenge jurisdiction or settle in France cases",
          "rationale": "Critical weakness in France (25% vs 68% overall). ..."
        }
    """
    from tools.analytics import AnalyticsOutput

    # Convert dict back to AnalyticsOutput
    try:
        analytics = AnalyticsOutput(**analytics_output)
        recs = generate_recommendations(analytics)
        return [
            {
                "priority": r.priority,
                "icon": r.icon,
                "action": r.action,
                "rationale": r.rationale
            }
            for r in recs
        ]
    except Exception as e:
        return [{
            "error": str(e),
            "hint": "Ensure analytics_output is valid AnalyticsOutput dict from tool_analyze_party_performance"
        }]


# ═══════════════════════════════════════════════════════════════
# Citation Chain Tools (Phase 5: Layer 1 citation chain)
# ═══════════════════════════════════════════════════════════════

@mcp.tool()
def check_citation(case_id: str) -> dict:
    """
    Check whether a case has been overruled, distinguished, or is still good law.

    Returns a traffic-light signal:
      - GREEN: No negative treatment found
      - YELLOW: Distinguished/questioned but not overruled
      - RED: Overruled by higher court
      - UNKNOWN: Case not found or no citing cases in DB

    Args:
        case_id: The case ID in format "JURISDICTION:source_id" (e.g., "US:12345")

    Returns:
        dict with signal, reason, citing_count, and overruling_cases details
    """
    return _check_validity(case_id)


@mcp.tool()
def tool_get_citing_cases(case_id: str, limit: int = 20) -> dict:
    """
    Get cases that cite a given case, with treatment analysis.

    Each citing case includes treatment detection:
      - "neutral": Standard citation
      - "distinguishing": Case was distinguished or questioned
      - "overruling": Case was overruled or reversed

    Args:
        case_id: The cited case's ID
        limit: Maximum number of results (default 20)

    Returns:
        dict with citing_cases list and count
    """
    cases = _get_citing_cases(case_id, limit=limit)
    return {
        "case_id": case_id,
        "citing_cases": cases,
        "count": len(cases),
    }


@mcp.tool()
def tool_get_cited_cases(case_id: str) -> dict:
    """
    Get all cases cited by a given case.

    Args:
        case_id: The citing case's ID

    Returns:
        dict with cited_cases list and count
    """
    cases = _get_cited_cases(case_id)
    return {
        "case_id": case_id,
        "cited_cases": cases,
        "count": len(cases),
    }


@mcp.tool()
def tool_extract_citations(text: str, jurisdiction: str = "US") -> dict:
    """
    Extract legal citations from text using jurisdiction-specific patterns.

    Supports 12 jurisdictions: US, EU, UK, JP, DE, IN, AU, FR, CA, NZ, KR, BR.

    Args:
        text: The legal text to extract citations from
        jurisdiction: Primary jurisdiction for pattern matching (default "US")

    Returns:
        dict with citations list (each with citation_string, jurisdiction, position, context) and count
    """
    citations = _extract_citations(text, jurisdiction)
    return {
        "jurisdiction": jurisdiction,
        "citations": citations,
        "count": len(citations),
    }


@mcp.tool()
def get_caselaw_db_stats() -> dict:
    """
    Get current caselaw database statistics.

    Returns:
        dict with total_cases, total_citations, and by_jurisdiction breakdown
    """
    return _get_db_stats()


# ═══════════════════════════════════════════════════════════════
# Layer 3 Analytics Tools
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
def get_judge_stats(
    judge_name: str,
    jurisdiction: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict:
    """
    判事の統計情報を返す: 担当件数、結果分布、法分野、活動期間。

    Args:
        judge_name: 判事名（部分一致検索）
        jurisdiction: 管轄フィルタ（US, JP, EU, etc.）
        year_from: 開始年フィルタ
        year_to: 終了年フィルタ

    Returns:
        dict: total_cases, outcome_distribution, case_type_distribution,
              earliest_date, latest_date, courts, top_topics
    """
    import json as _json

    conn = _get_db()
    sql = """
        SELECT c.case_id, c.case_name, c.jurisdiction, c.court,
               c.decision_date, c.case_type, c.subject_area, c.outcome,
               c.raw_metadata
        FROM cases c
        WHERE c.raw_metadata LIKE ?
    """
    params: list = [f"%{judge_name}%"]

    if jurisdiction:
        sql += " AND c.jurisdiction = ?"
        params.append(jurisdiction)
    if year_from:
        sql += " AND c.decision_date >= ?"
        params.append(f"{year_from}-01-01")
    if year_to:
        sql += " AND c.decision_date <= ?"
        params.append(f"{year_to}-12-31")
    sql += " ORDER BY c.decision_date DESC LIMIT 500"

    rows = conn.execute(sql, params).fetchall()

    # Filter to rows where judge_names actually contains the name
    matched = []
    for r in rows:
        meta = r["raw_metadata"]
        if not meta:
            continue
        try:
            md = _json.loads(meta) if isinstance(meta, str) else meta
        except (ValueError, TypeError):
            continue
        judges = md.get("judge_names", "")
        if isinstance(judges, list):
            judges = " ".join(judges)
        if judge_name.lower() in str(judges).lower():
            matched.append(r)

    if not matched:
        return {"error": f"No cases found for judge '{judge_name}'", "total_cases": 0}

    # Compute distributions
    outcomes: dict[str, int] = {}
    case_types: dict[str, int] = {}
    courts: dict[str, int] = {}
    dates = []

    for r in matched:
        o = r["outcome"] or "unknown"
        outcomes[o] = outcomes.get(o, 0) + 1
        ct = r["case_type"] or "unknown"
        case_types[ct] = case_types.get(ct, 0) + 1
        court = r["court"] or "unknown"
        courts[court] = courts.get(court, 0) + 1
        if r["decision_date"]:
            dates.append(r["decision_date"])

    dates.sort()

    return {
        "judge_name": judge_name,
        "total_cases": len(matched),
        "outcome_distribution": dict(sorted(outcomes.items(), key=lambda x: -x[1])),
        "case_type_distribution": dict(sorted(case_types.items(), key=lambda x: -x[1])),
        "courts": dict(sorted(courts.items(), key=lambda x: -x[1])),
        "earliest_date": dates[0] if dates else None,
        "latest_date": dates[-1] if dates else None,
        "sample_cases": [
            {"case_id": r["case_id"], "case_name": r["case_name"], "date": r["decision_date"]}
            for r in matched[:10]
        ],
    }


@mcp.tool()
async def compare_jurisdictions(
    topic: str,
    jurisdictions: list[str],
    max_results_per_jurisdiction: int = 10,
) -> dict:
    """
    指定トピックについて複数法域の判例を横断比較する。

    件数、時期の分布、結果の傾向、裁判所レベルを法域ごとに集計し
    横断的な比較分析を返す。

    Args:
        topic: 検索トピック（例: "platform liability", "著作権侵害", "GDPR"）
        jurisdictions: 比較対象の法域リスト（例: ["US", "EU", "JP", "GB"]）
        max_results_per_jurisdiction: 各法域の最大取得件数

    Returns:
        dict: per-jurisdiction stats, comparison summary, timeline
    """
    conn = _get_db()
    comparison = {}

    for jur in jurisdictions:
        # FTS5 search per jurisdiction
        try:
            conn.execute("SELECT 1 FROM cases_fts LIMIT 0")
            safe_terms = []
            for t in topic.strip().split():
                if t.strip():
                    escaped = t.strip().replace('"', '""')
                    safe_terms.append(f'"{escaped}"')
            fts_query = " ".join(safe_terms)

            sql = """
                SELECT c.case_id, c.case_name, c.jurisdiction, c.court,
                       c.decision_date, c.case_type, c.outcome, c.has_content
                FROM cases_fts f
                JOIN cases c ON c.rowid = f.rowid
                WHERE cases_fts MATCH ? AND c.jurisdiction = ?
                ORDER BY bm25(cases_fts, 10.0, 1.0)
                LIMIT ?
            """
            rows = conn.execute(sql, [fts_query, jur, max_results_per_jurisdiction]).fetchall()
        except Exception:
            # Fallback to LIKE search
            sql = """
                SELECT case_id, case_name, jurisdiction, court,
                       decision_date, case_type, outcome, has_content
                FROM cases
                WHERE jurisdiction = ? AND (case_name LIKE ? OR full_text LIKE ?)
                ORDER BY decision_date DESC
                LIMIT ?
            """
            rows = conn.execute(
                sql, [jur, f"%{topic}%", f"%{topic}%", max_results_per_jurisdiction]
            ).fetchall()

        # Aggregate per jurisdiction
        outcomes: dict[str, int] = {}
        years: dict[int, int] = {}
        courts_set: set[str] = set()

        for r in rows:
            o = r["outcome"] or "unknown"
            outcomes[o] = outcomes.get(o, 0) + 1
            if r["decision_date"]:
                try:
                    yr = int(r["decision_date"][:4])
                    years[yr] = years.get(yr, 0) + 1
                except (ValueError, IndexError):
                    pass
            if r["court"]:
                courts_set.add(r["court"])

        comparison[jur] = {
            "case_count": len(rows),
            "outcome_distribution": dict(sorted(outcomes.items(), key=lambda x: -x[1])),
            "year_distribution": dict(sorted(years.items())),
            "courts": sorted(courts_set),
            "sample_cases": [
                {
                    "case_id": r["case_id"],
                    "case_name": r["case_name"],
                    "date": r["decision_date"],
                    "outcome": r["outcome"],
                }
                for r in rows[:5]
            ],
        }

    # Build comparison summary
    total_cases = sum(v["case_count"] for v in comparison.values())
    most_active = max(comparison.items(), key=lambda x: x[1]["case_count"])[0] if comparison else None

    return {
        "topic": topic,
        "jurisdictions_compared": jurisdictions,
        "total_cases_found": total_cases,
        "most_active_jurisdiction": most_active,
        "per_jurisdiction": comparison,
    }


@mcp.tool()
def get_citation_network(
    case_id: str,
    depth: int = 2,
    max_nodes: int = 50,
) -> dict:
    """
    指定判例を中心とした引用ネットワークをグラフ形式で返す。

    BFSで引用チェーンを辿り、ノード（判例）とエッジ（引用関係）を返す。
    ハブ判例（被引用数が多い）の特定も行う。

    Args:
        case_id: 起点となる判例ID（例: "US:cl:12345"）
        depth: 探索深度（1=直接引用のみ、2=引用の引用まで）。最大3。
        max_nodes: ネットワーク内の最大ノード数

    Returns:
        dict: nodes (判例メタデータ), edges (引用関係), hub_nodes (被引用数上位)
    """
    conn = _get_db()
    depth = min(depth, 3)

    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    frontier = {case_id}
    visited: set[str] = set()

    for d in range(depth):
        if not frontier or len(nodes) >= max_nodes:
            break

        next_frontier: set[str] = set()
        for cid in frontier:
            if cid in visited or len(nodes) >= max_nodes:
                continue
            visited.add(cid)

            # Get case metadata if not already fetched
            if cid not in nodes:
                row = conn.execute(
                    "SELECT case_id, case_name, jurisdiction, court, decision_date FROM cases WHERE case_id = ?",
                    [cid],
                ).fetchone()
                if row:
                    nodes[cid] = {
                        "case_id": row["case_id"],
                        "case_name": row["case_name"],
                        "jurisdiction": row["jurisdiction"],
                        "court": row["court"],
                        "date": row["decision_date"],
                        "depth": d,
                    }

            # Forward citations (cases that cite this case)
            citing = conn.execute(
                "SELECT citing_case_id FROM case_citations WHERE cited_case_id = ? LIMIT ?",
                [cid, max_nodes],
            ).fetchall()
            for r in citing:
                src = r["citing_case_id"]
                edges.append({"source": src, "target": cid, "type": "cites"})
                if src not in visited and len(nodes) < max_nodes:
                    next_frontier.add(src)

            # Backward citations (cases cited by this case)
            cited = conn.execute(
                "SELECT cited_case_id FROM case_citations WHERE citing_case_id = ? AND cited_case_id IS NOT NULL LIMIT ?",
                [cid, max_nodes],
            ).fetchall()
            for r in cited:
                tgt = r["cited_case_id"]
                edges.append({"source": cid, "target": tgt, "type": "cites"})
                if tgt not in visited and len(nodes) < max_nodes:
                    next_frontier.add(tgt)

        # Fetch metadata for new frontier nodes
        for fid in next_frontier:
            if fid not in nodes and len(nodes) < max_nodes:
                row = conn.execute(
                    "SELECT case_id, case_name, jurisdiction, court, decision_date FROM cases WHERE case_id = ?",
                    [fid],
                ).fetchone()
                if row:
                    nodes[fid] = {
                        "case_id": row["case_id"],
                        "case_name": row["case_name"],
                        "jurisdiction": row["jurisdiction"],
                        "court": row["court"],
                        "date": row["decision_date"],
                        "depth": d + 1,
                    }

        frontier = next_frontier

    # Deduplicate edges
    seen_edges: set[tuple[str, str]] = set()
    unique_edges = []
    for e in edges:
        key = (e["source"], e["target"])
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(e)

    # Identify hub nodes (most cited)
    cite_counts: dict[str, int] = {}
    for e in unique_edges:
        cite_counts[e["target"]] = cite_counts.get(e["target"], 0) + 1

    hub_nodes = sorted(cite_counts.items(), key=lambda x: -x[1])[:10]

    return {
        "center": case_id,
        "depth": depth,
        "node_count": len(nodes),
        "edge_count": len(unique_edges),
        "nodes": list(nodes.values()),
        "edges": unique_edges,
        "hub_nodes": [
            {"case_id": cid, "cited_by_count": cnt, **nodes.get(cid, {})}
            for cid, cnt in hub_nodes
        ],
    }


# ═══════════════════════════════════════════════════════════════
# Phase 4 Tools — Extended Schema
# ═══════════════════════════════════════════════════════════════

@mcp.tool()
def search_cases_advanced(
    query: str,
    jurisdiction: str | None = None,
    case_type: str | None = None,
    subject_area: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    max_results: int = 20,
) -> dict:
    """
    Advanced case search with type/subject/date filters.

    Args:
        query: Search text (case name, keywords, or party name)
        jurisdiction: Filter by jurisdiction code (US, EU, JP, IN, etc.)
        case_type: Filter by case type (ip, criminal, civil, labor, administrative, constitutional, family)
        subject_area: Filter by subject (patent, copyright, trademark, data_privacy, antitrust, etc.)
        year_from: Start year filter
        year_to: End year filter
        max_results: Maximum results to return
    """
    conn = _get_db()
    params = []

    # Try FTS5 first for text search
    use_fts5 = False
    if query:
        try:
            # Test FTS5 availability
            conn.execute("SELECT 1 FROM cases_fts LIMIT 0")
            use_fts5 = True
        except Exception:
            pass

    if use_fts5 and query:
        # FTS5 search with BM25 ranking
        safe_terms = []
        for t in query.strip().split():
            if t.strip():
                escaped = t.strip().replace('"', '""')
                safe_terms.append(f'"{escaped}"')
        fts_query = " ".join(safe_terms)

        sql = """SELECT c.case_id, c.case_name, c.jurisdiction, c.court, c.decision_date,
                 c.case_type, c.subject_area, c.outcome, c.importance_score,
                 c.has_content, length(c.full_text) as text_len,
                 bm25(cases_fts, 10.0, 1.0) as score
                 FROM cases_fts f
                 JOIN cases c ON c.rowid = f.rowid
                 WHERE cases_fts MATCH ?"""
        params = [fts_query]
    else:
        sql = """SELECT case_id, case_name, jurisdiction, court, decision_date,
                 case_type, subject_area, outcome, importance_score,
                 has_content, length(full_text) as text_len
                 FROM cases WHERE 1=1"""
        if query:
            terms = query.strip().split()
            for term in terms:
                if term.strip():
                    sql += " AND (case_name LIKE ? OR full_text LIKE ?)"
                    params.extend([f"%{term.strip()}%", f"%{term.strip()}%"])

    if jurisdiction:
        jur_col = "c.jurisdiction" if use_fts5 else "jurisdiction"
        sql += f" AND {jur_col} = ?"
        params.append(jurisdiction)
    if case_type:
        ct_prefix = "c." if use_fts5 else ""
        sql += f" AND ({ct_prefix}case_type = ? OR {ct_prefix}case_type_suggested = ?)"
        params.extend([case_type, case_type])
    if subject_area:
        sa_prefix = "c." if use_fts5 else ""
        sql += f" AND ({sa_prefix}subject_area = ? OR {sa_prefix}subject_area_suggested = ?)"
        params.extend([subject_area, subject_area])
    if year_from:
        dd_col = "c.decision_date" if use_fts5 else "decision_date"
        sql += f" AND {dd_col} >= ?"
        params.append(f"{year_from}-01-01")
    if year_to:
        dd_col = "c.decision_date" if use_fts5 else "decision_date"
        sql += f" AND {dd_col} <= ?"
        params.append(f"{year_to}-12-31")

    if use_fts5:
        sql += " ORDER BY c.has_content DESC, score LIMIT ?"
    else:
        sql += " ORDER BY has_content DESC, importance_score DESC NULLS LAST LIMIT ?"
    params.append(max_results)

    rows = conn.execute(sql, params).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d.pop("score", None)
        results.append(d)
    return {
        "results": results,
        "count": len(results),
        "filters": {"jurisdiction": jurisdiction, "case_type": case_type,
                     "subject_area": subject_area},
        "search_mode": "fts5" if use_fts5 else "like",
    }


@mcp.tool()
def get_case_importance(case_id: str) -> dict:
    """
    Get importance score and citation network for a specific case.

    Args:
        case_id: The case identifier
    """
    conn = _get_db()
    case = conn.execute("""
        SELECT case_id, case_name, jurisdiction, court, importance_score,
               case_type, subject_area, outcome
        FROM cases WHERE case_id = ?
    """, (case_id,)).fetchone()

    if not case:
        return {"error": "Case not found"}

    citing = conn.execute("""
        SELECT c.case_id, c.case_name, c.jurisdiction
        FROM case_citations cc JOIN cases c ON cc.citing_case_id = c.case_id
        WHERE cc.cited_case_id = ?
    """, (case_id,)).fetchall()

    cited = conn.execute("""
        SELECT cc.cited_reference, cc.cited_case_id,
               c.case_name, c.jurisdiction
        FROM case_citations cc
        LEFT JOIN cases c ON cc.cited_case_id = c.case_id
        WHERE cc.citing_case_id = ?
    """, (case_id,)).fetchall()

    return {
        "case": dict(case),
        "cited_by": [dict(r) for r in citing],
        "cited_by_count": len(citing),
        "cites": [dict(r) for r in cited],
        "cites_count": len(cited),
    }


@mcp.tool()
def get_classification_stats() -> dict:
    """
    Get statistics on case classification (types, subjects, outcomes).
    """
    conn = _get_db()

    type_stats = conn.execute("""
        SELECT case_type, COUNT(*) as cnt FROM cases
        WHERE case_type IS NOT NULL
        GROUP BY case_type ORDER BY cnt DESC
    """).fetchall()

    subject_stats = conn.execute("""
        SELECT subject_area, COUNT(*) as cnt FROM cases
        WHERE subject_area IS NOT NULL
        GROUP BY subject_area ORDER BY cnt DESC
    """).fetchall()

    outcome_stats = conn.execute("""
        SELECT outcome, COUNT(*) as cnt FROM cases
        WHERE outcome IS NOT NULL
        GROUP BY outcome ORDER BY cnt DESC
    """).fetchall()

    return {
        "case_types": {r[0]: r[1] for r in type_stats},
        "subject_areas": {r[0]: r[1] for r in subject_stats},
        "outcomes": {r[0]: r[1] for r in outcome_stats},
    }


@mcp.tool()
def search_ip_disputes(
    query: str | None = None,
    dispute_type: str | None = None,
    jurisdiction: str | None = None,
    max_results: int = 20,
) -> dict:
    """
    Search IP disputes (UDRP, PTAB, EPO opposition, ITC 337, etc.).

    Args:
        query: Search text
        dispute_type: Filter by type (udrp, ptab, epo_opposition, itc337, upc, wipo_adr)
        jurisdiction: Filter by jurisdiction
        max_results: Maximum results
    """
    conn = _get_db()
    sql = "SELECT * FROM ip_disputes WHERE 1=1"
    params = []
    if query:
        sql += " AND (title LIKE ? OR full_text LIKE ?)"
        params.extend([f"%{query}%", f"%{query}%"])
    if dispute_type:
        sql += " AND dispute_type = ?"
        params.append(dispute_type)
    if jurisdiction:
        sql += " AND jurisdiction = ?"
        params.append(jurisdiction)
    sql += f" ORDER BY decision_date DESC LIMIT {max_results}"
    rows = conn.execute(sql, params).fetchall()
    return {"results": [dict(r) for r in rows], "count": len(rows)}


@mcp.tool()
def search_statutes_v2(
    query: str,
    jurisdiction: str | None = None,
    max_results: int = 10,
) -> dict:
    """
    Search statutes and legislation.

    Args:
        query: Search text (law name, section number, keywords)
        jurisdiction: Filter by jurisdiction
        max_results: Maximum results
    """
    conn = _get_db()
    params = []

    # Try FTS5 first
    use_fts5 = False
    if query:
        try:
            conn.execute("SELECT 1 FROM statutes_fts LIMIT 0")
            use_fts5 = True
        except Exception:
            pass

    if use_fts5 and query:
        safe_terms = []
        for t in query.strip().split():
            if t.strip():
                escaped = t.strip().replace('"', '""')
                safe_terms.append(f'"{escaped}"')
        fts_query = " ".join(safe_terms)

        sql = """SELECT s.*, bm25(statutes_fts, 10.0, 1.0) as score
                 FROM statutes_fts f
                 JOIN statutes s ON s.rowid = f.rowid
                 WHERE statutes_fts MATCH ?"""
        params = [fts_query]
        if jurisdiction:
            sql += " AND s.jurisdiction = ?"
            params.append(jurisdiction)
        sql += f" ORDER BY score LIMIT {max_results}"
    else:
        sql = "SELECT *, CASE WHEN title LIKE ? THEN 0 ELSE 1 END as title_rank FROM statutes WHERE 1=1"
        params = [f"%{query}%" if query else "%"]
        if query:
            terms = query.strip().split()
            for term in terms:
                if term.strip():
                    sql += " AND (title LIKE ? OR full_text LIKE ?)"
                    params.extend([f"%{term.strip()}%", f"%{term.strip()}%"])
        if jurisdiction:
            sql += " AND jurisdiction = ?"
            params.append(jurisdiction)
        sql += f" ORDER BY title_rank ASC, effective_date DESC LIMIT {max_results}"

    rows = conn.execute(sql, params).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d.pop("title_rank", None)
        d.pop("score", None)
        results.append(d)
    return {"results": results, "count": len(results), "search_mode": "fts5" if use_fts5 else "like"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Legal MCP server (Phase A)")
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default="stdio",
        help="MCP transport to use",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
