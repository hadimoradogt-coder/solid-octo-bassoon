import os
import logging
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN='7651648073:AAEYmoldWDZOaV4VI8bVlO2cJrd8IGOu294'
ADMIN_USER_ID = 5080529808

async def download_instagram_reel(url: str) -> str | None:
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except Exception as e:
        logger.error(f"Download Error: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 **ربات دانلود اینستاگرام**\n\n"
        "👇 لینک ریلز اینستاگرام رو بفرست تا برات دانلودش کنم\n\n"
        "🔹 `https://www.instagram.com/reel/...`\n\n"
        "✨ سریع و با بهترین کیفیت 🚀"
    , parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "instagram.com/reel/" in text or "instagram.com/p/" in text:
        status_msg = await update.message.reply_text("⏳ **در حال دانلود ویدیو...**\nلطفاً صبر کن 🎥", parse_mode="Markdown")
        file_path = await download_instagram_reel(text)
        if file_path and os.path.exists(file_path):
            await status_msg.delete()
            await update.message.reply_video(
                video=open(file_path, 'rb'),
                caption="✅ **ویدیو آماده شد!**\n\n📥 دانلود شده توسط ربات اینستاگرام 🤖"
            )
            os.remove(file_path)
        else:
            await status_msg.edit_text("❌ **دانلود نشد!**\nلینک رو چک کن یا دوباره امتحان کن.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ **فقط لینک ریلز اینستاگرام قبوله!**\nمثلاً:\n`https://www.instagram.com/reel/...`", parse_mode="Markdown")

def main():
    os.makedirs('downloads', exist_ok=True)
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🚀 ربات با موفقیت بالا اومد!")
    application.run_polling()

if __name__ == "__main__":
    main()
