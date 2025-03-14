import os
import sys
import logging
import time
import re
import threading
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
import youtube_dl
import requests
from instaloader import Instaloader, Post
from flask import Flask

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

# راه‌اندازی Flask برای پینگ
app = Flask(__name__)

@app.route('/')
def ping():
    return "Bot is alive!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

# تابع خوش‌آمدگویی
def start(update: Update, context):
    if not check_membership(update, context):
        return
    update.message.reply_text(
        "سلام! لینک ویدیو رو از اینستاگرام، یوتیوب، تیک‌تاک یا فیسبوک بفرستید تا براتون دانلود کنم."
    )

# تابع بررسی عضویت
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
        update.message.reply_text("لطفاً در کانال‌ها عضو بشید:", reply_markup=InlineKeyboardMarkup(keyboard))
        return False
    return True

# تابع دانلود و ارسال ویدیو (یوتیوب، تیک‌تاک، فیسبوک)
def process_and_send_video(url, chat_id, context):
    ydl_opts = {'format': 'best', 'outtmpl': 'downloads/%(id)s.%(ext)s', 'quiet': True}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        video_url = info['url']
        title = info.get('title', 'بدون عنوان')
        thumbnail_url = info.get('thumbnail')

    # دانلود و ارسال ویدیو
    video_path = f"downloads/{info['id']}.{info['ext']}"
    with requests.get(video_url, stream=True) as r:
        with open(video_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    with open(video_path, 'rb') as f:
        context.bot.send_video(chat_id=chat_id, video=f, caption=f"{title}\n[TaskForce](https://t.me/task_1_4_1_force)", parse_mode="Markdown", timeout=30)
    os.remove(video_path)

    # ارسال کاور
    if thumbnail_url:
        thumbnail_path = f"downloads/{info['id']}_thumbnail.jpg"
        with requests.get(thumbnail_url, stream=True) as r:
            with open(thumbnail_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        with open(thumbnail_path, 'rb') as f:
            context.bot.send_photo(chat_id=chat_id, photo=f, caption=f"کاور ویدیو\n[TaskForce](https://t.me/task_1_4_1_force)", parse_mode="Markdown", timeout=30)
        os.remove(thumbnail_path)

# تابع دانلود و ارسال پست اینستاگرام
def process_and_send_instagram_post(shortcode, chat_id, context):
    L = Instaloader()
    post = Post.from_shortcode(L.context, shortcode)
    L.download_post(post, target="downloads")
    for file in os.listdir("downloads"):
        file_path = os.path.join("downloads", file)
        if file.endswith(".mp4"):
            with open(file_path, 'rb') as f:
                context.bot.send_video(chat_id=chat_id, video=f, caption="[TaskForce](https://t.me/task_1_4_1_force)", parse_mode="Markdown", timeout=30)
        elif file.endswith((".jpg", ".jpeg", ".png")):
            with open(file_path, 'rb') as f:
                context.bot.send_photo(chat_id=chat_id, photo=f, caption=post.caption or "[TaskForce](https://t.me/task_1_4_1_force)", parse_mode="Markdown", timeout=30)
        os.remove(file_path)
        context.bot.send_message(chat_id=chat_id, text="پست اینستاگرام با موفقیت ارسال شد.")

# تابع مدیریت لینک‌ها
def handle_link(update: Update, context):
    chat_id = update.effective_chat.id
    message_text = update.message.text

    if update.effective_chat.type == "private" and not check_membership(update, context):
        return

    update.message.reply_text("در حال پردازش لینک...")
    try:
        if "instagram.com" in message_text:
            shortcode = re.search(r"(?:/p/|/reel/)([^/?]+)", message_text).group(1)
            threading.Thread(target=process_and_send_instagram_post, args=(shortcode, chat_id, context)).start()
        elif "youtube.com" in message_text or "youtu.be" in message_text:
            threading.Thread(target=process_and_send_video, args=(message_text, chat_id, context)).start()
        elif "tiktok.com" in message_text:
            threading.Thread(target=process_and_send_video, args=(message_text, chat_id, context)).start()
        elif "facebook.com" in message_text or "fb.watch" in message_text:
            threading.Thread(target=process_and_send_video, args=(message_text, chat_id, context)).start()
        else:
            update.message.reply_text("این پلتفرم پشتیبانی نمی‌شه.")
    except Exception as e:
        logger.error(f"خطا در پردازش لینک: {str(e)}")
        update.message.reply_text(f"خطا در پردازش لینک: {str(e)}")

# تابع اصلی
def main():
    logger.info("Bot is starting...")
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))

    threading.Thread(target=run_flask, daemon=True).start()
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    main()
