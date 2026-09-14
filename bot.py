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
    return "All-Rounder Bot is alive!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

# Credentials
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

genai.configure(api_key=GEMINI_API_KEY)

# All-rounder smart assistant instruction
SYSTEM_INSTRUCTION = (
    "You are an authentic, adaptive, all-rounder AI collaborator with deep knowledge across all domains: "
    "Law, Computer Science/IT, Mathematics, Science, History, General Knowledge, and daily problem solving.\n\n"
    "HOW TO RESPOND:\n"
    "1. Answer naturally, clearly, and directly like an intelligent peer and expert mentor.\n"
    "2. Language: Match the user's language smoothly (pure Hindi, simple English, or natural Hinglish).\n"
    "3. For Law: Give structured explanations of legal provisions (IPC/BNS, CrPC/BNSS, Constitution, etc.), sections, and principles.\n"
    "4. For Tech/Computers: Give clean code blocks, clear logic, and practical step-by-step guidance.\n"
    "5. For Math/Science: Keep steps neat and structured. NEVER use LaTeX dollar signs ($ or $$). "
    "NEVER use the caret symbol (^) for powers; always write real Unicode superscripts like x², x³, x⁴, y².\n"
    "6. Prioritize scannability using bullet points and clean paragraphs. Avoid robotic fluff."
)

model = genai.GenerativeModel(
    'gemini-3.6-flash',
    system_instruction=SYSTEM_INSTRUCTION
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Namaste! Main aapka All-Rounder AI Assistant hoon.\n\n"
        "Aap mujhse kuch bhi pooch sakte hain:\n"
        "• Law / Kanoon (Sections, Rights, IPC/BNS)\n"
        "• Computer, Coding & Tech doubts\n"
        "• Math, Science & Academics\n"
        "• Daily general questions\n\n"
        "Chahein toh text likhein ya seedha photo bhejein!"
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
            "Analyze and answer the query or question in this image thoroughly and clearly. "
            "Do not use LaTeX dollar signs ($) or caret (^) for powers."
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
