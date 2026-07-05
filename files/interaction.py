# files/bot_replies.py

import random
import asyncio
import aiohttp
from pyrogram import Client, filters
from files import config

# ================== قوائم الردود ==================
BOT_REPLIES = [
    "أنا مو بوت، أنا قلوب تنبض 🥺",
    "أنت البوت يا أخي، على البشر ما تناديني بوت 😒",
    "لا تعيدها مرة ثانية، اسمي أحلى من كلمة بوت 🔪",
    "عيون البوت، أؤمرني؟ 👀",
    "بوت في عينك، احترم نفسك 😤"
]

NAME_REPLIES = [
    "في خدمتك يا سيدي، أؤمر يا باشا 🫡",
    "اطلب وأنا أنفذ 🧞‍♂️",
    "معاك يا بعد روحي ❤️",
    "معاك يا قلبي، تفضل 🥰",
    "لبيك يا غالي 🌹"
]

# ================== دالة الريأكت السريعة جداً ==================
async def send_bot_reaction(client, chat_id, message_id, emoji):
    """دالة ترسل الريأكت في الخلفية فوراً بدون انتظار"""
    token = getattr(config, "BOT_TOKEN", None) or getattr(config, "TOKEN", None) or getattr(client, "bot_token", None)
    if not token:
        return
        
    url = f"https://api.telegram.org/bot{token}/setMessageReaction"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reaction": [{"type": "emoji", "emoji": emoji}],
        "is_big": False
    }
    
    # دالة داخلية للاتصال بالسيرفر
    async def fetch():
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=payload)
        except:
            pass

    # تشغيل المهمة في الخلفية فوراً عشان البوت ما يعطلش ثانية واحدة
    asyncio.create_task(fetch())


# ================== أوامر المطور (تفاعلية في الخاص) ==================

# 1. المطور يطلب تغيير الاسم
@Client.on_message(filters.command(["تعيين اسم", "تعيين اسم البوت", "اسم البوت"], prefixes=["", "/", "!"]) & filters.private)
async def ask_for_bot_name(client, message):
    if message.from_user.id != config.OWNER_ID:
        return
        
    # نستخدم نظام الحالات اللي موجود أساساً في البوت عشان نمنع التداخل
    config.user_states[message.from_user.id] = "wait_bot_name"
    await message.reply("عنوني ليك يا غالي، أرسل الآن اسم البوت الجديد الذي تريده:")

# 2. استقبال الاسم وحفظه بدون أخطاء
@Client.on_message(filters.private & filters.text & ~filters.bot, group=1)
async def save_bot_name(client, message):
    user_id = message.from_user.id
    
    # نتأكد إن المطور في حالة "انتظار الاسم"
    if user_id == config.OWNER_ID and config.user_states.get(user_id) == "wait_bot_name":
        text = message.text.strip()
        
        # الخطوة دي بتمنع البوت إنه يسجل كلمة "تعيين اسم البوت" نفسها كاسم ليه
        if text in ["تعيين اسم", "تعيين اسم البوت", "اسم البوت", "/تعيين اسم", "/تعيين اسم البوت"]:
            return
            
        # حفظ الاسم وتفريغ حالة الانتظار
        config.bot_cache["custom_bot_name"] = text
        config.save_cache()
        config.user_states[user_id] = None
        
        await message.reply(f"✅ تم حفظ اسم البوت بنجاح!\nالاسم الحالي المعتمد هو: **{text}**")


# ================== التفاعل والرد (في المجموعات) ==================
@Client.on_message(filters.text & filters.group & ~filters.bot, group=5)
async def handle_bot_mentions(client, message):
    text = message.text.strip()
    words = text.split()
    custom_name = config.bot_cache.get("custom_bot_name", "")
    
    # 1. إذا تم نداء البوت باسمه المخصص
    if custom_name and custom_name in text:
        # الريأكت بيتبعت في الخلفية، والرد بينزل في نفس اللحظة (أسرع بكتير)
        asyncio.create_task(send_bot_reaction(client, message.chat.id, message.id, "❤️"))
        await message.reply(random.choice(NAME_REPLIES))
        return
        
    # 2. إذا تم نداء كلمة "بوت"
    if "بوت" in words:
        asyncio.create_task(send_bot_reaction(client, message.chat.id, message.id, "😘"))
        await message.reply(random.choice(BOT_REPLIES))
