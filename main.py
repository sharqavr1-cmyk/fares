import asyncio
import os
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls import idle
from pytgcalls.types import AudioStream  # استخدام AudioStream بدلاً من MediaStream

# ========== قراءة متغيرات البيئة ==========
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
CHAT_ID = int(os.environ.get("CHAT_ID"))          # مثال: -1001234567890
AUDIO_FILE = "audio/baqarah.mp3"                 # الملف الصوتي المحلي

# ========== تهيئة العميل ==========
client = Client(
    "quran_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

pytgcalls = PyTgCalls(client)

async def main():
    print("🚀 جاري بدء تشغيل البوت (Python 3.8 - pytgcalls 3.0.0.dev24)...")
    await client.start()
    await pytgcalls.start()
    
    # التحقق من وجود الملف الصوتي
    if not os.path.exists(AUDIO_FILE):
        print(f"❌ خطأ: الملف {AUDIO_FILE} غير موجود!")
        return
    
    # بدء البث في المحطة الصوتية
    await pytgcalls.play(CHAT_ID, AudioStream(AUDIO_FILE))
    print(f"🎙️ جاري بث {AUDIO_FILE} في المحطة الصوتية للدردشة {CHAT_ID}")
    
    # إرسال رسالة تأكيد في القناة (اختياري)
    try:
        await client.send_message(CHAT_ID, "🎙️ **بدء بث القرآن الكريم**")
    except Exception as e:
        print(f"⚠️ لم نتمكن من إرسال رسالة التأكيد: {e}")
    
    # البقاء شغالاً (بدون حلقة لا نهائية يدوية)
    await idle()

if __name__ == "__main__":
    asyncio.run(main())