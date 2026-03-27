"""Adapter for Swedish legislation via Riksdagen Open Data API."""
from __future__ import annotations
from typing import Any
from .base import AdapterError, BaseAdapter

class SELegAdapter(BaseAdapter):
    """Swedish legislation adapter via Riksdagen Open Data API."""
    API_URL = "https://data.riksdagen.se/dokumentlista/"

    def search_statutes(self, query: str, article: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q: raise AdapterError("Empty query")
        cache_key = f"seleg:{q.lower()}:{article}:{limit}"
        def _fetch() -> list[dict[str, Any]]:
            data = self._request_json("GET", self.API_URL,
                params={"doktyp": "sfs", "utformat": "json", "antal": str(min(limit, 20))},
                headers={"User-Agent": "legal-mcp/1.0"})
            docs = data.get("dokumentlista", {}).get("dokument", [])
            if not docs: raise AdapterError(f"No SE legislation results for '{q}'")
            rows: list[dict[str, Any]] = []
            for doc in docs[:limit]:
                title = doc.get("titel", doc.get("undertitel", doc.get("id", "Unknown")))
                doc_id = doc.get("id", "")
                datum = doc.get("datum", "")
                url = f"https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/{doc_id}/"
                rows.append({"law_name": title, "jurisdiction": "SE", "article": article,
                    "text": url, "theme": "legislation", "date": datum,
                    "_source": "riksdagen_api"})
            return rows
        return self._run_with_cache(cache_key, _fetch)
