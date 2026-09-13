import os
import io
import threading
from flask import Flask
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# --- Dummy Web Server for Render Free Tier ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

# --- Telegram Bot Code ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Namaste! Sawal likhkar bhejiye ya math question ki photo, main solve kar dunga.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        response = model.generate_content(update.message.text)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text("Abhi answer generate nahi ho paya, kripya dobara try karein.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        image = Image.open(io.BytesIO(photo_bytes))
        prompt = update.message.caption or "Solve this problem step-by-step with explanation."
        response = model.generate_content([prompt, image])
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text("Photo process karne mein dikkat aayi.")

if __name__ == '__main__':
    # Web server ko background thread mein start karein
    web_thread = threading.Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()

    # Telegram bot start karein
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()
    
