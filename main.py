import asyncio
import os
from pyrogram import Client
from py_tgcalls import PyTgCalls, idle
from py_tgcalls.types import MediaStream

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
CHAT_ID = int(os.environ.get("CHAT_ID"))
AUDIO_FILE = "audio/baqarah.mp3"

client = Client("quran_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
pytgcalls = PyTgCalls(client)

async def main():
    await client.start()
    await pytgcalls.start()
    if not os.path.exists(AUDIO_FILE):
        print(f"❌ الملف {AUDIO_FILE} غير موجود!")
        return
    await pytgcalls.play(CHAT_ID, MediaStream(AUDIO_FILE))
    print(f"🎙️ بث {AUDIO_FILE} في {CHAT_ID}")
    await client.send_message(CHAT_ID, "🎙️ **بدء بث القرآن الكريم**")
    await idle()

asyncio.run(main())