"""Apply a single migration file by name."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "supabase" / "migrations"


def _dsn_from_env() -> str:
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "DATABASE_URL":
                url = value.strip().strip('"').strip("'")
                return url.replace("postgresql+asyncpg://", "postgresql://", 1)

    from app.core.config import settings

    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


async def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/apply_one_migration.py 012_referrals.sql")
        return 1

    name = sys.argv[1]
    path = MIGRATIONS_DIR / name
    if not path.exists():
        print(f"ERROR: migration not found: {path}")
        return 1

    sql = path.read_text(encoding="utf-8")
    print(f"Applying {name}...")

    try:
        conn = await asyncpg.connect(_dsn_from_env())
    except Exception as exc:
        print(f"ERROR: cannot connect: {exc}")
        return 1

    try:
        await conn.execute(sql)
        print(f"OK: {name}")
    finally:
        await conn.close()

    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(asyncio.run(main()))
