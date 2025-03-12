import json
import os
import uuid

DB_FILE = "database.json"

def initialize_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({}, f)
        print(f"پایگاه داده جدید ایجاد شد: {DB_FILE}")

def register_user(telegram_id):
    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        
        token = str(uuid.uuid4())[:8]
        user_key = f"user_{telegram_id}"
        db[user_key] = {"telegram_id": telegram_id, "token": token}
        
        with open(DB_FILE, "w") as f:
            json.dump(db, f)
        
        return token
    except Exception as e:
        print(f"خطا در ثبت کاربر: {str(e)}")
        return None

def get_telegram_id_by_token(token):
    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        
        for key, value in db.items():
            if key.startswith("user_") and value.get("token") == token:
                return value["telegram_id"]
        return None
    except Exception as e:
        print(f"خطا در جستجوی توکن: {str(e)}")
        return None

def update_instagram_username(telegram_id, instagram_username):
    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        
        user_key = f"user_{telegram_id}"
        if user_key in db:
            db[user_key]["instagram_username"] = instagram_username
            with open(DB_FILE, "w") as f:
                json.dump(db, f)
            return True
        return False
    except Exception as e:
        print(f"خطا در به‌روزرسانی نام کاربری اینستاگرام: {str(e)}")
        return False

def get_telegram_id_by_instagram_username(instagram_username):
    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        
        for key, value in db.items():
            if key.startswith("user_") and value.get("instagram_username") == instagram_username:
                return value["telegram_id"]
        return None
    except Exception as e:
        print(f"خطا در جستجوی نام کاربری اینستاگرام: {str(e)}")
        return None

def is_message_processed(message_id):
    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        
        processed_key = "processed_messages"
        if processed_key not in db:
            db[processed_key] = []
            with open(DB_FILE, "w") as f:
                json.dump(db, f)
            return False
        
        return message_id in db[processed_key]
    except Exception as e:
        print(f"خطا در بررسی پیام پردازش شده: {str(e)}")
        return False

def mark_message_processed(message_id):
    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        
        processed_key = "processed_messages"
        if processed_key not in db:
            db[processed_key] = []
        
        if message_id not in db[processed_key]:
            db[processed_key].append(message_id)
            with open(DB_FILE, "w") as f:
                json.dump(db, f)
        return True
    except Exception as e:
        print(f"خطا در علامت‌گذاری پیام پردازش شده: {str(e)}")
        return False

def keys():
    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        return db.keys()
    except Exception as e:
        print(f"خطا در دریافت کلیدها: {str(e)}")
        return []

def __getitem__(key):
    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        return db.get(key, {})
    except Exception as e:
        print(f"خطا در دریافت داده: {str(e)}")
        return {}
