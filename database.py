import os
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL")

async def init_db():
    conn = await asyncpg.connect(dsn=DATABASE_URL)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            admin_msg_id BIGINT,
            user_id BIGINT
        );
        CREATE TABLE IF NOT EXISTS bans (
            user_id BIGINT PRIMARY KEY
        );
    """)
    await conn.close()

async def save_message(admin_msg_id: int, user_id: int):
    conn = await asyncpg.connect(dsn=DATABASE_URL)
    await conn.execute(
        "INSERT INTO messages (admin_msg_id, user_id) VALUES ($1, $2)",
        admin_msg_id, user_id
    )
    await conn.close()

async def get_user_by_admin_msg(admin_msg_id: int):
    conn = await asyncpg.connect(dsn=DATABASE_URL)
    row = await conn.fetchrow(
        "SELECT user_id FROM messages WHERE admin_msg_id = $1",
        admin_msg_id
    )
    await conn.close()
    return row["user_id"] if row else None

async def is_banned(user_id: int) -> bool:
    conn = await asyncpg.connect(dsn=DATABASE_URL)
    row = await conn.fetchrow("SELECT user_id FROM bans WHERE user_id = $1", user_id)
    await conn.close()
    return row is not None

async def ban_user(user_id: int):
    conn = await asyncpg.connect(dsn=DATABASE_URL)
    await conn.execute("INSERT INTO bans (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user_id)
    await conn.close()

async def unban_user(user_id: int):
    conn = await asyncpg.connect(dsn=DATABASE_URL)
    await conn.execute("DELETE FROM bans WHERE user_id = $1", user_id)
    await conn.close()
    
