"""
Metadata extractor: 判決テキストから構造化メタデータを抽出する。
LLMは使わない。正規表現とルールベースで抽出。
"""
import re
import json
from typing import Dict, Optional


def extract_metadata(text: str, jurisdiction: str) -> Dict:
    """
    判決テキストから構造化メタデータを抽出する。

    Returns:
        {
            "judge_names": ["Judge Smith", ...],
            "lawyer_names": [{"name": "John Doe", "role": "plaintiff"}, ...],
            "case_type": "civil",
            "outcome": "granted",
            "damages_amount": 500000,
            "damages_currency": "USD",
            "court_level": "district",
        }
    """
    result = {}

    # 管轄別の抽出ロジック
    if jurisdiction == "US":
        result = _extract_us(text)
    elif jurisdiction == "JP":
        result = _extract_jp(text)
    elif jurisdiction in ("EU", "ECHR"):
        result = _extract_eu(text)
    elif jurisdiction in ("UK", "GB"):
        result = _extract_uk(text)
    elif jurisdiction == "DE":
        result = _extract_de(text)
    elif jurisdiction == "IN":
        result = _extract_in(text)
    else:
        result = _extract_generic(text)

    return result


def _extract_us(text: str) -> Dict:
    result = {}

    # 判事名
    judge_patterns = [
        r'(?:Chief )?Justice\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'(?:Circuit |District )?Judge\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'(?:Before|Per)\s+(?:Chief )?(?:Justice|Judge)\s+([A-Z][a-z]+)',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s+(?:Circuit |District )?(?:Judge|J\.)',
    ]
    judges = set()
    for p in judge_patterns:
        for m in re.finditer(p, text):
            judges.add(m.group(1))
    if judges:
        result["judge_names"] = list(judges)

    # 賠償額
    damages_patterns = [
        r'\$\s*([\d,]+(?:\.\d{2})?)\s*(?:in damages|damages)',
        r'(?:awarded|judgment of|verdict of)\s*\$\s*([\d,]+(?:\.\d{2})?)',
        r'damages\s+(?:of|in the amount of)\s+\$\s*([\d,]+(?:\.\d{2})?)',
    ]
    for p in damages_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            amount_str = m.group(1).replace(",", "")
            try:
                result["damages_amount"] = float(amount_str)
                result["damages_currency"] = "USD"
            except ValueError:
                pass
            break

    # 判決結果 (ordered by specificity — more specific patterns first)
    outcome_checks = [
        ("granted", r'(?:motion|summary judgment|petition).*?\bis\s+granted\b'),
        ("granted", r'\bgranted\b.*?(?:motion|summary judgment|petition)'),
        ("denied", r'(?:motion|summary judgment|petition).*?\bis\s+denied\b'),
        ("denied", r'\bdenied\b.*?(?:motion|summary judgment|petition)'),
        ("affirmed", r'\b(?:affirmed|we affirm|is affirmed)\b'),
        ("reversed", r'\b(?:reversed|we reverse|is reversed)\b'),
        ("remanded", r'\b(?:remanded|we remand|is remanded)\b'),
        ("dismissed", r'\b(?:case|action|complaint|appeal)\s+(?:is\s+)?(?:dismissed|hereby dismissed)\b'),
    ]
    for outcome, pattern in outcome_checks:
        if re.search(pattern, text, re.IGNORECASE):
            result["outcome"] = outcome
            break

    return result


def _extract_jp(text: str) -> Dict:
    result = {}

    # 裁判官名
    judge_patterns = [
        r'裁判長裁判官\s*(\S+)',
        r'裁判官\s*(\S+)',
    ]
    judges = []
    for p in judge_patterns:
        for m in re.finditer(p, text):
            judges.append(m.group(1))
    if judges:
        result["judge_names"] = judges

    # 判決結果
    if re.search(r'主文.*?棄却', text, re.DOTALL):
        result["outcome"] = "棄却"
    elif re.search(r'主文.*?認容', text, re.DOTALL):
        result["outcome"] = "認容"
    elif re.search(r'主文.*?却下', text, re.DOTALL):
        result["outcome"] = "却下"
    elif re.search(r'破棄.*?差戻', text, re.DOTALL):
        result["outcome"] = "破棄差戻"
    elif re.search(r'上告.*?棄却', text, re.DOTALL):
        result["outcome"] = "上告棄却"

    # 賠償額
    m = re.search(r'金(\d[\d,]*)円', text)
    if m:
        try:
            result["damages_amount"] = int(m.group(1).replace(",", ""))
            result["damages_currency"] = "JPY"
        except ValueError:
            pass

    return result


def _extract_eu(text: str) -> Dict:
    result = {}

    # Application number
    m = re.search(r'Application\s+no\.\s*(\d+/\d{2,4})', text)
    if m:
        result["application_number"] = m.group(1)

    # Conclusion
    if re.search(r'[Vv]iolation of Article', text):
        result["outcome"] = "violation"
    elif re.search(r'[Nn]o violation', text):
        result["outcome"] = "no_violation"

    # Judges
    judge_pattern = r'(?:Judge|President)\s+([A-Z][a-z\u00e0-\u00ff]+(?:\s+[A-Z][a-z\u00e0-\u00ff]+)*)'
    judges = set()
    for m in re.finditer(judge_pattern, text):
        judges.add(m.group(1))
    if judges:
        result["judge_names"] = list(judges)

    return result


def _extract_uk(text: str) -> Dict:
    result = {}

    # Judge names: Lord/Lady Justice, Mr/Mrs Justice
    patterns = [
        r'(?:Lord|Lady)\s+Justice\s+([A-Z][a-z]+)',
        r'(?:Mr|Mrs)\s+Justice\s+([A-Z][a-z]+)',
        r'(?:Lord|Baroness)\s+([A-Z][a-z]+)',
    ]
    judges = set()
    for p in patterns:
        for m in re.finditer(p, text):
            judges.add(m.group(1))
    if judges:
        result["judge_names"] = list(judges)

    return result


def _extract_de(text: str) -> Dict:
    result = {}

    # Aktenzeichen
    m = re.search(r'(\d+\s+\w+\s+\d+/\d{2,4})', text)
    if m:
        result["case_number"] = m.group(1)

    # Richter
    judge_pattern = r'(?:Richter(?:in)?|Vorsitzende[r]?)\s+(?:am\s+\w+\s+)?(\S+)'
    for m in re.finditer(judge_pattern, text):
        result.setdefault("judge_names", []).append(m.group(1))

    return result


def _extract_in(text: str) -> Dict:
    result = {}

    # Judge names: Hon'ble Justice, J.
    patterns = [
        r"Hon'?ble\s+(?:Mr\.?\s+)?Justice\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*[a-z]+)*)",
        r'([A-Z][a-z]+(?:\.\s*[A-Z]\.?\s*)?[A-Za-z]+),?\s*J\.',
    ]
    judges = set()
    for p in patterns:
        for m in re.finditer(p, text):
            judges.add(m.group(1).strip())
    if judges:
        result["judge_names"] = list(judges)

    return result


def _extract_generic(text: str) -> Dict:
    """汎用抽出（管轄固有パターンがない場合）"""
    result = {}

    # 一般的なJudgeパターン
    m = re.findall(r'(?:Judge|Justice)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
    if m:
        result["judge_names"] = list(set(m))

    return result
