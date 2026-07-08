"""Supabase PostgREST client for direct table access (async-safe wrapper)."""

from __future__ import annotations

import asyncio
import logging
import re
from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)

_PROJECT_REF_RE = re.compile(r"@db\.([a-z0-9-]+)\.supabase\.co", re.IGNORECASE)


def _derive_supabase_url(database_url: str) -> str | None:
    """Build the Supabase REST URL from a Postgres DATABASE_URL when possible."""
    match = _PROJECT_REF_RE.search(database_url)
    if match:
        return f"https://{match.group(1)}.supabase.co"
    return None


@lru_cache
def _build_client() -> Client:
    url = settings.SUPABASE_URL or _derive_supabase_url(settings.DATABASE_URL)
    key = settings.SUPABASE_SERVICE_ROLE_KEY

    if not url or not key:
        raise RuntimeError(
            "Supabase client requires SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY "
            "(or DATABASE_URL with a supabase.co host plus SUPABASE_SERVICE_ROLE_KEY)."
        )

    return create_client(url, key)


class _AsyncSupabaseProxy:
    """Expose the sync Supabase client without blocking the event loop."""

    def table(self, name: str) -> Any:
        return _AsyncTableProxy(_build_client().table(name))


class _AsyncTableProxy:
    def __init__(self, table: Any) -> None:
        self._table = table

    def select(self, *columns: str) -> Any:
        return _AsyncQueryProxy(self._table.select(*columns))

    def upsert(self, data: dict[str, Any] | list[dict[str, Any]], **kwargs: Any) -> Any:
        return _AsyncQueryProxy(self._table.upsert(data, **kwargs))

    def delete(self) -> Any:
        return _AsyncQueryProxy(self._table.delete())

    def insert(self, data: dict[str, Any] | list[dict[str, Any]]) -> Any:
        return _AsyncQueryProxy(self._table.insert(data))


class _AsyncQueryProxy:
    def __init__(self, query: Any) -> None:
        self._query = query

    def eq(self, column: str, value: Any) -> _AsyncQueryProxy:
        self._query = self._query.eq(column, value)
        return self

    def execute(self) -> Any:
        raise RuntimeError("Use await query.execute_async() in async code.")

    async def execute_async(self) -> Any:
        try:
            return await asyncio.to_thread(self._query.execute)
        except Exception:
            logger.exception("Supabase query failed.")
            raise


# Public import expected by route modules.
supabase = _AsyncSupabaseProxy()
