# Image-hosting-free-

# Telegram ImgBB Uploader Bot

A high-performance Telegram bot that instantly uploads images to ImgBB and returns direct, public-accessible links. Built with **Python** and **python-telegram-bot** for speed and efficiency.

> **Copyright (c) 2026 Kaustav Ray**

---

## 🚀 Features

* **Instant Uploads:** Asynchronous uploads to ImgBB.
* **Smart Detection:** Automatically handles compressed Telegram photos and uncompressed files (Documents).
* **Format Support:** JPG, PNG, WEBP.
* **User Friendly:** Returns a Direct Link, Thumbnail URL, and a "View Page" link.
* **Interactive UI:** Inline buttons to open or share the image immediately.
* **Production Ready:** Includes error handling, logging, and rate-limit protection.

## 🛠 Prerequisites

Before you begin, ensure you have the following:

1.  **Python 3.9+** installed.
2.  **Telegram Bot Token** from [@BotFather](https://t.me/BotFather).
3.  **ImgBB API Key** from [api.imgbb.com](https://api.imgbb.com/).

## 📥 Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/yourusername/imgbb-bot.git](https://github.com/yourusername/imgbb-bot.git)
    cd imgbb-bot
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## ⚙️ Configuration

Create a file named `.env` in the root directory and add your credentials. You can use the example below:

```ini
# .env file

# Telegram Configs
BOT_TOKEN=your_bot_token_here

# ImgBB Config
IMGBB_API_KEY=your_imgbb_key_here
