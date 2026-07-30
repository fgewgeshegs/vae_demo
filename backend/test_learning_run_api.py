import asyncio
import aiohttp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

BASE = "http://localhost:8000/api/v1"
DATABASE_URL = "postgresql+asyncpg://ailearn:ailearn123@localhost:5433/ai_learning"

async def main():
    # First check what users exist
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT id, username, is_active FROM users LIMIT 10"))
        print("Users:")
        for r in result:
            print(f"  id={r[0]}, username={r[1]}, active={r[2]}")
    await engine.dispose()

    async with aiohttp.ClientSession() as session:
        # Try login with different credentials
        for username, password in [("user1", "user123"), ("admin", "admin123"), ("test", "test123"), ("demo", "demo123")]:
            async with session.post(f"{BASE}/auth/login", json={"username": username, "password": password}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    token = data.get("access_token")
                    print(f"\nLogin success with {username}: token={token[:20]}...")
                    break
                else:
                    detail = (await resp.json()).get("detail", "")
                    print(f"Login {username}: {resp.status} - {detail}")
        else:
            print("\nNo valid credentials found")
            return

        headers = {"Authorization": f"Bearer {token}"}

        # Try creating a learning run for chapter 1
        print("\n--- Creating learning run for chapter 1 ---")
        payload = {"chapter_id": 1}
        async with session.post(f"{BASE}/learning-runs", headers=headers, json=payload) as resp:
            print(f"Create run status: {resp.status}")
            body = await resp.text()
            print(f"Response: {body[:500]}")

asyncio.run(main())
