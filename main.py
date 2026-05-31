import asyncio
import os
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import Stream
from pytgcalls.types import AudioParameters, AudioQuality

# ========== متغيرات البيئة (من Railway) ==========
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")   # <----- متغير الجلسة (حروف وأرقام)
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))

# ========== إعدادات مجلد الصوت ==========
AUDIO_FOLDER = "audio"

# ========== قائمة السور (أضف اللي عندك) ==========
SURAHS = [
    "baqarah.mp3",           # سورة البقرة
    # "fatiha.mp3",          # سورة الفاتحة (علقها حالياً)
    # "ikhlas.mp3",          # سورة الإخلاص
]

# ========== تهيئة اليوزر بوت باستخدام Session String ==========
userbot = Client(
    "userbot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING      # <----- استخدام متغير الجلسة
)

# ========== تهيئة PyTgCalls ==========
app = PyTgCalls(userbot)

# ========== الدالة الرئيسية ==========
async def main():
    print("🚀 جاري تشغيل يوزر بوت القرآن...")
    
    # تشغيل PyTgCalls
    await app.start()
    
    # تشغيل العميل
    await userbot.start()
    
    # جلب معلومات الحساب
    me = await userbot.get_me()
    print(f"✅ تم تسجيل الدخول باسم: {me.first_name} (ID: {me.id})")
    
    # التحقق من وجود مجلد الصوت
    if not os.path.exists(AUDIO_FOLDER):
        print(f"❌ خطأ: مجلد {AUDIO_FOLDER} غير موجود!")
        return
    
    # اختيار أول سورة
    first_surah = os.path.join(AUDIO_FOLDER, SURAHS[0])
    
    # التحقق من وجود ملف الصوت
    if not os.path.exists(first_surah):
        print(f"❌ خطأ: ملف الصوت {first_surah} غير موجود!")
        return
    
    print(f"🎙️ جاري الدخول إلى القناة {CHANNEL_ID}...")
    
    try:
        # بدء البث في المحطة الصوتية
        await app.play(
            CHANNEL_ID,
            Stream(
                first_surah,
                AudioParameters(
                    bitrate=AudioQuality.BITRATE_HIGH,
                )
            )
        )
        print(f"✅ تم بدء البث: {SURAHS[0]}")
        
        # إرسال رسالة تأكيد في القناة
        await userbot.send_message(
            CHANNEL_ID,
            "🎙️ **تم بدء بث القرآن الكريم**\n\n"
            f"📀 **السورة الحالية:** {SURAHS[0]}\n"
            "🔊 **الحالة:** يتم البث الآن"
        )
        
        print("📻 البث شغال... اضغط Ctrl+C للإيقاف")
        
        # إبقاء البرنامج شغالاً
        await asyncio.Event().wait()
        
    except Exception as e:
        print(f"❌ حدث خطأ: {e}")
        return

# ========== تشغيل البرنامج ==========
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ تم إيقاف البث بواسطة المستخدم")
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع: {e}")