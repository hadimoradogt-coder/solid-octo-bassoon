import os
import re
import json
import logging
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ===== تنظیمات =====
BOT_TOKEN='***'
ADMIN_USER_ID = 5080529808

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ================ توابع دانلود ================

async def download_instagram(url: str, quality: str = "best") -> dict:
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'outtmpl': 'downloads/%(id)s.%(ext)s',
    }

    if quality == "best":
        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    elif quality == "medium":
        ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best'
    elif quality == "low":
        ydl_opts['format'] = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best'
    elif quality == "audio":
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            result = {
                'title': info.get('title', 'بدون عنوان'),
                'uploader': info.get('uploader', 'ناشناس'),
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'comment_count': info.get('comment_count', 0),
                'files': [],
                'type': 'video',
            }

            if info.get('entries'):
                result['type'] = 'gallery'
                for entry in info['entries'][:10]:
                    img_url = entry.get('url')
                    if img_url:
                        result['files'].append(img_url)
                return result

            ydl.download([url])
            filename = ydl.prepare_filename(info)
            base, ext = os.path.splitext(filename)
            
            if quality == "audio":
                filename = base + '.mp3'
            elif not ext or ext == '.m4a':
                for f in os.listdir('downloads/'):
                    if info.get('id') in f:
                        filename = os.path.join('downloads', f)
                        break
            
            if os.path.exists(filename):
                result['files'].append(filename)
            
            return result

    except Exception as e:
        logger.error(f"Download error: {e}")
        return {'error': str(e), 'files': []}


def format_duration(seconds: int) -> str:
    if not seconds:
        return "نامشخص"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    return f"{m}:{s:02d}"


def format_count(n: int) -> str:
    if not n:
        return "0"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


# ================ هندلرهای ربات ================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"🎬 **به ربات دانلود اینستاگرام خوش اومدی {user.first_name} جان!**\n\n"
        f"✨ **قابلیت‌ها:**\n"
        f"📹 دانلود **ریلز** با کیفیت 1080p\n"
        f"🖼️ دانلود **پست‌های تصویری** (چندتایی)\n"
        f"🎵 استخراج **صدا** از ویدیوها\n"
        f"📊 نمایش اطلاعات ویدیو\n\n"
        f"🔗 **فقط کافیه لینک اینستاگرام رو بفرستی:**\n"f"• `https://www.instagram.com/reel/...`\n"
        f"• `https://www.instagram.com/p/...`\n\n"
        f"⚡ توسط **@Danloderebot**"
    )
    
    keyboard = [
        [InlineKeyboardButton("📖 راهنما", callback_data="help"),
         InlineKeyboardButton("💡 نکات", callback_data="tips")],
        [InlineKeyboardButton("👨‍💻 سازنده", url="https://t.me/hadi_dev")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📖 **راهنمای استفاده**\n\n"
        "1️⃣ یک لینک اینستاگرام برام بفرست\n"
        "2️⃣ اطلاعات ویدیو رو برات می‌فرستم\n"
        "3️⃣ کیفیت مورد نظرت رو انتخاب کن\n"
        "4️⃣ فایل آماده دانلوده! 🎉\n\n"
        "**لینک‌های قابل قبول:**\n"
        "• `instagram.com/reel/...` ← ریلز\n"
        "• `instagram.com/p/...` ← پست\n"
        "• لینک رو کامل بفرست\n\n"
        "**محدودیت‌ها:**\n"
        "• پیج‌های خصوصی قابل دانلود نیست\n"
        "• حداکثر حجم 50 مگابایت",
        parse_mode="Markdown"
    )


async def tips_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💡 **نکات طلایی**\n\n"
        "🎯 **کیفیت 1080p** → بالاترین کیفیت\n"
        "🎯 **کیفیت 720p** ← متعادل و سریع\n"
        "🎯 **کیفیت 480p** ← کم‌حجم\n"
        "🎯 **فقط صدا** ← برای گوش دادن\n\n"
        "🔄 لینک‌های اینستاگرام رو از داخل اپ\n"
        "یا مرورگر کپی کن و بفرست\n\n"
        "❌ اگه خطا گرفتی:\n"
        "• مطمئن شو لینک درسته\n"
        "• پیج عمومی باشه\n"
        "• دوباره امتحان کن",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    instagram_pattern = r'(https?://)?(www\.)?(instagram\.com|instagr\.am)/(p|reel|tv)/([A-Za-z0-9_-]+)'
    match = re.search(instagram_pattern, text)

    if match:
        url = match.group(0)
        if not url.startswith('http'):
            url = 'https://' + url
        
        context.user_data['instagram_url'] = url
        
        status_msg = await update.message.reply_text("🔍 **در حال دریافت اطلاعات...**", parse_mode="Markdown")
        
        result = await download_instagram(url)
        
        if result.get('error'):
            await status_msg.edit_text(
                "❌ **خطا در دانلود!**\n\n"
                f"`{result['error'][:100]}`\n\n"
                "🔹 لینک رو چک کن\n🔹 صفحه عمومی باشه\n🔹 دوباره تلاش کن",
                parse_mode="Markdown"
            )
            return
        
        duration_str = format_duration(result.get('duration', 0))
        views_str = format_count(result.get('view_count', 0))
        likes_str = format_count(result.get('like_count', 0))
        
        info_text = (
            f"✅ **اطلاعات دریافت شد!**\n\n"
            f"📹 **عنوان:** {result.get('title', 'بدون عنوان')[:80]}\n"
            f"👤 **ناشر:** {result.get('uploader', 'ناشناس')}\n"
            f"⏱ **مدت:** {duration_str}\n"
            f"👁 **بازدید:** {views_str}\n"
            f"❤️ **لایک:** {likes_str}\n"
            f"💬 **کامنت:** {format_count(result.get('comment_count', 0))}\n\n"
            f"🔽 **کیفیت مورد نظر رو انتخاب کن:**"
        )
        
        await status_msg.delete()
        
        keyboard = [
            [InlineKeyboardButton("🎬 1080p", callback_data="quality_best"),
             InlineKeyboardButton("📺 720p", callback_data="quality_medium")],
            [InlineKeyboardButton("📱 480p", callback_data="quality_low"),
             InlineKeyboardButton("🎵 فقط صدا", callback_data="quality_audio")],
            [InlineKeyboardButton("❌ لغو", callback_data="cancel")]
  ]
      reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(info_text, reply_markup=reply_markup, parse_mode="Markdown")
    
    elif user_id == ADMIN_USER_ID and text.startswith("/"):
        if text == "/stats":
            await update.message.reply_text("📊 **آمار ربات:**\n\n🚧 در دست ساخت...", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ دستور نامعتبر")
    else:
        await update.message.reply_text(
            "🤔 **این چیه فرستادی؟**\n\n"
            "لطفاً یه لینک اینستاگرام بفرست:\n"
            "`https://www.instagram.com/reel/...`",
            parse_mode="Markdown"
        )


async def quality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    quality_map = {
        "quality_best": ("best", "🎬 **1080p**"),
        "quality_medium": ("medium", "📺 **720p**"),
        "quality_low": ("low", "📱 **480p**"),
        "quality_audio": ("audio", "🎵 **فقط صدا**"),
        "cancel": None
    }
    
    if query.data == "cancel":
        await query.edit_message_text("❌ **عملیات لغو شد.**", parse_mode="Markdown")
        return
    
    quality_key, quality_name = quality_map[query.data]
    url = context.user_data.get('instagram_url')
    
    if not url:
        await query.edit_message_text("❌ **لینگی ذخیره نشده!** دوباره یه لینک بفرست.", parse_mode="Markdown")
        return
    
    await query.edit_message_text(
        f"⏳ **در حال دانلود...**\nکیفیت: {quality_name}\n\n"
        f"🔹 دریافت اطلاعات\n🔸 دانلود فایل...\n🔹 آماده‌سازی برای ارسال",
        parse_mode="Markdown"
    )
    
    result = await download_instagram(url, quality_key)
    
    if result.get('error'):
        await query.edit_message_text(f"❌ **خطا در دانلود!**\n\n`{result['error'][:150]}`", parse_mode="Markdown")
        return
    
    files = result.get('files', [])
    if not files:
        await query.edit_message_text("❌ **فایلی برای ارسال پیدا نشد!**", parse_mode="Markdown")
        return
    
    await query.edit_message_text(f"📤 **در حال ارسال...**\nکیفیت: {quality_name}", parse_mode="Markdown")
    
    for file_path in files:
        if not os.path.exists(file_path):
            continue
        
        try:
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > 45:
                await query.message.reply_text(f"⚠️ **فایل حجیم هست** ({file_size_mb:.0f}MB)\nممکنه ارسالش طول بکشه...")
            
            if file_path.endswith(('.mp3', '.m4a', '.ogg')):
                with open(file_path, 'rb') as f:
                    await query.message.reply_audio(audio=f, title=result.get('title', 'صدا'))
            elif file_path.endswith(('.jpg', '.jpeg', '.png')):
                with open(file_path, 'rb') as f:
                    await query.message.reply_photo(photo=f)
            elif file_path.endswith(('.mp4', '.mov', '.webm')):
                with open(file_path, 'rb') as f:
                    await query.message.reply_video(video=f, supports_streaming=True)
            else:
                with open(file_path, 'rb') as f:
                    await query.message.reply_document(document=f)
            
            os.remove(file_path)
            
        except Exception as e:
            logger.error(f"Send error: {e}")
            await query.message.reply_text(f"❌ **خطا در ارسال فایل:** {str(e)[:100]}")
    
    await query.edit_message_text("✅ **دانلود کامل شد!** ممنون که از ربات استفاده کردی 🙏")


def main():
    os.makedirs('downloads', exist_ok=True)
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(quality_callback, pattern="^quality_|^cancel$"))
    application.add_handler(CallbackQueryHandler(help_callback, pattern="^help$"))application.add_handler(CallbackQueryHandler(tips_callback, pattern="^tips$"))
    
    logger.info("🚀 ربات اینستاگرام با موفقیت راه‌اندازی شد!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
