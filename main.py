import asyncio
import os
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream          # <-- التغيير الأساسي هنا
from pytgcalls.types import AudioParameters, AudioQuality

# ========== متغيرات البيئة (من Railway) ==========
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))

# ========== مجلد الصوت ==========
AUDIO_FOLDER = "audio"
AUDIO_FILE = "baqarah.mp3"

# ========== تهيئة اليوزر بوت ==========
userbot = Client(
    "userbot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

app = PyTgCalls(userbot)

# ========== تشغيل البث ==========
async def main():
    await app.start()
    await userbot.start()
    
    print(f"✅ تم تشغيل اليوزر بوت: {(await userbot.get_me()).first_name}")
    
    file_path = os.path.join(AUDIO_FOLDER, AUDIO_FILE)
    
    # التحقق من وجود الملف
    if not os.path.exists(file_path):
        print(f"❌ الخطأ: الملف {file_path} مش موجود")
        return
    
    # بدء البث - باستخدام MediaStream
    await app.play(
        CHANNEL_ID,
        MediaStream(                            # <-- استخدام MediaStream بدلاً من Stream
            file_path,
            audio_parameters=AudioParameters(
                bitrate=AudioQuality.BITRATE_HIGH,
            )
        )
    )
    
    print(f"🎙️ جاري تشغيل: {AUDIO_FILE}")
    
    # إرسال رسالة في القناة
    await userbot.send_message(CHANNEL_ID, "🎙️ **بدء بث القرآن الكريم**")
    
    # خلي البرنامج شغال
    await asyncio.Event().wait()

asyncio.run(main())
