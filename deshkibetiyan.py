import sys
import asyncio
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
def home(): return "Bot is Alive 24/7!"
def run_web():
    port = int(os.environ.get("PORT", 8080))
    web.run(host="0.0.0.0", port=port)
def keep_alive():
    Thread(target=run_web, daemon=True).start()

# ==========================================
# ⚙️ CONFIGURATION (STRICT)
# ==========================================
API_ID = 35025088
API_HASH = "b409c31c0c25b927dca36fcc0d05c149"
BOT_TOKEN = "8602387086:AAGiV9tLsCpuFXxq1YFxZtRPZr6CbFihBh0"

# 📢 STRICT CHANNELS LIST
CHANNELS = [
    {"id": -1004460480150, "link": "https://t.me/+TsUwg9LKW2wzNDE1"},
    {"id": -1004442592541, "link": "https://t.me/+NdBuwwTcRQo2NDU1"}
]

AUTO_DELETE_TIME = 300 
SITE_URL = "https://sundarikanya.ink"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

logging.basicConfig(level=logging.ERROR)

# Initialize Client with in_memory session
app = Client("VIPPrivateVault", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# Cache Storage
GLOBAL_CATS, USER_VIDS, FILE_CACHE = {}, {}, {}

# ==========================================
# 🔒 THE ULTIMATE LOCK (NO BYPASS)
# ==========================================
async def is_user_joined_all(client, user_id):
    """Checks if user is in ALL channels. Returns False if even one check fails."""
    for channel in CHANNELS:
        try:
            member = await client.get_chat_member(channel["id"], user_id)
            # Check if status is valid
            if member.status not in [enums.ChatMemberStatus.MEMBER, 
                                     enums.ChatMemberStatus.ADMINISTRATOR, 
                                     enums.ChatMemberStatus.OWNER]:
                return False
        except UserNotParticipant:
            return False # Strictly Not Joined
        except Exception as e:
            # If bot can't check (not admin), we block for safety
            print(f"Critial Check Error: {e}")
            return False 
    return True

def get_force_sub_keyboard():
    buttons = [[InlineKeyboardButton(f"📢 Join Channel {i+1}", url=c["link"])] for i, c in enumerate(CHANNELS)]
    buttons.append([InlineKeyboardButton("✅ Verify & Start Bot", callback_data="verify_now")])
    return InlineKeyboardMarkup(buttons)

# ==========================================
# 🛡️ CLEANING & AUTO-DELETE
# ==========================================
async def auto_delete_msg(chat_id, message_id):
    await asyncio.sleep(AUTO_DELETE_TIME)
    try: await app.delete_messages(chat_id, message_id)
    except: pass

def clean_branding(text):
    if not text: return ""
    text = re.sub(r'(?i)sundari\s*kanya|sundarikanya\.ink', '', text)
    return re.sub(r'\s+', ' ', text).strip() or "Premium File"

# ==========================================
# 🔍 SCRAPERS
# ==========================================
def fetch_cats():
    try:
        r = requests.get(SITE_URL, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        GLOBAL_CATS.clear()
        for a in soup.select('.wp-block-heading a, .entry-content a, .menu-item a'):
            name = clean_branding(a.get_text(strip=True))
            url = a.get('href')
            if url and SITE_URL in url and len(name) > 2:
                if not any(x in name.lower() for x in ['home', 'login', 'dmca', 'membership']):
                    GLOBAL_CATS[name] = url
        return True
    except: return False

def fetch_vids(url):
    vids = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select('h2 a, h3 a, article a, .entry-title a'):
            t, u = clean_branding(a.get_text(strip=True)), a.get('href')
            if u and SITE_URL in u and len(t) > 3:
                if not any(x in u.lower() for x in ['/author/', '/category/', '/tag/']):
                    if not any(v['url'] == u for v in vids):
                        vids.append({'title': t[:50], 'url': u})
        return vids
    except: return []

# ==========================================
# 🤖 BOT HANDLERS (ALL WRAPPED IN LOCK)
# ==========================================

@app.on_message(filters.command("start"))
async def start_handler(client, message):
    if not await is_user_joined_all(client, message.from_user.id):
        await message.reply(
            "🔒 **ACCESS DENIED!**\n\nContent unlock karne ke liye aapko hamare **Dono Channels** join karne honge.\n\n"
            "Join karke niche **Verify** button dabayein.", 
            reply_markup=get_force_sub_keyboard()
        )
        return

    if not GLOBAL_CATS: fetch_cats()
    kb = []
    row = []
    for c in list(GLOBAL_CATS.keys())[:16]:
        row.append(KeyboardButton(c))
        if len(row) == 2: kb.append(row); row = []
    if row: kb.append(row)
    kb.append([KeyboardButton("🔍 Search"), KeyboardButton("🔄 Refresh Menu")])
    await message.reply("💎 **Media Dashboard Active**\nSelect Category:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

@app.on_message(filters.text & ~filters.command(["start", "search"]))
async def menu_handler(client, message):
    # Lock Check on every click
    if not await is_user_joined_all(client, message.from_user.id):
        await start_handler(client, message); return

    text = message.text
    if text == "🔄 Refresh Menu": fetch_cats(); await start_handler(client, message); return
    if text == "🔍 Search": await message.reply("Type `/search <keyword>`"); return
    
    if text in GLOBAL_CATS:
        load = await message.reply(f"⏳ **Loading {text}...**", quote=True)
        vids = fetch_vids(GLOBAL_CATS[text])
        if not vids: await load.edit("❌ Empty Folder."); return
        USER_VIDS[message.from_user.id] = vids
        btns = [[InlineKeyboardButton(f"▶️ {v['title']}", callback_data=f"play_{i}")] for i, v in enumerate(vids[:20])]
        await load.edit(f"📂 **Category: {text}**", reply_markup=InlineKeyboardMarkup(btns))

@app.on_callback_query()
async def cb_handler(client, query):
    if query.data == "verify_now":
        if await is_user_joined_all(client, query.from_user.id):
            await query.answer("✅ Verified! Press /start", show_alert=True)
            await query.message.delete()
            await start_handler(client, query.message)
        else: 
            await query.answer("❌ Aapne abhi tak dono channels join nahi kiye!", show_alert=True)
        return

    if query.data.startswith("play_"):
        # Double safety lock
        if not await is_user_joined_all(client, query.from_user.id):
            await query.answer("🔒 Pehle Dono Channels Join Karein!", show_alert=True)
            return

        idx = int(query.data.split("_")[1])
        vid = USER_VIDS[query.from_user.id][idx]
        status = await query.message.reply("🚀 **Streaming...**")
        
        r = requests.get(vid['url'], headers=HEADERS)
        mp4s = list(set(re.findall(r"https?://[^\s\"'<>]+\.mp4", r.text)))
        
        for i, mp4 in enumerate(mp4s[:2]):
            caption = f"🎬 **{vid['title']}**\n\n⏳ _Auto-deleting in 5 mins!_"
            try:
                sent = await client.send_video(query.message.chat.id, mp4, caption=caption, protect_content=True)
                asyncio.create_task(auto_delete_msg(query.message.chat.id, sent.id))
            except:
                await client.send_message(query.message.chat.id, f"🎬 {vid['title']}\n⚡ [Play Online]({mp4})")
        await status.delete()

@app.on_message(filters.command("search"))
async def search_cmd(client, message):
    if not await is_user_joined_all(client, message.from_user.id): return
    q = " ".join(message.command[1:])
    vids = fetch_vids(f"{SITE_URL}/?s={q}")
    USER_VIDS[message.from_user.id] = vids
    btns = [[InlineKeyboardButton(v['title'], callback_data=f"play_{i}")] for i, v in enumerate(vids[:20])]
    await message.reply(f"🔎 Results for {q}:", reply_markup=InlineKeyboardMarkup(btns))

@app.on_chat_join_request()
async def auto_approve(client, message):
    try: await client.approve_chat_join_request(message.chat.id, message.from_user.id)
    except: pass

if __name__ == "__main__":
    keep_alive()
    fetch_cats()
    app.run()
