import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://ailearn:ailearn123@localhost:5433/ai_learning"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        result = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        ))
        tables = [r[0] for r in result]
        print("All tables:")
        for t in tables:
            print(f"  {t}")

        lr_exists = "chapter_learning_runs" in tables
        ls_exists = "chapter_learning_stages" in tables
        print(f"\nchapter_learning_runs exists: {lr_exists}")
        print(f"chapter_learning_stages exists: {ls_exists}")

        if "chapters" in tables:
            result = await conn.execute(text("SELECT id, title FROM chapters ORDER BY id LIMIT 10"))
            print("\nChapters:")
            for r in result:
                print(f"  id={r[0]}, title={r[1]}")

        if "knowledge_points" in tables:
            result = await conn.execute(text("SELECT id, chapter_id, title FROM knowledge_points ORDER BY id LIMIT 10"))
            print("\nKnowledge points:")
            for r in result:
                print(f"  id={r[0]}, chapter_id={r[1]}, title={r[2]}")

    await engine.dispose()

asyncio.run(main())
