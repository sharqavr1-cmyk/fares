import asyncio
import os
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls import idle  # هذا السطر مهم للبقاء

# ------------------- الإعدادات ------------------
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
CHAT_ID = int(os.environ.get("CHAT_ID", 0))

AUDIO_FILE = "audio/baqarah.mp3"
# ------------------------------------------------

if not os.path.exists(AUDIO_FILE):
    raise FileNotFoundError(f"الملف الصوتي غير موجود: {AUDIO_FILE}")

client = Client(
    name="my_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

pytgcalls = PyTgCalls(client)

async def start_stream():
    await client.start()
    await pytgcalls.start()
    await pytgcalls.play(CHAT_ID, AUDIO_FILE)
    print(f"🎙️ جاري البث في {CHAT_ID} من {AUDIO_FILE}")
    
    # ========== السطر المطلوب ==========
    await idle()  # هذا السطر يبقي البوت شغالاً لأجل غير مسمى
    # ====================================

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_stream())