import sys
import asyncio
import os
import re
import time
import requests
import logging
from threading import Thread

# 1. FORCE EVENT LOOP CREATION FOR PYTHON 3.11+ (RAILWAY FIX)
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

# 🔒 14 HARDCODED DEFAULT CATEGORIES (KABHI GAYAB NAHI HONGI)
PERMANENT_CATS = {
    "💃 Village Bhabhi": f"{SITE_URL}/village-bhabhi/",
    "📸 Snapchat": f"{SITE_URL}/snapchat/",
    "🔥 Sexy Babe": f"{SITE_URL}/sexy-babe/",
    "👰 Beautiful Wife": f"{SITE_URL}/beautiful-wife/",
    "🍼 Milf": f"{SITE_URL}/milf/",
    "⚡ Trending Videos": f"{SITE_URL}/trending-videos/",
    "🔞 Horny": f"{SITE_URL}/horny/",
    "😮 Blowjob": f"{SITE_URL}/category/blowjob/",
    "✨ Beautiful": f"{SITE_URL}/category/beautiful/",
    "🍑 Cute": f"{SITE_URL}/category/cute/",
    "🌟 Young": f"{SITE_URL}/category/young/",
    "👉 Fingering": f"{SITE_URL}/category/fingering/",
    "💥 Hard Fucking": f"{SITE_URL}/category/hard-fucking/",
    "🇮🇳 Desi Special": f"{SITE_URL}/category/desi/"
}

logging.basicConfig(level=logging.ERROR)

app = Client(
    "VIPVaultRailway",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
)

GLOBAL_CATS = dict(PERMANENT_CATS)
USER_VIDS, FILE_CACHE = {}, {}

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

def is_junk_image(url):
    u = (url or "").lower()
    return any(x in u for x in ['logo', 'butterfly', 'icon', 'avatar', '626x626', 'favicon', 'header'])

def get_emoji(name):
    n = name.lower()
    if 'bhabhi' in n: return "💃 "
    if 'snap' in n: return "📸 "
    if 'sexy' in n or 'hot' in n or 'babe' in n: return "🔥 "
    if 'wife' in n: return "👰 "
    if 'milf' in n: return "🍼 "
    if 'viral' in n or 'trend' in n: return "⚡ "
    if 'desi' in n: return "🇮🇳 "
    if 'blowjob' in n: return "😮 "
    if 'cute' in n: return "🍑 "
    if 'young' in n: return "🌟 "
    if 'fingering' in n: return "👉 "
    if 'hard' in n: return "💥 "
    return "📁 "

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
        r = requests.get(SITE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        new_cats = {}
        for a in soup.select(".wp-block-heading a, .entry-content a, .menu-item a, .cat-item a"):
            name = clean_branding(a.get_text(strip=True))
            url = a.get("href")
            if url and SITE_URL in url and len(name) > 2:
                ignore = ['home', 'login', 'contact', 'dmca', 'membership', 'search', 'about', 'author']
                if not any(x in name.lower() for x in ignore):
                    disp_name = get_emoji(name) + name
                    new_cats[disp_name] = url
        
        if new_cats and len(new_cats) >= 4:
            GLOBAL_CATS = new_cats
        else:
            GLOBAL_CATS = dict(PERMANENT_CATS)
    except Exception:
        GLOBAL_CATS = dict(PERMANENT_CATS)

def fetch_vids(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        vids = []
        for a in soup.select("h2.entry-title a, h2 a, h3 a, article a, .entry-title a, .pt-cv-title a, .post-title a"):
            t = clean_branding(a.get_text(strip=True))
            u = a.get("href")
            if u and SITE_URL in u and len(t) > 3:
                if not any(x in u.lower() for x in ["/author/", "/category/", "/tag/", "/page/", "?s="]):
                    if not any(v['url'] == u for v in vids):
                        vids.append({"title": t[:50], "url": u})
        return vids
    except Exception:
        return []

def extract_media(post_url):
    media = {'videos': [], 'images': []}
    try:
        r = requests.get(post_url, headers=HEADERS, timeout=12)
        html = r.text
        archive = re.findall(r"https?://archive\.sundarikanya\.ink/[^\s\"'<>]+\.mp4", html)
        general = re.findall(r"https?://[^\s\"'<>]+\.mp4", html)
        media['videos'] = list(dict.fromkeys(archive + general))
        
        soup = BeautifulSoup(html, "html.parser")
        for img in soup.select(".entry-content img, article img")[:4]:
            src = img.get("src") or img.get("data-src")
            if src and src.startswith("http") and not src.endswith((".svg", ".gif")):
                if not is_junk_image(src):
                    media['images'].append(src)
        media['images'] = list(dict.fromkeys(media['images']))[:3]
        return media
    except Exception:
        return media

# ==========================================
# 📱 UI BUILDER (NEVER EMPTY GUARANTEE)
# ==========================================
def build_bottom_keyboard():
    rows = []
    row = []
    # Guaranteed fallback check
    cats_to_show = GLOBAL_CATS if len(GLOBAL_CATS) > 0 else PERMANENT_CATS
    cats_keys = list(cats_to_show.keys())[:16]
    
    for c in cats_keys:
        row.append(KeyboardButton(c))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
        
    rows.append([KeyboardButton("🔍 Search"), KeyboardButton("🔄 Refresh Menu")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

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

    await message.reply(
        "💎 **Media Dashboard Active**\nNiche menu se category select karein ya Search dabayein:",
        reply_markup=build_bottom_keyboard(),
    )

@app.on_message(filters.text & ~filters.command(["start", "search"]))
async def menu_handler(client, message):
    if not await is_joined(client, message.from_user.id):
        await start_handler(client, message)
        return

    text = message.text or ""

    if text == "🔄 Refresh Menu":
        fetch_cats()
        await message.reply("✅ Menu Refreshed!", reply_markup=build_bottom_keyboard())
        return

    if text == "🔍 Search":
        return await message.reply("🔍 Type `/search keyword`\nExample: `/search bhabhi`")

    # Determine category URL
    cats_dict = GLOBAL_CATS if len(GLOBAL_CATS) > 0 else PERMANENT_CATS
    
    if text in cats_dict:
        load = await message.reply(f"⏳ **Loading {text}...**", quote=True)
        vids = fetch_vids(cats_dict[text])
        if not vids:
            return await load.edit(f"❌ **{text}** me abhi koi video nahi mili.")

        USER_VIDS[message.from_user.id] = vids
        kb = [
            [InlineKeyboardButton(f"▶️ {v['title']}", callback_data=f"play_{i}")]
            for i, v in enumerate(vids[:20])
        ]
        kb.append([InlineKeyboardButton("❌ Close List", callback_data="close")])
        await load.edit(
            f"📂 **Category: {text}**\nSelect a video to play:",
            reply_markup=InlineKeyboardMarkup(kb),
        )

@app.on_callback_query()
async def cb_handler(client, query):
    data = query.data or ""
    user_id = query.from_user.id

    if data == "verify":
        if await is_joined(client, user_id):
            try:
                await query.message.delete()
            except Exception:
                pass
            await start_handler(client, query.message)
        else:
            await query.answer("❌ Join Dono Channels Pehle!", show_alert=True)

    elif data == "close":
        try:
            await query.message.delete()
        except Exception:
            pass

    elif data.startswith("play_"):
        if not await is_joined(client, user_id):
            await query.answer("🔒 Pehle Channels Join Karein!", show_alert=True)
            return

        idx = int(data.split("_")[1])
        if user_id not in USER_VIDS or idx >= len(USER_VIDS[user_id]):
            await query.answer("Session expired. Category dubara select karo.", show_alert=True)
            return

        vid = USER_VIDS[user_id][idx]
        await query.answer(f"Loading: {vid['title']}")
        status = await query.message.reply(f"🚀 **Streaming:** {vid['title']}...")

        media = extract_media(vid["url"])

        # Preview Photos
        if media["images"]:
            try:
                if len(media["images"]) == 1:
                    sent_p = await client.send_photo(
                        query.message.chat.id,
                        media["images"][0],
                        caption=f"🖼 **{vid['title']}**\n\n⏳ _Auto-deleting in 5 mins!_",
                        protect_content=True
                    )
                    asyncio.create_task(auto_delete_msg(query.message.chat.id, sent_p.id))
                else:
                    group = [InputMediaPhoto(p) for p in media["images"]]
                    await client.send_media_group(query.message.chat.id, group)
            except Exception:
                pass

        # Videos Streaming
        if media["videos"]:
            total = len(media["videos"])
            for i, mp4 in enumerate(media["videos"][:3]):
                caption = f"🎬 **{vid['title']}**"
                if total > 1:
                    caption += f" (Part {i+1}/{min(total,3)})"
                caption += "\n\n⏳ _Auto-deleting in 5 mins to prevent copyright!_"

                sent_vid = None
                if mp4 in FILE_CACHE:
                    try:
                        sent_vid = await client.send_video(
                            query.message.chat.id,
                            FILE_CACHE[mp4],
                            caption=caption,
                            supports_streaming=True,
                            protect_content=True
                        )
                    except Exception:
                        pass

                if not sent_vid:
                    try:
                        sent_vid = await client.send_video(
                            query.message.chat.id,
                            mp4,
                            caption=caption,
                            supports_streaming=True,
                            protect_content=True
                        )
                        if sent_vid.video:
                            FILE_CACHE[mp4] = sent_vid.video.file_id
                    except Exception:
                        btn = InlineKeyboardMarkup(
                            [[InlineKeyboardButton("▶️ Open HD Player", url=mp4)]]
                        )
                        await client.send_message(query.message.chat.id, f"{caption}\n\n⚡ Stream online:", reply_markup=btn)

                if sent_vid:
                    asyncio.create_task(auto_delete_msg(query.message.chat.id, sent_vid.id))
        else:
            if not media["images"]:
                await client.send_message(query.message.chat.id, "⚠️ Stream currently unavailable.")

        try:
            await status.delete()
        except Exception:
            pass

@app.on_message(filters.command("search"))
async def search_cmd(client, message):
    if not await is_joined(client, message.from_user.id):
        await start_handler(client, message)
        return

    q = " ".join(message.command[1:]).strip()
    if not q:
        await message.reply("Usage: `/search bhabhi`")
        return

    msg = await message.reply(f"🔍 Searching for `{q}`...")
    vids = fetch_vids(f"{SITE_URL}/?s={q}")
    if not vids:
        await msg.edit_text("❌ No results found.")
        return

    USER_VIDS[message.from_user.id] = vids
    kb = [
        [InlineKeyboardButton(f"▶️ {v['title']}", callback_data=f"play_{i}")]
        for i, v in enumerate(vids[:20])
    ]
    kb.append([InlineKeyboardButton("❌ Close", callback_data="close")])
    await msg.edit_text(f"🔎 **Results for '{q}':**", reply_markup=InlineKeyboardMarkup(kb))

@app.on_chat_join_request()
async def auto_approve(client, m):
    try:
        await client.approve_chat_join_request(m.chat.id, m.from_user.id)
    except Exception:
        pass

# ==========================================
# 🚀 MAIN ASYNC RUNNER
# ==========================================
async def main():
    print("Starting Flask Web Server...")
    keep_alive()
    print("Fetching Categories...")
    fetch_cats()
    print(f"Categories Loaded: {len(GLOBAL_CATS)}")
    print("Starting Pyrogram Client...")
    await app.start()
    print("🚀 BOT IS LIVE AND RUNNING ON RAILWAY 24/7!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    loop.run_until_complete(main())
