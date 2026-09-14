import os
import io
import threading
from flask import Flask
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# Lightweight web server for Render Free Web Service
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is alive!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

# Credentials
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

genai.configure(api_key=GEMINI_API_KEY)

# Custom instructions strictly tuned to Indian curriculum (NCERT / CBSE / JEE)
SYSTEM_INSTRUCTION = (
    "You are an expert Indian teacher and tutor for students studying NCERT, CBSE, ICSE, and competitive exams like JEE/NEET. "
    "Guidelines for your responses:\n"
    "1. Follow the standard Indian mathematics curriculum and methodology step-by-step (e.g., Given, Formula used, Step-by-step calculation, Final Answer).\n"
    "2. Explain in clear, easy-to-understand English or natural Hinglish if the user asks in Hindi/Hinglish.\n"
    "3. Format numbers using Indian conventions (Lakhs/Crores) where applicable.\n"
    "4. STRICTLY NEVER use LaTeX dollar signs ($ or $$). Format mathematical terms in plain, easy-to-read text (e.g., x^2, x^3, sqrt, +, -, *, /, =) so that it looks neat and readable on Telegram mobile screens.\n"
    "5. Keep the steps clean, structured, and exam-oriented."
)

model = genai.GenerativeModel(
    'gemini-3.6-flash',
    system_instruction=SYSTEM_INSTRUCTION
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Namaste! Main aapka Study Assistant hoon.\n\n"
        "Aap NCERT, CBSE, JEE ya kisi bhi exam ka sawal likhkar bhej sakte hain ya photo upload kar sakte hain. "
        "Main step-by-step solution dunga!"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        response = model.generate_content(update.message.text)
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text(f"Error details: {e}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        image = Image.open(io.BytesIO(photo_bytes))
        prompt = update.message.caption or (
            "Solve this question step-by-step strictly following the NCERT/Indian curriculum format. "
            "Do not use LaTeX dollar signs."
        )
        response = model.generate_content([prompt, image])
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text(f"Error details: {e}")

if __name__ == '__main__':
    web_thread = threading.Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()
    
