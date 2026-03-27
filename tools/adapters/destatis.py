"""Adapter for Germany gesetze-im-internet statute XML."""

from __future__ import annotations

import io
import zipfile
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from .base import AdapterError, BaseAdapter

class DeStaatisAdapter(BaseAdapter):
    """Fetch and normalize German statutes from gesetze-im-internet.de."""

    API_BASE = "https://www.gesetze-im-internet.de"
    LAW_ABBREV_TABLE = {
        "URHG": "urhg",
        "TMG": "tmg",
        "UWG": "uwg",
        "TKG": "tkg",
        "BDSG": "bdsg_2018",
        "STGB": "stgb",
        "ZPO": "zpo",
    }

    @staticmethod
    def _tag_suffix(tag: str) -> str:
        return tag.split("}")[-1]

    @classmethod
    def _text_by_suffix(cls, element: ET.Element, suffix: str) -> str:
        for node in element.iter():
            if cls._tag_suffix(node.tag) == suffix and node.text:
                return node.text.strip()
        return ""

    @staticmethod
    def _normalize_article(article: str) -> str:
        return "".join(article.lower().split())

    def _request_bytes(self, method: str, url: str) -> bytes:
        req = Request(url, method=method.upper())
        try:
            with urlopen(req, timeout=self.timeout_seconds) as resp:  # nosec B310
                return resp.read()
        except (URLError, OSError) as exc:
            raise AdapterError(f"HTTP request failed: {url}") from exc

    def _load_norm_rows(self, law_abbrev: str) -> list[dict[str, Any]]:
        law_key = law_abbrev.strip().upper()
        slug = self.LAW_ABBREV_TABLE.get(law_key, law_abbrev.strip().lower())
        if not slug:
            return []

        cache_key = f"destatis:{slug}:norms"

        def _fetch() -> list[dict[str, Any]]:
            zip_url = f"{self.API_BASE}/{slug}/xml.zip"
            payload = self._request_bytes("GET", zip_url)

            try:
                archive = zipfile.ZipFile(io.BytesIO(payload))
            except zipfile.BadZipFile as exc:
                raise AdapterError("Invalid gesetze-im-internet ZIP response") from exc

            rows: list[dict[str, Any]] = []
            for name in archive.namelist():
                if not name.lower().endswith(".xml"):
                    continue
                with archive.open(name) as fp:
                    try:
                        root = ET.fromstring(fp.read())
                    except ET.ParseError as exc:
                        raise AdapterError("Invalid gesetze-im-internet XML") from exc

                for norm in root.iter():
                    if self._tag_suffix(norm.tag) != "norm":
                        continue
                    jurabk = self._text_by_suffix(norm, "jurabk") or law_key
                    enbez = self._text_by_suffix(norm, "enbez")
                    titel = self._text_by_suffix(norm, "titel")

                    paragraphs: list[str] = []
                    for node in norm.iter():
                        if self._tag_suffix(node.tag) != "P":
                            continue
                        text = " ".join(node.itertext()).strip()
                        if text:
                            paragraphs.append(text)

                    text = "\n".join(paragraphs).strip()
                    if not enbez and not text:
                        continue

                    rows.append(
                        {
                            "law_name": jurabk,
                            "jurisdiction": "DE",
                            "article": enbez or None,
                            "text": text,
                            "theme": titel or None,
                            "_source": "destatis",
                        }
                    )
            return rows

        return self._run_with_cache(cache_key, _fetch)

    def search_statutes(
        self,
        query: str,
        article: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        law_abbrev: str | None = None
        keywords: list[str] | None = None

        # If query is given but not law_abbrev, try to match a known law or use as keywords
        if query:
            q_upper = query.strip().upper()
            if q_upper in self.LAW_ABBREV_TABLE:
                law_abbrev = q_upper
            else:
                keywords = (keywords or []) + [query]

        if law_abbrev:
            try:
                rows = self._load_norm_rows(law_abbrev)
            except (AdapterError, Exception):
                rows = []
        else:
            rows = []

        article_norm = self._normalize_article(article or "")
        keyword_norm = [kw.strip().lower() for kw in (keywords or []) if kw and kw.strip()]

        matches: list[dict[str, Any]] = []
        for row in rows:
            target_article = self._normalize_article(str(row.get("article", "") or ""))
            if article_norm and article_norm not in target_article:
                continue

            if keyword_norm:
                space = " ".join(
                    [
                        str(row.get("law_name", "")),
                        str(row.get("article", "")),
                        str(row.get("text", "")),
                        str(row.get("theme", "")),
                    ]
                ).lower()
                if not any(kw in space for kw in keyword_norm):
                    continue
            matches.append(row)
            if len(matches) >= limit:
                break

        return matches[:limit]

    def get_article(self, law_abbrev: str, article: str) -> dict[str, Any] | None:
        article_norm = self._normalize_article(article)
        if not article_norm:
            return None
        rows = self._load_norm_rows(law_abbrev)
        for row in rows:
            target_article = self._normalize_article(str(row.get("article", "") or ""))
            if article_norm == target_article:
                return row
        return None
