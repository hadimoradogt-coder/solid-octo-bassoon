import os, re, logging, asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

BOT_TOKEN='7651648073:AAEYmoldWDZOaV4VI8bVlO2cJrd8IGOu294'
ADMIN_USER_ID = 5080529808

SHAD_API_URL = ""
SHAD_HEADERS = {}
SHAD_CHANNEL_ID = ""

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_admin = update.effective_user.id == ADMIN_USER_ID
    txt = ("🎬 **ربات دانلود اینستاگرام**\n\n📥 لینک ریلز یا پست اینستاگرام بفرست تا برات دانلود کنم.\n\n✨ قابلیت‌ها:\n• 📹 دانلود ریلز و پست\n• 🎵 استخراج صدا\n• 📊 نمایش اطلاعات\n")
    if is_admin:
        txt += "\n🔐 **شما ادمین هستید:** می‌تونی به شاد هم آپلود کنی."
    await update.message.reply_text(txt, parse_mode="Markdown")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    match = re.search(r'(https?://)?(www\.)?(instagram\.com|instagr\.am)/(p|reel|tv)/([A-Za-z0-9_-]+)', text)
    if not match:
        await update.message.reply_text("❌ لطفاً یه لینک اینستاگرام بفرست.")
        return
    url = match.group(0)
    if not url.startswith('http'): url = 'https://' + url
    context.user_data['url'] = url
    msg = await update.message.reply_text("🔍 **در حال دریافت اطلاعات...**", parse_mode="Markdown")
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        await msg.edit_text(f"❌ **خطا:**\n`{str(e)[:120]}`", parse_mode="Markdown")
        return
    dur = info.get('duration', 0); dur = f"{dur//60}:{dur%60:02d}" if dur else "نامشخص"
    views = info.get('view_count', 0); views = f"{views/1000:.0f}K" if views >= 1000 else views
    info_text = (f"✅ **اطلاعات ویدیو**\n\n📹 {str(info.get('title',''))[:80]}\n👤 {info.get('uploader','ناشناس')}\n⏱ {dur}\n👁 {views}\n\n🔽 **کیفیت رو انتخاب کن:**")
    keyboard = [[InlineKeyboardButton("🎬 1080p", callback_data="q_best"), InlineKeyboardButton("📺 720p", callback_data="q_med")],
                [InlineKeyboardButton("📱 480p", callback_data="q_low"), InlineKeyboardButton("🎵 صدا", callback_data="q_audio")]]
    if update.effective_user.id == ADMIN_USER_ID:
        keyboard.append([InlineKeyboardButton("🔐 آپلود به شاد", callback_data="shad")])
    keyboard.append([InlineKeyboardButton("❌ لغو", callback_data="cancel")])
    await msg.delete()
    await update.message.reply_text(info_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

def do_download(url: str, quality: str) -> str | None:
    fmt_map = {'best': 'best', 'med': 'best/best[height<=720]', 'low': 'best/best[height<=480]', 'audio': 'bestaudio'}
    ydl_opts = {'quiet': True, 'noplaylist': True, 'outtmpl': 'downloads/%(id)s.%(ext)s', 'format': fmt_map[quality]}
    if quality == 'audio':
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if quality == 'audio':
                base = os.path.splitext(filename)[0]; filename = base + '.mp3'
            if not os.path.exists(filename):
                vid_id = info.get('id', '')
                for f in os.listdir('downloads'):
                    if vid_id in f and not f.endswith('.part'):return os.path.join('downloads', f)
            return filename if os.path.exists(filename) else None
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None

async def quality_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "cancel":
        await q.edit_message_text("❌ لغو شد."); return
    if q.data == "shad":
        await shad_menu(update, context); return
    url = context.user_data.get('url')
    if not url:
        await q.edit_message_text("❌ دوباره لینک بفرست."); return
    qmap = {'q_best': 'best', 'q_med': 'med', 'q_low': 'low', 'q_audio': 'audio'}
    qname = {'q_best': '🎬 1080p', 'q_med': '📺 720p', 'q_low': '📱 480p', 'q_audio': '🎵 صدا'}
    await q.edit_message_text(f"⏳ **در حال دانلود...**\nکیفیت: {qname[q.data]}", parse_mode="Markdown")
    filename = await asyncio.to_thread(do_download, url, qmap[q.data])
    if not filename:
        await q.edit_message_text("❌ دانلود نشد. لینک رو چک کن یا دوباره امتحان کن."); return
    await q.edit_message_text("📤 **در حال ارسال...**", parse_mode="Markdown")
    try:
        ext = os.path.splitext(filename)[1].lower()
        with open(filename, 'rb') as f:
            if ext in ('.mp3','.m4a','.ogg'): await q.message.reply_audio(audio=f)
            elif ext in ('.jpg','.jpeg','.png','.webp'): await q.message.reply_photo(photo=f)
            elif ext in ('.mp4','.mov','.webm'): await q.message.reply_video(video=f, supports_streaming=True)
            else: await q.message.reply_document(document=f)
        context.user_data['last_file'] = filename
    except Exception as e:
        await q.message.reply_text(f"❌ خطا در ارسال: {str(e)[:120]}")
    if update.effective_user.id == ADMIN_USER_ID:
        kb = [[InlineKeyboardButton("🔐 آپلود به شاد", callback_data="shad")]]
        await q.message.reply_text("✅ **دانلود کامل شد!**\nبرای آپلود به شاد دکمه زیر رو بزن:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await q.edit_message_text("✅ **دانلود کامل شد!** 🙏", parse_mode="Markdown")

async def shad_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not SHAD_API_URL:
        await q.edit_message_text("⚠️ **API شاد تنظیم نشده!**\n\nاز بخش DevTools مرورگر این موارد رو پیدا کن:\n• POST Request URL\n• Headers (Authorization/Token/Cookie)\n• Body format\n\nبعد اینا رو بده تا ست کنم 🔧", parse_mode="Markdown"); return
    filename = context.user_data.get('last_file')
    if not filename or not os.path.exists(filename):
        await q.edit_message_text("❌ فایلی برای آپلود نداری. اول یه ویدیو دانلود کن."); return
    await q.edit_message_text("⏳ **در حال آپلود به شاد...**", parse_mode="Markdown")
    try:
        import requests
        with open(filename, 'rb') as f:
            r = requests.post(SHAD_API_URL, headers=SHAD_HEADERS, files={'file': f}, data={'chat_id': SHAD_CHANNEL_ID}, timeout=60)
        if r.status_code == 200:
            await q.edit_message_text("✅ **با موفقیت به شاد آپلود شد!** 🚀", parse_mode="Markdown")
        else:
            await q.edit_message_text(f"❌ خطای شاد: `{r.status_code}`\n{r.text[:100]}", parse_mode="Markdown")
    except Exception as e:
        await q.edit_message_text(f"❌ خطا در آپلود شاد:\n`{str(e)[:150]}`", parse_mode="Markdown")
    finally:
        if os.path.exists(filename): os.remove(filename)

def main():
    os.makedirs('downloads', exist_ok=True)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_handler(CallbackQueryHandler(quality_cb, pattern="^(q_|shad|cancel)$"))
    logger.info("✅ ربات فعال شد!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
