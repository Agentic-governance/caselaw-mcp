"""Citation extraction module for legal case law system.

Extracts legal citation strings from judgment full text using
regex patterns organised by jurisdiction.
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Jurisdiction pattern registry
# Each entry: (compiled_regex, jurisdiction_tag)
# ---------------------------------------------------------------------------

_US_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Federal Reporter / Supreme Court / L.Ed. — volume + reporter + page
    (
        re.compile(
            r"\b(\d{1,4})\s+"
            r"(F\.\d?d|F\.\s*Supp\.\s*\d?d|U\.S\.|S\.\s*Ct\.|L\.\s*Ed\.\s*\d?d)"
            r"\s+(\d{1,4})\b"
        ),
        "US",
    ),
    # Supreme Court with year — 384 U.S. 436 (1966)
    (
        re.compile(
            r"\b(\d{1,4})\s+U\.S\.\s+(\d{1,4})\s*\(\d{4}\)"
        ),
        "US",
    ),
    # Case name + reporter — Miranda v. Arizona, 384 U.S. 436
    (
        re.compile(
            r"([A-Z][a-z]+\s+v\.\s+[A-Z][a-z]+)"
            r",?\s+(\d{1,4}\s+\w+\.?\s*\d*\w*\.?\s+\d{1,4})"
        ),
        "US",
    ),
]

_EU_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # ECHR Application number — Application no. 39954/08
    (
        re.compile(r"Application\s+no\.\s*(\d+/\d{2,4})"),
        "EU",
    ),
    # CELEX identifier
    (
        re.compile(r"CELEX:\w+"),
        "EU",
    ),
    # CJEU Case — Case C-131/12 or Case T-99/04
    (
        re.compile(r"Case\s+[CT]-\d{1,4}/\d{2,4}"),
        "EU",
    ),
]

_UK_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Neutral citation — [2020] UKSC 5
    (
        re.compile(r"\[\d{4}\]\s+[A-Z]{2,6}\s+\d{1,4}"),
        "UK",
    ),
    # Law Reports — [1998] 1 AC 147  or  [2003] QB 1
    (
        re.compile(r"\[\d{4}\]\s+\d?\s*[A-Z]{1,4}\s+\d{1,4}"),
        "UK",
    ),
]

_JP_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Court decisions — 最大判昭和48年4月4日 / 知財高判令和3年6月1日
    (
        re.compile(
            r"(最[大小]?判|[東大名広福仙札高].*?[地高]判|知財高判)"
            r"(平成|令和|昭和)\d{1,2}年\d{1,2}月\d{1,2}日"
        ),
        "JP",
    ),
    # Case reporters — 民集27巻3号265頁
    (
        re.compile(
            r"(民集|刑集|判時|判タ|金判|労判)\d{1,3}巻\d{1,3}号\d{1,5}頁"
        ),
        "JP",
    ),
]

_DE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Aktenzeichen — BVerfG, 1 BvR 357/05
    (
        re.compile(
            r"(BVerfG|BGH|BVerwG|BAG|BSG|BFH),?\s*\d+\s+\w+\s+\d+/\d{2,4}"
        ),
        "DE",
    ),
    # BPatG Aktenzeichen — 1 Ni 33/08, 3 Ni 15/09
    (
        re.compile(r"\b\d{1,2}\s+Ni\s+\d{1,4}/\d{2,4}\b"),
        "DE",
    ),
    # Generic Aktenzeichen — I ZB 12/67, II ZR 195/05
    (
        re.compile(r"\b[IVX]{1,4}\s+[A-Z][A-Za-z]{1,3}\s+\d{1,4}/\d{2,4}\b"),
        "DE",
    ),
]

_IN_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # AIR citation — AIR 2017 SC 4161
    (
        re.compile(r"AIR\s+\d{4}\s+[A-Z]{2,4}\s+\d{1,4}"),
        "IN",
    ),
    # SCC citation — (2014) 9 SCC 1
    (
        re.compile(r"\(\d{4}\)\s+\d{1,2}\s+SCC\s+\d{1,4}"),
        "IN",
    ),
]

_AU_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Neutral citation — [2019] HCA 18
    (
        re.compile(r"\[\d{4}\]\s+[A-Z]{2,6}\s+\d{1,4}"),
        "AU",
    ),
    # CLR citation — (1992) 175 CLR 1
    (
        re.compile(r"\(\d{4}\)\s+\d{1,4}\s+CLR\s+\d{1,4}"),
        "AU",
    ),
]

_FR_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Cour de cassation — Cass. civ. 1re, 15 janv. 2024, n° 22-12.345
    # Also matches: Cass. crim., Cass. soc., Cass. ass. plén.
    (
        re.compile(
            r"Cass\.\s*(?:civ\.\s*\d(?:re|e)?|com\.|crim\.|soc\.|ass\.\s*plén\.)\s*,\s*"
            r"\d{1,2}\s+[A-Za-zÀ-ÿ]+\.?\s+\d{4},\s*n(?:°|o)\s*\d{2}[-‑]\d{2}[.\s]\s*\d{3}"
        ),
        "FR",
    ),
    # Standalone pourvoi number — pourvoi n° 22-12.345 / pourvoi n° E 09-15.956
    (
        re.compile(
            r"pourvois?\s+n(?:°|o)\s*[A-Z]?\s*\d{2}[-‑]\d{2}[.\s]\s*\d{3}"
        ),
        "FR",
    ),
    # Bulletin citation — Bull. civ. II, n° 123 / Bull. crim. n° 45
    (
        re.compile(
            r"Bull\.\s*(?:civ\.\s*[IV]{1,3}|crim\.)\s*,?\s*n(?:°|o)\s*\d{1,4}"
        ),
        "FR",
    ),
    # Conseil d'Etat — CE, ass., 15 janv. 2024, no 467890
    (
        re.compile(
            r"CE,\s*(?:(?:ass|sect|réf)\.,\s*)?\d{1,2}\s+[A-Za-zÀ-ÿ]+\.?\s+\d{4},\s*"
            r"n(?:°|o)\s*\d{4,6}"
        ),
        "FR",
    ),
    # Conseil constitutionnel short form — CC, décision n° 2023-1234 QPC
    (
        re.compile(r"CC,\s*décision\s*n(?:°|o)\s*\d{4}[-‑]\d{1,4}\s+QPC"),
        "FR",
    ),
    # Conseil constitutionnel long form — Cons. const., 12 mai 2024, n° 2024-1089 QPC
    (
        re.compile(
            r"Cons\.\s*const\.,\s*\d{1,2}\s+[A-Za-zÀ-ÿ]+\.?\s+\d{4},\s*"
            r"n(?:°|o)\s*\d{4}[-‑]\d{1,4}\s+QPC"
        ),
        "FR",
    ),
    # Article du Code references — article 1351 du code civil
    (
        re.compile(
            r"articles?\s+(?:L\.?\s*)?[\d]+(?:[-‑]\d+)*\s+du\s+[Cc]ode\s+"
            r"(?:civil|pénal|de\s+procédure\s+(?:civile|pénale)|de\s+commerce|"
            r"de\s+la\s+propriété\s+intellectuelle|du\s+travail|de\s+la\s+consommation)"
        ),
        "FR",
    ),
    # Journal officiel / JORF references
    (
        re.compile(
            r"JO\s+du\s+\d{1,2}\s+[A-Za-zÀ-ÿ]+\s+\d{4}|JORF\s+n(?:°|o)\s*\d{3,5}"
        ),
        "FR",
    ),
    # Recueil Lebon
    (
        re.compile(r"Lebon\s+p\.\s*\d{1,4}"),
        "FR",
    ),
    # Recueil Dalloz / JCP / RTD references
    (
        re.compile(r"(?:D\.\s*\d{4}|JCP\s+\d{4}|RTD\s+(?:civ|com)\.\s*\d{4})\s*[.,]\s*(?:p\.\s*)?\d{1,5}"),
        "FR",
    ),
]

_CA_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Supreme Court Reports — [2024] 1 SCR 123
    (
        re.compile(r"\[\d{4}\]\s+\d+\s+SCR\s+\d{1,4}"),
        "CA",
    ),
    # Supreme Court of Canada neutral — 2024 SCC 15
    (
        re.compile(r"\b\d{4}\s+SCC\s+\d{1,4}\b"),
        "CA",
    ),
    # Federal Court / Federal Court of Appeal — 2024 FC 123 / 2024 FCA 45
    (
        re.compile(r"\b\d{4}\s+FCA?\s+\d{1,4}\b"),
        "CA",
    ),
    # Provincial neutral citations — 2024 ONCA 123 / 2024 BCSC 456 / 2024 QCCA 789
    (
        re.compile(
            r"\b\d{4}\s+(?:ONCA|ONSC|BCSC|BCCA|QCCA|QCCS|ABCA|ABKB|ABQB|MBCA|MBQB|SKCA|SKQB|NSCA|NSSC|NBCA|NBQB|NLCA|PECA|TCC|CMAC|CanLII)\s+\d{1,4}\b"
        ),
        "CA",
    ),
    # DLR reporter — (2024) 456 DLR (4th) 123
    (
        re.compile(r"\(\d{4}\)\s+\d+\s+DLR\s+\(\d+(?:st|nd|rd|th)\)\s+\d{1,4}"),
        "CA",
    ),
]

_NZ_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Supreme Court of New Zealand — [2024] NZSC 12
    (
        re.compile(r"\[\d{4}\]\s+NZSC\s+\d{1,4}"),
        "NZ",
    ),
    # High Court of New Zealand — [2024] NZHC 345
    (
        re.compile(r"\[\d{4}\]\s+NZHC\s+\d{1,4}"),
        "NZ",
    ),
    # Court of Appeal of New Zealand — [2024] NZCA 67
    (
        re.compile(r"\[\d{4}\]\s+NZCA\s+\d{1,4}"),
        "NZ",
    ),
    # New Zealand Law Reports — [2024] 1 NZLR 123
    (
        re.compile(r"\[\d{4}\]\s+\d+\s+NZLR\s+\d{1,4}"),
        "NZ",
    ),
]

_KR_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Supreme Court of Korea — 대법원 2024. 1. 15. 선고 2023다12345 판결
    (
        re.compile(
            r"대법원\s+\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.\s*선고\s+\d{4}[가-힣]+\d+\s+판결"
        ),
        "KR",
    ),
    # Constitutional Court — 헌법재판소 2024. 3. 28. 2023헌바123 결정
    (
        re.compile(
            r"헌법재판소\s+\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.\s*\d{4}헌[가-힣]+\d+\s+결정"
        ),
        "KR",
    ),
    # Neutral case IDs
    (
        re.compile(r"\b\d{4}다\d+\b"),
        "KR",
    ),
    (
        re.compile(r"\b\d{4}헌[가-힣]+\d+\b"),
        "KR",
    ),
]

_CH_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # BGer (Swiss Federal Supreme Court) — BGer 4A_123/2024
    (
        re.compile(r"\bBGer\s+\d[A-Z]_\d{1,4}/\d{4}\b"),
        "CH",
    ),
    # BGE (official reports) — BGE 148 III 57
    (
        re.compile(r"\bBGE\s+\d{2,3}\s+[IVX]+\s+\d{1,4}\b"),
        "CH",
    ),
    # ATF (French version of BGE) — ATF 148 III 57
    (
        re.compile(r"\bATF\s+\d{2,3}\s+[IVX]+\s+\d{1,4}\b"),
        "CH",
    ),
    # DTF (Italian version of BGE) — DTF 148 III 57
    (
        re.compile(r"\bDTF\s+\d{2,3}\s+[IVX]+\s+\d{1,4}\b"),
        "CH",
    ),
    # Urteil/Arrêt references — Urteil 4A_123/2024 or Arrêt 4A_123/2024
    (
        re.compile(r"\b(?:Urteil|Arrêt)\s+\d[A-Z]_\d{1,4}/\d{4}\b"),
        "CH",
    ),
]

_PL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Supreme Court (Sąd Najwyższy) — III CZP 1/23
    (
        re.compile(r"\b[IV]{1,4}\s+(?:CZP|CSK|CKN|CNP|KZP|KK|SK)\s+\d{1,4}/\d{2,4}\b"),
        "PL",
    ),
    # Criminal/civil case refs — II K 69/11, III Ca 123/20, II AKa 45/19
    (
        re.compile(r"\b[IV]{1,4}\s+(?:K|Ka|AKa|Ca|C|W|Ws|S|U|P|Kp)\s+\d{1,4}/\d{2,4}\b"),
        "PL",
    ),
    # Constitutional Tribunal — K 1/23, SK 1/23, P 1/23
    (
        re.compile(r"\b[KPS]\s+\d{1,4}/\d{2,4}\b"),
        "PL",
    ),
    # Supreme Administrative Court — II OSK 123/23, II GSK 123/23
    (
        re.compile(r"\b[IV]{1,4}\s+(?:OSK|GSK|FSK|SA)\s+\d{1,4}/\d{2,4}\b"),
        "PL",
    ),
    # Dz.U. (Journal of Laws) — Dz.U. 2023 poz. 1234 or Dz.U. z 2023 r. poz. 1234
    (
        re.compile(r"Dz\.U\.\s+(?:z\s+)?\d{4}\s+(?:r\.\s+)?poz\.\s+\d{1,5}"),
        "PL",
    ),
    # OSNC / OSP (court reporter) — OSNC 2023/1/12
    (
        re.compile(r"\b(?:OSNC|OSP|OSNKW|OSNP)\s+\d{4}/\d{1,2}/\d{1,4}\b"),
        "PL",
    ),
    # Sygnatura akt (case signature) — sygn. akt II K 69/11
    (
        re.compile(r"sygn\.\s*akt\s+[IV]{1,4}\s+\w{1,4}\s+\d{1,4}/\d{2,4}", re.IGNORECASE),
        "PL",
    ),
]

_AT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # VwGH (Verwaltungsgerichtshof) — VwGH 2023/15/0123
    (re.compile(r"\bVwGH\s+\d{4}/\d{2}/\d{4}\b"), "AT"),
    # VfGH (Verfassungsgerichtshof) — VfGH G 123/2023
    (re.compile(r"\bVfGH\s+[A-Z]\s+\d{1,4}/\d{4}\b"), "AT"),
    # BVwG (Bundesverwaltungsgericht) — BVwG W123 1234567-1
    (re.compile(r"\bBVwG\s+[A-Z]\d{3}\s+\d{5,7}[-/]\d\b"), "AT"),
    # OGH (Oberster Gerichtshof) — OGH 1 Ob 123/23x
    (re.compile(r"\bOGH\s+\d{1,2}\s+Ob\s+\d{1,4}/\d{2}[a-z]?\b"), "AT"),
    # Austrian law gazette — BGBl. I Nr. 123/2023
    (re.compile(r"BGBl\.\s*(?:I{1,3}|Nr\.)\s*(?:Nr\.\s*)?\d{1,4}/\d{4}"), "AT"),
    # Geschäftszahl (generic) — Gz. 2023/15/0123
    (re.compile(r"\bGz\.?\s+\d{4}/\d{2}/\d{4}\b"), "AT"),
]

_HK_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Hong Kong neutral citations — [2024] HKCA 123 / [2024] HKCFI 456
    (
        re.compile(r"\[\d{4}\]\s+(?:HKCA|HKCFA|HKCFI|HKDC|HKFC|HKLC|HKCT)\s+\d{1,4}"),
        "HK",
    ),
    # HKLRD references — (2024) 27 HKLRD 123
    (re.compile(r"\(\d{4}\)\s+\d{1,2}\s+HKLRD\s+\d{1,4}"), "HK"),
]

_SG_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Singapore neutral citations — [2024] SGCA 12 / [2024] SGHC 34
    (
        re.compile(r"\[\d{4}\]\s+(?:SGCA|SGHC|SGDC|SGMC|SGHCF|SGAB)\s+\d{1,4}"),
        "SG",
    ),
    # SLR references — [2024] 1 SLR 123 / [2024] 1 SLR(R) 456
    (re.compile(r"\[\d{4}\]\s+\d\s+SLR(?:\(R\))?\s+\d{1,4}"), "SG"),
]

_BR_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # STF references — STF, RE 123456
    (
        re.compile(r"STF,\s*RE\s+\d{3,7}"),
        "BR",
    ),
    # STF neutral/state form — RE 123.456/SP
    (
        re.compile(r"\bRE\s+\d{1,3}(?:\.\d{3})+(?:/[A-Z]{2})?\b"),
        "BR",
    ),
    # STJ references — STJ, REsp 1234567/SP
    (
        re.compile(r"STJ,\s*REsp\s+\d{1,7}(?:/[A-Z]{2})?"),
        "BR",
    ),
    # STJ neutral form — REsp 1.234.567
    (
        re.compile(r"\bREsp\s+\d{1,3}(?:\.\d{3})+(?:/[A-Z]{2})?\b"),
        "BR",
    ),
    # Tribunal references — TJSP, Ap. 1234567-12.2024.8.26.0100
    (
        re.compile(r"\bTJ[A-Z]{2},\s*Ap\.\s*\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b"),
        "BR",
    ),
]

# Map jurisdiction codes to their pattern lists
_JURISDICTION_PATTERNS: dict[str, list[tuple[re.Pattern[str], str]]] = {
    "US": _US_PATTERNS,
    "EU": _EU_PATTERNS,
    "UK": _UK_PATTERNS,
    "JP": _JP_PATTERNS,
    "DE": _DE_PATTERNS,
    "IN": _IN_PATTERNS,
    "AU": _AU_PATTERNS,
    "FR": _FR_PATTERNS,
    "CA": _CA_PATTERNS,
    "NZ": _NZ_PATTERNS,
    "KR": _KR_PATTERNS,
    "BR": _BR_PATTERNS,
    "CH": _CH_PATTERNS,
    "PL": _PL_PATTERNS,
    "AT": _AT_PATTERNS,
    "HK": _HK_PATTERNS,
    "SG": _SG_PATTERNS,
}

# All patterns flattened (used for cross-jurisdiction scanning)
_ALL_PATTERNS: list[tuple[re.Pattern[str], str]] = []
for _pats in _JURISDICTION_PATTERNS.values():
    _ALL_PATTERNS.extend(_pats)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _context_window(text: str, start: int, end: int, width: int = 50) -> str:
    """Return up to *width* characters before and after the match."""
    ctx_start = max(0, start - width)
    ctx_end = min(len(text), end + width)
    return text[ctx_start:ctx_end]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_citations(
    text: str,
    jurisdiction: str,
) -> list[dict[str, Any]]:
    """Extract legal citations from *text*.

    Parameters
    ----------
    text:
        The full text of a judgment or legal document.
    jurisdiction:
        ISO-style jurisdiction code (``US``, ``EU``, ``UK``, ``JP``,
        ``DE``, ``IN``, ``AU``, ``FR``, ``CA``, ``NZ``, ``KR``, ``BR``,
        ``CH``, ``PL``, ``AT``, ``HK``, ``SG``).
        Patterns for this jurisdiction are always applied.  Additionally,
        **all other** jurisdiction patterns are scanned to detect
        cross-jurisdiction references.

    Returns
    -------
    list[dict]
        De-duplicated list of citation dicts.  Each dict contains:

        - ``citation_string`` — the matched text
        - ``jurisdiction`` — jurisdiction tag of the **pattern** that
          matched (may differ from the *jurisdiction* argument when a
          cross-reference is detected)
        - ``position`` — ``(start, end)`` character offsets in *text*
        - ``context`` — surrounding text snippet (up to 50 chars each
          side)
    """
    if not text:
        return []

    jurisdiction = jurisdiction.upper()

    # Collect primary patterns for the requested jurisdiction
    primary_patterns = _JURISDICTION_PATTERNS.get(jurisdiction, [])

    # Collect cross-jurisdiction patterns (all *other* jurisdictions)
    cross_patterns: list[tuple[re.Pattern[str], str]] = []
    for jur, pats in _JURISDICTION_PATTERNS.items():
        if jur != jurisdiction:
            cross_patterns.extend(pats)

    # Run primary then cross patterns
    seen: set[str] = set()
    results: list[dict[str, Any]] = []

    for pattern, jur_tag in primary_patterns + cross_patterns:
        for m in pattern.finditer(text):
            cite_str = m.group(0)
            if cite_str in seen:
                continue
            seen.add(cite_str)
            results.append(
                {
                    "citation_string": cite_str,
                    "jurisdiction": jur_tag,
                    "position": (m.start(), m.end()),
                    "context": _context_window(text, m.start(), m.end()),
                }
            )

    return results
