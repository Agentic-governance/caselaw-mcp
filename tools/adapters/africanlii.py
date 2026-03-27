"""Adapter for pan-African legal information via AfricanLII (africanlii.org)."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

class AfricanLIIAdapter(BaseAdapter):
    """Pan-African case law adapter via AfricanLII."""
    BASE_URL = "https://africanlii.org"

    def search_cases(self, query: str, year_from: int | None = None, limit: int = 10, country: str | None = None) -> list[dict[str, Any]]:
        q = query.strip()
        if not q: raise AdapterError("Empty query")
        cache_key = f"africanlii:{q.lower()}:{year_from}:{limit}:{country}"
        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text("GET", self.BASE_URL + "/en/",
                headers={"User-Agent": "legal-mcp/1.0"})
            rows: list[dict[str, Any]] = []
            # Match AKN judgment links: /en/akn/aa-au/judgment/{court}/{year}/{num}/{lang}@{date}
            for m in re.finditer(r'<a[^>]+href="(/en/akn/[^"]+/judgment/[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 5: continue
                # Extract jurisdiction from AKN path
                akn_m = re.search(r'/akn/([a-z]{2}(?:-[a-z]{2})?)/judgment/([^/]+)/(\d{4})/', href)
                jurisdiction = akn_m.group(1).upper().replace("-", "_") if akn_m else "AF"
                court = akn_m.group(2) if akn_m else ""
                year = int(akn_m.group(3)) if akn_m else None
                if country and jurisdiction != country.upper(): continue
                if year_from and year and year < year_from: continue
                rows.append({"case_name": title, "jurisdiction": jurisdiction, "court": court,
                    "year": year, "result": "Unknown", "text": title,
                    "source_url": f"{self.BASE_URL}{href}", "domain": "external",
                    "keywords": [q], "_source": "africanlii"})
                if len(rows) >= limit: break
            # Also try legislation links as fallback
            if not rows:
                for m in re.finditer(r'<a[^>]+href="(/en/akn/[^"]+/act/[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
                    href, inner = m.groups()
                    title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                    title = re.sub(r"\s+", " ", title)
                    if not title or len(title) < 5: continue
                    rows.append({"case_name": title, "jurisdiction": "AF", "court": "",
                        "year": None, "result": "Unknown", "text": title,
                        "source_url": f"{self.BASE_URL}{href}", "domain": "external",
                        "keywords": [q], "_source": "africanlii"})
                    if len(rows) >= limit: break
            if not rows: raise AdapterError(f"No African case results for '{q}'")
            return rows
        return self._run_with_cache(cache_key, _fetch)
