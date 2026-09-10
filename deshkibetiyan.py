import sys
import asyncio

# Asyncio Loop Fix for Render/Linux
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import os
import re
import time
import requests
import logging
from threading import Thread
from flask import Flask
from bs4 import BeautifulSoup
from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    InputMediaPhoto
)
from pyrogram.errors import UserNotParticipant, FloodWait

# ==========================================
# 🌐 KEEP-ALIVE WEB SERVER (Render 24/7)
# ==========================================
web = Flask(__name__)

@web.route('/')
def home():
    return "Bot is Live 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_web, daemon=True)
    t.start()

# ==========================================
# ⚙️ CONFIGURATION (DUAL CHANNELS)
# ==========================================
API_ID = 35025088
API_HASH = "b409c31c0c25b927dca36fcc0d05c149"
BOT_TOKEN = "8602387086:AAGiV9tLsCpuFXxq1YFxZtRPZr6CbFihBh0"

# 📢 CHANNEL 1
CHANNEL_1_ID = -1004460480150
CHANNEL_1_LINK = "https://t.me/+TsUwg9LKW2wzNDE1"

# 📢 CHANNEL 2 (👈 Yahan Channel 2 ki numeric ID dalo -100...)
CHANNEL_2_ID = -1002233445566  # Replace with actual ID if different
CHANNEL_2_LINK = "https://t.me/+NdBuwwTcRQo2NDU1"

# ⏱️ AUTO DELETE TIMER (300 Seconds = 5 Minutes)
AUTO_DELETE_TIME = 300

SITE_URL = "https://sundarikanya.ink"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

logging.basicConfig(level=logging.ERROR)

app = Client(
    "VIPPrivateVault",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

GLOBAL_CATS = {}
USER_VIDS = {}
FILE_CACHE = {}

# Background Auto Delete Task
async def auto_delete_msg(chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try:
        await app.delete_messages(chat_id=chat_id, message_ids=message_id)
    except Exception as e:
        print(f"Auto Delete Note: {e}")

# ==========================================
# 🔮 AUTO-ACCEPT JOIN REQUESTS FOR ALL CHATS
# ==========================================
@app.on_chat_join_request()
async def auto_approve_join_request(client, message):
    try:
        await client.approve_chat_join_request(message.chat.id, message.from_user.id)
        await client.send_message(
            message.from_user.id,
            "✅ **Aapki Join Request Accept Ho Gayi Hai!**\n\nAb aap Bot mein `/start` karke content dekh sakte hain."
        )
    except Exception as e:
        print(f"Auto Approve Note: {e}")

# ==========================================
# 🛡️ CLEANING & FILTERS
# ==========================================
def clean_branding(text):
    if not text: return ""
    text = re.sub(r'(?i)sundari\s*kanya|sundarikanya\.ink', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

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
    return "📁 "

# ==========================================
# 🔒 DUAL FORCE JOIN CHECKER
# ==========================================
async def is_subscribed_single(client, channel_id, user_id):
    try:
        member = await client.get_chat_member(channel_id, user_id)
        status_str = str(member.status).lower()
        if any(s in status_str for s in ["member", "administrator", "owner", "creator"]):
            return True
        return False
    except UserNotParticipant:
        return False
    except Exception as e:
        print(f"Force Join Check Note ({channel_id}): {e}")
        return True # Fallback to true if bot has permission error

async def is_user_joined_all(client, user_id):
    sub1 = await is_subscribed_single(client, CHANNEL_1_ID, user_id)
    sub2 = await is_subscribed_single(client, CHANNEL_2_ID, user_id)
    return sub1 and sub2

def get_force_sub_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel 1", url=CHANNEL_1_LINK)],
        [InlineKeyboardButton("📢 Join Channel 2", url=CHANNEL_2_LINK)],
        [InlineKeyboardButton("✅ Verify All & Start", callback_data="verify_now")]
    ])

# ==========================================
# 🔍 SCRAPERS
# ==========================================
def fetch_cats():
    try:
        r = requests.get(SITE_URL, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        GLOBAL_CATS.clear()
        for a in soup.select('.wp-block-heading a, .entry-content a, .menu-item a, .cat-item a'):
            url = a.get('href') or ""
            name = clean_branding(a.get_text(strip=True))
            if not url.startswith("http") and url.startswith("/"):
                url = SITE_URL + url
            if url and SITE_URL in url and len(name) > 2:
                ignore = ['home', 'login', 'contact', 'dmca', 'membership', 'search', 'about', 'author', 'mirror']
                if not any(x in name.lower() for x in ignore):
                    disp_name = get_emoji(name) + name
                    if disp_name not in GLOBAL_CATS:
                        GLOBAL_CATS[disp_name] = url
        return True
    except Exception as e:
        print(f"Cat Error: {e}")
        return False

def fetch_vids(page_url):
    vids = []
    try:
        r = requests.get(page_url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select('h2.entry-title a, h2 a, h3 a, .entry-title a, article a, .pt-cv-title a, .post-title a')
        for a in items:
            title = clean_branding(a.get_text(strip=True))
            url = a.get('href') or ""
            if not url.startswith("http") and url.startswith("/"):
                url = SITE_URL + url
            if url and len(title) > 3 and SITE_URL in url:
                bad_urls = ['/author/', '/category/', '/tag/', '/page/', '?s=']
                if not any(x in url.lower() for x in bad_urls):
                    if not any(v['url'] == url for v in vids):
                        vids.append({'title': title[:50], 'url': url})
        return vids[:20]
    except Exception as e:
        print(f"Vid Error: {e}")
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
    except Exception as e:
        print(f"Media Error: {e}")
        return media

def download_file(url, file_path):
    with requests.get(url, headers=HEADERS, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(file_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk: f.write(chunk)
    return file_path

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================
@app.on_message(filters.command("start"))
async def start_handler(client, message):
    user_id = message.from_user.id
    if not await is_user_joined_all(client, user_id):
        await message.reply(
            "🔒 **ACCESS DENIED!**\n\n"
            "Is bot ka content dekhne ke liye hamare **Dono Private Channels** join karna / request bhejna zaroori hai.\n\n"
            "1. Dono channels ke links par click karke Request bhejein.\n"
            "2. Phir **Verify All & Start** button dabayein.",
            reply_markup=get_force_sub_keyboard()
        )
        return

    if not GLOBAL_CATS: fetch_cats()
    
    kb = []
    row = []
    for cat in list(GLOBAL_CATS.keys())[:20]:
        row.append(KeyboardButton(cat))
        if len(row) == 2:
            kb.append(row); row = []
    if row: kb.append(row)
    
    kb.append([KeyboardButton("🔍 Search"), KeyboardButton("🔄 Refresh Menu")])
    await message.reply("💎 **Media Dashboard Active**\nSelect a folder from below:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

@app.on_message(filters.command("search"))
async def search_command(client, message):
    if not await is_user_joined_all(client, message.from_user.id):
        await start_handler(client, message)
        return
        
    query = " ".join(message.command[1:]).strip()
    if not query:
        await message.reply("Usage: `/search bhabhi`")
        return
        
    msg = await message.reply(f"🔍 Searching for `{query}`...")
    vids = fetch_vids(f"{SITE_URL}/?s={requests.utils.quote(query)}")
    if not vids:
        await msg.edit_text("❌ No results found.")
        return
        
    USER_VIDS[message.from_user.id] = vids
    btns = [[InlineKeyboardButton(f"▶️ {v['title']}", callback_data=f"play_{i}")] for i, v in enumerate(vids)]
    btns.append([InlineKeyboardButton("❌ Close", callback_data="close")])
    await msg.edit_text(f"🔎 **Search Results for:** `{query}`", reply_markup=InlineKeyboardMarkup(btns))

@app.on_message(filters.text & ~filters.command(["start", "search"]))
async def menu_handler(client, message):
    if not await is_user_joined_all(client, message.from_user.id):
        await start_handler(client, message)
        return
        
    text = message.text or ""

    if text == "🔄 Refresh Menu":
        fetch_cats()
        await start_handler(client, message)
        return

    if text == "🔍 Search":
        await message.reply("🔍 Type `/search keyword`\nExample: `/search bhabhi`")
        return

    if text in GLOBAL_CATS:
        load = await message.reply(f"⏳ **Loading {text}...**", quote=True)
        vids = fetch_vids(GLOBAL_CATS[text])
        if not vids:
            await load.edit_text("❌ Is category mein abhi koi video nahi mili.")
            return

        USER_VIDS[message.from_user.id] = vids
        btns = [[InlineKeyboardButton(f"▶️ {v['title']}", callback_data=f"play_{i}")] for i, v in enumerate(vids)]
        btns.append([InlineKeyboardButton("❌ Close List", callback_data="close")])
        await load.edit_text(f"📂 **Category: {text}**\nSelect a file to play:", reply_markup=InlineKeyboardMarkup(btns))

@app.on_callback_query()
async def callback_handler(client, query):
    data = query.data or ""
    user_id = query.from_user.id

    if data == "verify_now":
        if await is_user_joined_all(client, user_id):
            await query.answer("✅ Success! Welcome.", show_alert=True)
            try: await query.message.delete()
            except: pass
            await start_handler(client, query.message)
        else:
            await query.answer("❌ Aapne Dono Channels Join Nahi Kiye / Request Nahi Bheji!", show_alert=True)
        return

    if data == "close":
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("play_"):
        if not await is_user_joined_all(client, user_id):
            await query.answer("🔒 Pehle Dono Channels Join Karein!", show_alert=True)
            return

        idx = int(data.split("_")[1])
        if user_id not in USER_VIDS or idx >= len(USER_VIDS[user_id]):
            await query.answer("Session expired. Select category again.", show_alert=True)
            return

        vid = USER_VIDS[user_id][idx]
        await query.answer(f"Loading: {vid['title']}")
        status = await query.message.reply("⏳ **Processing Media...**")
        media = extract_media(vid['url'])

        # Photos (Protect Content + Auto Delete)
        if media['images']:
            try:
                sent_img = await client.send_photo(
                    query.message.chat.id, 
                    media['images'][0], 
                    caption=f"🖼 **{vid['title']}**\n\n⏳ _Auto-deleting in 5 minutes!_",
                    protect_content=True
                )
                asyncio.create_task(auto_delete_msg(query.message.chat.id, sent_img.id, AUTO_DELETE_TIME))
            except: pass

        # Videos (Protect Content + Auto Delete)
        if media['videos']:
            total = len(media['videos'])
            for i, mp4 in enumerate(media['videos'][:3]):
                caption = f"🎬 **{vid['title']}**"
                if total > 1: caption += f" (Part {i+1}/{min(total, 3)})"
                caption += "\n\n⏳ _Auto-deleting in 5 minutes to prevent copyright!_"

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
                    except: pass

                if not sent_vid:
                    try:
                        sent_vid = await client.send_video(
                            query.message.chat.id, 
                            mp4, 
                            caption=caption, 
                            supports_streaming=True,
                            protect_content=True
                        )
                        if sent_vid.video: FILE_CACHE[mp4] = sent_vid.video.file_id
                    except Exception:
                        temp = f"temp_{user_id}_{i}.mp4"
                        try:
                            await status.edit_text("⏬ **Large file downloading...**")
                            download_file(mp4, temp)
                            await status.edit_text("⬆️ **Uploading to Telegram...**")
                            sent_vid = await client.send_video(
                                query.message.chat.id, 
                                temp, 
                                caption=caption, 
                                supports_streaming=True,
                                protect_content=True
                            )
                            if sent_vid.video: FILE_CACHE[mp4] = sent_vid.video.file_id
                        except Exception:
                            btn = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Open HD Player", url=mp4)]])
                            await client.send_message(query.message.chat.id, f"{caption}\n\n⚡ Stream online:", reply_markup=btn)
                        finally:
                            if os.path.exists(temp): os.remove(temp)

                if sent_vid:
                    asyncio.create_task(auto_delete_msg(query.message.chat.id, sent_vid.id, AUTO_DELETE_TIME))
        else:
            if not media['images']:
                await client.send_message(query.message.chat.id, "⚠️ Stream currently unavailable.")

        try: await status.delete()
        except: pass

if __name__ == "__main__":
    keep_alive()
    fetch_cats()
    app.run()
