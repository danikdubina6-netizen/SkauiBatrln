import aiosqlite

DB_FILE = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_msg_id INTEGER,
                user_id INTEGER,
                user_msg_id INTEGER
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bans (
                user_id INTEGER PRIMARY KEY
            );
        """)
        await db.commit()

async def save_message(admin_msg_id: int, user_id: int, user_msg_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT INTO messages (admin_msg_id, user_id, user_msg_id) VALUES (?, ?, ?)",
            (admin_msg_id, user_id, user_msg_id)
        )
        await db.commit()

async def get_user_by_admin_msg(admin_msg_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        # Сначала ищем точное совпадение
        async with db.execute(
            "SELECT user_id FROM messages WHERE admin_msg_id = ?",
            (admin_msg_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
        
        # Если не нашли, ищем по соседним ID (если реплай был на текст, а не на кнопку)
        async with db.execute(
            "SELECT user_id FROM messages WHERE admin_msg_id BETWEEN ? AND ?",
            (admin_msg_id - 1, admin_msg_id + 1)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def get_user_msg_id(admin_msg_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT user_msg_id FROM messages WHERE admin_msg_id = ?",
            (admin_msg_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def is_banned(user_id: int) -> bool:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT user_id FROM bans WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None

async def ban_user(user_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT OR IGNORE INTO bans (user_id) VALUES (?)",
            (user_id,)
        )
        await db.commit()

async def unban_user(user_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "DELETE FROM bans WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()
        
