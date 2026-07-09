import os
import re
import logging
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN='7651648073:AAEYmoldWDZOaV4VI8bVlO2cJrd8IGOu294'
ADMIN_USER_ID = 5080529808

BOT_USERNAME = "@Danloderebot"
CREATOR_USERNAME = "@thehadimoradi"

async def download_instagram_reel(url: str) -> tuple:
    ydl_opts = {'format': 'best', 'outtmpl': 'downloads/%(id)s.%(ext)s', 'noplaylist': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                vid_id = info.get('id', '')
                for f in os.listdir('downloads'):
                    if vid_id in f and not f.endswith('.part'):
                        filename = os.path.join('downloads', f)
                        break
            return filename, info
    except Exception as e:
        logger.error(f"Download Error: {e}")
        return None, None

def extract_song_name(info) -> str | None:
    desc = (info.get('description') or '').strip()
    title = (info.get('title') or '').strip()
    patterns = [
        r'(?:آهنگ|موزیک|song|music|track)\s*[:\-]\s*([^\n]+)',
        r'🎵\s*([^\n]+)',
    ]
    text = desc or title
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:80]
    if desc:
        words = desc.replace('\n', ' ').split()
        return ' '.join(words[:10])[:80]
    return None

def find_song(song_query: str) -> str | None:
    """جستجو و دانلود صدای آهنگ از یوتیوب (با کوکی اگه موجود باشه)"""
    if not song_query:
        return None
    cookie_opt = {'cookiefile': 'cookies.txt'} if os.path.exists('cookies.txt') else {}
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/song_%(id)s.%(ext)s',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
        'default_search': 'ytsearch1',
        **cookie_opt,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{song_query}", download=True)
            if info.get('entries'):
                entry = info['entries'][0]
                filename = ydl.prepare_filename(entry)
                base = os.path.splitext(filename)[0]
                mp3 = base + '.mp3'
                if os.path.exists(mp3):
                    return mp3
                for f in os.listdir('downloads'):
                    if f.startswith('song_') and f.endswith('.mp3'):
                        return os.path.join('downloads', f)
    except Exception as e:
        logger.error(f"Song find error: {e}")
    return None

def build_caption(info) -> str:
    parts = []
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

def build_keyboard() -> InlineKeyboardMarkup:
    """دکمه‌ها: 🟢 پیدا کردن آهنگ، 🔴 ارتباط با سازنده"""
    keyboard = [
        [InlineKeyboardButton("🟢 پیدا کردن آهنگ کلیپ", callback_data="find_song")],
        [InlineKeyboardButton("🔴 ارتباط با سازنده", url=f"https://t.me/{CREATOR_USERNAME.lstrip('@')}")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = ("🎬 **ربات دانلود اینستاگرام**\n\n👇 لینک ریلز اینستاگرام رو بفرست تا برات دانلودش کنم\n\n🔹 `https://www.instagram.com/reel/...`\n\n✨ سریع و با بهترین کیفیت 🚀")
    await update.message.reply_text(txt, parse_mode="Markdown")

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    role = "🔐 ادمین" if uid == ADMIN_USER_ID else "👤 کاربر عادی"
    await update.message.reply_text(f"🆔 آیدی تلگرام شما:\n`{uid}`\n\n{role}", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "instagram.com/reel/" in text or "instagram.com/p/" in text:
        status_msg = await update.message.reply_text("⏳ **در حال دانلود ویدیو...**\nلطفاً صبر کن 🎥", parse_mode="Markdown")
        file_path, info = await download_instagram_reel(text)
        if file_path and os.path.exists(file_path):
            await status_msg.delete()
            caption = build_caption(info) if info else f"✅ **ویدیو آماده شد!**\n\n🤖 {BOT_USERNAME}"
            keyboard = build_keyboard()
            await update.message.reply_video(video=open(file_path, 'rb'), caption=caption, reply_markup=keyboard, parse_mode="Markdown")
            context.user_data['last_file'] = file_path
            context.user_data['last_info'] = info
            context.user_data['last_caption'] = caption
        else:
            await status_msg.edit_text("❌ **دانلود نشد!**\nلینک رو چک کن یا دوباره امتحان کن.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ **فقط لینک ریلز اینستاگرام قبوله!**\nمثلاً:\n`https://www.instagram.com/reel/...`", parse_mode="Markdown")

async def find_song_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data != "find_song":
        return
    info = context.user_data.get('last_info')
    if not info:
        await q.edit_message_text("❌ اول یه ویدیو دانلود کن تا آهنگش رو پیدا کنم.")
        return
    desc = (info.get('description') or '').strip()
    title = (info.get('title') or '').strip()
    clip_text = desc or title
    if not clip_text:
        await q.edit_message_text("❌ متنی توی ویدیو پیدا نشد که بتونم جستجو کنم.")
        return
    song_name = extract_song_name(info) or clip_text[:80]
    await q.edit_message_text(
        f"🟢 **در حال جستجوی آهنگ...**\n🎵 `{song_name}`\n\n⏳ لطفاً صبر کن، دارم دانلودش می‌کنم...",
        parse_mode="Markdown"
    )
    import asyncio, urllib.parse
    filename = await asyncio.to_thread(find_song, song_name)
    if filename:
        try:
            await q.message.reply_audio(audio=open(filename, 'rb'), title=song_name[:64], caption=f"🎵 **{song_name}**\n\n🤖 {BOT_USERNAME}")
            os.remove(filename)
            await q.edit_message_text(f"✅ **آهنگ پیدا و ارسال شد!** 🎵\n\n🤖 {BOT_USERNAME}", parse_mode="Markdown")
            return
        except Exception as e:
            logger.error(f"Send song error: {e}")
    q_song = urllib.parse.quote(song_name)
    q_text = urllib.parse.quote(clip_text[:200])
    keyboard = [
        [InlineKeyboardButton("🟢 جستجوی آهنگ در Spotify", url=f"https://open.spotify.com/search/{q_song}")],
        [InlineKeyboardButton("🟢 جستجوی آهنگ در Google", url=f"https://www.google.com/search?q={q_song}+song")],
        [InlineKeyboardButton("🟢 جستجوی متن کلیپ در Google", url=f"https://www.google.com/search?q={q_text}")],
    ]
    await q.edit_message_text(
        f"🟢 **متن کلیپ استخراج شد:**\n`{clip_text[:200]}`\n\n🎵 **آهنگ احتمالی:** `{song_name}`\n\n🔍 دانلود خودکار لغو شد (نیاز به کوکی). برای پیدا کردن روی یه مورد بزن:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

def main():
    os.makedirs('downloads', exist_ok=True)
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("myid", myid))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(find_song_callback, pattern="^find_song$"))
    logger.info("🚀 ربات با موفقیت بالا اومد!")
    application.run_polling()

if __name__ == "__main__":
    main()
