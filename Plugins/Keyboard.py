'''
أمر «كيبورد» — كيبورد شخصي لكل عضو (مش مشترك بين الأعضاء)

الفكرة:
- الأمر بيتكتب: كيبورد {اسم البوت}  → مثلاً لو اسم البوت "فارس" يكتب: كيبورد فارس
  اسم البوت بيتقرأ ديناميكيًا من نفس المفتاح اللي بيستخدمه أمر "تعيين اسم البوت"
  ({Dev_Zaid}:BotName) فلو الاسم اتغيّر، الأمر بيتغيّر معاه أوتوماتيك من غير تعديل كود.

- لما يكتب "كيبورد {الاسم}" → يظهرله كيبورد شخصي (selective) فيه أزراره المحفوظة + 3 أزرار ثابتة:
    Add    → إضافة زر/أزرار جديدة
    Delete → حذف زر/أزرار
    مسح الكيبورد → إخفاء الكيبورد (بدون حذف الأزرار المحفوظة)

- بعد الضغط على Add: يبعت اسم الزر (يقدر يبعت كذا زر ورا بعض)، ولما يخلص يكتب "تم"
- بعد الضغط على Delete: نفس الفكرة، يبعت اسم/أسماء الأزرار اللي عايز يحذفها ثم "تم"
- أمر "مسح الازرار" أو "حذف الازرار": يحذف كل الأزرار المحفوظة للشخص اللي كتب الأمر فقط
  (مش بتتأثر بيه باقي الأعضاء إطلاقًا، لأن التخزين مربوط بـ user_id + chat_id)
- كل ده مخزن بالـ Redis مربوط بـ (user_id + chat_id) فمايظهرش عند باقي أعضاء الجروب.

ملاحظة: هذا ملف مستقل قائم بذاته، لا يعدّل على games.py ويمكن وضعه كـ plugin منفصل بجانبه.
هذا الملف متوافق مع نظام تغيير الأوامر الموجود في customCommad.py (أوامر "تغيير امر" / "تغيير امر عام") —
يعني لو حد غيّر نص أمر "كيبورد {الاسم}" لأي نص تاني، الملف هيفهمه ويشتغل عادي.
'''

from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from config import *

# ===== إعدادات =====
MAX_BUTTONS = 20          # أقصى عدد أزرار يقدر العضو يحفظها
BTNS_PER_ROW = 2          # عدد الأزرار في كل صف
DEFAULT_BOT_NAME = 'رعد'  # نفس الديفولت المستخدم في privateVsudos.py

BTN_ADD = "Add"
BTN_DEL = "Delete"
BTN_CLEAR = "مسح الكيبورد"

FIXED_BUTTONS = [BTN_ADD, BTN_DEL, BTN_CLEAR]


# ===== مفاتيح الـ Redis =====
def _buttons_key(user_id, chat_id):
    return f'{user_id}:kbButtons:{chat_id}{Dev_Zaid}'

def _state_key(user_id, chat_id):
    return f'{user_id}:kbState:{chat_id}{Dev_Zaid}'


# ===== دوال مساعدة =====
def _get_bot_name():
    return r.get(f'{Dev_Zaid}:BotName') or DEFAULT_BOT_NAME

def _get_buttons(user_id, chat_id):
    return sorted(list(r.smembers(_buttons_key(user_id, chat_id)) or []))

def _build_keyboard(user_id, chat_id):
    custom = _get_buttons(user_id, chat_id)
    rows = []
    for i in range(0, len(custom), BTNS_PER_ROW):
        rows.append([KeyboardButton(b) for b in custom[i:i + BTNS_PER_ROW]])
    rows.append([KeyboardButton(BTN_ADD), KeyboardButton(BTN_DEL)])
    rows.append([KeyboardButton(BTN_CLEAR)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, selective=True)


@Client.on_message(filters.text & filters.group, group=60)
def personalKeyboardHandler(c, m):
    k = r.get(f'{Dev_Zaid}:botkey') or '⇜'
    user_id = m.from_user.id
    chat_id = m.chat.id
    text = m.text.strip()

    # ===== دعم نظام تغيير الأوامر (نفس آلية customCommad.py) =====
    if r.get(f'{chat_id}:Custom:{chat_id}{Dev_Zaid}&text={text}'):
        text = r.get(f'{chat_id}:Custom:{chat_id}{Dev_Zaid}&text={text}')
    if r.get(f'Custom:{Dev_Zaid}&text={text}'):
        text = r.get(f'Custom:{Dev_Zaid}&text={text}')

    state = r.get(_state_key(user_id, chat_id))

    # ===== وضع إضافة أزرار =====
    if state == 'add':
        if text == 'تم':
            r.delete(_state_key(user_id, chat_id))
            return m.reply(
                f'{k} تم حفظ جميع ازرار كيبوردك بنجاح',
                reply_markup=_build_keyboard(user_id, chat_id)
            )
        if text in FIXED_BUTTONS:
            return m.reply(f'{k} ارسل مسمى الزر لأضافته')
        current = _get_buttons(user_id, chat_id)
        if len(current) >= MAX_BUTTONS:
            r.delete(_state_key(user_id, chat_id))
            return m.reply(
                f'{k} تم حفظ جميع ازرار كيبوردك بنجاح',
                reply_markup=_build_keyboard(user_id, chat_id)
            )
        if text in current:
            return m.reply(f'{k} ارسل مسمى الزر لأضافته')
        r.sadd(_buttons_key(user_id, chat_id), text)
        return m.reply(f'{k} تم حفظ الزر بنجاح اذا خلصت ارسل ( تم )')

    # ===== وضع حذف أزرار =====
    if state == 'del':
        if text == 'تم':
            r.delete(_state_key(user_id, chat_id))
            return m.reply(
                f'{k} تم حفظ جميع ازرار كيبوردك بنجاح',
                reply_markup=_build_keyboard(user_id, chat_id)
            )
        if text in FIXED_BUTTONS:
            return m.reply(f'{k} ارسل مسمى الزر لحذفه')
        current = _get_buttons(user_id, chat_id)
        if text not in current:
            return m.reply(f'{k} ارسل مسمى الزر لحذفه')
        r.srem(_buttons_key(user_id, chat_id), text)
        return m.reply(f'{k} تم حذف الزر بنجاح')

    # ===== فتح الكيبورد =====
    if text == f'كيبورد {_get_bot_name()}':
        return m.reply(
            f'{k} أهلاً بك عزيزي في كيبورد الخاص',
            reply_markup=_build_keyboard(user_id, chat_id)
        )

    # ===== زر Add =====
    if text == BTN_ADD:
        current = _get_buttons(user_id, chat_id)
        if len(current) >= MAX_BUTTONS:
            return m.reply(
                f'{k} تم حفظ جميع ازرار كيبوردك بنجاح',
                reply_markup=_build_keyboard(user_id, chat_id)
            )
        r.set(_state_key(user_id, chat_id), 'add')
        return m.reply(f'{k} ارسل مسمى الزر لأضافته')

    # ===== زر Delete =====
    if text == BTN_DEL:
        current = _get_buttons(user_id, chat_id)
        if not current:
            return m.reply(f'{k} ارسل مسمى الزر لحذفه')
        r.set(_state_key(user_id, chat_id), 'del')
        return m.reply(f'{k} ارسل مسمى الزر لحذفه')

    # ===== زر مسح الكيبورد (إخفاء بدون حذف الأزرار) =====
    if text == BTN_CLEAR:
        return m.reply(
            f'{k} تم مسح الكيبورد بنجاح',
            reply_markup=ReplyKeyboardRemove(selective=True)
        )

    # ===== أمر مسح/حذف كل الأزرار (خاص بصاحب الأمر فقط) =====
    if text == 'مسح الازرار' or text == 'حذف الازرار':
        r.delete(_buttons_key(user_id, chat_id))
        r.delete(_state_key(user_id, chat_id))
        return m.reply(
            f'{k} تم مسح الكيبورد بنجاح',
            reply_markup=_build_keyboard(user_id, chat_id)
        )
