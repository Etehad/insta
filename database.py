import os
import json
import uuid

# مسیر دیتابیس
DB_FILE = "database.json"

# دیکشنری برای نگهداری داده‌ها در حافظه
db_data = {}

def initialize_db():
    global db_data
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                db_data = json.load(f)
            print(f"دیتابیس با موفقیت بارگذاری شد. تعداد کلیدها: {len(db_data)}")
        except Exception as e:
            print(f"خطا در بارگذاری دیتابیس: {str(e)}")
            db_data = {}
    else:
        print("فایل دیتابیس وجود ندارد. دیتابیس جدید ایجاد شد.")
        db_data = {}
        save_db()

def save_db():
    try:
        with open(DB_FILE, 'w') as f:
            json.dump(db_data, f)
        print("دیتابیس با موفقیت ذخیره شد.")
    except Exception as e:
        print(f"خطا در ذخیره دیتابیس: {str(e)}")

def register_user(telegram_id):
    user_key = f"user_{telegram_id}"
    token = str(uuid.uuid4())
    db_data[user_key] = {
        "telegram_id": telegram_id,
        "token": token,
        "instagram_username": None
    }
    save_db()
    return token

def get_telegram_id_by_token(token):
    for key, value in db_data.items():
        if key.startswith("user_") and value.get("token") == token:
            return value.get("telegram_id")
    return None

def update_instagram_username(telegram_id, instagram_username):
    user_key = f"user_{telegram_id}"
    if user_key in db_data:
        db_data[user_key]["instagram_username"] = instagram_username
        save_db()
        return True
    return False

def get_telegram_id_by_instagram_username(instagram_username):
    for key, value in db_data.items():
        if key.startswith("user_") and value.get("instagram_username") == instagram_username:
            return value.get("telegram_id")
    return None

def is_message_processed(message_id):
    message_key = f"message_{message_id}"
    return message_key in db_data

def mark_message_processed(message_id):
    message_key = f"message_{message_id}"
    db_data[message_key] = True
    save_db()

def keys():
    return db_data.keys()

def __getitem__(key):
    return db_data.get(key, {})
