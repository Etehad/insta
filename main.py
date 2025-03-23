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

# تنظیم لاگ با جزئیات بیشتر
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
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

app = Flask(__name__)

@app.route('/')
def keep_alive():
    return "Bot is alive!"

def login_instagram():
    global ig_client
    try:
        if os.path.exists(SESSION_FILE):
            logger.info(f"Loading Instagram session from {SESSION_FILE}")
            ig_client.load_settings(SESSION_FILE)
            ig_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        else:
            logger.info(f"Logging into Instagram as {INSTAGRAM_USERNAME}")
            ig_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            ig_client.dump_settings(SESSION_FILE)
        logger.info(f"Successfully logged into Instagram ({INSTAGRAM_USERNAME})")
    except TwoFactorRequired:
        logger.error("Two-factor authentication required!")
        raise
    except ClientError as e:
        logger.error(f"Instagram login failed: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during Instagram login: {str(e)}")
        raise

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
            query.edit_message_text(f"توکن شما: `{token}`\nاین رو به دایرکت [etehad141](https://instagram.com/etehad141) بفرستید.", parse_mode="Markdown")
        else:
            query.edit_message_text("خطا در تولید توکن!")
    elif query.data == "instagram_help":
        query.edit_message_text("راهنما: توکن رو به [etehad141](https://instagram.com/etehad141) دایرکت کنید.")
    elif query.data == "manual_link":
        query.edit_message_text("لینک پست یا ریل رو بفرستید (مثلاً: https://www.instagram.com/reel/DHTLO0LOYoG/?utm_source=ig_web_copy_link&igsh=MzRlODBiNWFlZA==)")

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

def process_instagram_media(media_id, chat_id, context):
    try:
        logger.info(f"Processing Instagram media for chat_id: {chat_id}, media_id: {media_id}")
        media_info = ig_client.media_info(media_id)
        if media_info.media_type == 2:  # ویدیو یا ریل
            video_url = str(media_info.video_url)
            thumbnail_url = str(media_info.thumbnail_url)
            caption = media_info.caption_text or "بدون کپشن"
            page_id = media_info.user.username  # گرفتن آیدی پیج
            music_name = None
            if hasattr(media_info, 'clips_metadata') and media_info.clips_metadata:
                if 'music_info' in media_info.clips_metadata and media_info.clips_metadata['music_info']:
                    music_name = media_info.clips_metadata['music_info'].get('title', None)
            video_caption = "[TaskForce](https://t.me/task_1_4_1_force)"
            # کپشن کاور با توضیح و آیدی پیج
            cover_caption = (
                f"*کپشن پست:*\n{caption}\n"
                f"آیدی پیج: [{page_id}](https://www.instagram.com/{page_id}/)\n"
                "[TaskForce](https://t.me/task_1_4_1_force)"
            )
            if music_name:
                cover_caption += f"\nآهنگ: {music_name}"
            context.bot.send_video(chat_id=chat_id, video=video_url, caption=video_caption, parse_mode="Markdown")
            context.bot.send_photo(chat_id=chat_id, photo=thumbnail_url, caption=cover_caption, parse_mode="Markdown")
        else:
            context.bot.send_message(chat_id=chat_id, text="فقط پست ها پشتیبانی می‌شن!")
    except Exception as e:
        logger.error(f"Error processing Instagram media: {str(e)}")
        context.bot.send_message(chat_id=chat_id, text=f"خطا در دانلود: {str(e)}")

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
                                threading.Thread(target=process_instagram_media, args=(media_id, telegram_id, context)).start()
        except Exception as e:
            logger.error(f"Error checking Instagram DMs: {str(e)}")
            time.sleep(60)  # در صورت خطا، دوباره تلاش می‌کنه
        time.sleep(30)

def handle_link(update: Update, context):
    if not check_membership(update, context):
        return
    url = update.message.text
    if "instagram.com" not in url:
        if update.message.chat.type != "private":  # در گروه فقط لینک اینستا پردازش بشه
            return
        update.message.reply_text("لطفاً لینک اینستاگرام بفرستید!")
        return
    logger.info(f"Received Instagram link from user {update.effective_user.id} in chat {update.message.chat_id}: {url}")
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
            threading.Thread(target=process_instagram_media, args=(media_id, update.message.chat_id, context)).start()
        else:
            update.message.reply_text("رسانه پیدا نشد!")
    except Exception as e:
        logger.error(f"Error handling link: {str(e)}")
        update.message.reply_text(f"خطا: {str(e)}")

def main():
    logger.info("Starting bot...")
    db.initialize_db()

    # اجرای Flask برای Keep Alive
    flask_thread = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 8080}, daemon=True)
    flask_thread.start()

    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()

    # لاگین اینستاگرام فقط یک بار
    try:
        login_instagram()
    except Exception as e:
        logger.critical(f"Failed to login to Instagram: {str(e)}")
        updater = Updater(TOKEN, use_context=True)
        updater.bot.send_message(ADMIN_ID, f"خطا در لاگین اینستاگرام: {str(e)}")
        return

    updater = Updater(TOKEN, use_context=True)
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
