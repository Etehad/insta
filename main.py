import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import RetryAfter, TelegramError
import yt_dlp
import re
import requests
from bs4 import BeautifulSoup
import sqlite3
from flask import Flask
import threading
import time
import instaloader
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, ClientError
import database as db
from api import start_api_server
import logging

# تنظیم لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن ربات تلگرام
TOKEN = os.getenv('TOKEN', '7872003751:AAGK4IHqCqr-8nxxAfj1ImQNpRMlRHRGxxU')

# تنظیمات ادمین
ADMIN_ID = 6473845417

# تنظیم کانال‌های اجباری
REQUIRED_CHANNELS = [
    {"chat_id": "-1001860545237", "username": "@task_1_4_1_force"}
]

# تنظیمات اینستاگرام
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME', 'etehadtaskforce')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD', 'Aa123456*')
SESSION_FILE = "session.json"  # فایل برای ذخیره session

# راه‌اندازی وب‌سرور Flask برای فعال نگه داشتن
app = Flask(__name__)

@app.route('/')
def ping():
    return "Bot is alive!", 200

# تابع برای اجرای وب‌سرور
def run_flask():
    print("Starting Flask server for 24/7 activity...")
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# راه‌اندازی پایگاه داده
db.initialize_db()

# شروع سرور API (اگه لازم داری)
start_api_server()

# ورود به اینستاگرام با instagrapi
ig_client = Client()

def login_with_session():
    try:
        # بارگذاری session اگه وجود داشته باشه
        if os.path.exists(SESSION_FILE):
            print(f"بارگذاری session از {SESSION_FILE}")
            ig_client.load_settings(SESSION_FILE)
            ig_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            print(f"با موفقیت به اینستاگرام ({INSTAGRAM_USERNAME}) با session وارد شد.")
        else:
            print(f"در حال ورود به اینستاگرام با نام کاربری: {INSTAGRAM_USERNAME}")
            ig_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            print(f"با موفقیت به اینستاگرام ({INSTAGRAM_USERNAME}) وارد شد.")
            ig_client.dump_settings(SESSION_FILE)  # ذخیره session بعد از ورود موفق
            print(f"session با موفقیت در {SESSION_FILE} ذخیره شد.")
    except TwoFactorRequired as e:
        print("احراز هویت دو مرحله‌ای مورد نیاز است!")
        try:
            verification_code = input("لطفاً کد تأیید دو مرحله‌ای را وارد کنید: ").strip()
            print(f"کد وارد شده: {verification_code}")
            ig_client.two_factor_login(verification_code)
            print(f"با موفقیت به اینستاگرام ({INSTAGRAM_USERNAME}) وارد شد (با 2FA).")
            ig_client.dump_settings(SESSION_FILE)  # ذخیره session بعد از 2FA
            print(f"session با موفقیت در {SESSION_FILE} ذخیره شد.")
        except Exception as e:
            print(f"خطا در تأیید کد دو مرحله‌ای: {str(e)}")
            raise
    except ClientError as e:
        print(f"خطا در ورود به اینستاگرام: {str(e)}")
        raise
    except Exception as e:
        print(f"خطای غیرمنتظره در ورود: {str(e)}")
        raise

# اجرای فرآیند ورود
try:
    login_with_session()
except Exception as e:
    print(f"ورود به اینستاگرام ناموفق بود: {str(e)}")
    exit(1)

# تابع ارسال پیام با مدیریت خطا
def safe_send_message(context, chat_id, text, **kwargs):
    try:
        return context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
    except RetryAfter as e:
        logger.warning(f"RetryAfter error: {e}")
        time.sleep(e.retry_after)
        return safe_send_message(context, chat_id, text, **kwargs)
    except TelegramError as e:
        logger.error(f"Telegram error: {e}")
        return None

# تابع خوش‌آمدگویی
def start(update: Update, context):
    logger.info(f"User {update.effective_user.id} started the bot")
    if not check_membership(update, context):
        return

    keyboard = [
        [InlineKeyboardButton("راهنمای استفاده", callback_data="help")],
        [InlineKeyboardButton("پشتیبانی", callback_data="support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    safe_send_message(
        context,
        update.effective_chat.id,
        "سلام! به ربات دانلود ویدیو خوش آمدید.\n\n"
        "شما می‌توانید ویدیوهای زیر را دانلود کنید:\n"
        "📱 اینستاگرام\n"
        "🎥 یوتیوب\n"
        "📱 تیک تاک\n"
        "👥 فیسبوک\n\n"
        "لطفاً لینک ویدیوی مورد نظر خود را ارسال کنید.",
        reply_markup=reply_markup
    )

# تابع بررسی عضویت در کانال‌های اجباری
def check_membership(update: Update, context) -> bool:
    user_id = update.effective_user.id
    not_joined_channels = []

    for channel in REQUIRED_CHANNELS:
        try:
            member = context.bot.get_chat_member(chat_id=channel["chat_id"], user_id=user_id)
            status = member.status
            if status not in ['member', 'administrator', 'creator']:
                not_joined_channels.append(channel)
        except Exception as e:
            logger.error(f"خطا در بررسی عضویت کاربر {user_id} در کانال {channel['username']}: {str(e)}")
            not_joined_channels.append(channel)

    if not not_joined_channels:
        return True

    keyboard = []
    for channel in not_joined_channels:
        keyboard.append([InlineKeyboardButton(text=f"عضویت در {channel['username']}", url=f"https://t.me/{channel['username'].replace('@', '')}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    safe_send_message(
        context,
        update.effective_chat.id,
        "برای استفاده از ربات، لطفا در کانال‌های زیر عضو شوید و سپس دوباره امتحان کنید:",
        reply_markup=reply_markup
    )
    return False

# تابع دانلود ویدیو
def download_video(url, update: Update, context):
    try:
        safe_send_message(context, update.effective_chat.id, "در حال دانلود ویدیو... لطفاً صبر کنید.")
        
        ydl_opts = {
            'format': 'best',
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'cookiesfrombrowser': ('chrome',),  # استفاده از کوکی‌های کروم
            'extract_flat': False,
            'force_generic_extractor': False,
            'no_warnings': False,
            'verbose': True,
            'ignoreerrors': True,
            'no_check_certificates': True,
            'prefer_insecure': True,
            'geo_verification_proxy': '',
            'source_address': '0.0.0.0',
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
            'file_access_retries': 10,
            'extractor_retries': 10,
            'retry_sleep': 5,
            'retry_sleep_functions': {'fragment': lambda n: 5 * (n + 1)},
            'skip_unavailable_fragments': True,
            'keep_fragments': False,
            'buffersize': 32768,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            },
            'extractor_args': {
                'instagram': {
                    'username': INSTAGRAM_USERNAME,
                    'password': INSTAGRAM_PASSWORD,
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                if not info:
                    raise Exception("اطلاعات ویدیو استخراج نشد")
                    
                video_path = f"{info.get('title', 'video')}.{info.get('ext', 'mp4')}"
                
                if not os.path.exists(video_path):
                    raise Exception("فایل ویدیو دانلود نشد")
                
                # ارسال ویدیو
                try:
                    with open(video_path, 'rb') as video_file:
                        context.bot.send_video(
                            chat_id=update.effective_chat.id,
                            video=video_file,
                            caption=f"🎥 {info.get('title', 'ویدیو')}\n\n[TaskForce](https://t.me/task_1_4_1_force)",
                            parse_mode="Markdown"
                        )
                except RetryAfter as e:
                    logger.warning(f"RetryAfter error while sending video: {e}")
                    time.sleep(e.retry_after)
                    with open(video_path, 'rb') as video_file:
                        context.bot.send_video(
                            chat_id=update.effective_chat.id,
                            video=video_file,
                            caption=f"🎥 {info.get('title', 'ویدیو')}\n\n[TaskForce](https://t.me/task_1_4_1_force)",
                            parse_mode="Markdown"
                        )
                
                # حذف فایل موقت
                if os.path.exists(video_path):
                    os.remove(video_path)
                    
            except Exception as e:
                logger.error(f"خطا در دانلود: {str(e)}")
                if "login required" in str(e).lower():
                    safe_send_message(
                        context,
                        update.effective_chat.id,
                        "خطا در دسترسی به اینستاگرام. لطفاً دوباره تلاش کنید یا از لینک دیگری استفاده کنید."
                    )
                else:
                    safe_send_message(
                        context,
                        update.effective_chat.id,
                        f"خطا در دانلود ویدیو: {str(e)}"
                    )
            
    except Exception as e:
        logger.error(f"خطای کلی در دانلود: {str(e)}")
        safe_send_message(
            context,
            update.effective_chat.id,
            "خطا در دانلود ویدیو. لطفاً دوباره تلاش کنید."
        )

# تابع پردازش لینک
def handle_link(update: Update, context):
    if not check_membership(update, context):
        return

    url = update.message.text
    logger.info(f"Received URL: {url}")

    # بررسی نوع لینک
    if any(domain in url.lower() for domain in ['instagram.com', 'youtube.com', 'youtu.be', 'tiktok.com', 'facebook.com', 'fb.watch']):
        threading.Thread(target=download_video, args=(url, update, context)).start()
    else:
        safe_send_message(context, update.effective_chat.id, "لطفاً یک لینک معتبر از اینستاگرام، یوتیوب، تیک تاک یا فیسبوک ارسال کنید.")

# مدیریت دکمه‌ها
def button_handler(update: Update, context):
    query = update.callback_query
    query.answer()

    if query.data == "help":
        query.edit_message_text(
            "📱 **راهنمای استفاده از ربات:**\n\n"
            "1. لینک ویدیوی مورد نظر خود را از یکی از شبکه‌های زیر کپی کنید:\n"
            "   - اینستاگرام\n"
            "   - یوتیوب\n"
            "   - تیک تاک\n"
            "   - فیسبوک\n\n"
            "2. لینک را در چت ربات ارسال کنید\n"
            "3. ربات به صورت خودکار ویدیو را دانلود و برای شما ارسال می‌کند\n\n"
            "نکته: برای استفاده از ربات باید در کانال‌های اجباری عضو باشید.",
            parse_mode="Markdown"
        )
    elif query.data == "support":
        query.edit_message_text(
            "برای پشتیبانی با ادمین در ارتباط باشید:\n"
            "@task_1_4_1_force"
        )

# تابع دانلود و ارسال پست
def process_and_send_post(media_id, telegram_id, context):
    try:
        print(f"شروع دانلود برای telegram_id: {telegram_id}, media_id: {media_id}")
        if not os.path.exists("downloads"):
            os.makedirs("downloads")
            print(f"پوشه downloads ایجاد شد.")

        L = instaloader.Instaloader(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            max_connection_attempts=3
        )

        # تبدیل media_id به shortcode
        try:
            media_info = ig_client.media_info(media_id)
            shortcode = media_info.code
            print(f"Shortcode استخراج‌شده: {shortcode}")
        except Exception as e:
            print(f"خطا در دریافت اطلاعات رسانه: {str(e)}")
            context.bot.send_message(chat_id=telegram_id, text=f"خطا در پردازش رسانه: {str(e)}")
            return

        # دانلود پست
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        print(f"دانلود فایل‌ها شروع شد: {post}")

        L.download_post(post, target="downloads")
        downloaded_files = os.listdir("downloads")
        print(f"محتوای دانلود شده: {downloaded_files}")
        if not downloaded_files:
            context.bot.send_message(chat_id=telegram_id, text="هیچ فایلی دانلود نشد!")
            return

        # ارسال ویدیو با لینک قابل کلیک
        video_sent = False
        video_path = None
        for file in downloaded_files:
            file_path = os.path.join("downloads", file)
            if file.endswith(".mp4") and not video_sent:
                video_path = file_path
                try:
                    with open(video_path, 'rb') as f:
                        print(f"ارسال ویدیو: {video_path}, اندازه فایل: {os.path.getsize(video_path)} بایت")
                        context.bot.send_video(
                            chat_id=telegram_id,
                            video=f,
                            caption="[TaskForce](https://t.me/task_1_4_1_force)",
                            parse_mode="Markdown",
                            timeout=30
                        )
                        video_sent = True
                        print(f"ویدیو با موفقیت ارسال شد: {video_path}")
                except Exception as e:
                    print(f"خطا در ارسال ویدیو: {str(e)}")
                    context.bot.send_message(chat_id=telegram_id, text=f"خطا در ارسال ویدیو: {str(e)}")
                if os.path.exists(video_path) and video_sent:
                    os.remove(video_path)
                    print(f"فایل ویدیو حذف شد: {video_path}")

        # ارسال کاور با کپشن پست اینستاگرامی و لینک
        cover_sent = False
        if post.caption and not cover_sent:
            for file in downloaded_files:
                file_path = os.path.join("downloads", file)
                if file.endswith((".jpg", ".jpeg", ".png")) and not cover_sent:
                    try:
                        with open(file_path, 'rb') as f:
                            print(f"ارسال کاور: {file_path}, اندازه فایل: {os.path.getsize(file_path)} بایت")
                            context.bot.send_photo(
                                chat_id=telegram_id,
                                photo=f,
                                caption=f"{post.caption}\n[TaskForce](https://t.me/task_1_4_1_force)",
                                parse_mode="Markdown",
                                timeout=30
                            )
                            cover_sent = True
                            print(f"کاور با موفقیت ارسال شد: {file_path}")
                    except Exception as e:
                        print(f"خطا در ارسال کاور: {str(e)}")
                        context.bot.send_message(chat_id=telegram_id, text=f"خطا در ارسال کاور: {str(e)}")
                    if os.path.exists(file_path) and cover_sent:
                        os.remove(file_path)
                        print(f"فایل کاور حذف شد: {file_path}")
                    break

        # حذف فایل‌های باقیمانده
        for file in downloaded_files:
            file_path = os.path.join("downloads", file)
            if os.path.exists(file_path) and file_path not in [video_path if video_sent else None, file_path if cover_sent else None]:
                os.remove(file_path)
                print(f"فایل اضافی حذف شد: {file_path}")

        if video_sent or cover_sent:
            context.bot.send_message(chat_id=telegram_id, text="محتوای شما با موفقیت ارسال شد.")
        else:
            context.bot.send_message(chat_id=telegram_id, text="هیچ فایلی برای ارسال پیدا نشد!")

    except Exception as e:
        print(f"خطا کلی در دانلود و ارسال: {str(e)}")
        context.bot.send_message(chat_id=telegram_id, text=f"خطا کلی در دانلود: {str(e)}")

# تابع دانلود و ارسال استوری
def process_and_send_story(story_id, telegram_id, context):
    try:
        print(f"شروع دانلود استوری برای telegram_id: {telegram_id}, story_id: {story_id}")
        media = ig_client.story_info(story_id)
        if media:
            video_url = getattr(media, 'video_url', None)
            photo_url = getattr(media, 'thumbnail_url', None)
            if video_url:
                context.bot.send_message(chat_id=telegram_id, text="در حال دانلود استوری...")
                context.bot.send_video(chat_id=telegram_id, video=video_url, caption="استوری شما")
            elif photo_url:
                context.bot.send_message(chat_id=telegram_id, text="در حال دانلود استوری...")
                context.bot.send_photo(chat_id=telegram_id, photo=photo_url, caption="استوری شما")
            else:
                context.bot.send_message(chat_id=telegram_id, text="استوری مورد نظر قابل دانلود نیست.")
        else:
            context.bot.send_message(chat_id=telegram_id, text="استوری مورد نظر پیدا نشد.")
    except Exception as e:
        print(f"خطا در دانلود استوری: {str(e)}")
        context.bot.send_message(chat_id=telegram_id, text=f"خطا در دانلود استوری: {str(e)}")

# تابع چک کردن دایرکت‌ها
def check_instagram_dms(context):
    while True:
        try:
            print("چک کردن دایرکت‌ها...")
            inbox = ig_client.direct_threads(amount=50)
            print(f"تعداد دایرکت‌ها: {len(inbox)}")
            for thread in inbox:
                for message in thread.messages:
                    if not db.is_message_processed(message.id):
                        sender_id = message.user_id
                        print(f"پیام جدید پیدا شد: نوع پیام: {message.item_type}, از کاربر: {sender_id}")
                        db.mark_message_processed(message.id)

                        if message.item_type == "text":
                            text = message.text
                            telegram_id = db.get_telegram_id_by_token(text)
                            if telegram_id:
                                print(f"توکن معتبر پیدا شد: {text}, telegram_id: {telegram_id}")
                                ig_client.direct_send("توکن شما تأیید شد. از این پس هر پست و استوری که در دایرکت Share کنید در تلگرام دریافت می‌کنید.", user_ids=[sender_id])
                                context.bot.send_message(chat_id=telegram_id, text="پیج اینستاگرام شما متصل شد.")
                                sender_info = ig_client.user_info(sender_id)
                                instagram_username = sender_info.username
                                print(f"ثبت instagram_username: {instagram_username} برای telegram_id: {telegram_id}")
                                db.update_instagram_username(telegram_id, instagram_username)
                                continue

                        if message.item_type in ["media_share", "clip"]:
                            print(f"پست/کلیپ Share شده پیدا شد: media_id: {message.media_share.id if message.item_type == 'media_share' else message.clip.id}")
                            sender_info = ig_client.user_info(sender_id)
                            instagram_username = sender_info.username
                            telegram_id = db.get_telegram_id_by_instagram_username(instagram_username)
                            if telegram_id:
                                print(f"کاربر تأیید شده: instagram_username: {instagram_username}, telegram_id: {telegram_id}")
                                media_id = message.media_share.id if message.item_type == 'media_share' else message.clip.id
                                threading.Thread(
                                    target=process_and_send_post,
                                    args=(media_id, telegram_id, context)
                                ).start()
                                ig_client.direct_send("پست/کلیپ Share شده شما دریافت شد و در حال پردازش است.", user_ids=[sender_id])
                            else:
                                print(f"کاربر پیدا نشد: instagram_username: {instagram_username}")

                        if message.item_type == "story_share":
                            print(f"استوری Share شده پیدا شد: story_id: {message.story_share.id}")
                            sender_info = ig_client.user_info(sender_id)
                            instagram_username = sender_info.username
                            telegram_id = db.get_telegram_id_by_instagram_username(instagram_username)
                            if telegram_id:
                                print(f"کاربر تأیید شده: instagram_username: {instagram_username}, telegram_id: {telegram_id}")
                                threading.Thread(
                                    target=process_and_send_story,
                                    args=(message.story_share.id, telegram_id, context)
                                ).start()
                                ig_client.direct_send("استوری Share شده شما دریافت شد و در حال پردازش است.", user_ids=[sender_id])
                            else:
                                print(f"کاربر پیدا نشد: instagram_username: {instagram_username}")

        except Exception as e:
            print(f"خطا در چک کردن دایرکت‌ها: {str(e)}")
        time.sleep(30)

# تابع پنل ادمین
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

# مدیریت دکمه‌های پنل ادمین
def admin_button_handler(update: Update, context):
    query = update.callback_query
    query.answer()

    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        query.edit_message_text("شما دسترسی به این بخش را ندارید!")
        return

    if query.data == "view_users":
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT telegram_id, instagram_username FROM users")
        users = c.fetchall()
        conn.close()
        if users:
            user_list = "\n".join([f"ID: {user[0]}, Instagram: {user[1] or 'N/A'}" for user in users])
            query.edit_message_text(f"لیست کاربران:\n{user_list}")
        else:
            query.edit_message_text("هیچ کاربری ثبت نشده است.")

    elif query.data == "broadcast":
        query.edit_message_text("لطفاً متن پیام همگانی را ارسال کنید.")
        context.user_data['state'] = 'awaiting_broadcast'

# دریافت پیام همگانی
def handle_message(update: Update, context):
    if 'state' in context.user_data and context.user_data['state'] == 'awaiting_broadcast':
        if update.effective_user.id != ADMIN_ID:
            update.message.reply_text("شما دسترسی به این بخش را ندارید!")
            return
        message_text = update.message.text
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT telegram_id FROM users")
        users = c.fetchall()
        conn.close()
        for user in users:
            context.bot.send_message(chat_id=user[0], text=message_text)
        update.message.reply_text("پیام همگانی با موفقیت ارسال شد.")
        del context.user_data['state']

# تابع دیباگ برای تست دریافت پیام
def debug_handler(update: Update, context):
    print(f"Debug: Received any message: {update.message.text}")

# تابع اصلی
def main():
    logger.info("Bot is starting...")
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # ثبت handlerها
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))
    dispatcher.add_handler(CommandHandler("admin", admin))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))
    dispatcher.add_handler(CallbackQueryHandler(admin_button_handler))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(MessageHandler(Filters.all, debug_handler))

    threading.Thread(target=check_instagram_dms, args=(dispatcher,), daemon=True).start()
    updater.start_polling()

    # اجرای وب‌سرور Flask برای جلوگیری از خوابیدن
    threading.Thread(target=run_flask, daemon=False).start()

    updater.idle()

# تابع مدیریت خطا
def error_handler(update: Update, context):
    logger.error(f"Update {update} caused error: {context.error}")
    if update and update.effective_message:
        safe_send_message(
            context,
            update.effective_chat.id,
            "متأسفانه خطایی رخ داد. لطفاً دوباره تلاش کنید."
        )

if __name__ == "__main__":
    main()
