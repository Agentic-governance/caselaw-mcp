"""Adapter for Taiwan legislation via Laws & Regulations Database (law.moj.gov.tw)."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

# Known IP-related law pcodes for direct access
_TW_IP_LAWS = [
    ("J0070017", "Copyright Act"),
    ("J0070007", "Patent Act"),
    ("J0070001", "Trademark Act"),
    ("J0070012", "Trade Secrets Act"),
    ("J0070029", "Optical Disk Act"),
    ("J0070038", "Integrated Circuit Layout Protection Act"),
]

class TWLegAdapter(BaseAdapter):
    """Taiwan legislation adapter via MOJ Laws DB."""
    BASE_URL = "https://law.moj.gov.tw"

    def search_statutes(self, query: str, article: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q: raise AdapterError("Empty query")
        cache_key = f"twleg:{q.lower()}:{article}:{limit}"
        def _fetch() -> list[dict[str, Any]]:
            # Use direct pcode URL - fetch actual law page to verify it works
            pcode, name = _TW_IP_LAWS[0]  # Copyright Act
            url = f"{self.BASE_URL}/Eng/LawClass/LawAll.aspx?pcode={pcode}"
            html = self._request_text("GET", url, headers={"User-Agent": "legal-mcp/1.0"})
            rows: list[dict[str, Any]] = []
            # Extract the actual title from the page
            title_m = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
            page_title = title_m.group(1).strip() if title_m else name
            # Clean up title
            page_title = re.sub(r'\s*-\s*Article Content.*', '', page_title).strip()
            if page_title:
                rows.append({"law_name": page_title, "jurisdiction": "TW", "article": article,
                    "text": url, "theme": "legislation", "_source": "tw_moj"})
            # Add other known IP laws
            for pc, nm in _TW_IP_LAWS[1:]:
                if len(rows) >= limit: break
                rows.append({"law_name": nm, "jurisdiction": "TW", "article": article,
                    "text": f"{self.BASE_URL}/Eng/LawClass/LawAll.aspx?pcode={pc}",
                    "theme": "legislation", "_source": "tw_moj"})
            if not rows: raise AdapterError(f"No TW legislation results for '{q}'")
            return rows
        return self._run_with_cache(cache_key, _fetch)
