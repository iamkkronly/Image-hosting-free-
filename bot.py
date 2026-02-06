# © 2026 Kaustav Ray. All rights reserved.
# Licensed under the MIT License.

"""
ImgBB Telegram Upload Bot
------------------------
• Uploads Telegram images to ImgBB
• Returns direct, thumbnail & viewer links
• Includes built-in web server for UptimeRobot ping
• Async, memory-safe, production-ready

Author: Kaustav Ray
"""

import os
import asyncio
import base64
import logging
import traceback
from io import BytesIO
from datetime import datetime

import aiohttp
from aiohttp import web
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from pyrogram.errors import FloodWait

# -------------------- ENV SETUP --------------------

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
IMGBB_KEY = os.getenv("IMGBB_API_KEY")
PORT = int(os.getenv("PORT", 8080))

if not all([API_ID, API_HASH, BOT_TOKEN, IMGBB_KEY]):
    raise RuntimeError("Missing required environment variables")

# -------------------- LOGGING --------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("ImgBBBot")

# -------------------- TELEGRAM CLIENT --------------------

app = Client(
    "imgbb_uploader_bot",
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"

# -------------------- IMGBB UPLOADER --------------------

async def upload_to_imgbb(file_stream: BytesIO, filename: str) -> dict | None:
    """
    Upload image to ImgBB using base64 encoding.

    Design decisions:
    • Base64 is ImgBB's most reliable input
    • Prevents multipart upload edge cases
    • Acceptable memory tradeoff (<33%)

    Returns:
        Parsed JSON response on success, None otherwise
    """
    try:
        file_stream.seek(0)
        raw_bytes = file_stream.read()

        if not raw_bytes:
            raise ValueError("Empty image stream")

        encoded = base64.b64encode(raw_bytes).decode("utf-8")

        payload = {
            "key": IMGBB_KEY,
            "image": encoded,
            "name": filename
        }

        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(IMGBB_UPLOAD_URL, data=payload) as resp:
                text = await resp.text()

                if resp.status != 200:
                    logger.error(f"ImgBB HTTP {resp.status}: {text}")
                    return None

                data = await resp.json()

                if not data.get("success"):
                    logger.error(f"ImgBB API failure: {data}")
                    return None

                return data

    except Exception:
        logger.exception("ImgBB upload error")
        return None

# -------------------- BOT COMMANDS --------------------

@app.on_message(filters.command("start"))
async def start_handler(_, message: Message):
    await message.reply_text(
        f"👋 **Hi {message.from_user.first_name}!**\n\n"
        "Send me any **photo or image document**, "
        "I’ll upload it to **ImgBB** and give you a direct link.\n\n"
        "📦 Supported: JPG, PNG, WEBP, GIF",
        quote=True
    )

@app.on_message(filters.photo | filters.document)
async def image_handler(_, message: Message):
    if message.document and "image" not in message.document.mime_type:
        await message.reply_text("❌ This file is not an image.", quote=True)
        return

    status = await message.reply_text("⏳ Downloading...", quote=True)

    try:
        downloaded = await message.download(in_memory=True)

        if isinstance(downloaded, bytes):
            file_stream = BytesIO(downloaded)
        else:
            file_stream = downloaded

        file_stream.seek(0)

        await status.edit_text("🚀 Uploading to ImgBB...")

        filename = (
            f"img_{message.from_user.id}_"
            f"{int(datetime.utcnow().timestamp())}.jpg"
        )

        response = await upload_to_imgbb(file_stream, filename)

        if not response:
            await status.edit_text("⚠️ Upload failed. Try again later.")
            return

        data = response["data"]

        text = (
            "✅ **Upload Successful!**\n\n"
            f"🔗 **Direct:** `{data['url']}`\n\n"
            f"🖼 **Thumbnail:** [View]({data['thumb']['url']})\n"
            f"📄 **Page:** [Open]({data['url_viewer']})"
        )

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Open Image", url=data["url"])],
            [InlineKeyboardButton("📤 Share", switch_inline_query=data["url"])]
        ])

        await status.edit_text(
            text,
            reply_markup=buttons,
            disable_web_page_preview=True
        )

    except FloodWait as e:
        await asyncio.sleep(e.value)

    except Exception:
        traceback.print_exc()
        await status.edit_text("❌ Internal error occurred.")

# -------------------- WEB SERVER (UPTIMEROBOT) --------------------

async def health_check(request):
    return web.Response(
        text="OK - ImgBB Telegram Bot is running",
        status=200
    )

async def start_web_server():
    app_web = web.Application()
    app_web.router.add_get("/", health_check)

    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    logger.info(f"Web server running on port {PORT}")

# -------------------- MAIN ENTRY --------------------

async def main():
    await start_web_server()
    await app.start()
    logger.info("Telegram bot started")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
