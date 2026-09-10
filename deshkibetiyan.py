import os
import re
import time
import requests
import logging
from bs4 import BeautifulSoup
from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    InputMediaPhoto
)
from pyrogram.errors import UserNotParticipant, FloodWait

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
API_ID = 35025088
API_HASH = "b409c31c0c25b927dca36fcc0d05c149"
BOT_TOKEN = "8602387086:AAGiV9tLsCpuFXxq1YFxZtRPZr6CbFihBh0"

# 📢 PRIVATE CHANNEL SETTINGS
FORCE_SUB_CHANNEL = -1004460480150
CHANNEL_LINK = "https://t.me/+TsUwg9LKW2wzNDE1"

SITE_URL = "https://sundarikanya.ink"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}

logging.basicConfig(level=logging.ERROR)
app = Client("VIPPrivateVault", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Persistent Memory
GLOBAL_CATS = {}
USER_VIDS = {}
FILE_CACHE = {}

# ==========================================
# 🛡️ CLEANING & FILTERS
# ==========================================
def clean_branding(text):
    if not text: return ""
    text = re.sub(r'(?i)sundari\s*kanya|sundarikanya\.ink', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_junk_image(url):
    u = url.lower()
    return any(x in u for x in ['logo', 'butterfly', 'icon', 'avatar', '626x626', 'favicon'])

def get_emoji(name):
    n = name.lower()
    if 'bhabhi' in n: return "💃 "
    if 'snap' in n: return "📸 "
    if 'sexy' in n or 'hot' in n: return "🔥 "
    if 'wife' in n: return "👰 "
    if 'milf' in n: return "🍼 "
    if 'viral' in n or 'trend' in n: return "⚡ "
    if 'desi' in n: return "🇮🇳 "
    return "📁 "

# ==========================================
# 🔒 FORCE JOIN CHECKER (Pyrogram v2)
# ==========================================
async def is_subscribed(client, user_id):
    try:
        member = await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        if member.status in [enums.ChatMemberStatus.MEMBER, 
                            enums.ChatMemberStatus.ADMINISTRATOR, 
                            enums.ChatMemberStatus.OWNER]:
            return True
    except UserNotParticipant: return False
    except Exception: return True
    return False

# ==========================================
# 🔍 POWER SCRAPERS (FIXED TITLES)
# ==========================================
def fetch_cats():
    try:
        r = requests.get(SITE_URL, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        GLOBAL_CATS.clear()
        # Astra & Gutenberg specific selectors
        for a in soup.select('.wp-block-heading a, .entry-content a, .menu-item a, .cat-item a'):
            url, name = a.get('href'), clean_branding(a.get_text(strip=True))
            if url and SITE_URL in url and len(name) > 2:
                if not any(x in name.lower() for x in ['home', 'login', 'contact', 'dmca', 'membership', 'search', 'about', 'author']):
                    disp_name = get_emoji(name) + name
                    if disp_name not in GLOBAL_CATS:
                        GLOBAL_CATS[disp_name] = url
        return True
    except: return False

def fetch_vids(page_url):
    vids = []
    try:
        r = requests.get(page_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        # Powerful selectors for video titles
        items = soup.select('h2 a, h3 a, .entry-title a, article a, .pt-cv-title a')
        for a in items:
            title = clean_branding(a.get_text(strip=True))
            url = a.get('href')
            # Title validation: Ensure it's not empty or too short
            if url and SITE_URL in url and len(title) > 3:
                if not any(x in url.lower() for x in ['/author/', '/category/', '/tag/', '/page/']):
                    if not any(v['url'] == url for v in vids):
                        vids.append({'title': title[:50], 'url': url})
        return vids
    except: return []

def extract_media(post_url):
    media = {'videos': [], 'images': []}
    try:
        r = requests.get(post_url, headers=HEADERS, timeout=12)
        html = r.text
        media['videos'] = list(set(re.findall(r"https?://[^\s\"'<>]+\.mp4", html)))
        soup = BeautifulSoup(html, "html.parser")
        for img in soup.select(".entry-content img, article img")[:3]:
            src = img.get("src") or img.get("data-src")
            if src and src.startswith("http") and not is_junk_image(src):
                media['images'].append(src)
        return media
    except: return media

def download_video(url, path):
    with requests.get(url, headers=HEADERS, stream=True) as r:
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024): f.write(chunk)
    return path

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================

@app.on_message(filters.command("start"))
async def start_handler(client, message):
    user_id = message.from_user.id
    if not await is_subscribed(client, user_id):
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Private Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ Verify & Start", callback_data="verify_now")]
        ])
        await message.reply("🔒 **ACCESS DENIED!**\n\nIs bot ka content dekhne ke liye hamara Private Channel join karna zaroori hai.", reply_markup=btn)
        return

    if not GLOBAL_CATS: fetch_cats()
    
    # 📱 2-Column Responsive Keyboard
    kb = []
    row = []
    cats_list = list(GLOBAL_CATS.keys())[:20]
    for cat in cats_list:
        row.append(KeyboardButton(cat))
        if len(row) == 2:
            kb.append(row); row = []
    if row: kb.append(row)
    
    # 🔍 Search & Refresh Row (Always Visible)
    kb.append([KeyboardButton("🔍 Search"), KeyboardButton("🔄 Refresh Menu")])
    
    await message.reply("💎 **Media Dashboard Active**\nSelect a folder from below:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

@app.on_message(filters.text & ~filters.command(["start", "search"]))
async def menu_handler(client, message):
    if not await is_subscribed(client, message.from_user.id): return
    text = message.text

    if text == "🔄 Refresh Menu":
        fetch_cats()
        await start_handler(client, message); return
    
    if text == "🔍 Search":
        await message.reply("🔍 **Search Mode**\nType `/search keyword` (e.g. `/search bhabhi`) to find videos."); return

    if text in GLOBAL_CATS:
        load = await message.reply(f"⏳ **Loading {text}...**", quote=True)
        vids = fetch_vids(GLOBAL_CATS[text])
        if not vids:
            await load.edit("❌ Is category mein abhi koi video nahi mili."); return
            
        USER_VIDS[message.from_user.id] = vids
        btns = [[InlineKeyboardButton(f"▶️ {v['title']}", callback_data=f"play_{i}")] for i, v in enumerate(vids[:20])]
        btns.append([InlineKeyboardButton("❌ Close List", callback_data="close")])
        await load.edit(f"📂 **Category: {text}**\nSelect a file to play:", reply_markup=InlineKeyboardMarkup(btns))

@app.on_message(filters.command("search"))
async def search_command(client, message):
    if not await is_subscribed(client, message.from_user.id): return
    query = " ".join(message.command[1:]).strip()
    if not query:
        await message.reply("Usage: `/search bhabhi`")
        return
    msg = await message.reply(f"🔍 Searching for `{query}`...")
    vids = fetch_vids(f"{SITE_URL}/?s={query}")
    if not vids:
        await msg.edit("❌ No results found."); return
    USER_VIDS[message.from_user.id] = vids
    btns = [[InlineKeyboardButton(f"▶️ {v['title']}", callback_data=f"play_{i}")] for i, v in enumerate(vids[:20])]
    await msg.edit(f"🔎 **Search Results for:** `{query}`", reply_markup=InlineKeyboardMarkup(btns))

@app.on_callback_query()
async def callback_handler(client, query):
    data = query.data
    user_id = query.from_user.id

    if data == "verify_now":
        if await is_subscribed(client, user_id):
            await query.answer("✅ Success!", show_alert=True)
            await query.message.delete()
            await start_handler(client, query.message)
        else:
            await query.answer("❌ Pehle Join Karein!", show_alert=True)
        return

    if data == "close":
        await query.message.delete(); return

    if data.startswith("play_"):
        idx = int(data.split("_")[1])
        if user_id not in USER_VIDS:
            await query.answer("Session expired. Select category again.", show_alert=True); return
        
        vid = USER_VIDS[user_id][idx]
        await query.answer(f"Loading: {vid['title']}")
        status = await query.message.reply("⏳ **Processing Media...**")
        media = extract_media(vid['url'])
        
        if media['images']:
            try: await client.send_photo(query.message.chat.id, media['images'][0], caption=f"🖼 **Preview:** {vid['title']}")
            except: pass

        if media['videos']:
            for i, mp4 in enumerate(media['videos'][:2]):
                caption = f"🎬 **{vid['title']}**"
                if len(media['videos']) > 1: caption += f" (Part {i+1})"
                
                if mp4 in FILE_CACHE:
                    await client.send_video(query.message.chat.id, FILE_CACHE[mp4], caption=caption)
                else:
                    try:
                        sent = await client.send_video(query.message.chat.id, mp4, caption=caption, supports_streaming=True)
                        FILE_CACHE[mp4] = sent.video.file_id
                    except:
                        temp = f"file_{user_id}_{i}.mp4"
                        try:
                            await status.edit("⏬ **Downloading Large File...**")
                            download_video(mp4, temp)
                            await status.edit("⬆️ **Uploading to Player...**")
                            sent = await client.send_video(query.message.chat.id, temp, caption=caption, supports_streaming=True)
                            FILE_CACHE[mp4] = sent.video.file_id
                        except:
                            await client.send_message(query.message.chat.id, f"⚠️ Large File: [Watch Online]({mp4})")
                        finally:
                            if os.path.exists(temp): os.remove(temp)
        await status.delete()

print("🚀 ULTIMATE SAAS BOT IS RUNNING!")
fetch_cats()
app.run()