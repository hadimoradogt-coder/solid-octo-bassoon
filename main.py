import os, re, logging, yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN='7651648073:AAFcKGDQC7gkQBr8e-SG78gu0kQ8DH1dcs0'
ADMIN_USER_ID = 5080529808

async def download_instagram(url: str) -> dict:
    ydl_opts = {'quiet': True, 'noplaylist': True, 'outtmpl': 'downloads/%(id)s.%(ext)s',
                'format': 'best[ext=mp4]/best'}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base, ext = os.path.splitext(filename)
            if not ext or ext == '.m4a':
                for f in os.listdir('downloads/'):
                    if info.get('id') in f:
                        filename = os.path.join('downloads', f); break
            return {'title': info.get('title','')[:80], 'uploader': info.get('uploader','ناشناس'),
                    'duration': info.get('duration',0), 'view_count': info.get('view_count',0),
                    'files': [filename] if os.path.exists(filename) else []}
    except Exception as e:
        return {'error': str(e), 'files': []}

def fmt_dur(s):
    if not s: return "نامشخص"
    m, s = divmod(s, 60); h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def fmt_num(n):
    if not n: return "0"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return str(n)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📖 راهنما", callback_data="help")]]
    await update.message.reply_text(
        f"🎬 **سلام {update.effective_user.first_name} جان!**\n"
        f"به ربات دانلود اینستاگرام خوش اومدی 🚀\n\n"
        f"📹 دانلود ریلز و پست‌ها\n🎵 استخراج صدا\n📊 نمایش اطلاعات\n\n"
        f"🔗 **فقط لینک اینستاگرام رو بفرست:**\n"
        f"`https://www.instagram.com/reel/...`",
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
        result = await download_instagram(url)
        if result.get('error'):
            await msg.edit_text(f"❌ **خطا**\n`{result['error'][:100]}`\nدوباره تلاش کن.", parse_mode="Markdown"); return
        info = (f"✅ **اطلاعات ویدیو**\n\n📹 {result.get('title','')}\n"
                f"👤 {result.get('uploader','')}\n⏱ {fmt_dur(result.get('duration',0))}\n"
                f"👁 {fmt_num(result.get('view_count',0))}\n\n🔽 **کیفیت رو انتخاب کن:**")
        await msg.delete()
        keyboard = [[InlineKeyboardButton("🎬 1080p", callback_data="q_best"),
                     InlineKeyboardButton("📺 720p", callback_data="q_med")],
                    [InlineKeyboardButton("📱 480p", callback_data="q_low"),
                     InlineKeyboardButton("🎵 صدا", callback_data="q_audio")],
[InlineKeyboardButton("❌ لغو", callback_data="cancel")]]
        await update.message.reply_text(info, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ لطفاً یه لینک اینستاگرام بفرست.")

async def quality_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "cancel": await q.edit_message_text("❌ لغو شد."); return
    url = context.user_data.get('url')
    if not url: await q.edit_message_text("❌ دوباره لینک بفرست."); return
    
    qmap = {'q_best': 'best', 'q_med': 'best[height<=720]', 'q_low': 'best[height<=480]', 'q_audio': 'bestaudio'}
    qname = {'q_best': '🎬 1080p', 'q_med': '📺 720p', 'q_low': '📱 480p', 'q_audio': '🎵 صدا'}
    fmt = qmap[q.data]
    await q.edit_message_text(f"⏳ **در حال دانلود...**\nکیفیت: {qname[q.data]}", parse_mode="Markdown")
    
    ydl_opts = {'quiet': True, 'noplaylist': True, 'outtmpl': 'downloads/%(id)s.%(ext)s', 'format': fmt}
    if q.data == 'q_audio':
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if q.data == 'q_audio': filename = filename.replace('.m4a','.mp3').replace('.webm','.mp3')
            elif not os.path.exists(filename):
                for f in os.listdir('downloads/'):
                    if info.get('id') in f: filename = os.path.join('downloads', f); break
    except Exception as e:
        await q.edit_message_text(f"❌ **خطا:** `{str(e)[:150]}`", parse_mode="Markdown"); return
    
    if not os.path.exists(filename): await q.edit_message_text("❌ فایل پیدا نشد."); return
    
    await q.edit_message_text("📤 **در حال ارسال...**", parse_mode="Markdown")
    try:
        ext = os.path.splitext(filename)[1].lower()
        is_audio = ext in ('.mp3','.m4a','.ogg'); is_image = ext in ('.jpg','.jpeg','.png'); is_video = ext in ('.mp4','.mov','.webm')
        with open(filename,'rb') as f:
            if is_audio: await q.message.reply_audio(audio=f)
            elif is_image: await q.message.reply_photo(photo=f)
            elif is_video: await q.message.reply_video(video=f)
            else: await q.message.reply_document(document=f)
        os.remove(filename)
    except Exception as e:
        await q.message.reply_text(f"❌ خطا: {str(e)[:100]}")
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
