import os
import logging
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from faster_whisper import WhisperModel

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8329708640:AAG1vUcykAZHM503GPtiiLqMXTv9U8UaZvs")
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "300"))
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "20"))
MAX_UPLOAD_SIZE = MAX_UPLOAD_MB * 1024 * 1024
MAX_MESSAGE_CHUNK = 4095
DOWNLOADS_DIR = os.environ.get("DOWNLOADS_DIR", "./downloads")

os.makedirs(DOWNLOADS_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

user_mode = {}
user_transcriptions = {}

bot = TeleBot(BOT_TOKEN)

model = WhisperModel("tiny", device="cpu", compute_type="int8")

def get_user_mode(uid):
    return user_mode.get(uid, "📄 Text File")

def ensure_joined(message):
    return True

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if ensure_joined(message):
        welcome_text = (
            "👋 Salaam!\n"
            "• Send me any audio or video file\n"
            "• voice message\n"
            "• document\n\n"
            "I'll transcribe the audio and return the text."
        )
        bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['mode'])
def choose_mode(message):
    if ensure_joined(message):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Split messages", callback_data="mode|Split messages")],
            [InlineKeyboardButton("📄 Text File", callback_data="mode|Text File")]
        ])
        bot.reply_to(message, "How do I send you long transcripts?:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith('mode|'))
def mode_cb(call):
    if not ensure_joined(call.message):
        return
    mode = call.data.split("|")[1]
    user_mode[call.from_user.id] = mode
    try:
        bot.edit_message_text(f"you choosed: {mode}", call.message.chat.id, call.message.message_id, reply_markup=None)
    except:
        pass
    bot.answer_callback_query(call.id, f"Mode set to: {mode} ☑️")

def transcribe_with_whisper(file_path):
    segments, _ = model.transcribe(file_path)
    text = "".join([s.text for s in segments])
    return text

@bot.message_handler(content_types=['voice', 'audio', 'document', 'video'])
def handle_media(message):
    if not ensure_joined(message):
        return
    media = message.voice or message.audio or message.document or message.video
    if not media:
        return
    if getattr(media, 'file_size', 0) > MAX_UPLOAD_SIZE:
        bot.reply_to(message, f"Just send me a file less than {MAX_UPLOAD_MB}MB or use another service")
        return
    bot.send_chat_action(message.chat.id, 'typing')
    file_path = os.path.join(DOWNLOADS_DIR, f"temp_{message.id}_{media.file_unique_id}")
    try:
        file_info = bot.get_file(media.file_id)
        downloaded = bot.download_file(file_info.file_path)
        with open(file_path, 'wb') as f:
            f.write(downloaded)

        text = transcribe_with_whisper(file_path)
        if not text:
            raise ValueError("Empty response")
        sent = send_long_text(message.chat.id, text, message.id, message.from_user.id)
        if sent:
            user_transcriptions.setdefault(message.chat.id, {})[sent.message_id] = {"text": text, "origin": message.id}
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass

def send_long_text(chat_id, text, reply_id, uid, action="Transcript"):
    mode = get_user_mode(uid)
    if len(text) > MAX_MESSAGE_CHUNK:
        if mode == "Split messages":
            sent = None
            for i in range(0, len(text), MAX_MESSAGE_CHUNK):
                sent = bot.send_message(chat_id, text[i:i+MAX_MESSAGE_CHUNK], reply_to_message_id=reply_id)
            return sent
        else:
            fname = os.path.join(DOWNLOADS_DIR, f"{action}.txt")
            with open(fname, "w", encoding="utf-8") as f:
                f.write(text)
            sent = bot.send_document(chat_id, open(fname, 'rb'), caption="Open this file and copy the text inside 👍\n For summarizing and cleaning use ChatGPT", reply_to_message_id=reply_id)
            os.remove(fname)
            return sent
    return bot.send_message(chat_id, text, reply_to_message_id=reply_id)

if __name__ == "__main__":
    bot.remove_webhook()
    print("Bot is starting via Polling...")
    bot.infinity_polling()
