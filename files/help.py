# files/help.py

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from files import config

@Client.on_message(filters.command(["الاوامر", "أوامر", "اوامر"], prefixes=["", "/", "!"]) & filters.group)
async def help_command(client, message):
    text = (
        "📜 **قائمة الأوامر الخاصة بالبوت:**\n\n"
        "م1 ↤ أوامر التشغيل\n"
        "م2 ↤ أوامر التحكم والمكالمة\n"
        "م3 ↤ أوامر المنوعات والألعاب\n"
        "م4 ↤ أوامر المطور (خاص جداً 🚷)\n\n"
        "اختر القسم المناسب من الأزرار بالأسفل 👇"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("م2 (التحكم)", callback_data="help_m2"), InlineKeyboardButton("م1 (التشغيل)", callback_data="help_m1")],
        [InlineKeyboardButton("م4 (المطور)", callback_data="help_dev"), InlineKeyboardButton("م3 (المنوعات)", callback_data="help_m3")]
    ])
    
    bot_image = config.bot_cache.get("bot_image")
    
    if bot_image:
        await message.reply_photo(photo=bot_image, caption=text, reply_markup=keyboard)
    else:
        await message.reply(text, reply_markup=keyboard)

@Client.on_callback_query(filters.regex(r"^help_"))
async def help_callbacks(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    # 🔴 حماية قسم المطور برسالة عفوية
    if data == "help_dev":
        if user_id != config.OWNER_ID:
            return await callback_query.answer("أنت بتدخل هنا ليه يا أسطى؟ 👀 القسم ده بتاع المطور بس، متلعبش في حاجة مش بتاعتك! 😂", show_alert=True)
        else:
            text = (
                "👨‍💻 **م4: أوامر المطور الخاصة**\n\n"
                "• `تفعيل` / `تعطيل`: لتشغيل أو إيقاف البوت في الجروب\n"
                "• `رفع مشغل` / `تنزيل مشغل`: لإدارة المشغلين\n"
                "• `تعيين اسم البوت`: لتغيير اسم البوت (في الخاص)\n"
                "• `بدء`: للدخول للوحة التحكم الرئيسية (في الخاص)"
            )
    elif data == "help_m1":
        text = (
            "🎵 **م1: أوامر التشغيل**\n\n"
            "• `تشغيل` أو `شغل` [الاسم]: لتشغيل مقطع صوتي\n"
            "• `فيديو` أو `فيد` [الاسم]: لتشغيل مقطع فيديو\n"
            "• ملاحظة: يمكنك الرد على مقطع صوتي أو فيديو محفوظ للتشغيل المباشر."
        )
    elif data == "help_m2":
        text = (
            "⚙️ **م2: أوامر التحكم**\n\n"
            "• `إيقاف` أو `اسكت`: لإيقاف التشغيل ومغادرة المساعد\n"
            "• `تخطي`: لتخطي المقطع وتشغيل التالي\n"
            "• `وقف` / `كمل`: لإيقاف البث مؤقتاً أو استئنافه\n"
            "• `كرر`: لإضافة المقطع الحالي للطابور مرة أخرى\n"
            "• `مرر` / `رجع` [الثواني]: لتقديم أو تأخير المقطع"
        )
    elif data == "help_m3":
        text = (
            "🎲 **م3: أوامر المنوعات والألعاب**\n\n"
            "• `ايدي` أو `ا`: لعرض معلوماتك (الاسم، الايدي، البايو)\n"
            "• `مين مشغل`: لمعرفة من قام بطلب المقطع الحالي\n"
            "• `المعجبين`: لعرض قائمة الأشخاص الذين أعجبوا بملفك\n"
            "• `كت`: لعرض سؤال عشوائي للنقاش"
        )
    elif data == "help_back":
        text = (
            "📜 **قائمة الأوامر الخاصة بالبوت:**\n\n"
            "م1 ↤ أوامر التشغيل\n"
            "م2 ↤ أوامر التحكم والمكالمة\n"
            "م3 ↤ أوامر المنوعات والألعاب\n"
            "م4 ↤ أوامر المطور (خاص جداً 🚷)\n\n"
            "اختر القسم المناسب من الأزرار بالأسفل 👇"
        )
    
    if data == "help_back":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("م2 (التحكم)", callback_data="help_m2"), InlineKeyboardButton("م1 (التشغيل)", callback_data="help_m1")],
            [InlineKeyboardButton("م4 (المطور)", callback_data="help_dev"), InlineKeyboardButton("م3 (المنوعات)", callback_data="help_m3")]
        ])
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="help_back")]
        ])
        
    try:
        if callback_query.message.photo:
            await callback_query.edit_message_caption(caption=text, reply_markup=keyboard)
        else:
            await callback_query.edit_message_text(text=text, reply_markup=keyboard)
    except Exception:
        pass
