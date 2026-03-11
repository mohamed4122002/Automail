import asyncio
import sys
import os

sys.path.append(os.getcwd())

from backend.db import init_db, close_db
from backend.models import User

async def check():
    try:
        await init_db()
        count = await User.count()
        print(f"Total Users: {count}")
        users = await User.find_all().to_list()
        for u in users:
            print(f"- {u.email} | Role: {u.role} | Roles: {getattr(u, 'roles', 'N/A')}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(check())
