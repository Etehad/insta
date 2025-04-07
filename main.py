import os
import threading
import time
import logging
import requests
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, ClientError
import database as db
from api import start_api_server
from flask import Flask
import re

# تنظیم لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

TOKEN = "7872003751:AAForhz28960IHKBJoZUoymEvDpU_u85JKQ"
INSTAGRAM_USERNAME = "etehad141"
INSTAGRAM_PASSWORD = "Aa123456"
SESSION_FILE = "session.json"
ADMIN_IDS = [6473845417, 1516721587]

REQUIRED_CHANNELS = [
    {"chat_id": "-1001860545237", "username": "@task_1_4_1_force"}
]

GROUP_CHAT_IDS = ["-1002294804720"]

ig_client = Client()
ig_client.delay_range = [1, 3]

app = Flask(__name__)

@app.route('/')
def keep_alive():
    return "Bot is alive!"

def login_instagram():
    global ig_client
    max_attempts = 3
    for attempt in range(max_attempts):
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
            return True
        except TwoFactorRequired:
            logger.error("Two-factor authentication required!")
            raise
        except ClientError as e:
            logger.error(f"Instagram login failed: {str(e)}")
            if attempt < max_attempts - 1:
                time.sleep(5)
                continue
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Instagram login: {str(e)}")
            raise
    return False

def start(update: Update, context):
    logger.info(f"User {update.effective_user.id} started the bot")
    db.register_user(update.effective_user.id, update.effective_user.username)
    if not check_membership(update, context):
        return
    keyboard = [
        [InlineKeyboardButton("ارسال لینک مستقیم", callback_data="manual_link")],
        [InlineKeyboardButton("دریافت پروفایل و استوری", callback_data="get_profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "سلام! به ربات دانلود اینستاگرام خوش آمدید.\n\n"
        "شما می‌توانید:\n"
        "1️⃣ لینک پست/ریل/استوری را مستقیم ارسال کنید\n"
        "2️⃣ پروفایل و استوری پیج‌ها را دریافت کنید\n",
        reply_markup=reply_markup
    )

def admin(update: Update, context):
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("شما دسترسی به این دستور ندارید!")
        return
    if update.message.chat.type != "private":
        update.message.reply_text("این دستور فقط در چت خصوصی قابل استفاده است!")
        return
    users = db.get_all_users()
    user_list = "\n".join([f"ID: {u[0]}, Username: @{u[3] or 'ندارد'}, Token: {u[1]}, Instagram: {u[2] or 'ندارد'}" for u in users])
    keyboard = [
        [InlineKeyboardButton("ارسال پیام خصوصی (/pv)", callback_data="admin_private")],
        [InlineKeyboardButton("ارسال پیام جمعی (/broadcast)", callback_data="admin_broadcast")],
        [InlineKeyboardButton("ارسال پیام به گروه‌ها (/gap)", callback_data="admin_group")],
        [InlineKeyboardButton("مدیریت کانال‌ها (/set)", callback_data="admin_channels")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(f"کاربران ربات:\n{user_list}\n\nانتخاب کنید:", reply_markup=reply_markup)

def broadcast(update: Update, context):
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("شما دسترسی به این دستور ندارید!")
        return
    if update.message.chat.type != "private":
        update.message.reply_text("این دستور فقط در چت خصوصی قابل استفاده است!")
        return
    if not context.args:
        update.message.reply_text("لطفاً پیام مورد نظر را بعد از دستور وارد کنید! مثال: /broadcast سلام")
        return
    
    message = " ".join(context.args)
    users = db.get_all_users()
    for user in users:
        try:
            user_id = user[0]
            context.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error sending broadcast to user {user_id}: {str(e)}")
    for group_id in GROUP_CHAT_IDS:
        try:
            context.bot.send_message(chat_id=group_id, text=message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error sending broadcast to group {group_id}: {str(e)}")
    update.message.reply_text(f"پیام '{message}' به همه کاربران و گروه‌ها ارسال شد!")

def gap(update: Update, context):
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("شما دسترسی به این دستور ندارید!")
        return
    if update.message.chat.type != "private":
        update.message.reply_text("این دستور فقط در چت خصوصی قابل استفاده است!")
        return
    if not context.args:
        update.message.reply_text("لطفاً پیام مورد نظر را بعد از دستور وارد کنید! مثال: /gap سلام")
        return
    
    message = " ".join(context.args)
    for group_id in GROUP_CHAT_IDS:
        try:
            context.bot.send_message(chat_id=group_id, text=message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error sending message to group {group_id}: {str(e)}")
    update.message.reply_text(f"پیام '{message}' به همه گروه‌ها ارسال شد!")

def pv(update: Update, context):
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("شما دسترسی به این دستور ندارید!")
        return
    if update.message.chat.type != "private":
        update.message.reply_text("این دستور فقط در چت خصوصی قابل استفاده است!")
        return
    if len(context.args) < 2:
        update.message.reply_text("لطفاً آیدی کاربر و پیام را وارد کنید! مثال: /pv 12345 سلام چطوری؟")
        return
    
    try:
        user_id = int(context.args[0])
        message = " ".join(context.args[1:])
        context.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
        update.message.reply_text(f"پیام به {user_id} ارسال شد!")
    except Exception as e:
        update.message.reply_text(f"خطا در ارسال پیام: {str(e)}")

def set_channel(update: Update, context):
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("شما دسترسی به این دستور ندارید!")
        return
    if update.message.chat.type != "private":
        update.message.reply_text("این دستور فقط در چت خصوصی قابل استفاده است!")
        return
    if not context.args:
        update.message.reply_text("لطفاً دستور را به درستی وارد کنید!\n"
                                 "اضافه کردن: /set add chat_id username\n"
                                 "حذف کردن: /set remove username\n"
                                 "مثال: /set add -100123456789 @channel")
        return
    
    action = context.args[0].lower()
    if action == "add" and len(context.args) == 3:
        chat_id = context.args[1]
        username = context.args[2]
        REQUIRED_CHANNELS.append({"chat_id": chat_id, "username": username})
        update.message.reply_text(f"کانال {username} اضافه شد!")
    elif action == "remove" and len(context.args) == 2:
        username = context.args[1]
        REQUIRED_CHANNELS[:] = [c for c in REQUIRED_CHANNELS if c["username"] != username]
        update.message.reply_text(f"کانال {username} حذف شد!")
    else:
        update.message.reply_text("فرمت اشتباه! استفاده:\n"
                                 "/set add chat_id username\n"
                                 "/set remove username")

def button_handler(update: Update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    logger.info(f"Button clicked by user {user_id}: {query.data}")
    
    if query.data == "manual_link":
        query.edit_message_text("لینک پست یا ریل رو بفرستید (مثلاً: https://www.instagram.com/reel/xyz/)")
    elif query.data == "get_profile":
        query.edit_message_text("برای دریافت پروفایل و استوری‌های پیج موردنظر، نام کاربری او را به صورت 'پیج نام‌کاربری' ارسال کنید (مثلاً: پیج instagram)")
    elif query.data.startswith("get_caption_"):
        media_id = query.data.split("get_caption_")[1]
        chat_id = query.message.chat_id
        threading.Thread(target=send_caption_and_cover, args=(media_id, chat_id, context)).start()
    elif query.data.startswith("get_comments_"):
        media_id = query.data.split("get_comments_")[1]
        chat_id = query.message.chat_id
        threading.Thread(target=send_first_10_comments, args=(media_id, chat_id, context)).start()
    elif query.data.startswith("download_song_"):  # تغییر نام دکمه
        media_id = query.data.split("download_song_")[1]
        chat_id = query.message.chat_id
        threading.Thread(target=send_to_beatjoo, args=(media_id, chat_id, context)).start()
    elif query.data == "admin_private":
        query.edit_message_text("برای ارسال پیام خصوصی از دستور /pv استفاده کنید. مثال: /pv 12345 سلام چطوری؟")
    elif query.data == "admin_broadcast":
        query.edit_message_text("برای ارسال پیام همگانی از دستور /broadcast استفاده کنید. مثال: /broadcast سلام")
    elif query.data == "admin_group":
        query.edit_message_text("برای ارسال پیام به گروه‌ها از دستور /gap استفاده کنید. مثال: /gap سلام")
    elif query.data == "admin_channels":
        query.edit_message_text("برای مدیریت کانال‌ها از دستور /set استفاده کنید.\n"
                               "اضافه کردن: /set add chat_id username\n"
                               "حذف کردن: /set remove username")
    elif query.data.startswith("download_stories_"):
        username = query.data.split("download_stories_")[1]
        chat_id = query.message.chat_id
        threading.Thread(target=download_instagram_stories, args=(username, chat_id, context)).start()
    elif query.data.startswith("track_profile_"):
        username = query.data.split("track_profile_")[1]
        chat_id = query.message.chat_id
        threading.Thread(target=process_instagram_profile, args=(username, chat_id, context)).start()
    elif query.data.startswith("get_last_post_"):
        username = query.data.split("get_last_post_")[1]
        chat_id = query.message.chat_id
        threading.Thread(target=download_last_post, args=(username, chat_id, context)).start()

def check_membership(update: Update, context):
    user_id = update.effective_user.id
    if user_id in ADMIN_IDS:
        return True
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
            keyboard = [
                [InlineKeyboardButton("دریافت کاور و کپشن", callback_data=f"get_caption_{media_id}")],
                [InlineKeyboardButton("دریافت آهنگ", callback_data=f"download_song_{media_id}")],  # تغییر نام دکمه
                [InlineKeyboardButton("دریافت 10 کامنت اول", callback_data=f"get_comments_{media_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_video(chat_id=chat_id, video=video_url, caption="[TaskForce](https://t.me/task_1_4_1_force)", parse_mode="Markdown", reply_markup=reply_markup)
        elif media_info.media_type == 1:  # عکس
            photo_url = str(media_info.thumbnail_url)
            keyboard = [
                [InlineKeyboardButton("دریافت کاور و کپشن", callback_data=f"get_caption_{media_id}")],
                [InlineKeyboardButton("دریافت آهنگ", callback_data=f"download_song_{media_id}")],  # تغییر نام دکمه
                [InlineKeyboardButton("دریافت 10 کامنت اول", callback_data=f"get_comments_{media_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_photo(chat_id=chat_id, photo=photo_url, caption="[TaskForce](https://t.me/task_1_4_1_force)", parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error processing Instagram media: {str(e)}")
        context.bot.send_message(chat_id=chat_id, text=f"خطا در دانلود: {str(e)}")

def send_caption_and_cover(media_id, chat_id, context):
    try:
        media_info = ig_client.media_info(media_id)
        thumbnail_url = str(media_info.thumbnail_url)
        caption = media_info.caption_text or "بدون کپشن"
        page_id = media_info.user.username
        cover_caption = (
            f"*کپشن خود پست اینستاگرام:*\n{caption}\n"
            f"آیدی پیج: [{page_id}](https://www.instagram.com/{page_id}/)\n"
            "[TaskForce](https://t.me/task_1_4_1_force)"
        )
        context.bot.send_photo(chat_id=chat_id, photo=thumbnail_url, caption=cover_caption, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error sending caption and cover: {str(e)}")
        context.bot.send_message(chat_id=chat_id, text=f"خطا در ارسال کاور و کپشن: {str(e)}")

def send_first_10_comments(media_id, chat_id, context):
    try:
        logger.info(f"Fetching first 10 comments for media_id: {media_id}")
        comments = ig_client.media_comments(media_id, amount=10)
        if not comments:
            context.bot.send_message(chat_id=chat_id, text="هیچ کامنتی برای این پست وجود ندارد!")
            return
        
        def sanitize_text(text):
            text = text.replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]')
            return text[:1000] if len(text) > 1000 else text

        comment_text = "*10 کامنت اول:*\n"
        for i, comment in enumerate(comments[:10], 1):
            username = comment.user.username
            text = sanitize_text(comment.text)
            comment_text += f"{i}. [{username}](https://www.instagram.com/{username}/): {text}\n"
        comment_text += "[TaskForce](https://t.me/task_1_4_1_force)"

        try:
            context.bot.send_message(
                chat_id=chat_id,
                text=comment_text,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        except Exception as markdown_error:
            logger.warning(f"Markdown parsing failed: {str(markdown_error)}. Retrying without parse_mode.")
            context.bot.send_message(
                chat_id=chat_id,
                text=comment_text,
                disable_web_page_preview=True
            )
    except Exception as e:
        logger.error(f"Error fetching comments: {str(e)}")
        context.bot.send_message(chat_id=chat_id, text=f"خطا در دریافت کامنت‌ها: {str(e)}")

def send_to_beatjoo(media_id, chat_id, context):
    try:
        # دریافت اطلاعات رسانه
        media_info = ig_client.media_info(media_id)
        media_url = f"https://www.instagram.com/p/{media_info.code}/"  # لینک پست
        
        # ارسال پیام به کاربر
        context.bot.send_message(chat_id=chat_id, text="در حال دانلود آهنگ از پست...")

        # ارسال درخواست به وب‌سایت دانلود (مثلاً reelsave.app)
        download_url = "https://reelsave.app/api/instagram/audio"  # آدرس API وب‌سایت (ممکن است نیاز به تغییر داشته باشد)
        payload = {"url": media_url}
        headers = {"User-Agent": "Mozilla/5.0"}
        
        response = requests.post(download_url, data=payload, headers=headers)
        if response.status_code != 200:
            raise Exception("خطا در اتصال به وب‌سایت دانلود")
        
        data = response.json()
        if "audio_url" not in data:
            raise Exception("لینک دانلود آهنگ پیدا نشد")
        
        audio_url = data["audio_url"]
        audio_response = requests.get(audio_url)
        
        if audio_response.status_code != 200:
            raise Exception("خطا در دانلود فایل آهنگ")
        
        # نام آهنگ (اگر در دسترس باشد، در غیر این صورت از کد پست استفاده می‌کنیم)
        song_name = media_info.caption_text[:50] if media_info.caption_text else f"song_{media_info.code}"
        song_filename = f"{song_name}.mp3"
        
        # ذخیره موقت فایل
        with open(song_filename, "wb") as f:
            f.write(audio_response.content)
        
        # ارسال فایل آهنگ به کاربر
        with open(song_filename, "rb") as audio_file:
            context.bot.send_audio(
                chat_id=chat_id,
                audio=audio_file,
                title=song_name,
                caption="*TaskForce*",
                parse_mode="Markdown"
            )
        
        # حذف فایل موقت
        os.remove(song_filename)
        logger.info(f"Song {song_name} downloaded and sent to chat_id {chat_id}")

    except Exception as e:
        logger.error(f"Error in downloading song: {str(e)}")
        context.bot.send_message(chat_id=chat_id, text=f"خطا در دانلود آهنگ: {str(e)}")

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
            f"*دنبال کنندگان:* {followers}\n"
            f"*دنبال شوندگان:* {following}\n"
            f"*تعداد پست‌ها:* {posts}\n"
            f"*وضعیت پیج:* {is_private}\n"
            f"*تعداد استوری‌ها:* {story_count}\n"
            "[TaskForce](https://t.me/task_1_4_1_force)"
        )
        keyboard = [
            [InlineKeyboardButton("دریافت استوری‌ها", callback_data=f"download_stories_{username}")],
            [InlineKeyboardButton("دریافت پست آخر", callback_data=f"get_last_post_{username}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_photo(chat_id=chat_id, photo=profile_pic_url, caption=profile_caption, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error processing Instagram profile: {str(e)}")
        context.bot.send_message(chat_id=chat_id, text=f"خطا در پردازش پروفایل: {str(e)}")

def download_last_post(username, chat_id, context):
    try:
        logger.info(f"Downloading last post for username: {username}, chat_id: {chat_id}")
        user_info = ig_client.user_info_by_username(username)
        user_id = user_info.pk
        medias = ig_client.user_medias(user_id, amount=1)
        if not medias:
            context.bot.send_message(chat_id=chat_id, text=f"پستی برای {username} پیدا نشد!")
            return
        media = medias[0]
        keyboard = [
            [InlineKeyboardButton("دریافت کاور و کپشن", callback_data=f"get_caption_{media.pk}")],
            [InlineKeyboardButton("دریافت 10 کامنت اول", callback_data=f"get_comments_{media.pk}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if media.media_type == 1:
            media_url = str(media.thumbnail_url)
            media_caption = "[TaskForce](https://t.me/task_1_4_1_force)"
            context.bot.send_photo(chat_id=chat_id, photo=media_url, caption=media_caption, parse_mode="Markdown", reply_markup=reply_markup)
        elif media.media_type == 2:
            media_url = str(media.video_url)
            media_caption = "[TaskForce](https://t.me/task_1_4_1_force)"
            context.bot.send_video(chat_id=chat_id, video=media_url, caption=media_caption, parse_mode="Markdown", reply_markup=reply_markup)
        context.bot.send_message(chat_id=chat_id, text=f"پست آخر {username} ارسال شد!")
    except Exception as e:
        logger.error(f"Error downloading last post: {str(e)}")
        context.bot.send_message(chat_id=chat_id, text=f"خطا در دانلود پست آخر: {str(e)}")

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

def process_instagram_story_link(url, chat_id, context):
    try:
        logger.info(f"Processing Instagram story link: {url}")
        story_pk = ig_client.story_pk_from_url(url)
        story_info = ig_client.story_info(story_pk)
        username = story_info.user.username
        if story_info.media_type == 1:
            story_url = str(story_info.thumbnail_url)
            story_caption = f"استوری از [{username}](https://www.instagram.com/{username}/)\n[TaskForce](https://t.me/task_1_4_1_force)"
            context.bot.send_photo(chat_id=chat_id, photo=story_url, caption=story_caption, parse_mode="Markdown")
        elif story_info.media_type == 2:
            story_url = str(story_info.video_url)
            story_caption = f"استوری از [{username}](https://www.instagram.com/{username}/)\n[TaskForce](https://t.me/task_1_4_1_force)"
            context.bot.send_video(chat_id=chat_id, video=story_url, caption=story_caption, parse_mode="Markdown")
        context.bot.send_message(chat_id=chat_id, text="استوری با موفقیت ارسال شد!")
    except Exception as e:
        logger.error(f"Error processing Instagram story link: {str(e)}")
        context.bot.send_message(chat_id=chat_id, text=f"خطا در پردازش استوری: {str(e)}")

def track_follower(page1, page2, chat_id, context):
    try:
        logger.info(f"Tracking if {page1} follows {page2}")
        user1_info = ig_client.user_info_by_username(page1)
        user2_info = ig_client.user_info_by_username(page2)
        user1_id = user1_info.pk
        user2_id = user2_info.pk
        
        is_following = ig_client.user_following(user1_id, amount=0).get(str(user2_id)) is not None
        
        response = f"{page1}، {page2} را دنبال می‌کند" if is_following else f"{page1}، {page2} را دنبال نمی‌کند"
        keyboard = [
            [InlineKeyboardButton(f"اطلاعات {page1}", callback_data=f"track_profile_{page1}"),
             InlineKeyboardButton(f"اطلاعات {page2}", callback_data=f"track_profile_{page2}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id=chat_id, text=response, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error tracking follower: {str(e)}")
        context.bot.send_message(chat_id=chat_id, text=f"خطا در ردیابی: {str(e)}")

def search_instagram(query, chat_id, context):
    try:
        logger.info(f"Searching Instagram for query: {query}")
        results = ig_client.search_users(query)[:10]
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

def handle_link(update: Update, context):
    if not check_membership(update, context):
        return
    text = update.message.text
    chat_id = update.message.chat_id
    
    if text.startswith("جستجو "):
        query = text[6:].strip()
        threading.Thread(target=search_instagram, args=(query, chat_id, context)).start()
        return
    
    if text.startswith("پیج "):
        username = text[4:].strip()
        logger.info(f"Received Instagram profile request from user {update.effective_user.id} in chat {chat_id}: {username}")
        update.message.reply_text(f"در حال پردازش پروفایل {username}...")
        threading.Thread(target=process_instagram_profile, args=(username, chat_id, context)).start()
        return
    
    if text.startswith("ردیابی "):
        parts = text[7:].strip().split(" - ")
        if len(parts) == 2:
            page1, page2 = parts[0].strip(), parts[1].strip()
            logger.info(f"Tracking if {page1} follows {page2} from user {update.effective_user.id} in chat {chat_id}")
            update.message.reply_text(f"در حال ردیابی {page1} و {page2}...")
            threading.Thread(target=track_follower, args=(page1, page2, chat_id, context)).start()
        else:
            update.message.reply_text("لطفاً دو نام کاربری را به صورت 'ردیابی page1 - page2' وارد کنید!")
        return
    
    if "instagram.com" in text:
        logger.info(f"Received Instagram link from user {update.effective_user.id} in chat {chat_id}: {text}")
        update.message.reply_text("در حال دانلود...")
        try:
            if "/stories/" in text:
                threading.Thread(target=process_instagram_story_link, args=(text, chat_id, context)).start()
            else:
                parts = text.split("/")
                shortcode = None
                for i, part in enumerate(parts):
                    if part in ("p", "reel") and i + 1 < len(parts):
                        shortcode = parts[i + 1].split("?")[0]
                        break
                if not shortcode and "share/reel" in text:
                    for i, part in enumerate(parts):
                        if part == "share" and i + 2 < len(parts) and parts[i + 1] == "reel":
                            shortcode = parts[i + 2].split("?")[0]
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
        return
    
    if update.message.chat.type != "private":
        return
    update.message.reply_text("لطفاً لینک اینستاگرام یا دستور 'پیج نام‌کاربری' یا 'جستجو عبارت' یا 'ردیابی page1 - page2' بفرستید!")

def handle_admin_message(update: Update, context):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if update.message.chat.type != "private":
        return
    
    text = update.message.text or ""
    if not text:
        update.message.reply_text("لطفاً از دستورات /pv، /broadcast، /gap یا /set استفاده کنید!")
        return
    update.message.reply_text("لطفاً از دستورات /pv، /broadcast، /gap یا /set استفاده کنید!")

def main():
    logger.info("Starting bot...")
    db.initialize_db()

    flask_thread = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': int(os.getenv('PORT', 8080))}, daemon=True)
    flask_thread.start()

    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()

    try:
        if not login_instagram():
            logger.critical("Failed to login to Instagram initially!")
            updater = Updater(TOKEN, use_context=True)
            updater.bot.send_message(ADMIN_IDS[0], "خطا در لاگین اولیه اینستاگرام!")
            return
    except Exception as e:
        logger.critical(f"Failed to login to Instagram: {str(e)}")
        updater = Updater(TOKEN, use_context=True)
        updater.bot.send_message(ADMIN_IDS[0], f"خطا در لاگین اینستاگرام: {str(e)}")
        return

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("admin", admin))
    dp.add_handler(CommandHandler("broadcast", broadcast))
    dp.add_handler(CommandHandler("gap", gap))
    dp.add_handler(CommandHandler("pv", pv))
    dp.add_handler(CommandHandler("set", set_channel))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))
    dp.add_handler(MessageHandler(Filters.text, handle_admin_message))
    dp.add_handler(CallbackQueryHandler(button_handler))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
