import os
import logging
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN='7651648073:AAEYmoldWDZOaV4VI8bVlO2cJrd8IGOu294'
ADMIN_USER_ID = 5080529808

SHAD_API_URL = ""
SHAD_HEADERS = {}
SHAD_CHANNEL_ID = ""

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
        [InlineKeyboardButton("🎵 پیدا کردن آهنگ کلیپ", url="https://shazam.com")],
        [InlineKeyboardButton("👤 ارتباط با سازنده", url=f"https://t.me/{CREATOR_USERNAME.lstrip('@')}")],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("🔐 آپلود به شاد", callback_data="shad_upload")])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_admin = update.effective_user.id == ADMIN_USER_ID
    txt = ("🎬 **ربات دانلود اینستاگرام**\n\n👇 لینک ریلز اینستاگرام رو بفرست تا برات دانلودش کنم\n\n🔹 `https://www.instagram.com/reel/...`\n\n✨ سریع و با بهترین کیفیت 🚀")
    if is_admin:
        txt += "\n\n🔐 *(شما ادمین هستید - دکمه آپلود به شاد برات فعاله)*"
    await update.message.reply_text(txt, parse_mode="Markdown")

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
            context.user_data['last_caption'] = caption
        else:
            await status_msg.edit_text("❌ **دانلود نشد!**\nلینک رو چک کن یا دوباره امتحان کن.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ **فقط لینک ریلز اینستاگرام قبوله!**\nمثلاً:\n`https://www.instagram.com/reel/...`", parse_mode="Markdown")

async def shad_upload_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data != "shad_upload":
        return
    if update.effective_user.id != ADMIN_USER_ID:
        await q.edit_message_text("❌ دسترسی نداری.")
        return
    if not SHAD_API_URL:
        await q.edit_message_text("⚠️ **بخش شاد فعلاً ست نشده!**\n\nوقتی API شاد رو از DevTools گرفتی، اینجا پر می‌کنم.\nفعلاً ویدیو دانلود شده آماده‌ست 🙏", parse_mode="Markdown")
        return
    filename = context.user_data.get('last_file')
    if not filename or not os.path.exists(filename):
        await q.edit_message_text("❌ فایلی برای آپلود نداری. اول یه ویدیو دانلود کن.")
        return
    await q.edit_message_text("⏳ **در حال آپلود به شاد...**", parse_mode="Markdown")
    try:
        import requests
        with open(filename, 'rb') as f:
            r = requests.post(SHAD_API_URL, headers=SHAD_HEADERS, files={'file': f}, data={'chat_id': SHAD_CHANNEL_ID}, timeout=60)
        if r.status_code == 200:
            await q.edit_message_text("✅ **با موفقیت به شاد آپلود شد!** 🚀", parse_mode="Markdown")
        else:
            await q.edit_message_text(f"❌ خطای شاد: `{r.status_code}`", parse_mode="Markdown")
    except Exception as e:
        await q.edit_message_text(f"❌ خطا در آپلود شاد:\n`{str(e)[:120]}`", parse_mode="Markdown")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

def main():
    os.makedirs('downloads', exist_ok=True)
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(shad_upload_callback, pattern="^shad_upload$"))
    logger.info("🚀 ربات با موفقیت بالا اومد!")
    application.run_polling()

if __name__ == "__main__":
    main()
