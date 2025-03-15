import sqlite3
import uuid
import time

def initialize_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (telegram_id INTEGER PRIMARY KEY,
                  token TEXT,
                  instagram_username TEXT,
                  created_at INTEGER)
              ''')
    c.execute('''CREATE TABLE IF NOT EXISTS processed_messages
                 (message_id TEXT PRIMARY KEY,
                  processed_at INTEGER)
              ''')
    conn.commit()
    conn.close()

def register_user(telegram_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT token FROM users WHERE telegram_id = ?', (telegram_id,))
    result = c.fetchone()
    if result:
        token = result[0]
    else:
        token = str(uuid.uuid4())
        c.execute('INSERT INTO users (telegram_id, token, created_at) VALUES (?, ?, ?)',
                  (telegram_id, token, int(time.time())))
        conn.commit()
    conn.close()
    return token


def get_telegram_id_by_token(token):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT telegram_id FROM users WHERE token = ?', (token,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def update_instagram_username(telegram_id, instagram_username):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('UPDATE users SET instagram_username = ? WHERE telegram_id = ?',
              (instagram_username, telegram_id))
    conn.commit()
    conn.close()


def get_telegram_id_by_instagram_username(instagram_username):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT telegram_id FROM users WHERE instagram_username = ?', (instagram_username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def is_message_processed(message_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT 1 FROM processed_messages WHERE message_id = ?', (message_id,))
    result = c.fetchone()
    conn.close()
    return bool(result)

def mark_message_processed(message_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO processed_messages (message_id, processed_at) VALUES (?, ?)',
              (message_id, int(time.time())))
    conn.commit()
    conn.close()
