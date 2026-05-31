import asyncio
import os
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioQuality, AudioParameters
from pytgcalls.types.stream import Stream

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))

AUDIO_FOLDER = "audio"
AUDIO_FILE = "baqarah.mp3"

userbot = Client(
    "userbot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

app = PyTgCalls(userbot)

async def main():
    await app.start()
    await userbot.start()
    print(f"✅ تم تشغيل اليوزر بوت: {(await userbot.get_me()).first_name}")

    file_path = os.path.join(AUDIO_FOLDER, AUDIO_FILE)
    if not os.path.exists(file_path):
        print(f"❌ الملف {file_path} مش موجود")
        return

    await app.play(
        CHANNEL_ID,
        Stream(
            file_path,
            AudioParameters(
                bitrate=AudioQuality.BITRATE_HIGH,
            )
        )
    )
    print(f"🎙️ جاري تشغيل: {AUDIO_FILE}")
    await userbot.send_message(CHANNEL_ID, "🎙️ **بدء بث القرآن الكريم**")
    await asyncio.Event().wait()

asyncio.run(main())