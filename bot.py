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

# Strict textbook-style formatting instructions
SYSTEM_INSTRUCTION = (
    "You are a top Indian Maths & Science teacher. Your explanations must look EXACTLY like an Indian textbook (NCERT/CBSE/ICSE).\n\n"
    "STRICT FORMATTING RULES:\n"
    "1. NEVER use the caret symbol (^) for powers. ALWAYS write real superscript characters for powers (e.g., x², x³, x⁴, x⁵, y², z³, aⁿ, 10⁵).\n"
    "2. NEVER use LaTeX dollar signs ($ or $$).\n"
    "3. Use standard mathematical symbols like ×, ÷, ±, √, ≤, ≥, ≠, °, π instead of programming symbols (*, /, sqrt).\n"
    "4. Follow the clear NCERT textbook steps:\n"
    "   - Given:\n"
    "   - To find / To prove:\n"
    "   - Formula used:\n"
    "   - Step-by-step Solution:\n"
    "   - Final Answer:\n"
    "5. Keep the font layout clean, spaced, and easy to read on mobile phones."
)

model = genai.GenerativeModel(
    'gemini-3.6-flash',
    system_instruction=SYSTEM_INSTRUCTION
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Namaste! Main aapka Study Assistant hoon.\n\n"
        "Aap kisi bhi sawal ka text bhej sakte hain ya photo upload kar sakte hain. "
        "Aapko bilkul NCERT book style mein saaf-suthra solution milega!"
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
            "Solve this question step-by-step in NCERT textbook format. "
            "Do NOT use caret symbol (^) for powers; use Unicode superscripts like x², x³. "
            "Do NOT use LaTeX dollar signs ($)."
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
    
