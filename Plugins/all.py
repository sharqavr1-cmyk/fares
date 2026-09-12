import random, re, time, pytz, os, gtts, requests, asyncio, inspect
import speech_recognition as sr
from pydub import AudioSegment
from hijri_converter import Hijri, Gregorian
from datetime import datetime
from threading import Thread
from pyrogram import *
from pyrogram.enums import *
from pyrogram.types import *
from config import *
from helpers.Ranks import *
from helpers.persianData import persianInformation
from .welcome_and_rules import *
from .games import *
from PIL import Image
from asyncio import run as RUN
from Python_ARQ import ARQ
from aiohttp import ClientSession

# from googletrans import Translator as googletranstr
from mutagen.mp3 import MP3 as mutagenMP3
# from main import TelegramBot

ARQ_API_KEY = "OZJRWV-SAURXD-PMBUKF-GMVSNS-ARQ"
ARQ_API_URL = "https://arq.hamker.dev"

# ============================================================
# 🎨 نظام تلوين الأزرار ( Colored Inline Buttons )
# بديل عن أزرار Pyrogram العادية عشان نقدر نضيف "style" للون الزر
# ونضمن ان اللون يفضل موجود حتى بعد التنقل بين القوائم.
# لا يُستخدم إلا لبناء/تعديل الأزرار الملونة فقط، باقي الكود لم يتغير.
# ============================================================
import json as _color_json


def _get_bot_token(obj):
    """يحاول ياخذ توكن البوت من الـ Client أو من الرسالة/الكولباك"""
    for chain in (("bot_token",), ("_client", "bot_token")):
        node = obj
        try:
            for attr in chain:
                node = getattr(node, attr)
            if node:
                return node
        except Exception:
            continue
    return None


class _ColoredMsg:
    """أوبجكت خفيف بيحاكي شكل رسالة Pyrogram (بس فيه .id) عشان الكود
    اللي بياخذ id الرسالة بعد الإرسال يفضل يعمل بدون أي تغيير تاني."""

    def __init__(self, raw):
        self._raw = raw or {}
        self.id = self._raw.get("message_id")
        self.message_id = self._raw.get("message_id")


def build_colored_keyboard(rows):
    """
    rows: list صفوف، كل صف عبارة عن list من dicts فيها:
        text, ونوع واحد من (callback_data / url / user_id), وممكن تحتوي "style"
    بيرجع الشكل اللي يفهمه Telegram Bot API: {"inline_keyboard": [[...]]}
    """
    inline_keyboard = []
    for row in rows:
        new_row = []
        for btn in row:
            b = {"text": btn["text"]}
            if "callback_data" in btn:
                b["callback_data"] = btn["callback_data"]
            if "url" in btn:
                b["url"] = btn["url"]
            if "user_id" in btn:
                b["url"] = f"tg://user?id={btn['user_id']}"
            if btn.get("style"):
                b["style"] = btn["style"]
            new_row.append(b)
        inline_keyboard.append(new_row)
    return {"inline_keyboard": inline_keyboard}


def send_colored_message(c, chat_id, text, rows=None, **extra):
    """إرسال رسالة جديدة بأزرار ملونة عن طريق Telegram HTTP API مباشرة"""
    token = _get_bot_token(c)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if rows is not None:
        payload["reply_markup"] = build_colored_keyboard(rows)
    payload.update(extra)
    try:
        res = requests.post(url, json=payload).json()
        return _ColoredMsg(res.get("result"))
    except Exception:
        return _ColoredMsg(None)


def edit_colored_markup(c, chat_id, message_id, rows):
    """تعديل أزرار رسالة موجودة فقط (بدون تغيير النص) عن طريق Telegram HTTP API مباشرة"""
    token = _get_bot_token(c)
    url = f"https://api.telegram.org/bot{token}/editMessageReplyMarkup"
    payload = {"chat_id": chat_id, "message_id": message_id, "reply_markup": build_colored_keyboard(rows)}
    try:
        requests.post(url, json=payload)
    except Exception:
        pass


def edit_colored_message(c, chat_id, message_id, text, rows=None, **extra):
    """تعديل رسالة موجودة بأزرار ملونة عن طريق Telegram HTTP API مباشرة"""
    token = _get_bot_token(c)
    url = f"https://api.telegram.org/bot{token}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if rows is not None:
        payload["reply_markup"] = build_colored_keyboard(rows)
    payload.update(extra)
    try:
        res = requests.post(url, json=payload).json()
        return _ColoredMsg(res.get("result"))
    except Exception:
        return _ColoredMsg(None)


def send_colored_photo(c, chat_id, photo_path, caption=None, rows=None, **extra):
    """إرسال صورة بأزرار ملونة عن طريق Telegram HTTP API مباشرة"""
    token = _get_bot_token(c)
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    data = {"chat_id": chat_id}
    if caption is not None:
        data["caption"] = caption
    if rows is not None:
        data["reply_markup"] = _color_json.dumps(build_colored_keyboard(rows))
    data.update(extra)
    try:
        with open(photo_path, "rb") as f:
            res = requests.post(url, data=data, files={"photo": f}).json()
        return _ColoredMsg(res.get("result"))
    except Exception:
        return _ColoredMsg(None)


COMMANDS_LAYOUT = [
    ("primary", [("الإدارة", "commands1"), ("الإعدادات", "commands2"), ("الحماية والردود", "commands3")]),
    ("danger", [("الالعاب", "commands4"), ("التسليه", "commands5"), ("اليوتيوب", "commands6")]),
    ("success", [("البنك", "commands7"), ("زواج", "commands8"), ("الموسيقى", "commands9")]),
    ("danger", [("المطور", "commands10")]),
]

CIRCLED_NUMS = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]


def commands_menu_list_text():
    """
    بيبني نص السطور المرقمة (①← الإدارة, ②← الإعدادات ...) اللي بتتحط
    فوق الأزرار في الكليشة، بنفس ترتيب الأزرار بالظبط.
    """
    lines = []
    i = 0
    for _style, items in COMMANDS_LAYOUT:
        for label, _key in items:
            num = CIRCLED_NUMS[i] if i < len(CIRCLED_NUMS) else str(i + 1)
            lines.append(f"{num}← {label}")
            i += 1
    return "\n".join(lines)


def commands_menu_rows(current_key, uid):
    """
    يبني صفوف قائمة الاوامر بالتلوين المطلوب:
    صف1 ازرق - صف2 احمر - صف3 اخضر - صف4 (المطور) احمر بالعرض
    الزر نفسه بيبقى مكتوب عليه رقمه بس (①، ②، ...) — الاسم الكامل
    (الإدارة، الإعدادات، ...) بيفضل موجود بس في نص الكليشة فوق الأزرار
    عن طريق commands_menu_list_text().
    والزر اللي انت واقف فيه حاليا (current_key) يظهر بدون لون ('‣')
    """
    rows = []
    i = 0
    for style, items in COMMANDS_LAYOUT:
        row = []
        for _label, key in items:
            num = CIRCLED_NUMS[i] if i < len(CIRCLED_NUMS) else str(i + 1)
            i += 1
            if key == current_key:
                row.append({"text": f"{num} ‣", "callback_data": "None"})
            else:
                row.append(
                    {
                        "text": num,
                        "callback_data": f"{key}:{uid}",
                        "style": style,
                    }
                )
        rows.append(row)
    # زر الرجوع للقائمة الرئيسية - يظهر فقط داخل أي قسم فرعي (مش في القائمة الأولى)
    if current_key is not None:
        rows.append(
            [
                {
                    "text": "🔙 الرجوع للقائمة الرئيسية",
                    "callback_data": f"commandsback:{uid}",
                    "style": "danger",
                }
            ]
        )
    return rows


# ============================================================

# ============================================================
# ============================================================
# 🔐 لوحة الحماية التفاعلية ( أمر "الحماية" / "الاعدادات" - نفس الأمر بالظبط )
# كل إعداد له صف فيه زرارين جنب بعض: "قفل" و"فتح". الزرار اللي
# بيمثل الحالة الحالية بس هو الملون (أحمر لو مقفول، أزرق لو مفتوح)
# والزرار التاني بيفضل من غير لون. مفيش أي إيموجي على أي زرار.
# تحت آخر صف فيه صف واحد فيه 3 أزرار: التالي (أزرق) / تحويل
# للقائمة النصية القديمة (أخضر) / إخفاء (أحمر).
# ============================================================

PROTECTION_ITEMS = [
    ("الملفات الصوتية", "lockAudios"),
    ("الفيديو", "lockVideo"),
    ("الفويس", "lockVoice"),
    ("الصور", "lockPhoto"),
    ("الدردشة", "mute"),
    ("الانلاين", "lockInline"),
    ("التوجيه", "lockForward"),
    ("الهشتاق", "lockHashtags"),
    ("التعديل", "lockEdit"),
    ("الستيكرات", "lockStickers"),
    ("الملفات", "lockFiles"),
    ("المتحركات", "lockAnimations"),
    ("الروابط", "lockUrls"),
    ("البوتات", "lockBots"),
    ("اليوزرات", "lockTags"),
    ("الاشعارات", "lockNot"),
    ("الاضافة", "lockaddContacts"),
    ("الكلام الكثير", "lockMessages"),
    ("السب", "lockSHTM"),
    ("التكرار", "lockSpam"),
    ("القنوات", "lockChannels"),
    ("تعديل الميديا", "lockEditM"),
    ("الدخول", "lockJoin"),
    ("الفارسية", "lockPersian"),
    ("دخول الإيراني", "lockJoinPersian"),
    ("الإباحي", "lockNSFW"),
]

PROTECTION_PAGE_SIZE = 7  # سبع صفوف إعدادات كحد أقصى في الصفحة الواحدة


def protection_redis_key(chat_id, item_key):
    return f"{chat_id}:{item_key}:{Dev_Zaid}"


def protection_total_pages():
    return (len(PROTECTION_ITEMS) + PROTECTION_PAGE_SIZE - 1) // PROTECTION_PAGE_SIZE


# ============================================================
# ⚖️ نظام اختيار طريقة التعامل مع المخالفين لكل قفل
# بعد كتابة أمر "قفل" نصي (زي قفل السب / قفل الإباحي / ... الخ)
# البوت بيبعت 3 أزرار ملونة: طرد ( أحمر ) / كتم ( أزرق ) / مسح ( أخضر )
# وبعدها بيبعت زرارين: لكل المستخدمين ( أحمر ) / للأعضاء فقط ( أزرق )
# القيم دي بتتخزن لكل قفل لوحده في كل جروب، وبتتستخدم لما حد يخالف
# القفل ده عشان نعرف نطرده / نكتمه / نمسح رسالته بس.
# ============================================================

PUNISH_ACTIONS = {"kick", "mute", "delete"}
PUNISH_SCOPES = {"all", "members"}


def punish_action_key(chat_id, item_key):
    return f"punishAction:{chat_id}:{item_key}:{Dev_Zaid}"


def punish_scope_key(chat_id, item_key):
    return f"punishScope:{chat_id}:{item_key}:{Dev_Zaid}"


def get_punish_action(chat_id, item_key):
    v = r.get(punish_action_key(chat_id, item_key))
    return v if v in PUNISH_ACTIONS else "delete"


def get_punish_scope(chat_id, item_key):
    v = r.get(punish_scope_key(chat_id, item_key))
    return v if v in PUNISH_SCOPES else "members"


def punish_action_rows(item_key, chat_id):
    return [
        [
            {
                "text": "طرد",
                "callback_data": f"punAct:{item_key}:kick:{chat_id}",
                "style": "danger",
            }
        ],
        [
            {
                "text": "كتم",
                "callback_data": f"punAct:{item_key}:mute:{chat_id}",
                "style": "primary",
            }
        ],
        [
            {
                "text": "مسح",
                "callback_data": f"punAct:{item_key}:delete:{chat_id}",
                "style": "success",
            }
        ],
    ]


def punish_scope_rows(item_key, chat_id):
    return [
        [
            {
                "text": "لكل المستخدمين",
                "callback_data": f"punScope:{item_key}:all:{chat_id}",
                "style": "danger",
            },
            {
                "text": "للأعضاء فقط",
                "callback_data": f"punScope:{item_key}:members:{chat_id}",
                "style": "primary",
            },
        ]
    ]


def html_escape(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def mention_link(user):
    """بيرجع اسم قابل للضغط ( لينك تليجرام باليوزر أيدي ) بصيغة HTML،
    عشان يبان صح لما يترسل عن طريق send_colored_message ( اللي بيبعت
    بالـ API مباشرة من غير أي Parse Mode افتراضي )."""
    if not user:
        return ""
    name = html_escape(user.first_name or "User")
    return f'<a href="tg://user?id={user.id}">{name}</a>'


def send_lock_confirmation(c, m, k, item_key, label):
    """بترسل بعد نجاح أي أمر قفل نصي: رسالة تأكيد عادية زي كل الأوامر
    ( من غير أزرار ومن غير سؤال عن طريقة التعامل مع المخالف )."""
    mention = m.from_user.mention if m.from_user else (
        m.sender_chat.title if m.sender_chat else ""
    )
    return m.reply(f"{k} من 「 {mention} 」\n{k} ابشر قفلت {label}\n☆")


WIRED_PUNISH_LOCKS = [
    "lockEdit",
    "lockEditM",
    "lockVoice",
    "lockVideo",
    "lockPhoto",
    "lockStickers",
    "lockPersian",
    "lockFiles",
    "lockAnimations",
    "lockUrls",
    "lockHashtags",
    "lockTags",
    "lockNSFW",
    "lockMessages",
    "lockForward",
    "lockInline",
    "lockSHTM",
    "lockAudios",
    "lockSpam",
    "mute",
]


def any_wired_scope_all(chat_id):
    """بترجع True لو في قفل واحد على الأقل من اللي معاه نظام العقاب
    متظبط على نطاق ( لكل المستخدمين )، عشان نعرف نسيب المشرفين
    يوصلوا لفحص الأقفال دي بدل ما يتستثنوا على طول."""
    for item_key in WIRED_PUNISH_LOCKS:
        if get_punish_scope(chat_id, item_key) == "all":
            return True
    return False


def apply_lock_punishment(c, m, chat_id, item_key, uid, mention, k):
    """بتتنفذ لما حد يخالف قفل متزود بعقاب ( طرد / كتم / مسح ) + نطاق
    ( لكل المستخدمين / للأعضاء فقط ). لو النطاق ( للأعضاء فقط ) والمخالف
    مشرف أو أدمن، ما بيتعملش أي حاجة خالص ( ولا حتى مسح الرسالة ).
    غير كده بتتمسح الرسالة المخالفة، وبعدين حسب الإعداد المحفوظ
    بتطرد أو بتكتم صاحبها."""
    scope = get_punish_scope(chat_id, item_key)
    is_protected = False
    try:
        is_protected = pre_pls(uid, chat_id)
    except Exception:
        is_protected = False

    if is_protected and scope == "members":
        return

    try:
        m.delete()
    except Exception:
        pass

    if is_protected and scope == "all":
        try:
            c.promote_chat_member(
                chat_id,
                uid,
                privileges=ChatPrivileges(
                    can_manage_chat=False,
                    can_delete_messages=False,
                    can_manage_video_chats=False,
                    can_restrict_members=False,
                    can_promote_members=False,
                    can_pin_messages=False,
                    can_change_info=False,
                    can_invite_users=False,
                ),
            )
        except Exception:
            pass

    action = get_punish_action(chat_id, item_key)
    if action == "kick":
        try:
            c.ban_chat_member(chat_id, uid)
            c.unban_chat_member(chat_id, uid)
        except Exception:
            pass
    elif action == "mute":
        # زي أمر "كتم" بالظبط: مش تقييد تليجرام، لسه يقدر يكتب، بس أي
        # رسالة يبعتها بعد كده في الجروب ده بتتمسح تلقائي.
        try:
            r.set(f"{uid}:mute:{chat_id}{Dev_Zaid}", 1)
            r.sadd(f"{chat_id}:listMUTE:{Dev_Zaid}", uid)
        except Exception:
            pass
    # action == "delete" -> الرسالة اتمسحت فوق وخلاص، من غير أي عقاب إضافي


# ============================================================


def protection_header_text(k, page):
    return (
        f"{k} أوامر التحكم في الحماية\n"
        f"صفحة {page + 1} من {protection_total_pages()}"
    )


def build_protection_text_list(chat_id, k, channel):
    """القائمة النصية القديمة (بدون أزرار) - بتتبعت لما تدوس زرار (تحويل)"""
    x1 = "مقفول" if r.get(f"{chat_id}:lockAudios:{Dev_Zaid}") else "مفتوح"
    x2 = "مقفول" if r.get(f"{chat_id}:lockVideo:{Dev_Zaid}") else "مفتوح"
    x3 = "مقفول" if r.get(f"{chat_id}:lockVoice:{Dev_Zaid}") else "مفتوح"
    x4 = "مقفول" if r.get(f"{chat_id}:lockPhoto:{Dev_Zaid}") else "مفتوح"
    x5 = "مقفول" if r.get(f"{chat_id}:mute:{Dev_Zaid}") else "مفتوح"
    x6 = "مقفول" if r.get(f"{chat_id}:lockInline:{Dev_Zaid}") else "مفتوح"
    x7 = "مقفول" if r.get(f"{chat_id}:lockForward:{Dev_Zaid}") else "مفتوح"
    x8 = "مقفول" if r.get(f"{chat_id}:lockHashtags:{Dev_Zaid}") else "مفتوح"
    x9 = "مقفول" if r.get(f"{chat_id}:lockEdit:{Dev_Zaid}") else "مفتوح"
    x10 = "مقفول" if r.get(f"{chat_id}:lockStickers:{Dev_Zaid}") else "مفتوح"
    x11 = "مقفول" if r.get(f"{chat_id}:lockFiles:{Dev_Zaid}") else "مفتوح"
    x12 = "مقفول" if r.get(f"{chat_id}:lockAnimations:{Dev_Zaid}") else "مفتوح"
    x13 = "مقفول" if r.get(f"{chat_id}:lockUrls:{Dev_Zaid}") else "مفتوح"
    x14 = "مقفول" if r.get(f"{chat_id}:lockBots:{Dev_Zaid}") else "مفتوح"
    x15 = "مقفول" if r.get(f"{chat_id}:lockTags:{Dev_Zaid}") else "مفتوح"
    x16 = "مقفول" if r.get(f"{chat_id}:lockNot:{Dev_Zaid}") else "مفتوح"
    x17 = "مقفول" if r.get(f"{chat_id}:lockaddContacts:{Dev_Zaid}") else "مفتوح"
    x18 = "مقفول" if r.get(f"{chat_id}:lockMessages:{Dev_Zaid}") else "مفتوح"
    x19 = "مقفول" if r.get(f"{chat_id}:lockSHTM:{Dev_Zaid}") else "مفتوح"
    x20 = "مقفول" if r.get(f"{chat_id}:lockSpam:{Dev_Zaid}") else "مفتوح"
    x21 = "مقفول" if r.get(f"{chat_id}:lockChannels:{Dev_Zaid}") else "مفتوح"
    x22 = "مقفول" if r.get(f"{chat_id}:lockEditM:{Dev_Zaid}") else "مفتوح"
    x23 = "مقفول" if r.get(f"{chat_id}:lockJoin:{Dev_Zaid}") else "مفتوح"
    x24 = "مقفول" if r.get(f"{chat_id}:lockPersian:{Dev_Zaid}") else "مفتوح"
    x25 = "مقفول" if r.get(f"{chat_id}:lockJoinPersian:{Dev_Zaid}") else "مفتوح"
    x26 = "مقفول" if r.get(f"{chat_id}:lockNSFW:{Dev_Zaid}") else "مفتوح"
    return f"""
اعدادات المجموعة :

{k} الملفات الصوتية ⇠ ( {x1} )
{k} الفيديو ⇠ ( {x2} )
{k} الفويس ⇠ ( {x3} )
{k} الصور ⇠ ( {x4} )

{k} الدردشة ⇠ ( {x5} )
{k} الانلاين ⇠ ( {x6} )
{k} التوجيه ⇠ ( {x7} )
{k} الهشتاق ⇠ ( {x8} )
{k} التعديل ⇠ ( {x9} )
{k} الستيكرات ⇠ ( {x10} )

{k} الملفات ⇠ ( {x11} )
{k} المتحركات ⇠ ( {x12} )
{k} الروابط ⇠ ( {x13} )
{k} البوتات ⇠ ( {x14} )
{k} اليوزرات ⇠ ( {x15} )

{k} الاشعارات ⇠ ( {x16} )
{k} الاضافة ⇠ ( {x17} )

{k} الكلام الكثير ⇠ ( {x18} )
{k} السب ⇠ ( {x19} )
{k} التكرار ⇠ ( {x20} )
{k} القنوات ⇠ ( {x21} )
{k} تعديل الميديا ⇠ ( {x22} )

{k} الدخول ⇠ ( {x23} )
{k} الفارسية ⇠ ( {x24} )
{k} دخول الإيراني ⇠ ( {x25} )
{k} الإباحي ⇠ ( {x26} )

~ @{channel}"""


def build_protection_rows(chat_id, page, uid):
    """
    بيبني صفوف لوحة الحماية: كل صف = زرارين (قفل / فتح) لإعداد واحد.
    الزرار اللي بيمثل الحالة الحالية فعليًا بس هو الملون (أحمر للمقفول،
    أزرق للمفتوح)، والزرار التاني من غير لون. مفيش أي إيموجي.
    أقصى حد سبع صفوف إعدادات في الصفحة، وتحتهم صف واحد فيه 3 أزرار:
    التالي / تحويل للقائمة النصية / إخفاء.
    """
    start = page * PROTECTION_PAGE_SIZE
    end = min(start + PROTECTION_PAGE_SIZE, len(PROTECTION_ITEMS))
    chunk = [(i, PROTECTION_ITEMS[i]) for i in range(start, end)]
    rows = []
    for idx, (label, item_key) in chunk:
        locked = bool(r.get(protection_redis_key(chat_id, item_key)))
        lock_btn = {
            "text": f"قفل {label}",
            "callback_data": f"protL:{idx}:{page}:{uid}",
        }
        open_btn = {
            "text": f"فتح {label}",
            "callback_data": f"protO:{idx}:{page}:{uid}",
        }
        if locked:
            lock_btn["style"] = "danger"
        else:
            open_btn["style"] = "primary"
        rows.append([lock_btn, open_btn])

    total_pages = protection_total_pages()
    next_page = (page + 1) % total_pages if total_pages > 1 else page
    if total_pages > 1:
        rows.append(
            [
                {
                    "text": "التالي",
                    "callback_data": f"protN:{next_page}:{uid}",
                    "style": "primary",
                }
            ]
        )
    rows.append(
        [{"text": "تحويل", "callback_data": f"protT:{page}:{uid}", "style": "success"}]
    )
    rows.append(
        [{"text": "إخفاء", "callback_data": f"protH:{uid}", "style": "danger"}]
    )
    return rows


# ============================================================


# translator = googletranstr()


list_UwU = [
    "كس",
    "كسمك",
    "كسختك",
    "عير",
    "كسخالتك",
    "خرا بالله",
    "عير بالله",
    "كسخواتكم",
    "كحاب",
    "مناويج",
    "مناويج",
    "كحبه",
    "ابن الكحبه",
    "فرخ",
    "فروخ",
    "طيزك",
    "طيزختك",
    "كسمك",
    "يا ابن الخول",
    "المتناك",
    "شرموط",
    "شرموطه",
    "ابن الشرموطه",
    "ابن الخول",
    "ابن العرص",
    "منايك",
    "متناك",
    "ابن المتناكه",
    "زبك",
    "عرص",
    "زبي",
    "خول",
    "لبوه",
    "لباوي",
    "ابن اللبوه",
    "منيوك",
    "كسمكك",
    "متناكه",
    "يا عرص",
    "يا خول",
    "قحبه",
    "القحبه",
    "شراميط",
    "العلق",
    "العلوق",
    "العلقه",
    "كسمك",
    "يا ابن الخول",
    "المتناك",
    "شرموط",
    "شرموطه",
    "ابن الشرموطه",
    "ابن الخول",
    "االمنيوك",
    "كسمككك",
    "الشرموطه",
    "ابن العرث",
    "ابن الحيضانه",
    "زبك",
    "خول",
    "زبي",
    "قاحب",
]

list_Shiaa = [
    "يا علي",
    "يا حسين",
    "ياعلي",
    "ياحسين",
    "علي ولي الله",
    "عليا ولي الله",
    "عائشه زانيه",
    "عائشة زانية",
    "عائشة عاهرة",
    "عائشه عاهره",
    "خرب ربك",
    "خرب الله",
    "يلعن ربك",
    "يلعن الله",
    "يا عمر",
    "ياعمر",
    "يا محمد",
    "يامحمد",
    "زوجات الرسول",
    "عير بالسنة",
    "عير بالسنه",
    "خرب السنه",
    "خرا بالسنه",
    "خرب السنة",
    "خرا بالسنة",
    "والحسين",
    "والعباس",
    "وعلي",
    "والامام علي",
    "ربنا علي",
    "علي الله",
    "الله علي",
    "رب علي",
    "علي رب",
]


def Find(text):
    m = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(m, text)
    return [x[0] for x in url]


"""
         r.get(f'{m.chat.id}:mute:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockJoin:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockChannels:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockEdit:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockEditM:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockVoice:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockVideo:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockNot:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockPhoto:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockStickers:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockAnimations:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockFiles:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockPersian:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockUrls:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockHashtags:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockMessages:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockTags:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockBots:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockSpam:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockInline:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockForward:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockAudios:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockaddContacts:{Dev_Zaid}')
         r.get(f'{m.chat.id}:lockSHTM:{Dev_Zaid}')
"""

from pyrogram.errors import UserNotParticipant, FloodWait


@Client.on_message(filters.group, group=-1111111111111)
async def on_zbi(c: Client, m: Message):
    name = r.get(f"{Dev_Zaid}:BotName") if r.get(f"{Dev_Zaid}:BotName") else "ليو"
    text = m.text
    if text and text.startswith(f"{name} "):
        text = text.replace(f"{name} ", "")
    if r.get(f"{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}"):
        text = r.get(f"{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}")
    if r.get(f"Custom:{Dev_Zaid}&text={text}"):
        text = r.get(f"Custom:{Dev_Zaid}&text={text}")

    if r.get(f"inDontCheck:{Dev_Zaid}"):
        return m.continue_propagation()

    if not m.from_user:
        return

    if dev_pls(m.from_user.id, m.chat.id):
        return

    if (
        text
        and (
            text.startswith("تفعيل ")
            or text.startswith("تعطيل ")
            or text.startswith("قفل ")
            or text.startswith("فتح ")
            or text == "ايدي"
            or text == "الاوامر"
        )
    ):
        if r.get(f"forceChannel:{Dev_Zaid}") and (
            not r.get(f"disableSubscribe:{Dev_Zaid}")
        ):
            username = r.get(f"forceChannel:{Dev_Zaid}").replace("@", "")
            not_member = False
            try:
                member = await c.get_chat_member(username, m.from_user.id)
            except FloodWait:
                return m.continue_propagation()
            except UserNotParticipant:
                send_colored_message(
                    c,
                    m.chat.id,
                    f"- انضم للقناة ( @{username} ) لتستطيع استخدام اوامر البوت",
                    rows=[
                        [
                            {
                                "text": "اضغط هنا",
                                "url": "https://t.me/" + username,
                                "style": "primary",
                            }
                        ]
                    ],
                )
                r.set(f"inDontCheck:{Dev_Zaid}", 1, ex=10)
                return m.stop_propagation()
            except Exception as e:
                print(e)
                return m.continue_propagation()

            if member.status in {
                enums.ChatMemberStatus.LEFT,
                enums.ChatMemberStatus.BANNED,
            } or member.status is None:
                not_member = True
            else:
                not_member = False

            if not_member:
                send_colored_message(
                    c,
                    m.chat.id,
                    f"- انضم للقناة ( @{username} ) لتستطيع استخدام اوامر البوت",
                    rows=[
                        [
                            {
                                "text": "اضغط هنا",
                                "url": "https://t.me/" + username,
                                "style": "primary",
                            }
                        ]
                    ],
                )
                r.set(f"inDontCheck:{Dev_Zaid}", ex=10)
                return m.stop_propagation()
            else:
                return m.continue_propagation()


@Client.on_message(filters.group, group=27)
def guardLocksResponse(c, m):
    k = r.get(f"{Dev_Zaid}:botkey")
    channel = (
        r.get(f"{Dev_Zaid}:BotChannel") if r.get(f"{Dev_Zaid}:BotChannel") else "YQYQY6"
    )
    Thread(target=guardResponseFunction, args=(c, m, k, channel)).start()


@Client.on_edited_message(filters.group, group=27)
def guardLocksResponse2(c, m):
    k = r.get(f"{Dev_Zaid}:botkey")
    channel = (
        r.get(f"{Dev_Zaid}:BotChannel") if r.get(f"{Dev_Zaid}:BotChannel") else "YQYQY6"
    )
    Thread(target=guardResponseFunction2, args=(c, m, k, channel)).start()


def guardResponseFunction2(c, m, k, channel):
    if not r.get(f"{m.chat.id}:enable:{Dev_Zaid}"):
        return
    warner = """
「 {} 」
{} ممنوع {}
☆
"""
    warn = False
    reason = False

    if m.sender_chat:
        id = m.sender_chat.id
        mention = f"[{m.sender_chat.title}](t.me/{channel})"
    if m.from_user:
        id = m.from_user.id
        mention = m.from_user.mention

    # استثناء البوت نفسه لما يعدل رسالة من عنده، واستثناء أصحاب الرتب
    # العالية (المطور/المالك/مالك الجروب/المدير/أي مشرف تليجرام حقيقي) —
    # دول مفروض مايتطبقش عليهم قفل التعديل خالص. الإرسال المجهول (مشرف
    # متخفي أو قناة مرتبطة) بيتعامل معاه كمان كإدمن موثوق فيه.
    # استثناء البوت نفسه لما يعدل رسالة من عنده، واستثناء المدير فما فوق
    # (مالك، مطور) ومشرفين تليجرام الحقيقيين بس - رتبة "أدمن" وتحت ممنوعة
    # زي أي عضو عادي. الإرسال المجهول (مشرف متخفي أو قناة مرتبطة) بيتعامل
    # معاه كمان كإدمن موثوق فيه.
    exempt = False
    if m.from_user:
        if m.from_user.id == c.me.id or mod_pls(m.from_user.id, m.chat.id):
            exempt = True
        else:
            try:
                member = m.chat.get_member(m.from_user.id)
                if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                    exempt = True
            except:
                pass
    elif m.sender_chat:
        exempt = True
    if exempt:
        return

    if r.get(f"{m.chat.id}:lockEdit:{Dev_Zaid}") and m.text:
        apply_lock_punishment(c, m, m.chat.id, "lockEdit", id, mention, k)
        warn = True
        reason = "التعديل"
        if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not r.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            r.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return m.reply(
                warner.format(mention, k, reason), disable_web_page_preview=True
            )

    if r.get(f"{m.chat.id}:lockEditM:{Dev_Zaid}") and m.media:
        apply_lock_punishment(c, m, m.chat.id, "lockEditM", id, mention, k)
        warn = True
        reason = "تعديل الميديا"
        if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not r.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            r.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return m.reply(
                warner.format(mention, k, reason), disable_web_page_preview=True
            )


# ============================================================
# 📡 تفعيل/تعطيل القنوات تلقائي ( زي أمر "تفعيل"/"تعطيل" في المجموعات
# + إشعار المطورين زي إشعار "شخص جديد دخل للبوت" في الخاص )
# القنوات - عكس المجموعات - ما بتبعتش new_chat_members لما البوت يتضاف،
# وبرضو مفيش عضو عادي يقدر يكتب "تفعيل" في قناة (المرسل مخفي/القناة نفسها
# هي اللي بتظهر كمرسل)، فبدل كده بنستخدم my_chat_member (ChatMemberUpdated)
# عشان نمسك اللحظة اللي البوت بيتضاف/بيتترقى أدمن فيها.
#
# بنبعت إشعارين مختلفين للمطورين:
# 1) لحظة ما البوت يتضاف كعضو عادي (لسه مش أدمن) → إشعار سريع فوري زي
#    إشعار "شخص جديد دخل للبوت" بالظبط، عشان تلاقي إشعار حتى لو محدش رقّاه
#    أدمن بعدين.
# 2) لحظة ما البوت يتترقى أدمن → نفعّل القناة فعليًا (زي أمر "تفعيل" في
#    المجموعات بالظبط: تسجيلها في channelslist + رسالة تفعيل في القناة نفسها
#    + إشعار تفصيلي للمطورين).
# ملحوظة: الاشتراط القديم إن البوت لازم يكون عنده *كل* الصلاحيات الأربعة
# (منها can_invite_users اللي مش دايمًا بتتفعّل تلقائي في القنوات) كان بيوقف
# التفعيل بصمت من غير أي إشعار، فاتشال الشرط ده وبقى يكفي إنه أدمن بأي صلاحية.
# ============================================================

@Client.on_chat_member_updated(filters.channel)
async def on_bot_channel_membership_update(c: Client, u: ChatMemberUpdated):
    try:
        if not u.new_chat_member or not u.new_chat_member.user or not u.new_chat_member.user.is_self:
            return
        k = r.get(f'{Dev_Zaid}:botkey')
        status = u.new_chat_member.status
        by = u.from_user
        mention = by.mention if by else 'مجهول'
        usrr = ('@' + by.username) if (by and by.username) else 'مافيه'
        byid = by.id if by else 'مجهول'
        chatusr = '@' + u.chat.username if u.chat.username else 'مافيه'

        async def notify_devs(text, reply_markup=None):
            if r.get(f'DevGroup:{Dev_Zaid}'):
                try:
                    await c.send_message(int(r.get(f'DevGroup:{Dev_Zaid}')), text, reply_markup=reply_markup, disable_web_page_preview=True)
                except Exception:
                    pass
            else:
                for dev in get_devs_br():
                    try:
                        await c.send_message(int(dev), text, disable_web_page_preview=True, reply_markup=reply_markup)
                        await asyncio.sleep(3)
                    except Exception:
                        pass

        # ===== إشعار فوري لحظة إضافة البوت للقناة (سواء عضو أو أدمن مباشرة) =====
        if status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR) and not r.get(f'{u.chat.id}:seenChannel:{Dev_Zaid}'):
            r.set(f'{u.chat.id}:seenChannel:{Dev_Zaid}', 1)
            text = '''
☆ قناة جديدة اتضاف لها البوت
☆ من : {}
☆ يوزره : {}
☆ ايديه : `{}`

☆ اسم القناة : {}
☆ يوزر القناة : {}
☆ ايدي القناة : `{}`
'''.format(mention, usrr, byid, u.chat.title, chatusr, u.chat.id)
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(by.first_name, url=f"tg://user?id={by.id}")]]) if by else None
            await notify_devs(text, reply_markup)

        # ===== البوت اتضاف/اترقى أدمن في القناة → نفعّلها زي "تفعيل" بالظبط =====
        if status == ChatMemberStatus.ADMINISTRATOR:
            if r.get(f'{u.chat.id}:enable:{Dev_Zaid}'):
                return  # مفعلة من قبل
            if r.get(f'DisableBot:{Dev_Zaid}'):
                try:
                    await c.send_message(u.chat.id, f'{k} تم تعطيل البوت الخدمي من المطور')
                except Exception:
                    pass
                return

            r.set(f'{u.chat.id}:enable:{Dev_Zaid}', 1)
            r.sadd(f'channelslist:{Dev_Zaid}', u.chat.id)

            try:
                await c.send_message(u.chat.id, f'{k} من「 {mention} 」\n{k} ابشر تم تفعيل القناة\n☆')
            except Exception:
                pass

            try:
                get = await c.get_chat(u.chat.id)
                invite_link = get.invite_link
            except Exception:
                invite_link = None

            text = f'{k} من「 {mention} 」\n'
            text += f'{k} يوزره : {usrr}\n'
            text += f'{k} ايديه : `{byid}`\n'
            text += f'\n{k} تم تفعيل البوت بقناة جديدة :\n\n'
            text += f'{k} اسم القناة : {u.chat.title}\n'
            text += f'{k} يوزر القناة : {chatusr}\n'
            text += f'{k} ايدي القناة : `{u.chat.id}`'
            if r.smembers(f'channelslist:{Dev_Zaid}'):
                text += f'\n{k} عدد القنوات الآن : {len(r.smembers(f"channelslist:{Dev_Zaid}"))}\n'
            text += '\n\n☆'
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(u.chat.title, url=invite_link)]]) if invite_link else None
            await notify_devs(text, reply_markup)

        # ===== البوت اتشال من الأدمنية أو خرج/اتطرد من القناة → نعطلها زي "تعطيل" بالظبط =====
        elif status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
            r.delete(f'{u.chat.id}:seenChannel:{Dev_Zaid}')
            if not r.get(f'{u.chat.id}:enable:{Dev_Zaid}'):
                return
            r.delete(f'{u.chat.id}:enable:{Dev_Zaid}')
            r.srem(f'channelslist:{Dev_Zaid}', u.chat.id)

            text = f'{k} من「 {mention} 」\n'
            text += f'{k} يوزره : {usrr}\n'
            text += f'{k} ايديه : `{byid}`\n'
            text += f'\n{k} تم تعطيل البوت بقناة :\n\n'
            text += f'{k} اسم القناة : {u.chat.title}\n'
            text += f'{k} يوزر القناة : {chatusr}\n'
            text += f'{k} ايدي القناة : `{u.chat.id}`'
            if r.smembers(f'channelslist:{Dev_Zaid}'):
                text += f'\n{k} عدد القنوات الآن : {len(r.smembers(f"channelslist:{Dev_Zaid}"))}\n'
            text += '\n\n☆'
            await notify_devs(text)
    except Exception as e:
        print(e)


def guardResponseFunction(c, m, k, channel):
    if not r.get(f"{m.chat.id}:enable:{Dev_Zaid}"):
        return
    warner = """
「 {} 」
{} ممنوع {}
☆
"""
    warn = False
    reason = False

    if r.get(f"{m.chat.id}:lockNot:{Dev_Zaid}") and m.service:
        m.delete()

    if (
        r.get(f"{m.chat.id}:lockaddContacts:{Dev_Zaid}")
        and m.from_user
        and m.new_chat_members
    ):
        if pre_pls(m.from_user.id, m.chat.id):
            return
        for me in m.new_chat_members:
            if not me.id == m.from_user.id:
                warn = True
                mention = m.from_user.mention
                m.chat.ban_member(me.id)
                reason = "تضيف حد هنا"
                m.delete()
                if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}"):
                    return m.reply(
                        warner.format(mention, k, reason), disable_web_page_preview=True
                    )

    if m.sender_chat:
        id = m.sender_chat.id
        mention = f"[{m.sender_chat.title}](t.me/{channel})"
    if m.from_user:
        id = m.from_user.id
        mention = m.from_user.mention

    # print(id)

    if m.media:
        rep = m
        if rep.sticker:
            file_id = rep.sticker.file_id
        if rep.animation:
            file_id = rep.animation.file_id
        if rep.photo:
            file_id = rep.photo.file_id
        if rep.video:
            file_id = rep.video.file_id
        if rep.voice:
            file_id = rep.voice.file_id
        if rep.audio:
            file_id = rep.audio.file_id
        if rep.document:
            file_id = rep.document.file_id
        idd = file_id[-6:]
        if r.get(f"{idd}:NotAllow:{m.chat.id}{Dev_Zaid}"):
            if not admin_pls(id, m.chat.id, c):
                return m.delete()

    if m.text and r.smembers(f"{m.chat.id}:NotAllowedListText:{Dev_Zaid}"):
        if not admin_pls(id, m.chat.id, c):
            for word in r.smembers(f"{m.chat.id}:NotAllowedListText:{Dev_Zaid}"):
                if word in m.text:
                    return m.delete()

    if r.get(f"{id}:mute:{m.chat.id}{Dev_Zaid}") or r.get(f"{id}:mute:{Dev_Zaid}"):
        try:
            m.delete()
        except Exception:
            pass
        return False

    is_pre = False
    try:
        is_pre = pre_pls(id, m.chat.id)
    except Exception:
        is_pre = False

    if is_pre and not any_wired_scope_all(m.chat.id):
        return False

    if r.get(f"{m.chat.id}:mute:{Dev_Zaid}"):
        apply_lock_punishment(c, m, m.chat.id, "mute", id, mention, k)
        return False

    if (
        r.get(f"{m.chat.id}:lockBots:{Dev_Zaid}")
        and m.new_chat_members
        and not is_pre
    ):
        for mem in m.new_chat_members:
            if mem.is_bot:
                return m.chat.ban_member(mem.id)

    if (
        r.get(f"{m.chat.id}:lockJoin:{Dev_Zaid}")
        and m.new_chat_members
        and not is_pre
    ):
        for mem in m.new_chat_members:
            if not admin_pls(mem.id, m.chat.id, c):
                m.chat.ban_member(mem.id)
                m.chat.unban_member(mem.id)
                return False

    if (
        r.get(f"{m.chat.id}:lockChannels:{Dev_Zaid}")
        and m.sender_chat
        and not is_pre
    ):
        try:
            m.delete()
        except Exception:
            pass
        try:
            m.chat.ban_member(m.sender_chat.id)
        except Exception:
            pass
        return c.send_message(m.chat.id, f"{k} ممنوع القنوات\n☆")

    if r.get(f"{m.chat.id}:lockSpam:{Dev_Zaid}"):
        if not r.get(f"{id}in_spam:{m.chat.id}{Dev_Zaid}"):
            r.set(f"{id}in_spam:{m.chat.id}{Dev_Zaid}", 1, ex=10)
        else:
            if int(r.get(f"{id}in_spam:{m.chat.id}{Dev_Zaid}")) == 10:
                if m.from_user:
                    r.delete(f"{id}in_spam:{m.chat.id}{Dev_Zaid}")
                    apply_lock_punishment(c, m, m.chat.id, "lockSpam", id, mention, k)
                    return False

                if m.sender_chat:
                    m.chat.ban_member(m.sender_chat)
                    return m.reply(
                        f"「 {mention} 」 {k} حظرتك يالبثر عشان تتعلم تكرر\n☆"
                    )
            else:
                get = int(r.get(f"{id}in_spam:{m.chat.id}{Dev_Zaid}"))
                r.set(f"{id}in_spam:{m.chat.id}{Dev_Zaid}", get + 1, ex=10)

    if r.get(f"{m.chat.id}:lockInline:{Dev_Zaid}") and m.via_bot:
        apply_lock_punishment(c, m, m.chat.id, "lockInline", id, mention, k)
        warn = True
        reason = "ترسل انلاين"
        if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not r.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            r.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return m.reply(
                warner.format(mention, k, reason), disable_web_page_preview=True
            )

    if r.get(f"{m.chat.id}:lockForward:{Dev_Zaid}") and m.forward_date:
        apply_lock_punishment(c, m, m.chat.id, "lockForward", id, mention, k)
        warn = True
        reason = "ترسل توجيه"
        if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not r.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            r.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return m.reply(
                warner.format(mention, k, reason), disable_web_page_preview=True
            )

    """
  if r.get(f'{m.chat.id}:lockForward:{Dev_Zaid}') and m.forward_from_chat:
     m.delete()
     warn = True
     reason = 'ترسل توجيه'
     if not r.get(f'{m.chat.id}:disableWarn:{Dev_Zaid}') and not r.get(f'{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}'):
        r.set(f'{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}',1,ex=60)
        return m.reply(warner.format(mention,k,reason),disable_web_page_preview=True)
  """

    if r.get(f"{m.chat.id}:lockAudios:{Dev_Zaid}") and m.audio:
        apply_lock_punishment(c, m, m.chat.id, "lockAudios", id, mention, k)
        warn = True
        reason = "ترسل صوت"
        if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not r.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            r.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return m.reply(
                warner.format(mention, k, reason), disable_web_page_preview=True
            )

    if r.get(f"{m.chat.id}:lockVideo:{Dev_Zaid}") and m.video:
        apply_lock_punishment(c, m, m.chat.id, "lockVideo", id, mention, k)
        warn = True
        reason = "ترسل فيديوهات"
        if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not r.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            r.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return m.reply(
                warner.format(mention, k, reason), disable_web_page_preview=True
            )

    if r.get(f"{m.chat.id}:lockPhoto:{Dev_Zaid}") and m.photo:
        apply_lock_punishment(c, m, m.chat.id, "lockPhoto", id, mention, k)
        warn = True
        reason = "ترسل صور"
        if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not r.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            r.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return m.reply(
                warner.format(mention, k, reason), disable_web_page_preview=True
            )

    if r.get(f"{m.chat.id}:lockStickers:{Dev_Zaid}") and m.sticker:
        apply_lock_punishment(c, m, m.chat.id, "lockStickers", id, mention, k)
        warn = True
        reason = "ترسل ملصقات"
        if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not r.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            r.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return m.reply(
                warner.format(mention, k, reason), disable_web_page_preview=True
            )

    if r.get(f"{m.chat.id}:lockAnimations:{Dev_Zaid}") and m.animation:
        apply_lock_punishment(c, m, m.chat.id, "lockAnimations", id, mention, k)
        warn = True
        reason = "ترسل متحركات"
        if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not r.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            r.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return m.reply(
                warner.format(mention, k, reason), disable_web_page_preview=True
            )

    if r.get(f"{m.chat.id}:lockFiles:{Dev_Zaid}") and m.document:
        apply_lock_punishment(c, m, m.chat.id, "lockFiles", id, mention, k)
        warn = True
        reason = "ترسل ملفات"
        if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not r.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            r.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return m.reply(
                warner.format(mention, k, reason), disable_web_page_preview=True
            )

    if r.get(f"{m.chat.id}:lockPersian:{Dev_Zaid}") and m.text:
        if "ه‍" in m.text or "ی" in m.text or "ک" in m.text or "چ" in m.text:
            apply_lock_punishment(c, m, m.chat.id, "lockPersian", id, mention, k)
            warn = True
            reason = "ترسل فارسي"
            if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}"):
                return m.reply(
                    warner.format(mention, k, reason), disable_web_page_preview=True
                )

    if r.get(f"{m.chat.id}:lockPersian:{Dev_Zaid}") and m.caption:
        if "ه‍" in m.caption or "ی" in m.caption or "ک" in m.caption or "چ" in m.caption:
            apply_lock_punishment(c, m, m.chat.id, "lockPersian", id, mention, k)
            warn = True
            reason = "ترسل فارسي"
            if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}"):
                return m.reply(
                    warner.format(mention, k, reason), disable_web_page_preview=True
                )

    if (
        r.get(f"{m.chat.id}:lockUrls:{Dev_Zaid}")
        and m.text
        and len(Find(m.text.html)) > 0
    ):
        apply_lock_punishment(c, m, m.chat.id, "lockUrls", id, mention, k)
        warn = True
        reason = "ترسل روابط"
        if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not r.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            r.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return m.reply(
                warner.format(mention, k, reason), disable_web_page_preview=True
            )

    if (
        r.get(f"{m.chat.id}:lockHashtags:{Dev_Zaid}")
        and m.text
        and len(re.findall(r"#(\w+)", m.text)) > 0
    ):
        apply_lock_punishment(c, m, m.chat.id, "lockHashtags", id, mention, k)
        warn = True
        reason = "ترسل هاشتاق"
        if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not r.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            r.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return m.reply(
                warner.format(mention, k, reason), disable_web_page_preview=True
            )

    if r.get(f"{m.chat.id}:lockMessages:{Dev_Zaid}") and m.text and len(m.text) > 150:
        apply_lock_punishment(c, m, m.chat.id, "lockMessages", id, mention, k)
        warn = True
        reason = "ترسل كلام كثير"
        if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not r.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            r.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return m.reply(
                warner.format(mention, k, reason), disable_web_page_preview=True
            )

    if r.get(f"{m.chat.id}:lockVoice:{Dev_Zaid}") and m.voice:
        apply_lock_punishment(c, m, m.chat.id, "lockVoice", id, mention, k)
        warn = True
        reason = "ترسل فويس"
        if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not r.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            r.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return m.reply(
                warner.format(mention, k, reason), disable_web_page_preview=True
            )

    if r.get(
        f"{m.chat.id}:lockTags:{Dev_Zaid}"
    ) and '"type": "MessageEntityType.MENTION"' in str(m):
        apply_lock_punishment(c, m, m.chat.id, "lockTags", id, mention, k)
        warn = True
        reason = "ترسل منشنات"
        if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not r.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            r.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return m.reply(
                warner.format(mention, k, reason), disable_web_page_preview=True
            )

    if r.get(f"{m.chat.id}:lockSHTM:{Dev_Zaid}") and (m.caption or m.text):
        if m.caption:
            txt = m.caption
        if m.text:
            txt = m.text
        for a in list_UwU:
            if txt == a or f" {a} " in txt or a in txt:
                apply_lock_punishment(c, m, m.chat.id, "lockSHTM", id, mention, k)
                warn = True
                reason = "السب هنا"
                if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not r.get(
                    f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
                ):
                    r.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
                    return m.reply(
                        warner.format(mention, k, reason), disable_web_page_preview=True
                    )

    """
  if r.get(f'{m.chat.id}:lockKFR:{Dev_Zaid}') and (m.caption or m.text):
     if m.caption:
         txt = m.caption.replace("*","").replace("`","").replace("|","").replace("#","").replace("<","").replace(">","").replace("_","").replace("ـ","").replace("َ","").replace("ٕ","").replace("ُ","").replace("ِ","").replace("ٰ","").replace("ٖ","").replace("ً","").replace("ّ","").replace("ٌ","").replace("ٍ","").replace("ْ","").replace("ٔ","").replace("'","").replace('"',"")
     if m.text:
         txt = m.text.replace("*","").replace("`","").replace("|","").replace("#","").replace("<","").replace(">","").replace("_","").replace("ـ","").replace("َ","").replace("ٕ","").replace("ُ","").replace("ِ","").replace("ٰ","").replace("ٖ","").replace("ً","").replace("ّ","").replace("ٌ","").replace("ٍ","").replace("ْ","").replace("ٔ","").replace("'","").replace('"',"")
     for kfr in list_Shiaa:
         if kfr in txt:
            m.delete()
            warn = True
            reason = 'الكفر هنا'
            if not r.get(f'{m.chat.id}:disableWarn:{Dev_Zaid}') and not r.get(f'{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}'):
                 r.set(f'{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}',1,ex=60)
                 return m.reply(warner.format(mention,k,reason),disable_web_page_preview=True)
  """

    if r.get(f"{m.chat.id}:lockJoinPersian:{Dev_Zaid}") and m.new_chat_members:
        if m.from_user.first_name:
            if (
                m.from_user.first_name in persianInformation["names"]
                or m.from_user.id in persianInformation["ids"]
                or "ه‍" in m.from_user.first_name
                or "ی" in m.from_user.first_name
                or "ک" in m.from_user.first_name
                or "چ" in m.from_user.first_name
                or "👙" in m.from_user.first_name
            ) and not pre_pls(m.from_user.id, m.chat.id):
                if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}"):
                    m.reply(
                        """
「 {} 」
{} تم حظره لاشتباهه ببوت إيراني
☆
""".format(m.from_user.mention, k)
                    )
                return c.ban_chat_member(m.chat.id, m.from_user.id)

        if m.from_user.last_name:
            if (
                m.from_user.last_name in persianInformation["last_names"]
                or m.from_user.id in persianInformation["ids"]
                or "ه‍" in m.from_user.last_name
                or "ی" in m.from_user.last_name
                or "ک" in m.from_user.last_name
                or "چ" in m.from_user.last_name
                or "👙" in m.from_user.last_name
            ) and not pre_pls(m.from_user.id, m.chat.id):
                if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}"):
                    m.reply(
                        """
「 {} 」
{} تم حظره لاشتباهه ببوت إيراني
☆
""".format(m.from_user.mention, k)
                    )
                return c.ban_chat_member(m.chat.id, m.from_user.id)

    if r.get(f"{m.chat.id}:enableVerify:{Dev_Zaid}") and m.new_chat_members:
        for me in m.new_chat_members:
            if not pre_pls(me.id, m.chat.id):
                c.restrict_chat_member(
                    m.chat.id, me.id, ChatPermissions(can_send_messages=False)
                )
                get_random = get_for_verify(me)
                question = get_random["question"]
                reply_markup = get_random["key"]
                return m.reply(
                    f"{k} قيدناك عشان نتاكد انك شخص حقيقي مو زومبي\n\n{question}",
                    reply_markup=reply_markup,
                )

    if m.media and r.get(f"{m.chat.id}:lockNSFW:{Dev_Zaid}"):
        print("nsfw scanner")
        if not admin_pls(id, m.chat.id, c):
            if m.sticker:
                id = m.sticker.thumbs[0].file_id
            if m.photo:
                id = m.photo.file_id
            if m.video:
                id = m.video.thumbs[0].file_id
            if m.animation:
                id = m.animation.thumbs[0].file_id
        file = c.download_media(id)
        Thread(target=scanR, args=(c, m, id, file)).start()


def scanR(c, m, id, file):
    RUN(scan4(c, m, id, file))


async def scan4(c, m, id, file):
    session = ClientSession()
    arq = ARQ(ARQ_API_URL, ARQ_API_KEY, session)
    resp = await arq.nsfw_scan(file=file)
    if resp.result.is_nsfw:
        print("xNSFW")
        k = r.get(f"{Dev_Zaid}:botkey")
        chat_id = m.chat.id
        uid = m.from_user.id if m.from_user else m.sender_chat.id
        channel = (
            r.get(f"{Dev_Zaid}:BotChannel") if r.get(f"{Dev_Zaid}:BotChannel") else "YQYQY6"
        )
        mention = (
            m.from_user.mention
            if m.from_user
            else f"[{m.sender_chat.title}](t.me/{channel})"
        )
        try:
            await m.delete()
        except Exception:
            pass

        scope = get_punish_scope(chat_id, "lockNSFW")
        is_protected = False
        try:
            is_protected = pre_pls(uid, chat_id)
        except Exception:
            is_protected = False

        if not (is_protected and scope == "members"):
            if is_protected and scope == "all":
                try:
                    await c.promote_chat_member(
                        chat_id,
                        uid,
                        privileges=ChatPrivileges(
                            can_manage_chat=False,
                            can_delete_messages=False,
                            can_manage_video_chats=False,
                            can_restrict_members=False,
                            can_promote_members=False,
                            can_pin_messages=False,
                            can_change_info=False,
                            can_invite_users=False,
                        ),
                    )
                except Exception:
                    pass

            action = get_punish_action(chat_id, "lockNSFW")
            if action == "kick":
                try:
                    await c.ban_chat_member(chat_id, uid)
                    await c.unban_chat_member(chat_id, uid)
                except Exception:
                    pass
            elif action == "mute":
                try:
                    await c.restrict_chat_member(
                        chat_id, uid, ChatPermissions(can_send_messages=False)
                    )
                except Exception:
                    pass

        await m.reply(
            f"「 {mention} 」\n{k} تم حذف رسالتك لإحتوائها على محتوى إباحي .\n☆"
        )
    os.remove(file)
    await session.close()


def get_for_verify(me):
    for_verify = [
        {
            "question": "ماهو الحيوان الذي ينتهي اسمه بحرف الباء ؟",
            "key": InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("فأر", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("وشق", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("بشار الأسد", callback_data=f"no:{me.id}"),
                    ],
                    [
                        InlineKeyboardButton("حمار", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("كلب", callback_data=f"yes:{me.id}"),
                        InlineKeyboardButton("قطة", callback_data=f"no:{me.id}"),
                    ],
                ]
            ),
        },
        {
            "question": "ماهي عاصمة فرنسا؟",
            "key": InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("دمشق", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("الرياض", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("باريس", callback_data=f"yes:{me.id}"),
                    ],
                    [
                        InlineKeyboardButton("الكويت", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("القاهرة", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("ماشا والدب", callback_data=f"no:{me.id}"),
                    ],
                ]
            ),
        },
        {
            "question": "نادي يبدأ بحرف الباء :",
            "key": InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("برشلونا", callback_data=f"yes:{me.id}"),
                        InlineKeyboardButton("الهلال", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("النصر", callback_data=f"no:{me.id}"),
                    ],
                    [
                        InlineKeyboardButton("الزمالك", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("ريال مدريد", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("مانشستر", callback_data=f"no:{me.id}"),
                    ],
                ]
            ),
        },
        {
            "question": "دولة يبدأ اسمها بحرف التاء :",
            "key": InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("قطر", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("امريكا", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("سوريا", callback_data=f"no:{me.id}"),
                    ],
                    [
                        InlineKeyboardButton("مصر", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("الصين", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("تركيا", callback_data=f"yes:{me.id}"),
                    ],
                ]
            ),
        },
        {
            "question": "اختر هذا الايموجي - 🤑 -",
            "key": InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🍭", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("🤑", callback_data=f"yes:{me.id}"),
                        InlineKeyboardButton("🏆", callback_data=f"no:{me.id}"),
                    ],
                    [
                        InlineKeyboardButton("🌀", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("🪨", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("💎", callback_data=f"no:{me.id}"),
                    ],
                ]
            ),
        },
        {
            "question": "اختر هذا الايموجي - 🔓 -",
            "key": InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🏆", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("💎", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("🙄", callback_data=f"no:{me.id}"),
                    ],
                    [
                        InlineKeyboardButton("💸", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("💣", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("🔓", callback_data=f"yes:{me.id}"),
                    ],
                ]
            ),
        },
        {
            "question": "اختر هذا الايموجي - 🌠 -",
            "key": InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("☄️", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("🙈", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("🦄", callback_data=f"no:{me.id}"),
                    ],
                    [
                        InlineKeyboardButton("🌠", callback_data=f"yes:{me.id}"),
                        InlineKeyboardButton("🌈", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("🧑‍💻", callback_data=f"no:{me.id}"),
                    ],
                ]
            ),
        },
        {
            "question": "ماهي عاصمة سوريا",
            "key": InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("دمشق", callback_data=f"yes:{me.id}"),
                        InlineKeyboardButton("دير الزور", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("ادلب", callback_data=f"no:{me.id}"),
                    ],
                    [
                        InlineKeyboardButton("ليو ميسي", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("الرياض", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("مزة فيلات", callback_data=f"no:{me.id}"),
                    ],
                ]
            ),
        },
        {
            "question": "ماهي عملة الولايات المتحدة الأمريكية",
            "key": InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("الروبية", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("الجنيه", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("الليرة", callback_data=f"no:{me.id}"),
                    ],
                    [
                        InlineKeyboardButton("الدولار", callback_data=f"yes:{me.id}"),
                        InlineKeyboardButton("الدينار", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("الين", callback_data=f"no:{me.id}"),
                    ],
                ]
            ),
        },
        {
            "question": "اسم مذكر يبدأ بحرف ز",
            "key": InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("زيد", callback_data=f"yes:{me.id}"),
                        InlineKeyboardButton("علي", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("محمد", callback_data=f"no:{me.id}"),
                    ],
                    [
                        InlineKeyboardButton("عمر", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("المريخ", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("احمد", callback_data=f"no:{me.id}"),
                    ],
                ]
            ),
        },
        {
            "question": "اسم مؤنث ينتهي بحرف ي",
            "key": InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("لورين", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("ماجدة", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("علياء", callback_data=f"no:{me.id}"),
                    ],
                    [
                        InlineKeyboardButton("أماني", callback_data=f"yes:{me.id}"),
                        InlineKeyboardButton("فرح", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("أمل", callback_data=f"no:{me.id}"),
                    ],
                ]
            ),
        },
        {
            "question": "اسم مؤنث يبدأ بحرف أ",
            "key": InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("لورين", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("ماجدة", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("علياء", callback_data=f"no:{me.id}"),
                    ],
                    [
                        InlineKeyboardButton("أمل", callback_data=f"yes:{me.id}"),
                        InlineKeyboardButton("فرح", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("يمنى", callback_data=f"no:{me.id}"),
                    ],
                ]
            ),
        },
        {
            "question": "الأسبوع كم يوم؟",
            "key": InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("1", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("2", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("3", callback_data=f"no:{me.id}"),
                    ],
                    [
                        InlineKeyboardButton("4", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("5", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("6", callback_data=f"no:{me.id}"),
                    ],
                    [
                        InlineKeyboardButton("7", callback_data=f"yes:{me.id}"),
                        InlineKeyboardButton("8", callback_data=f"no:{me.id}"),
                        InlineKeyboardButton("9", callback_data=f"no:{me.id}"),
                    ],
                ]
            ),
        },
    ]
    return random.choice(for_verify)


@Client.on_chat_join_request(filters.group, group=100)
def antiPersian(c, m):
    if r.get(f"{m.chat.id}:lockJoinPersian:{Dev_Zaid}"):
        k = r.get(f"{Dev_Zaid}:botkey")
        if not pre_pls(m.from_user.id, m.chat.id):
            if m.from_user.first_name:
                if (
                    m.from_user.first_name in persianInformation["names"]
                    or m.from_user.id in persianInformation["ids"]
                    or "ه‍" in m.from_user.first_name
                    or "ی" in m.from_user.first_name
                    or "ک" in m.from_user.first_name
                    or "چ" in m.from_user.first_name
                    or "👙" in m.from_user.first_name
                ):
                    c.decline_chat_join_request(m.chat.id, m.from_user.id)
                    if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}"):
                        c.send_message(
                            m.chat.id,
                            """
「 {} 」
{} تم رفض طلب انضمامه لاشتباهه ببوت إيراني
☆
""".format(m.from_user.mention, k),
                        )
                    return True
            if m.from_user.last_name:
                if (
                    m.from_user.last_name in persianInformation["last_names"]
                    or m.from_user.id in persianInformation["ids"]
                    or "ه‍" in m.from_user.last_name
                    or "ی" in m.from_user.last_name
                    or "ک" in m.from_user.last_name
                    or "چ" in m.from_user.last_name
                    or "👙" in m.from_user.last_name
                ):
                    c.decline_chat_join_request(m.chat.id, m.from_user.id)
                    if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}"):
                        c.send_message(
                            m.chat.id,
                            """
「 {} 」
{} تم رفض طلب انضمامه لاشتباهه ببوت إيراني
☆
""".format(m.from_user.mention, k),
                        )
                    return True


@Client.on_message((filters.group | filters.channel) & filters.text, group=28)
def guardCommandsHandler(c, m):
    k = r.get(f"{Dev_Zaid}:botkey")
    channel = (
        r.get(f"{Dev_Zaid}:BotChannel") if r.get(f"{Dev_Zaid}:BotChannel") else "YQYQY6"
    )
    Thread(target=guardCommands, args=(c, m, k, channel)).start()


# ====================== نظام رفع المشرف الجديد (من ملف kk.py) ======================
def resolve_user(c, target):
    if isinstance(target, int):
        return target
    if isinstance(target, str):
        try:
            if target.isdigit():
                return int(target)
            else:
                user = c.get_users(target)
                return user.id
        except:
            return None
    return None

def parse_promote_command(text):
    target = None
    title = None
    body = text
    if body.startswith("رفع مشرف"):
        body = body[len("رفع مشرف"):].strip()
    username_match = re.match(r"@(\w+)", body)
    id_match = re.match(r"(\d{5,})", body)
    rest = ""
    if username_match:
        target = username_match.group(1)
        rest = body[username_match.end():].strip()
    elif id_match:
        target = int(id_match.group(1))
        rest = body[id_match.end():].strip()
    if rest.startswith("لقب"):
        rest = rest[len("لقب"):].strip()
    title = rest if rest else None
    return target, title

def parse_demote_command(text):
    body = text
    if body.startswith("تنزيل مشرف"):
        body = body[len("تنزيل مشرف"):].strip()
    username_match = re.match(r"@(\w+)", body)
    id_match = re.match(r"(\d{5,})", body)
    if username_match:
        return username_match.group(1)
    if id_match:
        return int(id_match.group(1))
    return None

def get_permission_rows(target_id, chat_id, perms, is_channel=False):
    if is_channel:
        perm_list = [
            ("can_manage_chat", "إدارة القناة"),
            ("can_post_messages", "نشر الرسائل"),
            ("can_edit_messages", "تعديل رسائل الآخرين"),
            ("can_delete_messages", "حذف الرسائل"),
            ("can_post_stories", "نشر القصص"),
            ("can_edit_stories", "تعديل القصص"),
            ("can_delete_stories", "حذف القصص"),
            ("can_manage_video_chats", "إدارة البثوث المباشرة"),
            ("can_restrict_members", "حظر المستخدمين"),
            ("can_promote_members", "رفع مشرفين"),
            ("can_change_info", "تعديل القناة"),
            ("can_invite_users", "دعوة مستخدمين"),
            ("is_anonymous", "مشرف مجهول"),
        ]
    else:
        perm_list = [
            ("can_manage_chat", "إدارة المجموعة"),
            ("can_delete_messages", "حذف الرسائل"),
            ("can_manage_video_chats", "إدارة المكالمات"),
            ("can_restrict_members", "تقييد الأعضاء"),
            ("can_promote_members", "رفع مشرفين"),
            ("can_change_info", "تعديل المجموعة"),
            ("can_invite_users", "دعوة مستخدمين"),
            ("can_pin_messages", "تثبيت الرسائل"),
            ("can_manage_topics", "إدارة المواضيع"),
            ("is_anonymous", "مشرف مجهول"),
        ]
    rows = []
    for key, label in perm_list:
        status = perms.get(key, False)
        text = f"{'✅' if status else '❌'} {label}"
        callback = f"promote:perm:{key}:{target_id}:{chat_id}"
        rows.append([{"text": text, "callback_data": callback, "style": "success" if status else "danger"}])
    rows.append([{"text": "تأكيد الصلاحيات", "callback_data": f"promote:confirm:{target_id}:{chat_id}", "style": "success"}])
    rows.append([{"text": "إلغاء", "callback_data": f"promote:cancel:{target_id}:{chat_id}", "style": "danger"}])
    return rows


def _build_chat_privileges(perms):
    """بتبني ChatPrivileges من كل الصلاحيات المتاحة، وبتتجاهل تلقائيًا أي
    صلاحية مش مدعومة في نسخة Pyrogram المثبتة عشان الأمر ميكرشش."""
    import inspect
    wanted = {
        "can_manage_chat": perms.get("can_manage_chat", False),
        "can_delete_messages": perms.get("can_delete_messages", False),
        "can_manage_video_chats": perms.get("can_manage_video_chats", False),
        "can_restrict_members": perms.get("can_restrict_members", False),
        "can_promote_members": perms.get("can_promote_members", False),
        "can_change_info": perms.get("can_change_info", False),
        "can_invite_users": perms.get("can_invite_users", False),
        "can_pin_messages": perms.get("can_pin_messages", False),
        "can_manage_topics": perms.get("can_manage_topics", False),
        "can_post_messages": perms.get("can_post_messages", False),
        "can_edit_messages": perms.get("can_edit_messages", False),
        "can_post_stories": perms.get("can_post_stories", False),
        "can_edit_stories": perms.get("can_edit_stories", False),
        "can_delete_stories": perms.get("can_delete_stories", False),
        "is_anonymous": perms.get("is_anonymous", False),
    }
    try:
        supported = set(inspect.signature(ChatPrivileges.__init__).parameters)
        wanted = {k: v for k, v in wanted.items() if k in supported}
    except Exception:
        pass
    return ChatPrivileges(**wanted)
# ============================================================


def guardCommands(c, m, k, channel):
    if not r.get(f"{m.chat.id}:enable:{Dev_Zaid}"):
        return False
    if m.from_user is None:
        text = m.text
        if text and (text == "رفع مشرف" or text.startswith("رفع مشرف ")):
            # مفيش يوزر معروف هنا لسببين: إما إنها رسالة اتبعتت في فيد قناة
            # (تليجرام مايسمحش غير للمشرفين يبعتوا هناك)، أو إن اللي بعتها
            # مشرف مجهول في جروب (خاصية "البقاء متخفيًا" متاحة للمشرفين بس).
            # في الحالتين بنثق إنه مشرف بدل ما نطلب هوية تليجرام مش هيديها.
            # هوية اللي هيدوس على الأزرار بعد كده هتتفحص عادي وقت الضغط.
            target, title = parse_promote_command(text)
            if not target:
                return m.reply(" الرجاء إرسال ايدي أو يوزر العضو الذي تريد رفعه.")
            resolved = resolve_user(c, target)
            if not resolved:
                return m.reply(" لم أتمكن من العثور على العضو.")
            target = resolved
            bot_member = m.chat.get_member(c.me.id)
            if not bot_member.privileges or not bot_member.privileges.can_promote_members:
                return m.reply(" البوت ليس لديه صلاحية رفع مشرفين.")
            try:
                target_member = m.chat.get_member(target)
                if target_member.status == ChatMemberStatus.OWNER:
                    return m.reply("👑 هذا المالك لا يمكن رفعه كمشرف.")
                if target_member.status == ChatMemberStatus.ADMINISTRATOR:
                    return m.reply(" هذا الشخص مشرف بالفعل.")
            except:
                pass
            if target == c.me.id:
                return m.reply(" البوت لا يمكنه رفع نفسه.")
            r.set(f"anonpromote:{m.chat.id}:title:{target}", title if title else "")
            return send_colored_message(
                c,
                m.chat.id,
                f"{k} تم تحديد العضو، الآن اضغط على الزر أدناه لتعديل صلاحيات المشرف.",
                rows=[[{"text": "تعديل الصلاحيات", "callback_data": f"promote:button:{target}:{m.chat.id}", "style": "primary"}]],
            )
        if text and (text == "تنزيل مشرف" or text.startswith("تنزيل مشرف ")):
            if m.reply_to_message and m.reply_to_message.from_user:
                target = m.reply_to_message.from_user.id
            else:
                target = parse_demote_command(text)
            if not target:
                return m.reply(" الرجاء إرسال ايدي أو يوزر العضو الذي تريد تنزيله.")
            resolved = resolve_user(c, target)
            if not resolved:
                return m.reply(" لم أتمكن من العثور على العضو.")
            target = resolved
            return send_colored_message(
                c,
                m.chat.id,
                f"{k} هتنزل الإشراف عن العضو ده، متأكد؟",
                rows=[[
                    {"text": "تأكيد التنزيل", "callback_data": f"demote:confirm:{target}:{m.chat.id}", "style": "danger"},
                    {"text": "إلغاء", "callback_data": f"demote:cancel:{target}:{m.chat.id}", "style": "success"},
                ]],
            )
        return False
    if r.get(f"{m.chat.id}:mute:{Dev_Zaid}") and not admin_pls(
        m.from_user.id, m.chat.id
    ):
        return False
    if r.get(f"{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}"):
        return False
    if r.get(f"{m.from_user.id}:mute:{Dev_Zaid}"):
        return False
    if r.get(f"{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}"):
        return False
    if r.get(f"{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}"):
        return False
    if r.get(f"{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}") or r.get(
        f"{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}"
    ):
        return False
    text = m.text
    name = r.get(f"{Dev_Zaid}:BotName") if r.get(f"{Dev_Zaid}:BotName") else "ليو"
    if text.startswith(f"{name} "):
        text = text.replace(f"{name} ", "")
    if r.get(f"{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}"):
        text = r.get(f"{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}")
    if r.get(f"Custom:{Dev_Zaid}&text={text}"):
        text = r.get(f"Custom:{Dev_Zaid}&text={text}")
    if isLockCommand(m.from_user.id, m.chat.id, text):
        return

    # ====================== PROMOTION FLOW ======================
    promote_state = r.get(f"{m.from_user.id}:promote:step:{m.chat.id}")
    if promote_state:
        if promote_state == "waiting_target":
            target, title = parse_promote_command(text)
            if not target:
                return m.reply("❌ لم يتم التعرف على العضو، الرجاء إرسال معرف أو يوزر صحيح.")
            resolved = resolve_user(c, target)
            if not resolved:
                return m.reply("❌ لم أتمكن من العثور على العضو.")
            target = resolved
            r.set(f"{m.from_user.id}:promote:target:{m.chat.id}", str(target))
            r.set(f"{m.from_user.id}:promote:step:{m.chat.id}", "waiting_title")
            return m.reply("✅ تم التعرف على العضو، الآن أرسل اللقب الذي تريده (أو اكتب 'تخطي' لتركه فارغاً).")
        elif promote_state == "waiting_title":
            title = text.strip()
            if title.lower() == "تخطي":
                title = None
            r.set(f"{m.from_user.id}:promote:title:{m.chat.id}", title if title else "")
            r.set(f"{m.from_user.id}:promote:step:{m.chat.id}", "done")
            target_id_str = r.get(f"{m.from_user.id}:promote:target:{m.chat.id}")
            try:
                target_id = int(target_id_str)
            except:
                return m.reply("❌ حدث خطأ في معرف العضو، حاول مرة أخرى.")
            return send_colored_message(
                c,
                m.chat.id,
                f"{k} تم حفظ اللقب، الآن اضغط على الزر أدناه لتعديل صلاحيات المشرف.",
                rows=[[{"text": "تعديل الصلاحيات", "callback_data": f"promote:button:{target_id}:{m.chat.id}", "style": "primary"}]],
            )
    Open = """
{} من 「 {} 」
{} ابشر فتحت {}
☆
"""
    Openn = """
{} من 「 {} 」
{} {} مفتوح من قبل
☆
"""
    Openn2 = """
{} من 「 {} 」
{} {} مفتوحه من قبل
☆
"""

    lock = """
{} من 「 {} 」
{} ابشر قفلت {}
☆
"""

    lockn = """
{} من 「 {} 」
{} {} مقفل من قبل
☆
"""
    locknn = """
{} من 「 {} 」
{} {} مقفله من قبل
☆
"""

    if text == "الاعدادات" or text == "الحماية" or text == "الحمايه":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            return send_colored_message(
                c,
                m.chat.id,
                protection_header_text(k, 0),
                rows=build_protection_rows(m.chat.id, 0, m.from_user.id),
            )

    if text == "الساعه" or text == "الساعة" or text == "الوقت":
        TIME_ZONE = "Asia/Riyadh"
        ZONE = pytz.timezone(TIME_ZONE)
        TIME = datetime.now(ZONE)
        clock = TIME.strftime("%I:%M %p")
        return m.reply(f"{k} الساعة ( {clock} )")

    if text == "القوانين":
        if r.get(f"{m.chat.id}:CustomRules:{Dev_Zaid}"):
            rules = r.get(f"{m.chat.id}:CustomRules:{Dev_Zaid}")
        else:
            rules = f"""{k} ممنوع نشر الروابط
{k} ممنوع التكلم او نشر صور اباحيه
{k} ممنوع اعاده توجيه
{k} ممنوع العنصرية بكل انواعها
{k} الرجاء احترام المدراء والادمنيه"""
        return m.reply(rules, disable_web_page_preview=True)

    if text == "التاريخ":
        b = Hijri.today().isoformat()
        a = b.split("-")
        year = int(a[0])
        month = int(a[1])
        day = int(a[2])
        hijri = Hijri(year, month, day)
        hijri_date = str(b).replace("-", "/")
        hijri_month = hijri.month_name("ar")

        b = Gregorian.today().isoformat()
        a = b.split("-")
        year = int(a[0])
        month = int(a[1])
        day = int(a[2])
        geo = Gregorian(year, month, day)
        geo_date = str(b).replace("-", "/")
        geo_month = geo.month_name("en")[:3]

        return m.reply(f"""
التاريخ:
{k} هجري ↢ {hijri_date} {hijri_month}
{k} ميلادي ↢ {geo_date} {geo_month}
""")

    if text == "المالك":
        owner = None
        for mm in m.chat.get_members(filter=ChatMembersFilter.ADMINISTRATORS):
            if mm.status == ChatMemberStatus.OWNER:
                owner = mm.user
                break
        if owner:
            if owner.is_deleted:
                m.reply("حساب المالك محذوف")
            else:
                owner_username = owner.username if owner.username else owner.id
                caption = f"• Owner ☆ ↦ {owner.mention}\n\n"
                caption += f"• Owner User ↦ @{owner_username}"
                reply_markup = InlineKeyboardMarkup(
                    [[InlineKeyboardButton(owner.first_name, url=f"tg://user?id={owner.id}")]]
                )
                if owner.photo:
                    file_id = owner.photo.big_file_id
                    photo_path = c.download_media(file_id)
                    m.reply_photo(photo_path, caption=caption, reply_markup=reply_markup)
                    os.remove(photo_path)
                else:
                    m.reply(caption, reply_markup=reply_markup)

    # مطور السورس - صاحب أعلى رتبة في البوت. الآيدي بيتقرأ مباشرة من جوه
    # كود ملف Ranks.py وقت تنفيذ الأمر (مش متخزن في متغير ثابت هنا)، فلو
    # غيّرت الرقم يدويًا في Ranks.py هيتعرف عليه الأمر ده أوتوماتيك من غير
    # ما تحتاج تعدل أي حاجة في الملف ده خالص.
    def get_source_dev_id():
        try:
            src = inspect.getsource(admin_pls)
            match = re.search(r"id\s*==\s*(\d+)", src)
            if match:
                return int(match.group(1))
        except Exception:
            pass
        return None

    if text == "مطور السورس":
        source_dev_id = get_source_dev_id()
        if not source_dev_id:
            return m.reply("تعذر تحديد آيدي مطور السورس من ملف Ranks.py")
        try:
            dev = c.get_users(source_dev_id)
        except Exception:
            return m.reply("تعذر جلب حساب مطور السورس")
        if dev.is_deleted:
            m.reply("حساب مطور السورس محذوف")
        else:
            dev_username = dev.username if dev.username else dev.id
            caption = f"• Source Dev ☆ ↦ {dev.mention}\n\n"
            caption += f"• Source Dev User ↦ @{dev_username}"
            reply_markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton(dev.first_name, url=f"tg://user?id={dev.id}")]]
            )
            if dev.photo:
                file_id = dev.photo.big_file_id
                photo_path = c.download_media(file_id)
                m.reply_photo(photo_path, caption=caption, reply_markup=reply_markup)
                os.remove(photo_path)
            else:
                m.reply(caption, reply_markup=reply_markup)

    # السورس - بيجيب صورة واسم قناة السورس اللي اتحطت عن طريق زر "وضع
    # قناة السورس"، وبيحطهم في كابشن مع زرار اونلاين بيوصل للقناة نفسها
    if text == "السورس" or text == "سورس":
        channel_username = r.get(f"{Dev_Zaid}:BotChannel")
        if not channel_username:
            return m.reply(f"{k} قناة السورس مو معينة")
        try:
            ch = c.get_chat(channel_username)
        except Exception:
            return m.reply(f"{k} تعذر جلب قناة السورس")
        channel_name = ch.title or ch.first_name or channel_username
        caption = f"{k} السورس ☆ ↦ {channel_name}"
        reply_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "𝓟𝓱𝓸𝓽𝓸",
                        url=f"https://t.me/{channel_username}",
                    )
                ]
            ]
        )
        if ch.photo:
            file_id = ch.photo.big_file_id
            photo_path = c.download_media(file_id)
            m.reply_photo(photo_path, caption=caption, reply_markup=reply_markup)
            os.remove(photo_path)
        else:
            m.reply(caption, reply_markup=reply_markup)

    if text == "اطردني":
        if r.get(f"{m.chat.id}:enableKickMe:{Dev_Zaid}"):
            get = m.chat.get_member(m.from_user.id)
            if get.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                return m.reply(f"{k} ممنوع طرد الحلوين")
            if admin_pls(m.from_user.id, m.chat.id, c):
                return m.reply(f"{k} ممنوع طرد الحلوين")
            else:
                m.reply(
                    f"طردتك يانفسية , وارسلت لك الرابط خاص تقدر ترجع متى مابغيت يامعقد"
                )
                m.chat.ban_member(m.from_user.id)
                time.sleep(0.5)
                c.unban_chat_member(m.chat.id, m.from_user.id)
                link = c.get_chat(m.chat.id).invite_link
                try:
                    c.send_message(
                        m.from_user.id,
                        f"{k} حبيبي النفسية رابط القروب الي طردتك منه: {link}",
                    )
                except:
                    pass
                return False

    if text == "الرابط":
        if not r.get(f"{m.chat.id}:disableLINK:{Dev_Zaid}"):
            link = c.get_chat(m.chat.id).invite_link
            return m.reply(f"[{m.chat.title}]({link})", disable_web_page_preview=True)

    if text == "انشاء رابط":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        link = c.get_chat(m.chat.id).invite_link
        c.revoke_chat_invite_link(m.chat.id, link)
        return m.reply(f'{k} ابشر سويت رابط جديد ارسل "الرابط"')

    if text.startswith("@all"):
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if r.get(f"{m.chat.id}:disableALL:{Dev_Zaid}"):
            return m.reply("المنشن معطل")
        if r.get(f"{m.chat.id}:inMention:{Dev_Zaid}"):
            return False
        if r.get(f"{m.chat.id}:inMentionWAIT:{Dev_Zaid}"):
            get = r.ttl(f"{m.chat.id}:inMentionWAIT:{Dev_Zaid}")
            tm = time.strftime("%M:%S", time.gmtime(get))
            return m.reply(f"{k} سويت منشن من شوي تعال بعد {tm}")
        else:
            if len(text.split()) > 1:
                reason = text.split(None, 1)[1]
            else:
                reason = ""
            users_list = []
            r.set(f"{m.chat.id}:inMention:{Dev_Zaid}", 1)
            m.reply(f"{k} بسوي منشن يحلو ، اذا تبي توقفه ارسل `/Cancel` او `ايقاف`")
            for mm in m.chat.get_members(limit=150):
                if mm.user and not mm.user.is_deleted and not mm.user.is_bot:
                    users_list.append(mm.user.mention)
            final_list = [users_list[x : x + 5] for x in range(0, len(users_list), 5)]
            ftext = f"{reason}\n\n"
            for a in final_list:
                for i in a:
                    if not r.get(f"{m.chat.id}:inMention:{Dev_Zaid}"):
                        return False
                    ftext += f"{i} , "
                c.send_message(m.chat.id, ftext)
                ftext = f"{reason}\n\n"
            r.delete(f"{m.chat.id}:inMention:{Dev_Zaid}")
            r.set(f"{m.chat.id}:inMentionWAIT:{Dev_Zaid}", 1, ex=1200)

    if text.lower() == "/cancel" or text == "ايقاف التاك":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:inMention:{Dev_Zaid}"):
                return m.reply(f"{k} مو قاعده اسوي منشن ركز")
            else:
                r.delete(f"{m.chat.id}:inMention:{Dev_Zaid}")
                return m.reply("ابشر وقفت المنشن")

    if text == "منشن":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        return m.reply("استخدم امر\n@all مع الكلام")

    if text == "تعطيل المنشن":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:disableALL:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} المشن معطل من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:disableALL:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت المنشن\n☆"
                )

    if text == "تفعيل المنشن":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:disableALL:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} المنشن مفعل من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:disableALL:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت المنشن\n☆"
                )

    if text == "تعطيل الترحيب":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:disableWelcome:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} الترحيب معطل من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:disableWelcome:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت الترحيب\n☆"
                )

    if text == "تفعيل الترحيب":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:disableWelcome:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} الترحيب مفعل من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:disableWelcome:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت الترحيب\n☆"
                )

    if text == "تعطيل الترحيب بالصورة" or text == "تعطيل الترحيب بالصوره":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:disableWelcomep:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} الترحيب بالصورة من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:disableWelcomep:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت الترحيب بالصورة\n☆"
                )

    if text == "تفعيل الترحيب بالصورة" or text == "تفعيل الترحيب بالصوره":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:disableWelcomep:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} الترحيب بالصورة مفعل من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:disableWelcomep:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت الترحيب بالصورة\n☆"
                )

    if text == "تعطيل الرابط":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:disableLINK:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} الرابط معطل من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:disableLINK:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت الرابط\n☆"
                )

    if text == "تفعيل الرابط":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:disableLINK:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} الرابط مفعل من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:disableLINK:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت الرابط\n☆"
                )

    if text == "تعطيل البايو":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:disableBio:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} البايو معطل من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:disableBio:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت البايو\n☆"
                )

    if text == "تفعيل البايو":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:disableBio:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} البايو مفعل من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:disableBio:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت البايو\n☆"
                )

    if text == "تعطيل اطردني":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:enableKickMe:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} اطردني معطل من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:enableKickMe:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت اطردني\n☆"
                )

    if text == "تفعيل اطردني":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:enableKickMe:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} اطردني مفعل من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:enableKickMe:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت اطردني\n☆"
                )

    if text == "تعطيل التحقق":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:enableVerify:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} التحقق معطل من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:enableVerify:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت التحقق\n☆"
                )

    if text == "تفعيل التحقق":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:enableVerify:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} التحقق مفعل من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:enableVerify:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت التحقق\n☆"
                )

    if text == "تعطيل انطقي" or text == "تعطيل انطق":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:disableSay:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} انطقي معطل من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:disableSay:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت انطقي\n☆"
                )

    if text == "تفعيل انطقي" or text == "تفعيل انطق":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:disableSay:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} انطقي مفعل من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:disableSay:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت انطقي\n☆"
                )

    if text.startswith("انطق "):
        if not r.get(f"{m.chat.id}:disableSay:{Dev_Zaid}"):
            txt = text.split(None, 1)[1]
            if len(txt) > 500:
                return m.reply("توكل مايمدي انطق اكثر من ٥٠٠ حرف بتعب بعدين")
            """
         det = translator.detect(txt).lang.lower()
         if det == 'fa' or det == 'ar':
           lang = 'ar'
         else:
           lang = det
         """
            id = random.randint(999, 10000)
            """
         o = gtts.gTTS(text=txt, lang="ar", slow=False)
         o.save(f'zaid{id}.mp3')
         """
            with open(f"zaid{id}.mp3", "wb") as f:
                try:
                    c.send_chat_action(m.chat.id, ChatAction.RECORD_AUDIO)
                except:
                    pass
                f.write(
                    requests.get(
                        f"https://eduardo-tate.com/AI/voice.php?text={txt}&model=3"
                    ).content
                )
            """
         audio = MP3(f'zaid{id}.mp3')
         duration=int(audio.info.length)
         os.rename(f'zaid{id}.mp3',f'zaid{id}.ogg')
         TelegramBot.send_voice(
         m.chat.id,
         voice,
         caption=f'الكلمة: {txt}',
         duration=duration
         )
         """
            try:
                c.send_chat_action(m.chat.id, ChatAction.RECORD_AUDIO)
            except:
                pass
            os.system(
                f"ffmpeg -i zaid{id}.mp3 -ac 1 -strict -2 -codec:a libopus -b:a 128k -vbr off -ar 24000 zaid{id}.ogg"
            )
            try:
                c.send_chat_action(m.chat.id, ChatAction.UPLOAD_AUDIO)
            except:
                pass
            m.reply_voice(f"zaid{id}.ogg", caption=f"الكلمة: {txt}")
            """
         voice = open(f'zaid{id}.ogg','rb')
         url = f"https://api.telegram.org/bot{c.bot_token}/sendVoice"
         response=requests.post(url, data={'chat_id': m.chat.id,'caption':f'الكلمة: {txt}','reply_to_message_id':m.id}, files={'voice': voice})
         os.remove(f'zaid{id}.ogg')
         """
            os.remove(f"zaid{id}.ogg")
            os.remove(f"zaid{id}.mp3")
            return True

    if text.startswith("انطقي "):
        if not r.get(f"{m.chat.id}:disableSay:{Dev_Zaid}"):
            txt = text.split(None, 1)[1]
            if len(txt) > 500:
                return m.reply("توكل مايمدي انطق اكثر من ٥٠٠ حرف بتعب بعدين")
            """
         det = translator.detect(txt).lang.lower()
         if det == 'fa' or det == 'ar':
           lang = 'ar'
         else:
           lang = det
         """
            id = random.randint(999, 10000)
            """
         o = gtts.gTTS(text=txt, lang="ar", slow=False)
         o.save(f'zaid{id}.mp3')
         """
            with open(f"zaid{id}.mp3", "wb") as f:
                try:
                    c.send_chat_action(m.chat.id, ChatAction.RECORD_AUDIO)
                except:
                    pass
                f.write(
                    requests.get(
                        f"https://eduardo-tate.com/AI/voice.php?text={txt}"
                    ).content
                )
            """
         audio = MP3(f'zaid{id}.mp3')
         duration=int(audio.info.length)
         os.rename(f'zaid{id}.mp3',f'zaid{id}.ogg')
         TelegramBot.send_voice(
         m.chat.id,
         voice,
         caption=f'الكلمة: {txt}',
         duration=duration
         )
         """
            try:
                c.send_chat_action(m.chat.id, ChatAction.RECORD_AUDIO)
            except:
                pass
            os.system(
                f"ffmpeg -i zaid{id}.mp3 -ac 1 -strict -2 -codec:a libopus -b:a 128k -vbr off -ar 24000 zaid{id}.ogg"
            )
            try:
                c.send_chat_action(m.chat.id, ChatAction.UPLOAD_AUDIO)
            except:
                pass
            m.reply_voice(f"zaid{id}.ogg", caption=f"الكلمة: {txt}")
            """
         voice = open(f'zaid{id}.ogg','rb')
         url = f"https://api.telegram.org/bot{c.bot_token}/sendVoice"
         response=requests.post(url, data={'chat_id': m.chat.id,'caption':f'الكلمة: {txt}','reply_to_message_id':m.id}, files={'voice': voice})
         os.remove(f'zaid{id}.ogg')
         """
            os.remove(f"zaid{id}.ogg")
            os.remove(f"zaid{id}.mp3")
            return True

    if (
        (text == "وش يقول" or text == "وش تقول؟")
        and m.reply_to_message
        and m.reply_to_message.voice
    ):
        if m.reply_to_message.voice.file_size > 20971520:
            return m.reply("حجمه اكثر من ٢٠ ميجابايت، توكل")
        id = random.randint(99, 1000)
        voice = m.reply_to_message.download(f"./zaid{id}.wav")
        s = sr.Recognizer()
        sound = AudioSegment.from_ogg(voice)
        wav_file = sound.export(voice, format="wav")
        with sr.AudioFile(wav_file) as src:
            audio_source = s.record(src)
        try:
            text = s.recognize_google(audio_source, language="ar-SA")
        except Exception as e:
            print(e)
            os.remove(f"zaid{id}.wav")
            return m.reply("عجزت افهم وش يقول ")
        os.remove(f"zaid{id}.wav")
        return m.reply(f"يقول : {text}")

    if (
        (text == "zaid" or text == "زوز")
        and m.reply_to_message
        and m.reply_to_message.voice
        and m.from_user.id == 7532687479
    ):
        if m.reply_to_message.voice.file_size > 20971520:
            return m.reply("حجمه اكثر من ٢٠ ميجابايت، توكل")
        id = random.randint(99, 1000)
        voice = m.reply_to_message.download(f"./zaid{id}.wav")
        s = sr.Recognizer()
        sound = AudioSegment.from_ogg(voice)
        wav_file = sound.export(voice, format="wav")
        with sr.AudioFile(wav_file) as src:
            audio_source = s.record(src)
        try:
            text = s.recognize_google(audio_source, language="en-US")
        except Exception as e:
            print(e)
            os.remove(f"zaid{id}.wav")
            return m.reply("عجزت افهم وش يقول ")
        os.remove(f"zaid{id}.wav")
        return m.reply(f"يقول : {text}")

    if text.startswith("منع "):
        if mod_pls(m.from_user.id, m.chat.id):
            noice = text.split(None, 1)[1]
            if r.sismember(f"{m.chat.id}:NotAllowedListText:{Dev_Zaid}", noice):
                return m.reply(
                    f"{k} الكلمة ( {noice} ) موجودة بقائمة المنع",
                    disable_web_page_preview=True,
                )
            else:
                r.sadd(f"{m.chat.id}:NotAllowedListText:{Dev_Zaid}", noice)
                return m.reply(
                    f"{k} الكلمة ( {noice} ) اضفتها الى قائمة المنع",
                    disable_web_page_preview=True,
                )

    if text.startswith("الغاء منع ") and len(text.split()) > 2:
        if mod_pls(m.from_user.id, m.chat.id):
            noice = text.split(None, 2)[2]
            if not r.sismember(f"{m.chat.id}:NotAllowedListText:{Dev_Zaid}", noice):
                return m.reply(
                    f"{k} الكلمة ( {noice} ) مو مضافة بقائمة المنع",
                    disable_web_page_preview=True,
                )
            else:
                r.srem(f"{m.chat.id}:NotAllowedListText:{Dev_Zaid}", noice)
                return m.reply(
                    f"{k} ابشر مسحت ( {noice} ) من قائمة المنع",
                    disable_web_page_preview=True,
                )

    if text == "منع" and m.reply_to_message and m.reply_to_message.media:
        if mod_pls(m.from_user.id, m.chat.id):
            rep = m.reply_to_message
            if rep.sticker:
                file_id = rep.sticker.file_id
                type = "sticker"
            if rep.animation:
                file_id = rep.animation.file_id
                type = "animation"
            if rep.photo:
                file_id = rep.photo.file_id
                type = "photo"
            if rep.video:
                file_id = rep.photo.file_id
                type = "video"
            if rep.voice:
                file_id = rep.voice.file_id
                type = "voice"
            if rep.audio:
                file_id = rep.audio.file_id
                type = "audio"
            if rep.document:
                file_id = rep.document.file_id
                type = "document"

            id = file_id[-6:]
            if r.get(f"{id}:NotAllow:{m.chat.id}{Dev_Zaid}"):
                return m.reply(f"{k} موجودة بقائمة المنع")
            else:
                r.set(f"{id}:NotAllow:{m.chat.id}{Dev_Zaid}", 1)
                r.sadd(
                    f"{m.chat.id}:NotAllowedList:{Dev_Zaid}",
                    f"file={id}&by={m.from_user.id}&type={type}&file_id={file_id}",
                )
                return m.reply(f"{k} واضفناها لقائمة المنع")

    if text == "الغاء منع" and m.reply_to_message and m.reply_to_message.media:
        if mod_pls(m.from_user.id, m.chat.id):
            rep = m.reply_to_message
            if rep.sticker:
                file_id = rep.sticker.file_id
                type = "sticker"
            if rep.animation:
                file_id = rep.animation.file_id
                type = "animation"
            if rep.photo:
                file_id = rep.photo.file_id
                type = "photo"
            if rep.video:
                file_id = rep.photo.file_id
                type = "video"
            if rep.voice:
                file_id = rep.voice.file_id
                type = "voice"
            if rep.audio:
                file_id = rep.audio.file_id
                type = "audio"
            if rep.document:
                file_id = rep.document.file_id
                type = "document"

            id = file_id[-6:]
            if not r.get(f"{id}:NotAllow:{m.chat.id}{Dev_Zaid}"):
                return m.reply(f"{k} مو موجودة بقائمة المنع")
            else:
                r.delete(f"{id}:NotAllow:{m.chat.id}{Dev_Zaid}")
                r.srem(
                    f"{m.chat.id}:NotAllowedList:{Dev_Zaid}",
                    f"file={id}&by={m.from_user.id}&type={type}&file_id={file_id}",
                )
                return m.reply(f"{k} ابشر شلتها من قائمه المنع")

    if text == "منع" and m.reply_to_message and not m.reply_to_message.media:
        if mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} المنع بالرد فقط للوسائط")

    if text == "قائمه المنع" or text == "قائمة المنع":
        text1 = "الكلمات الممنوعة:\n"
        text2 = "الوسائط الممنوعة:\n"
        count = 1
        count2 = 1
        if mod_pls(m.from_user.id, m.chat.id):
            if not r.smembers(
                f"{m.chat.id}:NotAllowedListText:{Dev_Zaid}"
            ) and not r.smembers(f"{m.chat.id}:NotAllowedList:{Dev_Zaid}"):
                return m.reply(f"{k} مافي شي ممنوع")
            else:
                if not r.smembers(f"{m.chat.id}:NotAllowedListText:{Dev_Zaid}"):
                    text1 += "لايوجد"
                else:
                    for a in r.smembers(f"{m.chat.id}:NotAllowedListText:{Dev_Zaid}"):
                        text1 += f"{count} - {a}\n"
                        count += 1
                if not r.smembers(f"{m.chat.id}:NotAllowedList:{Dev_Zaid}"):
                    text2 += "لايوجد"
                else:
                    for a in r.smembers(f"{m.chat.id}:NotAllowedList:{Dev_Zaid}"):
                        g = a
                        id = g.split("file=")[1].split("&")[0]
                        by = g.split("by=")[1].split("&")[0]
                        type = g.split("type=")[1].split("&")[0]
                        text2 += (
                            f"{count2} - (`{id}`) ࿓ ( [{type}](tg://user?id={by}) )\n"
                        )
                return m.reply(f"{text1}\n{text2}", disable_web_page_preview=True)

    if text == "مسح قائمه المنع" or text == "مسح قائمة المنع":
        if mod_pls(m.from_user.id, m.chat.id):
            if not r.smembers(
                f"{m.chat.id}:NotAllowedListText:{Dev_Zaid}"
            ) and not r.smembers(f"{m.chat.id}:NotAllowedList:{Dev_Zaid}"):
                return m.reply(f"{k} مافي شي ممنوع")
            else:
                if r.smembers(f"{m.chat.id}:NotAllowedListText:{Dev_Zaid}"):
                    r.delete(f"{m.chat.id}:NotAllowedListText:{Dev_Zaid}")
                if r.smembers(f"{m.chat.id}:NotAllowedList:{Dev_Zaid}"):
                    for a in r.smembers(f"{m.chat.id}:NotAllowedList:{Dev_Zaid}"):
                        file_id = a.split("file=")[1].split("&by=")[0]
                        r.delete(f"{file_id}:NotAllow:{m.chat.id}{Dev_Zaid}")
                r.delete(f"{m.chat.id}:NotAllowedList:{Dev_Zaid}")
                return m.reply(f"{k} ابشر مسحت قائمة المنع")

    if text == "قفل الكل":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if (
                r.get(f"{m.chat.id}:mute:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockEdit:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockEditM:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockVoice:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockVideo:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockNot:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockPhoto:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockPersian:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockStickers:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockFiles:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockAnimations:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockUrls:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockHashtags:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockBots:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockTags:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockMessages:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockSpam:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockForward:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockSHTM:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockaddContacts:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockAudios:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockChannels:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockJoin:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockInline:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockNSFW:{Dev_Zaid}")
            ):
                return m.reply(
                    f"{k} من 「 {m.from_user.mention} 」 \n{k} كل شي مقفل يالطيب!\n☆"
                )
            else:
                m.reply(f"{k} من 「 {m.from_user.mention} 」 \n{k} ابشر قفلت كل شي\n☆")
                r.set(f"{m.chat.id}:mute:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockJoin:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockChannels:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockEdit:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockEditM:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockVoice:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockVideo:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockNot:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockPhoto:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockStickers:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockAnimations:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockFiles:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockPersian:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockUrls:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockHashtags:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockMessages:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockTags:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockBots:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockSpam:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockInline:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockForward:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockAudios:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockaddContacts:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockSHTM:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockNSFW:{Dev_Zaid}", 1)
                return False

    if text == "فتح الكل":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if (
                not r.get(f"{m.chat.id}:mute:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockEdit:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockEditM:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockVoice:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockVideo:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockNot:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockPhoto:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockPersian:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockStickers:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockFiles:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockAnimations:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockUrls:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockHashtags:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockBots:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockTags:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockMessages:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockSpam:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockForward:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockSHTM:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockaddContacts:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockAudios:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockChannels:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockJoin:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockInline:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockNSFW:{Dev_Zaid}")
            ):
                return m.reply(
                    f"{k} من 「 {m.from_user.mention} 」 \n{k} كل شي مفتوح يالطيب!\n☆"
                )
            else:
                m.reply(f"{k} من 「 {m.from_user.mention} 」 \n{k} ابشر فتحت كل شي\n☆")
                r.delete(f"{m.chat.id}:mute:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockJoin:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockChannels:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockEdit:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockEditM:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockVoice:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockVideo:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockNot:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockPhoto:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockStickers:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockAnimations:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockFiles:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockPersian:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockUrls:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockHashtags:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockMessages:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockTags:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockBots:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockSpam:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockInline:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockForward:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockAudios:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockaddContacts:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockSHTM:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockKFR:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockNSFW:{Dev_Zaid}")
                return False

    if text == "تفعيل الحماية" or text == "تفعيل الحمايه":
        if not owner_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المالك وفوق ) بس")
        else:
            if (
                r.get(f"{m.chat.id}:lockEditM:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockVoice:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockVideo:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockPhoto:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockPersian:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockStickers:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockFiles:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockAnimations:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockUrls:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockTags:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockMessages:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockSpam:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockForward:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockSHTM:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockAudios:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockChannels:{Dev_Zaid}")
                and r.get(f"{m.chat.id}:lockNSFW:{Dev_Zaid}")
            ):
                return m.reply(
                    f"{k} من 「 {m.from_user.mention} 」 \n{k} الحماية مفعله من قبل\n☆"
                )
            else:
                m.reply(
                    f"{k} من 「 {m.from_user.mention} 」 \n{k} ابشر فعلت الحمايه\n☆"
                )

                r.set(f"{m.chat.id}:lockChannels:{Dev_Zaid}", 1)
                r.delete(f"{m.chat.id}:disableWarn:{Dev_Zaid}")
                r.set(f"{m.chat.id}:lockVoice:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockVideo:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockPhoto:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockStickers:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockAnimations:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockFiles:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockPersian:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockUrls:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockTags:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockSpam:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockForward:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockAudios:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockSHTM:{Dev_Zaid}", 1)
                r.set(f"{m.chat.id}:lockNSFW:{Dev_Zaid}", 1)
                return False

    if text == "تعطيل الحماية" or text == "تعطيل الحمايه":
        if not owner_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المالك وفوق ) بس")
        else:
            if (
                r.get(f"{m.chat.id}:lockEditM:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockVoice:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockVideo:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockPhoto:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockPersian:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockStickers:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockFiles:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockAnimations:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockUrls:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockTags:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockMessages:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockSpam:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockForward:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockSHTM:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockAudios:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockChannels:{Dev_Zaid}")
                and not r.get(f"{m.chat.id}:lockNSFW:{Dev_Zaid}")
            ):
                return m.reply(
                    f"{k} من 「 {m.from_user.mention} 」 \n{k} الحماية معطله من قبل\n☆"
                )
            else:
                m.reply(
                    f"{k} من 「 {m.from_user.mention} 」 \n{k} ابشر عطلت الحمايه\n☆"
                )

                r.delete(f"{m.chat.id}:lockChannels:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockVoice:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockVideo:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockPhoto:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockStickers:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockAnimations:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockFiles:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockPersian:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockUrls:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockTags:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockSpam:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockForward:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockAudios:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockSHTM:{Dev_Zaid}")
                r.delete(f"{m.chat.id}:lockNSFW:{Dev_Zaid}")
                return False

    if text == "قفل الدردشة" or text == "قفل الدردشه" or text == "قفل الشات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:mute:{Dev_Zaid}"):
                return m.reply(lockn.format(k, m.from_user.mention, k, "الشات"))
            else:
                r.set(f"{m.chat.id}:mute:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "mute", "الشات")

    if text == "فتح الدردشة" or text == "فتح الدردشه" or text == "فتح الشات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:mute:{Dev_Zaid}"):
                return m.reply(Openn.format(k, m.from_user.mention, k, "الشات"))
            else:
                r.delete(f"{m.chat.id}:mute:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "الشات"))

    if text == "قفل التعديل":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockEdit:{Dev_Zaid}"):
                return m.reply(lockn.format(k, m.from_user.mention, k, "التعديل"))
            else:
                r.set(f"{m.chat.id}:lockEdit:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockEdit", "التعديل")

    if text == "فتح التعديل":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockEdit:{Dev_Zaid}"):
                return m.reply(Openn.format(k, m.from_user.mention, k, "التعديل"))
            else:
                r.delete(f"{m.chat.id}:lockEdit:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "التعديل"))

    if text == "قفل تعديل الميديا":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockEditM:{Dev_Zaid}"):
                return m.reply(lockn.format(k, m.from_user.mention, k, "تعديل الميديا"))
            else:
                r.set(f"{m.chat.id}:lockEditM:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockEditM", "تعديل الميديا")

    if text == "فتح تعديل الميديا":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockEditM:{Dev_Zaid}"):
                return m.reply(Openn.format(k, m.from_user.mention, k, "تعديل الميديا"))
            else:
                r.delete(f"{m.chat.id}:lockEditM:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "تعديل الميديا"))

    if text == "قفل الفويسات" or text == "قفل البصمات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockVoice:{Dev_Zaid}"):
                return m.reply(lockn.format(k, m.from_user.mention, k, "الفويس"))
            else:
                r.set(f"{m.chat.id}:lockVoice:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockVoice", "الفويس")

    if text == "فتح الفويسات" or text == "فتح البصمات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockVoice:{Dev_Zaid}"):
                return m.reply(Openn.format(k, m.from_user.mention, k, "الفويس"))
            else:
                r.delete(f"{m.chat.id}:lockVoice:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "الفويس"))

    if text == "قفل الفيديو" or text == "قفل الفيديوهات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockVideo:{Dev_Zaid}"):
                return m.reply(lockn.format(k, m.from_user.mention, k, "الفيديو"))
            else:
                r.set(f"{m.chat.id}:lockVideo:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockVideo", "الفيديو")

    if text == "فتح الفيديو" or text == "فتح الفيديوهات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockVideo:{Dev_Zaid}"):
                return m.reply(Openn.format(k, m.from_user.mention, k, "الفيديو"))
            else:
                r.delete(f"{m.chat.id}:lockVideo:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "الفيديو"))

    if text == "قفل الاشعارات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockNot:{Dev_Zaid}"):
                return m.reply(locknn.format(k, m.from_user.mention, k, "الاشعارات"))
            else:
                r.set(f"{m.chat.id}:lockNot:{Dev_Zaid}", 1)
                return m.reply(lock.format(k, m.from_user.mention, k, "الاشعارات"))

    if text == "فتح الاشعارات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockNot:{Dev_Zaid}"):
                return m.reply(Openn2.format(k, m.from_user.mention, k, "الاشعارات"))
            else:
                r.delete(f"{m.chat.id}:lockNot:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "الاشعارات"))

    if text == "قفل الصور":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockPhoto:{Dev_Zaid}"):
                return m.reply(locknn.format(k, m.from_user.mention, k, "الصور"))
            else:
                r.set(f"{m.chat.id}:lockPhoto:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockPhoto", "الصور")

    if text == "فتح الصور":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockPhoto:{Dev_Zaid}"):
                return m.reply(Openn2.format(k, m.from_user.mention, k, "الصور"))
            else:
                r.delete(f"{m.chat.id}:lockPhoto:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "الصور"))

    if text == "قفل الملصقات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockStickers:{Dev_Zaid}"):
                return m.reply(locknn.format(k, m.from_user.mention, k, "الملصقات"))
            else:
                r.set(f"{m.chat.id}:lockStickers:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockStickers", "الملصقات")

    if text == "فتح الملصقات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockStickers:{Dev_Zaid}"):
                return m.reply(Openn2.format(k, m.from_user.mention, k, "الملصقات"))
            else:
                r.delete(f"{m.chat.id}:lockStickers:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "الملصقات"))

    if text == "قفل الفارسيه" or text == "قفل الفارسية":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockPersian:{Dev_Zaid}"):
                return m.reply(locknn.format(k, m.from_user.mention, k, "الفارسيه"))
            else:
                r.set(f"{m.chat.id}:lockPersian:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockPersian", "الفارسيه")

    if text == "فتح الفارسيه" or text == "فتح الفارسية":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockPersian:{Dev_Zaid}"):
                return m.reply(Openn2.format(k, m.from_user.mention, k, "الفارسيه"))
            else:
                r.delete(f"{m.chat.id}:lockPersian:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "الفارسيه"))

    if text == "قفل الملفات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockFiles:{Dev_Zaid}"):
                return m.reply(locknn.format(k, m.from_user.mention, k, "الملفات"))
            else:
                r.set(f"{m.chat.id}:lockFiles:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockFiles", "الملفات")

    if text == "فتح الملفات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockFiles:{Dev_Zaid}"):
                return m.reply(Openn2.format(k, m.from_user.mention, k, "الملفات"))
            else:
                r.delete(f"{m.chat.id}:lockFiles:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "الملفات"))

    if text == "قفل المتحركات" or text == "قفل المتحركه" or text == "قفل المتحركة":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockAnimations:{Dev_Zaid}"):
                return m.reply(locknn.format(k, m.from_user.mention, k, "المتحركات"))
            else:
                r.set(f"{m.chat.id}:lockAnimations:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockAnimations", "المتحركات")

    if text == "فتح المتحركات" or text == "فتح المتحركه" or text == "فتح المتحركة":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockAnimations:{Dev_Zaid}"):
                return m.reply(Openn2.format(k, m.from_user.mention, k, "المتحركات"))
            else:
                r.delete(f"{m.chat.id}:lockAnimations:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "المتحركات"))

    if text == "قفل الروابط":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockUrls:{Dev_Zaid}"):
                return m.reply(locknn.format(k, m.from_user.mention, k, "الروابط"))
            else:
                r.set(f"{m.chat.id}:lockUrls:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockUrls", "الروابط")

    if text == "فتح الروابط":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockUrls:{Dev_Zaid}"):
                return m.reply(Openn2.format(k, m.from_user.mention, k, "الروابط"))
            else:
                r.delete(f"{m.chat.id}:lockUrls:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "الروابط"))

    if text == "قفل الهشتاق" or text == "قفل الهاشتاق":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockHashtags:{Dev_Zaid}"):
                return m.reply(lockn.format(k, m.from_user.mention, k, "الهاشتاق"))
            else:
                r.set(f"{m.chat.id}:lockHashtags:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockHashtags", "الهاشتاق")

    if text == "فتح الهشتاق" or text == "فتح الهاشتاق":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockHashtags:{Dev_Zaid}"):
                return m.reply(Openn.format(k, m.from_user.mention, k, "الهاشتاق"))
            else:
                r.delete(f"{m.chat.id}:lockHashtags:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "الهاشتاق"))

    if text == "قفل البوتات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockBots:{Dev_Zaid}"):
                return m.reply(locknn.format(k, m.from_user.mention, k, "البوتات"))
            else:
                r.set(f"{m.chat.id}:lockBots:{Dev_Zaid}", 1)
                return m.reply(lock.format(k, m.from_user.mention, k, "البوتات"))

    if text == "فتح البوتات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockBots:{Dev_Zaid}"):
                return m.reply(Openn2.format(k, m.from_user.mention, k, "البوتات"))
            else:
                r.delete(f"{m.chat.id}:lockBots:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "البوتات"))

    if text == "قفل اليوزرات" or text == "قفل المنشن":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockTags:{Dev_Zaid}"):
                return m.reply(locknn.format(k, m.from_user.mention, k, "اليوزرات"))
            else:
                r.set(f"{m.chat.id}:lockTags:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockTags", "اليوزرات")

    if text == "فتح اليوزرات" or text == "فتح المنشن":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockTags:{Dev_Zaid}"):
                return m.reply(Openn2.format(k, m.from_user.mention, k, "اليوزرات"))
            else:
                r.delete(f"{m.chat.id}:lockTags:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "اليوزرات"))

    """
   if text == 'قفل الكفر' or text == 'قفل الشيعه' or text == 'قفل الشيعة':
     if not admin_pls(m.from_user.id, m.chat.id, c):
       return m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
     else:
       if r.get(f'{m.chat.id}:lockKFR:{Dev_Zaid}'):
         return m.reply(locknn.format(k,m.from_user.mention,k,'الكفر'))
       else:
         r.set(f'{m.chat.id}:lockKFR:{Dev_Zaid}',1)
         return m.reply(lock.format(k,m.from_user.mention,k,'الكفر'))

   if text == 'فتح الكفر' or text == 'فتح الشيعه' or text == 'فتح الشيعة':
     if not admin_pls(m.from_user.id, m.chat.id, c):
       return m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
     else:
       if not r.get(f'{m.chat.id}:lockKFR:{Dev_Zaid}'):
         return m.reply(Openn2.format(k,m.from_user.mention,k,'الكفر'))
       else:
         r.delete(f'{m.chat.id}:lockKFR:{Dev_Zaid}')
         return m.reply(Open.format(k,m.from_user.mention,k,'الكفر'))
   """

    if text == "قفل الإباحي" or text == "قفل الاباحي":
        if not owner_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المالك وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockNSFW:{Dev_Zaid}"):
                return m.reply(lockn.format(k, m.from_user.mention, k, "الإباحي"))
            else:
                r.set(f"{m.chat.id}:lockNSFW:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockNSFW", "الإباحي")

    if text == "فتح الإباحي" or text == "فتح الاباحي":
        if not owner_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المالك وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockNSFW:{Dev_Zaid}"):
                return m.reply(Openn.format(k, m.from_user.mention, k, "االإباحي"))
            else:
                r.delete(f"{m.chat.id}:lockNSFW:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "الإباحي"))

    if text == "قفل الكلام الكثير" or text == "قفل الكلايش":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockMessages:{Dev_Zaid}"):
                return m.reply(lockn.format(k, m.from_user.mention, k, "الكلام الكثير"))
            else:
                r.set(f"{m.chat.id}:lockMessages:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockMessages", "الكلام الكثير")

    if text == "فتح الكلام الكثير" or text == "فتح الكلايش":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockMessages:{Dev_Zaid}"):
                return m.reply(Openn.format(k, m.from_user.mention, k, "الكلام الكثير"))
            else:
                r.delete(f"{m.chat.id}:lockMessages:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "الكلام الكثير"))

    if text == "قفل التكرار":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockSpam:{Dev_Zaid}"):
                return m.reply(lockn.format(k, m.from_user.mention, k, "التكرار"))
            else:
                r.set(f"{m.chat.id}:lockSpam:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockSpam", "التكرار")

    if text == "فتح التكرار":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockSpam:{Dev_Zaid}"):
                return m.reply(Openn.format(k, m.from_user.mention, k, "التكرار"))
            else:
                r.delete(f"{m.chat.id}:lockSpam:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "التكرار"))

    if text == "قفل التوجيه":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockForward:{Dev_Zaid}"):
                return m.reply(lockn.format(k, m.from_user.mention, k, "التوجيه"))
            else:
                r.set(f"{m.chat.id}:lockForward:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockForward", "التوجيه")

    if text == "فتح التوجيه":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockForward:{Dev_Zaid}"):
                return m.reply(Openn.format(k, m.from_user.mention, k, "التوجيه"))
            else:
                r.delete(f"{m.chat.id}:lockForward:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "التوجيه"))

    if text == "قفل الانلاين":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockInline:{Dev_Zaid}"):
                return m.reply(lockn.format(k, m.from_user.mention, k, "الانلاين"))
            else:
                r.set(f"{m.chat.id}:lockInline:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockInline", "الانلاين")

    if text == "فتح الانلاين":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockInline:{Dev_Zaid}"):
                return m.reply(Openn.format(k, m.from_user.mention, k, "الانلاين"))
            else:
                r.delete(f"{m.chat.id}:lockInline:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "الانلاين"))

    if text == "قفل السب":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockSHTM:{Dev_Zaid}"):
                return m.reply(lockn.format(k, m.from_user.mention, k, "السب"))
            else:
                r.set(f"{m.chat.id}:lockSHTM:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockSHTM", "السب")

    if text == "فتح السب":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockSHTM:{Dev_Zaid}"):
                return m.reply(Openn.format(k, m.from_user.mention, k, "السب"))
            else:
                r.delete(f"{m.chat.id}:lockSHTM:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "السب"))

    if text == "قفل الاضافه" or text == "قفل الاضافة" or text == "قفل الجهات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockaddContacts:{Dev_Zaid}"):
                return m.reply(locknn.format(k, m.from_user.mention, k, "الاضافه"))
            else:
                r.set(f"{m.chat.id}:lockaddContacts:{Dev_Zaid}", 1)
                return m.reply(lock.format(k, m.from_user.mention, k, "الاضافه"))

    if text == "فتح الاضافه" or text == "فتح الاضافة" or text == "فتح الجهات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockaddContacts:{Dev_Zaid}"):
                return m.reply(Openn2.format(k, m.from_user.mention, k, "الاضافه"))
            else:
                r.delete(f"{m.chat.id}:lockaddContacts:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "الاضافه"))

    if text == "قفل دخول البوتات" or text == "قفل الوهمي" or text == "قفل الايراني":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockJoinPersian:{Dev_Zaid}"):
                return m.reply(locknn.format(k, m.from_user.mention, k, "دخول البوتات"))
            else:
                r.set(f"{m.chat.id}:lockJoinPersian:{Dev_Zaid}", 1)
                return m.reply(lock.format(k, m.from_user.mention, k, "دخول البوتات"))

    if text == "فتح دخول البوتات" or text == "فتح الوهمي" or text == "فتح الايراني":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockJoinPersian:{Dev_Zaid}"):
                return m.reply(Openn2.format(k, m.from_user.mention, k, "دخول البوتات"))
            else:
                r.delete(f"{m.chat.id}:lockJoinPersian:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "دخول البوتات"))

    if text == "قفل الصوت":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockAudios:{Dev_Zaid}"):
                return m.reply(lockn.format(k, m.from_user.mention, k, "الصوت"))
            else:
                r.set(f"{m.chat.id}:lockAudios:{Dev_Zaid}", 1)
                return send_lock_confirmation(c, m, k, "lockAudios", "الصوت")

    if text == "فتح الصوت":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockAudios:{Dev_Zaid}"):
                return m.reply(Openn.format(k, m.from_user.mention, k, "الصوت"))
            else:
                r.delete(f"{m.chat.id}:lockAudios:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "الصوت"))

    if text == "قفل القنوات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockChannels:{Dev_Zaid}"):
                return m.reply(locknn.format(k, m.from_user.mention, k, "القنوات"))
            else:
                r.set(f"{m.chat.id}:lockChannels:{Dev_Zaid}", 1)
                return m.reply(lock.format(k, m.from_user.mention, k, "القنوات"))

    if text == "فتح القنوات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockChannels:{Dev_Zaid}"):
                return m.reply(Openn2.format(k, m.from_user.mention, k, "القنوات"))
            else:
                r.delete(f"{m.chat.id}:lockChannels:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "القنوات"))

    if text == "قفل الدخول":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:lockJoin:{Dev_Zaid}"):
                return m.reply(lockn.format(k, m.from_user.mention, k, "الدخول"))
            else:
                r.set(f"{m.chat.id}:lockJoin:{Dev_Zaid}", 1)
                return m.reply(lock.format(k, m.from_user.mention, k, "الدخول"))

    if text == "فتح الدخول":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:lockJoin:{Dev_Zaid}"):
                return m.reply(Openn.format(k, m.from_user.mention, k, "الدخول"))
            else:
                r.delete(f"{m.chat.id}:lockJoin:{Dev_Zaid}")
                return m.reply(Open.format(k, m.from_user.mention, k, "الدخول"))

    if text == "تعطيل التحذير":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} التحذير معطل من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:disableWarn:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت التحذير\n☆"
                )

    if text == "تفعيل التحذير":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} التحذير مفعل من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:disableWarn:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت التحذير\n☆"
                )

    if text == "تعطيل اليوتيوب":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:disableYT:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} اليوتيوب معطل من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:disableYT:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت اليوتيوب\n☆"
                )

    if text == "تفعيل اليوتيوب":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:disableYT:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} اليوتيوب مفعل من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:disableYT:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت اليوتيوب\n☆"
                )

    if text == "تعطيل الساوند":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:disableSound:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} الساوند معطل من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:disableSound:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت الساوند\n☆"
                )

    if text == "تفعيل الساوند":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:disableSound:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} الساوند مفعل من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:disableSound:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت الساوند\n☆"
                )

    if text == "تعطيل الانستا":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:disableINSTA:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} الانستا معطل من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:disableINSTA:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت الانستا\n☆"
                )

    if text == "تفعيل الانستا":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:disableINSTA:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} الانستا مفعل من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:disableINSTA:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت الانستا\n☆"
                )

    if text == "تعطيل اهمس":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:disableWHISPER:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} اهمس معطل من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:disableWHISPER:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت اهمس\n☆"
                )

    if text == "تفعيل اهمس":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:disableWHISPER:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} اهمس مفعل من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:disableWHISPER:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت اهمس\n☆"
                )

    if text == "تعطيل التيك":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:disableTik:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} التيك معطل من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:disableTik:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت التيك\n☆"
                )

    if text == "تفعيل التيك":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:disableTik:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} التيك مفعل من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:disableTik:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت التيك\n☆"
                )

    if text == "تعطيل شازام":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:disableShazam:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} شازام معطل من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:disableShazam:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت شازام\n☆"
                )

    if text == "تفعيل شازام":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:disableShazam:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} شازام مفعل من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:disableShazam:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت شازام\n☆"
                )

    if text == "تعطيل الالعاب":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:disableGames:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} الالعاب معطله من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:disableGames:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت الالعاب\n☆"
                )

    if text == "تفعيل الالعاب":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:disableGames:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} الالعاب مفعله من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:disableGames:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت الالعاب\n☆"
                )

    if text == "تعطيل الترجمة" or text == "تعطيل الترجمه":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:disableTrans:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} الترجمه معطله من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:disableTrans:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت الترجمه\n☆"
                )

    if text == "تفعيل الترجمة" or text == "تفعيل الترجمه":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:disableTrans:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} الترجمه مفعله من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:disableTrans:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت الترجمه\n☆"
                )

    if text == "تعطيل التسلية" or text == "تعطيل التسليه":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if r.get(f"{m.chat.id}:disableFun:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} التسلية معطله من قبل\n☆"
                )
            else:
                r.set(f"{m.chat.id}:disableFun:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت التسلية\n☆"
                )

    if text == "تفعيل التسلية" or text == "تفعيل التسليه":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:disableFun:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} التسلية مفعله من قبل\n☆"
                )
            else:
                r.delete(f"{m.chat.id}:disableFun:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت التسلية\n☆"
                )

    if text == "تعطيل الاشتراك":
        if not dev2_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المطور وفوق ) بس")
        else:
            if r.get(f"disableSubscribe:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} الاشتراك الاجباري معطل من قبل\n☆"
                )
            else:
                r.set(f"disableSubscribe:{Dev_Zaid}", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت الاشتراك الاجباري\n☆"
                )

    if text == "قناة الاشتراك":
        if not dev2_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المطور وفوق ) بس")
        ch = r.get(f"forceChannel:{Dev_Zaid}") or "مافي قناة"
        return m.reply(f"{k} قناة الاشتراك هي ( {ch} )")

    if text.startswith("وضع قناة @"):
        if not dev2_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المطور وفوق ) بس")
        username = text.split("@")[1]
        try:
            chat = c.get_chat(username)
        except:
            return m.reply(f"{k} حدث خطأ")
        r.set(f"forceChannel:{Dev_Zaid}", "@" + username)
        return m.reply(f"{k} تم تعيين القناة بنجاح")

    if text == "تفعيل الاشتراك":
        if not dev2_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المطور وفوق ) بس")
        else:
            if not r.get(f"disableSubscribe:{Dev_Zaid}"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} الاشتراك الاجباري مفعل من قبل\n☆"
                )
            else:
                r.delete(f"disableSubscribe:{Dev_Zaid}")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت الاشتراك الاجباري\n☆"
                )

    if (
        text == "/ar"
        and m.reply_to_message
        and (m.reply_to_message.text or m.reply_to_message.caption)
    ):
        if not r.get(f"{m.chat.id}:disableTrans:{Dev_Zaid}"):
            text = m.reply_to_message.text or m.reply_to_message.caption
            translation = requests.get(
                f"https://hozory.com/translate/?target=ar&text={text}"
            ).json()["result"]["translate"]
            m.reply(f"`{translation}`")

    if (
        text == "/en"
        and m.reply_to_message
        and (m.reply_to_message.text or m.reply_to_message.caption)
    ):
        if not r.get(f"{m.chat.id}:disableTrans:{Dev_Zaid}"):
            text = m.reply_to_message.text or m.reply_to_message.caption
            translation = requests.get(
                f"https://hozory.com/translate/?target=en&text={text}"
            ).json()["result"]["translate"]
            m.reply(f"`{translation}`")

    if (
        text == "ترجمه"
        and m.reply_to_message
        and (m.reply_to_message.text or m.reply_to_message.caption)
    ):
        if not r.get(f"{m.chat.id}:disableTrans:{Dev_Zaid}"):
            text = m.reply_to_message.text or m.reply_to_message.caption
            en = requests.get(
                f"https://hozory.com/translate/?target=en&text={text}"
            ).json()["result"]["translate"]
            ar = requests.get(
                f"https://hozory.com/translate/?target=ar&text={text}"
            ).json()["result"]["translate"]
            ru = requests.get(
                f"https://hozory.com/translate/?target=ru&text={text}"
            ).json()["result"]["translate"]
            zh = requests.get(
                f"https://hozory.com/translate/?target=zh&text={text}"
            ).json()["result"]["translate"]
            fr = requests.get(
                f"https://hozory.com/translate/?target=fr&text={text}"
            ).json()["result"]["translate"]
            du = requests.get(
                f"https://hozory.com/translate/?target=nl&text={text}"
            ).json()["result"]["translate"]
            tr = requests.get(
                f"https://hozory.com/translate/?target=tr&text={text}"
            ).json()["result"]["translate"]
            txt = f"🇷🇺 : \n {ru}\n\n🇨🇳 : \n {zh}\n\n🇫🇷 :\n {fr}\n\n🇩🇪 :\n {du}\n\n🇹🇷 : \n{tr}"
            return m.reply(txt)

    if (
        (text.startswith("ترجمه ") or text.startswith("ترجمة "))
        and m.reply_to_message
        and (m.reply_to_message.text or m.reply_to_message.caption)
    ):
        if not r.get(f"{m.chat.id}:disableTrans:{Dev_Zaid}"):
            lang = text.split()[1]
            text = m.reply_to_message.text or m.reply_to_message.caption
            translation = requests.get(
                f"https://hozory.com/translate/?target={lang}&text={text}"
            ).json()["result"]["translate"]
            m.reply(f"`{translation}`")

    if text == "ابلاغ" and m.reply_to_message:
        text = f"{k} تم ابلاغ المشرفين"
        cc = 0
        for mm in c.get_chat_members(
            m.chat.id, filter=ChatMembersFilter.ADMINISTRATORS
        ):
            if not mm.user.is_deleted and not mm.user.is_bot:
                cc += 1
                text += f"[⁪⁬⁪⁬⁮⁪⁬⁪⁬⁮](tg://user?id={mm.user.id})"
        if cc == 0:
            return False
        return send_colored_message(
            c,
            m.chat.id,
            text,
            rows=[[{"text": "⚠️", "callback_data": "delAdminMSG", "style": "primary"}]],
        )

    if text == "المقيدين":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            co = 0
            cc = 1
            text = "المقيدين:\n\n"
            for mm in c.get_chat_members(
                m.chat.id, filter=ChatMembersFilter.RESTRICTED
            ):
                if co == 100:
                    break
                if not mm.user.is_deleted:
                    co += 1
                    user = (
                        f"@{mm.user.username}"
                        if mm.user.username
                        else f"[@{channel}](tg://user?id={mm.user.id})"
                    )
                    text += f"{cc} ➣ {user} ☆ ( `{mm.user.id}` )\n"
                    cc += 1
            text += "☆"
            if co == 0:
                return m.reply(f"{k} مافيه مقيديين")
            else:
                return m.reply(text)

    if text == "مسح المقيدين":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            co = 0
            for mm in c.get_chat_members(
                m.chat.id, filter=ChatMembersFilter.RESTRICTED
            ):
                co += 1
                c.restrict_chat_member(
                    m.chat.id,
                    mm.user.id,
                    ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_other_messages=True,
                        can_send_polls=True,
                        can_invite_users=True,
                        can_add_web_page_previews=True,
                        can_change_info=True,
                        can_pin_messages=True,
                    ),
                )
            if co == 0:
                return m.reply(f"{k} مافيه مقيديين")
            else:
                return m.reply(f"{k} ابشر مسحت ( {co} ) من المقيدين")

    if text == "تثبيت" and m.reply_to_message:
        if mod_pls(m.from_user.id, m.chat.id):
            m.reply_to_message.pin(disable_notification=False)
            m.reply(f"{k} ابشر ثبتت الرسالة ")

    if text == "الغاء التثبيت" and m.reply_to_message:
        if mod_pls(m.from_user.id, m.chat.id):
            m.reply_to_message.unpin()
            m.reply(f"{k} ابشر لغيت تثبيت الرسالة ")

    if text.startswith("تقييد ") and len(text.split()) == 2:
        if not admin_pls(m.from_user.id, m.chat.id, c):
            return m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")
        else:
            try:
                user = int(text.split()[1])
            except:
                user = text.split()[1].replace("@", "")
            try:
                get = m.chat.get_member(user)
                if m.from_user.id == get.user.id:
                    return m.reply("شفيك تبي تنزل نفسك")
                if pre_pls(get.user.id, m.chat.id):
                    rank = get_rank(get.user.id, m.chat.id)
                    return m.reply(f"{k} هييه مايمديك تقييد {rank} ياورع!")
                if get.status == ChatMemberStatus.RESTRICTED:
                    return m.reply(f"「 {get.user.mention} 」 \n{k} مقيد من قبل\n☆")
            except:
                return m.reply(f"{k} مافي عضو بهذا اليوزر")
            c.restrict_chat_member(
                m.chat.id, get.user.id, ChatPermissions(can_send_messages=False)
            )
            return m.reply(f"「 {get.user.mention} 」 \n{k} قييدته\n☆")

    if text == "تقييد" and m.reply_to_message and m.reply_to_message.from_user:
        if not admin_pls(m.from_user.id, m.chat.id, c):
            return m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")
        else:
            if m.from_user.id == m.reply_to_message.from_user.id:
                return m.reply("شفيك تبي تنزل نفسك")
            get = m.chat.get_member(m.reply_to_message.from_user.id)
            if pre_pls(m.reply_to_message.from_user.id, m.chat.id):
                rank = get_rank(m.reply_to_message.from_user.id, m.chat.id)
                return m.reply(f"{k} هييه مايمديك تقييد {rank} ياورع!")
            if get.status == ChatMemberStatus.RESTRICTED:
                return m.reply(
                    f"「 {m.reply_to_message.from_user.mention} 」 \n{k} مقيد من قبل\n☆"
                )
            c.restrict_chat_member(
                m.chat.id,
                m.reply_to_message.from_user.id,
                ChatPermissions(can_send_messages=False),
            )
            return m.reply(
                f"「 {m.reply_to_message.from_user.mention} 」 \n{k} قييدته\n☆"
            )

    if (
        (text.startswith("الغاء تقييد ") or text.startswith("الغاء التقييد "))
        and len(text.split()) == 3
    ):
        if not admin_pls(m.from_user.id, m.chat.id, c):
            return m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")
        else:
            try:
                user = int(text.split()[2])
            except:
                user = text.split()[2].replace("@", "")
            try:
                get = m.chat.get_member(user)
                if not get.status == ChatMemberStatus.RESTRICTED:
                    return m.reply(f"「 {get.user.mention} 」 \n{k} مو مقيد من قبل\n☆")
            except:
                return m.reply(f"{k} مافي عضو بهذا اليوزر")
            c.restrict_chat_member(
                m.chat.id,
                get.user.id,
                ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_send_polls=True,
                    can_invite_users=True,
                    can_add_web_page_previews=True,
                    can_change_info=True,
                    can_pin_messages=True,
                ),
            )
            return m.reply(f"「 {get.user.mention} 」 \n{k} ابشر الغيت تقييده\n☆")

    if (
        (text == "الغاء تقييد" or text == "الغاء التقييد")
        and m.reply_to_message
        and m.reply_to_message.from_user
    ):
        if not admin_pls(m.from_user.id, m.chat.id, c):
            return m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")
        else:
            get = m.chat.get_member(m.reply_to_message.from_user.id)
            if not get.status == ChatMemberStatus.RESTRICTED:
                return m.reply(
                    f"「 {m.reply_to_message.from_user.mention} 」 \n{k} مو مقيد من قبل\n☆"
                )
            c.restrict_chat_member(
                m.chat.id,
                m.reply_to_message.from_user.id,
                ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_send_polls=True,
                    can_invite_users=True,
                    can_add_web_page_previews=True,
                    can_change_info=True,
                    can_pin_messages=True,
                ),
            )
            return m.reply(
                f"「 {m.reply_to_message.from_user.mention} 」 \n{k} ابشر الغيت تقييده\n☆"
            )

    if text == "المحظورين":
        if not admin_pls(m.from_user.id, m.chat.id, c):
            return m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")
        else:
            co = 0
            cc = 1
            text = "المحظورين:\n\n"
            for mm in c.get_chat_members(m.chat.id, filter=ChatMembersFilter.BANNED):
                if co == 100:
                    break
                if mm.user:
                    if not mm.user.is_deleted:
                        co += 1
                        user = (
                            f"@{mm.user.username}"
                            if mm.user.username
                            else f"[@{channel}](tg://user?id={mm.user.id})"
                        )
                        text += f"{cc} ➣ {user} ☆ ( `{mm.user.id}` )\n"
                        cc += 1
                if mm.chat:
                    co += 1
                    user = f"@{mm.chat.username}"
                    text += f"{cc} ➣ {user} ☆ (`{mm.chat.id}`)\n"
                    cc += 1
            text += "☆"
            if co == 0:
                return m.reply(f"{k} مافيه محظورين")
            else:
                return m.reply(text)

    if text == "مسح المحظورين":
        if not admin_pls(m.from_user.id, m.chat.id, c):
            return m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")
        else:
            co = 0
            for mm in c.get_chat_members(m.chat.id, filter=ChatMembersFilter.BANNED):
                if mm.user:
                    co += 1
                    c.unban_chat_member(m.chat.id, mm.user.id)
                if mm.chat:
                    co += 1
                    c.unban_chat_member(m.chat.id, mm.chat.id)
            if co == 0:
                return m.reply(f"{k} مافيه محظورين")
            else:
                return m.reply(f"{k} ابشر مسحت ( {co} ) من المحظورين")

    if text.startswith("حظر ") and len(text.split()) == 2:
        if not admin_pls(m.from_user.id, m.chat.id, c):
            return m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")
        else:
            try:
                user = int(text.split()[1])
            except:
                user = text.split()[1].replace("@", "")
            try:
                get = m.chat.get_member(user)
                if m.from_user.id == get.user.id:
                    return m.reply("شفيك تبي تنزل نفسك")
                if pre_pls(get.user.id, m.chat.id):
                    rank = get_rank(get.user.id, m.chat.id)
                    return m.reply(f"{k} هييه مايمديك تحظر {rank} ياورع!")
                if get.status == ChatMemberStatus.BANNED:
                    return m.reply(f"「 {get.user.mention} 」 \n{k} محظور من قبل\n☆")
            except:
                return m.reply(f"{k} مافي عضو بهذا اليوزر")
            m.chat.ban_member(get.user.id)
            return m.reply(f"「 {get.user.mention} 」 \n{k} حظرته\n☆")

    if text == "حظر" and m.reply_to_message and m.reply_to_message.from_user:
        if not admin_pls(m.from_user.id, m.chat.id, c):
            return m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")
        else:
            if m.from_user.id == m.reply_to_message.from_user.id:
                return m.reply("شفيك تبي تنزل نفسك")
            get = m.chat.get_member(m.reply_to_message.from_user.id)
            if pre_pls(m.reply_to_message.from_user.id, m.chat.id):
                rank = get_rank(m.reply_to_message.from_user.id, m.chat.id)
                return m.reply(f"{k} هييه مايمديك تحظر {rank} ياورع!")
            if get.status == ChatMemberStatus.BANNED:
                return m.reply(
                    f"「 {m.reply_to_message.from_user.mention} 」 \n{k} محظور من قبل\n☆"
                )
            m.chat.ban_member(m.reply_to_message.from_user.id)
            return m.reply(
                f"「 {m.reply_to_message.from_user.mention} 」 \n{k} حظرته\n☆"
            )

    if text == "طرد البوتات":
        if not owner_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الأمر يخص ( المالك وفوق ) بس")
        else:
            co = 0
            for mm in m.chat.get_members(filter=ChatMembersFilter.BOTS):
                try:
                    m.chat.ban_member(mm.user.id)
                    co += 1
                except:
                    pass
            if co == 0:
                return m.reply(f"{k} مافيه بوتات")
            else:
                return m.reply(f"{k} ابشر حظر ( {co} ) بوت")

    if text.startswith("طرد ") and len(text.split()) == 2:
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")
        else:
            try:
                user = int(text.split()[1])
            except:
                user = text.split()[1].replace("@", "")
            try:
                get = m.chat.get_member(user)
                if m.from_user.id == get.user.id:
                    return m.reply("شفيك تبي تنزل نفسك")
                if pre_pls(get.user.id, m.chat.id):
                    rank = get_rank(get.user.id, m.chat.id)
                    return m.reply(f"{k} هييه مايمديك تطرد {rank} ياورع!")
                if get.status == ChatMemberStatus.BANNED:
                    return m.reply(f"「 {get.user.mention} 」 \n{k} مطرود من قبل\n☆")
            except:
                return m.reply(f"{k} مافي عضو بهذا اليوزر")
            m.chat.ban_member(get.user.id)
            m.chat.unban_member(get.user.id)
            return m.reply(f"「 {get.user.mention} 」 \n{k} طردته\n☆")

    if text in ["اهمس", "همسه", "ه"] and m.reply_to_message and m.reply_to_message.from_user:
        if r.get(f"{m.chat.id}:lockWHISPER:{Dev_Zaid}"):
                return m.reply(f"{k} امر الهمسة معطل")
        user_id = m.reply_to_message.from_user.id
        if user_id == m.from_user.id:
                return m.reply(f"{k} مافيك تهمس لنفسك ياغبي")
        else:
                import uuid
                id = str(uuid.uuid4())[:6]
                data = {
                        "from": m.from_user.id,
                        "to": user_id,
                        "chat": m.chat.id,
                        }
                reply_msg = m.reply_to_message
                if reply_msg.media:
                        if reply_msg.photo:
                                data["media_type"] = "photo"
                                data["media_id"] = reply_msg.photo.file_id
                        elif reply_msg.video:
                                data["media_type"] = "video"
                                data["media_id"] = reply_msg.video.file_id
                        elif reply_msg.animation:
                                data["media_type"] = "animation"
                                data["media_id"] = reply_msg.animation.file_id
                        elif reply_msg.audio:
                                data["media_type"] = "audio"
                                data["media_id"] = reply_msg.audio.file_id
                        elif reply_msg.voice:
                                data["media_type"] = "voice"
                                data["media_id"] = reply_msg.voice.file_id
                        elif reply_msg.document:
                                data["media_type"] = "document"
                                data["media_id"] = reply_msg.document.file_id
                        elif reply_msg.sticker:
                                data["media_type"] = "sticker"
                                data["media_id"] = reply_msg.sticker.file_id
                        elif reply_msg.video_note:
                                data["media_type"] = "video_note"
                                data["media_id"] = reply_msg.video_note.file_id
                        if reply_msg.caption:
                                data["caption"] = reply_msg.caption
                else:
                        data["media_type"] = "text"
                        data["text"] = reply_msg.text
                a = m.reply(
                        f"{k} تم تحديد الهمسة الى [ {m.reply_to_message.from_user.mention} ]",
                        reply_markup=InlineKeyboardMarkup(
                                [
                                        [
                                                InlineKeyboardButton(
                                                        f"اهمس الى [ {m.reply_to_message.from_user.first_name[:25]} ]",
                                                        url=f"t.me/{c.me.username}?start=hmsa{id}",
                                                        )
                                        ]
                                ]
                                ),
                        )
                data["button_id"] = a.id
                wsdb.setex(key=id, ttl=3600, value=data)
                return True

    if text == "تعطيل التنظيف":
        if not gowner_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الأمر يخص ( المالك الاساسي وفوق ) بس")
        else:
            if not r.hget(Dev_Zaid + str(m.chat.id), "ena-clean"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} التنظيف معطل من قبل\n☆"
                )
            else:
                r.hdel(Dev_Zaid + str(m.chat.id), "ena-clean")
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت التنظيف\n☆"
                )

    if text == "تفعيل التنظيف":
        if not gowner_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الأمر يخص ( المالك الاساسي وفوق ) بس")
        else:
            if r.hget(Dev_Zaid + str(m.chat.id), "ena-clean"):
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} التنظيف مفعل من قبل\n☆"
                )
            else:
                r.hset(Dev_Zaid + str(m.chat.id), "ena-clean", 1)
                return m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت التنظيف\n☆"
                )

    if re.search("^وضع وقت التنظيف [0-9]+$", text):
        if not gowner_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الأمر يخص ( المالك الاساسي وفوق ) بس")
        else:
            secs = int(text.split()[3])
            if secs > 3600 or secs < 60:
                return m.reply(
                    f"{k} عليك تحديد وقت التنظيف بالثواني من 60 الى 3600 ثانية"
                )
            else:
                r.hset(Dev_Zaid + str(m.chat.id), "clean-secs", secs)
                return m.reply(f"{k} تم تعيين وقت التنظيف ( {secs} ) ثانية")

    if text == "وقت التنظيف":
        if not gowner_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الأمر يخص ( المالك الاساسي وفوق ) بس")
        else:
            secs = r.hget(Dev_Zaid + str(m.chat.id), "clean-secs") or "60"
            return m.reply(f"`{secs}`")

    if text == "طرد" and m.reply_to_message and m.reply_to_message.from_user:
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            try:
                if m.from_user.id == m.reply_to_message.from_user.id:
                    return m.reply("شفيك تبي تنزل نفسك")
                get = m.chat.get_member(m.reply_to_message.from_user.id)
                if pre_pls(m.reply_to_message.from_user.id, m.chat.id):
                    rank = get_rank(m.reply_to_message.from_user.id, m.chat.id)
                    return m.reply(f"{k} هييه مايمديك تطرد {rank} ياورع!")
                if get.status == ChatMemberStatus.BANNED:
                    return m.reply(
                        f"「 {m.reply_to_message.from_user.mention} 」 \n{k} مطرود من قبل\n☆"
                    )
                m.chat.ban_member(m.reply_to_message.from_user.id)
                m.reply(f"「 {m.reply_to_message.from_user.mention} 」 \n{k} طردته\n☆")
                return m.chat.unban_member(m.reply_to_message.from_user.id)
            except:
                return m.reply(f"{k} العضو مو بالمجموعة")

    if (
        (text.startswith("رفع الحظر ") or text.startswith("الغاء الحظر "))
        and len(text.split()) == 3
    ):
        if not admin_pls(m.from_user.id, m.chat.id, c):
            return m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")
        else:
            try:
                user = int(text.split()[2])
            except:
                user = text.split()[2].replace("@", "")
            try:
                get = m.chat.get_member(user)
                if not get.status == ChatMemberStatus.BANNED:
                    return m.reply(f"「 {get.user.mention} 」 \n{k} مو محظور من قبل\n☆")
            except:
                return m.reply(f"{k} مافي عضو بهذا اليوزر")
            m.chat.unban_member(get.user.id)
            return m.reply(f"「 {get.user.mention} 」 \n{k} ابشر الغيت حظره\n☆")

    if (
        (text == "رفع الحظر" or text == "الغاء الحظر")
        and m.reply_to_message
        and m.reply_to_message.from_user
    ):
        if not admin_pls(m.from_user.id, m.chat.id, c):
            return m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")
        else:
            try:
                get = m.chat.get_member(m.reply_to_message.from_user.id)
                if not get.status == ChatMemberStatus.BANNED:
                    return m.reply(
                        f"「 {m.reply_to_message.from_user.mention} 」 \n{k} مو محظور من قبل\n☆"
                    )
                m.chat.unban_member(m.reply_to_message.from_user.id)
                return m.reply(
                    f"「 {m.reply_to_message.from_user.mention} 」 \n{k} ابشر الغيت حظره\n☆"
                )
            except:
                return m.reply(f"{k} العضو مو بالمجموعة")

    if text.startswith("رفع القيود ") and len(text.split()) == 3:
        if not admin_pls(m.from_user.id, m.chat.id, c):
            return m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")
        else:
            try:
                user = int(text.split()[2])
            except:
                user = text.split()[2].replace("@", "")
            co = 0
            text = ""
            try:
                get = m.chat.get_member(user)
                if get.status == ChatMemberStatus.BANNED:
                    m.chat.unban_member(get.user.id)
                    text += "حظر\n"
                    co += 1
                if get.status == ChatMemberStatus.RESTRICTED:
                    c.restrict_chat_member(
                        m.chat.id,
                        get.user.id,
                        ChatPermissions(
                            can_send_messages=True,
                            can_send_media_messages=True,
                            can_send_other_messages=True,
                            can_send_polls=True,
                            can_invite_users=True,
                            can_add_web_page_previews=True,
                            can_change_info=True,
                            can_pin_messages=True,
                        ),
                    )
                    text += "تقييد\n"
                    co += 1
                if r.get(f"{get.user.id}:mute:{m.chat.id}{Dev_Zaid}"):
                    r.delete(f"{get.user.id}:mute:{m.chat.id}{Dev_Zaid}")
                    r.srem(f"{m.chat.id}:listMUTE:{Dev_Zaid}", get.user.id)
                    text += "كتم\n"
                    co += 1
                if co > 0:
                    return m.reply(f"رفعت القيود التالية:\n{text}\n☆")
                else:
                    return m.reply(f"「 {get.user.mention} 」\n{k} ماله قيود من قبل\n☆")

            except:
                return m.reply(f"{k} مافي عضو بهذا اليوزر")
            m.chat.unban_member(get.user.id)
            return m.reply(f"「 {get.user.mention} 」 \n{k} ابشر الغيت حظره\n☆")

    if text == "رفع القيود" and m.reply_to_message and m.reply_to_message.from_user:
        if not admin_pls(m.from_user.id, m.chat.id, c):
            return m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")
        else:
            try:
                text = ""
                co = 0
                get = m.chat.get_member(m.reply_to_message.from_user.id)
                if get.status == ChatMemberStatus.BANNED:
                    m.chat.unban_member(get.user.id)
                    text += "حظر\n"
                    co += 1
                if get.status == ChatMemberStatus.RESTRICTED:
                    c.restrict_chat_member(
                        m.chat.id,
                        get.user.id,
                        ChatPermissions(
                            can_send_messages=True,
                            can_send_media_messages=True,
                            can_send_other_messages=True,
                            can_send_polls=True,
                            can_invite_users=True,
                            can_add_web_page_previews=True,
                            can_change_info=True,
                            can_pin_messages=True,
                        ),
                    )
                    text += "تقييد\n"
                    co += 1
                if r.get(f"{get.user.id}:mute:{m.chat.id}{Dev_Zaid}"):
                    r.delete(f"{get.user.id}:mute:{m.chat.id}{Dev_Zaid}")
                    r.srem(f"{m.chat.id}:listMUTE:{Dev_Zaid}", get.user.id)
                    text += "كتم\n"
                    co += 1
                if co > 0:
                    return m.reply(f"رفعت القيود التالية:\n{text}\n☆")
                else:
                    return m.reply(f"「 {get.user.mention} 」\n{k} ماله قيود من قبل\n☆")
            except:
                return m.reply(f"{k} العضو مو بالمجموعة")

    if text == "كشف البوتات":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            co = 0
            text = "بوتات المجموعة:\n\n"
            cc = 1
            for mm in m.chat.get_members(filter=ChatMembersFilter.BOTS):
                if co == 100:
                    break
                text += f"{cc}) {mm.user.mention}"
                if mm.status == ChatMemberStatus.ADMINISTRATOR:
                    text += "👑"
                text += "\n"
                cc += 1
                co += 1
            text += "☆"
            if co == 0:
                return m.reply(f"{k} مافيه بوتات")
            else:
                return m.reply(text)

    if text == "مين ضافني":
        get = m.chat.get_member(m.from_user.id).invited_by
        if not get:
            return m.reply(f"{k} محد ضافك")
        else:
            return m.reply(get.mention)

    if text == "بايو عشوائي":
        return m.reply(f"{k} تحت الصيانة")

    if text == "مسح" and m.reply_to_message:
        if admin_pls(m.from_user.id, m.chat.id, c):
            m.reply_to_message.delete()
            m.delete()
        else:
            m.delete()

    if (
        text.startswith("مسح ")
        and len(text.split()) == 2
        and re.findall("[0-9]+", text)
    ):
        count = int(re.findall("[0-9]+", text)[0])
        if not admin_pls(m.from_user.id, m.chat.id, c):
            return m.delete()
        else:
            if count > 400:
                return m.reply(f"{k} اختار من 1 الى 400")
            else:
                for msg in range(m.id, m.id - count, -1):
                    try:
                        c.delete_messages(m.chat.id, msg)
                    except:
                        pass

    if text == "تنزيل مشرف" or text.startswith("تنزيل مشرف "):
        if not owner_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الأمر يخص ( المالك وفوق ) بس")
        if m.reply_to_message and m.reply_to_message.from_user:
            target = m.reply_to_message.from_user.id
        else:
            target = parse_demote_command(text)
        if not target:
            return m.reply(" الرجاء إرسال ايدي أو يوزر العضو الذي تريد تنزيله.")
        resolved = resolve_user(c, target)
        if not resolved:
            return m.reply(" لم أتمكن من العثور على العضو.")
        target = resolved
        try:
            mention = m.chat.get_member(target).user.mention
        except:
            mention = f"`{target}`"
        try:
            c.promote_chat_member(m.chat.id, target, privileges=_build_chat_privileges({}))
            return m.reply(f"「 {mention} 」\n{k} نزلته من الاشراف")
        except:
            return m.reply(f"「 {mention} 」\n{k} مو انا الي رفعته او ماعندي صلاحيات")

    # ====================== نظام رفع المشرف الجديد (من ملف kk.py) ======================
    if (text == "رفع مشرف" or text.startswith("رفع مشرف ")) and owner_pls(m.from_user.id, m.chat.id):
        target = None
        title = None
        if m.reply_to_message and m.reply_to_message.from_user:
            target = m.reply_to_message.from_user.id
            remainder = text[len("رفع مشرف"):].strip()
            title = remainder if remainder else None
        else:
            target, title = parse_promote_command(text)
        if not target:
            r.set(f"{m.from_user.id}:promote:step:{m.chat.id}", "waiting_target")
            return m.reply(" الرجاء إرسال ايدي أو يوزر العضو الذي تريد رفعه.")
        resolved = resolve_user(c, target)
        if not resolved:
            return m.reply(" لم أتمكن من العثور على العضو.")
        target = resolved

       
        bot_member = m.chat.get_member(c.me.id)
        if not bot_member.privileges or not bot_member.privileges.can_promote_members:
            return m.reply(" البوت ليس لديه صلاحية رفع مشرفين.")

      
        try:
            target_member = m.chat.get_member(target)
            if target_member.status == ChatMemberStatus.OWNER:
                return m.reply("👑 هذا المالك لا يمكن رفعه كمشرف.")
        except:
            pass

      
        try:
            target_member = m.chat.get_member(target)
            if target_member.status in [ChatMemberStatus.ADMINISTRATOR]:
                return m.reply(" هذا الشخص مشرف بالفعل.")
        except:
            pass

      
        if target == c.me.id:
            return m.reply(" البوت لا يمكنه رفع نفسه.")

        r.set(f"{m.from_user.id}:promote:target:{m.chat.id}", str(target))
        if title:
            r.set(f"{m.from_user.id}:promote:title:{m.chat.id}", title)
        else:
            r.set(f"{m.from_user.id}:promote:title:{m.chat.id}", "")
        r.set(f"{m.from_user.id}:promote:step:{m.chat.id}", "done")
        return send_colored_message(
            c,
            m.chat.id,
            f"{k} تم تحديد العضو، الآن اضغط على الزر أدناه لتعديل صلاحيات المشرف.",
            rows=[[{"text": "تعديل الصلاحيات", "callback_data": f"promote:button:{target}:{m.chat.id}", "style": "primary"}]],
        )
    # ============================================================

    if text == "مسح قائمة التثبيت":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            c.unpin_all_chat_messages(m.chat.id)
            return m.reply(f"{k} ابشر مسحت قائمة التثبيت")

    if (
        text == "الاوامر"
        or text.lower() == "/commands"
        or text.lower() == f"/commands@{botUsername.lower()}"
    ):
        if admin_pls(m.from_user.id, m.chat.id, c):
            channel = (
                r.get(f"{Dev_Zaid}:BotChannel")
                if r.get(f"{Dev_Zaid}:BotChannel")
                else "YQYQY6"
            )
            return send_colored_message(
                c,
                m.chat.id,
                f"{k} اهلين فيك باوامر البوت\n\nللاستفسار - @{channel}\n\n{commands_menu_list_text()}",
                rows=commands_menu_rows(None, m.from_user.id),
            )
        else:
            return m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")


@Client.on_callback_query(group=1)
def CallbackQueryHandler(c, m):
    channel = (
        r.get(f"{Dev_Zaid}:BotChannel") if r.get(f"{Dev_Zaid}:BotChannel") else "YQYQY6"
    )
    Thread(target=CallbackQueryResponse, args=(c, m, channel)).start()


def CallbackQueryResponse(c, m, channel):
    k = r.get(f"{Dev_Zaid}:botkey")

    # ====================== أزرار اختيار طريقة التعامل مع المخالفين بعد أمر القفل ======================
    if m.data.startswith("punAct:"):
        parts = m.data.split(":")
        item_key = parts[1]
        action = parts[2]
        chat_id = int(parts[3])
        if not mod_pls(m.from_user.id, chat_id):
            return m.answer(f"{k} هذا الزر يخص ( المدير وفوق ) بس", show_alert=True)
        r.set(punish_action_key(chat_id, item_key), action)
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            f"{k} تم اختيار طريقة التعامل\nاختر نطاق التنفيذ من الأزرار بالأسفل",
            rows=punish_scope_rows(item_key, chat_id),
        )
        return m.answer()

    if m.data.startswith("punScope:"):
        parts = m.data.split(":")
        item_key = parts[1]
        scope = parts[2]
        chat_id = int(parts[3])
        if not mod_pls(m.from_user.id, chat_id):
            return m.answer(f"{k} هذا الزر يخص ( المدير وفوق ) بس", show_alert=True)
        r.set(punish_scope_key(chat_id, item_key), scope)
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            f"{k} تم حفظ إعدادات المنع بنجاح",
        )
        return m.answer(f"{k} تم الحفظ")
    # ============================================================

    # ====================== أزرار تعديل صلاحيات المشرف (تكملة نظام رفع المشرف) ======================
    if m.data.startswith("promote:button:"):
        parts = m.data.split(":")
        target_id = int(parts[2])
        chat_id = int(parts[3])
        if not owner_pls(m.from_user.id, m.message.chat.id):
            return m.answer(f"{k} هذا الزر يخص ( المالك وفوق ) بس", show_alert=True)
        is_channel = m.message.chat.type == ChatType.CHANNEL
        if is_channel:
            default_perms = {
                "can_manage_chat": True,
                "can_post_messages": True,
                "can_edit_messages": True,
                "can_delete_messages": True,
                "can_post_stories": True,
                "can_edit_stories": True,
                "can_delete_stories": True,
                "can_manage_video_chats": True,
                "can_restrict_members": True,
                "can_promote_members": False,
                "can_change_info": True,
                "can_invite_users": True,
                "is_anonymous": False,
            }
        else:
            default_perms = {
                "can_manage_chat": True,
                "can_delete_messages": True,
                "can_manage_video_chats": True,
                "can_restrict_members": True,
                "can_promote_members": False,
                "can_change_info": True,
                "can_invite_users": True,
                "can_pin_messages": True,
                "can_manage_topics": True,
                "is_anonymous": False,
            }
        r.set(
            f"{m.from_user.id}:promote:perms:{target_id}:{chat_id}",
            _color_json.dumps(default_perms),
        )
        try:
            get = m.message.chat.get_member(target_id)
            mention = get.user.mention
        except:
            mention = f"`{target_id}`"
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            f"{k} اختار صلاحيات المشرف لـ「 {mention} 」ثم دوس تأكيد الصلاحيات",
            rows=get_permission_rows(target_id, chat_id, default_perms, is_channel=is_channel),
        )
        return

    if m.data.startswith("promote:perm:"):
        parts = m.data.split(":")
        perm_key = parts[2]
        target_id = int(parts[3])
        chat_id = int(parts[4])
        if not owner_pls(m.from_user.id, m.message.chat.id):
            return m.answer(f"{k} هذا الزر يخص ( المالك وفوق ) بس", show_alert=True)
        stored = r.get(f"{m.from_user.id}:promote:perms:{target_id}:{chat_id}")
        if not stored:
            return m.answer(f"{k} انتهت صلاحية هذه القائمة، ابدأ الأمر من جديد", show_alert=True)
        perms = _color_json.loads(stored)
        perms[perm_key] = not perms.get(perm_key, False)
        r.set(
            f"{m.from_user.id}:promote:perms:{target_id}:{chat_id}",
            _color_json.dumps(perms),
        )
        edit_colored_markup(
            c,
            m.message.chat.id,
            m.message.id,
            get_permission_rows(target_id, chat_id, perms, is_channel="can_post_messages" in perms),
        )
        return

    if m.data.startswith("promote:confirm:"):
        parts = m.data.split(":")
        target_id = int(parts[2])
        chat_id = int(parts[3])
        if not owner_pls(m.from_user.id, m.message.chat.id):
            return m.answer(f"{k} هذا الزر يخص ( المالك وفوق ) بس", show_alert=True)
        stored = r.get(f"{m.from_user.id}:promote:perms:{target_id}:{chat_id}")
        if not stored:
            return m.answer(f"{k} انتهت صلاحية هذه القائمة، ابدأ الأمر من جديد", show_alert=True)
        perms = _color_json.loads(stored)
        title = r.get(f"{m.from_user.id}:promote:title:{chat_id}")
        if not title:
            title = r.get(f"anonpromote:{chat_id}:title:{target_id}")
        bot_member = m.message.chat.get_member(c.me.id)
        if not bot_member.privileges or not bot_member.privileges.can_promote_members:
            return m.answer(f"{k} البوت ليس لديه صلاحية رفع مشرفين", show_alert=True)
        try:
            privileges = _build_chat_privileges(perms)
            c.promote_chat_member(chat_id, target_id, privileges=privileges)
        except:
            return m.answer(f"{k} ما قدرت ارفعه، تأكد من صلاحيات البوت", show_alert=True)
        if title:
            try:
                c.set_administrator_title(chat_id, target_id, title)
            except:
                pass
        r.set(f"{chat_id}:rankADMIN:{target_id}{Dev_Zaid}", 1)
        r.sadd(f"{chat_id}:listADMIN:{Dev_Zaid}", target_id)
        r.delete(f"{m.from_user.id}:promote:step:{chat_id}")
        r.delete(f"{m.from_user.id}:promote:target:{chat_id}")
        r.delete(f"{m.from_user.id}:promote:title:{chat_id}")
        r.delete(f"{m.from_user.id}:promote:perms:{target_id}:{chat_id}")
        try:
            get = m.message.chat.get_member(target_id)
            mention = get.user.mention
        except:
            mention = f"`{target_id}`"
        m.edit_message_text(f"الحلو 「 {mention} 」\n{k} رفعته مشرف بالصلاحيات اللي اخترتها")
        return

    if m.data.startswith("promote:cancel:"):
        parts = m.data.split(":")
        target_id = int(parts[2])
        chat_id = int(parts[3])
        if not owner_pls(m.from_user.id, m.message.chat.id):
            return m.answer(f"{k} هذا الزر يخص ( المالك وفوق ) بس", show_alert=True)
        r.delete(f"{m.from_user.id}:promote:step:{chat_id}")
        r.delete(f"{m.from_user.id}:promote:target:{chat_id}")
        r.delete(f"{m.from_user.id}:promote:title:{chat_id}")
        r.delete(f"{m.from_user.id}:promote:perms:{target_id}:{chat_id}")
        m.edit_message_text(f"{k} تم إلغاء رفع المشرف")
        return
    # ============================================================

    # ====================== أزرار تنزيل مشرف من قناة أو من مشرف مجهول ======================
    if m.data.startswith("demote:confirm:"):
        parts = m.data.split(":")
        target_id = int(parts[2])
        chat_id = int(parts[3])
        if not owner_pls(m.from_user.id, m.message.chat.id):
            return m.answer(f"{k} هذا الزر يخص ( المالك وفوق ) بس", show_alert=True)
        try:
            mention = m.message.chat.get_member(target_id).user.mention
        except:
            mention = f"`{target_id}`"
        try:
            c.promote_chat_member(chat_id, target_id, privileges=_build_chat_privileges({}))
            m.edit_message_text(f"「 {mention} 」\n{k} نزلته من الاشراف")
        except:
            m.edit_message_text(f"「 {mention} 」\n{k} مو انا الي رفعته او ماعندي صلاحيات")
        return

    if m.data.startswith("demote:cancel:"):
        if not owner_pls(m.from_user.id, m.message.chat.id):
            return m.answer(f"{k} هذا الزر يخص ( المالك وفوق ) بس", show_alert=True)
        m.edit_message_text(f"{k} تم إلغاء التنزيل")
        return
    # ============================================================

    # ====================== أزرار لوحة الحماية (أمر "الحماية") ======================
    if m.data.startswith("protO:") or m.data.startswith("protL:"):
        parts = m.data.split(":")
        action = parts[0]
        idx = int(parts[1])
        page = int(parts[2])
        uid = int(parts[3])
        if m.from_user.id != uid:
            return m.answer(f"{k} هذه القائمة مش ليك", show_alert=True)
        if not mod_pls(m.from_user.id, m.message.chat.id):
            return m.answer(f"{k} هذا الزر يخص ( المدير وفوق ) بس", show_alert=True)
        label, item_key = PROTECTION_ITEMS[idx]
        key = protection_redis_key(m.message.chat.id, item_key)
        if action == "protO":
            r.delete(key)
        else:
            r.set(key, 1)
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            protection_header_text(k, page),
            rows=build_protection_rows(m.message.chat.id, page, uid),
        )
        return m.answer(f"{k} تم {'فتح' if action == 'protO' else 'قفل'} {label}")

    if m.data.startswith("protN:"):
        parts = m.data.split(":")
        page = int(parts[1])
        uid = int(parts[2])
        if m.from_user.id != uid:
            return m.answer(f"{k} هذه القائمة مش ليك", show_alert=True)
        if not mod_pls(m.from_user.id, m.message.chat.id):
            return m.answer(f"{k} هذا الزر يخص ( المدير وفوق ) بس", show_alert=True)
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            protection_header_text(k, page),
            rows=build_protection_rows(m.message.chat.id, page, uid),
        )
        return

    if m.data.startswith("protT:"):
        parts = m.data.split(":")
        page = int(parts[1])
        uid = int(parts[2])
        if m.from_user.id != uid:
            return m.answer(f"{k} هذه القائمة مش ليك", show_alert=True)
        if not mod_pls(m.from_user.id, m.message.chat.id):
            return m.answer(f"{k} هذا الزر يخص ( المدير وفوق ) بس", show_alert=True)
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            build_protection_text_list(m.message.chat.id, k, channel),
            rows=[[{"text": "رجوع", "callback_data": f"protB:{page}:{uid}"}]],
        )
        return m.answer()

    if m.data.startswith("protB:"):
        parts = m.data.split(":")
        page = int(parts[1])
        uid = int(parts[2])
        if m.from_user.id != uid:
            return m.answer(f"{k} هذه القائمة مش ليك", show_alert=True)
        if not mod_pls(m.from_user.id, m.message.chat.id):
            return m.answer(f"{k} هذا الزر يخص ( المدير وفوق ) بس", show_alert=True)
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            protection_header_text(k, page),
            rows=build_protection_rows(m.message.chat.id, page, uid),
        )
        return

    if m.data.startswith("protH:"):
        parts = m.data.split(":")
        uid = int(parts[1])
        if m.from_user.id != uid:
            return m.answer(f"{k} هذه القائمة مش ليك", show_alert=True)
        try:
            m.message.delete()
        except Exception:
            pass
        return
    # ============================================================

    if m.data == f"commands1:{m.from_user.id}":
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            f"""
للاستفسار - @{channel}


❨ اوامر الرفع والتنزيل ❩

⌯ رفع ↣ ↢ تنزيل مشرف
⌯ رفع ↣ ↢ تنزيل مالك اساسي
⌯ رفع ↣ ↢ تنزيل مالك
⌯ رفع ↣ ↢ تنزيل مدير
⌯ رفع ↣ ↢ تنزيل ادمن
⌯ رفع ↣ ↢ تنزيل مميز
⌯ تنزيل الكل  ↢ بالرد  ↢ لتنزيل الشخص من جميع رتبه
⌯ مسح الكل  ↢ بدون رد  ↢ لتنزيل كل رتب المجموعة

❨ اوامر المسح ❩

⌯ مسح المالكيين
⌯ مسح المدراء
⌯ مسح الادمنيه
⌯ مسح المميزين
⌯ مسح المحظورين
⌯ مسح المكتومين
⌯ مسح قائمة المنع
⌯ مسح رتبه
⌯ مسح الرتب
⌯ مسح الردود
⌯ مسح الاوامر
⌯ مسح + العدد
⌯ مسح بالرد
⌯ مسح الترحيب
⌯ مسح قائمة التثبيت

❨ اوامر الطرد الحظر الكتم ❩

⌯ حظر ↢ ❨ بالرد،بالمعرف،بالايدي ❩
⌯ طرد ↢ ❨ بالرد،بالمعرف،بالايدي ❩
⌯ كتم ↢ ❨ بالرد،بالمعرف،بالايدي ❩
⌯ تقيد ↢ ❨ بالرد،بالمعرف،بالايدي ❩
⌯ الغاء الحظر ↢ ❨ بالرد،بالمعرف،بالايدي ❩
⌯ الغاء الكتم ↢ ❨ بالرد،بالمعرف،بالايدي ❩
⌯ الغاء التقييد ↢ ❨ بالرد،بالمعرف،بالايدي ❩
⌯ رفع القيود ↢ لحذف الكتم,الحظر,التقييد
⌯ منع الكلمة
⌯ منع بالرد على قيف او ستيكر
⌯ الغاء منع الكلمة
⌯ طرد البوتات
⌯ كشف البوتات

❨ اوامر النطق ❩

⌯ انطقي + الكلمة
⌯ وش يقول؟ + بالرد على فويس لترجمه المحتوى

❨ اوامر اخرى ❩

⌯ الرابط
⌯ معلومات الرابط
⌯ انشاء رابط
⌯ بايو
⌯ بايو عشوائي
⌯ ايدي
⌯ الانشاء
⌯ مجموعاتي
⌯ ابلاغ
⌯ نقل ملكية
⌯ صوره
⌯ افتاري
⌯ افتار + باليوزر او الرد
⌯ مين ضافني؟
⌯ شازام، قرآن، سورة + اسم السورة
""",
            rows=commands_menu_rows("commands1", m.from_user.id),
        )
        return

    if m.data == f"commands2:{m.from_user.id}":
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            f"""
للاستفسار - @{channel}


❨ اوامر الوضع ❩

⌯ وضع ترحيب
⌯ وضع قوانين
⌯ تغيير رتبه
⌯ تغيير امر

❨ اوامر رؤية الاعدادات ❩

⌯ المطورين
⌯ المالكيين الاساسيين
⌯ المالكيين
⌯ الادمنيه
⌯ المدراء
⌯ المشرفين
⌯ المميزين
⌯ القوانين
⌯ قائمه المنع
⌯ المكتومين
⌯ المطور
⌯ معلوماتي
⌯ الاعدادت
⌯ المجموعه
⌯ الساعه
⌯ التاريخ
⌯ صلاحياتي
⌯ لقبي
⌯ صلاحياته + بالرد
""",
            rows=commands_menu_rows("commands2", m.from_user.id),
        )
        return

    if m.data == f"commands3:{m.from_user.id}":
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            f"""
للاستفسار - @{channel}


❨ اوامر الردود ❩

⌯ الردود ↢ تشوف كل الردود المضافه
⌯ الردود المتعدده ↢ تشوف كل الردود المتعدده المضافه
⌯ اضف رد ↢ عشان تضيف رد
⌯ اضف رد متعدد ↢ عشان تضيف أكثر من رد
⌯ اضف رد متعدد ↢ خاص بالاعضاء
⌯ مسح رد ↢ عشان تمسح الرد
⌯ مسح رد متعدد ↢ عشان تمسح رد متعدد
⌯ مسح ردي ↢ عشان تمسح ردك اذا كان بردود الأعضاء
⌯ مسح الردود ↢ تمسح كل الردود
⌯ مسح الردود المتعدده ↢ عشان تمسح كل الردود المتعدده
⌯ الرد + كلمة الرد
-

❨ اوامر القفل والفتح بالمسح ❩

⌯ قفل ↣ ↢ فتح  التعديل
⌯ قفل ↣ ↢ فتح  الفويسات
⌯ قفل ↣ ↢ فتح  الفيديو
⌯ قفل ↣ ↢ فتح  الـصــور
⌯ قفل ↣ ↢ فتح  الملصقات
⌯ قفل ↣ ↢ فتح  الدخول
⌯ قفل ↣ ↢ فتح  الفارسية
⌯ قفل ↣ ↢ فتح  الملفات
⌯ قفل ↣ ↢ فتح  المتحركات
⌯ قفل ↣ ↢ فتح  تعديل الميديا
⌯ قفل ↣ ↢ فتح  تعديل الميديا بالتقييد
⌯ قفل ↣ ↢ فتح  الدردشه
⌯ قفل ↣ ↢ فتح  الروابط
⌯ قفل ↣ ↢ فتح  الهشتاق
⌯ قفل ↣ ↢ فتح  البوتات
⌯ قفل ↣ ↢ فتح  اليوزرات
⌯ قفل ↣ ↢ فتح  الاشعارات
⌯ قفل ↣ ↢ فتح  الكلام الكثير
⌯ قفل ↣ ↢ فتح  التكرار
⌯ قفل ↣ ↢ فتح  التوجيه
⌯ قفل ↣ ↢ فتح  الانلاين
⌯ قفل ↣ ↢ فتح  الجهات
⌯ قفل ↣ ↢ فتح  الــكـــل
⌯ قفل ↣ ↢ فتح  السب
⌯ قفل ↣ ↢ فتح  الاضافه
⌯ قفل ↣ ↢ فتح  الصوت
⌯ قفل ↣ ↢ فتح  القنوات
⌯ قفل ↣ ↢ فتح الايراني
⌯ قفل ↣ ↢ فتح الإباحي

❨ اوامر التفعيل والتعطيل ❩

⌯ تفعيل ↣ ↢ تعطيل الترحيب
⌯ تفعيل ↣ ↢ تعطيل الترحيب بالصورة
⌯ تفعيل ↣ ↢ تعطيل الردود
⌯ تفعيل ↣ ↢ تعطيل ردود الاعضاء
⌯ تفعيل ↣ ↢ تعطيل الايدي
⌯ تفعيل ↣ ↢ تعطيل الرابط
⌯ تفعيل ↣ ↢ تعطيل اطردني
⌯ تفعيل ↣ ↢ تعطيل الحماية
⌯ تفعيل ↣ ↢ تعطيل المنشن
⌯ تفعيل ↣ ↢ تعطيل التحقق
⌯ تفعيل ↣ ↢ تعطيل ردود المطور
⌯ تفعيل ↣ ↢ تعطيل التحذير
⌯ تفعيل ↣ ↢ تعطيل البايو
⌯ تفعيل ↣ ↢ تعطيل انطقي
⌯ تفعيل ↣ ↢ تعطيل شازام
""",
            rows=commands_menu_rows("commands3", m.from_user.id),
        )
        return

    if m.data == f"commands4:{m.from_user.id}":
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            """
☤ تفعيل الالعاب
☤ تعطيل الالعاب
    ╼╾
✽ جمل
✽ كلمات
✽ اغاني
✽ دين
✽ عربي
✽ اكمل
✽ صور
✽ كت تويت
✽ مؤقت
✽ اعلام
✽ معاني
✽ تخمين
✽ احكام
✽ ارقام
✽ احسب
✽ خواتم
✽ انقليزي
✽ ترتيب
✽ انمي
✽ تركيب
✽ تفكيك
✽ عواصم
✽ روليت
✽ سيارات
✽ ايموجي
✽ حجره
✽ تشفير
✽ كره قدم
✽ ديمون
╼╾
❖ فلوسي ↼ عشان تشوف فلوسك
❖ بيع فلوسي + العدد ↼ للأستبدال
""",
            rows=commands_menu_rows("commands4", m.from_user.id),
        )
        return

    if m.data == f"commands5:{m.from_user.id}":
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            f"""
للاستفسار - @{channel}

🍰 ⌯ رفع ↣ ↢ تنزيل كيكه
🍯 ⌯ رفع ↣ ↢ تنزيل عسل
💩 ⌯ رفع ↣ ↢ تنزيل زق
🦓 ⌯ رفع ↣ ↢ تنزيل حمار
🐄 ⌯ رفع ↣ ↢ تنزيل بقره
🐩 ⌯ رفع ↣ ↢ تنزيل كلب
🐒 ⌯ رفع ↣ ↢ تنزيل قرد
🐐 ⌯ رفع ↣ ↢ تنزيل تيس
🐂 ⌯ رفع ↣ ↢ تنزيل ثور
🏅 ⌯ رفع ↣ ↢ تنزيل هكر
🐓 ⌯ رفع ↣ ↢ تنزيل دجاجه
🧱 ⌯ رفع ↣ ↢ تنزيل ملكه
🔫 ⌯ رفع ↣ ↢ تنزيل صياد
🐏 ⌯ رفع ↣ ↢ تنزيل خاروف
❤️ ⌯ رفع لقلبي ↣ ↢ تنزيل من قلبي

⌯ قائمة الكيك
⌯ قائمة العسل
⌯ قائمة الزق
⌯ قائمة الحمير
⌯ قائمة البقر
⌯ قائمة الكلاب
⌯ قائمة القرود
⌯ قائمة التيس
⌯ قائمة الثور
⌯ قائمة الهكر
⌯ قائمة الدجاج
⌯ قائمة الهطوف
⌯ قائمة الصيادين
⌯ قائمة الخرفان
""",
            rows=commands_menu_rows("commands5", m.from_user.id),
        )
        return

    if m.data == f"commands6:{m.from_user.id}":
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            """
⚘ اليـوتيوب

تفعيل اليوتيوب
تعطيل اليوتيوب

❋ البـحث عن اغنية ↓

بحث اسم الاغنية

يوت اسم الاغنية
⚘ الساوند كلاود

تفعيل الساوند
تعطيل الساوند

❋ البـحث عن اغنية ↓

رابط الاغنية أو ساوند + اسم الاغنية


⚘ التيك توك

تفعيل التيك
تعطيل للتيك

❋ للتحميل من التيك ↓

تيك ورابط المقطع
""",
            rows=commands_menu_rows("commands6", m.from_user.id),
        )
        return

    if m.data == f"commands7:{m.from_user.id}":
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            """
✜ اوامر البنك

⌯ انشاء حساب بنكي  ↢ تسوي حساب وتقدر تحول فلوس مع مزايا ثانيه

⌯ مسح حساب بنكي  ↢ تلغي حسابك البنكي

⌯ تحويل ↢ تطلب رقم حساب الشخص وتحول له فلوس

⌯ حسابي  ↢ يطلع لك رقم حسابك عشان تعطيه للشخص اللي بيحول لك

⌯ فلوسي ↢ يعلمك كم فلوسك

⌯ راتب ↢ يعطيك راتبك كل ٥ دقيقة

⌯ بخشيش ↢ يعطيك بخشيش كل ٥ دقايق

⌯ زرف ↢ تزرف فلوس اشخاص كل ٥ دقايق

⌯ كنز ↢ يعطيك كنز كل ١٠ دقايق

⌯ استثمار ↢ تستثمر بالمبلغ اللي تبيه مع نسبة ربح مضمونه من ١٪؜ الى ١٥٪؜ ( او استثمار فلوسي )

⌯ حظ ↢ تلعبها بأي مبلغ ياتدبله ياتخسره انت وحظك ( او حظ فلوسي )

⌯ عجله ↢ تلعب عجله الحظ ولو تشابهو ال ٣ ايموجيات تكسب من ١٠٠ الف لحد ٣٠٠ الف انت وحظك

⌯ توب الفلوس ↢ يطلع توب اكثر ناس معهم فلوس بكل القروبات

⌯ توب الحراميه ↢ يطلع لك اكثر ناس زرفوا
""",
            rows=commands_menu_rows("commands7", m.from_user.id),
        )
        return

    if m.data == f"commands8:{m.from_user.id}":
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            """
✜ اوامر الزواج

⌯ زواج  ↢ تكتبه بالرد على رسالة شخص مع المهر ويزوجك

⌯ زواجي  ↢ يطلع وثيقة زواجك اذا متزوج

⌯ طلاق ↢ يطلقك اذا متزوج

⌯ خلع  ↢ يخلع زوجك ويرجع له المهر

⌯ زواجات ↢ يطلع اغلى الزواجات بالقروب
""",
            rows=commands_menu_rows("commands8", m.from_user.id),
        )
        return

    if m.data == f"commands9:{m.from_user.id}":
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            """
✜ اوامر الميوزك

⌯  تشغيل ↢ شغل

⌯  فيديو ↢ فيد

⌯  ايقاف ↢ لايقاف التشغيل 

⌯ تخطي  ↢ لتخطي الاغنيه

⌯  وقف ↢ لايقاف التشغيل مؤقتا

⌯   كمل ↢ لاستئناف التشغيل 

⌯  مرر ↢ لتقديم الاغنيه بالثواني

⌯  رجع ↢ لارجاع الاغنيه بالثواني

⌯  يوت ↢ لتحميل مقطع صوتي

⌯ كرر ↢ لعمل تكرار للمقطع الذي يعمل 

⌯ مين مشغل ↢ لمعرفت من قام بطلب الاغنيه
⌯  مين في الكول ↢ لمعرف الاشخاص في المكالمه الصوتيه
""",
            rows=commands_menu_rows("commands9", m.from_user.id),
        )
        return

    # ============================================================
    # قسم "المطور" — الزر متاح للجميع، لكن المحتوى مقفول إلا على المطورين
    # أي عضو عادي يضغط عليه ياخذ تنبيه فقط، والمطور (dev_pls) يفتحله القسم
    # ============================================================
    if m.data.startswith("commands10:"):
        if not dev_pls(m.from_user.id, m.message.chat.id):
            return m.answer(f"{k} ما تلعبش في حاجة مش بتاعتك", show_alert=True)
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            """
❨ اوامر المطور ❩

⌯ رفع مطور اساسي (بيوزر/آيدي) ↢ رفع حد مطور اساسي

⌯ تنزيل مطور اساسي (بالرد) ↢ تنزيل مطور اساسي

⌯ رفع/تنزيل مطور ثانوي (بالرد) ↢ رفع أو تنزيل مطور ثانوي

⌯ المطورين الأساسيين/الثانويين + مسحهم ↢ عرض أو حذف قوائم المطورين

⌯ قائمه مطور اساسي/ثانوي + مسحها ↢ عرض أو حذف نفس القوائم بصيغة تانية

⌯ المالكين الاساسيين + مسحهم ↢ عرض أو حذف كل المالكين الأساسيين

⌯ تغيير المطور الاساسي ↢ استبدال آيدي المطور الأساسي للبوت

⌯ تفعيل/تعطيل البوت الخدمي ↢ تشغيل أو إيقاف البوت بالكامل

⌯ تفعيل/تعطيل التحميل واليوتيوب ↢ تشغيل أو إيقاف أوامر التحميل

⌯ تفعيل/تعطيل الميوزك ↢ تشغيل أو إيقاف أوامر الميوزك

⌯ تغيير الحد [دقايق] ↢ أقصى مدة مسموحة لتشغيل مقطع بالميوزك

⌯ تفعيل/تعطيل الاشتراك ↢ تشغيل أو إيقاف الاشتراك الإجباري

⌯ قناة الاشتراك / وضع قناة @ ↢ عرض أو تحديد قناة الاشتراك الإجباري

⌯ اسم البوت + تعيين/مسح ↢ عرض أو تغيير اسم البوت

⌯ رمز السورس + وضع/مسح ↢ عرض أو تغيير رمز السورس

⌯ قناة السورس + وضع/مسح ↢ عرض أو تغيير قناة السورس

⌯ مجموعة المطور + وضع/مسح ↢ تحديد جروب استقبال الإشعارات

⌯ رابط [آيدي] ↢ يجيب رابط دعوة أي جروب بالآيدي

⌯ اذاعة بالخاص/بالمجموعات/بالقنوات (+تثبيت) ↢ رسالة جماعية حسب النوع

⌯ اذاعة عام ↢ رسالة لكل حاجة مع بعض دفعة واحدة

⌯ جلب نسخة القروبات/المستخدمين/القنوات ↢ تصدير قوائم بيانات البوت

⌯ الردود العامه + اضف/مسح ↢ ردود تلقائية على مستوى كل الجروبات

⌯ الردود المتعدده العامه + اضف/مسح ↢ زي الردود العامة بس لأكتر من كلمة

⌯ الاوامر العامه + اضف/تغيير/مسح ↢ أوامر مخصصة على كل الجروبات

⌯ اضف/مسح ميزة ↢ إضافة أو حذف ميزة مخصصة للبوت

⌯ المميزات المضافه ↢ عرض كل الميزات المخصصة المضافة

⌯ استبدال كلمة ↢ استبدال كلمة معينة بكلمة تانية في كل رد

⌯ كتم/حظر عام + الغاء ↢ كتم أو حظر شخص من كل الجروبات مع بعض

⌯ حظر عام من الالعاب + الغاء ↢ منع شخص من ألعاب البوت في كل مكان

⌯ المحظورين/المكتومين عام + مسح ↢ عرض أو مسح قوائم الحظر/الكتم العامة

⌯ المحظورين من الالعاب / المجموعات المحظورة ↢ قوائم عرض إضافية

⌯ وضع/مسح ترحيب عام ↢ ترحيب موحد يشتغل على كل الجروبات

⌯ تعيين/مسح الايدي عام ↢ التحكم في كارت الايدي على مستوى الكل

⌯ تفعيل/تعطيل ايدي الادمن ↢ اظهار أو اخفاء بيانات ادمن الجروب بالكارت

⌯ اضف/مسح عدد لايكات (بالرد) ↢ زيادة أو مسح لايكات وهمية لشخص

⌯ تصفير لايكاته / الغاء تصفير لايكاته ↢ تصفير كل لايكات شخص أو استرجاعها

⌯ تصفير/مسح القروبات ↢ تصفير قائمة توب القروبات الأكثر تفاعلاً

⌯ الاحصائيات ↢ إحصائيات عامة عن البوت (جروبات/مستخدمين/قنوات)

⌯ تحديث ↢ تحديث كود البوت من المصدر

⌯ السيرفر / معلومات السيرفر ↢ حالة السيرفر (رامات/معالج/تخزين)

⌯ الملفات ↢ عرض حجم واستخدام ملفات البوت

⌯ جلب السجل ↢ إرسال ملف سجل تشغيل البوت (لوج)

⌯ /eval ↢ تنفيذ كود بايثون مباشر (للمطور الأساسي بس)
""",
            rows=commands_menu_rows("commands10", m.from_user.id),
        )
        return

    if m.data == f"commandsback:{m.from_user.id}":
        channel = (
            r.get(f"{Dev_Zaid}:BotChannel")
            if r.get(f"{Dev_Zaid}:BotChannel")
            else "YQYQY6"
        )
        edit_colored_message(
            c,
            m.message.chat.id,
            m.message.id,
            f"{k} اهلين فيك باوامر البوت\n\nللاستفسار - @{channel}\n\n{commands_menu_list_text()}",
            rows=commands_menu_rows(None, m.from_user.id),
        )
        return

    if m.data == "delAdminMSG":
        if str(m.from_user.id) in m.message.text.html:
            return m.message.delete()

    if m.data == f"yes:{m.from_user.id}":
        try:
            c.restrict_chat_member(
                m.message.chat.id,
                m.from_user.id,
                ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_send_polls=True,
                    can_invite_users=True,
                    can_add_web_page_previews=True,
                    can_change_info=True,
                    can_pin_messages=True,
                ),
            )
        except:
            return False
        edit_colored_message(
                c, m.message.chat.id, m.message.id,            f"""
{k} تم التحقق منك وطلعت مو زومبي
{k} الحين تقدر تسولف بالقروب
☆
""",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🧚‍♀️", url=f"t.me/{channel}")]]
            ),
        )

    if m.data == f"no:{m.from_user.id}":
        return m.edit_message_text(
            f"""
{k} للأسف طلعت زومبي 🧟‍♀️
{k} مالك غير تنطر حد من المشرفين يجي يتوسطلك
☆
""",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "رفع التقييد والسماح",
                            callback_data=f"yesVER:{m.from_user.id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "طرد", callback_data=f"noVER:{m.from_user.id}"
                        )
                    ],
                ]
            ),
        )

    if m.data.startswith("yesVER"):
        user_id = int(m.data.split(":")[1])
        if not admin_pls(m.from_user.id, m.message.chat.id, c):
            return m.answer(f"{k} هذا الزر يخص ( الادمن وفوق ) بس", show_alert=True)
        else:
            m.edit_message_text(f"{k} توسطلك واحد من الادمن ورفعت عنك القيود")
            try:
                c.restrict_chat_member(
                    m.message.chat.id,
                    user_id,
                    ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_other_messages=True,
                        can_send_polls=True,
                        can_invite_users=True,
                        can_add_web_page_previews=True,
                        can_change_info=True,
                        can_pin_messages=True,
                    ),
                )
            except:
                return False

    if m.data.startswith("noVER"):
        user_id = int(m.data.split(":")[1])
        if not admin_pls(m.from_user.id, m.message.chat.id, c):
            return m.answer(f"{k} هذا الزر يخص ( الادمن وفوق ) بس", show_alert=True)
        else:
            m.edit_message_text(f"{k} انقلع برا القروب يلا")
            try:
                m.message.chat.ban_member(user_id)
                m.message.chat.unban_member(user_id)
            except:
                pass

    if m.data == "yes:del:bank":
        if not devp_pls(m.from_user.id, m.message.chat.id):
            return m.answer("تعجبني ثقتك")
        else:
            m.edit_message_text("ابشر صفرت البنك")
            keys = r.keys("*:Floos")
            for a in keys:
                r.delete(a)
            for a in r.keys("*:BankWait"):
                r.delete(a)
            for a in r.keys("*:BankWaitB5"):
                r.delete(a)
            for a in r.keys("*:BankWaitZRF"):
                r.delete(a)
            for a in r.keys("*:BankWaitEST"):
                r.delete(a)
            for a in r.keys("*:BankWaitHZ"):
                r.delete(a)
            for a in r.keys("*:BankWait3JL"):
                r.delete(a)
            for a in r.keys("*:Zrf"):
                r.delete(a)
            r.delete("BankTop")
            r.delete("BankTopZRF")
            return True

    if m.data == "no:del:bank":
        if not devp_pls(m.from_user.id, m.message.chat.id):
            return m.answer("تعجبني ثقتك")
        else:
            m.message.delete()

    if m.data == f"topfloos:{m.from_user.id}":
        if not r.smembers("BankList"):
            return m.answer(f"{k} مافيه حسابات بالبنك", show_alert=True)
        else:
            rep = [
                [
                    {"text": "‣ 💸", "callback_data": "None"},
                    {
                        "text": "توب الحرامية 💰",
                        "callback_data": f"topzrf:{m.from_user.id}",
                        "style": "primary",
                    },
                ],
                [{"text": "🧚‍♀️", "url": f"t.me/{channel}", "style": "primary"}],
            ]
            if r.get("BankTop"):
                text = r.get("BankTop")
                if not r.get(f"{m.from_user.id}:Floos"):
                    floos = 0
                else:
                    floos = int(r.get(f"{m.from_user.id}:Floos"))
                get = r.ttl("BankTop")
                wait = time.strftime("%M:%S", time.gmtime(get))
                text += "\n━━━━━━━━━"
                text += f"\n# You ) {floos:,} 💸 l {m.from_user.first_name}"
                text += f"\n\n[قوانين التُوب](https://t.me/{botUsername}?start=rules)"
                text += f"\n\nالقائمة تتحدث بعد {wait} دقيقة"
                return edit_colored_message(
                    c, m.message.chat.id, m.message.id, text, rows=rep, disable_web_page_preview=True
                )
            else:
                users = []
                ccc = 0
                for user in r.smembers("BankList"):
                    ccc += 1
                    id = int(user)
                    if r.get(f"{id}:bankName"):
                        name = r.get(f"{id}:bankName")[:10]
                    else:
                        try:
                            name = c.get_chat(id).first_name
                            r.set(f"{id}:bankName", name)
                        except:
                            name = "INVALID_NAME"
                            r.set(f"{id}:bankName", name)
                    if not r.get(f"{id}:Floos"):
                        floos = 0
                    else:
                        floos = int(r.get(f"{id}:Floos"))
                    users.append({"name": name, "money": floos})
                top = get_top(users)
                text = "توب 20 اغنى اشخاص:\n\n"
                count = 0
                for user in top:
                    count += 1
                    if count == 21:
                        break
                    emoji = get_emoji_bank(count)
                    floos = user["money"]
                    name = user["name"]
                    text += f'**{emoji}{floos:,}** 💸 l {name.replace("*","").replace("`","").replace("|","").replace("#","").replace("<","").replace(">","").replace("_","")}\n'
                r.set("BankTop", text, ex=300)
                if not r.get(f"{m.from_user.id}:Floos"):
                    floos_from_user = 0
                else:
                    floos_from_user = int(r.get(f"{m.from_user.id}:Floos"))
                text += "\n━━━━━━━━━"
                text += f"\n# You ) {floos_from_user:,} 💸 l {m.from_user.first_name}"
                text += f"\n\n[قوانين التُوب](https://t.me/{botUsername}?start=rules)"
                get = r.ttl("BankTop")
                wait = time.strftime("%M:%S", time.gmtime(get))
                text += f"\n\nالقائمة تتحدث بعد {wait} دقيقة"
                edit_colored_message(
                    c, m.message.chat.id, m.message.id, text, rows=rep, disable_web_page_preview=True
                )

    if m.data == f"topzrf:{m.from_user.id}":
        if not r.smembers("BankList"):
            return m.answer(f"{k} مافيه حسابات بالبنك", show_alert=True)
        else:
            rep = [
                [
                    {
                        "text": "توب الفلوس 💸",
                        "callback_data": f"topfloos:{m.from_user.id}",
                        "style": "primary",
                    },
                    {"text": "‣ 💰", "callback_data": "None"},
                ],
                [{"text": "🧚‍♀️", "url": f"t.me/{channel}", "style": "primary"}],
            ]
            if r.get("BankTopZRF"):
                text = r.get("BankTopZRF")
                if not r.get(f"{m.from_user.id}:Zrf"):
                    zrf = 0
                else:
                    zrf = int(r.get(f"{m.from_user.id}:Zrf"))
                get = r.ttl("BankTopZRF")
                wait = time.strftime("%M:%S", time.gmtime(get))
                text += "\n━━━━━━━━━"
                text += f"\n# You ) {zrf:,} 💰 l {m.from_user.first_name}"
                text += f"\n\n[قوانين التُوب](https://t.me/{botUsername}?start=rules)"
                text += f"\n\nالقائمة تتحدث بعد {wait} دقيقة"
                return edit_colored_message(
                    c, m.message.chat.id, m.message.id, text, rows=rep, disable_web_page_preview=True
                )
            else:
                users = []
                ccc = 0
                for user in r.smembers("BankList"):
                    ccc += 1
                    id = int(user)
                    if r.get(f"{id}:bankName"):
                        name = r.get(f"{id}:bankName")[:10]
                    else:
                        try:
                            name = c.get_chat(id).first_name
                            r.set(f"{id}:bankName", name)
                        except:
                            name = "INVALID_NAME"
                            r.set(f"{id}:bankName", name)
                    if not r.get(f"{id}:Zrf"):
                        pass
                    else:
                        zrf = int(r.get(f"{id}:Zrf"))
                        users.append({"name": name, "money": zrf})
                top = get_top(users)
                text = "توب 20 اكثر الحراميه زرفًا:\n\n"
                count = 0
                for user in top:
                    count += 1
                    if count == 21:
                        break
                    emoji = get_emoji_bank(count)
                    floos = user["money"]
                    name = user["name"]
                    text += f'**{emoji}{floos}** 💰 l {name.replace("*","").replace("`","").replace("|","").replace("#","").replace("<","").replace(">","").replace("_","")}\n'
                r.set("BankTopZRF", text, ex=300)
                if not r.get(f"{m.from_user.id}:Zrf"):
                    floos_from_user = 0
                else:
                    floos_from_user = int(r.get(f"{m.from_user.id}:Zrf"))
                text += "\n━━━━━━━━━"
                text += f"\n# You ) {floos_from_user} 💰 l {m.from_user.first_name}"
                text += f"\n\n[قوانين التُوب](https://t.me/{botUsername}?start=rules)"
                get = r.ttl("BankTopZRF")
                wait = time.strftime("%M:%S", time.gmtime(get))
                text += f"\n\nالقائمة تتحدث بعد {wait} دقيقة"
                edit_colored_message(
                    c, m.message.chat.id, m.message.id, text, rows=rep, disable_web_page_preview=True
                )

    """
   if m.data == f'toplast:{m.from_user.id}':
     if not r.get(f'BankTopLast') and not r.get(f'BankTopLastZrf'):
       return m.answer(f'{k} مافي توب اسبوع الي فات',show_alert=True)
     else:
       text = 'توب أوائل الأسبوع الي راح:\n'
       text += r.get(f'BankTopLast')
       text += '\n\nتوب حرامية الاسبوع اللي راح:\n'
       text += r.get(f'BankTopLastZrf')
       text += '\n༄'
       rep = InlineKeyboardMarkup (
         [[InlineKeyboardButton ('🧚‍♀️', url=f't.me/{channel}')]]
       )
       edit_colored_message(c, m.message.chat.id, m.message.id, text, rows=rep, disable_web_page_preview=True)
   """

    name = r.get(f"{Dev_Zaid}:BotName") if r.get(f"{Dev_Zaid}:BotName") else "رعد"
    if m.data == f"RPS:rock++{m.from_user.id}":
        RPS = ["paper", "scissors", "rock"]
        kk = random.choice(RPS)
        if kk == "scissors":
            if r.get(f"{m.from_user.id}:Floos"):
                get = int(r.get(f"{m.from_user.id}:Floos"))
                r.set(f"{m.from_user.id}:Floos", get + 1)
            else:
                r.set(f"{m.from_user.id}:Floos", 1)
            rep = [[{"text": "🧚‍♀️", "url": f"t.me/{channel}", "style": "primary"}]]
            m.edit_message_text(
                f"""
أنت: 🪨
أنا: ✂️

النتيجة: ⁪⁬⁪⁬ 🏆 {m.from_user.first_name}
""",
                rows=rep,
                disable_web_page_preview=True,
            )

        if kk == "paper":
            rep = [[{"text": "🧚‍♀️", "url": f"t.me/{channel}", "style": "primary"}]]
            edit_colored_message(
                c, m.message.chat.id, m.message.id,                f"""
أنت: 🪨
أنا: 📃

النتيجة: ⁪⁬⁪⁬ 🏆️ {name.replace("*","").replace("`","").replace("|","").replace("#","").replace("<","").replace(">","").replace("_","")}
""",
                rows=rep,
                disable_web_page_preview=True,
            )
        if kk == "rock":
            rep = [[{"text": "🧚‍♀️", "url": f"t.me/{channel}", "style": "primary"}]]
            edit_colored_message(
                c, m.message.chat.id, m.message.id,                f"""
أنت: 🪨
أنا: 🪨

النتيجة: ⁪⁬⁪⁬ ⚖️ {name.replace("*","").replace("`","").replace("|","").replace("#","").replace("<","").replace(">","").replace("_","")}
""",
                rows=rep,
                disable_web_page_preview=True,
            )

    if m.data == f"gowner+{m.from_user.id}":
        if not gowner_pls(m.from_user.id, m.message.chat.id):
            m.asnwer("هذا الامر للمالك الاساسي و فوق بس", show_alert=True)
            return m.message.delete()
        else:
            command = m.message.reply_to_message.text.split(None, 2)[2]
            r.hset(Dev_Zaid + f"locks-{m.message.chat.id}", command, 0)
            return edit_colored_message(
                c, m.message.chat.id, m.message.id,                f"- تم تعيين الامر ( {command} ) للمالك الاساسي وفوق فقط"
            )

    if m.data == f"owner+{m.from_user.id}":
        if not gowner_pls(m.from_user.id, m.message.chat.id):
            m.asnwer("هذا الامر للمالك الاساسي و فوق بس", show_alert=True)
            return m.message.delete()
        else:
            command = m.message.reply_to_message.text.split(None, 2)[2]
            r.hset(Dev_Zaid + f"locks-{m.message.chat.id}", command, 1)
            return m.edit_message_text(
                f"- تم تعيين الامر ( {command} ) للمالك وفوق فقط"
            )

    if m.data == f"mod+{m.from_user.id}":
        if not gowner_pls(m.from_user.id, m.message.chat.id):
            m.asnwer("هذا الامر للمالك الاساسي و فوق بس", show_alert=True)
            return m.message.delete()
        else:
            command = m.message.reply_to_message.text.split(None, 2)[2]
            r.hset(Dev_Zaid + f"locks-{m.message.chat.id}", command, 2)
            return m.edit_message_text(
                f"- تم تعيين الامر ( {command} ) للمدير وفوق فقط"
            )

    if m.data == f"admin+{m.from_user.id}":
        if not gowner_pls(m.from_user.id, m.message.chat.id):
            m.asnwer("هذا الامر للمالك الاساسي و فوق بس", show_alert=True)
            return m.message.delete()
        else:
            command = m.message.reply_to_message.text.split(None, 2)[2]
            r.hset(Dev_Zaid + f"locks-{m.message.chat.id}", command, 3)
            return m.edit_message_text(
                f"- تم تعيين الامر ( {command} ) للادمن وفوق فقط"
            )

    if m.data == f"pre+{m.from_user.id}":
        if not gowner_pls(m.from_user.id, m.message.chat.id):
            m.asnwer("هذا الامر للمالك الاساسي و فوق بس", show_alert=True)
            return m.message.delete()
        else:
            command = m.message.reply_to_message.text.split(None, 2)[2]
            r.hset(Dev_Zaid + f"locks-{m.message.chat.id}", command, 4)
            return m.edit_message_text(
                f"- تم تعيين الامر ( {command} ) للمميز وفوق فقط"
            )

    if m.data == f"RPS:paper++{m.from_user.id}":
        RPS = ["paper", "scissors", "rock"]
        kk = random.choice(RPS)
        if kk == "rock":
            if r.get(f"{m.from_user.id}:Floos"):
                get = int(r.get(f"{m.from_user.id}:Floos"))
                r.set(f"{m.from_user.id}:Floos", get + 1)
            else:
                r.set(f"{m.from_user.id}:Floos", 1)
            rep = [[{"text": "🧚‍♀️", "url": f"t.me/{channel}", "style": "primary"}]]
            m.edit_message_text(
                f"""
أنت: 📃
أنا: 🪨

النتيجة: ⁪⁬⁪⁬ 🏆 {m.from_user.first_name}
""",
                rows=rep,
                disable_web_page_preview=True,
            )

        if kk == "scissors":
            rep = [[{"text": "🧚‍♀️", "url": f"t.me/{channel}", "style": "primary"}]]
            edit_colored_message(
                c, m.message.chat.id, m.message.id,                f"""
أنت: 📃
أنا: ✂️

النتيجة: ⁪⁬⁪⁬ 🏆️ {name.replace("*","").replace("`","").replace("|","").replace("#","").replace("<","").replace(">","").replace("_","")}
""",
                rows=rep,
                disable_web_page_preview=True,
            )
        if kk == "paper":
            rep = [[{"text": "🧚‍♀️", "url": f"t.me/{channel}", "style": "primary"}]]
            edit_colored_message(
                c, m.message.chat.id, m.message.id,                f"""
أنت: 📃
أنا: 📃

النتيجة: ⁪⁬⁪⁬ ⚖️ {name.replace("*","").replace("`","").replace("|","").replace("#","").replace("<","").replace(">","").replace("_","")}
""",
                rows=rep,
                disable_web_page_preview=True,
            )

    if m.data == f"RPS:scissors++{m.from_user.id}":
        RPS = ["paper", "scissors", "rock"]
        kk = random.choice(RPS)
        if kk == "paper":
            if r.get(f"{m.from_user.id}:Floos"):
                get = int(r.get(f"{m.from_user.id}:Floos"))
                r.set(f"{m.from_user.id}:Floos", get + 1)
            else:
                r.set(f"{m.from_user.id}:Floos", 1)
            rep = [[{"text": "🧚‍♀️", "url": f"t.me/{channel}", "style": "primary"}]]
            edit_colored_message(
                c, m.message.chat.id, m.message.id,                f"""
أنت: ✂️
أنا: 📃

النتيجة: ⁪⁬⁪⁬ 🏆 {m.from_user.first_name}
""",
                rows=rep,
                disable_web_page_preview=True,
            )

        if kk == "rock":
            rep = [[{"text": "🧚‍♀️", "url": f"t.me/{channel}", "style": "primary"}]]
            edit_colored_message(
                c, m.message.chat.id, m.message.id,                f"""
أنت: ✂️
أنا: 🪨

النتيجة: ⁪⁬⁪⁬ 🏆️ {name.replace("*","").replace("`","").replace("|","").replace("#","").replace("<","").replace(">","").replace("_","")}
""",
                rows=rep,
                disable_web_page_preview=True,
            )
        if kk == "scissors":
            rep = [[{"text": "🧚‍♀️", "url": f"t.me/{channel}", "style": "primary"}]]
            edit_colored_message(
                c, m.message.chat.id, m.message.id,                f"""
أنت: ✂️
أنا: ✂️

النتيجة: ⁪⁬⁪⁬ ⚖️ {name.replace("*","").replace("`","").replace("|","").replace("#","").replace("<","").replace(">","").replace("_","")}
""",
                rows=rep,
                disable_web_page_preview=True,
            )
