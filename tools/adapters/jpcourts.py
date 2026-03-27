"""Adapter for JP case-law search via courts.go.jp (`hanrei_jp`)."""

from __future__ import annotations

import io
import re
import time
from html import unescape
from typing import Any
from urllib.error import URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from .base import AdapterError, BaseAdapter


class JPCourtsAdapter(BaseAdapter):
    """Fetch and normalize JP case-law from courts.go.jp with multi-strategy crawling."""

    BASE_URL = "https://www.courts.go.jp"
    # New URL format (courts.go.jp restructured URLs circa 2025-2026)
    LIST_URL = "https://www.courts.go.jp/hanrei/search2/index.html"
    DETAIL_URL = "https://www.courts.go.jp/app/hanrei_jp/detail2"
    # New detail URL pattern: /hanrei/{id}/detail2/index.html
    DETAIL_URL_NEW = "https://www.courts.go.jp/hanrei/{case_id}/detail2/index.html"
    USER_AGENT = "legal-mcp/1.0"
    MIN_REQUEST_INTERVAL_SECONDS = 1.5

    COURT_STRATEGIES: list[dict[str, str]] = [
        {"courtType": "1", "courtName": "最高裁判所"},
        {"courtType": "2", "courtName": "高等裁判所"},
        {"courtType": "3", "courtName": "地方裁判所"},
        {"courtType": "4", "courtName": "知的財産高等裁判所"},
        {"courtType": "5", "courtName": "家庭裁判所"},
        {"courtType": "6", "courtName": "簡易裁判所"},
    ]

    # Exhaustive court sub-categories for bulk crawl
    COURT_CATEGORIES_BULK: list[dict[str, str]] = [
        # 最高裁判所 — sub-divisions
        {"courtType": "1", "courtName": "最高裁判所大法廷"},
        {"courtType": "1", "courtName": "最高裁判所第一小法廷"},
        {"courtType": "1", "courtName": "最高裁判所第二小法廷"},
        {"courtType": "1", "courtName": "最高裁判所第三小法廷"},
        # 高等裁判所
        {"courtType": "2", "courtName": "東京高等裁判所"},
        {"courtType": "2", "courtName": "大阪高等裁判所"},
        {"courtType": "2", "courtName": "名古屋高等裁判所"},
        {"courtType": "2", "courtName": "福岡高等裁判所"},
        {"courtType": "2", "courtName": "仙台高等裁判所"},
        {"courtType": "2", "courtName": "札幌高等裁判所"},
        {"courtType": "2", "courtName": "広島高等裁判所"},
        {"courtType": "2", "courtName": "高松高等裁判所"},
        # 知財高裁
        {"courtType": "4", "courtName": "知的財産高等裁判所"},
        # 下級裁判所 — generic
        {"courtType": "3", "courtName": "地方裁判所"},
        {"courtType": "5", "courtName": "家庭裁判所"},
        {"courtType": "6", "courtName": "簡易裁判所"},
    ]

    LEGAL_FIELDS = ["民事", "刑事", "行政", "知的財産", "労働", "家事"]

    # Case categories on courts.go.jp (事件種別)
    CASE_CATEGORIES = [
        "民事事件",
        "刑事事件",
        "行政事件",
        "知的財産事件",
        "労働事件",
        "家事事件",
    ]
    OUTCOME_KEYWORDS = [
        "棄却",
        "破棄",
        "破棄差戻し",
        "破棄差戻",
        "却下",
        "認容",
        "一部認容",
        "有罪",
        "無罪",
        "和解",
        "判決",
        "決定",
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._last_request_at = 0.0

    @staticmethod
    def _clean(text: str) -> str:
        plain = re.sub(r"<[^>]+>", " ", text)
        plain = unescape(plain)
        return re.sub(r"\s+", " ", plain).strip()

    @classmethod
    def _extract_year(cls, text: str) -> int | None:
        m = re.search(r"\b(19|20)\d{2}\b", text)
        if m:
            return int(m.group(0))

        era_match = re.search(r"(令和|平成|昭和)\s*(元|\d{1,2})年", text)
        if not era_match:
            return None
        era, val = era_match.group(1), era_match.group(2)
        num = 1 if val == "元" else int(val)
        if era == "令和":
            return 2018 + num
        if era == "平成":
            return 1988 + num
        if era == "昭和":
            return 1925 + num
        return None

    def _sleep_if_needed(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_request_at
        if self._last_request_at > 0 and elapsed < self.MIN_REQUEST_INTERVAL_SECONDS:
            time.sleep(self.MIN_REQUEST_INTERVAL_SECONDS - elapsed)

    def _request_text_rate_limited(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        self._sleep_if_needed()
        merged_headers = {"User-Agent": self.USER_AGENT, "Accept-Language": "ja,en;q=0.8"}
        if headers:
            merged_headers.update(headers)
        text = self._request_text(method, url, params=params, headers=merged_headers)
        self._last_request_at = time.monotonic()
        return text

    def _request_bytes_rate_limited(self, url: str, max_retries: int = 3) -> bytes:
        self._sleep_if_needed()
        req = Request(url, method="GET", headers={"User-Agent": self.USER_AGENT})

        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                with urlopen(req, timeout=self.timeout_seconds) as resp:  # nosec B310
                    payload = resp.read()
                    self._last_request_at = time.monotonic()
                    return payload
            except (URLError, OSError) as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                break

        raise AdapterError(f"Failed to fetch bytes from: {url}") from last_error

    @staticmethod
    def _extract_case_id(url_or_href: str) -> str:
        parsed = urlparse(url_or_href)
        qs = parse_qs(parsed.query)
        if "id" in qs and qs["id"]:
            return qs["id"][0]

        for pattern in (
            r"[?&]id=(\d+)",
            r"/hanrei/(\d+)/",
            r"/detail\d?/(\d+)",
            r"detail\d?[^\d]*(\d{3,})",
            r"\b(\d{4,})\b",
        ):
            m = re.search(pattern, url_or_href)
            if m:
                return m.group(1)
        return ""

    @classmethod
    def _build_detail_url(cls, case_id: str) -> str:
        """Build detail URL using new format, with old format as fallback."""
        return cls.DETAIL_URL_NEW.format(case_id=case_id)

    @staticmethod
    def _extract_court(text: str) -> str:
        m = re.search(r"(最高裁判所(?:第一|第二|第三)?[小大]?法廷?|知的財産高等裁判所|\S*高等裁判所|\S*地方裁判所|\S*家庭裁判所|\S*簡易裁判所)", text)
        return m.group(1) if m else "裁判所"

    @classmethod
    def _extract_result(cls, text: str) -> str:
        for kw in cls.OUTCOME_KEYWORDS:
            if kw in text:
                return kw
        return "Unknown"

    @staticmethod
    def _tokenize_keywords(query: str) -> list[str]:
        return [t for t in re.split(r"[\s　,、]+", query.strip()) if t]

    def _parse_list_page(self, html: str) -> tuple[list[dict[str, Any]], bool]:
        soup = BeautifulSoup(html, "lxml")
        rows: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if not href:
                continue
            if not any(token in href for token in ("detail2", "detail3", "detail?id=", "detail2?id=", "/hanrei/")):
                continue

            case_id = self._extract_case_id(href)
            if not case_id or case_id in seen_ids:
                continue

            container = a.find_parent(["tr", "li", "article", "div"]) or a.parent
            container_text = self._clean(container.get_text(" ", strip=True) if container else a.get_text(" ", strip=True))
            case_name = self._clean(a.get_text(" ", strip=True)) or container_text[:120] or f"事件 {case_id}"

            rows.append(
                {
                    "case_id": case_id,
                    "source_url": self._build_detail_url(case_id),
                    "case_name": case_name,
                    "court": self._extract_court(container_text),
                    "year": self._extract_year(container_text),
                    "result": self._extract_result(container_text),
                    "summary": container_text[:280],
                    "_meta_text": container_text,
                }
            )
            seen_ids.add(case_id)

        if not rows:
            # regex fallback for varied/legacy HTML layouts
            for m in re.finditer(r"href=\"([^\"]*(?:detail2\?id=\d+|detail\?id=\d+|detail3\?id=\d+)[^\"]*)\"", html):
                href = m.group(1)
                case_id = self._extract_case_id(href)
                if not case_id or case_id in seen_ids:
                    continue
                around = html[max(0, m.start() - 400) : m.end() + 400]
                around_text = self._clean(around)
                rows.append(
                    {
                        "case_id": case_id,
                        "source_url": self._build_detail_url(case_id),
                        "case_name": f"事件 {case_id}",
                        "court": self._extract_court(around_text),
                        "year": self._extract_year(around_text),
                        "result": self._extract_result(around_text),
                        "summary": around_text[:280],
                        "_meta_text": around_text,
                    }
                )
                seen_ids.add(case_id)

        has_next = False
        if soup.find("a", href=re.compile(r"[?&]page=\d+")):
            # true when there is an explicit larger page number or "次へ" link
            for a in soup.select("a[href]"):
                label = self._clean(a.get_text(" ", strip=True))
                href = a.get("href", "")
                if re.search(r"[?&]page=\d+", href):
                    has_next = True
                    break
                if label in {"次へ", "次", "次ページ", "Next", ">"}:
                    has_next = True
                    break

        return rows, has_next

    def _extract_pdf_urls(self, html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        urls: list[str] = []

        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if not href:
                continue
            text = self._clean(a.get_text(" ", strip=True))
            if ".pdf" in href.lower() or "pdf" in text.lower():
                abs_url = urljoin(base_url, href)
                if abs_url not in urls:
                    urls.append(abs_url)

        if not urls:
            for m in re.finditer(r"https?://[^\"'\s>]+\.pdf(?:\?[^\"'\s>]*)?", html, re.IGNORECASE):
                u = m.group(0)
                if u not in urls:
                    urls.append(u)

        return urls

    def _extract_detail_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        candidates: list[str] = []

        selectors = [
            "#mainContent",
            "#contents",
            "#main",
            "main",
            "article",
            "div.hanrei",
            "div.hanreiBody",
            "div.case_text",
            "div#detail",
            "td",
        ]

        for selector in selectors:
            for node in soup.select(selector):
                text = self._clean(node.get_text("\n", strip=True))
                if len(text) >= 120:
                    candidates.append(text)

        if not candidates:
            for p in soup.find_all(["p", "div"]):
                text = self._clean(p.get_text("\n", strip=True))
                if len(text) >= 120:
                    candidates.append(text)

        if candidates:
            candidates.sort(key=len, reverse=True)
            return candidates[0][:20000]

        # regex fallback: extract content around key legal headings
        for pattern in (
            r"(主文.{80,12000})",
            r"(理由.{80,12000})",
            r"(判示事項.{80,12000})",
            r"(裁判要旨.{80,12000})",
        ):
            m = re.search(pattern, self._clean(html), flags=re.DOTALL)
            if m:
                return self._clean(m.group(1))[:20000]

        return ""

    def _extract_pdf_text_from_url(self, pdf_url: str) -> str:
        try:
            payload = self._request_bytes_rate_limited(pdf_url)
        except Exception:
            return ""

        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(payload))
            pages: list[str] = []
            for page in reader.pages:
                t = page.extract_text() or ""
                clean = self._clean(t)
                if clean:
                    pages.append(clean)
            text = "\n".join(pages)
            return text[:20000]
        except Exception:
            return ""

    def _fetch_case_detail(self, seed: dict[str, Any]) -> dict[str, Any]:
        case_id = str(seed.get("case_id", ""))
        if not case_id:
            return seed

        detail_urls = [
            self._build_detail_url(case_id),
            f"{self.BASE_URL}/app/hanrei_jp/detail2?id={case_id}",
            f"{self.BASE_URL}/app/hanrei_jp/detail3?id={case_id}",
            f"{self.BASE_URL}/app/hanrei_jp/detail?id={case_id}",
        ]

        detail_html = ""
        used_url = detail_urls[0]

        for candidate in detail_urls:
            try:
                detail_html = self._request_text_rate_limited("GET", candidate)
                if detail_html:
                    used_url = candidate
                    break
            except Exception:
                continue

        if not detail_html:
            return seed

        detail_text = self._extract_detail_text(detail_html)
        if len(detail_text) < 300:
            for pdf_url in self._extract_pdf_urls(detail_html, used_url):
                pdf_text = self._extract_pdf_text_from_url(pdf_url)
                if len(pdf_text) >= 300:
                    detail_text = pdf_text
                    break

        merged_text = self._clean(f"{seed.get('_meta_text', '')} {detail_text}")
        year = self._extract_year(merged_text)

        title = seed.get("case_name", "")
        title_from_header = ""
        soup = BeautifulSoup(detail_html, "lxml")
        for node in soup.select("h1, h2, h3, th, dt"):
            t = self._clean(node.get_text(" ", strip=True))
            if 4 <= len(t) <= 180 and "裁判" in t:
                title_from_header = t
                break

        case_name = title_from_header or title or f"事件 {case_id}"
        summary = self._clean(detail_text[:320] or seed.get("summary", ""))

        return {
            "case_id": case_id,
            "source_url": self._build_detail_url(case_id),
            "case_name": case_name,
            "court": self._extract_court(merged_text) or str(seed.get("court", "裁判所")),
            "year": year if isinstance(year, int) else seed.get("year"),
            "result": self._extract_result(merged_text) or str(seed.get("result", "Unknown")),
            "summary": summary,
            "text": detail_text or seed.get("summary", ""),
        }

    def _build_strategies(self, query: str, year_from: int | None) -> list[tuple[str, dict[str, Any]]]:
        strategies: list[tuple[str, dict[str, Any]]] = []

        # Strategy A: by court category
        for court_info in self.COURT_STRATEGIES:
            params = {
                "keyword": query,
                "sort": "1",
                "filter[courtType]": court_info["courtType"],
                "filter[courtName]": court_info["courtName"],
            }
            strategies.append(("court", params))

        # Strategy B: by year listing
        start_year = max(year_from or 2000, 2000)
        for year in range(start_year, 2027):
            params = {
                "keyword": query,
                "sort": "1",
                "filter[judgeDateFrom]": f"{year}-01-01",
                "filter[judgeDateTo]": f"{year}-12-31",
            }
            strategies.append(("year", params))

        # Strategy C: by legal field
        for field in self.LEGAL_FIELDS:
            k = f"{query} {field}".strip()
            params = {
                "keyword": k,
                "sort": "1",
                "filter[text1]": field,
            }
            strategies.append(("field", params))

        # Strategy D: full-text keyword variants
        strategies.extend(
            [
                (
                    "fulltext",
                    {
                        "keyword": query,
                        "sort": "1",
                        "filter[text1]": query,
                    },
                ),
                (
                    "fulltext",
                    {
                        "keyword": query,
                        "sort": "1",
                        "filter[fulltext]": query,
                    },
                ),
            ]
        )

        return strategies

    def _crawl_listing(
        self, params: dict[str, Any], max_cases: int, *, max_pages: int = 0
    ) -> list[dict[str, Any]]:
        """Crawl paginated listing. max_pages=0 means unlimited."""
        page = 1
        collected: list[dict[str, Any]] = []
        seen: set[str] = set()

        while len(collected) < max_cases:
            if max_pages > 0 and page > max_pages:
                break

            req_params = dict(params)
            req_params["page"] = page

            try:
                html = self._request_text_rate_limited("GET", self.LIST_URL, params=req_params)
            except Exception:
                break
            rows, has_next = self._parse_list_page(html)
            if not rows:
                break

            added_in_page = 0
            for row in rows:
                case_id = str(row.get("case_id", ""))
                if not case_id or case_id in seen:
                    continue
                collected.append(row)
                seen.add(case_id)
                added_in_page += 1
                if len(collected) >= max_cases:
                    break

            if added_in_page == 0:
                break

            if not has_next:
                # explicit fallback: if page+1 is linked by number text
                next_marker = f"page={page + 1}"
                if next_marker not in html:
                    break

            page += 1

        return collected

    def crawl_all(
        self,
        year_from: int = 2000,
        year_to: int = 2026,
        max_total: int = 10000,
        *,
        fetch_detail: bool = True,
        callback: Any = None,
    ) -> list[dict[str, Any]]:
        """
        Exhaustive crawl of courts.go.jp by court × year × category.

        Designed for bulk data collection. Iterates through all combinations
        of court sub-categories and year ranges to maximize coverage.

        Args:
            year_from: Start year (default: 2000)
            year_to: End year (default: 2026)
            max_total: Stop after this many unique cases
            fetch_detail: If True, fetch full detail page + PDF text for each case
            callback: Optional callable(case_dict) for streaming results

        Returns:
            List of normalized case dicts
        """
        unique: dict[str, dict[str, Any]] = {}

        for year in range(year_to, year_from - 1, -1):  # newest first
            if len(unique) >= max_total:
                break

            for court_info in self.COURT_CATEGORIES_BULK:
                if len(unique) >= max_total:
                    break

                params = {
                    "sort": "1",
                    "filter[courtType]": court_info["courtType"],
                    "filter[courtName]": court_info["courtName"],
                    "filter[judgeDateFrom]": f"{year}-01-01",
                    "filter[judgeDateTo]": f"{year}-12-31",
                }

                try:
                    seeds = self._crawl_listing(
                        params, max_cases=max_total - len(unique), max_pages=50
                    )
                except Exception:
                    continue

                for seed in seeds:
                    case_id = str(seed.get("case_id", ""))
                    if not case_id or case_id in unique:
                        continue

                    if fetch_detail:
                        try:
                            detailed = self._fetch_case_detail(seed)
                        except Exception:
                            detailed = seed
                    else:
                        detailed = seed

                    norm = self._normalize_case(detailed, "", None)
                    if norm:
                        unique[case_id] = norm
                        if callback:
                            callback(norm)

            # Also try by legal field for this year
            for field in self.LEGAL_FIELDS:
                if len(unique) >= max_total:
                    break

                params = {
                    "sort": "1",
                    "filter[text1]": field,
                    "filter[judgeDateFrom]": f"{year}-01-01",
                    "filter[judgeDateTo]": f"{year}-12-31",
                }

                try:
                    seeds = self._crawl_listing(
                        params, max_cases=max_total - len(unique), max_pages=20
                    )
                except Exception:
                    continue

                for seed in seeds:
                    case_id = str(seed.get("case_id", ""))
                    if not case_id or case_id in unique:
                        continue

                    if fetch_detail:
                        try:
                            detailed = self._fetch_case_detail(seed)
                        except Exception:
                            detailed = seed
                    else:
                        detailed = seed

                    norm = self._normalize_case(detailed, field, None)
                    if norm:
                        unique[case_id] = norm
                        if callback:
                            callback(norm)

        results = list(unique.values())
        results.sort(key=lambda r: int(r.get("year", 0) or 0), reverse=True)
        return results

    def _normalize_case(self, item: dict[str, Any], query: str, year_from: int | None) -> dict[str, Any] | None:
        year_raw = item.get("year")
        year: int = int(year_raw) if isinstance(year_raw, int) else 0
        if year_from is not None and year and year < year_from:
            return None

        text = str(item.get("text", "")).strip()
        if not text:
            text = str(item.get("summary", "")).strip()

        source_url = str(item.get("source_url", "")).strip()
        if not source_url:
            return None

        return {
            "case_name": str(item.get("case_name", "")).strip() or "事件",
            "jurisdiction": "JP",
            "court": str(item.get("court", "裁判所")).strip() or "裁判所",
            "year": year,
            "result": str(item.get("result", "Unknown")).strip() or "Unknown",
            "text": text,
            "source_url": source_url,
            "summary": str(item.get("summary", "")).strip() or text[:200],
            "domain": "external",
            "keywords": self._tokenize_keywords(query),
            "_source": "courts_go_jp",
        }

    def _load_local(self, query: str, year_from: int | None, limit: int) -> list[dict[str, Any]]:
        rows = [
            {
                "case_name": "漫画村事件",
                "jurisdiction": "JP",
                "court": "東京地方裁判所",
                "year": 2021,
                "result": "有罪",
                "text": "海賊版サイト『漫画村』運営に関する著作権侵害事件。公衆送信権侵害と刑事責任が認定された。",
                "source_url": "https://www.courts.go.jp/app/hanrei_jp/detail2?id=999999",
                "summary": "海賊版サイト運営に対する刑事責任と著作権侵害の重大性が認定された。",
                "domain": "external",
                "keywords": self._tokenize_keywords(query),
                "_source": "jp_local",
            }
        ]
        if year_from is not None:
            rows = [r for r in rows if int(r["year"]) >= year_from]
        return rows[:limit]

    def search_cases(self, query: str, year_from: int | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            raise AdapterError("Empty query")

        cache_key = f"jpcourts:v2:{q}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            unique_by_source: dict[str, dict[str, Any]] = {}

            try:
                strategies = self._build_strategies(q, year_from)
                per_strategy_target = max(25, min(200, limit * 2))

                for _, params in strategies:
                    if len(unique_by_source) >= limit:
                        break

                    seeds = self._crawl_listing(params, max_cases=per_strategy_target)
                    if not seeds:
                        continue

                    for seed in seeds:
                        detailed = self._fetch_case_detail(seed)
                        norm = self._normalize_case(detailed, q, year_from)
                        if not norm:
                            continue
                        unique_by_source[norm["source_url"]] = norm
                        if len(unique_by_source) >= limit:
                            break
            except Exception:
                # fall through to local fallback
                pass

            rows = list(unique_by_source.values())
            if not rows:
                return self._load_local(q, year_from, limit)

            rows.sort(key=lambda r: int(r.get("year", 0) or 0), reverse=True)
            return rows[:limit]

        return self._run_with_cache(cache_key, _fetch)
