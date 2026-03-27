"""Adapter for Tanzanian case law via TanzLII (tanzlii.org)."""
from __future__ import annotations
import re
from html import unescape
from typing import Any
from .base import AdapterError, BaseAdapter

class TZLawAdapter(BaseAdapter):
    """Tanzanian case law adapter via TanzLII."""
    BASE_URL = "https://tanzlii.org"

    def search_cases(self, query: str, year_from: int | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q: raise AdapterError("Empty query")
        cache_key = f"tzlaw:{q.lower()}:{year_from}:{limit}"
        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text("GET", self.BASE_URL + "/",
                headers={"User-Agent": "legal-mcp/1.0"})
            rows: list[dict[str, Any]] = []
            # Match AKN links with /en/ prefix: /en/akn/tz/judgment/{court}/{year}/{num}/eng@{date}
            for m in re.finditer(r'<a[^>]+href="(/en/akn/tz/judgment/[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
                href, inner = m.groups()
                title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                title = re.sub(r"\s+", " ", title)
                if not title or len(title) < 5: continue
                ym = re.search(r'/(\d{4})/', href)
                year = int(ym.group(1)) if ym else None
                if year_from and year and year < year_from: continue
                court_m = re.search(r'/judgment/([^/]+)/', href)
                court = court_m.group(1) if court_m else ""
                rows.append({"case_name": title, "jurisdiction": "TZ", "court": court,
                    "year": year, "result": "Unknown", "text": title,
                    "source_url": f"{self.BASE_URL}{href}", "domain": "external",
                    "keywords": [q], "_source": "tanzlii"})
                if len(rows) >= limit: break
            # Fallback: legislation links
            if not rows:
                for m in re.finditer(r'<a[^>]+href="(/en/akn/tz/act/[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
                    href, inner = m.groups()
                    title = unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
                    title = re.sub(r"\s+", " ", title)
                    if not title or len(title) < 5: continue
                    rows.append({"case_name": title, "jurisdiction": "TZ", "court": "",
                        "year": None, "result": "Unknown", "text": title,
                        "source_url": f"{self.BASE_URL}{href}", "domain": "external",
                        "keywords": [q], "_source": "tanzlii"})
                    if len(rows) >= limit: break
            if not rows: raise AdapterError(f"No TZ case results for '{q}'")
            return rows
        return self._run_with_cache(cache_key, _fetch)
