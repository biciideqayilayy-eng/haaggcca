import os
import asyncio
import time
import requests
from pyrogram import Client, filters
from yt_dlp import YoutubeDL

API_ID = 29169428
API_HASH = '55742b16a85aac494c7944568b5507e5'
BOT_TOKEN = '8006815965:AAHnxOmVoqJDeQBqy4PbAqyqH-JGxLZf1tc'

MAX_DURATION = 30 * 60

app = Client(
    "video_dl_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=20
)

NEW_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'

YDL_OPTS_YOUTUBE = {
    'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
    'merge_output_format': 'mp4',
    'outtmpl': 'video_%(id)s.%(ext)s',
    'quiet': True,
    'no_warnings': True,
    'proxy': 'http://127.0.0.1:40000',
    'http_headers': {'User-Agent': NEW_USER_AGENT},
    'postprocessor_args': {
        'ffmpeg': [
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
            '-c:a', 'aac', '-pix_fmt', 'yuv420p', '-movflags', '+faststart'
        ]
    }
}

YDL_OPTS_PINTEREST = {
    'format': 'bestvideo+bestaudio/best',
    'outtmpl': 'video_%(id)s.%(ext)s',
    'quiet': True,
    'no_warnings': True,
    'http_headers': {'User-Agent': NEW_USER_AGENT}
}

YDL_OPTS_DEFAULT = {
    'format': 'best',
    'outtmpl': 'video_%(id)s.%(ext)s',
    'quiet': True,
    'no_warnings': True,
    'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
    'http_headers': {'User-Agent': NEW_USER_AGENT}
}

def extract_metadata_from_info(info):
    width = info.get("width")
    height = info.get("height")
    duration = info.get("duration")
    if not width or not height:
        formats = info.get("formats") or []
        for f in formats:
            if f.get("width") and f.get("height"):
                width = f.get("width")
                height = f.get("height")
                break
    return width, height, duration

def download_thumb(url, video_id):
    thumb_path = f"thumb_{video_id}.jpg"
    try:
        headers = {'User-Agent': NEW_USER_AGENT}
        response = requests.get(url, headers=headers, timeout=10)
        with open(thumb_path, "wb") as f:
            f.write(response.content)
        return thumb_path
    except:
        return None

def pick_opts(url):
    if "youtube.com" in url or "youtu.be" in url:
        return YDL_OPTS_YOUTUBE
    if "pinterest.com" in url:
        return YDL_OPTS_PINTEREST
    return YDL_OPTS_DEFAULT

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text("""Welcome 👋

This bot lets you download videos from
YouTube, TikTok, Instagram, and more.

  🛠 By: @laki3012
  
👉 Just send the video link""", quote=True)

@app.on_message(filters.private & filters.text)
async def handler(client, message):
    url = message.text.strip()
    if not url.startswith(("http://", "https://")):
        return

    msg = await message.reply_text("👀 Checking video...", quote=True)

    try:
        loop = asyncio.get_event_loop()
        ydl_opts = pick_opts(url)

        with YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            duration = info.get("duration")

            if duration and duration > MAX_DURATION:
                await msg.edit("masoo dajin karo muuqaal ka dheer 30 daqiiqo")
                return

            await msg.edit("🥴 Downloading ...")
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            
            if not os.path.exists(filename):
                base, _ = os.path.splitext(filename)
                for ext in ['mp4', 'mkv', 'webm', 'mov']:
                    if os.path.exists(f"{base}.{ext}"):
                        filename = f"{base}.{ext}"
                        break

        await msg.edit_text("🔥 Sending ...")

        if "youtube.com" in url or "youtu.be" in url:
            caption = info.get('title', 'Video')
        else:
            caption = info.get('description') or info.get('title', 'Video')
            if caption and len(caption) > 1024:
                caption = caption[:1021] + "..."

        width, height, duration = extract_metadata_from_info(info)
        thumb_url = info.get("thumbnail")
        video_id = info.get("id", "temp")
        thumb_path = download_thumb(thumb_url, video_id) if thumb_url else None

        await app.send_video(
            chat_id=message.chat.id,
            video=filename,
            caption=caption if caption else "",
            thumb=thumb_path,
            width=width if width else 0,
            height=height if height else 0,
            duration=int(duration) if duration else 0,
            supports_streaming=True,
            reply_to_message_id=message.id
        )

        if os.path.exists(filename):
            os.remove(filename)
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)

        await msg.delete()

    except Exception as e:
        await msg.edit(f"Error repot 👉🏻 @laki3012")

if __name__ == "__main__":
    app.run()
