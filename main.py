import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
import instaloader
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, ClientError
import database as db
from api import start_api_server
import threading
import time
import sqlite3
from flask import Flask

# توکن ربات تلگرام
TOKEN = os.environ.get('TOKEN', '7872003751:AAGK4IHqCqr-8nxxAfj1ImQNpRMlRHRGxxU')

# تنظیمات ادمین
ADMIN_ID = int(os.environ.get('ADMIN_ID', '6473845417'))

# تنظیم کانال‌های اجباری
REQUIRED_CHANNELS = [
    {'chat_id': '-1001860545237', 'username': '@task_1_4_1_force'}
]


# تنظیمات اینستاگرام
INSTAGRAM_USERNAME = os.environ.get('INSTAGRAM_USERNAME', 'etehadtaskforce')
INSTAGRAM_PASSWORD = os.environ.get('INSTAGRAM_PASSWORD', 'Aa123456*')
SESSION_FILE = 'session.json'  # فایل برای ذخیره session

# راه‌اندازی وب‌سرور Flask برای فعال نگه داشتن
app = Flask(__name__)

@app.route('/')
def ping():
    return 'Bot is alive!', 200

@app.route('/health')
def health():
    return 'OK', 200

# تابع برای اجرای وب‌سرور با حلقه فعال
def run_flask():
    print('Starting Flask server for 24/7 activity...')
    # استفاده از پورت متفاوت برای Flask
    flask_port = int(os.environ.get('FLASK_PORT', 8080))
    app.run(host='0.0.0.0', port=flask_port)

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
            print(f'بارگذاری session از {SESSION_FILE}')
            ig_client.load_settings(SESSION_FILE)
            ig_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            print(f'با موفقیت به اینستاگرام ({INSTAGRAM_USERNAME}) با session وارد شد.')
        else:
            print(f'در حال ورود به اینستاگرام با نام کاربری: {INSTAGRAM_USERNAME}')
            ig_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            print(f'با موفقیت به اینستاگرام ({INSTAGRAM_USERNAME}) وارد شد.')
            ig_client.dump_settings(SESSION_FILE)  # ذخیره session بعد از ورود موفق
            print(f'session با موفقیت در {SESSION_FILE} ذخیره شد.')
    except TwoFactorRequired as e:
        print('احراز هویت دو مرحله‌ای مورد نیاز است!')
        try:
            verification_code = input('لطفاً کد تأیید دو مرحله‌ای را وارد کنید: ').strip()
            print(f'کد وارد شده: {verification_code}')
            ig_client.two_factor_login(verification_code)
            print(f'با موفقیت به اینستاگرام ({INSTAGRAM_USERNAME}) وارد شد (با 2FA).')
            ig_client.dump_settings(SESSION_FILE)  # ذخیره session بعد از 2FA
            print(f'session با موفقیت در {SESSION_FILE} ذخیره شد.')
        except Exception as e:
            print(f'خطا در تأیید کد دو مرحله‌ای: {str(e)}')
            raise
    except ClientError as e:
        print(f'خطا در ورود به اینستاگرام: {str(e)}')
        raise
    except Exception as e:
        print(f'خطای غیرمنتظره در ورود: {str(e)}')
        raise


# اجرای فرآیند ورود
try:
    login_with_session()
except Exception as e:
    print(f'ورود به اینستاگرام ناموفق بود: {str(e)}')
    # در محیط render.com نباید برنامه متوقف شود
    # exit(1)

# تابع خوش‌آمدگویی
def start(update: Update, context):
    print(f'User {update.effective_user.id} started the bot')  # لاگ شروع
    if not check_membership(update, context):
        return

    keyboard = [
        [InlineKeyboardButton('دریافت توکن اتصال به اینستاگرام', callback_data='get_token')],
        [InlineKeyboardButton('راهنمای اتصال به اینستاگرام', callback_data='instagram_help')],
        [InlineKeyboardButton('ارسال لینک مستقیم', callback_data='manual_link')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        'سلام! به ربات دانلود اینستاگرام خوش آمدید.\n\n'
        'شما می‌توانید:\n'
        '1️⃣ توکن اتصال به اینستاگرام دریافت کنید تا پست‌های شما به صورت خودکار دانلود شود\n'
        '2️⃣ یا به صورت مستقیم لینک پست را ارسال کنید\n\n'
        'لطفاً یکی از گزینه‌های زیر را انتخاب کنید:',
        reply_markup=reply_markup
    )


# مدیریت دکمه‌ها
def button_handler(update: Update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    print(f'Button clicked by user {user_id}: {query.data}')  # لاگ کلیک دکمه

    if query.data == 'get_token':
        token = db.register_user(user_id)
        if token:
            keyboard = [
                [InlineKeyboardButton('راهنمای اتصال به اینستاگرام', callback_data='instagram_help')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(
                f'توکن شما:\n\n`{token}`\n\n'
                'این توکن را در دایرکت اکانت اینستاگرام خود به پیج \'etehadtaskforce\' ارسال کنید.\n'
                'پس از اتصال، هر پستی که در دایرکت برای این پیج Share کنید به صورت خودکار برای شما دانلود خواهد شد.\n\n'
                'اگر مشکلی داشتید، از راهنما استفاده کنید!',
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            print(f'Token generated for user {user_id}: {token}')
        else:
            query.edit_message_text('خطا در تولید توکن. لطفاً دوباره تلاش کنید یا با ادمین تماس بگیرید.')
            print(f'Error generating token for user {user_id}')


    elif query.data == 'instagram_help':
        query.edit_message_text(
            '📱 **راهنمای اتصال به اینستاگرام:**\n\n'
            '1. ابتدا دکمه \'دریافت توکن اتصال به اینستاگرام\' را بزنید و توکن خود را دریافت کنید.\n'
            '2. به اینستاگرام بروید و به پیج \'etehadtaskforce\' پیام دهید.\n'
            '3. توکن خود را در دایرکت ارسال کنید.\n'
            '4. پس از تأیید توسط ربات، پیامی دریافت خواهید کرد.\n'
            '5. حالا می‌توانید پست‌های اینستاگرام را در دایرکت این پیج Share کنید تا به‌صورت خودکار دانلود شوند.\n\n'
            'برای بازگشت به منو اصلی، دستور /start را ارسال کنید.',
            parse_mode='Markdown'
        )
        print(f'Help message sent to user {user_id}')

    elif query.data == 'manual_link':
        query.edit_message_text(
            'لطفاً لینک پست یا ریل اینستاگرام خود را در چت ارسال کنید.\n'
            'مثال: https://www.instagram.com/p/Cabc123/\n'
            'ربات به‌صورت خودکار لینک را پردازش کرده و محتوا را برای شما ارسال خواهد کرد.'
        )
        print(f'Manual link instruction sent to user {user_id}')

# تابع بررسی عضویت در کانال‌های اجباری
def check_membership(update: Update, context) -> bool:
    user_id = update.effective_user.id
    not_joined_channels = []

    for channel in REQUIRED_CHANNELS:
        try:
            member = context.bot.get_chat_member(chat_id=channel['chat_id'], user_id=user_id)
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
        'برای استفاده از ربات، لطفا در کانال‌های زیر عضو شوید و سپس دوباره امتحان کنید:',
        reply_markup=reply_markup
    )
    return False

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
                            timeout=30  # افزایش زمان‌منتظر برای ارسال
                        )
                        video_sent = True
                        print(f"ویدیو با موفقیت ارسال شد: {video_path}")
                except Exception as e:
                    print(f"خطا در ارسال ویدیو: {str(e)}")
                    context.bot.send_message(chat_id=telegram_id, text=f"خطا در ارسال ویدیو: {str(e)}")
                # فایل ویدیو رو بعد از ارسال حذف می‌کنیم
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
                                timeout=30  # افزایش زمان‌منتظر برای ارسال
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

# تابع دریافت لینک مستقیم (هماهنگ با دایرکت)
def handle_link(update: Update, context):
    print(f"Received message: {update.message.text}")  # لاگ برای چک کردن دریافت پیام
    if not check_membership(update, context):
        return

    url = update.message.text
    print(f"Received URL: {url}")  # لاگ برای چک کردن لینک دریافت‌شده
    if "instagram.com" in url:
        update.message.reply_text("در حال دانلود... لطفا منتظر بمانید!")
        try:
            # استخراج shortcode از لینک
            if "/p/" in url:
                shortcode = url.split("/p/")[1].split("/")[0]
            elif "/reel/" in url:
                shortcode = url.split("/reel/")[1].split("/")[0]
            else:
                parts = url.strip('/').split('/')
                shortcode = parts[-1] if parts[-1] else parts[-2]
            if "?" in shortcode:
                shortcode = shortcode.split("?")[0]
            print(f"Extracted Shortcode: {shortcode}")  # لاگ برای چک کردن Shortcode

            # تبدیل shortcode به media_id
            media_id = ig_client.media_pk_from_code(shortcode)
            print(f"Extracted Media ID: {media_id}")  # لاگ برای چک کردن media_id

            # پردازش مثل دایرکت (استفاده از media_id مستقیم)
            telegram_id = update.effective_user.id
            threading.Thread(
                target=process_and_send_post,
                args=(media_id, telegram_id, context)
            ).start()
            update.message.reply_text("پست شما دریافت شد و در حال پردازش است.")

        except Exception as e:
            print(f"Error processing link: {str(e)}")  # لاگ خطا
            update.message.reply_text(f"خطا در پردازش لینک: {str(e)}")
    else:
        update.message.reply_text("لطفاً یه لینک معتبر از اینستاگرام ارسال کنید.")

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
            try:
                context.bot.send_message(chat_id=user[0], text=message_text)
            except Exception as e:
                print(f"خطا در ارسال پیام به کاربر {user[0]}: {str(e)}")
        update.message.reply_text("پیام همگانی با موفقیت ارسال شد.")
        del context.user_data['state']

# تابع دیباگ برای تست دریافت پیام
def debug_handler(update: Update, context):
    print(f"Debug: Received any message: {update.message.text}")

# تابع اصلی
def main():
    print("Bot is starting...")

    # راه اندازی Flask در یک thread جداگانه
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # راه اندازی تلگرام بات
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

    # شروع چک کردن دایرکت اینستاگرام
    instagram_thread = threading.Thread(target=check_instagram_dms, args=(dispatcher,), daemon=True)
    instagram_thread.start()

    # استفاده از polling به جای webhook برای سادگی و اجتناب از تداخل پورت
    print("Starting bot with polling mode...")
    updater.start_polling()
    
    updater.idle()

if __name__ == "__main__":
    main()
