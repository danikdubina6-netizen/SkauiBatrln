import sqlite3

def init_db():
    conn = sqlite3.connect("bridge_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_msg_id INTEGER,
            user_id INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

def save_message(admin_msg_id: int, user_id: int):
    conn = sqlite3.connect("bridge_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (admin_msg_id, user_id) VALUES (?, ?)",
        (admin_msg_id, user_id)
    )
    conn.commit()
    conn.close()

def get_user_by_admin_msg(admin_msg_id: int):
    conn = sqlite3.connect("bridge_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM messages WHERE admin_msg_id = ?",
        (admin_msg_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def is_banned(user_id: int) -> bool:
    conn = sqlite3.connect("bridge_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM bans WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def ban_user(user_id: int):
    conn = sqlite3.connect("bridge_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO bans (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    
