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
# KEEP-ALIVE (Koyeb 24/7 ke liye zaroori)
# ==========================================
web = Flask(__name__)

@web.route("/")
def home():
    return "Bot is Alive 24/7!"

def run_web():
    web.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run_web, daemon=True)
    t.start()

# ==========================================
# CONFIG
# ==========================================
API_ID = 35025088
API_HASH = "b409c31c0c25b927dca36fcc0d05c149"
BOT_TOKEN = "8602387086:AAGiV9tLsCpuFXxq1YFxZtRPZr6CbFihBh0"

FORCE_SUB_CHANNEL = -1004460480150
CHANNEL_LINK = "https://t.me/+TsUwg9LKW2wzNDE1"

SITE_URL = "https://sundarikanya.ink"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

logging.basicConfig(level=logging.ERROR)
app = Client("VIPPrivateVault", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

GLOBAL_CATS = {}
USER_VIDS = {}
FILE_CACHE = {}

# ==========================================
# HELPERS
# ==========================================
def clean_branding(text):
    if not text:
        return ""
    text = re.sub(r"(?i)sundari\s*kanya|sundarikanya\.ink", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def is_junk_image(url):
    u = (url or "").lower()
    return any(x in u for x in ["logo", "butterfly", "icon", "avatar", "626x626", "favicon", "header"])

def get_emoji(name):
    n = name.lower()
    if "bhabhi" in n: return "💃 "
    if "snap" in n: return "📸 "
    if "sexy" in n or "hot" in n or "babe" in n: return "🔥 "
    if "wife" in n: return "👰 "
    if "milf" in n: return "🍼 "
    if "viral" in n or "trend" in n: return "⚡ "
    if "desi" in n: return "🇮🇳 "
    return "📁 "

# ==========================================
# FORCE JOIN
# ==========================================
async def is_subscribed(client, user_id):
    try:
        member = await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        if member.status in [
            enums.ChatMemberStatus.MEMBER,
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER,
        ]:
            return True
        return False
    except UserNotParticipant:
        return False
    except Exception as e:
        print(f"Force Join Note: {e}")
        return False

# ==========================================
# SCRAPERS
# ==========================================
def fetch_cats():
    try:
        r = requests.get(SITE_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        GLOBAL_CATS.clear()
        for a in soup.select(".wp-block-heading a, .entry-content a, .menu-item a, .cat-item a"):
            url = a.get("href") or ""
            name = clean_branding(a.get_text(strip=True))
            if not url.startswith("http") and url.startswith("/"):
                url = SITE_URL + url
            if url and SITE_URL in url and len(name) > 2:
                ignore = ["home", "login", "contact", "dmca", "membership", "search", "about", "author", "mirror"]
                if not any(x in name.lower() for x in ignore):
                    disp = get_emoji(name) + name
                    if disp not in GLOBAL_CATS:
                        GLOBAL_CATS[disp] = url
        return True
    except Exception as e:
        print(f"Cats Error: {e}")
        return False

def fetch_vids(page_url):
    vids = []
    try:
        r = requests.get(page_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select("h2.entry-title a, h2 a, h3 a, .entry-title a, article a, .pt-cv-title a, .post-title a")
        for a in items:
            title = clean_branding(a.get_text(strip=True))
            url = a.get("href") or ""
            if not url.startswith("http") and url.startswith("/"):
                url = SITE_URL + url
            if url and SITE_URL in url and len(title) > 3:
                bad = ["/author/", "/category/", "/tag/", "/page/", "?s="]
                if not any(x in url.lower() for x in bad):
                    if not any(v["url"] == url for v in vids):
                        vids.append({"title": title[:50], "url": url})
        return vids[:20]
    except Exception as e:
        print(f"Vids Error: {e}")
        return []

def extract_media(post_url):
    media = {"videos": [], "images": []}
    try:
        r = requests.get(post_url, headers=HEADERS, timeout=15)
        html = r.text
        archive = re.findall(r"https?://archive\.sundarikanya\.ink/[^\s\"'<>]+\.mp4", html)
        general = re.findall(r"https?://[^\s\"'<>]+\.mp4", html)
        media["videos"] = list(dict.fromkeys(archive + general))
        soup = BeautifulSoup(html, "html.parser")
        for img in soup.select(".entry-content img, article img")[:4]:
            src = img.get("src") or img.get("data-src")
            if src and src.startswith("http") and not src.endswith((".svg", ".gif")):
                if not is_junk_image(src):
                    media["images"].append(src)
        media["images"] = list(dict.fromkeys(media["images"]))[:3]
        return media
    except Exception as e:
        print(f"Media Error: {e}")
        return media

def download_video(url, path):
    with requests.get(url, headers=HEADERS, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return path

# ==========================================
# HANDLERS
# ==========================================
@app.on_message(filters.command("start"))
async def start_handler(client, message):
    user_id = message.from_user.id
    if not await is_subscribed(client, user_id):
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Private Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ Verify & Start", callback_data="verify_now")],
        ])
        await message.reply(
            "🔒 **ACCESS DENIED!**\n\n"
            "Bot use karne se pehle Private Channel join karo.\n"
            "Phir **Verify & Start** dabao.",
            reply_markup=btn,
        )
        return

    if not GLOBAL_CATS:
        fetch_cats()

    kb = []
    row = []
    for cat in list(GLOBAL_CATS.keys())[:20]:
        row.append(KeyboardButton(cat))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([KeyboardButton("🔍 Search"), KeyboardButton("🔄 Refresh Menu")])

    await message.reply(
        "💎 **Media Dashboard Active**\nSelect a folder from below:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
    )

@app.on_message(filters.command("search"))
async def search_command(client, message):
    if not await is_subscribed(client, message.from_user.id):
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
    if not await is_subscribed(client, message.from_user.id):
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
        await load.edit_text(
            f"📂 **Category: {text}**\nSelect a file to play:",
            reply_markup=InlineKeyboardMarkup(btns),
        )

@app.on_callback_query()
async def callback_handler(client, query):
    data = query.data or ""
    user_id = query.from_user.id

    if data == "verify_now":
        if await is_subscribed(client, user_id):
            await query.answer("✅ Success!", show_alert=True)
            try:
                await query.message.delete()
            except:
                pass
            await start_handler(client, query.message)
        else:
            await query.answer("❌ Pehle Join Karein!", show_alert=True)
        return

    if data == "close":
        try:
            await query.message.delete()
        except:
            pass
        return

    if data.startswith("play_"):
        if not await is_subscribed(client, user_id):
            await query.answer("🔒 Pehle Channel Join Karein!", show_alert=True)
            return

        idx = int(data.split("_")[1])
        if user_id not in USER_VIDS or idx >= len(USER_VIDS[user_id]):
            await query.answer("Session expired. Category dubara select karo.", show_alert=True)
            return

        vid = USER_VIDS[user_id][idx]
        await query.answer(f"Loading: {vid['title']}")
        status = await query.message.reply("⏳ **Processing Media...**")
        media = extract_media(vid["url"])

        if media["images"]:
            try:
                if len(media["images"]) == 1:
                    await client.send_photo(
                        query.message.chat.id,
                        media["images"][0],
                        caption=f"🖼 {vid['title']}",
                    )
                else:
                    group = [InputMediaPhoto(p) for p in media["images"]]
                    await client.send_media_group(query.message.chat.id, group)
            except:
                pass

        if media["videos"]:
            total = len(media["videos"])
            for i, mp4 in enumerate(media["videos"][:3]):
                caption = f"🎬 **{vid['title']}**"
                if total > 1:
                    caption += f" (Part {i+1}/{min(total,3)})"

                if mp4 in FILE_CACHE:
                    try:
                        await client.send_video(
                            query.message.chat.id,
                            FILE_CACHE[mp4],
                            caption=caption,
                            supports_streaming=True,
                        )
                        continue
                    except:
                        pass

                try:
                    sent = await client.send_video(
                        query.message.chat.id,
                        mp4,
                        caption=caption,
                        supports_streaming=True,
                    )
                    if sent.video:
                        FILE_CACHE[mp4] = sent.video.file_id
                except Exception:
                    temp = f"temp_{user_id}_{i}.mp4"
                    try:
                        await status.edit_text("⏬ **Large file downloading...**")
                        download_video(mp4, temp)
                        await status.edit_text("⬆️ **Uploading to Telegram...**")
                        sent = await client.send_video(
                            query.message.chat.id,
                            temp,
                            caption=caption,
                            supports_streaming=True,
                        )
                        if sent.video:
                            FILE_CACHE[mp4] = sent.video.file_id
                    except Exception:
                        btn = InlineKeyboardMarkup(
                            [[InlineKeyboardButton("▶️ Open HD Player", url=mp4)]]
                        )
                        await client.send_message(
                            query.message.chat.id,
                            f"{caption}\n\n⚡ Stream online:",
                            reply_markup=btn,
                        )
                    finally:
                        if os.path.exists(temp):
                            os.remove(temp)
        else:
            if not media["images"]:
                await client.send_message(
                    query.message.chat.id,
                    "⚠️ Stream currently unavailable.",
                )

        try:
            await status.delete()
        except:
            pass

# ==========================================
# BOOT
# ==========================================
if __name__ == "__main__":
    print("Starting keep-alive web server...")
    keep_alive()
    print("Fetching categories...")
    fetch_cats()
    print(f"Categories loaded: {len(GLOBAL_CATS)}")
    print("🚀 BOT LIVE 24/7")
    app.run()
