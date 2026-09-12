# ملف: Plugins/my_commands.py

from pyrogram import Client, filters
from config import *
import re

# ============================================================
# دعم نظام "تغيير أمر" من customCommad.py:
# لو حد غيّر كلمة (مثلاً "حلو" -> "جميل") عن طريق أمر "تغيير امر"،
# نرجع أي كلمة في رسالة العضو لأصلها الأساسي قبل ما نقارنها بالكلمات
# المعروفة (هاي / حلو / لا / اها / آيدي المجموعة).
# ============================================================
def _translate_command_word(m, word):
    chat_id = m.chat.id if m.chat else None
    if chat_id and r.get(f'{chat_id}:Custom:{chat_id}{Dev_Zaid}&text={word}'):
        word = r.get(f'{chat_id}:Custom:{chat_id}{Dev_Zaid}&text={word}')
    if r.get(f'Custom:{Dev_Zaid}&text={word}'):
        word = r.get(f'Custom:{Dev_Zaid}&text={word}')
    return word

def _contains_translated_word(m, text, target):
    # بيدور على أي كلمة في الرسالة (بعد ترجمتها لأصلها لو اتغيرت)
    # تساوي الكلمة المستهدفة
    for raw_word in re.findall(r'\w+', text, re.UNICODE):
        if _translate_command_word(m, raw_word) == target:
            return True
    return False

@Client.on_message(filters.text & filters.group & ~filters.bot)
async def my_commands(c, m):
    if not m.from_user:
        return

    text = m.text

    # آيدي المجموعة (أمر كامل - مش كلمة مفردة جوه جملة)
    id_text = _translate_command_word(m, text.strip())
    if id_text == "ايدي المجموعه":
        await m.reply(f"ايدي المجموعه:\n`{m.chat.id}`")
        return

    # البحث عن كلمة "هاي" في أي مكان بالجملة
    if _contains_translated_word(m, text, "هاي"):
        await m.reply("مسوي فيها اجنبي؟🦦")
        return

    # البحث عن كلمة "حلو" في أي مكان بالجملة
    if _contains_translated_word(m, text, "حلو"):
        await m.reply("احسن منك 🦦.")
        return

    # البحث عن كلمة "لا" في أي مكان بالجملة
    if _contains_translated_word(m, text, "لا"):
        await m.reply("تمزح!")
        return

    # البحث عن كلمة "أها" في أي مكان بالجملة (الأمر الجديد)
    if _contains_translated_word(m, text, "اها"):
        await m.reply("مسوي فيها فهمت🦦")
        return