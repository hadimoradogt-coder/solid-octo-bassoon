import os, re, logging, yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN='7651648073:AAFcKGDQC7gkQBr8e-SG78gu0kQ8DH1dcs0'
ADMIN_USER_ID = 5080529808

def find_file(id_or_url: str) -> str | None:
    if not os.path.exists('downloads'): return None
    for f in os.listdir('downloads'):
        if id_or_url in f and not f.endswith('.part'):
            return os.path.join('downloads', f)
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📖 راهنما", callback_data="help")]]
    await update.message.reply_text(
        f"🎬 **سلام {update.effective_user.first_name} جان!**\n"
        f"به ربات دانلود اینستاگرام خوش اومدی 🚀\n\n"
        f"📹 دانلود ریلز و پست‌ها\n🎵 استخراج صدا\n📊 نمایش اطلاعات\n\n"
        f"🔗 **فقط لینک اینستاگرام رو بفرست:**\n`https://www.instagram.com/reel/...`",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def help_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("📖 **راهنما**\n\n1️⃣ لینک بفرست\n2️⃣ اطلاعات نمایش داده میشه\n3️⃣ کیفیت رو انتخاب کن\n4️⃣ فایل آماده‌ست 🎉", parse_mode="Markdown")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    match = re.search(r'(https?://)?(www\.)?(instagram\.com|instagr\.am)/(p|reel|tv)/([A-Za-z0-9_-]+)', text)
    if match:
        url = match.group(0)
        if not url.startswith('http'): url = 'https://' + url
        context.user_data['url'] = url
        msg = await update.message.reply_text("🔍 **در حال دریافت اطلاعات...**", parse_mode="Markdown")
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            await msg.edit_text(f"❌ **خطا در دریافت اطلاعات:**\n`{str(e)[:120]}`", parse_mode="Markdown")
            return
        dur = info.get('duration', 0)
        dur = f"{dur//60}:{dur%60:02d}" if dur else "نامشخص"
        views = info.get('view_count', 0)
        views = f"{views/1000:.0f}K" if views >= 1000 else views
        info_text = (f"✅ **اطلاعات ویدیو**\n\n📹 {str(info.get('title',''))[:80]}\n"
                     f"👤 {info.get('uploader','ناشناس')}\n⏱ {dur}\n👁 {views}\n\n"
                     f"🔽 **کیفیت رو انتخاب کن:**")
        await msg.delete()
        keyboard = [[InlineKeyboardButton("🎬 1080p", callback_data="q_best"),
                     InlineKeyboardButton("📺 720p", callback_data="q_med")],
                    [InlineKeyboardButton("📱 480p", callback_data="q_low"),
                     InlineKeyboardButton("🎵 صدا", callback_data="q_audio")],
                    [InlineKeyboardButton("❌ لغو", callback_data="cancel")]]
        await update.message.reply_text(info_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ لطفاً یه لینک اینستاگرام بفرست.")

async def quality_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "cancel":
        await q.edit_message_text("❌ لغو شد."); return
    url = context.user_data.get('url')
    if not url:
        await q.edit_message_text("❌ دوباره لینک بفرست."); return
    qmap = {'q_best': 'best', 'q_med': 'best[height<=720]', 'q_low': 'best[height<=480]', 'q_audio': 'bestaudio'}
    qname = {'q_best': '🎬 1080p', 'q_med': '📺 720p', 'q_low': '📱 480p', 'q_audio': '🎵 صدا'}
    vid_id = re.search(r'/([A-Za-z0-9_-]+)/?$', url)
    vid_id = vid_id.group(1) if vid_id else 'video'
    await q.edit_message_text(f"⏳ **در حال دانلود...**\nکیفیت: {qname[q.data]}", parse_mode="Markdown")
    ydl_opts = {'quiet': True, 'noplaylist': True, 'outtmpl': f'downloads/{vid_id}.%(ext)s', 'format': qmap[q.data]}
    if q.data == 'q_audio':
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        await q.edit_message_text(f"❌ **خطا در دانلود:**\n`{str(e)[:150]}`", parse_mode="Markdown")
        return
    filename = find_file(vid_id)
    if not filename:
        await q.edit_message_text("❌ فایل پیدا نشد، دوباره امتحان کن."); return
    await q.edit_message_text("📤 **در حال ارسال...**", parse_mode="Markdown")
    try:
        ext = os.path.splitext(filename)[1].lower()
        with open(filename, 'rb') as f:
            if ext in ('.mp3','.m4a','.ogg'): await q.message.reply_audio(audio=f)
            elif ext in ('.jpg','.jpeg','.png','.webp'): await q.message.reply_photo(photo=f)
            elif ext in ('.mp4','.mov','.webm'): await q.message.reply_video(video=f, supports_streaming=True)
            else: await q.message.reply_document(document=f)
        os.remove(filename)
    except Exception as e:
        await q.message.reply_text(f"❌ خطا در ارسال: {str(e)[:120]}")
    await q.edit_message_text("✅ **دانلود کامل شد!** 🙏", parse_mode="Markdown")

def main():
    os.makedirs('downloads', exist_ok=True)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_handler(CallbackQueryHandler(quality_cb, pattern="^q_|^cancel$"))
    app.add_handler(CallbackQueryHandler(help_cb, pattern="^help$"))
    logger.info("✅ ربات فعال شد!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
