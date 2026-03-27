"""Shared utilities for external API adapters."""

from __future__ import annotations

import hashlib
import json
import random
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CACHE_TTL_SECONDS = 86400


class AdapterError(RuntimeError):
    """Raised when an adapter cannot fetch or parse external API data."""


class BaseAdapter:
    """Base adapter with timeout, SQLite cache, and caching."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        timeout_seconds: float = 30.0,
        cache_ttl_seconds: int = CACHE_TTL_SECONDS,
    ) -> None:
        self.cache_dir = cache_dir or (Path(__file__).resolve().parents[2] / "data" / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        self._init_db()

    @property
    def _db_path(self) -> Path:
        return self.cache_dir / "cache.db"

    def _cache_db_key(self, cache_key: str) -> str:
        return hashlib.sha256(cache_key.encode("utf-8")).hexdigest()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache(
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            )

    def _load_cached(self, cache_key: str) -> Any | None:
        key = self._cache_db_key(cache_key)
        now = time.time()

        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT data, expires_at FROM cache WHERE key = ?",
                (key,),
            ).fetchone()

            if row is None:
                return None

            data_text, expires_at = row
            if not isinstance(expires_at, (int, float)) or float(expires_at) < now:
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                return None

        try:
            return json.loads(data_text)
        except json.JSONDecodeError:
            return None

    def _save_cached(self, cache_key: str, data: Any) -> None:
        key = self._cache_db_key(cache_key)
        payload = json.dumps(data, ensure_ascii=False)
        expires_at = time.time() + self.cache_ttl_seconds

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache(key, data, expires_at)
                VALUES(?, ?, ?)
                """,
                (key, payload, expires_at),
            )

        if random.random() < 0.1:
            self._cleanup_expired()

    def _cleanup_expired(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM cache WHERE expires_at < ?", (time.time(),))

    def _request_text(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        body: str | None = None,
        max_retries: int = 3,
    ) -> str:
        target_url = url
        if params:
            query = urlencode({k: v for k, v in params.items() if v is not None})
            target_url = f"{url}?{query}"

        req = Request(
            target_url,
            data=body.encode("utf-8") if body is not None else None,
            method=method.upper(),
            headers=headers or {},
        )

        last_error = None
        for attempt in range(max_retries):
            try:
                with urlopen(req, timeout=self.timeout_seconds) as resp:  # nosec B310
                    charset = resp.headers.get_content_charset("utf-8")
                    return resp.read().decode(charset, errors="replace")
            except (URLError, OSError) as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))  # exponential backoff
                    continue
                break

        raise AdapterError(f"HTTP request failed after {max_retries} attempts: {target_url}") from last_error

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Any:
        text = self._request_text(method, url, params=params, headers=headers, body=body)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise AdapterError("Invalid JSON response") from exc

    def search_with_text(
        self,
        query: str,
        max_results: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Unified search interface that dispatches to the adapter's native method."""
        for method_name in ("search_cases", "search_statutes", "search_disputes", "search_stats"):
            method = getattr(self, method_name, None)
            if method is None:
                continue
            # Skip if it's inherited from BaseAdapter itself (not overridden)
            if getattr(method, "__func__", None) is BaseAdapter.__dict__.get(method_name):
                continue
            try:
                if method_name in ("search_cases",):
                    return method(query=query, limit=max_results, **kwargs)
                elif method_name in ("search_statutes",):
                    return method(query=query, limit=max_results, **kwargs)
                elif method_name in ("search_disputes",):
                    return method(query=query, limit=max_results, **kwargs)
                else:  # search_stats
                    return method(limit=max_results, **kwargs)
            except TypeError:
                # Fallback: try without query for stats-like methods
                return method(limit=max_results)
        raise AdapterError(f"{type(self).__name__} has no search method")

    def _run_with_cache(
        self,
        cache_key: str,
        fetcher: Callable[[], Any],
    ) -> Any:
        cached = self._load_cached(cache_key)
        if cached is not None:
            return cached

        data = fetcher()
        self._save_cached(cache_key, data)
        return data
