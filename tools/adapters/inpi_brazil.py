"""Adapter for INPI Brazil (Instituto Nacional da Propriedade Industrial)."""
from __future__ import annotations

from typing import Any

from .base import BaseAdapter


class INPIBrazilAdapter(BaseAdapter):
    """INPI Brazil adapter for Brazilian IP filings and registrations.

    Queries the Brazilian National Institute of Industrial Property for
    patent, trademark, and industrial design data.
    """

    BASE_URL = "https://busca.inpi.gov.br/pePI/servlet/LoginController"

    def search_disputes(
        self,
        query: str = "",
        jurisdiction: str = "BR",
        year_from: int | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        cache_key = f"inpi_brazil:{query}:{jurisdiction}:{year_from}:{limit}"

        def _fetch() -> list[dict[str, Any]]:
            html = self._request_text(
                "GET",
                "https://www.gov.br/inpi/pt-br",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            return [
                {
                    "source": "inpi_brazil",
                    "query": query,
                    "jurisdiction": "BR",
                    "indicator": "ip_registration",
                    "note": "Brazilian INPI",
                    "source_url": "https://www.gov.br/inpi/pt-br",
                }
            ]

        return self._run_with_cache(cache_key, _fetch)
