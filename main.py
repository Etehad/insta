import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import RetryAfter, TelegramError
import yt_dlp
import re
import logging
import tempfile
import sys
import atexit
import threading
import time
import requests
from keep_alive import keep_alive
from bs4 import BeautifulSoup
import json
from instagrapi import Client
from instagrapi.exceptions import LoginRequired

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

# متغیر برای نگهداری نمونه ربات
bot_instance = None

# تابع پاکسازی در هنگام خروج
def cleanup():
    global bot_instance
    if bot_instance:
        logger.info("Stopping bot...")
        bot_instance.stop()
        bot_instance = None

# ثبت تابع پاکسازی
atexit.register(cleanup)

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
        "شما می‌توانید ویدیوهای اینستاگرام و یوتیوب را دانلود کنید.\n\n"
        "لطفاً لینک ویدیوی اینستاگرام یا یوتیوب مورد نظر خود را ارسال کنید.",
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

# تابع جایگزین برای دانلود ویدیو با استفاده از requests
def download_with_requests(url, output_path):
    try:
        logger.info(f"تلاش برای دانلود با استفاده از requests: {url}")
        
        # استخراج اطلاعات ویدیو بدون دانلود
        ydl_opts = {
            'format': 'best[height<=480]',
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            },
            'extractor_args': {'youtube': {'player_client': ['android']}},
            # 'proxy': 'socks5://127.0.0.1:9050',  # استفاده از پروکسی Tor (اگر نصب باشد)
        }
        
        # تلاش برای استفاده از چند پروکسی مختلف
        proxies = [
            None,  # بدون پروکسی
            {'http': 'socks5://127.0.0.1:9050', 'https': 'socks5://127.0.0.1:9050'},  # Tor
            {'http': 'http://free-proxy.cz:8080', 'https': 'http://free-proxy.cz:8080'},  # یک پروکسی عمومی
            {'http': 'http://103.152.112.162:80', 'https': 'http://103.152.112.162:80'},
            {'http': 'http://185.199.229.156:7492', 'https': 'http://185.199.229.156:7492'},
            {'http': 'http://185.199.228.220:7300', 'https': 'http://185.199.228.220:7300'},
            {'http': 'http://185.199.231.45:8382', 'https': 'http://185.199.231.45:8382'},
            {'http': 'http://8.219.74.58:8080', 'https': 'http://8.219.74.58:8080'},
        ]
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise Exception("اطلاعات ویدیو استخراج نشد")
            
            # پیدا کردن بهترین فرمت با کیفیت مناسب
            formats = info.get('formats', [])
            target_format = None
            
            # ابتدا فرمت‌های با کیفیت 480p را جستجو می‌کنیم
            for fmt in formats:
                if fmt.get('height') == 480 and fmt.get('ext') in ['mp4', 'webm']:
                    target_format = fmt
                    break
            
            # اگر فرمت 480p پیدا نشد، بهترین فرمت موجود را انتخاب می‌کنیم
            if not target_format:
                for fmt in formats:
                    if fmt.get('ext') in ['mp4', 'webm']:
                        if not target_format or (fmt.get('height', 0) <= 480 and fmt.get('height', 0) > target_format.get('height', 0)):
                            target_format = fmt
            
            if not target_format:
                raise Exception("هیچ فرمت مناسبی برای دانلود پیدا نشد")
            
            # دانلود ویدیو با استفاده از requests
            video_url = target_format.get('url')
            if not video_url:
                raise Exception("URL ویدیو یافت نشد")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Referer': 'https://www.youtube.com/',
            }
            
            # تلاش با پروکسی‌های مختلف
            last_error = None
            for proxy in proxies:
                try:
                    logger.info(f"تلاش دانلود با پروکسی: {proxy}")
                    response = requests.get(video_url, headers=headers, proxies=proxy, stream=True, timeout=60)
                    response.raise_for_status()
                    
                    # ذخیره فایل
                    with open(output_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    return info.get('title', 'ویدیوی یوتیوب')
                except Exception as e:
                    last_error = e
                    logger.warning(f"خطا در دانلود با پروکسی {proxy}: {str(e)}")
                    continue
            
            # اگر همه پروکسی‌ها ناموفق بودند
            if last_error:
                raise last_error
    
    except Exception as e:
        logger.error(f"خطا در دانلود با requests: {str(e)}")
        raise

# تابع دانلود ویدیو یوتیوب
def download_youtube_video(url, update: Update, context):
    try:
        safe_send_message(context, update.effective_chat.id, "در حال دانلود ویدیوی یوتیوب... لطفاً صبر کنید.")
        
        # استفاده از پوشه موقت برای دانلود
        with tempfile.TemporaryDirectory() as temp_dir:
            # تنظیمات yt-dlp برای یوتیوب با کیفیت 480p
            ydl_opts = {
                'format': 'best[height<=480]/worst[height>=480]/best',  # انتخاب کیفیت 480p یا نزدیک آن
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'quiet': True,
                'verbose': False,
                'noplaylist': True,  # فقط یک ویدیو دانلود شود، نه پلی‌لیست
                'retries': 10,
                'socket_timeout': 60,
                'nocheckcertificate': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': 'https://www.youtube.com/',
                    'Origin': 'https://www.youtube.com',
                },
                'nocheckcertificate': True,
                'no_warnings': True,
                'ignoreerrors': False,
                'skip_download': False,
                'writethumbnail': False,
                'geo_bypass': True,
                'geo_bypass_country': 'US',
                'prefer_ffmpeg': True,
                'quiet_download': True,
                'external_downloader_args': ['-loglevel', 'panic'],
                'cookiefile': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt'),
                'extractor_args': {'youtube': {'player_client': ['android']}},
                'extractor_retries': 5,
                # پروکسی را فقط در صورت نیاز فعال کنید
                # 'proxy': 'socks5://127.0.0.1:9050',  # استفاده از پروکسی Tor (اگر نصب باشد)
            }
            
            try:
                logger.info(f"شروع دانلود ویدیوی یوتیوب از آدرس: {url}")
                
                # متغیر برای نگهداری عنوان ویدیو
                title = "ویدیوی یوتیوب"
                video_file = None
                download_success = False
                
                # دانلود ویدیو
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        # تلاش دانلود با تنظیمات پیش‌فرض
                        try:
                            info = ydl.extract_info(url, download=True)
                            title = info.get('title', 'ویدیوی یوتیوب')
                            download_success = True
                        except Exception as e:
                            # اگر تلاش اول ناموفق بود، با تنظیمات متفاوت امتحان کنید
                            logger.warning(f"دانلود اول ناموفق بود: {str(e)}. تلاش با تنظیمات دیگر...")
                            
                            # روش دوم: استفاده از فرمت متفاوت
                            try:
                                ydl_opts['format'] = 'best/worst'
                                ydl_opts['extractor_args'] = {'youtube': {'player_client': ['web']}}
                                with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                                    info = ydl2.extract_info(url, download=True)
                                    title = info.get('title', 'ویدیوی یوتیوب')
                                    download_success = True
                            except Exception as e2:
                                logger.warning(f"دانلود دوم ناموفق بود: {str(e2)}. تلاش با روش سوم...")
                                
                                # روش سوم: استفاده از User-Agent متفاوت
                                try:
                                    ydl_opts['http_headers'] = {
                                        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                                        'Accept-Language': 'en-US,en;q=0.9',
                                        'Referer': 'https://www.google.com/',
                                    }
                                    ydl_opts['extractor_args'] = {'youtube': {'player_client': ['ios']}}
                                    with yt_dlp.YoutubeDL(ydl_opts) as ydl3:
                                        info = ydl3.extract_info(url, download=True)
                                        title = info.get('title', 'ویدیوی یوتیوب')
                                        download_success = True
                                except Exception as e3:
                                    logger.warning(f"دانلود سوم ناموفق بود: {str(e3)}. تلاش با روش چهارم...")
                                    
                                    # روش چهارم: استفاده از پروکسی
                                    try:
                                        ydl_opts['proxy'] = 'socks5://127.0.0.1:9050'  # استفاده از پروکسی Tor
                                        with yt_dlp.YoutubeDL(ydl_opts) as ydl4:
                                            info = ydl4.extract_info(url, download=True)
                                            title = info.get('title', 'ویدیوی یوتیوب')
                                            download_success = True
                                    except Exception as e4:
                                        logger.warning(f"دانلود چهارم ناموفق بود: {str(e4)}. تلاش با روش requests...")
                except Exception as e_all:
                    logger.warning(f"همه تلاش‌های yt-dlp ناموفق بود: {str(e_all)}. تلاش با روش requests...")
                
                # اگر همه روش‌های yt-dlp ناموفق بود، از requests استفاده می‌کنیم
                if not download_success:
                    output_file = os.path.join(temp_dir, "youtube_video.mp4")
                    title = download_with_requests(url, output_file)
                    download_success = True
                
                # یافتن فایل دانلود شده
                downloaded_files = os.listdir(temp_dir)
                logger.info(f"فایل‌های موجود در پوشه موقت: {downloaded_files}")
                
                if not downloaded_files:
                    raise Exception("هیچ فایلی دانلود نشد")
                
                # انتخاب فایل ویدیو
                video_file = os.path.join(temp_dir, downloaded_files[0])
                
                # بررسی اندازه فایل (محدودیت تلگرام 50 مگابایت است)
                file_size = os.path.getsize(video_file)
                if file_size > 50 * 1024 * 1024:
                    safe_send_message(
                        context,
                        update.effective_chat.id,
                        "اندازه ویدیو بزرگتر از محدودیت تلگرام است. امکان ارسال وجود ندارد."
                    )
                    return
                
                logger.info(f"ارسال ویدیو: {video_file} (اندازه: {file_size} بایت)")
                
                # ارسال ویدیو به کاربر
                try:
                    with open(video_file, 'rb') as video_data:
                        context.bot.send_video(
                            chat_id=update.effective_chat.id,
                            video=video_data,
                            caption=f"🎥 {title}\n\n[TaskForce](https://t.me/task_1_4_1_force)",
                            parse_mode="Markdown"
                        )
                    logger.info(f"ویدیو با موفقیت ارسال شد")
                except RetryAfter as e:
                    logger.warning(f"خطای RetryAfter هنگام ارسال ویدیو: {e}")
                    time.sleep(e.retry_after)
                    with open(video_file, 'rb') as video_data:
                        context.bot.send_video(
                            chat_id=update.effective_chat.id,
                            video=video_data,
                            caption=f"🎥 {title}\n\n[TaskForce](https://t.me/task_1_4_1_force)",
                            parse_mode="Markdown"
                        )
                
            except Exception as e:
                logger.error(f"خطا در دانلود ویدیوی یوتیوب: {str(e)}")
                safe_send_message(
                    context,
                    update.effective_chat.id,
                    f"خطا در دانلود ویدیوی یوتیوب: لطفاً لینک دیگری امتحان کنید یا بعداً دوباره تلاش کنید."
                )
                
    except Exception as e:
        logger.error(f"خطای کلی در دانلود ویدیو: {str(e)}")
        safe_send_message(
            context,
            update.effective_chat.id,
            "خطا در دانلود ویدیو. لطفاً دوباره تلاش کنید."
        )

# تابع دانلود ویدیوی اینستاگرام
def download_instagram_video(url, update: Update, context):
    try:
        safe_send_message(context, update.effective_chat.id, "در حال دانلود ویدیوی اینستاگرام... لطفاً صبر کنید.")
        
        # استفاده از پوشه موقت برای دانلود
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                logger.info(f"شروع دانلود ویدیوی اینستاگرام از آدرس: {url}")
                
                # استخراج شناسه پست از URL
                if 'instagram.com/p/' in url or 'instagram.com/reel/' in url:
                    # استخراج شناسه پست
                    post_id = None
                    if '/p/' in url:
                        post_id = url.split('/p/')[1].split('/')[0].split('?')[0]
                    elif '/reel/' in url:
                        post_id = url.split('/reel/')[1].split('/')[0].split('?')[0]
                    
                    if not post_id:
                        raise Exception("شناسه پست اینستاگرام یافت نشد")
                    
                    logger.info(f"شناسه پست اینستاگرام: {post_id}")
                    
                    # متغیرها برای نگهداری اطلاعات ویدیو
                    video_url = None
                    caption = "ویدیوی اینستاگرام"
                    video_file = os.path.join(temp_dir, f"instagram_video_{post_id}.mp4")
                    download_success = False
                    
                    # روش اول: استفاده از instagrapi بدون لاگین
                    try:
                        logger.info("تلاش برای دانلود با instagrapi بدون لاگین...")
                        cl = Client()
                        
                        # تلاش برای دانلود بدون لاگین
                        try:
                            # تبدیل شناسه کوتاه به شناسه عددی
                            media_pk = cl.media_pk_from_code(post_id)
                            logger.info(f"شناسه عددی پست: {media_pk}")
                            
                            # دانلود ویدیو
                            media_path = cl.video_download(media_pk, temp_dir)
                            logger.info(f"ویدیو با موفقیت دانلود شد: {media_path}")
                            
                            # دریافت اطلاعات پست
                            try:
                                media_info = cl.media_info(media_pk)
                                caption = media_info.caption_text if media_info.caption_text else "ویدیوی اینستاگرام"
                            except Exception as e:
                                logger.warning(f"خطا در دریافت اطلاعات پست: {str(e)}")
                            
                            video_file = media_path
                            download_success = True
                        except LoginRequired:
                            logger.warning("نیاز به لاگین برای دانلود با instagrapi. تلاش با روش دیگر...")
                        except Exception as e:
                            logger.warning(f"خطا در دانلود با instagrapi: {str(e)}")
                    except Exception as e:
                        logger.warning(f"خطا در استفاده از instagrapi: {str(e)}")
                    
                    # روش دوم: استفاده از requests و BeautifulSoup
                    if not download_success:
                        try:
                            logger.info("تلاش برای دانلود با روش مستقیم...")
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                                'Accept-Language': 'en-US,en;q=0.5',
                            }
                            
                            # تلاش برای دریافت عنوان ویدیو
                            try:
                                api_url = f"https://api.instagram.com/oembed/?url={url}"
                                response = requests.get(api_url, headers=headers)
                                if response.status_code == 200:
                                    data = response.json()
                                    caption = data.get('title', 'ویدیوی اینستاگرام')
                            except Exception as e:
                                logger.warning(f"خطا در دریافت اطلاعات از API اینستاگرام: {str(e)}")
                            
                            # روش مستقیم: استخراج لینک ویدیو از HTML
                            response = requests.get(url, headers=headers)
                            if response.status_code == 200:
                                html_content = response.text
                                
                                # جستجوی لینک ویدیو در HTML
                                video_pattern = r'<meta property="og:video" content="([^"]+)"'
                                video_match = re.search(video_pattern, html_content)
                                
                                if video_match:
                                    video_url = video_match.group(1)
                                    logger.info(f"لینک ویدیو از HTML: {video_url}")
                                else:
                                    # جستجوی لینک ویدیو در JSON داده‌های صفحه
                                    json_pattern = r'<script type="application/ld\+json">(.+?)</script>'
                                    json_match = re.search(json_pattern, html_content, re.DOTALL)
                                    
                                    if json_match:
                                        try:
                                            json_data = json.loads(json_match.group(1))
                                            if json_data.get('video'):
                                                video_url = json_data.get('video').get('contentUrl')
                                                logger.info(f"لینک ویدیو از JSON: {video_url}")
                                        except Exception as e:
                                            logger.warning(f"خطا در پردازش JSON: {str(e)}")
                                
                                # جستجوی لینک ویدیو در تگ‌های ویدیو
                                if not video_url:
                                    soup = BeautifulSoup(html_content, 'html.parser')
                                    video_tags = soup.find_all('video')
                                    for video_tag in video_tags:
                                        if video_tag.get('src'):
                                            video_url = video_tag.get('src')
                                            logger.info(f"لینک ویدیو از تگ ویدیو: {video_url}")
                                            break
                            
                            # اگر لینک ویدیو پیدا شد، آن را دانلود کنید
                            if video_url:
                                response = requests.get(video_url, headers=headers, stream=True)
                                response.raise_for_status()
                                
                                with open(video_file, 'wb') as f:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        f.write(chunk)
                                
                                download_success = True
                        except Exception as e:
                            logger.warning(f"خطا در دانلود با روش مستقیم: {str(e)}")
                    
                    # روش سوم: استفاده از سرویس‌های دانلود آنلاین
                    if not download_success:
                        try:
                            logger.info("تلاش برای دانلود با سرویس SaveFrom.net...")
                            savefrom_url = f"https://worker.sf-tools.com/savefrom.php?url={url}"
                            savefrom_headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                                'Accept': 'application/json, text/javascript, */*; q=0.01',
                                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                'Origin': 'https://en.savefrom.net',
                                'Referer': 'https://en.savefrom.net/',
                            }
                            
                            savefrom_response = requests.post(
                                savefrom_url,
                                headers=savefrom_headers,
                                data=f"sf_url={url}&sf_submit=&new=2&lang=en&app=&country=&os=Windows&browser=Chrome&channel=&sf-nomad=1"
                            )
                            
                            if savefrom_response.status_code == 200:
                                savefrom_data = savefrom_response.json()
                                if savefrom_data.get('url'):
                                    for item in savefrom_data.get('url', []):
                                        if item.get('url') and item.get('type') == 'mp4':
                                            video_url = item.get('url')
                                            logger.info(f"لینک ویدیو از SaveFrom.net: {video_url}")
                                            
                                            # دانلود ویدیو
                                            response = requests.get(video_url, headers=savefrom_headers, stream=True)
                                            response.raise_for_status()
                                            
                                            with open(video_file, 'wb') as f:
                                                for chunk in response.iter_content(chunk_size=8192):
                                                    f.write(chunk)
                                            
                                            download_success = True
                                            break
                        except Exception as e:
                            logger.warning(f"خطا در استفاده از سرویس SaveFrom.net: {str(e)}")
                    
                    # اگر هیچ یک از روش‌ها موفق نبود
                    if not download_success:
                        raise Exception("دانلود ویدیو با همه روش‌ها ناموفق بود")
                    
                    # بررسی اندازه فایل (محدودیت تلگرام 50 مگابایت است)
                    file_size = os.path.getsize(video_file)
                    if file_size > 50 * 1024 * 1024:
                        safe_send_message(
                            context,
                            update.effective_chat.id,
                            "اندازه ویدیو بزرگتر از محدودیت تلگرام است. امکان ارسال وجود ندارد."
                        )
                        return
                    
                    logger.info(f"ارسال ویدیو: {video_file} (اندازه: {file_size} بایت)")
                    
                    # ارسال ویدیو به کاربر
                    try:
                        with open(video_file, 'rb') as video_data:
                            context.bot.send_video(
                                chat_id=update.effective_chat.id,
                                video=video_data,
                                caption=f"🎥 {caption}\n\n[TaskForce](https://t.me/task_1_4_1_force)",
                                parse_mode="Markdown"
                            )
                        logger.info(f"ویدیو با موفقیت ارسال شد")
                    except RetryAfter as e:
                        logger.warning(f"خطای RetryAfter هنگام ارسال ویدیو: {e}")
                        time.sleep(e.retry_after)
                        with open(video_file, 'rb') as video_data:
                            context.bot.send_video(
                                chat_id=update.effective_chat.id,
                                video=video_data,
                                caption=f"🎥 {caption}\n\n[TaskForce](https://t.me/task_1_4_1_force)",
                                parse_mode="Markdown"
                            )
                else:
                    raise Exception("لینک اینستاگرام نامعتبر است. لطفاً یک لینک پست یا ریل اینستاگرام ارسال کنید.")
                
            except Exception as e:
                logger.error(f"خطا در دانلود ویدیوی اینستاگرام: {str(e)}")
                safe_send_message(
                    context,
                    update.effective_chat.id,
                    f"خطا در دانلود ویدیوی اینستاگرام: لطفاً لینک دیگری امتحان کنید یا بعداً دوباره تلاش کنید."
                )
                
    except Exception as e:
        logger.error(f"خطای کلی در دانلود ویدیو: {str(e)}")
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

    # بررسی لینک اینستاگرام
    if any(domain in url.lower() for domain in ['instagram.com']):
        threading.Thread(target=download_instagram_video, args=(url, update, context)).start()
    # بررسی لینک یوتیوب
    elif any(domain in url.lower() for domain in ['youtube.com', 'youtu.be']):
        threading.Thread(target=download_youtube_video, args=(url, update, context)).start()
    else:
        safe_send_message(context, update.effective_chat.id, "لطفاً یک لینک معتبر از اینستاگرام یا یوتیوب ارسال کنید.")

# مدیریت دکمه‌ها
def button_handler(update: Update, context):
    query = update.callback_query
    query.answer()

    if query.data == "help":
        query.edit_message_text(
            "📱 **راهنمای استفاده از ربات:**\n\n"
            "1. لینک ویدیوی مورد نظر خود را از اینستاگرام یا یوتیوب کپی کنید\n"
            "2. لینک را در چت ربات ارسال کنید\n"
            "3. ربات به صورت خودکار ویدیو را دانلود و برای شما ارسال می‌کند\n\n"
            "**لینک‌های پشتیبانی شده:**\n"
            "- لینک پست اینستاگرام (مثال: https://www.instagram.com/p/ABC123/)\n"
            "- لینک ریل اینستاگرام (مثال: https://www.instagram.com/reel/ABC123/)\n"
            "- لینک ویدیوی یوتیوب (مثال: https://youtu.be/ABC123 یا https://www.youtube.com/watch?v=ABC123)\n\n"
            "نکته: برای استفاده از ربات باید در کانال‌های اجباری عضو باشید.",
            parse_mode="Markdown"
        )
    elif query.data == "support":
        query.edit_message_text(
            "برای پشتیبانی با ادمین در ارتباط باشید:\n"
            "@task_1_4_1_force"
        )

# تابع مدیریت خطا
def error_handler(update: Update, context):
    logger.error(f"Update {update} caused error: {context.error}")
    if update and update.effective_message:
        safe_send_message(
            context,
            update.effective_chat.id,
            "متأسفانه خطایی رخ داد. لطفاً دوباره تلاش کنید."
        )

# تابع اصلی
def main():
    global bot_instance
    
    # بررسی وجود نمونه قبلی
    if bot_instance:
        logger.warning("Bot is already running!")
        return
    
    try:
        logger.info("Bot is starting...")
        
        # راه‌اندازی وب‌سرور برای نگه داشتن ربات در حالت فعال
        keep_alive()
        
        bot_instance = Updater(TOKEN, use_context=True)
        dispatcher = bot_instance.dispatcher

        # ثبت handlerها
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))
        dispatcher.add_handler(CallbackQueryHandler(button_handler))

        # اضافه کردن error handler
        dispatcher.add_error_handler(error_handler)

        # شروع ربات
        bot_instance.start_polling(drop_pending_updates=True)

        logger.info("Bot started successfully!")
        bot_instance.idle()

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()
