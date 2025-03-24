import sqlite3
import logging

logger = logging.getLogger(__name__)

def initialize_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        token TEXT,
        instagram_username TEXT,
        telegram_username TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS processed_messages (
        message_id TEXT PRIMARY KEY
    )''')
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def register_user(telegram_id, telegram_username):
    try:
        token = str(telegram_id) + "_token"
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO users (telegram_id, token, telegram_username) VALUES (?, ?, ?)", 
                  (telegram_id, token, telegram_username))
        conn.commit()
        conn.close()
        return token
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        return None

def get_telegram_id_by_token(token):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT telegram_id FROM users WHERE token = ?", (token,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_telegram_id_by_instagram_username(username):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT telegram_id FROM users WHERE instagram_username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def update_instagram_username(telegram_id, username):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE users SET instagram_username = ? WHERE telegram_id = ?", (username, telegram_id))
    conn.commit()
    conn.close()

def is_message_processed(message_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT message_id FROM processed_messages WHERE message_id = ?", (message_id,))
    result = c.fetchone()
    conn.close()
    return bool(result)

def mark_message_processed(message_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO processed_messages (message_id) VALUES (?)", (message_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT telegram_id, token, instagram_username, telegram_username FROM users")
    users = c.fetchall()
    conn.close()
    return users
