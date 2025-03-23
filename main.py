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
        [InlineKeyboardButton("ارسال لینک مستقیم", callback_data="manual_link")],
        [InlineKeyboardButton("دریافت پروفایل و استوری", callback_data="get_profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "سلام! به ربات دانلود اینستاگرام خوش آمدید.\n\n"
        "شما می‌توانید:\n"
        "1️⃣ توکن اتصال به اینستاگرام دریافت کنید\n"
        "2️⃣ یا لینک پست/ریل را مستقیم ارسال کنید\n"
        "3️⃣ پروفایل و استوری پیج‌ها را دریافت کنید\n",
        reply_markup=reply_markup
    )

def admin(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("شما دسترسی به این دستور ندارید!")
        return
    users = db.get_all_users()
    user_list = "\n".join([f"ID: {u[0]}, Token: {u[1]}, Instagram: {u[2] or 'ندارد'}" for u in users])
    keyboard = [
        [InlineKeyboardButton("ارسال پیام خصوصی", callback_data="admin_private")],
        [InlineKeyboardButton("ارسال پیام جمعی", callback_data="admin_broadcast")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(f"کاربران ربات:\n{user_list}\n\nانتخاب کنید:", reply_markup=reply_markup)

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
        video_url = "https://t.me/gghffgdydyr/2"
        caption = "پیج: [etehad141](https://www.instagram.com/etehad141/)"
        context.bot.send_video(chat_id=user_id, video=video_url, caption=caption, parse_mode="Markdown")
        query.edit_message_text("ویدیو راهنما برای شما ارسال شد!")
    elif query.data == "manual_link":
        query.edit_message_text("لینک پست یا ریل رو بفرستید (مثلاً: https://www.instagram.com/reel/xyz/)")
    elif query.data == "get_profile":
        query.edit_message_text("برای دریافت پروفایل و استوری‌های پیجی، نام کاربری او را به صورت 'پیج نام‌کاربری' ارسال کنید (مثلاً: پیج instagram)")
    elif query.data.startswith("get_caption_"):
        media_id = query.data.split("get_caption_")[1]
        chat_id = query.message.chat_id
        threading.Thread(target=send_caption_and_cover, args=(media_id, chat_id, context)).start()
    elif query.data == "admin_private":
        query.edit_message_text("آیدی کاربر (عددی) و پیام خود را به صورت 'آیدی:متن' بفرستید (مثلاً: 12345:سلام چطوری؟)")
    elif query.data == "admin_broadcast":
        query.edit_message_text("پیام خود را بفرستید تا به همه کاربران ارسال شود (می‌توانید عکس یا ویدیو هم بفرستید)")

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
            keyboard = [[InlineKeyboardButton("دریافت کاور و کپشن", callback_data=f"get_caption_{media_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_video(chat_id=chat_id, video=video_url, caption="[TaskForce](https://t.me/task_1_4_1_force)", parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error processing Instagram media: {str(e)}")
        context.bot.send_message(chat_id=chat_id, text=f"خطا در دانلود: {str(e)}")

def send_caption_and_cover(media_id, chat_id, context):
    try:
        media_info = ig_client.media_info(media_id)
        thumbnail_url = str(media_info.thumbnail_url)
        caption = media_info.caption_text or "بدون کپشن"
        page_id = media_info.user.username
        music_name = None
        if hasattr(media_info, 'clips_metadata') and media_info.clips_metadata:
            if 'music_info' in media_info.clips_metadata and media_info.clips_metadata['music_info']:
                music_name = media_info.clips_metadata['music_info'].get('title', None)
        cover_caption = (
            f"*کپشن خود پست اینستاگرام:*\n{caption}\n"
            f"آیدی پیج: [{page_id}](https://www.instagram.com/{page_id}/)\n"
            "[TaskForce](https://t.me/task_1_4_1_force)"
        )
        if music_name:
            cover_caption += f"\nآهنگ: {music_name}"
        context.bot.send_photo(chat_id=chat_id, photo=thumbnail_url, caption=cover_caption, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error sending caption and cover: {str(e)}")
        context.bot.send_message(chat_id=chat_id, text=f"خطا در ارسال کاور و کپشن: {str(e)}")

def process_instagram_profile(username, chat_id, context):
    try:
        logger.info(f"Processing Instagram profile for username: {username}, chat_id: {chat_id}")
        user_info = ig_client.user_info_by_username(username)
        profile_pic_url = str(user_info.profile_pic_url_hd)
        full_name = user_info.full_name or username
        followers = user_info.follower_count
        following = user_info.following_count
        posts = user_info.media_count
        is_private = "خصوصی" if user_info.is_private else "عمومی"
        user_id = user_info.pk
        stories = ig_client.user_stories(user_id)
        story_count = len(stories)
        
        profile_caption = (
            f"*نام پیج:* {full_name}\n"
            f"*آیدی:* [{username}](https://www.instagram.com/{username}/)\n"
            f"*فالوئرها:* {followers}\n"
            f"*فالوئینگ‌ها:* {following}\n"
            f"*تعداد پست‌ها:* {posts}\n"
            f"*وضعیت پیج:* {is_private}\n"
            f"*تعداد استوری‌ها:* {story_count}\n"
            "[TaskForce](https://t.me/task_1_4_1_force)"
        )
        keyboard = [[InlineKeyboardButton("دانلود استوری‌ها", callback_data=f"download_stories_{username}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_photo(chat_id=chat_id, photo=profile_pic_url, caption=profile_caption, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error processing Instagram profile: {str(e)}")
        context.bot.send_message(chat_id=chat_id, text=f"خطا در پردازش پروفایل: {str(e)}")

def download_instagram_stories(username, chat_id, context):
    try:
        logger.info(f"Downloading stories for username: {username}, chat_id: {chat_id}")
        user_info = ig_client.user_info_by_username(username)
        user_id = user_info.pk
        stories = ig_client.user_stories(user_id)
        if not stories:
            context.bot.send_message(chat_id=chat_id, text=f"استوری فعالی برای {username} پیدا نشد!")
            return
        for story in stories:
            if story.media_type == 1:
                story_url = str(story.thumbnail_url)
                story_caption = f"استوری از [{username}](https://www.instagram.com/{username}/)\n[TaskForce](https://t.me/task_1_4_1_force)"
                context.bot.send_photo(chat_id=chat_id, photo=story_url, caption=story_caption, parse_mode="Markdown")
            elif story.media_type == 2:
                story_url = str(story.video_url)
                story_caption = f"استوری از [{username}](https://www.instagram.com/{username}/)\n[TaskForce](https://t.me/task_1_4_1_force)"
                context.bot.send_video(chat_id=chat_id, video=story_url, caption=story_caption, parse_mode="Markdown")
        context.bot.send_message(chat_id=chat_id, text=f"استوری‌های {username} با موفقیت ارسال شدند!")
    except Exception as e:
        logger.error(f"Error downloading Instagram stories: {str(e)}")
        context.bot.send_message(chat_id=chat_id, text=f"خطا در دانلود استوری‌ها: {str(e)}")

def search_instagram(query, chat_id, context):
    try:
        logger.info(f"Searching Instagram for query: {query}")
        results = ig_client.search_users(query)[:5]  # 5 اکانت اول
        if not results:
            context.bot.send_message(chat_id=chat_id, text="نتیجه‌ای پیدا نشد!")
            return
        response = "نتایج جستجو:\n"
        for user in results:
            username = user.username
            full_name = user.full_name or "بدون نام"
            response += f"[{username}](https://www.instagram.com/{username}/) - {full_name}\n"
        context.bot.send_message(chat_id=chat_id, text=response, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Error searching Instagram: {str(e)}")
        context.bot.send_message(chat_id=chat_id, text=f"خطا در جستجو: {str(e)}")

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
            time.sleep(60)
        time.sleep(30)

def handle_link(update: Update, context):
    if not check_membership(update, context):
        return
    text = update.message.text
    chat_id = update.message.chat_id
    
    # بررسی دستور جستجو
    if text.startswith("جستجو "):
        query = text[6:].strip()
        threading.Thread(target=search_instagram, args=(query, chat_id, context)).start()
        return
    
    # بررسی پروفایل با فرمت "پیج username"
    if text.startswith("پیج "):
        username = text[4:].strip()
        logger.info(f"Received Instagram profile request from user {update.effective_user.id} in chat {chat_id}: {username}")
        update.message.reply_text(f"در حال پردازش پروفایل {username}...")
        threading.Thread(target=process_instagram_profile, args=(username, chat_id, context)).start()
        return
    
    # بررسی لینک اینستاگرام
    if "instagram.com" not in text:
        if update.message.chat.type != "private":
            return
        update.message.reply_text("لطفاً لینک اینستاگرام یا دستور 'پیج نام‌کاربری' یا 'جستجو عبارت' بفرستید!")
        return
    
    logger.info(f"Received Instagram link from user {update.effective_user.id} in chat {chat_id}: {text}")
    update.message.reply_text("در حال دانلود...")
    try:
        parts = text.split("/")
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
            threading.Thread(target=process_instagram_media, args=(media_id, chat_id, context)).start()
        else:
            update.message.reply_text("رسانه پیدا نشد!")
    except Exception as e:
        logger.error(f"Error handling link: {str(e)}")
        update.message.reply_text(f"خطا: {str(e)}")

def handle_admin_message(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    text = update.message.text
    if text and ":" in text:
        # پیام خصوصی
        user_id, message = text.split(":", 1)
        try:
            user_id = int(user_id.strip())
            if update.message.photo:
                context.bot.send_photo(chat_id=user_id, photo=update.message.photo[-1].file_id, caption=message, parse_mode="Markdown")
            elif update.message.video:
                context.bot.send_video(chat_id=user_id, video=update.message.video.file_id, caption=message, parse_mode="Markdown")
            else:
                context.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
            update.message.reply_text(f"پیام به {user_id} ارسال شد!")
        except Exception as e:
            update.message.reply_text(f"خطا در ارسال پیام: {str(e)}")
    else:
        # پیام جمعی
        users = db.get_all_users()
        for user in users:
            try:
                user_id = user[0]
                if update.message.photo:
                    context.bot.send_photo(chat_id=user_id, photo=update.message.photo[-1].file_id, caption=text, parse_mode="Markdown")
                elif update.message.video:
                    context.bot.send_video(chat_id=user_id, video=update.message.video.file_id, caption=text, parse_mode="Markdown")
                else:
                    context.bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Error sending broadcast to {user_id}: {str(e)}")
        update.message.reply_text("پیام به همه کاربران ارسال شد!")

def main():
    logger.info("Starting bot...")
    db.initialize_db()

    flask_thread = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 8080}, daemon=True)
    flask_thread.start()

    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()

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
    dp.add_handler(CommandHandler("admin", admin))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))
    dp.add_handler(MessageHandler(Filters.photo | Filters.video | Filters.text, handle_admin_message))
    dp.add_handler(CallbackQueryHandler(button_handler))

    instagram_thread = threading.Thread(target=check_instagram_dms, args=(dp,), daemon=True)
    instagram_thread.start()

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
