"""Apply SQL migrations from supabase/migrations/ to the configured Postgres DB."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "supabase" / "migrations"

# Run in dependency order; skip the monolithic schema if partial migrations exist.
MIGRATION_FILES = [
    "001_company_managers.sql",
    "002_users.sql",
]


def _dsn_from_env() -> str:
    from app.core.config import settings

    url = settings.DATABASE_URL
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def main() -> int:
    dsn = _dsn_from_env()
    print("Connecting to database...")

    try:
        conn = await asyncpg.connect(dsn)
    except Exception as exc:
        print(f"ERROR: cannot connect: {exc}")
        return 1

    try:
        for name in MIGRATION_FILES:
            path = MIGRATIONS_DIR / name
            if not path.exists():
                print(f"SKIP: {name} (file not found)")
                continue
            sql = path.read_text(encoding="utf-8")
            print(f"Applying {name}...")
            await conn.execute(sql)
            print(f"OK: {name}")

        row = await conn.fetchrow(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'company_managers'
            ) AS exists
            """
        )
        print(f"company_managers table exists: {row['exists']}")
    finally:
        await conn.close()

    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(asyncio.run(main()))
