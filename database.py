import sqlite3

def init_db():
    conn = sqlite3.connect("bridge_bot.db")
    cursor = conn.cursor()
    # Таблица связывает ID сообщения у получателя с ID реального отправителя
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_msg_id INTEGER,
            sender_id INTEGER,
            recipient_id INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

def save_bridge(target_msg_id: int, sender_id: int, recipient_id: int):
    conn = sqlite3.connect("bridge_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (target_msg_id, sender_id, recipient_id) VALUES (?, ?, ?)",
        (target_msg_id, sender_id, recipient_id)
    )
    conn.commit()
    conn.close()

def get_original_sender(target_msg_id: int, recipient_id: int):
    conn = sqlite3.connect("bridge_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sender_id FROM messages WHERE target_msg_id = ? AND recipient_id = ?",
        (target_msg_id, recipient_id)
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
    
