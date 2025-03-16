import os
import threading
import time
import sqlite3
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
import instaloader
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, ClientError
import database as db
from api import start_api_server

# تنظیم لاگ برای دیباگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# توکن ربات تلگرام
TOKEN = '7872003751:AAForhz28960IHKBJoZUoymEvDpU_u85JKQ'

# تنظیمات ادمین
ADMIN_ID = 6473845417

# تنظیم کانال‌های اجباری
REQUIRED_CHANNELS = [
    {"chat_id": "-1001860545237", "username": "@task_1_4_1_force"}
]

# تنظیمات اینستاگرام
INSTAGRAM_USERNAME = "etehadtaskforce"
INSTAGRAM_PASSWORD = "Aa123456"
SESSION_FILE = "session.json"

# راه‌اندازی دیتابیس
db.initialize_db()

# ورود به اینستاگرام با instagrapi
ig_client = Client()

def login_with_session(updater=None):
    try:
        if os.path.exists(SESSION_FILE):
            logger.info(f"Loading session from {SESSION_FILE}")
            ig_client.load_settings(SESSION_FILE)
            ig_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            logger.info(f"Logged into Instagram ({INSTAGRAM_USERNAME}) with session")
        else:
            logger.info(f"Logging into Instagram as {INSTAGRAM_USERNAME}")
            ig_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            ig_client.dump_settings(SESSION_FILE)
            logger.info(f"Session saved to {SESSION_FILE}")
    except TwoFactorRequired:
        logger.error("Two-factor authentication required!")
        if updater:
            updater.bot.send_message(ADMIN_ID, "احراز هویت دو مرحله‌ای نیازه! لطفاً کد 2FA رو بفرستید.")
            # اینجا باید یه سیستم برای دریافت کد از ادمین بذارید (در ادامه توضیح می‌دم)
        raise Exception("2FA required - manual intervention needed")
    except ClientError as e:
        logger.error(f"Instagram login error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected login error: {str(e)}")
        raise

# تابع خوش‌آمدگویی
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
        "1️⃣ توکن اتصال به اینستاگرام دریافت کنید تا پست‌های شما به صورت خودکار دانلود شود\n"
        "2️⃣ یا به صورت مستقیم لینک پست را ارسال کنید\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=reply_markup
    )

# مدیریت دکمه‌ها
def button_handler(update: Update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    logger.info(f"Button clicked by user {user_id}: {query.data}")

    if query.data == "get_token":
        token = db.register_user(user_id)
        if token:
            keyboard = [
                [InlineKeyboardButton("راهنمای اتصال به اینستاگرام", callback_data="instagram_help")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(
                f"توکن شما:\n\n`{token}`\n\n"
                "این توکن را در دایرکت اکانت اینستاگرام خود به پیج 'etehadtaskforce' ارسال کنید.\n"
                "پس از اتصال، هر پستی که در دایرکت برای این پیج Share کنید به صورت خودکار برای شما دانلود خواهد شد.\n\n"
                "اگر مشکلی داشتید، از راهنما استفاده کنید!",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            logger.info(f"Token generated for user {user_id}: {token}")
        else:
            query.edit_message_text("خطا در تولید توکن. لطفاً دوباره تلاش کنید یا با ادمین تماس بگیرید.")
            logger.error(f"Error generating token for user {user_id}")

    elif query.data == "instagram_help":
        query.edit_message_text(
            "📱 **راهنمای اتصال به اینستاگرام:**\n\n"
            "1. ابتدا دکمه 'دریافت توکن اتصال به اینستاگرام' را بزنید و توکن خود را دریافت کنید.\n"
            "2. به اینستاگرام بروید و به پیج 'etehadtaskforce' پیام دهید.\n"
            "3. توکن خود را در دایرکت ارسال کنید.\n"
            "4. پس از تأیید توسط ربات، پیامی دریافت خواهید کرد.\n"
            "5. حالا می‌توانید پست‌های اینستاگرام را در دایرکت این پیج Share کنید تا به‌صورت خودکار دانلود شوند.\n\n"
            "برای بازگشت به منو اصلی، دستور /start را ارسال کنید.",
            parse_mode="Markdown"
        )
        logger.info(f"Help message sent to user {user_id}")

    elif query.data == "manual_link":
        query.edit_message_text(
            "لطفاً لینک پست یا ریل اینستاگرام خود را در چت ارسال کنید.\n"
            "مثال: https://www.instagram.com/p/Cabc123/\n"
            "ربات به‌صورت خودکار لینک را پردازش کرده و محتوا را برای شما ارسال خواهد کرد."
        )
        logger.info(f"Manual link instruction sent to user {user_id}")

# بررسی عضویت در کانال‌ها
def check_membership(update: Update, context) -> bool:
    user_id = update.effective_user.id
    not_joined_channels = []

    for channel in REQUIRED_CHANNELS:
        try:
            member = context.bot.get_chat_member(chat_id=channel["chat_id"], user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                not_joined_channels.append(channel)
        except Exception as e:
            logger.error(f"Error checking membership for user {user_id} in {channel['username']}: {str(e)}")
            not_joined_channels.append(channel)

    if not not_joined_channels:
        return True

    keyboard = [[InlineKeyboardButton(f"عضویت در {channel['username']}", url=f"https://t.me/{channel['username'].replace('@', '')}")] for channel in not_joined_channels]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("برای استفاده از ربات، لطفاً در کانال‌های زیر عضو شوید:", reply_markup=reply_markup)
    return False

# دانلود و ارسال پست
def process_and_send_post(media_id, telegram_id, context):
    try:
        logger.info(f"Starting download for telegram_id: {telegram_id}, media_id: {media_id}")
        if not os.path.exists("downloads"):
            os.makedirs("downloads")

        L = instaloader.Instaloader(max_connection_attempts=3)
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
                    context.bot.send_video(
                        chat_id=telegram_id,
                        video=f,
                        caption="[TaskForce](https://t.me/task_1_4_1_force)",
                        parse_mode="Markdown",
                        timeout=30
                    )
                    video_sent = True
                os.remove(file_path)

        cover_sent = False
        if post.caption and not cover_sent:
            for file in downloaded_files:
                file_path = os.path.join("downloads", file)
                if file.endswith((".jpg", ".jpeg", ".png")) and not cover_sent:
                    with open(file_path, 'rb') as f:
                        context.bot.send_photo(
                            chat_id=telegram_id,
                            photo=f,
                            caption=f"{post.caption}\n[TaskForce](https://t.me/task_1_4_1_force)",
                            parse_mode="Markdown",
                            timeout=30
                        )
                        cover_sent = True
                    os.remove(file_path)
                    break

        for file in downloaded_files:
            file_path = os.path.join("downloads", file)
            if os.path.exists(file_path):
                os.remove(file_path)

        if video_sent or cover_sent:
            context.bot.send_message(chat_id=telegram_id, text="محتوای شما با موفقیت ارسال شد.")
        else:
            context.bot.send_message(chat_id=telegram_id, text="هیچ فایلی برای ارسال پیدا نشد!")

    except Exception as e:
        logger.error(f"Error in download/send: {str(e)}")
        context.bot.send_message(chat_id=telegram_id, text=f"خطا در دانلود: {str(e)}")

# دانلود و ارسال استوری
def process_and_send_story(story_id, telegram_id, context):
    try:
        media = ig_client.story_info(story_id)
        if media:
            video_url = getattr(media, 'video_url', None)
            photo_url = getattr(media, 'thumbnail_url', None)
            if video_url:
                context.bot.send_video(chat_id=telegram_id, video=video_url, caption="استوری شما")
            elif photo_url:
                context.bot.send_photo(chat_id=telegram_id, photo=photo_url, caption="استوری شما")
            else:
                context.bot.send_message(chat_id=telegram_id, text="استوری قابل دانلود نیست.")
        else:
            context.bot.send_message(chat_id=telegram_id, text="استوری پیدا نشد.")
    except Exception as e:
        logger.error(f"Error downloading story: {str(e)}")
        context.bot.send_message(chat_id=telegram_id, text=f"خطا در دانلود استوری: {str(e)}")

# چک کردن دایرکت‌های اینستاگرام
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
                            text = message.text
                            telegram_id = db.get_telegram_id_by_token(text)
                            if telegram_id:
                                ig_client.direct_send("توکن شما تأیید شد.", user_ids=[sender_id])
                                context.bot.send_message(chat_id=telegram_id, text="پیج اینستاگرام شما متصل شد.")
                                sender_info = ig_client.user_info(sender_id)
                                db.update_instagram_username(telegram_id, sender_info.username)

                        elif message.item_type in ["media_share", "clip"]:
                            sender_info = ig_client.user_info(sender_id)
                            telegram_id = db.get_telegram_id_by_instagram_username(sender_info.username)
                            if telegram_id:
                                media_id = message.media_share.id if message.item_type == 'media_share' else message.clip.id
                                threading.Thread(target=process_and_send_post, args=(media_id, telegram_id, context)).start()
                                ig_client.direct_send("پست/کلیپ شما در حال پردازش است.", user_ids=[sender_id])

                        elif message.item_type == "story_share":
                            sender_info = ig_client.user_info(sender_id)
                            telegram_id = db.get_telegram_id_by_instagram_username(sender_info.username)
                            if telegram_id:
                                threading.Thread(target=process_and_send_story, args=(message.story_share.id, telegram_id, context)).start()
                                ig_client.direct_send("استوری شما در حال پردازش است.", user_ids=[sender_id])

        except Exception as e:
            logger.error(f"Error checking DMs: {str(e)}")
        time.sleep(30)

# دریافت لینک مستقیم
def handle_link(update: Update, context):
    if not check_membership(update, context):
        return

    url = update.message.text
    if "instagram.com" in url:
        update.message.reply_text("در حال دانلود...")
        try:
            shortcode = url.split("/")[-2] if url.endswith('/') else url.split("/")[-1].split("?")[0]
            media_id = ig_client.media_pk_from_code(shortcode)
            telegram_id = update.effective_user.id
            threading.Thread(target=process_and_send_post, args=(media_id, telegram_id, context)).start()
            update.message.reply_text("پست شما در حال پردازش است.")
        except Exception as e:
            logger.error(f"Error processing link: {str(e)}")
            update.message.reply_text(f"خطا در پردازش لینک: {str(e)}")
    else:
        update.message.reply_text("لطفاً لینک معتبر اینستاگرام بفرستید.")

# پنل ادمین
def admin(update: Update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        update.message.reply_text("شما دسترسی ندارید!")
        return

    keyboard = [
        [InlineKeyboardButton("مشاهده کاربران", callback_data="view_users")],
        [InlineKeyboardButton("ارسال پیام همگانی", callback_data="broadcast")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("پنل ادمین:", reply_markup=reply_markup)

def admin_button_handler(update: Update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        query.edit_message_text("شما دسترسی ندارید!")
        return

    if query.data == "view_users":
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT telegram_id, instagram_username FROM users")
        users = c.fetchall()
        conn.close()
        user_list = "\n".join([f"ID: {user[0]}, Instagram: {user[1] or 'N/A'}" for user in users]) if users else "کاربری ثبت نشده."
        query.edit_message_text(f"لیست کاربران:\n{user_list}")

    elif query.data == "broadcast":
        query.edit_message_text("لطفاً متن پیام همگانی رو بفرستید.")
        context.user_data['state'] = 'awaiting_broadcast'

def handle_message(update: Update, context):
    if context.user_data.get('state') == 'awaiting_broadcast' and update.effective_user.id == ADMIN_ID:
        message_text = update.message.text
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT telegram_id FROM users")
        users = c.fetchall()
        conn.close()
        for user in users:
            context.bot.send_message(chat_id=user[0], text=message_text)
        update.message.reply_text("پیام همگانی ارسال شد.")
        del context.user_data['state']

# تابع اصلی
def main():
    logger.info("Starting bot...")

    # شروع سرور API
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()

    # ورود به اینستاگرام
    try:
        login_with_session()
    except Exception as e:
        logger.error(f"Instagram login failed: {str(e)}")
        return

    # راه‌اندازی ربات تلگرام
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # ثبت handlerها
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))
    dispatcher.add_handler(CommandHandler("admin", admin))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))
    dispatcher.add_handler(CallbackQueryHandler(admin_button_handler))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # شروع چک کردن دایرکت‌ها
    instagram_thread = threading.Thread(target=check_instagram_dms, args=(dispatcher,), daemon=True)
    instagram_thread.start()

    # حلقه پایداری
    while True:
        try:
            updater.start_polling()
            updater.idle()
        except Exception as e:
            logger.error(f"Bot crashed: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    main()
