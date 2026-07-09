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

def extract_instagram_urls(text: str) -> list:
    """استخراج همه لینک‌های اینستاگرام از یک پیام"""
    pattern = r'(https?://)?(www\.)?(instagram\.com|instagr\.am)/(p|reel|tv|stories)/([A-Za-z0-9_-]+)'
    urls = []
    for m in re.findall(pattern, text):
        url = 'https://www.instagram.com/' + m[2] + '/' + m[3] + '/' + m[4]
        if url not in urls:
            urls.append(url)
    return urls

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

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """منوی اصلی /start"""
    kb = [
        [
            InlineKeyboardButton("📨 دعوت دوست", switch_inline_query=""),
            InlineKeyboardButton("➕ اضافه به چت", url=f"https://t.me/{BOT_USERNAME.lstrip('@')}?startgroup=true"),
        ],
        [
            InlineKeyboardButton("⚙️ منو", callback_data="open_menu"),
        ],
    ]
    return InlineKeyboardMarkup(kb)

def settings_keyboard() -> InlineKeyboardMarkup:
    """زیرمنوی تنظیمات"""
    kb = [
        [InlineKeyboardButton("📊 کیفیت: خودکار (بهترین)", callback_data="set_quality")],
        [InlineKeyboardButton("🔔 اعلان‌ها: روشن", callback_data="toggle_notif")],
        [InlineKeyboardButton("🎨 تم: تیره", callback_data="set_theme")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "🎬 **ربات دانلود اینستاگرام**\n\n"
        "👇 لینک ریلز یا پست اینستاگرام رو بفرست تا با بهترین کیفیت برات دانلودش کنم ✨\n\n"
        "🔹 `https://www.instagram.com/reel/...`\n\n"
        "📦 چند لینک رو همزمان بفرست تا همه رو بگیری!"
    )
    await update.message.reply_text(txt, parse_mode="Markdown", reply_markup=main_menu_keyboard())

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

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "open_menu":
        txt = (
            "⚙️ **منوی تنظیمات**\n\n"
            "از اینجا می‌تونی تنظیمات ربات رو تغییر بدی:\n"
            "• 📊 کیفیت دانلود\n"
            "• 🔔 اعلان‌ها\n"
            "• 🎨 تم رابط کاربری\n\n"
            "💡 **درباره ربات:**\n"
            "ربات اختصاصی دانلود اینستاگرام با بالاترین کیفیت و سرعت ⚡️"
        )
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=settings_keyboard())
    elif q.data == "back_main":
        txt = (
            "🎬 **ربات دانلود اینستاگرام**\n\n"
            "👇 لینک ریلز یا پست اینستاگرام رو بفرست تا با بهترین کیفیت برات دانلودش کنم ✨\n\n"
            "🔹 `https://www.instagram.com/reel/...`\n\n"
            "📦 چند لینک رو همزمان بفرست تا همه رو بگیری!"
        )
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=main_menu_keyboard())
    elif q.data == "set_quality":
        await q.answer("📊 کیفیت روی «بهترین» تنظیم شد (پیش‌فرض)", show_alert=True)
    elif q.data == "toggle_notif":
        await q.answer("🔔 اعلان‌ها تغییر کرد", show_alert=True)
    elif q.data == "set_theme":
        await q.answer("🎨 تم تغییر کرد", show_alert=True)

async def send_one_video(update: Update, url: str, index: int, total: int):
    """دانلود و ارسال یک ویدیو اینستاگرام"""
    status = await update.message.reply_text(f"⏳ **({index}/{total}) در حال دانلود...**\nلطفاً صبر کن 🎥", parse_mode="Markdown")
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
    urls = extract_instagram_urls(text)
    if not urls:
        await update.message.reply_text("❌ **فقط لینک اینستاگرام قبوله!**\nمثلاً:\n`https://www.instagram.com/reel/...`", parse_mode="Markdown")
        return

    if len(urls) > 1:
        await update.message.reply_text(f"🔢 **{len(urls)} لینک پیدا شد!**\nدر حال دانلود همه‌شون... ⏳", parse_mode="Markdown")

    for i, url in enumerate(urls, 1):
        await send_one_video(update, url, i, len(urls))

    if len(urls) > 1:
        await update.message.reply_text("✅ **همه ویدیوها آماده شد!**\n\n🤖 " + BOT_USERNAME, parse_mode="Markdown")

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
    application.add_handler(CallbackQueryHandler(menu_callback))
    logger.info("🚀 ربات با موفقیت بالا اومد!")
    application.run_polling()

if __name__ == "__main__":
    main()
