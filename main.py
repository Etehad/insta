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
    {"chat_id": "-1001860545237", "username": "@task_1_4_1_force"},
    {"chat_id": "-1002301139625", "username": "@kingwor17172"}
]

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

# تابع اصلی
def main():
    logger.info("Bot is starting...")
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # ثبت handlerها
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))

    # اضافه کردن error handler
    dispatcher.add_error_handler(error_handler)

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
