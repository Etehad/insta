import os
import sys
import json
import logging
import time
import re
import threading
from datetime import datetime
import uuid

try:
    from PIL import Image
except ImportError:
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow>=8.1.1"])
        print("Pillow با موفقیت نصب شد.")
    except Exception as e:
        print(f"خطا در نصب Pillow: {str(e)}")

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
import instaloader
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, ClientError, LoginRequired
import database as db
from flask import Flask, request

# تنظیم لاگ‌گیری
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تنظیمات
TOKEN = os.getenv('TOKEN', '7872003751:AAGK4IHqCqr-8nxxAfj1ImQNpRMlRHRGxxU')
ADMIN_ID = 6473845417
REQUIRED_CHANNELS = [{"chat_id": "-1001860545237", "username": "@task_1_4_1_force"}]
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME', 'etehadtaskforce')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD', 'Aa123456*')
SESSION_FILE = "session.json"
PROXY = os.getenv('INSTAGRAM_PROXY', None)

# راه‌اندازی Flask
app = Flask(__name__)
updater = Updater(TOKEN, use_context=True)
dispatcher = updater.dispatcher

# تنظیمات اینستاگرام
ig_client = Client()
if PROXY:
    ig_client.set_proxy(PROXY)
    logger.info(f"پروکسی تنظیم شد: {PROXY}")

def login_with_session():
    try:
        if os.path.exists(SESSION_FILE):
            logger.info(f"بارگذاری session از {SESSION_FILE}")
            ig_client.load_settings(SESSION_FILE)
            ig_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            logger.info(f"با موفقیت به اینستاگرام ({INSTAGRAM_USERNAME}) با session وارد شد.")
        else:
            logger.info(f"فایل {SESSION_FILE} وجود ندارد. در حال ورود به اینستاگرام...")
            ig_client.delay_range = [5, 10]
            ig_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            logger.info(f"با موفقیت به اینستاگرام ({INSTAGRAM_USERNAME}) وارد شد.")
            ig_client.dump_settings(SESSION_FILE)
            logger.info(f"session با موفقیت در {SESSION_FILE} ذخیره شد.")
    except TwoFactorRequired as e:
        logger.error("احراز هویت دو مرحله‌ای مورد نیاز است!")
        two_factor_code = os.getenv('TWO_FACTOR_CODE')
        if two_factor_code:
            ig_client.two_factor_login(two_factor_code)
            ig_client.dump_settings(SESSION_FILE)
        else:
            raise Exception("کد 2FA تنظیم نشده!")
    except ClientError as e:
        logger.error(f"خطا در ورود به اینستاگرام: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"خطای غیرمنتظره در ورود: {str(e)}")
        raise

try:
    login_with_session()
except Exception as e:
    logger.error(f"ورود به اینستاگرام ناموفق بود: {str(e)}")
    exit(1)

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(json.loads(request.get_data().decode('utf-8')), updater.bot)
    dispatcher.process_update(update)
    return '', 200

@app.route('/')
def ping():
    return "Bot is alive!", 200

def setup_handlers(dp):
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.regex(r'^@[\w.]+$'), handle_username))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))
    dp.add_handler(CommandHandler("admin", admin))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(CallbackQueryHandler(admin_button_handler))

def start(update: Update, context):
    if not check_membership(update, context):
        return
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("دریافت توکن اتصال به اینستاگرام", callback_data="get_token")],
        [InlineKeyboardButton("راهنمای اتصال به اینستاگرام", callback_data="instagram_help")],
        [InlineKeyboardButton("ارسال لینک مستقیم", callback_data="manual_link")],
        [InlineKeyboardButton("تاریخچه بارگیری", callback_data="download_history")],
        [InlineKeyboardButton("دریافت پروفایل", callback_data="get_profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "سلام! به ربات دانلود اینستاگرام خوش آمدید.\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=reply_markup
    )

def button_handler(update: Update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id

    if query.data == "get_token":
        token = db.register_user(user_id)
        if token:
            query.edit_message_text(
                f"توکن شما:\n\n`{token}`\n\n"
                "این توکن را در دایرکت [etehadtaskforce](https://www.instagram.com/etehadtaskforce) ارسال کنید.",
                parse_mode="Markdown"
            )
        else:
            query.edit_message_text("خطا در تولید توکن!")

    elif query.data == "instagram_help":
        query.edit_message_text(
            "📱 **راهنمای اتصال به اینستاگرام:**\n\n"
            "1. توکن را از 'دریافت توکن' بگیرید.\n"
            "2. آن را در دایرکت [etehadtaskforce](https://www.instagram.com/etehadtaskforce) ارسال کنید.\n"
            "3. پس از تأیید، پست‌ها و استوری‌ها را Share کنید.",
            parse_mode="Markdown"
        )

    elif query.data == "manual_link":
        query.edit_message_text("لطفاً لینک پست یا استوری را ارسال کنید.")

    elif query.data == "download_history":
        downloads = db.get_user_downloads(user_id)
        if downloads:
            history_text = "📥 **تاریخچه بارگیری:**\n\n" + "\n".join(
                f"{i}. {d['type']} - {datetime.fromtimestamp(d['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}"
                for i, d in enumerate(downloads, 1)
            )
            query.edit_message_text(history_text, parse_mode="Markdown")
        else:
            query.edit_message_text("هنوز بارگیری‌ای انجام نشده.")

    elif query.data == "get_profile":
        query.edit_message_text("لطفاً نام کاربری را با فرمت `@username` ارسال کنید.")
        context.user_data['state'] = 'awaiting_username'

def check_membership(update: Update, context):
    user_id = update.effective_user.id
    not_joined = []
    for channel in REQUIRED_CHANNELS:
        try:
            status = context.bot.get_chat_member(chat_id=channel["chat_id"], user_id=user_id).status
            if status not in ['member', 'administrator', 'creator']:
                not_joined.append(channel)
        except Exception as e:
            logger.error(f"خطا در بررسی عضویت: {str(e)}")
            not_joined.append(channel)
    if not_joined:
        keyboard = [[InlineKeyboardButton(f"عضویت در {c['username']}", url=f"https://t.me/{c['username'][1:]}")] for c in not_joined]
        update.message.reply_text("لطفاً در کانال‌ها عضو شوید:", reply_markup=InlineKeyboardMarkup(keyboard))
        return False
    return True

def process_and_send_post(media_id, chat_id, context):
    retries = 3
    for attempt in range(retries):
        try:
            if not os.path.exists("downloads"):
                os.makedirs("downloads")
            L = instaloader.Instaloader(max_connection_attempts=3)
            if PROXY:
                L.context._session.proxies = {"http": PROXY, "https": PROXY}
            media_info = ig_client.media_info(media_id)
            shortcode = media_info.code
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            L.download_post(post, target="downloads")
            downloaded_files = os.listdir("downloads")

            video_sent = False
            for file in downloaded_files:
                file_path = os.path.join("downloads", file)
                if file.endswith(".mp4") and not video_sent:
                    with open(file_path, 'rb') as f:
                        context.bot.send_video(chat_id=chat_id, video=f, caption="[TaskForce](https://t.me/task_1_4_1_force)", parse_mode="Markdown", timeout=30)
                        video_sent = True
                        db.add_download(chat_id, "ویدیو", time.time())
                    os.remove(file_path)
                elif file.endswith((".jpg", ".jpeg", ".png")):
                    with open(file_path, 'rb') as f:
                        context.bot.send_photo(chat_id=chat_id, photo=f, caption=post.caption or "[TaskForce](https://t.me/task_1_4_1_force)", parse_mode="Markdown", timeout=30)
                        db.add_download(chat_id, "عکس", time.time())
                    os.remove(file_path)
            for file in downloaded_files:
                file_path = os.path.join("downloads", file)
                if os.path.exists(file_path):
                    os.remove(file_path)
            context.bot.send_message(chat_id=chat_id, text="محتوا با موفقیت ارسال شد.")
            break
        except Exception as e:
            logger.error(f"خطا در دانلود (تلاش {attempt + 1}/{retries}): {str(e)}")
            if "401 Unauthorized" in str(e):
                time.sleep(60)
            if attempt == retries - 1:
                context.bot.send_message(chat_id=chat_id, text=f"خطا در دانلود پس از {retries} تلاش: {str(e)}")

def handle_link(update: Update, context):
    chat_id = update.effective_chat.id
    message_text = update.message.text
    if "instagram.com" not in message_text:
        return
    if update.effective_chat.type == "private" and not check_membership(update, context):
        return
    update.message.reply_text("در حال دانلود...")
    try:
        shortcode = re.search(r"(?:/p/|/reel/|/stories/[^/]+/)([^/?]+)", message_text).group(1)
        media_id = ig_client.media_pk_from_code(shortcode)
        threading.Thread(target=process_and_send_post, args=(media_id, chat_id, context)).start()
    except Exception as e:
        logger.error(f"خطا در پردازش لینک: {str(e)}")
        update.message.reply_text(f"خطا در پردازش لینک: {str(e)}")

def check_instagram_dms(context):
    logger.info("شروع چک کردن دایرکت‌ها")
    while True:
        try:
            inbox = ig_client.direct_threads(amount=50)
            logger.info(f"تعداد دایرکت‌ها: {len(inbox)}")
            for thread in inbox:
                for message in thread.messages:
                    if not db.is_message_processed(message.id):
                        sender_id = message.user_id
                        logger.info(f"پیام جدید: نوع: {message.item_type}, از: {sender_id}")
                        db.mark_message_processed(message.id)

                        if message.item_type == "text":
                            text = message.text.strip()
                            logger.info(f"پیام متنی: '{text}'")
                            telegram_id = db.get_telegram_id_by_token(text)
                            if telegram_id:
                                logger.info(f"توکن معتبر: '{text}', telegram_id: {telegram_id}")
                                try:
                                    telegram_user = context.bot.get_chat(telegram_id)
                                    telegram_username = telegram_user.username or str(telegram_id)
                                    ig_client.direct_send(
                                        f"توکن شما تأیید شد. پیج شما به [اکانت تلگرام](https://t.me/{telegram_username}) متصل شد.",
                                        user_ids=[sender_id]
                                    )
                                except Exception as e:
                                    ig_client.direct_send(
                                        "توکن شما تأیید شد. از این پس Share کنید تا دانلود شود.",
                                        user_ids=[sender_id]
                                    )
                                sender_info = ig_client.user_info(sender_id)
                                instagram_username = sender_info.username
                                db.update_instagram_username(telegram_id, instagram_username)
                                context.bot.send_message(
                                    chat_id=telegram_id,
                                    text=f"اکانت شما به [@{instagram_username}](https://www.instagram.com/{instagram_username}) متصل شد.",
                                    parse_mode="Markdown"
                                )
                            else:
                                logger.info(f"توکن نامعتبر: '{text}'")
                                ig_client.direct_send(
                                    "توکن نامعتبر است. با /start در تلگرام توکن جدید بگیرید.",
                                    user_ids=[sender_id]
                                )
                            continue

                        if message.item_type in ["media_share", "clip"]:
                            media_id = message.media_share.id if message.item_type == 'media_share' else message.clip.id
                            sender_info = ig_client.user_info(sender_id)
                            instagram_username = sender_info.username
                            telegram_id = db.get_telegram_id_by_instagram_username(instagram_username)
                            if telegram_id:
                                threading.Thread(target=process_and_send_post, args=(media_id, telegram_id, context)).start()
                                ig_client.direct_send("محتوا در حال پردازش است.", user_ids=[sender_id])
                                context.bot.send_message(chat_id=telegram_id, text="محتوا در حال پردازش است.")
                            else:
                                ig_client.direct_send(
                                    "ابتدا توکن خود را ارسال کنید. با /start در تلگرام توکن بگیرید.",
                                    user_ids=[sender_id]
                                )
        except LoginRequired as e:
            logger.error(f"Session نامعتبر: {str(e)}. تلاش برای ورود مجدد...")
            login_with_session()
        except Exception as e:
            logger.error(f"خطا در چک کردن دایرکت‌ها: {str(e)}")
            time.sleep(60)
        time.sleep(10)

def admin(update: Update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        update.message.reply_text("شما دسترسی به این بخش را ندارید!")
        return
    keyboard = [
        [InlineKeyboardButton("مشاهده کاربران", callback_data="view_users")],
        [InlineKeyboardButton("ارسال پیام همگانی", callback_data="broadcast")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("پنل ادمین:\nلطفاً گزینه مورد نظر را انتخاب کنید:", reply_markup=reply_markup)

def admin_button_handler(update: Update, context):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    if user_id != ADMIN_ID:
        query.edit_message_text("شما دسترسی به این بخش را ندارید!")
        return
    
    if query.data == "view_users":
        users = []
        with open(db.DB_FILE, "r") as f:
            db_data = json.load(f)
        for user_id, data in db_data["users"].items():
            users.append(f"ID: {data['telegram_id']}, Instagram: {data.get('instagram_username', 'N/A')}")
        if users:
            user_list = "\n".join(users)
            query.edit_message_text(f"لیست کاربران:\n{user_list}")
        else:
            query.edit_message_text("هیچ کاربری ثبت نشده است.")
    
    elif query.data == "broadcast":
        query.edit_message_text("لطفاً متن پیام همگانی را ارسال کنید.")
        context.user_data['state'] = 'awaiting_broadcast'

def handle_username(update: Update, context):
    message_text = update.message.text
    if message_text.startswith('@'):
        username = message_text[1:]
        chat_id = update.effective_chat.id
        # اینجا باید تابع process_and_send_profile را اضافه کنید اگر نیاز دارید
        return True
    return False

def main():
    logger.info("Bot is starting...")
    db.initialize_db()
    setup_handlers(dispatcher)
    threading.Thread(target=check_instagram_dms, args=(dispatcher,), daemon=True).start()
    PORT = int(os.environ.get("PORT", 10000))
    WEBHOOK_URL = f"https://insta-zpnb.onrender.com/{TOKEN}"
    updater.bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Starting Flask server on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False)

if __name__ == "__main__":
    main()
