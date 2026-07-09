import os
import re
import logging
import asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN='7651648073:AAEYmoldWDZOaV4VI8bVlO2cJrd8IGOu294'
BOT_USERNAME = "@Danloderebot"
CREATOR_USERNAME = "@thehadimoradi"

def extract_supported_urls(text: str) -> list:
    """استخراج لینک‌های پشتیبانی‌شده: اینستاگرام، تیک‌تاک، یوتیوب، اسپاتیفای"""
    urls = []
    for word in re.findall(r'https?://[^\s]+', text):
        if any(s in word for s in ['instagram', 'instagr.am', 'tiktok', 'youtube', 'youtu.be', 'spotify']):
            clean = word.rstrip('.,)')
            if clean not in urls:
                urls.append(clean)
    return urls

def detect_source(url: str) -> str:
    """تشخیص منبع لینک"""
    if 'spotify' in url:
        return 'spotify'
    if 'tiktok' in url:
        return 'tiktok'
    if 'youtu' in url:
        return 'youtube'
    if 'instagram' in url or 'instagr.am' in url:
        return 'instagram'
    return 'unknown'

def get_info(url: str) -> dict | None:
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        logger.error(f"info error: {e}")
        return None

def get_video(url: str, tag: str) -> list:
    """دانلود بهترین کیفیت (آلبوم چندتایی پشتیبانی میشه)"""
    outtmpl = f'downloads/{tag}_%(id)s_%(playlist_index)02d.%(ext)s'
    ydl_opts = {
        'format': 'best',
        'outtmpl': outtmpl,
        'noplaylist': False,
        'quiet': True,
        'no_warnings': True,
    }
    files = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            entries = info.get('entries')
            if entries:
                for e in entries:
                    if not e:
                        continue
                    fn = ydl.prepare_filename(e)
                    if os.path.exists(fn):
                        files.append(fn)
                    else:
                        vid = e.get('id', '')
                        for f in os.listdir('downloads'):
                            if tag in f and vid[:6] in f and not f.endswith('.part'):
                                files.append(os.path.join('downloads', f))
                                break
            else:
                fn = ydl.prepare_filename(info)
                if os.path.exists(fn):
                    files.append(fn)
                else:
                    vid = info.get('id', '')
                    for f in os.listdir('downloads'):
                        if tag in f and vid[:6] in f and not f.endswith('.part'):
                            files.append(os.path.join('downloads', f))
                            break
    except Exception as e:
        logger.error(f"video error: {e}")
    return files

def build_caption(info) -> str:
    parts = []
    if info:
        desc = (info.get('description') or '').strip()
        title = (info.get('title') or '').strip()
        if desc:
            clean = desc.replace('\n', ' ').strip()
            if len(clean) > 300:
                clean = clean[:300] + '...'
            parts.append(f"📝 **کپشن:**\n{clean}")
        elif title and not title.startswith('Video by'):
            parts.append(f"📝 **عنوان:** {title[:300]}")
    parts.append(f"\n🤖 {BOT_USERNAME}")
    return "\n".join(parts)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "🎬 **ربات دانلود ویدیو**\n\n"
        "👇 لینک ویدیو رو بفرست (چندتا همزمان هم اوکیه) تا با بهترین کیفیت دانلودش کنم\n\n"
        "✨ **پلتفرم‌های پشتیبانی‌شده:**\n"
        "• 📸 اینستاگرام (رییلز/پست/استوری)\n"
        "• 🎵 تیک‌تاک\n"
        "• ▶️ یوتیوب (ویدیو/شورتس)\n"
        "• 🟢 اسپاتیفای (فقط نمایش لینک)\n\n"
        "🔹 چند لینک رو پشت سر هم بفرست تا همه رو بگیری!"
    )
    await update.message.reply_text(txt, parse_mode="Markdown")

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "🔴 **ارتباط با سازنده**\n\n"
        f"برای پشتیبانی و سفارش ربات به آیدی زیر پیام بده:\n"
        f"👤 @{CREATOR_USERNAME.lstrip('@')}"
    )
    await update.message.reply_text(txt, parse_mode="Markdown")

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(f"🆔 آیدی تلگرام شما:\n`{uid}`", parse_mode="Markdown")

async def send_one_media(update: Update, url: str, index: int, total: int):
    """دانلود و ارسال یک مدیا (اینستاگرام/تیک‌تاک/یوتیوب)"""
    source = detect_source(url)
    status = await update.message.reply_text(f"⏳ **({index}/{total}) [{source}] در حال دانلود...**\nلطفاً صبر کن 🎥", parse_mode="Markdown")

    # اسپاتیفای: فقط لینک رو میده
    if source == 'spotify':
        await status.edit_text(f"🟢 **لینک اسپاتیفای:**\n{url}\n\n⚠️ دانلود مستقیم اسپاتیفای پشتیبانی نمیشه (نیاز به اشتراک).", parse_mode="Markdown",
                               reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🟢 باز کردن در اسپاتیفای", url=url)]]))
        return url

    info = await asyncio.to_thread(get_info, url)
    if not info:
        await status.edit_text(f"❌ **({index}/{total}) لینک نامعتبره یا خصوصیه!**", parse_mode="Markdown")
        return None
    files = await asyncio.to_thread(get_video, url, 'dl')
    if not files:
        await status.edit_text(f"❌ **({index}/{total}) دانلود نشد!**", parse_mode="Markdown")
        return None
    caption = build_caption(info)
    try:
        if len(files) == 1:
            with open(files[0], 'rb') as fh:
                await update.message.reply_video(video=fh, supports_streaming=True, caption=caption, parse_mode="Markdown")
            os.remove(files[0])
        else:
            media = []
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in ('.jpg', '.jpeg', '.png', '.webp'):
                    media.append(InputMediaPhoto(open(f, 'rb')))
                else:
                    media.append(InputMediaVideo(open(f, 'rb')))
            await update.message.reply_media_group(media)
            for f in files:
                os.remove(f)
            await update.message.reply_text("✅ **آلبوم آماده شد!**\n\n🤖 " + BOT_USERNAME, parse_mode="Markdown")
        await status.delete()
        return url
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارسال ({index}/{total}): {str(e)[:100]}")
        return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    urls = extract_supported_urls(text)
    if not urls:
        await update.message.reply_text("❌ **فقط لینک اینستاگرام/تیک‌تاک/یوتیوب/اسپاتیفای قبوله!**", parse_mode="Markdown")
        return

    if len(urls) > 1:
        await update.message.reply_text(f"🔢 **{len(urls)} لینک پیدا شد!**\nدر حال دانلود همه‌شون... ⏳", parse_mode="Markdown")

    for i, url in enumerate(urls, 1):
        await send_one_media(update, url, i, len(urls))

    if len(urls) > 1:
        await update.message.reply_text("✅ **همه مدیا آماده شد!**\n\n🤖 " + BOT_USERNAME, parse_mode="Markdown")

def main():
    os.makedirs('downloads', exist_ok=True)
    application = Application.builder().token(BOT_TOKEN).build()
    try:
        application.bot.set_my_commands([
            ('start', 'شروع و راهنما'),
            ('contact', 'ارتباط با سازنده'),
            ('myid', 'نمایش آیدی تلگرام'),
        ])
    except Exception as e:
        logger.warning(f"set_my_commands: {e}")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("contact", contact))
    application.add_handler(CommandHandler("myid", myid))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🚀 ربات با موفقیت بالا اومد!")
    application.run_polling()

if __name__ == "__main__":
    main()
