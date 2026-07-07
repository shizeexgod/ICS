import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as s:
        r = await s.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'company_managers' ORDER BY ordinal_position"
        ))
        for row in r:
            print(row)

asyncio.run(main())
