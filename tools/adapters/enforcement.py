"""Adapter for EU IPR enforcement data via TAXUD page scraping."""
from __future__ import annotations

import re
from html import unescape
from typing import Any
from urllib.parse import urljoin

from .base import AdapterError, BaseAdapter

# Pattern to detect language-selector links: the current page URL with a
# different 2-letter locale suffix (e.g., _bg, _es, _fr).
_LANG_SELECTOR_RE = re.compile(
    r"counterfeit-piracy-other-ipr-violations_[a-z]{2}$", re.IGNORECASE
)


class EnforcementAdapter(BaseAdapter):
    """IP enforcement adapter (EU customs/IPR enforcement page).

    Scrapes the EU TAXUD page on counterfeit, piracy, and other IPR
    violations for enforcement-related links, regulations, and reports.
    """

    STATS_URL = (
        "https://taxation-customs.ec.europa.eu/customs/prohibitions-restrictions/"
        "counterfeit-piracy-other-ipr-violations_en"
    )

    # Strong indicators: if these appear in the link text the link is
    # almost certainly about IP enforcement content (not just navigation).
    _STRONG_TOKENS = (
        "counterfeit",
        "piracy",
        "intellectual property",
        "ipr",
        "enforcement",
        "seizure",
        "trips",
        "defend your rights",
        "facts and figures",
        "implementing regulation",
    )

    # Weaker indicators that qualify only when the link text is descriptive
    # (longer than a simple navigation label).
    _WEAK_TOKENS = (
        "regulation",
        "report",
        "annual",
        "statistics",
    )

    # Minimum text length for a link matched only by weak tokens.
    _MIN_TEXT_LEN_WEAK = 20

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "EU",
        year_from: int | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        cache_key = f"enforcement:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            try:
                html = self._request_text(
                    "GET",
                    self.STATS_URL,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    },
                )
            except AdapterError as exc:
                raise AdapterError(
                    f"Failed to fetch EU IPR enforcement page ({self.STATS_URL}); "
                    "the site may be unavailable or blocking automated access"
                ) from exc

            lower_html = html.lower()
            if any(
                token in lower_html
                for token in (
                    "captcha",
                    "cloudflare",
                    "attention required",
                    "access denied",
                    "security check",
                )
            ):
                raise AdapterError(
                    f"EU IPR enforcement page returned an anti-bot challenge "
                    f"at {self.STATS_URL}; cannot parse content"
                )

            q_norm = query.strip().lower()

            # The page is specifically about "counterfeit, piracy and other
            # IPR violations".  When the query matches the overall page
            # topic we include all enforcement-relevant links without
            # further per-link query filtering.
            page_topic_tokens = (
                "counterfeit", "piracy", "ipr", "intellectual property",
                "enforcement", "customs",
            )
            query_matches_page = not q_norm or any(
                tok in q_norm for tok in page_topic_tokens
            )

            rows: list[dict[str, Any]] = []
            seen_hrefs: set[str] = set()

            for match in re.finditer(
                r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                html,
                flags=re.IGNORECASE | re.DOTALL,
            ):
                href, inner = match.groups()
                if href in seen_hrefs:
                    continue
                seen_hrefs.add(href)

                # Skip language-selector links (same page in different locales)
                if _LANG_SELECTOR_RE.search(href):
                    continue

                # Clean link text
                text = unescape(re.sub(r"<[^>]+>", " ", inner))
                text = re.sub(r"\s+", " ", text).strip()
                if not text or len(text) < 5:
                    continue

                lower_text = text.lower()

                # Check if the link looks enforcement-relevant.
                has_strong = any(tok in lower_text for tok in self._STRONG_TOKENS)
                has_weak = any(tok in lower_text for tok in self._WEAK_TOKENS)

                if has_strong:
                    pass  # always include
                elif has_weak and len(text) >= self._MIN_TEXT_LEN_WEAK:
                    pass  # include if text is descriptive enough
                else:
                    continue  # skip generic navigation links

                # Extract surrounding context for year matching
                context = html[max(0, match.start() - 300): min(len(html), match.end() + 300)]

                # Query filter
                if not query_matches_page:
                    lower_context = context.lower()
                    if (
                        q_norm not in lower_text
                        and q_norm not in href.lower()
                        and q_norm not in lower_context
                    ):
                        continue

                year_match = re.search(r"\b(20\d{2}|19\d{2})\b", context)
                year = int(year_match.group(1)) if year_match else None

                if year_from and year and year < year_from:
                    continue

                full_url = urljoin(self.STATS_URL, href)

                # Determine the indicator sub-type
                indicator = "customs_ip_enforcement_publication"
                if "regulation" in lower_text or "eur-lex" in href.lower():
                    indicator = "customs_ip_enforcement_regulation"
                elif "statistic" in lower_text or "facts" in lower_text or "figures" in lower_text:
                    indicator = "customs_ip_enforcement_statistics"

                rows.append(
                    {
                        "indicator": indicator,
                        "jurisdiction": jurisdiction.upper(),
                        "year": year,
                        "value": 1.0,
                        "unit": "document",
                        "source": "enforcement",
                        "note": f"{text} | {full_url}",
                        "title": text,
                        "text": text,
                        "source_url": full_url,
                    }
                )
                if len(rows) >= limit:
                    break

            if not rows:
                raise AdapterError("No enforcement content found")
            return rows

        return self._run_with_cache(cache_key, _fetch)
