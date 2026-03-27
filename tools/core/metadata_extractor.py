"""
Judgment metadata extraction utilities for Legal MCP.

Flow:
  1. partial_extract(text, hint_source) → deterministic fields via regex
  2. normalize_metadata(raw_dict)       → date format, entity resolution, schema validation
  3. build_empty_schema()               → returns the schema template with all-null fields

The calling LLM (Claude) fills in the non-deterministic fields.
"""
from __future__ import annotations

import re
import json
from datetime import datetime
from typing import Any

# ── 日付パターン（多様な形式を YYYY-MM-DD に正規化）
_DATE_PATTERNS = [
    # 2024-01-15  2024/01/15
    (re.compile(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})'), '%Y-%m-%d'),
    # January 15, 2024  Jan. 15, 2024
    (re.compile(r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
                r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
                r'\.?\s+(\d{1,2}),?\s+(\d{4})', re.IGNORECASE), 'month_name'),
    # 15 January 2024
    (re.compile(r'(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
                r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
                r'\.?\s+(\d{4})', re.IGNORECASE), 'day_month_year'),
    # 令和5年1月15日 / 令和6年
    (re.compile(r'令和(\d+)年(\d{1,2})月(\d{1,2})日'), 'reiwa'),
    # 平成30年
    (re.compile(r'平成(\d+)年(\d{1,2})月(\d{1,2})日'), 'heisei'),
    # 2024年1月15日
    (re.compile(r'(\d{4})年(\d{1,2})月(\d{1,2})日'), '%Y-%m-%d'),
]

_MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
}

def _normalize_date(raw: str) -> str | None:
    """Try to convert date string to YYYY-MM-DD."""
    raw = raw.strip()
    for pat, fmt in _DATE_PATTERNS:
        m = pat.search(raw)
        if not m:
            continue
        try:
            if fmt == '%Y-%m-%d':
                y, mo, d = m.group(1), m.group(2), m.group(3)
                return f'{int(y):04d}-{int(mo):02d}-{int(d):02d}'
            elif fmt == 'month_name':
                mo_name, day, year = m.group(1).lower()[:3], m.group(2), m.group(3)
                mo = _MONTH_MAP.get(mo_name)
                if mo:
                    return f'{int(year):04d}-{mo:02d}-{int(day):02d}'
            elif fmt == 'day_month_year':
                day, mo_name, year = m.group(1), m.group(2).lower()[:3], m.group(3)
                mo = _MONTH_MAP.get(mo_name)
                if mo:
                    return f'{int(year):04d}-{mo:02d}-{int(day):02d}'
            elif fmt == 'reiwa':
                year = 2018 + int(m.group(1))  # 令和元年=2019
                return f'{year:04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'
            elif fmt == 'heisei':
                year = 1988 + int(m.group(1))  # 平成元年=1989
                return f'{year:04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'
        except (ValueError, TypeError):
            continue
    return None

# ── 金額パターン（数値 + 通貨）
_AMOUNT_PATTERNS = [
    # $1,234,567  USD 5,000,000
    re.compile(r'\$\s*([\d,]+(?:\.\d+)?)\s*(?:million|billion|M|B)?', re.IGNORECASE),
    re.compile(r'USD\s*([\d,]+(?:\.\d+)?)', re.IGNORECASE),
    re.compile(r'EUR\s*([\d,]+(?:\.\d+)?)', re.IGNORECASE),
    re.compile(r'€\s*([\d,]+(?:\.\d+)?)', re.IGNORECASE),
    re.compile(r'JPY\s*([\d,]+(?:\.\d+)?)', re.IGNORECASE),
    re.compile(r'¥\s*([\d,]+(?:\.\d+)?)', re.IGNORECASE),
    # 5億円 / 1億4,200万ユーロ
    re.compile(r'([\d,]+(?:\.\d+)?)\s*億\s*円', re.IGNORECASE),
    re.compile(r'([\d,]+(?:\.\d+)?)\s*万\s*円', re.IGNORECASE),
]

_CURRENCY_MAP = {
    '$': 'USD', 'USD': 'USD',
    '€': 'EUR', 'EUR': 'EUR',
    '¥': 'JPY', 'JPY': 'JPY', '円': 'JPY',
}

def _extract_amount(text: str) -> tuple[float | None, str | None]:
    """Extract first monetary amount and currency from text."""
    # 億円
    m = re.search(r'([\d,]+(?:\.\d+)?)\s*億\s*円', text)
    if m:
        val = float(m.group(1).replace(',', '')) * 1e8
        return val, 'JPY'
    m = re.search(r'([\d,]+(?:\.\d+)?)\s*万\s*円', text)
    if m:
        val = float(m.group(1).replace(',', '')) * 1e4
        return val, 'JPY'
    # €14.2 million  $5M
    m = re.search(r'(€|\$|USD|EUR|JPY|¥)\s*([\d,]+(?:\.\d+)?)\s*(million|billion|M|B)?', text, re.IGNORECASE)
    if m:
        sym = m.group(1).upper()
        val_str = m.group(2).replace(',', '')
        mult_str = (m.group(3) or '').lower()
        try:
            val = float(val_str)
            if mult_str in ('million', 'm'):
                val *= 1e6
            elif mult_str in ('billion', 'b'):
                val *= 1e9
            cur = _CURRENCY_MAP.get(sym, sym)
            return val, cur
        except ValueError:
            pass
    return None, None

# ── 事件番号パターン
_CASE_NUM_PATTERNS = [
    re.compile(r'IPR\d{4}-\d{5}', re.IGNORECASE),           # PTAB IPR
    re.compile(r'PGR\d{4}-\d{5}', re.IGNORECASE),           # PTAB PGR
    re.compile(r'ITC[-\s]?No\.?\s*\d{3}-\d+', re.IGNORECASE),  # ITC
    re.compile(r'(?:Case\s+)?D\d{4}-\d{4,5}', re.IGNORECASE),  # UDRP
    re.compile(r'T\s+\d{4}/\d{2}', re.IGNORECASE),          # EPO Opposition
    re.compile(r'App\.\s+No\.\s+[\d/]+', re.IGNORECASE),    # EPO appeal
    re.compile(r'\d+\s+U\.S\.C\b'),                          # US statute ref
    re.compile(r'(?:令和|平成)\d+年(?:\([ワアネ]\)|（[ワアネ]）)第?\d+号'),  # JP civil case
    re.compile(r'平成\d+年\(行ケ\)\d+号'),                    # JP IP High Court
    re.compile(r'\d{4}[A-Z]{1,3}\d{4,6}'),                  # UPC style
    re.compile(r'No\.\s*\d+[-\s]\w+[-\s]\d{4}', re.IGNORECASE),
]

def _extract_case_number(text: str) -> str | None:
    for pat in _CASE_NUM_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(0).strip()
    return None

# ── ソースヒント → 判定ロジック
_SOURCE_PROCEDURE_MAP = {
    'ptab':          ('administrative', 'patent'),
    'itc337':        ('administrative', 'patent'),
    'epo_opposition': ('opposition', 'patent'),
    'upc':           ('litigation', 'patent'),
    'wipo_adr':      ('UDRP', 'domain'),
    'udrp':          ('UDRP', 'domain'),
    'jp-court':      ('litigation', 'patent'),
    'cn-court':      ('litigation', 'patent'),
    'icc':           ('criminal', 'other'),
    'icsid':         ('arbitration', 'other'),
    'wto':           ('arbitration', 'other'),
    'courtlistener': ('litigation', 'patent'),
}

# ── Legal provision patterns
_PROVISION_PATTERNS = [
    re.compile(r'(?:§|section|art\.?|article)\s*\d+[\w()\.\-]*', re.IGNORECASE),
    re.compile(r'\d+\s+U\.S\.C\.?\s+§?\s*\d+\w*', re.IGNORECASE),
    re.compile(r'DMCA\s+§?\s*\d+\w*', re.IGNORECASE),
    re.compile(r'17\s+U\.S\.C\.?\s+§?\s*5\d{2}', re.IGNORECASE),
    re.compile(r'TRIPS\s+Art(?:icle)?\.?\s*\d+', re.IGNORECASE),
    re.compile(r'DSU\s+Art(?:icle)?\.?\s*\d+', re.IGNORECASE),
    re.compile(r'著作権法\s*第?\s*\d+\s*条', re.IGNORECASE),
    re.compile(r'特許法\s*第?\s*\d+\s*条', re.IGNORECASE),
]

def _extract_provisions(text: str, limit: int = 10) -> list[str]:
    found = []
    seen = set()
    for pat in _PROVISION_PATTERNS:
        for m in pat.finditer(text):
            s = m.group(0).strip()
            if s.lower() not in seen and len(found) < limit:
                seen.add(s.lower())
                found.append(s)
    return found

# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def build_empty_schema() -> dict[str, Any]:
    """Return the full schema template with all-null / empty values."""
    return {
        "case_id": {
            "source": None,
            "court_name": None,
            "country_or_region": None,
            "case_number": None,
            "decision_date": None,
        },
        "procedure": {
            "type": None,
            "ip_field": None,
            "technical_sector": None,
        },
        "parties": {
            "plaintiffs": [],
            "defendants": [],
            "third_parties": [],
        },
        "outcome": {
            "liability": None,
            "injunction": None,
            "damages": {
                "amount": None,
                "currency": None,
            },
        },
        "procedure_timeline": {
            "filing_date": None,
            "major_decisions": [],
        },
        "citations": {
            "legal_provisions": [],
            "case_law": [],
        },
        "notes": None,
    }


def partial_extract(text: str, hint_source: str | None = None) -> dict[str, Any]:
    """
    Extract deterministic fields from judgment text using regex.
    Returns a schema dict with as many fields filled as possible.
    Non-deterministic fields (party names, liability outcome, notes) are left null.
    The calling LLM should complete the remaining fields.
    """
    result = build_empty_schema()

    # ── source ヒント適用
    if hint_source:
        src = hint_source.lower()
        result["case_id"]["source"] = hint_source
        if src in _SOURCE_PROCEDURE_MAP:
            proc_type, ip_field = _SOURCE_PROCEDURE_MAP[src]
            result["procedure"]["type"] = proc_type
            result["procedure"]["ip_field"] = ip_field

    # ── 事件番号
    result["case_id"]["case_number"] = _extract_case_number(text)

    # ── 日付: 最初に見つかった2つを decision_date と filing_date に
    dates_found = []
    for pat, _ in _DATE_PATTERNS:
        for m in pat.finditer(text):
            d = _normalize_date(m.group(0))
            if d and d not in dates_found:
                dates_found.append(d)
            if len(dates_found) >= 5:
                break
        if len(dates_found) >= 5:
            break

    if dates_found:
        # 最新日を decision_date, 最古日を filing_date とする（ヒューリスティック）
        dates_found_sorted = sorted(dates_found)
        result["case_id"]["decision_date"] = dates_found_sorted[-1]
        result["procedure_timeline"]["filing_date"] = dates_found_sorted[0]

    # ── 損害額
    amount, currency = _extract_amount(text)
    if amount is not None:
        result["outcome"]["damages"]["amount"] = amount
        result["outcome"]["damages"]["currency"] = currency

    # ── 法令・条文
    result["citations"]["legal_provisions"] = _extract_provisions(text)

    # ── アウトカムキーワード（簡易）
    text_lower = text.lower()
    for kw, val in [
        ('plaintiff prevail', 'plaintiff_win'), ('granted in favor of plaintiff', 'plaintiff_win'),
        ('defendant prevail', 'defendant_win'), ('dismissed', 'dismissed'),
        ('settled', 'settlement'), ('partial', 'partial'),
        ('原告勝訴', 'plaintiff_win'), ('被告勝訴', 'defendant_win'),
    ]:
        if kw in text_lower:
            result["outcome"]["liability"] = val
            break

    # ── injunction
    if any(k in text_lower for k in ('preliminary injunction granted', 'injunction granted', '仮処分命令')):
        result["outcome"]["injunction"] = 'granted'
    elif any(k in text_lower for k in ('injunction denied', 'injunction not granted')):
        result["outcome"]["injunction"] = 'denied'

    return result


def normalize_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize a metadata dict (LLM-filled or partial_extract result):
    - Convert all date strings to YYYY-MM-DD
    - Resolve entity names via Entity Resolver if available
    - Validate schema structure (add missing keys)
    Returns a clean, schema-compliant dict.
    """
    # 日付正規化
    ci = raw.get("case_id", {})
    for date_field in ("decision_date", "filing_date"):
        target = ci if date_field == "decision_date" else raw.get("procedure_timeline", {})
        raw_date = target.get(date_field)
        if raw_date and isinstance(raw_date, str):
            normalized = _normalize_date(raw_date)
            target[date_field] = normalized  # null if unrecognized

    # major_decisions の日付も正規化
    for dec in raw.get("procedure_timeline", {}).get("major_decisions", []):
        if isinstance(dec, dict) and dec.get("date"):
            dec["date"] = _normalize_date(dec["date"])

    # Entity解決（Entity Resolverが利用可能な場合）
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from entity.registry import EntityRegistry
        from entity.resolver import EntityResolver
        from entity.data.entities_seed import SEED_ENTITIES
        reg = EntityRegistry()
        for e in SEED_ENTITIES:
            reg.register(e)
        resolver = EntityResolver(reg)

        for party_type in ("plaintiffs", "defendants", "third_parties"):
            for party in raw.get("parties", {}).get(party_type, []):
                if party.get("raw_name") and party.get("normalized_entity_id") is None:
                    r = resolver.resolve(party["raw_name"])
                    if r and r.confidence >= 0.85:
                        party["normalized_entity_id"] = r.entity.canonical_id
    except Exception:
        pass  # Entity layer not available → skip

    # スキーマ完全性チェック（不足キーを null で補完）
    template = build_empty_schema()
    _deep_merge_defaults(raw, template)

    return raw


def _deep_merge_defaults(target: dict, defaults: dict) -> None:
    """Add missing keys from defaults into target (non-destructive)."""
    for key, default_val in defaults.items():
        if key not in target:
            target[key] = default_val
        elif isinstance(default_val, dict) and isinstance(target.get(key), dict):
            _deep_merge_defaults(target[key], default_val)


def validate_schema(metadata: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate that metadata conforms to the required schema.
    Returns (is_valid, list_of_issues).
    """
    issues = []
    required_top = {"case_id", "procedure", "parties", "outcome",
                    "procedure_timeline", "citations", "notes"}
    for field in required_top:
        if field not in metadata:
            issues.append(f"Missing top-level field: {field}")

    ci = metadata.get("case_id", {})
    for f in ("source", "court_name", "country_or_region", "case_number", "decision_date"):
        if f not in ci:
            issues.append(f"Missing case_id.{f}")

    # 日付形式チェック
    for date_val, label in [
        (ci.get("decision_date"), "case_id.decision_date"),
        (metadata.get("procedure_timeline", {}).get("filing_date"), "procedure_timeline.filing_date"),
    ]:
        if date_val is not None:
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(date_val)):
                issues.append(f"Invalid date format for {label}: {date_val}")

    return len(issues) == 0, issues
