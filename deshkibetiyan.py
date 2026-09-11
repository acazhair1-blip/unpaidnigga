import asyncio
import logging
import os
import re
import time
from threading import Thread

# 1. FORCE EVENT LOOP CREATION FOR PYTHON 3.11+
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from bs4 import BeautifulSoup
from flask import Flask
from pyrogram import Client, enums, filters, idle
from pyrogram.errors import UserNotParticipant
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# ==========================================
# 🌐 KEEP-ALIVE FLASK SERVER FOR RAILWAY
# ==========================================
web = Flask(__name__)


@web.route("/")
def home():
    return "Bot is Live 24/7 on Railway!"


def run_web():
    port = int(os.environ.get("PORT", 8080))
    web.run(host="0.0.0.0", port=port)


def keep_alive():
    t = Thread(target=run_web, daemon=True)
    t.start()


# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
API_ID = 35025088
API_HASH = "b409c31c0c25b927dca36fcc0d05c149"
BOT_TOKEN = "8602387086:AAGiV9tLsCpuFXxq1YFxZtRPZr6CbFihBh0"

CHANNELS = [
    {"id": -1004460480150, "link": "https://t.me/+TsUwg9LKW2wzNDE1"},
    {"id": -1004442592541, "link": "https://t.me/+NdBuwwTcRQo2NDU1"},
]

AUTO_DELETE_TIME = 300  # 5 Minutes
SITE_URL = "https://sundarikanya.ink"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

logging.basicConfig(level=logging.ERROR)

app = Client(
    "VIPVaultRailway",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
)

# Cache Storage
GLOBAL_CATS, USER_VIDS, FILE_CACHE = {}, {}, {}


# ==========================================
# 🛡️ UTILS & FORCE JOIN
# ==========================================
async def auto_delete_msg(chat_id, message_id):
    await asyncio.sleep(AUTO_DELETE_TIME)
    try:
        await app.delete_messages(chat_id, message_id)
    except Exception:
        pass


def clean_branding(text):
    if not text:
        return ""
    text = re.sub(r"(?i)sundari\s*kanya|sundarikanya\.ink", "", text)
    return re.sub(r"\s+", " ", text).strip() or "Premium File"


async def is_joined(client, user_id):
    for ch in CHANNELS:
        try:
            m = await client.get_chat_member(ch["id"], user_id)
            if m.status not in [
                enums.ChatMemberStatus.MEMBER,
                enums.ChatMemberStatus.ADMINISTRATOR,
                enums.ChatMemberStatus.OWNER,
            ]:
                return False
        except UserNotParticipant:
            return False
        except Exception:
            continue
    return True


# ==========================================
# 🔍 SCRAPERS
# ==========================================
def fetch_cats():
    global GLOBAL_CATS
    try:
        r = requests.get(SITE_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        new_cats = {}
        for a in soup.select(
            ".wp-block-heading a, .entry-content a, .menu-item a"
        ):
            name = clean_branding(a.get_text(strip=True))
            url = a.get("href")
            if url and SITE_URL in url and len(name) > 2:
                new_cats[name] = url
        if new_cats:
            GLOBAL_CATS = new_cats
    except Exception:
        pass


def fetch_vids(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        vids = []
        for a in soup.select("h2 a, h3 a, article a, .entry-title a"):
            t = clean_branding(a.get_text(strip=True))
            u = a.get("href")
            if u and SITE_URL in u and len(t) > 3:
                if not any(x in u.lower() for x in ["/author/", "/category/"]):
                    vids.append({"title": t[:50], "url": u})
        return vids
    except Exception:
        return []


# ==========================================
# 🤖 HANDLERS
# ==========================================
@app.on_message(filters.command("start"))
async def start_handler(client, message):
    if not await is_joined(client, message.from_user.id):
        kb = [
            [InlineKeyboardButton(f"📢 Join Channel {i+1}", url=c["link"])]
            for i, c in enumerate(CHANNELS)
        ]
        kb.append(
            [InlineKeyboardButton("✅ Verify & Start", callback_data="verify")]
        )
        return await message.reply(
            "🔒 **ACCESS DENIED!**\n\nContent unlock karne ke liye dono channels join karein.",
            reply_markup=InlineKeyboardMarkup(kb),
        )

    if not GLOBAL_CATS:
        fetch_cats()
    btns = [[KeyboardButton(c)] for c in list(GLOBAL_CATS.keys())[:15]]
    btns.append(
        [KeyboardButton("🔍 Search"), KeyboardButton("🔄 Refresh Menu")]
    )
    await message.reply(
        "💎 **Media Dashboard Active**\nSelect Category:",
        reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True),
    )


@app.on_message(filters.text & ~filters.command(["start", "search"]))
async def menu_handler(client, message):
    if not await is_joined(client, message.from_user.id):
        return
    if message.text == "🔄 Refresh Menu":
        fetch_cats()
        await start_handler(client, message)
        return
    if message.text == "🔍 Search":
        return await message.reply("Usage: `/search bhabhi`")

    if message.text in GLOBAL_CATS:
        load = await message.reply(f"⏳ **Loading {message.text}...**")
        vids = fetch_vids(GLOBAL_CATS[message.text])
        USER_VIDS[message.from_user.id] = vids
        kb = [
            [InlineKeyboardButton(f"▶️ {v['title']}", callback_data=f"play_{i}")]
            for i, v in enumerate(vids[:20])
        ]
        await load.edit(
            f"📂 **Category: {message.text}**",
            reply_markup=InlineKeyboardMarkup(kb),
        )


@app.on_callback_query()
async def cb_handler(client, query):
    if query.data == "verify":
        if await is_joined(client, query.from_user.id):
            await query.message.delete()
            await start_handler(client, query.message)
        else:
            await query.answer("❌ Join Dono Channels Pehle!", show_alert=True)

    elif query.data.startswith("play_"):
        idx = int(query.data.split("_")[1])
        vid = USER_VIDS[query.from_user.id][idx]
        status = await query.message.reply(f"🚀 **Streaming:** {vid['title']}...")
        try:
            r = requests.get(vid["url"], headers=HEADERS, timeout=15)
            mp4s = list(
                set(re.findall(r"https?://[^\s\"'<>]+\.mp4", r.text))
            )
            for mp4 in mp4s[:1]:
                caption = f"🎬 **{vid['title']}**\n\n⏳ _Auto-deleting in 5 mins!_"
                sent = await client.send_video(
                    query.message.chat.id,
                    mp4,
                    caption=caption,
                    protect_content=True,
                )
                asyncio.create_task(
                    auto_delete_msg(query.message.chat.id, sent.id)
                )
            await status.delete()
        except Exception:
            await status.edit("⚠️ Stream Error.")


@app.on_message(filters.command("search"))
async def search_cmd(client, message):
    q = " ".join(message.command[1:])
    vids = fetch_vids(f"{SITE_URL}/?s={q}")
    USER_VIDS[message.from_user.id] = vids
    kb = [
        [InlineKeyboardButton(v["title"], callback_data=f"play_{i}")]
        for i, v in enumerate(vids[:20])
    ]
    await message.reply(
        f"🔎 Results for {q}:", reply_markup=InlineKeyboardMarkup(kb)
    )


@app.on_chat_join_request()
async def auto_approve(client, m):
    try:
        await client.approve_chat_join_request(m.chat.id, m.from_user.id)
    except Exception:
        pass


# ==========================================
# 🚀 MAIN ASYNC RUNNER (CRASH-PROOF)
# ==========================================
async def main():
    print("Starting Flask Web Server...")
    keep_alive()
    print("Fetching Categories...")
    fetch_cats()
    print("Starting Pyrogram Client...")
    await app.start()
    print("🚀 BOT IS LIVE AND RUNNING ON RAILWAY 24/7!")
    await idle()
    await app.stop()


if __name__ == "__main__":
    loop.run_until_complete(main())
