import os
import re
import logging
import asyncio
import yt_dlp
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN='7651648073:AAEYmoldWDZOaV4VI8bVlO2cJrd8IGOu294'
BOT_USERNAME = "@Danloderebot"

def extract_instagram_urls(text: str) -> list:
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

def get_media(url: str, tag: str) -> list:
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
        logger.error(f"media error: {e}")
    return files

def build_caption(info) -> str:
    if not info:
        return f"🤖 {BOT_USERNAME}"
    desc = (info.get('description') or '').strip()
    title = (info.get('title') or '').strip()
    if desc:
        clean = desc.replace('\n', ' ').strip()
        if len(clean) > 400:
            clean = clean[:400] + '...'
        return f"📝 {clean}\n\n🤖 {BOT_USERNAME}"
    elif title and not title.startswith('Video by'):
        return f"📝 {title[:400]}\n\n🤖 {BOT_USERNAME}"
    return f"🤖 {BOT_USERNAME}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 **ربات دانلود اینستاگرام**\n\n"
        "فقط لینک ریلز یا پست اینستاگرام رو بفرست تا فایل + کپشن رو برات بفرستم ✨\n\n"
        "🔹 `https://www.instagram.com/reel/...`",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    urls = extract_instagram_urls(text)
    if not urls:
        await update.message.reply_text("❌ فقط لینک اینستاگرام قبوله.")
        return

    for url in urls:
        status = await update.message.reply_text("⏳ در حال دانلود... لطفاً صبر کن 🎥")
        info = await asyncio.to_thread(get_info, url)
        files = await asyncio.to_thread(get_media, url, 'dl')
        if not files:
            await status.edit_text("❌ دانلود نشد! لینک رو چک کن.")
            continue
        caption = build_caption(info)
        try:
            if len(files) == 1:
                ext = os.path.splitext(files[0])[1].lower()
                with open(files[0], 'rb') as fh:
                    if ext in ('.jpg', '.jpeg', '.png', '.webp'):
                        await update.message.reply_photo(photo=fh, caption=caption, parse_mode="Markdown")
                    else:
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
                if caption:
                    await update.message.reply_text(caption, parse_mode="Markdown")
            await status.delete()
        except Exception as e:
            await status.edit_text(f"❌ خطا: {str(e)[:100]}")

def main():
    os.makedirs('downloads', exist_ok=True)
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🚀 ربات بالا اومد!")
    application.run_polling()

if __name__ == "__main__":
    main()
