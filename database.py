import json
import os
import uuid
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_FILE = "database.json"

def initialize_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({"users": {}, "processed_messages": [], "downloads": {}}, f)
        logger.info(f"پایگاه داده جدید ایجاد شد: {DB_FILE}")

def register_user(telegram_id):
    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        token = str(uuid.uuid4())
        db["users"][str(telegram_id)] = {"telegram_id": telegram_id, "token": token}
        with open(DB_FILE, "w") as f:
            json.dump(db, f)
        logger.info(f"کاربر ثبت شد: telegram_id={telegram_id}, token={token}")
        return token
    except Exception as e:
        logger.error(f"خطا در ثبت کاربر: {str(e)}")
        return None

def get_telegram_id_by_token(token):
    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        for user_id, data in db["users"].items():
            if data.get("token") == token:
                logger.info(f"توکن یافت شد: {token}, telegram_id={user_id}")
                return int(user_id)
        return None
    except Exception as e:
        logger.error(f"خطا در جستجوی توکن: {str(e)}")
        return None

def update_instagram_username(telegram_id, instagram_username):
    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        user_key = str(telegram_id)
        if user_key in db["users"]:
            db["users"][user_key]["instagram_username"] = instagram_username
            with open(DB_FILE, "w") as f:
                json.dump(db, f)
            logger.info(f"نام کاربری به‌روزرسانی شد: {instagram_username} برای {telegram_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی: {str(e)}")
        return False

def get_telegram_id_by_instagram_username(instagram_username):
    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        for user_id, data in db["users"].items():
            if data.get("instagram_username") == instagram_username:
                return int(user_id)
        return None
    except Exception as e:
        logger.error(f"خطا در جستجوی نام کاربری: {str(e)}")
        return None

def is_message_processed(message_id):
    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        return message_id in db["processed_messages"]
    except Exception as e:
        logger.error(f"خطا در بررسی پیام: {str(e)}")
        return False

def mark_message_processed(message_id):
    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        if message_id not in db["processed_messages"]:
            db["processed_messages"].append(message_id)
            with open(DB_FILE, "w") as f:
                json.dump(db, f)
            logger.info(f"پیام پردازش‌شده علامت‌گذاری شد: {message_id}")
        return True
    except Exception as e:
        logger.error(f"خطا در علامت‌گذاری: {str(e)}")
        return False

def get_user_downloads(user_id):
    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        return db["downloads"].get(str(user_id), [])
    except Exception as e:
        logger.error(f"خطا در دریافت تاریخچه: {str(e)}")
        return []

def add_download(user_id, download_type, timestamp):
    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        user_key = str(user_id)
        if user_key not in db["downloads"]:
            db["downloads"][user_key] = []
        db["downloads"][user_key].append({"type": download_type, "timestamp": timestamp})
        with open(DB_FILE, "w") as f:
            json.dump(db, f)
        logger.info(f"دانلود اضافه شد: {download_type} برای {user_id}")
    except Exception as e:
        logger.error(f"خطا در اضافه کردن دانلود: {str(e)}")
