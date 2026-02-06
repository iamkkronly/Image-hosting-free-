# © 2025 Kaustav Ray. All rights reserved.
# Licensed under the MIT License.

"""
Telegram Image to Direct Link Bot
--------------------------------
- Uploads images to imgbb
- Returns direct, thumbnail, and delete URLs
- Includes HTTP ping server for UptimeRobot

Built for speed, stability, and real-world traffic.

Author: Kaustav Ray
"""

import os
import base64
import logging
import asyncio
import threading
from typing import Tuple
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

# ================== IMGBB CONFIG ================== #
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")
IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"

# ================== BOT CONFIG ================== #
BOT_TOKEN = os.getenv("BOT_TOKEN")

MAX_FILE_SIZE_MB = 10
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

PING_PORT = int(os.getenv("PORT", 8000))

# ================== LOGGING ================== #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ================== HTTP PING SERVER ================== #


class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write("Bot is alive ✅".encode("utf-8"))

    def log_message(self, format, *args):
        return  # silence logs


def start_ping_server():
    server = HTTPServer(("0.0.0.0", PING_PORT), PingHandler)
    logger.info(f"Ping server running on port {PING_PORT}")
    server.serve_forever()


# ================== HELPERS ================== #


def is_valid_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_to_imgbb(image_bytes: bytes) -> Tuple[str, str, str]:
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    response = requests.post(
        IMGBB_UPLOAD_URL,
        data={
            "key": IMGBB_API_KEY,
            "image": encoded,
        },
        timeout=20,
    )

    if response.status_code != 200:
        raise RuntimeError("imgbb API unreachable")

    data = response.json()

    if not data.get("success"):
        msg = data.get("error", {}).get("message", "Upload failed")
        raise RuntimeError(msg)

    payload = data["data"]
    return payload["url"], payload["thumb"]["url"], payload["delete_url"]


# ================== TELEGRAM HANDLERS ================== #


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🖼️ *Image to Direct Link Bot*\n\n"
        "Send me any image and I’ll instantly give you a direct link.\n"
        "Supported: JPG, PNG, WEBP\n\n"
        "Fast. Simple. Reliable.",
        parse_mode="Markdown",
    )


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    await msg.chat.send_action("typing")

    try:
        if msg.photo:
            tg_file = msg.photo[-1]
            filename = "image.jpg"
        elif msg.document:
            tg_file = msg.document
            filename = tg_file.file_name or ""
            if not is_valid_image(filename):
                await msg.reply_text(
                    "❌ Unsupported file type.\nAllowed: JPG, PNG, WEBP"
                )
                return
        else:
            return

        if tg_file.file_size and tg_file.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            await msg.reply_text(
                f"⚠️ Image too large.\nMax size: {MAX_FILE_SIZE_MB} MB"
            )
            return

        file = await tg_file.get_file()
        image_bytes = await file.download_as_bytearray()

        direct, thumb, delete = await asyncio.to_thread(
            upload_to_imgbb, bytes(image_bytes)
        )

        buttons = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔗 Open Image", url=direct)],
                [InlineKeyboardButton("🖼️ Thumbnail", url=thumb)],
            ]
        )

        await msg.reply_text(
            f"✅ *Upload Successful*\n\n"
            f"*Direct URL:*\n`{direct}`\n\n"
            f"*Thumbnail URL:*\n`{thumb}`\n\n"
            f"*Delete URL:*\n`{delete}`",
            parse_mode="Markdown",
            reply_markup=buttons,
        )

    except Exception as e:
        logger.exception("Image processing failed")
        await msg.reply_text("❌ Upload failed. Please try again later.")


# ================== MAIN ================== #


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing in environment")
    if not IMGBB_API_KEY:
        raise RuntimeError("IMGBB_API_KEY missing in environment")

    threading.Thread(target=start_ping_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image))

    logger.info("Telegram bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
