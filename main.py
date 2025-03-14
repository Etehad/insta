import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import re
import requests
from bs4 import BeautifulSoup
import sqlite3
from flask import Flask

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

# تابع خوش‌آمدگویی
def start(update: Update, context):
    print(f"User {update.effective_user.id} started the bot")
    if not check_membership(update, context):
        return

    keyboard = [
        [InlineKeyboardButton("راهنمای استفاده", callback_data="help")],
        [InlineKeyboardButton("پشتیبانی", callback_data="support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
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
            print(f"خطا در بررسی عضویت کاربر {user_id} در کانال {channel['username']}: {str(e)}")
            not_joined_channels.append(channel)

    if not not_joined_channels:
        return True

    keyboard = []
    for channel in not_joined_channels:
        keyboard.append([InlineKeyboardButton(text=f"عضویت در {channel['username']}", url=f"https://t.me/{channel['username'].replace('@', '')}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "برای استفاده از ربات، لطفا در کانال‌های زیر عضو شوید و سپس دوباره امتحان کنید:",
        reply_markup=reply_markup
    )
    return False

# تابع دانلود ویدیو
def download_video(url, update: Update, context):
    try:
        update.message.reply_text("در حال دانلود ویدیو... لطفاً صبر کنید.")
        
        ydl_opts = {
            'format': 'best',
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = f"{info['title']}.{info['ext']}"
            
            # ارسال ویدیو
            with open(video_path, 'rb') as video_file:
                context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=video_file,
                    caption=f"🎥 {info['title']}\n\n[TaskForce](https://t.me/task_1_4_1_force)",
                    parse_mode="Markdown"
                )
            
            # حذف فایل موقت
            os.remove(video_path)
            
    except Exception as e:
        print(f"خطا در دانلود: {str(e)}")
        update.message.reply_text(f"خطا در دانلود ویدیو: {str(e)}")

# تابع پردازش لینک
def handle_link(update: Update, context):
    if not check_membership(update, context):
        return

    url = update.message.text
    print(f"Received URL: {url}")

    # بررسی نوع لینک
    if any(domain in url.lower() for domain in ['instagram.com', 'youtube.com', 'youtu.be', 'tiktok.com', 'facebook.com', 'fb.watch']):
        threading.Thread(target=download_video, args=(url, update, context)).start()
    else:
        update.message.reply_text("لطفاً یک لینک معتبر از اینستاگرام، یوتیوب، تیک تاک یا فیسبوک ارسال کنید.")

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
    print("Bot is starting...")
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # ثبت handlerها
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))

    updater.start_polling()

    # اجرای وب‌سرور Flask برای جلوگیری از خوابیدن
    threading.Thread(target=run_flask, daemon=False).start()

    updater.idle()

if __name__ == "__main__":
    main()
