import os
import threading
import time
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, ClientError
import database as db
from api import start_api_server
from flask import Flask

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "7872003751:AAForhz28960IHKBJoZUoymEvDpU_u85JKQ"
INSTAGRAM_USERNAME = "etehad141"
INSTAGRAM_PASSWORD = "Aa123456"
SESSION_FILE = "session.json"
ADMIN_ID = 6473845417

REQUIRED_CHANNELS = [
    {"chat_id": "-1001860545237", "username": "@task_1_4_1_force"}
]

ig_client = Client()
# ig_client.set_proxy("http://103.174.102.223:8080")  # بدون پراکسی

# Flask app برای Keep Alive
app = Flask(__name__)

@app.route('/')
def keep_alive():
    return "Bot is alive!"

def login_with_session(updater=None):
    global ig_client
    while True:
        try:
            if os.path.exists(SESSION_FILE):
                logger.info(f"Loading session from {SESSION_FILE}")
                ig_client.load_settings(SESSION_FILE)
                ig_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            else:
                logger.info(f"Logging into Instagram as {INSTAGRAM_USERNAME}")
                ig_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
                ig_client.dump_settings(SESSION_FILE)
            logger.info(f"Logged into Instagram ({INSTAGRAM_USERNAME})")
            break
        except TwoFactorRequired:
            logger.error("Two-factor authentication required!")
            if updater:
                updater.bot.send_message(ADMIN_ID, "احراز هویت دو مرحله‌ای نیازه!")
            time.sleep(300)
        except ClientError as e:
            logger.error(f"Instagram login failed: {str(e)}")
            if updater:
                updater.bot.send_message(ADMIN_ID, f"خطا در لاگین: {str(e)}")
            time.sleep(300)
            if os.path.exists(SESSION_FILE):
                os.remove(SESSION_FILE)
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
            if updater:
                updater.bot.send_message(ADMIN_ID, f"خطای ناشناخته: {str(e)}. ممکنه پراکسی یا اتصال مشکل داشته باشه.")
            time.sleep(300)
            if os.path.exists(SESSION_FILE):
                os.remove(SESSION_FILE)

def start(update: Update, context):
    logger.info(f"User {update.effective_user.id} started the bot")
    if not check_membership(update, context):
        return
    keyboard = [
        [InlineKeyboardButton("دریافت توکن اتصال به اینستاگرام", callback_data="get_token")],
        [InlineKeyboardButton("راهنمای اتصال به اینستاگرام", callback_data="instagram_help")],
        [InlineKeyboardButton("ارسال لینک مستقیم", callback_data="manual_link")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "سلام! به ربات دانلود اینستاگرام خوش آمدید.\n\n"
        "شما می‌توانید:\n"
        "1️⃣ توکن اتصال به اینستاگرام دریافت کنید\n"
        "2️⃣ یا لینک پست/ریل را مستقیم ارسال کنید\n",
        reply_markup=reply_markup
    )

def button_handler(update: Update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    logger.info(f"Button clicked by user {user_id}: {query.data}")
    if query.data == "get_token":
        token = db.register_user(user_id)
        if token:
            query.edit_message_text(f"توکن شما: `{token}`\nاین رو به دایرکت 'etehad141' بفرستید.", parse_mode="Markdown")
        else:
            query.edit_message_text("خطا در تولید توکن!")
    elif query.data == "instagram_help":
        query.edit_message_text("راهنما: توکن رو به 'etehad141' دایرکت کنید.")
    elif query.data == "manual_link":
        try:
            query.edit_message_text("لینک پست یا ریل رو بفرستید (مثلاً: https://www.instagram.com/reel/xyz/)")
        except Exception as e:
            logger.info(f"Ignoring repeat button press: {str(e)}")

def check_membership(update: Update, context):
    user_id = update.effective_user.id
    not_joined = []
    for channel in REQUIRED_CHANNELS:
        try:
            member = context.bot.get_chat_member(chat_id=channel["chat_id"], user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                not_joined.append(channel)
        except:
            not_joined.append(channel)
    if not not_joined:
        return True
    keyboard = [[InlineKeyboardButton(f"عضویت در {c['username']}", url=f"https://t.me/{c['username'].replace('@', '')}")] for c in not_joined]
    update.message.reply_text("لطفاً در کانال‌ها عضو شوید:", reply_markup=InlineKeyboardMarkup(keyboard))
    return False

def process_and_send_post(media_id, telegram_id, context):
    try:
        logger.info(f"Downloading for telegram_id: {telegram_id}, media_id: {media_id}")
        media_info = ig_client.media_info(media_id)
        if media_info.media_type == 2:  # ویدیو یا ریل
            video_url = str(media_info.video_url)
            thumbnail_url = str(media_info.thumbnail_url)
            caption = media_info.caption_text or "بدون کپشن"
            music_name = None

            # چک کردن نام آهنگ
            if hasattr(media_info, 'clips_metadata') and media_info.clips_metadata:
                if 'music_info' in media_info.clips_metadata and media_info.clips_metadata['music_info']:
                    music_name = media_info.clips_metadata['music_info'].get('title', None)

            # کپشن ویدیو
            video_caption = "[TaskForce](https://t.me/task_1_4_1_force)"

            # کپشن کاور
            cover_caption = f"{caption}\n[TaskForce](https://t.me/task_1_4_1_force)"
            if music_name:
                cover_caption += f"\nآهنگ: {music_name}"

            if video_url:
                # ارسال ویدیو
                context.bot.send_video(
                    chat_id=telegram_id,
                    video=video_url,
                    caption=video_caption,
                    parse_mode="Markdown"
                )
                # ارسال کاور
                context.bot.send_photo(
                    chat_id=telegram_id,
                    photo=thumbnail_url,
                    caption=cover_caption,
                    parse_mode="Markdown"
                )
                context.bot.send_message(chat_id=telegram_id, text="ریل با موفقیت ارسال شد!")
            else:
                context.bot.send_message(chat_id=telegram_id, text="ویدیو پیدا نشد!")
        else:
            context.bot.send_message(chat_id=telegram_id, text="فقط ریل‌ها پشتیبانی می‌شن!")
    except Exception as e:
        logger.error(f"Error in download: {str(e)}")
        context.bot.send_message(chat_id=telegram_id, text=f"خطا در دانلود: {str(e)}. ممکنه پراکسی یا اتصال مشکل داشته باشه.")

def check_instagram_dms(context):
    while True:
        try:
            inbox = ig_client.direct_threads(amount=50)
            for thread in inbox:
                for message in thread.messages:
                    if not db.is_message_processed(message.id):
                        sender_id = message.user_id
                        db.mark_message_processed(message.id)
                        if message.item_type == "text":
                            telegram_id = db.get_telegram_id_by_token(message.text)
                            if telegram_id:
                                ig_client.direct_send("توکن تأیید شد!", user_ids=[sender_id])
                                context.bot.send_message(chat_id=telegram_id, text="پیج شما متصل شد!")
                                sender_info = ig_client.user_info(sender_id)
                                db.update_instagram_username(telegram_id, sender_info.username)
                        elif message.item_type in ["media_share", "clip"]:
                            sender_info = ig_client.user_info(sender_id)
                            telegram_id = db.get_telegram_id_by_instagram_username(sender_info.username)
                            if telegram_id:
                                media_id = message.media_share.id if message.item_type == 'media_share' else message.clip.id
                                threading.Thread(target=process_and_send_post, args=(media_id, telegram_id, context)).start()
        except Exception as e:
            logger.error(f"Error checking DMs: {str(e)}")
            login_with_session(context)
        time.sleep(30)

def handle_link(update: Update, context):
    if not check_membership(update, context):
        return
    url = update.message.text
    logger.info(f"Received link from user {update.effective_user.id}: {url}")
    if "instagram.com" in url:
        update.message.reply_text("در حال دانلود...")
        try:
            parts = url.split("/")
            shortcode = None
            for i, part in enumerate(parts):
                if part in ("p", "reel") and i + 1 < len(parts):
                    shortcode = parts[i + 1].split("?")[0]
                    break
            if not shortcode:
                update.message.reply_text("لینک نامعتبر!")
                return
            media_id = ig_client.media_pk_from_code(shortcode)
            if media_id and media_id != "0":
                threading.Thread(target=process_and_send_post, args=(media_id, update.effective_user.id, context)).start()
                update.message.reply_text("در حال پردازش...")
            else:
                update.message.reply_text("رسانه پیدا نشد!")
        except Exception as e:
            update.message.reply_text(f"خطا: {str(e)}")
    else:
        update.message.reply_text("لطفاً لینک اینستاگرام بفرستید!")

def main():
    logger.info("Starting bot...")
    db.initialize_db()

    # اجرای Flask برای Keep Alive
    flask_thread = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 8080}, daemon=True)
    flask_thread.start()

    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()

    updater = Updater(TOKEN, use_context=True)
    login_thread = threading.Thread(target=login_with_session, args=(updater,), daemon=True)
    login_thread.start()

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))
    dp.add_handler(CallbackQueryHandler(button_handler))

    instagram_thread = threading.Thread(target=check_instagram_dms, args=(dp,), daemon=True)
    instagram_thread.start()

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
