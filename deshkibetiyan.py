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
from pyrogram.errors import UserNotParticipant

# ==========================================
# 🌐 WEB SERVER (Keeping Render Awake)
# ==========================================
web = Flask(__name__)
@web.route('/')
def home(): 
    return "Bot is Running 24/7! Ping received."

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web.run(host="0.0.0.0", port=port)

def keep_alive():
    Thread(target=run_web, daemon=True).start()

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
API_ID = 35025088
API_HASH = "b409c31c0c25b927dca36fcc0d05c149"
BOT_TOKEN = "8602387086:AAGiV9tLsCpuFXxq1YFxZtRPZr6CbFihBh0"

# 📢 STRICT CHANNELS
CHANNELS = [
    {"id": -1004460480150, "link": "https://t.me/+TsUwg9LKW2wzNDE1"},
    {"id": -1004442592541, "link": "https://t.me/+NdBuwwTcRQo2NDU1"}
]

AUTO_DELETE_TIME = 300 
SITE_URL = "https://sundarikanya.ink"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

logging.basicConfig(level=logging.INFO)
app = Client("VIPPrivateVault", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

GLOBAL_CATS, USER_VIDS, FILE_CACHE = {}, {}, {}

# ==========================================
# 🔒 THE ULTIMATE LOCK (NO BYPASS)
# ==========================================
async def is_user_joined_all(client, user_id):
    for channel in CHANNELS:
        try:
            member = await client.get_chat_member(channel["id"], user_id)
            if member.status not in [enums.ChatMemberStatus.MEMBER, 
                                     enums.ChatMemberStatus.ADMINISTRATOR, 
                                     enums.ChatMemberStatus.OWNER]:
                return False
        except UserNotParticipant:
            return False
        except Exception:
            # Agar bot check nahi kar paa raha (Admin error), toh block rakho.
            return False 
    return True

def get_force_sub_keyboard():
    buttons = [[InlineKeyboardButton(f"📢 Join Channel {i+1}", url=c["link"])] for i, c in enumerate(CHANNELS)]
    buttons.append([InlineKeyboardButton("✅ Verify & Start Bot", callback_data="verify_now")])
    return InlineKeyboardMarkup(buttons)

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================

@app.on_message(filters.command("start"))
async def start_handler(client, message):
    user_id = message.from_user.id
    if not await is_user_joined_all(client, user_id):
        await message.reply(
            "🔒 **ACCESS DENIED!**\n\nContent unlock karne ke liye aapko hamare **Dono Channels** join karne honge.", 
            reply_markup=get_force_sub_keyboard()
        )
        return
    
    if not GLOBAL_CATS:
        try:
            r = requests.get(SITE_URL, headers=HEADERS, timeout=12)
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select('.wp-block-heading a, .entry-content a, .menu-item a'):
                name = re.sub(r'(?i)sundari\s*kanya|sundarikanya\.ink', '', a.get_text(strip=True))
                url = a.get('href')
                if url and SITE_URL in url and len(name) > 2:
                    GLOBAL_CATS[name] = url
        except: pass

    kb = [[KeyboardButton(c)] for c in list(GLOBAL_CATS.keys())[:15]]
    kb.append([KeyboardButton("🔍 Search"), KeyboardButton("🔄 Refresh Menu")])
    await message.reply("💎 **Media Vault Dashboard Active**", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

@app.on_message(filters.text & ~filters.command(["start", "search"]))
async def menu_handler(client, message):
    if not await is_user_joined_all(client, message.from_user.id):
        await start_handler(client, message); return

    text = message.text
    if text == "🔄 Refresh Menu":
        await start_handler(client, message); return

    if text in GLOBAL_CATS:
        load = await message.reply(f"⏳ **Loading {text}...**", quote=True)
        try:
            r = requests.get(GLOBAL_CATS[text], headers=HEADERS)
            soup = BeautifulSoup(r.text, "html.parser")
            vids = []
            for a in soup.select('h2 a, h3 a, article a, .entry-title a'):
                t = re.sub(r'(?i)sundari\s*kanya|sundarikanya\.ink', '', a.get_text(strip=True))
                u = a.get('href')
                if u and SITE_URL in u and len(t) > 3:
                    vids.append({'title': t[:50], 'url': u})
            
            if not vids: 
                await load.edit("❌ Empty Folder."); return
            
            USER_VIDS[message.from_user.id] = vids
            btns = [[InlineKeyboardButton(f"▶️ {v['title']}", callback_data=f"play_{i}")] for i, v in enumerate(vids[:20])]
            await load.edit(f"📂 **{text}**", reply_markup=InlineKeyboardMarkup(btns))
        except:
            await load.edit("❌ Connection Error.")

@app.on_callback_query()
async def cb_handler(client, query):
    if query.data == "verify_now":
        if await is_user_joined_all(client, query.from_user.id):
            await query.answer("✅ Verified!", show_alert=True)
            await query.message.delete()
            await start_handler(client, query.message)
        else: 
            await query.answer("❌ Dono channels join karein pehle!", show_alert=True)
        return

    if query.data.startswith("play_"):
        if not await is_user_joined_all(client, query.from_user.id):
            await query.answer("🔒 Join both channels first!", show_alert=True); return

        idx = int(query.data.split("_")[1])
        vid = USER_VIDS[query.from_user.id][idx]
        status = await query.message.reply("🚀 **Streaming...**")
        
        try:
            r = requests.get(vid['url'], headers=HEADERS)
            mp4s = list(set(re.findall(r"https?://[^\s\"'<>]+\.mp4", r.text)))
            for mp4 in mp4s[:1]:
                await client.send_video(query.message.chat.id, mp4, caption=f"🎬 {vid['title']}", protect_content=True)
            await status.delete()
        except:
            await status.edit("⚠️ Stream Error.")

@app.on_chat_join_request()
async def auto_approve(client, message):
    try: await client.approve_chat_join_request(message.chat.id, message.from_user.id)
    except: pass

if __name__ == "__main__":
    keep_alive()
    app.run()
