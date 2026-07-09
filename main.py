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

def get_info(url: str) -> dict | None:
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        logger.error(f"info error: {e}")
        return None

def get_audio(url: str, tag: str) -> str | None:
    """استخراج صدای ویدیو به MP3 (نیاز به ffmpeg)"""
    outtmpl = f'downloads/{tag}_%(id)s.%(ext)s'
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': outtmpl,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': '/usr/local/bin',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
    }
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        ydl_opts['ffmpeg_location'] = ffmpeg_exe
    except Exception:
        pass
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            fn = ydl.prepare_filename(info)
            base = os.path.splitext(fn)[0] + '.mp3'
            if os.path.exists(base):
                return base
            for f in os.listdir('downloads'):
                if f.startswith(tag) and f.endswith('.mp3'):
                    return os.path.join('downloads', f)
    except Exception as e:
        logger.error(f"audio error: {e}")
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

def find_song_youtube(query: str) -> str | None:
    """جستجو و دانلود آهنگ از یوتیوب (با کوکی اگه موجود باشه)"""
    if not query:
        return None
    cookie_opt = {'cookiefile': 'cookies.txt'} if os.path.exists('cookies.txt') else {}
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/song_%(id)s.%(ext)s',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        **cookie_opt,
    }
    for q in [query, f"{query} official audio", f"{query} song"]:
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
            logger.error(f"yt search '{q}': {e}")
    return None

async def recognize_song(audio_path: str) -> dict | None:
    """تشخیص آهنگ از روی صدا با shazamio"""
    try:
        from shazamio import Shazam
        shazam = Shazam()
        out = await shazam.recognize(audio_path)
        track = out.get('track', {})
        title = track.get('title')
        artist = track.get('subtitle') or (track.get('artists') or [{}])[0].get('name')
        if title:
            return {'title': title, 'artist': artist or ''}
    except Exception as e:
        logger.error(f"shazam: {e}")
    return None

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

def action_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton("🟢 پیدا کردن آهنگ کلیپ", callback_data="find_song")],
        [InlineKeyboardButton("🎵 دانلود صدا (MP3)", callback_data="get_mp3")],
    ]
    return InlineKeyboardMarkup(kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "🎬 **ربات دانلود اینستاگرام**\n\n"
        "👇 لینک ریلز یا پست اینستاگرام رو بفرست تا با بهترین کیفیت برات دانلودش کنم\n\n"
        "✨ **قابلیت‌ها:**\n"
        "• 🎬 دانلود بهترین کیفیت\n"
        "• 🖼️ پشتیبانی از پست‌های چندتایی\n"
        "• 🎵 دانلود صدای MP3\n"
        "• 🟢 تشخیص و دانلود آهنگ کلیپ (از روی صدا)\n\n"
        "🔹 `https://www.instagram.com/reel/...`"
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    m = re.search(r'(https?://)?(www\.)?(instagram\.com|instagr\.am)/(p|reel|tv)/([A-Za-z0-9_-]+)', text)
    if not m:
        await update.message.reply_text("❌ **فقط لینک اینستاگرام قبوله!**\nمثلاً:\n`https://www.instagram.com/reel/...`", parse_mode="Markdown")
        return

    url = m.group(0)
    if not url.startswith('http'):
        url = 'https://' + url

    status = await update.message.reply_text("🔍 **در حال دریافت اطلاعات...**", parse_mode="Markdown")
    info = await asyncio.to_thread(get_info, url)
    if not info:
        await status.edit_text("❌ **لینک نامعتبره یا دانلود نشد!**", parse_mode="Markdown")
        return

    context.user_data['url'] = url
    context.user_data['info'] = info

    await status.edit_text("⏳ **در حال دانلود با بهترین کیفیت...**\nلطفاً صبر کن 🎥", parse_mode="Markdown")
    files = await asyncio.to_thread(get_video, url, 'dl')

    if not files:
        await status.edit_text("❌ **دانلود نشد!** لینک رو چک کن یا دوباره امتحان کن.", parse_mode="Markdown")
        return

    caption = build_caption(info)
    try:
        if len(files) == 1:
            with open(files[0], 'rb') as fh:
                await update.message.reply_video(video=fh, supports_streaming=True, caption=caption, reply_markup=action_keyboard(), parse_mode="Markdown")
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
            await update.message.reply_text("✅ **آلبوم آماده شد!**\n\nبرای آهنگ/صدا از دکمه‌ها استفاده کن.", reply_markup=action_keyboard(), parse_mode="Markdown")
        await status.delete()
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارسال: {str(e)[:120]}")

async def get_mp3_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data != "get_mp3":
        return
    url = context.user_data.get('url')
    if not url:
        await q.message.reply_text("❌ اول یه ویدیو دانلود کن.")
        return
    status = await q.message.reply_text("🎵 **در حال استخراج صدا...**\n⏳ لطفاً صبر کن", parse_mode="Markdown")
    mp3 = await asyncio.to_thread(get_audio, url, 'mp3')
    if not mp3:
        await status.edit_text("❌ استخراج صدا ناموفق بود.", parse_mode="Markdown")
        return
    try:
        with open(mp3, 'rb') as fh:
            await q.message.reply_audio(audio=fh, caption=f"🎵 **صدای ویدیو**\n\n🤖 {BOT_USERNAME}")
        os.remove(mp3)
        await status.edit_text("✅ **صدای ویدیو ارسال شد!** 🎵", parse_mode="Markdown")
    except Exception as e:
        await status.edit_text(f"❌ خطا: {str(e)[:100]}", parse_mode="Markdown")

async def find_song_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data != "find_song":
        return
    url = context.user_data.get('url')
    if not url:
        await q.message.reply_text("❌ اول یه ویدیو دانلود کن.")
        return
    status = await q.message.reply_text("🟢 **در حال تشخیص آهنگ از روی صدا...**\n🎧 لطفاً صبر کن (۵-۱۰ ثانیه) ⏳", parse_mode="Markdown")

    audio = await asyncio.to_thread(get_audio, url, 'rec')
    if not audio:
        await status.edit_text("❌ نتونستم صدای ویدیو رو دانلود کنم.", parse_mode="Markdown")
        return

    song = await recognize_song(audio)
    if audio and os.path.exists(audio):
        try:
            os.remove(audio)
        except:
            pass

    if not song:
        await status.edit_text("❌ نتونستم آهنگ رو از روی صدا تشخیص بدم. احتمالاً موزیک اصلی نیست.", parse_mode="Markdown")
        return

    song_name = f"{song['title']} - {song['artist']}".strip(' -')
    await status.edit_text(f"🟢 **آهنگ پیدا شد!** 🎵\n\n**{song_name}**\n\n⏳ در حال دانلود آهنگ...", parse_mode="Markdown")

    mp3 = await asyncio.to_thread(find_song_youtube, song_name)
    if mp3:
        try:
            with open(mp3, 'rb') as fh:
                await q.message.reply_audio(audio=fh, title=song['title'][:64], performer=song.get('artist', '')[:64], caption=f"🎵 **{song_name}**\n\n🤖 {BOT_USERNAME}")
            os.remove(mp3)
            await status.edit_text(f"✅ **آهنگ دانلود و ارسال شد!** 🎵\n\n🤖 {BOT_USERNAME}", parse_mode="Markdown")
            return
        except Exception as e:
            logger.error(f"send song: {e}")

    import urllib.parse
    qs = urllib.parse.quote(song_name)
    kb = [
        [InlineKeyboardButton("🟢 Spotify", url=f"https://open.spotify.com/search/{qs}")],
        [InlineKeyboardButton("🟢 YouTube Music", url=f"https://music.youtube.com/search?q={qs}")],
        [InlineKeyboardButton("🟢 Google", url=f"https://www.google.com/search?q={qs}+song")],
    ]
    await status.edit_text(
        f"🟢 **آهنگ تشخیص داده شد:** `{song_name}`\n\n🔍 دانلود خودکار لغو شد (نیاز به کوکی یوتیوب). از لینک‌ها دانلود کن:",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )

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
    application.add_handler(CallbackQueryHandler(get_mp3_cb, pattern="^get_mp3$"))
    application.add_handler(CallbackQueryHandler(find_song_cb, pattern="^find_song$"))
    logger.info("🚀 ربات با موفقیت بالا اومد!")
    application.run_polling()

if __name__ == "__main__":
    main()
