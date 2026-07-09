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

# نقشه کیفیت‌ها
QUALITY_MAP = {
    'q_1080': ('best', '🎬 ۱۰۸۰'),
    'q_720':  ('best/best[height<=720]', '📺 ۷۲۰'),
    'q_480':  ('best/best[height<=480]', '📱 ۴۸۰'),
    'q_mp3':  ('bestaudio', '🎵 MP3'),
}

def download_media(url: str, quality_key: str, tag: str) -> list:
    """دانلود با کیفیت انتخابی. برمی‌گردونه لیست مسیر فایل‌ها."""
    fmt, label = QUALITY_MAP.get(quality_key, ('best', 'ویدیو'))
    is_audio = (quality_key == 'q_mp3')
    outtmpl = f'downloads/{tag}_%(id)s_%(playlist_index)02d.%(ext)s' if not is_audio else f'downloads/{tag}_%(id)s.%(ext)s'
    ydl_opts = {
        'format': fmt,
        'outtmpl': outtmpl,
        'noplaylist': False,   # برای آلبوم‌های چندتایی
        'quiet': True,
        'no_warnings': True,
    }
    if is_audio:
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]
    files = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # اگر آلبوم چندتایی باشه
            entries = info.get('entries')
            if entries:
                for e in entries:
                    if not e:
                        continue
                    fn = ydl.prepare_filename(e)
                    if is_audio:
                        base = os.path.splitext(fn)[0] + '.mp3'
                        if os.path.exists(base):
                            files.append(base)
                    elif os.path.exists(fn):
                        files.append(fn)
                    else:
                        # جستجوی فایل مشابه
                        vid = e.get('id', '')
                        for f in os.listdir('downloads'):
                            if tag in f and vid[:6] in f and not f.endswith('.part'):
                                files.append(os.path.join('downloads', f))
                                break
            else:
                fn = ydl.prepare_filename(info)
                if is_audio:
                    base = os.path.splitext(fn)[0] + '.mp3'
                    if os.path.exists(base):
                        files.append(base)
                elif os.path.exists(fn):
                    files.append(fn)
                else:
                    vid = info.get('id', '')
                    for f in os.listdir('downloads'):
                        if tag in f and vid[:6] in f and not f.endswith('.part'):
                            files.append(os.path.join('downloads', f))
                            break
    except Exception as e:
        logger.error(f"Download error ({quality_key}): {e}")
    return files

def extract_song_name(info) -> str | None:
    desc = (info.get('description') or '').strip()
    title = (info.get('title') or '').strip()
    patterns = [
        r'(?:آهنگ|موزیک|song|music|track|نوحه|مداحی|سرود)\s*[:\-]\s*([^\n]+)',
        r'🎵\s*([^\n]+)',
        r'(?:by|از)\s*[:\-]?\s*([^\n]+)',
    ]
    text = desc or title
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:80]
    if desc:
        # برداشتن اولین خط معنادار
        for line in desc.split('\n'):
            line = line.strip()
            if len(line) > 3 and not line.startswith('http'):
                return line[:80]
    return None

def find_song(query: str) -> str | None:
    """جستجوی دقیق و دانلود صدای آهنگ از یوتیوب (با کوکی اگه موجود باشه)"""
    if not query:
        return None
    cookie_opt = {'cookiefile': 'cookies.txt'} if os.path.exists('cookies.txt') else {}
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/song_%(id)s.%(ext)s',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
        **cookie_opt,
    }
    queries = [query, f"{query} official audio", f"{query} song"]
    for q in queries:
        ydl_opts['default_search'] = f"ytsearch1:{q}"
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{q}", download=True)
                if info.get('entries'):
                    entry = info['entries'][0]
                    fn = ydl.prepare_filename(entry)
                    base = os.path.splitext(fn)[0] + '.mp3'
                    if os.path.exists(base):
                        return base
                    for f in os.listdir('downloads'):
                        if f.startswith('song_') and f.endswith('.mp3'):
                            return os.path.join('downloads', f)
        except Exception as e:
            logger.error(f"Song search '{q}' failed: {e}")
            continue
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

def quality_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton("🎬 ۱۰۸۰p", callback_data="q_1080"),
            InlineKeyboardButton("📺 ۷۲۰p", callback_data="q_720"),
        ],
        [
            InlineKeyboardButton("📱 ۴۸۰p", callback_data="q_480"),
            InlineKeyboardButton("🎵 MP3 (صدا)", callback_data="q_mp3"),
        ],
        [InlineKeyboardButton("🟢 پیدا کردن آهنگ کلیپ", callback_data="find_song")],
        [InlineKeyboardButton("🔴 ارتباط با سازنده", url=f"https://t.me/{CREATOR_USERNAME.lstrip('@')}")],
    ]
    return InlineKeyboardMarkup(kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "🎬 **ربات دانلود اینستاگرام**\n\n"
        "👇 لینک ریلز یا پست اینستاگرام رو بفرست تا برات دانلودش کنم\n\n"
        "✨ **قابلیت‌ها:**\n"
        "• 📹 دانلود با کیفیت دلخواه (۱۰۸۰/۷۲۰/۴۸۰)\n"
        "• 🖼️ پشتیبانی از پست‌های چندتایی (آلبوم)\n"
        "• 🎵 استخراج صدای MP3\n"
        "• 🟢 پیدا کردن و دانلود آهنگ کلیپ\n\n"
        "🔹 `https://www.instagram.com/reel/...`"
    )
    await update.message.reply_text(txt, parse_mode="Markdown")

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(f"🆔 آیدی تلگرام شما:\n`{uid}`", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    # استخراج لینک اینستاگرام
    m = re.search(r'(https?://)?(www\.)?(instagram\.com|instagr\.am)/(p|reel|tv)/([A-Za-z0-9_-]+)', text)
    if not m:
        await update.message.reply_text("❌ **فقط لینک اینستاگرام قبوله!**\nمثلاً:\n`https://www.instagram.com/reel/...`", parse_mode="Markdown")
        return

    url = m.group(0)
    if not url.startswith('http'):
        url = 'https://' + url

    status = await update.message.reply_text("🔍 **در حال دریافت اطلاعات ویدیو...**", parse_mode="Markdown")
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        await status.edit_text(f"❌ **خطا در دریافت لینک:**\n`{str(e)[:120]}`", parse_mode="Markdown")
        return

    # ذخیره برای استفاده در دکمه‌ها
    context.user_data['url'] = url
    context.user_data['info'] = info

    # بررسی آلبوم
    is_album = bool(info.get('entries'))
    n = len(info.get('entries', [])) if is_album else 1
    media_type = "🖼️ آلبوم" if is_album else ("🎵 موزیک" if info.get('duration') is None else "🎬 ویدیو")

    dur = info.get('duration', 0)
    dur_s = f"{dur//60}:{dur%60:02d}" if dur else "—"
    views = info.get('view_count', 0)
    views_s = f"{views/1000:.0f}K" if views >= 1000 else str(views)

    info_text = (
        f"✅ **{media_type} آماده شد!**\n\n"
        f"👤 {info.get('uploader', 'ناشناس')}\n"
        f"⏱ {dur_s}  👁 {views_s}\n"
        f"📦 تعداد: {n} عدد\n\n"
        f"🔽 **کیفیت رو انتخاب کن:**"
    )
    await status.delete()
    await update.message.reply_text(info_text, reply_markup=quality_keyboard(), parse_mode="Markdown")

async def quality_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not q.data.startswith('q_'):
        return
    url = context.user_data.get('url')
    if not url:
        await q.edit_message_text("❌ دوباره لینک رو بفرست.")
        return
    label = QUALITY_MAP.get(q.data, ('best', 'ویدیو'))[1]
    await q.edit_message_text(f"⏳ **در حال دانلود...**\nکیفیت: {label}\nلطفاً صبر کن 🎥", parse_mode="Markdown")

    tag = 'dl'
    files = await asyncio.to_thread(download_media, url, q.data, tag)

    if not files:
        await q.edit_message_text("❌ **دانلود نشد!** لینک رو چک کن یا دوباره امتحان کن.", parse_mode="Markdown")
        return

    is_audio = (q.data == 'q_mp3')
    await q.edit_message_text("📤 **در حال ارسال...**", parse_mode="Markdown")
    try:
        if is_audio:
            for f in files:
                with open(f, 'rb') as fh:
                    await q.message.reply_audio(audio=fh, caption=f"🎵 {label}\n\n🤖 {BOT_USERNAME}")
                os.remove(f)
        elif len(files) == 1:
            with open(files[0], 'rb') as fh:
                await q.message.reply_video(video=fh, supports_streaming=True, caption=build_caption(context.user_data.get('info')), parse_mode="Markdown")
            os.remove(files[0])
        else:
            # آلبوم چندتایی
            media = []
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in ('.jpg', '.jpeg', '.png', '.webp'):
                    media.append(InputMediaPhoto(open(f, 'rb')))
                else:
                    media.append(InputMediaVideo(open(f, 'rb')))
            await q.message.reply_media_group(media)
            for f in files:
                os.remove(f)
        await q.edit_message_text("✅ **دانلود کامل شد!** 🙏", parse_mode="Markdown")
    except Exception as e:
        await q.message.reply_text(f"❌ خطا در ارسال: {str(e)[:120]}")

async def find_song_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data != "find_song":
        return
    info = context.user_data.get('info')
    if not info:
        await q.edit_message_text("❌ اول یه ویدیو دانلود کن تا آهنگش رو پیدا کنم.")
        return

    song = extract_song_name(info)
    if not song:
        await q.edit_message_text("❌ نتونستم نام آهنگ رو از کپشن پیدا کنم.")
        return

    await q.edit_message_text(f"🟢 **در حال جستجوی آهنگ...**\n🎵 `{song}`\n⏳ لطفاً صبر کن 🎧", parse_mode="Markdown")
    mp3 = await asyncio.to_thread(find_song, song)
    if mp3:
        try:
            with open(mp3, 'rb') as fh:
                await q.message.reply_audio(audio=fh, title=song[:64], caption=f"🎵 **{song}**\n\n🤖 {BOT_USERNAME}")
            os.remove(mp3)
            await q.edit_message_text(f"✅ **آهنگ پیدا و ارسال شد!** 🎵\n\n🤖 {BOT_USERNAME}", parse_mode="Markdown")
            return
        except Exception as e:
            logger.error(f"Send song error: {e}")

    # فال‌بک: لینک‌های جستجو
    import urllib.parse
    qs = urllib.parse.quote(song)
    kb = [
        [InlineKeyboardButton("🟢 Spotify", url=f"https://open.spotify.com/search/{qs}")],
        [InlineKeyboardButton("🟢 YouTube Music", url=f"https://music.youtube.com/search?q={qs}")],
        [InlineKeyboardButton("🟢 Google", url=f"https://www.google.com/search?q={qs}+song")],
    ]
    await q.edit_message_text(
        f"🟢 **آهنگ احتمالی:** `{song}`\n\n🔍 دانلود خودکار لغو شد (نیاز به کوکی یوتیوب). از لینک‌ها دانلود کن:",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )

def main():
    os.makedirs('downloads', exist_ok=True)
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("myid", myid))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(quality_cb, pattern="^q_"))
    application.add_handler(CallbackQueryHandler(find_song_cb, pattern="^find_song$"))
    logger.info("🚀 ربات با موفقیت بالا اومد!")
    application.run_polling()

if __name__ == "__main__":
    main()
