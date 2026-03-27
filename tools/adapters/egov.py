"""Adapter for Japan e-Gov law API."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote
from xml.etree import ElementTree as ET

from .base import AdapterError, BaseAdapter

class EGovAdapter(BaseAdapter):
    """Fetch and normalize statute data from e-Gov law API."""

    API_BASE = "https://laws.e-gov.go.jp/api/1"
    LAW_NUM_TABLE = {
        "著作権法": "昭和四十五年法律第四十八号",
        "プロバイダ責任制限法": "平成十三年法律第百三十七号",
        "不正アクセス禁止法": "平成十一年法律第百二十八号",
        "不正競争防止法": "平成五年法律第四十七号",
        "電気通信事業法": "昭和五十九年法律第八十六号",
        "個人情報保護法": "平成十五年法律第五十七号",
        "特定電子メール法": "平成十四年法律第二十六号",
    }

    @staticmethod
    def _text_by_suffix(element: ET.Element, suffix: str) -> str:
        for node in element.iter():
            tag = node.tag.split("}")[-1]
            if tag == suffix and node.text:
                return node.text.strip()
        return ""

    def search_statutes(self, query: str, article: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = (query or "").strip().lower()
        category = int(article) if article and article.isdigit() else 2
        cache_key = f"egov:lawlists:{category}:{q}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            xml_text = self._request_text("GET", f"{self.API_BASE}/lawlists/{category}")
            try:
                root = ET.fromstring(xml_text)
            except ET.ParseError as exc:
                raise AdapterError("Invalid e-Gov XML") from exc

            rows: list[dict[str, Any]] = []
            seen: set[tuple[str, str]] = set()
            for elem in root.iter():
                law_name = self._text_by_suffix(elem, "LawName")
                law_num = self._text_by_suffix(elem, "LawNo")
                if not law_name or not law_num:
                    continue
                key = (law_name, law_num)
                if key in seen:
                    continue
                seen.add(key)
                if q and q not in law_name.lower():
                    continue
                rows.append(
                    {
                        "law_name": law_name,
                        "law_num": law_num,
                        "jurisdiction": "JP",
                    }
                )
                if len(rows) >= limit:
                    break
            return rows

        return self._run_with_cache(cache_key, _fetch)

    def lookup_law_num(self, law_name: str) -> str | None:
        query = law_name.strip()
        if not query:
            return None

        if query in self.LAW_NUM_TABLE:
            return self.LAW_NUM_TABLE[query]

        for name, law_num in self.LAW_NUM_TABLE.items():
            if query in name or name in query:
                return law_num

        laws = self.search_statutes(query=query, article="2", limit=10)
        if not laws:
            return None
        return str(laws[0].get("law_num", "")) or None

    def get_law_overview(self, law_num: str, max_articles: int = 3) -> list[dict[str, Any]]:
        cache_key = f"egov:lawoverview:{law_num}:{max_articles}"

        def _fetch() -> list[dict[str, Any]]:
            xml_text = self._request_text("GET", f"{self.API_BASE}/lawdata/{quote(law_num, safe='')}")
            try:
                root = ET.fromstring(xml_text)
            except ET.ParseError as exc:
                raise AdapterError("Invalid e-Gov XML") from exc

            law_name = ""
            for node in root.iter():
                tag = node.tag.split("}")[-1]
                if tag in ("LawTitle", "LawName") and node.text:
                    law_name = node.text.strip()
                    break

            rows: list[dict[str, Any]] = []
            for art in root.iter():
                if art.tag.split("}")[-1] != "Article":
                    continue
                title = self._text_by_suffix(art, "ArticleTitle")
                text = "".join(art.itertext()).strip()
                rows.append(
                    {
                        "law_name": law_name,
                        "jurisdiction": "JP",
                        "article": title or None,
                        "text": text,
                        "theme": None,
                    }
                )
                if len(rows) >= max_articles:
                    break
            return rows

        return self._run_with_cache(cache_key, _fetch)

    def get_article(self, law_num: str, article: str) -> dict[str, Any] | None:
        article_norm = article.strip()
        cache_key = f"egov:lawdata:{law_num}:{article_norm}"

        def _fetch() -> dict[str, Any] | None:
            xml_text = self._request_text("GET", f"{self.API_BASE}/lawdata/{quote(law_num, safe='')}")
            try:
                root = ET.fromstring(xml_text)
            except ET.ParseError as exc:
                raise AdapterError("Invalid e-Gov XML") from exc

            law_name = ""
            for node in root.iter():
                tag = node.tag.split("}")[-1]
                if tag in ("LawTitle", "LawName") and node.text:
                    law_name = node.text.strip()
                    break

            for art in root.iter():
                if art.tag.split("}")[-1] != "Article":
                    continue
                title = self._text_by_suffix(art, "ArticleTitle")
                text = "".join(art.itertext()).strip()
                if article_norm and article_norm not in title:
                    continue
                return {
                    "law_name": law_name,
                    "jurisdiction": "JP",
                    "article": title or article_norm,
                    "text": text,
                    "theme": None,
                    "law_num": law_num,
                }
            return None

        return self._run_with_cache(cache_key, _fetch)
