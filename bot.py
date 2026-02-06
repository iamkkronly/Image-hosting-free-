# Copyright (c) 2026 Kaustav Ray
# Project: ImgBB Telegram Bot
# Developed for high-throughput image hosting.

import os
import asyncio
import traceback
import logging
from io import BytesIO

from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
import aiohttp

# Load up the environment
load_dotenv()

# Configs
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
IMGBB_KEY = os.getenv("IMGBB_API_KEY")

# Basic sanity check
if not all([API_ID, API_HASH, BOT_TOKEN, IMGBB_KEY]):
    print("Error: Missing env variables. Check your .env file.")
    exit(1)

# Logging (keep it simple for now)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Client(
    "imgbb_uploader_bot",
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

IMGBB_URL = "https://api.imgbb.com/1/upload"

async def upload_to_imgbb(file_stream, name):
    """
    Handles the actual API push to ImgBB.
    """
    async with aiohttp.ClientSession() as session:
        # ImgBB usually wants base64, but multipart/form-data with binary works 
        # and is better for RAM with larger files.
        payload = {
            "key": IMGBB_KEY,
        }
        data = aiohttp.FormData()
        data.add_field('key', IMGBB_KEY)
        data.add_field('image', file_stream, filename=name)
        # expiration could be added here if we want auto-delete features later

        try:
            async with session.post(IMGBB_URL, data=data) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    err_text = await resp.text()
                    logger.error(f"ImgBB Upload Failed: {err_text}")
                    return None
        except Exception as e:
            logger.error(f"Network error during upload: {e}")
            return None

@app.on_message(filters.command("start"))
async def start_handler(client, message: Message):
    txt = (
        f"👋 **Hi {message.from_user.first_name}!**\n\n"
        "I'm a fast image uploader bot. Send me any **Photo** or **Image File**, "
        "and I'll upload it to ImgBB and give you a direct link.\n\n"
        "🚀 *Supported formats:* JPG, PNG, WEBP, GIF"
    )
    await message.reply_text(txt, quote=True)

@app.on_message(filters.photo | filters.document)
async def image_handler(client, message: Message):
    # If it's a document, check mime type first to save bandwidth
    if message.document:
        if "image" not in message.document.mime_type:
            await message.reply_text("❌ That doesn't look like an image file.", quote=True)
            return
            
    status_msg = await message.reply_text("⏳ **Downloading...**", quote=True)
    
    file_stream = BytesIO()
    
    try:
        # Download in-memory. For a VPS with low RAM, you might want to switch 
        # to downloading to a temp file path instead.
        file_path = await message.download(in_memory=True)
        
        # Depending on pyrogram version/settings, this returns bytes or BytesIO
        if isinstance(file_path, bytes):
            file_stream = BytesIO(file_path)
        else:
            file_stream = file_path
            
        await status_msg.edit_text("🚀 **Uploading to ImgBB...**")
        
        # Generate a distinct filename or ImgBB might get confused
        timestamp = message.date.timestamp()
        user_id = message.from_user.id
        filename = f"img_{user_id}_{int(timestamp)}.jpg"

        response = await upload_to_imgbb(file_stream, filename)
        
        if response and response.get("success"):
            data = response["data"]
            direct_url = data["url"]
            thumb_url = data["thumb"]["url"]
            view_url = data["url_viewer"]
            
            # Clean output format
            text_response = (
                f"✅ **Upload Successful!**\n\n"
                f"🔗 **Direct Link:**\n`{direct_url}`\n\n"
                f"🖼 **Thumbnail:** [View]({thumb_url})\n"
                f"📝 **Page:** [View Page]({view_url})"
            )
            
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Open Image", url=direct_url)],
                [InlineKeyboardButton("📤 Share", switch_inline_query=direct_url)]
            ])
            
            await status_msg.edit_text(
                text_response,
                reply_markup=buttons,
                disable_web_page_preview=True 
            )
        else:
            await status_msg.edit_text("⚠️ **Upload Failed.** \nCheck the file size or try again later.")
            
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await status_msg.edit_text(f"😴 Rate limited. Sleeping for {e.value}s...")
    except Exception as e:
        traceback.print_exc()
        await status_msg.edit_text("❌ **Error:** Something went wrong while processing.")

if __name__ == "__main__":
    print("Bot is starting up...")
    app.run()

