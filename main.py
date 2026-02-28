import os
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from faster_whisper import WhisperModel

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8329708640:AAG1vUcykAZHM503GPtiiLqMXTv9U8UaZvs")
API_ID = int(os.environ.get("API_ID", "1234567"))
API_HASH = os.environ.get("API_HASH", "your_api_hash_here")
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "20"))
MAX_UPLOAD_SIZE = MAX_UPLOAD_MB * 1024 * 1024
MAX_MESSAGE_CHUNK = 4095
DOWNLOADS_DIR = os.environ.get("DOWNLOADS_DIR", "./downloads")

os.makedirs(DOWNLOADS_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

user_mode = {}
user_transcriptions = {}

app = Client("whisper_pyro_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

model = WhisperModel("tiny", device="cpu", compute_type="int8")

def get_user_mode(uid):
    return user_mode.get(uid, "📄 Text File")

@app.on_message(filters.command(['start', 'help']))
async def send_welcome(client, message):
    welcome_text = (
        "👋 Salaam!\n"
        "• Send me any audio or video file\n"
        "• voice message\n"
        "• document\n\n"
        "I'll transcribe the audio and return the text."
    )
    await message.reply_text(welcome_text, quote=True)

@app.on_message(filters.command(['mode']))
async def choose_mode(client, message):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Split messages", callback_data="mode|Split messages")],
        [InlineKeyboardButton("📄 Text File", callback_data="mode|Text File")]
    ])
    await message.reply_text("How do I send you long transcripts?:", reply_markup=kb, quote=True)

@app.on_callback_query(filters.regex(r'^mode\|'))
async def mode_cb(client, call):
    mode = call.data.split("|")[1]
    user_mode[call.from_user.id] = mode
    try:
        await call.edit_message_text(f"you choosed: {mode}")
    except:
        pass
    await call.answer(f"Mode set to: {mode} ☑️")

def transcribe_with_whisper(file_path):
    segments, _ = model.transcribe(file_path)
    text = "".join([s.text for s in segments])
    return text

@app.on_message(filters.voice | filters.audio | filters.document | filters.video)
async def handle_media(client, message):
    media = message.voice or message.audio or message.document or message.video
    if not media:
        return
    
    if getattr(media, 'file_size', 0) > MAX_UPLOAD_SIZE:
        await message.reply_text(f"Just send me a file less than {MAX_UPLOAD_MB}MB or use another service", quote=True)
        return

    file_path = os.path.join(DOWNLOADS_DIR, f"temp_{message.id}_{media.file_unique_id}")
    
    try:
        await message.download(file_name=file_path)
        
        text = await asyncio.to_thread(transcribe_with_whisper, file_path)
        
        if not text:
            raise ValueError("Empty response")
            
        await send_long_text(client, message.chat.id, text, message.id, message.from_user.id)
        
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}", quote=True)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def send_long_text(client, chat_id, text, reply_id, uid, action="Transcript"):
    mode = get_user_mode(uid)
    if len(text) > MAX_MESSAGE_CHUNK:
        if mode == "Split messages":
            for i in range(0, len(text), MAX_MESSAGE_CHUNK):
                await client.send_message(chat_id, text[i:i+MAX_MESSAGE_CHUNK], reply_to_message_id=reply_id)
        else:
            fname = os.path.join(DOWNLOADS_DIR, f"{action}.txt")
            with open(fname, "w", encoding="utf-8") as f:
                f.write(text)
            await client.send_document(chat_id, fname, caption="Open this file and copy the text inside 👍\n For summarizing and cleaning use ChatGPT", reply_to_message_id=reply_id)
            if os.path.exists(fname):
                os.remove(fname)
    else:
        await client.send_message(chat_id, text, reply_to_message_id=reply_id)

if __name__ == "__main__":
    app.run()
