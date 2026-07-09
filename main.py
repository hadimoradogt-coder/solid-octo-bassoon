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

# ===== تنظیمات شاد (Shad) - از DevTools گرفته شد =====
SHAD_UPLOAD_URL = "https://upshst577.iranlms.ir/UploadFile.ashx"
SHAD_AUTH="qfqtlljdcwrdgiyiobgwqfrfpwkkbvms"
SHAD_ACCESS_HASH = "aroifvnrqcohdyssnrsdvafdgu7392"
SHAD_CHANNEL_ID = "c0CuNJ0e7c1dc95b06564d0663118ea3"   # آیدی کانال شاد (از لینک web.shad.ir/#c=)
SHAD_CHUNK = 131072    # 128 KB
SHAD_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
# ===================================================

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
                base = os.path.sitext(filename)[0]
                mp3 = base + '.mp3'
                if os.path.exists(mp3):
                    return mp3
                for f in os.listdir('downloads'):
                    if f.startswith('song_') and f.endswith('.mp3'):
                        return os.path.join('downloads', f)
    except Exception as e:
        logger.error(f"Song find error: {e}")
    return None

def upload_to_shad(filename: str) -> dict | None:
    """آپلود chunked به شاد - برمی‌گردونه dict {file_id, access_hash} یا None"""
    import requests, uuid
    try:
        file_size = os.path.getsize(filename)
        total_parts = (file_size + SHAD_CHUNK - 1) // SHAD_CHUNK
        file_id = str(uuid.uuid4().int)[:14]
        access_hash_rec = str(uuid.uuid4().hex)[:24]

        with open(filename, 'rb') as f:
            part_number = 1
            while True:
                chunk = f.read(SHAD_CHUNK)
                if not chunk:
                    break
                headers = {
                    'auth': SHAD_AUTH,
                    'access-hash-send': SHAD_ACCESS_HASH,
                    'file-id': file_id,
                    'access-hash-rec': access_hash_rec,
                    'part-number': str(part_number),
                    'total-part': str(total_parts),
                    'chunk-size': str(len(chunk)),
                    'content-type': 'application/octet-stream',
                    'origin': 'https://web.shad.ir',
                    'referer': 'https://web.shad.ir/',
                    'user-agent': SHAD_USER_AGENT,
                }
                r = requests.post(SHAD_UPLOAD_URL, headers=headers, data=chunk, timeout=60)
                if r.status_code != 200:
                    logger.error(f"Shad upload part {part_number} failed: {r.status_code} - {r.text[:100]}")
                    return None
                part_number += 1

        return {'file_id': file_id, 'access_hash': access_hash_rec}
    except Exception as e:
        logger.error(f"Shad upload error: {e}")
        return None

def send_to_shad_channel(file_id: str, access_hash: str) -> bool:
    """تلاش برای ارسال فایل آپلود شده به کانال شاد."""
    import requests, json
    payloads = [
        {'file_id': file_id, 'access_hash': access_hash, 'chat_id': SHAD_CHANNEL_ID, 'type': 'video'},
        {'file': {'file_id': file_id, 'access_hash': access_hash}, 'chat_id': SHAD_CHANNEL_ID, 'type': 'video'},
    ]
    endpoints = [
        "https://api.shad.ir/v2/sendMessage",
        "https://api.shad.ir/sendMessage",
        "https://upshst577.iranlms.ir/sendMessage.ashx",
    ]
    headers = {
        'auth': SHAD_AUTH,
        'access-hash-send': SHAD_ACCESS_HASH,
        'content-type': 'application/json',
        'origin': 'https://web.shad.ir',
        'referer': 'https://web.shad.ir/',
        'user-agent': SHAD_USER_AGENT,
    }
    for ep in endpoints:
        for p in payloads:
            try:
                r = requests.post(ep, headers=headers, data=json.dumps(p), timeout=30)
                if r.status_code == 200:
                    logger.info(f"Shad send OK via {ep}: {r.text[:100]}")
                    return True
                else:
                    logger.warning(f"Shad send {ep} -> {r.status_code}: {r.text[:100]}")
            except Exception as e:
                logger.warning(f"Shad send {ep} error: {str(e)[:80]}")
    return False

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

def build_keyboard(is_admin: bool) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🟢 پیدا کردن آهنگ کلیپ", callback_data="find_song")],
        [InlineKeyboardButton("🔴 ارتباط با سازنده", url=f"https://t.me/{CREATOR_USERNAME.lstrip('@')}")],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("🔐 آپلود به شاد", callback_data="shad_upload")])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_admin = update.effective_user.id == ADMIN_USER_ID
    logger.info(f"User {update.effective_user.id} started bot. is_admin={is_admin}")
    txt = ("🎬 **ربات دانلود اینستاگرام**\n\n👇 لینک ریلز اینستاگرام رو بفرست تا برات دانلودش کنم\n\n🔹 `https://www.instagram.com/reel/...`\n\n✨ سریع و با بهترین کیفیت 🚀")
    if is_admin:
        txt += "\n\n🔐 *(شما ادمین هستید - دکمه آپلود به شاد برات فعاله)*"
    await update.message.reply_text(txt, parse_mode="Markdown")
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    role = "🔐 ادمین" if uid == ADMIN_USER_ID else "👤 کاربر عادی"
    await update.message.reply_text(f"🆔 آیدی تلگرام شما:\n`{uid}`\n\n{role}", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "instagram.com/reel/" in text or "instagram.com/p/" in text:
        is_admin = update.effective_user.id == ADMIN_USER_ID
        status_msg = await update.message.reply_text("⏳ **در حال دانلود ویدیو...**\nلطفاً صبر کن 🎥", parse_mode="Markdown")
        file_path, info = await download_instagram_reel(text)
        if file_path and os.path.exists(file_path):
            await status_msg.delete()
            caption = build_caption(info) if info else f"✅ **ویدیو آماده شد!**\n\n🤖 {BOT_USERNAME}"
            keyboard = build_keyboard(is_admin)
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

async def shad_upload_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data != "shad_upload":
        return
    if update.effective_user.id != ADMIN_USER_ID:
        await q.edit_message_text("❌ دسترسی نداری.")
        return
    filename = context.user_data.get('last_file')
    if not filename or not os.path.exists(filename):
    await q.edit_message_text("❌ فایلی برای آپلود نداری. اول یه ویدیو دانلود کن.")
        return

    await q.edit_message_text("⏳ **در حال آپلود به شاد...**\n📤 در حال ارسال تکه‌ها...", parse_mode="Markdown")

    import asyncio
    result = await asyncio.to_thread(upload_to_shad, filename)

    if not result:
        await q.edit_message_text("❌ آپلود به شاد ناموفق بود. لاگ رو چک کن.", parse_mode="Markdown")
        return

    if not SHAD_CHANNEL_ID:
        await q.edit_message_text(
            f"✅ **آپلود به فضای شاد انجام شد!** 🚀\n\n"
            f"📁 File ID: `{result['file_id']}`\n🔑 Access Hash: `{result['access_hash']}`\n\n"
            f"⚠️ آیدی کانال ست نشده.",
            parse_mode="Markdown"
        )
        return

    await q.edit_message_text("⏳ **آپلود شد! حالا دارم به کانال می‌فرستم...**", parse_mode="Markdown")
    sent = await asyncio.to_thread(send_to_shad_channel, result['file_id'], result['access_hash'])

    if sent:
        await q.edit_message_text("✅ **با موفقیت به کانال شاد آپلود شد!** 🚀", parse_mode="Markdown")
    else:
        try:
            if filename and os.path.exists(filename):
                await q.message.reply_video(video=open(filename, 'rb'),
                    caption=f"📤 **آپلود به شاد انجام شد!**\nفورواردش کن به کانال 🔄\n\n📁 File ID: `{result['file_id']}`")
        except Exception:
            pass
        await q.edit_message_text(
            f"✅ **آپلود به فضای شاد انجام شد!** 🚀\n\n"
            f"📁 File ID: `{result['file_id']}`\n🔑 Access Hash: `{result['access_hash']}`\n\n"
            f"⏳ ارسال خودکار به کانال فعلاً غیرفعاله (endpoint دقیق لازمه).\nویدیو رو برات فرستادم - فورواردش کن به کانال 🔄",
            parse_mode="Markdown"
        )

def main():
    os.makedirs('downloads', exist_ok=True)
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("myid", myid))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(find_song_callback, pattern="^find_song$"))
    application.add_handler(CallbackQueryHandler(shad_upload_callback, pattern="^shad_upload$"))
    logger.info("🚀 ربات با موفقیت بالا اومد!")
    application.run_polling()

if __name__ == "__main__":
    main()
