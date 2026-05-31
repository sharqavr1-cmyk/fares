import asyncio
import os
from pyrogram import Client
from pytgcalls import PyTgCalls

# المتغيرات من Railway
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))

# إعدادات الملف الصوتي
AUDIO_FOLDER = "audio"
AUDIO_FILE = "baqarah.mp3"

# تهيئة العميل
userbot = Client(
    "userbot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# تهيئة المكالمات الصوتية
app = PyTgCalls(userbot)

async def main():
    # بدء تشغيل العميل والمكالمات
    await app.start()
    await userbot.start()

    print(f"✅ تم تشغيل اليوزر بوت: {(await userbot.get_me()).first_name}")

    # تحديد مسار الملف الصوتي
    file_path = os.path.join(AUDIO_FOLDER, AUDIO_FILE)

    # بدء البث
    await app.play(CHANNEL_ID, file_path)

    print(f"🎙️ جاري تشغيل: {AUDIO_FILE}")

    # إرسال رسالة تأكيد في القناة
    await userbot.send_message(CHANNEL_ID, "🎙️ **بدء بث القرآن الكريم**")

    # إبقاء البرنامج قيد التشغيل
    await asyncio.Event().wait()

asyncio.run(main())