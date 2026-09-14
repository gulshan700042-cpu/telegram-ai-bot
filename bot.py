import os
import io
import asyncio
import threading
import logging
from flask import Flask
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# Setup logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

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

DELETE_NOTICE = "\n\n⚠️ *Yeh message 5 minute baad delete ho jayega, ise save or share kar lijiye!*"

# 5-minute background auto-delete function
async def delete_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 300):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.warning(f"Auto-delete skip ya fail hua (Msg ID {message_id}): {e}")

# Safe reply helper: Handles long text, deleted messages, and 5-min timer
async def safe_reply(msg, chat_id, context, text, auto_delete=True):
    if not text:
        text = "Koyi response generate nahi hua."

    if auto_delete:
        text += DELETE_NOTICE

    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
    
    for chunk in chunks:
        sent_msg = None
        try:
            if msg:
                sent_msg = await msg.reply_text(chunk, parse_mode="Markdown")
            else:
                sent_msg = await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode="Markdown")
        except Exception:
            try:
                # Markdown format fail hone par plain text delivery
                if msg:
                    sent_msg = await msg.reply_text(chunk)
                else:
                    sent_msg = await context.bot.send_message(chat_id=chat_id, text=chunk)
            except Exception:
                # Deleted message fallback: Direct chat message
                try:
                    sent_msg = await context.bot.send_message(chat_id=chat_id, text=chunk)
                except Exception as final_e:
                    logger.error(f"Message delivery fail hui: {final_e}")

        # 300 seconds (5 min) timer schedule
        if auto_delete and sent_msg:
            asyncio.create_task(
                delete_after_delay(context, chat_id=chat_id, message_id=sent_msg.message_id, delay=300)
            )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.channel_post
    chat_id = update.effective_chat.id if update.effective_chat else None
    if not chat_id:
        return

    welcome_text = (
        "Namaste! Main aapka All-Rounder AI Assistant hoon.\n\n"
        "Aap mujhse kuch bhi pooch sakte hain:\n"
        "• Law / Kanoon (Sections, Rights, IPC/BNS)\n"
        "• Computer, Coding & Tech doubts\n"
        "• Math, Science & Academics\n"
        "• Daily general questions\n\n"
        "Chahein toh text likhein ya seedha photo bhejein!"
    )
    await safe_reply(msg, chat_id, context, welcome_text, auto_delete=False)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.channel_post
    if not msg or not msg.text:
        return

    chat_id = update.effective_chat.id
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception:
        pass

    try:
        response = model.generate_content(msg.text)
        await safe_reply(msg, chat_id, context, response.text, auto_delete=True)
    except Exception as e:
        logger.error(f"Error in handle_text: {e}")
        await safe_reply(msg, chat_id, context, f"Error details: {e}", auto_delete=True)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.channel_post
    if not msg or not msg.photo:
        return

    chat_id = update.effective_chat.id
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception:
        pass

    try:
        photo_file = await msg.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        image = Image.open(io.BytesIO(photo_bytes))
        prompt = msg.caption or (
            "Analyze and answer the query or question in this image thoroughly and clearly. "
            "Do not use LaTeX dollar signs ($) or caret (^) for powers."
        )
        response = model.generate_content([prompt, image])
        await safe_reply(msg, chat_id, context, response.text, auto_delete=True)
    except Exception as e:
        logger.error(f"Error in handle_photo: {e}")
        await safe_reply(msg, chat_id, context, f"Error details: {e}", auto_delete=True)

# Global Error Handler: Prevents crashes from unhandled network exceptions
async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}")

if __name__ == '__main__':
    web_thread = threading.Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Register error handler
    app.add_error_handler(global_error_handler)

    # Handlers for PM, Groups & Channel Posts
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST & filters.TEXT, handle_text))
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST & filters.PHOTO, handle_photo))

    app.run_polling(drop_pending_updates=True)
    
