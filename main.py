import os
import sys

# تلاش برای نصب Pillow اگر وجود ندارد
try:
    from PIL import Image
except ImportError:
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow>=8.1.1"])
        print("Pillow با موفقیت نصب شد.")
    except Exception as e:
        print(f"خطا در نصب Pillow: {str(e)}")

# ادامه import های کد
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
import instaloader
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, ClientError
import database as db
import threading
import time
import re
from flask import Flask
from datetime import datetime

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
SESSION_FILE = "session.json"

# راه‌اندازی وب‌سرور Flask برای پینگ
app = Flask(__name__)

@app.route('/')
def ping():
    return "Bot is alive!", 200

# تغییر در تابع run_flask
def run_flask():
    print("Starting Flask server for 24/7 activity...")
    port = int(os.environ.get("PORT", 8080))  # پورت پیش‌فرض Render
    
    # اطمینان از استفاده از پورت متفاوت برای Flask و تلگرام
    if port == int(os.environ.get("PORT", 8443)):
        port = port + 1
    
    app.run(host='0.0.0.0', port=port, debug=False)  # استفاده از پورت محیطی

# راه‌اندازی پایگاه داده
db.initialize_db()
db.restore_database()

# ورود به اینستاگرام
ig_client = Client()

def login_with_session():
    try:
        if os.path.exists(SESSION_FILE):
            print(f"بارگذاری session از {SESSION_FILE}")
            ig_client.load_settings(SESSION_FILE)
            ig_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            print(f"با موفقیت به اینستاگرام ({INSTAGRAM_USERNAME}) با session وارد شد.")
        else:
            print(f"در حال ورود به اینستاگرام با نام کاربری: {INSTAGRAM_USERNAME}")
            ig_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            print(f"با موفقیت به اینستاگرام ({INSTAGRAM_USERNAME}) وارد شد.")
            ig_client.dump_settings(SESSION_FILE)
            print(f"session با موفقیت در {SESSION_FILE} ذخیره شد.")
    except TwoFactorRequired as e:
        print("احراز هویت دو مرحله‌ای مورد نیاز است!")
        two_factor_code = os.getenv('TWO_FACTOR_CODE')
        if two_factor_code:
            print(f"استفاده از کد 2FA از متغیر محیطی: {two_factor_code}")
            ig_client.two_factor_login(two_factor_code)
            print(f"با موفقیت به اینستاگرام ({INSTAGRAM_USERNAME}) وارد شد (با 2FA).")
            ig_client.dump_settings(SESSION_FILE)
            print(f"session با موفقیت در {SESSION_FILE} ذخیره شد.")
        else:
            raise Exception("کد 2FA توی متغیر محیطی تنظیم نشده!")
    except ClientError as e:
        print(f"خطا در ورود به اینستاگرام: {str(e)}")
        raise
    except Exception as e:
        print(f"خطای غیرمنتظره در ورود: {str(e)}")
        raise

try:
    login_with_session()
except Exception as e:
    print(f"ورود به اینستاگرام ناموفق بود: {str(e)}")
    exit(1)

# تابع خوش‌آمدگویی
def start(update: Update, context):
    print(f"User {update.effective_user.id} started the bot")
    if not check_membership(update, context):
        return

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
        "شما می‌توانید:\n"
        "1️⃣ توکن اتصال به اینستاگرام دریافت کنید تا پست‌های شما به صورت خودکار دانلود شود\n"
        "2️⃣ یا به صورت مستقیم لینک پست را ارسال کنید\n"
        "3️⃣ تاریخچه بارگیری خود را مشاهده کنید\n"
        "4️⃣ اطلاعات پروفایل کاربران اینستاگرام را دریافت کنید\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=reply_markup
    )

# مدیریت دکمه‌ها
def button_handler(update: Update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    print(f"Button clicked by user {user_id}: {query.data}")

    if query.data == "get_token":
        token = db.register_user(user_id)
        if token:
            keyboard = [
                [InlineKeyboardButton("راهنمای اتصال به اینستاگرام", callback_data="instagram_help")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(
                f"توکن شما:\n\n`{token}`\n\n"
                "این توکن را در دایرکت اکانت اینستاگرام پیج [etehadtaskforce](https://www.instagram.com/etehadtaskforce) ارسال کنید.\n"
                "پس از اتصال، هر پستی که در دایرکت برای این پیج Share کنید به صورت خودکار برای شما دانلود خواهد شد.\n\n"
                "اگر مشکلی داشتید، از راهنما استفاده کنید!",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            print(f"Token generated for user {user_id}: {token}")
        else:
            query.edit_message_text("خطا در تولید توکن. لطفاً دوباره تلاش کنید یا با ادمین تماس بگیرید.")
            print(f"Error generating token for user {user_id}")

    elif query.data == "instagram_help":
        query.edit_message_text(
            "📱 **راهنمای اتصال به اینستاگرام:**\n\n"
            "1. ابتدا دکمه 'دریافت توکن اتصال به اینستاگرام' را بزنید و توکن خود را دریافت کنید.\n"
            "2. توکن خود را به در دایرکت پیج [etehadtaskforce](https://www.instagram.com/etehadtaskforce) در اینستاگرام ارسال کنید.\n"
            "3. پس از تأیید توسط ربات، پیامی دریافت خواهید کرد.\n"
            "4. حالا می‌توانید پست‌ و استوری اینستاگرام را در دایرکت این پیج Share کنید تا به‌صورت خودکار دانلود شوند.\n\n"
            "برای بازگشت به منو اصلی، دستور /start را ارسال کنید.",
            parse_mode="Markdown"
        )
        print(f"Help message sent to user {user_id}")

    elif query.data == "manual_link":
        query.edit_message_text(
            "لطفاً لینک پست، ریل یا استوری اینستاگرام خود را در چت ارسال کنید.\n"
            "مثال پست: https://www.instagram.com/p/Cabc123/\n"
            "مثال ریل: https://www.instagram.com/reel/Cabc123/\n"
            "مثال استوری: https://www.instagram.com/stories/username/123456789/\n"
            "ربات به‌صورت خودکار لینک را پردازش کرده و محتوا را برای شما ارسال خواهد کرد."
        )
        print(f"Manual link instruction sent to user {user_id}")
        
    elif query.data == "download_history":
        downloads = db.get_user_downloads(user_id)
        if downloads and len(downloads) > 0:
            history_text = "📥 **تاریخچه بارگیری شما:**\n\n"
            for i, download in enumerate(downloads, 1):
                download_time = datetime.fromtimestamp(download["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                history_text += f"{i}. نوع: {download['type']}, زمان: {download_time}\n"
            history_text += f"\n**تعداد کل بارگیری‌ها: {len(downloads)}**"
            
            query.edit_message_text(
                history_text,
                parse_mode="Markdown"
            )
        else:
            query.edit_message_text("شما هنوز هیچ بارگیری‌ای انجام نداده‌اید.")
        print(f"Download history sent to user {user_id}")
        
    elif query.data == "get_profile":
        query.edit_message_text(
            "🔍 **دریافت اطلاعات پروفایل:**\n\n"
            "برای دریافت اطلاعات پروفایل و تصویر پروفایل یک کاربر اینستاگرام،\n"
            "لطفاً نام کاربری آن را با فرمت `@username` ارسال کنید.\n\n"
            "مثال: `@instagram`"
        )
        # Store user state to know they're in profile retrieval mode
        context.user_data['state'] = 'awaiting_username'
        print(f"Profile retrieval instruction sent to user {user_id}")

# تابع بررسی عضویت
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

def periodic_backup(context):
    db.backup_database()

# تابع دانلود و ارسال پست
def process_and_send_post(media_id, chat_id, context):
    try:
        print(f"شروع دانلود برای chat_id: {chat_id}, media_id: {media_id}")
        if not os.path.exists("downloads"):
            os.makedirs("downloads")
            print(f"پوشه downloads ایجاد شد.")

        L = instaloader.Instaloader(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            max_connection_attempts=3
        )

        try:
            media_info = ig_client.media_info(media_id)
            shortcode = media_info.code
            print(f"Shortcode استخراج‌شده: {shortcode}")
        except Exception as e:
            print(f"خطا در دریافت اطلاعات رسانه: {str(e)}")
            context.bot.send_message(chat_id=chat_id, text=f"خطا در پردازش رسانه: {str(e)}")
            return

        post = instaloader.Post.from_shortcode(L.context, shortcode)
        print(f"دانلود فایل‌ها شروع شد: {post}")

        L.download_post(post, target="downloads")
        downloaded_files = os.listdir("downloads")
        print(f"محتوای دانلود شده: {downloaded_files}")
        if not downloaded_files:
            context.bot.send_message(chat_id=chat_id, text="هیچ فایلی دانلود نشد!")
            return

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
                            chat_id=chat_id,  # ارسال به chat_id (گروه یا خصوصی)
                            video=f,
                            caption="[TaskForce](https://t.me/task_1_4_1_force)",
                            parse_mode="Markdown",
                            timeout=30
                        )
                        video_sent = True
                        print(f"ویدیو با موفقیت ارسال شد: {video_path}")
                        
                        # افزودن به تاریخچه دانلود
                        db.add_download(chat_id, "ویدیو", time.time())
                except Exception as e:
                    print(f"خطا در ارسال ویدیو: {str(e)}")
                    context.bot.send_message(chat_id=chat_id, text=f"خطا در ارسال ویدیو: {str(e)}")
                if os.path.exists(video_path) and video_sent:
                    os.remove(video_path)
                    print(f"فایل ویدیو حذف شد: {video_path}")

        cover_sent = False
        if post.caption and not cover_sent:
            for file in downloaded_files:
                file_path = os.path.join("downloads", file)
                if file.endswith((".jpg", ".jpeg", ".png")) and not cover_sent:
                    try:
                        with open(file_path, 'rb') as f:
                            print(f"ارسال کاور: {file_path}, اندازه فایل: {os.path.getsize(file_path)} بایت")
                            context.bot.send_photo(
                                chat_id=chat_id,  # ارسال به chat_id (گروه یا خصوصی)
                                photo=f,
                                caption=f"{post.caption}\n[TaskForce](https://t.me/task_1_4_1_force)",
                                parse_mode="Markdown",
                                timeout=30
                            )
                            cover_sent = True
                            print(f"کاور با موفقیت ارسال شد: {file_path}")
                            
                            # افزودن به تاریخچه دانلود
                            if not video_sent:  # اگر ویدیو ارسال نشده باشد (فقط عکس)
                                db.add_download(chat_id, "عکس", time.time())
                    except Exception as e:
                        print(f"خطا در ارسال کاور: {str(e)}")
                        context.bot.send_message(chat_id=chat_id, text=f"خطا در ارسال کاور: {str(e)}")
                    if os.path.exists(file_path) and cover_sent:
                        os.remove(file_path)
                        print(f"فایل کاور حذف شد: {file_path}")
                    break

        for file in downloaded_files:
            file_path = os.path.join("downloads", file)
            if os.path.exists(file_path) and file_path not in [video_path if video_sent else None, file_path if cover_sent else None]:
                os.remove(file_path)
                print(f"فایل اضافی حذف شد: {file_path}")

        if video_sent or cover_sent:
            context.bot.send_message(chat_id=chat_id, text="محتوای شما با موفقیت ارسال شد.")
        else:
            context.bot.send_message(chat_id=chat_id, text="هیچ فایلی برای ارسال پیدا نشد!")

    except Exception as e:
        print(f"خطا کلی در دانلود و ارسال: {str(e)}")
        context.bot.send_message(chat_id=chat_id, text=f"خطا کلی در دانلود: {str(e)}")

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
                context.bot.send_video(
                    chat_id=telegram_id, 
                    video=video_url, 
                    caption="[TaskForce](https://t.me/task_1_4_1_force)", 
                    parse_mode="Markdown"
                )
                db.add_download(telegram_id, "استوری ویدیویی", time.time())
                print(f"استوری ویدیویی با موفقیت ارسال شد")
            elif photo_url:
                context.bot.send_message(chat_id=telegram_id, text="در حال دانلود استوری...")
                context.bot.send_photo(
                    chat_id=telegram_id, 
                    photo=photo_url, 
                    caption="[TaskForce](https://t.me/task_1_4_1_force)", 
                    parse_mode="Markdown"
                )
                db.add_download(telegram_id, "استوری تصویری", time.time())
                print(f"استوری تصویری با موفقیت ارسال شد")
            else:
                context.bot.send_message(chat_id=telegram_id, text="استوری مورد نظر قابل دانلود نیست.")
        else:
            context.bot.send_message(chat_id=telegram_id, text="استوری مورد نظر پیدا نشد.")
    except Exception as e:
        print(f"خطا در دانلود استوری: {str(e)}")
        context.bot.send_message(chat_id=telegram_id, text=f"خطا در دانلود استوری: {str(e)}")

# تابع دریافت و ارسال پروفایل
def process_and_send_profile(username, chat_id, context):
    try:
        print(f"شروع دریافت پروفایل برای username: {username}, chat_id: {chat_id}")
        # حذف @ اگر وجود داشته باشد
        if username.startswith('@'):
            username = username[1:]
            
        # دریافت اطلاعات پروفایل
        user_info = ig_client.user_info_by_username(username)
        if not user_info:
            context.bot.send_message(chat_id=chat_id, text=f"کاربری با نام کاربری {username} یافت نشد.")
            return
            
        # دریافت عکس پروفایل
        profile_pic_url = user_info.profile_pic_url
        
        # جمع‌آوری اطلاعات
        full_name = user_info.full_name or "نامشخص"
        biography = user_info.biography or "بیوگرافی ندارد"
        follower_count = user_info.follower_count
        following_count = user_info.following_count
        media_count = user_info.media_count
        is_private = "خصوصی" if user_info.is_private else "عمومی"
        
        # ساخت پیام
        profile_info = (
            f"📊 **اطلاعات پروفایل @{username}**\n\n"
            f"👤 **نام:** {full_name}\n"
            f"🔐 **وضعیت حساب:** {is_private}\n"
            f"👥 **دنبال‌کنندگان:** {follower_count:,}\n"
            f"👣 **دنبال‌شده‌ها:** {following_count:,}\n"
            f"📸 **تعداد پست‌ها:** {media_count:,}\n\n"
            f"📝 **بیوگرافی:**\n{biography}"
        )
        
        # ارسال عکس پروفایل و اطلاعات
        context.bot.send_photo(
            chat_id=chat_id,
            photo=profile_pic_url,
            caption=profile_info,
            parse_mode="Markdown"
        )
        
        # افزودن به تاریخچه دانلود
        db.add_download(chat_id, "پروفایل", time.time())
        print(f"پروفایل با موفقیت ارسال شد: {username}")
        
    except Exception as e:
        print(f"خطا در دریافت پروفایل: {str(e)}")
        context.bot.send_message(chat_id=chat_id, text=f"خطا در دریافت پروفایل: {str(e)}")

# تابع استخراج و پردازش استوری از لینک
def handle_story_link(story_url, chat_id, context):
    try:
        print(f"پردازش لینک استوری: {story_url}")
        # الگوی لینک استوری: instagram.com/stories/username/123456789
        pattern = r"instagram\.com/stories/([^/]+)/(\d+)"
        match = re.search(pattern, story_url)
        
        if match:
            username = match.group(1)
            story_id = match.group(2)
            print(f"Username: {username}, Story ID: {story_id}")
            
            # دریافت اطلاعات کاربر
            user_info = ig_client.user_info_by_username(username)
            if not user_info:
                context.bot.send_message(chat_id=chat_id, text=f"کاربری با نام کاربری {username} یافت نشد.")
                return
                
            user_id = user_info.pk
            print(f"User ID: {user_id}")
            
            # تبدیل story_id به media_pk
            story_pk = int(story_id)
            
            # دانلود و ارسال استوری
            process_and_send_story(story_pk, chat_id, context)
            return True
        else:
            return False
    except Exception as e:
        print(f"خطا در پردازش لینک استوری: {str(e)}")
        context.bot.send_message(chat_id=chat_id, text=f"خطا در پردازش لینک استوری: {str(e)}")
        return False

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
                            print(f"پیام متنی دریافت شد: {text}")
                            telegram_id = db.get_telegram_id_by_token(text)
                            if telegram_id:
                                print(f"توکن معتبر پیدا شد: {text}, telegram_id: {telegram_id}")
                                
                                # دریافت اطلاعات تلگرام
                                try:
                                    telegram_user = context.bot.get_chat(telegram_id)
                                    telegram_username = telegram_user.username or str(telegram_id)
                                    
                                    # ارسال پیام به اینستاگرام با لینک به تلگرام
                                    ig_client.direct_send(
                                        f"توکن شما تأیید شد. پیج شما به [اکانت تلگرام](https://t.me/{telegram_username}) شما متصل شد.",
                                        user_ids=[sender_id]
                                    )
                                except Exception as e:
                                    print(f"خطا در دریافت اطلاعات تلگرام: {str(e)}")
                                    ig_client.direct_send(
                                        "توکن شما تأیید شد. از این پس هر پست و استوری که در دایرکت Share کنید در تلگرام دریافت می‌کنید.",
                                        user_ids=[sender_id]
                                    )
                                
                                # ارسال پیام به تلگرام
                                sender_info = ig_client.user_info(sender_id)
                                instagram_username = sender_info.username
                                print(f"ثبت instagram_username: {instagram_username} برای telegram_id: {telegram_id}")
                                db.update_instagram_username(telegram_id, instagram_username)
                                
                                # ارسال پیام به تلگرام با لینک به اینستاگرام
                                context.bot.send_message(
                                    chat_id=telegram_id, 
                                    text=f"اکانت شما به [پیج اینستاگرام](https://www.instagram.com/{instagram_username}) متصل شد.",
                                    parse_mode="Markdown"
                                )
                            else:
                                print(f"توکن نامعتبر: {text}")
                                ig_client.direct_send(
                                    "توکن شما نامعتبر است. لطفاً در تلگرام با دستور /start توکن جدید دریافت کنید و دوباره ارسال کنید.",
                                    user_ids=[sender_id]
                                )
                            continue

                        if message.item_type in ["media_share", "clip"]:
                            print(f"پست/کلیپ Share شده پیدا شد: media_id: {message.media_share.id if message.item_type == 'media_share' else message.clip.id}")
                            sender_info = ig_client.user_info(sender_id)
                            instagram_username = sender_info.username
                            print(f"تلاش برای پیدا کردن telegram_id برای instagram_username: {instagram_username}")
                            telegram_id = db.get_telegram_id_by_instagram_username(instagram_username)
                            if telegram_id:
                                print(f"کاربر تأیید شده: instagram_username: {instagram_username}, telegram_id: {telegram_id}")
                                media_id = message.media_share.id if message.item_type == 'media_share' else message.clip.id
                                threading.Thread(
                                    target=process_and_send_post,
                                    args=(media_id, telegram_id, context)
                                ).start()
                                ig_client.direct_send(
                                    "محتوای شما دریافت و در حال پردازش است.",
                                    user_ids=[sender_id]
                                )
                                # اطلاع به کاربر تلگرام
                                context.bot.send_message(
                                    chat_id=telegram_id, 
                                    text="محتوای شما دریافت و در حال پردازش است."
                                )
                            else:
                                print(f"کاربر پیدا نشد: instagram_username: {instagram_username}")
                                ig_client.direct_send(
                                    "لطفاً ابتدا توکن خود را در دایرکت ارسال کنید تا اکانت شما متصل شود. برای دریافت توکن، در تلگرام دستور /start را ارسال کنید.",
                                    user_ids=[sender_id]
                                )

                        if message.item_type == "story_share":
                            print(f"استوری Share شده پیدا شد: story_id: {message.story_share.id}")
                            sender_info = ig_client.user_info(sender_id)
                            instagram_username = sender_info.username
                            print(f"تلاش برای پیدا کردن telegram_id برای instagram_username: {instagram_username}")
                            telegram_id = db.get_telegram_id_by_instagram_username(instagram_username)
                            if telegram_id:
                                print(f"کاربر تأیید شده: instagram_username: {instagram_username}, telegram_id: {telegram_id}")
                                threading.Thread(
                                    target=process_and_send_story,
                                    args=(message.story_share.id, telegram_id, context)
                                ).start()
                                ig_client.direct_send(
                                    "محتوای شما دریافت و در حال پردازش است.",
                                    user_ids=[sender_id]
                                )
                                # اطلاع به کاربر تلگرام
                                context.bot.send_message(
                                    chat_id=telegram_id, 
                                    text="محتوای شما دریافت و در حال پردازش است."
                                )
                            else:
                                print(f"کاربر پیدا نشد: instagram_username: {instagram_username}")
                                ig_client.direct_send(
                                    "لطفاً ابتدا توکن خود را در دایرکت ارسال کنید تا اکانت شما متصل شود. برای دریافت توکن، در تلگرام دستور /start را ارسال کنید.",
                                    user_ids=[sender_id]
                                )

        except Exception as e:
            print(f"خطا در چک کردن دایرکت‌ها: {str(e)}")
        time.sleep(10)  # چک کردن هر 10 ثانیه
        
# تابع دریافت لینک مستقیم
def handle_link(update: Update, context):
    chat_id = update.effective_chat.id  # دریافت chat_id (گروه یا خصوصی)
    user_id = update.effective_user.id  # دریافت user_id فقط برای چک عضویت در چت خصوصی
    message_text = update.message.text

    # فقط لینک‌های اینستاگرام رو پردازش کن
    if "instagram.com" in message_text:
        print(f"Received Instagram URL in chat {chat_id}: {message_text}")

        # اگر چت خصوصی باشه، عضویت رو چک کن
        if update.effective_chat.type == "private" and not check_membership(update, context):
            return

        update.message.reply_text("در حال دانلود... لطفاً منتظر بمانید!")
        try:
            if "/p/" in message_text:
                shortcode = message_text.split("/p/")[1].split("/")[0]
            elif "/reel/" in message_text:
                shortcode = message_text.split("/reel/")[1].split("/")[0]
            else:
                parts = message_text.strip('/').split('/')
                shortcode = parts[-1] if parts[-1] else parts[-2]
            if "?" in shortcode:
                shortcode = shortcode.split("?")[0]
            print(f"Extracted Shortcode: {shortcode}")

            media_id = ig_client.media_pk_from_code(shortcode)
            print(f"Extracted Media ID: {media_id}")

            # ارسال محتوا به chat_id (گروه یا خصوصی)
            threading.Thread(
                target=process_and_send_post,
                args=(media_id, chat_id, context)  # استفاده از chat_id
            ).start()
            update.message.reply_text("پست شما دریافت شد و در حال پردازش است.")

        except Exception as e:
            print(f"Error processing link: {str(e)}")
            update.message.reply_text(f"خطا در پردازش لینک: {str(e)}")
    else:
        print(f"Ignored message in chat {chat_id}: {message_text}")
        return

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

# مدیریت دکمه‌های ادمین
def admin_button_handler(update: Update, context):
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    if user_id != ADMIN_ID:
        query.edit_message_text("شما دسترسی به این بخش را ندارید!")
        return
    
    if query.data == "view_users":
        users = []
        for key in db.keys():
            if key.startswith("user_"):
                user_data = db[key]
                users.append(f"ID: {user_data['telegram_id']}, Instagram: {user_data.get('instagram_username', 'N/A')}")
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
        username = message_text.strip()
        chat_id = update.effective_chat.id
        print(f"Processing username request: {username} from user {chat_id}")
        process_and_send_profile(username, chat_id, context)
        return True
    return False

# دریافت پیام همگانی
def handle_message(update: Update, context):
    if 'state' in context.user_data and context.user_data['state'] == 'awaiting_broadcast':
        if update.effective_user.id != ADMIN_ID:
            update.message.reply_text("شما دسترسی به این بخش را ندارید!")
            return
        message_text = update.message.text
        sent_count = 0
        for key in db.keys():
            if key.startswith("user_"):
                user_data = db[key]
                telegram_id = user_data["telegram_id"]
                try:
                    context.bot.send_message(chat_id=telegram_id, text=message_text)
                    sent_count += 1
                except Exception as e:
                    continue
        update.message.reply_text(f"پیام همگانی با موفقیت به {sent_count} کاربر ارسال شد.")
        context.user_data.clear()  # پاک کردن حالت

# تابع دیباگ
def debug_handler(update: Update, context):
    print(f"Debug: Received any message: {update.message.text}")

# تغییر در تابع main
def main():
    print("Bot is starting...")
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    job_queue = updater.job_queue
    job_queue.run_repeating(periodic_backup, interval=3600, first=300)
    # هندلرها
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.regex(r'^@[\w.]+$'), handle_username))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))  # فقط پیام‌های متنی
    dispatcher.add_handler(CommandHandler("admin", admin))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))
    dispatcher.add_handler(CallbackQueryHandler(admin_button_handler))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    threading.Thread(target=check_instagram_dms, args=(updater.dispatcher,), daemon=True).start()
    
    # اجرای Flask در ترد جداگانه
    threading.Thread(target=run_flask, daemon=True).start()
    
    # استفاده از start_webhook به جای start_polling برای جلوگیری از تداخل
    PORT = int(os.environ.get("PORT", 8443))
    
    updater.start_polling(drop_pending_updates=True)
    print("Bot started with polling")
    
    updater.idle()

if __name__ == "__main__":
    main()
