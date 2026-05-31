import os
import sys
import subprocess
import asyncio

# ========================================================
# 1. نظام التثبيت الذكي (لنسخة pytgcalls 3.0.0.dev24)
# ========================================================
try:
    from pyrogram import Client
    from pytgcalls import PyTgCalls, idle
    from pytgcalls.types import MediaStream
except ImportError:
    print("[!] المكتبات غير موجودة. جاري التثبيت التلقائي للإصدار المطلوب...")
    # استخدام المجلد الحالي كمساحة عمل مؤقتة لتجنب مشاكل المساحة
    os.environ["TMPDIR"] = os.getcwd()

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-cache-dir", "--prefix", ".local",
         "pyrogram==2.0.106", "pytgcalls==3.0.0.dev24", "tgcrypto"],
        check=True
    )
    print("[✅] تم تثبيت المكتبات بنجاح. جاري إعادة تشغيل البوت...")
    os.execv(sys.executable, [sys.executable] + sys.argv)

# ========================================================
# 2. إعدادات البوت (من متغيرات البيئة)
# ========================================================
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
CHAT_ID = int(os.environ.get("CHAT_ID"))          # مثال: -1001234567890
AUDIO_FILE = "audio/baqarah.mp3"                 # الملف الصوتي المحلي

# ========================================================
# 3. تشغيل البث
# ========================================================
client = Client("quran_bot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
pytgcalls = PyTgCalls(client)

async def main():
    await client.start()
    await pytgcalls.start()
    
    # التحقق من وجود الملف الصوتي
    if not os.path.exists(AUDIO_FILE):
        print(f"❌ خطأ: الملف {AUDIO_FILE} غير موجود!")
        return
    
    # بدء البث في المحطة الصوتية
    await pytgcalls.play(CHAT_ID, MediaStream(AUDIO_FILE))
    print(f"🎙️ جاري بث {AUDIO_FILE} في الدردشة {CHAT_ID}")
    
    # إرسال رسالة تأكيد (اختياري)
    await client.send_message(CHAT_ID, "🎙️ **بدء بث القرآن الكريم**")
    
    # البقاء شغالاً
    await idle()

if __name__ == "__main__":
    asyncio.run(main())