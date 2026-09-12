# ============================================================
# Plugins/music.py - أوامر الميوزك
# يشتغل مع البوت الأساسي (main.py)
# ============================================================

import os
import re
import io
import time
import asyncio
import json
import sys
import traceback
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType, ChatMemberStatus, ParseMode
from pyrogram.errors import UserNotParticipant, FloodWait
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import FloodWaitError
try:
    from telethon.errors import InviteRequestSentError
except ImportError:
    class InviteRequestSentError(Exception):
        pass
from pytgcalls.types import MediaStream, StreamEnded
try:
    from pytgcalls.exceptions import NoActiveGroupCall, GroupCallNotFoundError
except ImportError:
    class NoActiveGroupCall(Exception):
        pass
    class GroupCallNotFoundError(Exception):
        pass

# ===== استيراد كل المتغيرات من config.py =====
from config import *
from helpers.Ranks import dev_pls, mod_pls, admin_pls

# ===== جيب call_py و assistant_id و assistant_client من البوت الأساسي =====
def get_assistant(chat_id=None):
    main_module = sys.modules.get('__main__')
    if not main_module:
        return None, None, None
    return (
        getattr(main_module, 'call_py', None),
        getattr(main_module, 'assistant_id', None),
        getattr(main_module, 'assistant_client', None),
    )


def release_assistant(chat_id):
    pass


call_py, assistant_id, assistant_client = get_assistant()

# ============================================================
# دعم نظام "تغيير امر" / "تغيير امر عام" لأوامر الميوزك
# ============================================================
def _translate_command_word(m, word):
    chat_id = m.chat.id if m.chat else None
    if chat_id and r.get(f'{chat_id}:Custom:{chat_id}{Dev_Zaid}&text={word}'):
        word = r.get(f'{chat_id}:Custom:{chat_id}{Dev_Zaid}&text={word}')
    if r.get(f'Custom:{Dev_Zaid}&text={word}'):
        word = r.get(f'Custom:{Dev_Zaid}&text={word}')
    return word

def _translate_full_text(m, text):
    # نفس نظام "تغيير امر" بس على مستوى الجملة كاملة، عشان الأوامر اللي
    # من غير معطيات زي "مين في الكول" / "مين مشغل" / "التحكم" تقبل التغيير برضه
    chat_id = m.chat.id if m.chat else None
    if chat_id and r.get(f'{chat_id}:Custom:{chat_id}{Dev_Zaid}&text={text}'):
        return r.get(f'{chat_id}:Custom:{chat_id}{Dev_Zaid}&text={text}')
    if r.get(f'Custom:{Dev_Zaid}&text={text}'):
        return r.get(f'Custom:{Dev_Zaid}&text={text}')
    return text

def music_command(keywords):
    async def func(flt, c, m):
        if not m.text:
            return False
        # ===== السماح للأشخاص العاديين + منشورات القنوات المباشرة، ورفض
        # أي حاجة وسيطة زي البوتات أو رسائل مُعاد توجيهها تلقائيًا من قناة
        # لجروب متربط بيها، أو أدمن بعت بصفة الجروب نفسه (anonymous admin) =====
        if getattr(m.chat, "type", None) == ChatType.CHANNEL:
            # منشور مباشر جوه قناة - مفيش from_user أصلاً في القنوات (ده طبيعي)،
            # فبنسمح بيه هنا، واسم الناشر (لو القناة شغالة عندها "توقيع
            # الرسائل") بييجي بعدين من author_signature في get_user_mention
            pass
        else:
            if not m.from_user:
                return False
            if m.from_user.is_bot:
                return False
            if getattr(m, "sender_chat", None):
                return False
        text = m.text.strip()
        for p in ("/", "!"):
            if text.startswith(p):
                text = text[len(p):]
                break
        if not text:
            return False

        matched = False
        # ١) ترجمة الجملة كاملة (للأوامر من غير معطيات زي "مين في الكول")
        if _translate_full_text(m, text) in flt.keywords:
            matched = True
        else:
            # ٢) ترجمة أول كلمة بس (للأوامر اللي بتاخد معطيات زي "تشغيل اسم الاغنية")
            parts = text.split(None, 1)
            if parts:
                first_word = _translate_command_word(m, parts[0])
                matched = first_word in flt.keywords

        if matched:
            # مسح رسالة الأمر نفسها فور ما نتأكد إنها أمر ميوزك صحيح، قبل
            # ما الـ handler ينفذ - كده الشات يفضل نضيف من أوامر الميوزك
            try:
                await m.delete()
            except Exception:
                pass

        return matched
    return filters.create(func, keywords=keywords)

# ===== متغيرات التشغيل =====
music_queue = {}
current_playing = {}
is_playing_now = {}
playback_start_time = {}
playback_offset = {}
is_paused = {}  # chat_id -> هل البث متوقف مؤقتاً حاليًا (عشان منمنعش ضغط وقف/كمل مرتين)
is_seeking = {}
repeat_mode = {}
call_start_time = {}
changing_stream = {}  # متغير لمنع تداخل حدث StreamEnded أثناء التخطي
playing_messages = {}  # متغير لتخزين آيديات رسائل التشغيل عشان نمسحها عند الإيقاف

# ============================================================
# لما حد يكتب أمر تشغيل/شغل/فيديو/فيد/يوت/تحميل من غير ما يكتب اسم بعده،
# بدل رسالة خطأ بس، بنسأله "عايز تشغل إيه؟" ونستنى رده - أي رسالة نصية
# جاية منه بعد كده (في نفس المحادثة) بتتحسب هي الاسم المطلوب تلقائيًا.
# ده Dict بسيط (chat_id, user_id) -> نوع الأمر المعلّق، مش قائمة انتظار
# حقيقية معقدة، فمحتاج نضبط وقت صلاحية عشان لو الشخص اتلهى ومردش، الحالة
# متفضلش عالقة للأبد وتاخد رسالة تانية غلط بالغلط.
# ============================================================
pending_music_request = {}
PENDING_QUERY_TIMEOUT = 90  # ثانية

_PENDING_KIND_KEYWORD = {
    "play": "تشغيل",
    "video": "فيديو",
    "yt": "يوت",
    "download": "تحميل",
}

_PENDING_KIND_PROMPT = {
    "play": "عايز تشغل ايه",
    "video": "عايز تشغل ايه",
    "yt": "عايز تحمل ايه",
    "download": "عايز تحمل ايه",
}

async def _ask_for_query(message, kind):
    # لازم نسجل آيدي الرسالة اللي هي نفسها سبب السؤال (زي "تشغيل" لوحدها) -
    # عشان لما نفحص أي رسالة جاية بعد كده هل هي "رد" على السؤال ده، نستبعد
    # الرسالة دي نفسها بالتحديد. من غيره، تليجرام بيمرر نفس الرسالة على كل
    # الـ handlers المسجلة (بغض النظر عن الترتيب/الأولوية)، فرسالة "تشغيل"
    # نفسها كانت بتوصل تاني لنفس الفحص اللي بيستنى الرد، وبيتعامل معاها
    # وكأنها هي الرد نفسه - فبيشغل حاجة عشوائية من غير ما يستنى المستخدم فعليًا.
    key = (message.chat.id, message.from_user.id if message.from_user else message.chat.id)
    prompt = await message.reply(f"<b>{_PENDING_KIND_PROMPT[kind]}</b>")
    pending_music_request[key] = {
        "kind": kind,
        "expires": time.time() + PENDING_QUERY_TIMEOUT,
        "origin_msg_id": message.id,
        "prompt_msg_id": prompt.id,
    }

CACHE_FILE = "bot_cache.json"
bot_cache = {"audio": {}, "video": {}, "disabled_groups": [], "custom_players": {}}
# الصوت اللي الحساب المساعد بيشغله وقت أمر "مين في الكول" لو مفيش حاجة شغالة.
# لازم نبني المسار كامل (absolute) اعتمادًا على مكان ملف music.py نفسه، مش
# اسم الملف لوحده - عشان لو البوت اتشغل من مجلد تاني (working directory
# مختلف عن مجلد الملفات)، os.path.exists("salam.mp3") كان بيرجع False
# فالمساعد ما كانش بيلاقي الملف أصلاً وبالتالي ما كانش بيدخل الكول ولا
# يشغل حاجة، حتى لو الملف فعليًا موجود جنب music.py.
CALL_RECORD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salam.mp3")

def load_cache():
    global bot_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                bot_cache.update(data)
        except: pass

def save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(bot_cache, f, ensure_ascii=False, indent=4)

load_cache()

# ============================================================
# دوال مساعدة - نفس نظام البوت الأساسي
# ============================================================

def get_user_mention(message):
    if message.from_user:
        name = message.from_user.first_name or "مجهول"
        name = name.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
        return f'<a href="tg://user?id={message.from_user.id}">{name}</a>'
    # القناة عاملة "توقيع الرسائل" (Sign Messages) - Telegram بيرجّع اسم
    # الأدمن الفعلي اللي كتب/شغّل الأمر في author_signature، ده أدق من اسم
    # القناة نفسها فبنقدمه عليه لو موجود.
    sig = getattr(message, "author_signature", None)
    if sig:
        title = sig.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
        chat_ref = message.sender_chat.id if message.sender_chat else message.chat.id
        return f'<a href="tg://user?id={chat_ref}">{title}</a>'
    if message.sender_chat:
        title = message.sender_chat.title or "مجهول"
        title = title.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
        return f'<a href="tg://user?id={message.sender_chat.id}">{title}</a>'
    return "مجهول"

def _format_mmss(seconds):
    seconds = max(0, int(seconds or 0))
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"

def _build_progress_bar_text(elapsed, duration):
    """نص شريط تقدم بسيط بحروف يونيكود، بيتحط داخل زرار بدل ما يكون
    مرسوم في الصورة - عشان يقدر يتحدث لوحده كل ما الأغنية تتحرك، من غير
    ما يحتاج يعيد رسم الصورة كل مرة (ده أسرع وأخف بكتير). عدد رموز
    الشريط ثابت دايمًا (12 رمز) بغض النظر عن مدة الأغنية، عشان حجم
    الزرار يفضل تقريبًا زي ما هو ومايكبرش."""
    BAR_LEN = 7
    duration = duration or 0
    ratio = 0 if duration <= 0 else min(1, max(0, elapsed / duration))
    filled = int(round(ratio * BAR_LEN))
    filled = min(BAR_LEN, filled)
    bar = "▬" * filled + "●" + "▬" * (BAR_LEN - filled)
    return f"{_format_mmss(elapsed)} {bar} {_format_mmss(duration)}"

def get_play_buttons(progress_text=None):
    bottom_row = (
        [{"text": progress_text, "callback_data": "music_progress_noop", "style": "danger"}]
        if progress_text
        else [{"text": "اخفاء القائمة", "callback_data": "music_hide_menu", "style": "danger"}]
    )
    return {
        "inline_keyboard": [
            [
                {"text": "Ⅱ", "callback_data": "music_pause", "style": "primary"},
                {"text": "▷", "callback_data": "music_resume", "style": "primary"},
                {"text": "↻", "callback_data": "music_repeat", "style": "primary"},
                {"text": ">> ", "callback_data": "music_skip", "style": "primary"},
                {"text": "▣", "callback_data": "music_stop", "style": "primary"}
            ],
            [
                {"text": "<<30", "callback_data": "music_back30", "style": "danger"},
                {"text": "<<15", "callback_data": "music_back15", "style": "primary"},
                {"text": "15>>", "callback_data": "music_fwd15", "style": "primary"},
                {"text": "30>>", "callback_data": "music_fwd30", "style": "danger"}
            ],
            bottom_row,
            [
                {"text": "𝐀𝐃𝐃 𝐆𝐑𝐎𝐔𝐏", "url": "https://t.me/H0_VF_BOT?startgroup=true", "style": "success"}
            ]
        ]
    }

def _get_bot_token(client):
    token = getattr(client, "bot_token", None)
    if token:
        return token
    for name in ("BOT_TOKEN", "bot_token", "API_TOKEN", "TOKEN"):
        if name in globals() and globals()[name]:
            return globals()[name]
    return None

def _tg_api_call(client, method, payload):
    token = _get_bot_token(client)
    if not token:
        return None
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            return None
        return resp
    except Exception:
        return None

def _tg_api_call_file(client, method, payload, file_field, file_data):
    """زي _tg_api_call بس بيرفع ملف (multipart) بدل ما يبعته كـ JSON،
    عشان طلبات الـ sendPhoto اللي فيها صورة متولدة (كارت التشغيل) تفضل
    عدية من نفس مسار الـ API الخام وتحافظ على تلوين الأزرار.
    file_data ممكن يكون مسار ملف على القرص (str) أو BytesIO في الذاكرة."""
    token = _get_bot_token(client)
    if not token:
        return None
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        data = {}
        for k, v in payload.items():
            if k == file_field:
                continue
            data[k] = json.dumps(v) if isinstance(v, (dict, list)) else v

        if isinstance(file_data, (str, bytes)) and not isinstance(file_data, io.IOBase):
            with open(file_data, "rb") as f:
                resp = requests.post(url, data=data, files={file_field: f}, timeout=30)
        else:
            # كائن BytesIO في الذاكرة - يتبعت مباشرة من غير ما يتكتب على القرص
            file_data.seek(0)
            filename = getattr(file_data, "name", "photo.jpg")
            resp = requests.post(url, data=data, files={file_field: (filename, file_data)}, timeout=30)

        if resp.status_code != 200:
            return None
        return resp
    except Exception:
        return None

def _dict_markup_to_pyrogram(markup):
    if not markup or not markup.get("inline_keyboard"):
        return None
    rows = []
    for row in markup["inline_keyboard"]:
        btn_row = []
        for b in row:
            if b.get("url"):
                btn_row.append(InlineKeyboardButton(b["text"], url=b["url"]))
            else:
                btn_row.append(InlineKeyboardButton(b["text"], callback_data=b.get("callback_data")))
        rows.append(btn_row)
    return InlineKeyboardMarkup(rows)

async def send_styled_message(client, chat_id, text, reply_markup=None, reply_to_message_id=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "link_preview_options": {"is_disabled": True}, "disable_web_page_preview": True}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    resp = await asyncio.to_thread(_tg_api_call, client, "sendMessage", payload)
    if resp is not None:
        return resp
    try:
        return await client.send_message(
            chat_id, text,
            reply_markup=_dict_markup_to_pyrogram(reply_markup),
            reply_to_message_id=reply_to_message_id,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"[styled_buttons] fallback sendMessage فشل كمان: {e}")
        return None

async def send_styled_photo(client, chat_id, photo, caption, reply_markup=None, reply_to_message_id=None):
    payload = {"chat_id": chat_id, "photo": photo, "caption": caption, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    is_file_path = isinstance(photo, str) and os.path.isfile(photo)
    is_in_memory = isinstance(photo, io.IOBase)

    if is_file_path or is_in_memory:
        resp = await asyncio.to_thread(_tg_api_call_file, client, "sendPhoto", payload, "photo", photo)
    else:
        resp = await asyncio.to_thread(_tg_api_call, client, "sendPhoto", payload)

    if resp is not None:
        return resp
    try:
        if is_in_memory:
            photo.seek(0)
        return await client.send_photo(
            chat_id, photo=photo, caption=caption,
            reply_markup=_dict_markup_to_pyrogram(reply_markup),
            reply_to_message_id=reply_to_message_id,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"[styled_buttons] fallback sendPhoto فشل كمان: {e}")
        return None

async def edit_styled_reply_markup(client, chat_id, message_id, reply_markup):
    """زي send_styled_message/send_styled_photo بالظبط بس لتعديل أزرار
    رسالة موجودة بالفعل (بدون تعديل نص/صورة) - نفس النمط: نجرب الـ API
    الخام الأول، وبعدين pyrogram كـ فولباك لو فشل."""
    payload = {"chat_id": chat_id, "message_id": message_id, "reply_markup": reply_markup}
    resp = await asyncio.to_thread(_tg_api_call, client, "editMessageReplyMarkup", payload)
    if resp is not None:
        return resp
    try:
        return await client.edit_message_reply_markup(chat_id, message_id, reply_markup=_dict_markup_to_pyrogram(reply_markup))
    except Exception:
        return None

def _extract_message_id(resp):
    if resp is None:
        return None
    if hasattr(resp, "json"):
        try:
            data = resp.json()
            if isinstance(data, dict) and data.get("ok"):
                return data.get("result", {}).get("message_id")
        except Exception:
            pass
    if hasattr(resp, "id"):
        return resp.id
    return None

def _track_msg(chat_id, msg_id):
    if msg_id:
        playing_messages.setdefault(chat_id, []).append(msg_id)

async def _delete_playing_messages(client, chat_id):
    # وقف تحديث شريط التقدم الحي كمان - أي مكان بيمسح كروت التشغيل يبقى
    # التشغيل خلص/وقف أصلاً، فمفيش داعي إن اللووب يفضل شغال في الخلفية
    _stop_progress_bar_task(chat_id)
    msgs = playing_messages.get(chat_id, [])
    for msg_id in msgs:
        try:
            await client.delete_messages(chat_id, msg_id)
        except Exception:
            pass
    playing_messages[chat_id] = []

def _escape_html(text):
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _short_title(title, max_words=7):
    words = title.split()
    if len(words) > max_words:
        return " ".join(words[:max_words])
    return title

async def _auto_delete_after(client, chat_id, message_id, delay=10):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, message_id)
    except Exception:
        pass

def format_duration(seconds):
    if seconds <= 0: return "0:00"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours > 0 else f"{minutes}:{secs:02d}"

async def check_force_subscribe(client, message):
    """التحقق من الاشتراك الإجباري - لو مفعّل (forceChannel) وغير معطل
    (disableSubscribe)، والعضو مش مشترك في القناة، بيبعتله رسالة انضمام
    ويرجع True (يعني وقف الأمر). القنوات مالهاش from_user فبنتجاهلها."""
    if not r.get(f'forceChannel:{Dev_Zaid}') or r.get(f'disableSubscribe:{Dev_Zaid}'):
        return False
    if not message.from_user:
        return False
    username = r.get(f'forceChannel:{Dev_Zaid}').replace('@', '')
    try:
        member = await client.get_chat_member(username, message.from_user.id)
        not_member = member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED) or member.status is None
    except FloodWait:
        return False
    except UserNotParticipant:
        not_member = True
    except Exception:
        return False
    if not not_member:
        return False
    try:
        await message.reply(
            f"- انضم للقناة ( @{username} ) لتستطيع استخدام اوامر الميوزك",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("اضغط هنا", url="https://t.me/" + username)]]),
        )
    except Exception:
        pass
    return True

async def check_disabled(client, message):
    # لو البوت الخدمي كله معطل (تعطيل البوت الخدمي) نوقف الميوزك بصمت زي باقي البوت
    if r.get(f'DisableBot:{Dev_Zaid}'):
        return True
    # تعطيل/تفعيل الميوزك لوحدها (زر تعطيل الميوزك) بغض النظر عن باقي البوت
    if r.get(f'disableMusic:{Dev_Zaid}'):
        await message.reply("<b>الميوزك معطلة حالياً</b>")
        return True
    if message.chat.id in bot_cache.get("disabled_groups", []):
        await message.reply("<b>البوت معطل في هذه المجموعة</b>")
        return True
    # علم "enable" ده بيتحدد تلقائي لما البوت يدخل جروب (new_chat_members)،
    # لكن القنوات مفيهاش هذا الحدث خالص (بتستخدم my_chat_member بدل كده)،
    # والمحادثات الخاصة (بين شخص والبوت مباشرة) برضه مالهاش علاقة بمفهوم
    # "دخول جروب" خالص - فالعلم ده فاضل مش متحدد للقنوات والخاص للأبد،
    # وكان بيوقف كل أوامر الميوزك فيهم بصمت من غير أي رسالة خطأ. القنوات
    # والمحادثات الخاصة معفية من الشرط ده.
    chat_type = getattr(message.chat, "type", None)
    if chat_type not in (ChatType.CHANNEL, ChatType.PRIVATE) and not r.get(f'{message.chat.id}:enable:{Dev_Zaid}'):
        return True
    if await check_force_subscribe(client, message):
        return True
    return False

async def check_privilege(client, chat_id, user_id, check_player=False):
    if user_id == sudo_id:
        return True
    chat_str = str(chat_id)
    if check_player and chat_str in bot_cache.get("custom_players", {}) and user_id in bot_cache["custom_players"][chat_str]:
        return True
    # يقدر يتحكم في الميوزك (إيقاف/تخطي/كمل/وقف... إلخ) لو أي واحدة من دول:
    # 1) مشرف حقيقي في تليجرام (Owner/Administrator) - مش لازم يبقى أدمن في
    #    رتب البوت أصلاً عشان يتحكم.
    # 2) رتبته في رتب البوت "ادمن" أو فوق (admin_pls بتشمل أدمن ومدير ومالك
    #    وأي رتبة أعلى) - حتى لو مش مشرف حقيقي في تليجرام.
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return True
    except Exception:
        pass
    try:
        if admin_pls(user_id, chat_id):
            return True
    except Exception:
        pass
    return False

async def is_admin(client, message, check_player=False, show_error=True):
    if getattr(message.chat, "type", None) == ChatType.CHANNEL or getattr(message, "sender_chat", None):
        return True
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return False
    has_priv = await check_privilege(client, message.chat.id, user_id, check_player)
    if not has_priv and show_error:
        await message.reply("<b>❥ عذرا هذا الامر لايخصك</b>")
    return has_priv

def get_downloader():
    try:
        from .downloader import download_for_play, upload_to_storage
        return download_for_play, upload_to_storage
    except ImportError:
        return None, None

def get_downloads_dir():
    try:
        from .downloader import DOWNLOADS_DIR
        return DOWNLOADS_DIR
    except ImportError:
        return None

def get_progressive_downloader():
    try:
        from .downloader import _progressive_download_media
        return _progressive_download_media
    except ImportError:
        return None

def get_storage_finder():
    try:
        from .downloader import find_in_storage_channel
        return find_in_storage_channel
    except ImportError:
        return None

def get_time_to_seconds():
    try:
        from .downloader import time_to_seconds
        return time_to_seconds
    except ImportError:
        return None

def get_normalizer():
    try:
        from .downloader import _normalize_for_storage
        return _normalize_for_storage
    except ImportError:
        return None

def get_yt_search():
    try:
        from .downloader import yt_search_async
        return yt_search_async
    except ImportError:
        return None

async def resolve_yt_result(query, is_video):
    """بيحل اسم الأغنية/الفيديو لأقرب نتيجة يوتيوب (id/title/duration) -
    بحث حي في يوتيوب في كل مرة، من غير أي كاش لنتيجة البحث نفسها (عشان
    كل طلب ياخد أحدث وأدق نتيجة ممكنة، من غير أي احتمال يفضل مربوط
    بغلطة قديمة). الكاش بتاع الملف نفسه (Redis/قناة التخزين) لسه شغال
    عادي زي ما هو بعد ما بيتحدد الـ video id هنا."""
    yt_search_async = get_yt_search()
    if not yt_search_async:
        return None

    results = await yt_search_async(query, max_results=5)
    if not results:
        return None

    res = results[0]
    return {
        "id": res.get("id"),
        "title": res.get("title"),
        "duration": res.get("duration", "0:00"),
    }

# ============================================================
# حد أقصى لمدة المقطع المسموح بتشغيله في الكول (تشغيل/فيديو/فيد/شغل).
# القيمة الافتراضية ساعتين وعشر دقايق، لكن المطور يقدر يغيرها في أي وقت
# بأمر "تغيير الحد <رقم بالدقايق>" - القيمة بتتخزن في Redis وبتتقرأ من
# هنا في كل مرة بدل ما تكون رقم ثابت جوه الكود. نفس الحد ده بيتطبق كمان
# على أمري "يوت"/"تحميل".
# ============================================================
DEFAULT_MAX_PLAY_DURATION_MINUTES = 130

def get_max_play_duration_seconds():
    stored = r.get(f"{Dev_Zaid}:MaxPlayMinutes")
    minutes = DEFAULT_MAX_PLAY_DURATION_MINUTES
    if stored:
        try:
            minutes = int(stored)
        except (TypeError, ValueError):
            minutes = DEFAULT_MAX_PLAY_DURATION_MINUTES
    return minutes * 60

async def download_replied_media(client, message, is_video=False):
    """
    لو الأمر (تشغيل/فيديو) كان ردًا على رسالة فيها ملف صوتي أو فيديو أو
    Voice/VideoNote جاهز في تليجرام، بنزّله مباشرة ونشغّله من غير أي بحث
    في يوتيوب خالص. لو الملف أكبر من 15 ميجا، بيبدأ التشغيل بعد أول 1%
    والباقي بينزل في الخلفية (نفس آلية تحميل يوتيوب). بترجع
    (file_path, title, duration, download_task) أو None لو الرسالة
    المردود عليها مفيهاش ميديا مناسبة.
    """
    reply = message.reply_to_message
    if not reply:
        return None

    media = reply.audio or reply.voice or reply.video or reply.video_note or reply.document
    if not media:
        return None

    duration = getattr(media, "duration", 0) or 0

    if reply.audio:
        title = reply.audio.title or reply.audio.file_name or "مقطع صوتي"
        default_ext = ".mp3"
    elif reply.video:
        title = reply.video.file_name or "فيديو"
        default_ext = ".mp4"
    elif reply.voice:
        title = "رسالة صوتية"
        default_ext = ".ogg"
    elif reply.video_note:
        title = "فيديو دائري"
        default_ext = ".mp4"
    else:
        title = reply.document.file_name or "ملف"
        default_ext = ""

    # لازم نحدد الامتداد بأنفسنا مقدمًا (بدل ما نسيب Pyrogram يحدده هو بعد
    # التحميل) عشان نعرف مسار الملف النهائي الثابت من الأول - وده ضروري
    # للتحميل التدريجي (نرجع الملف بعد أول 1% والباقي بينزل في الخلفية)
    src_name = getattr(media, "file_name", None)
    ext = os.path.splitext(src_name)[1] if src_name and "." in src_name else default_ext

    downloads_dir = get_downloads_dir() or "downloads"
    os.makedirs(downloads_dir, exist_ok=True)
    safe_name = f"tg_{reply.chat.id}_{reply.id}{ext}"
    file_path = os.path.join(downloads_dir, safe_name)

    progressive_download = get_progressive_downloader()
    try:
        if progressive_download:
            file_path, download_task = await progressive_download(client, reply, file_path)
        else:
            file_path = await client.download_media(reply, file_name=file_path)
            download_task = None
    except Exception as e:
        print(f"[download_replied_media Error]: {e}")
        return None

    if not file_path or not os.path.exists(file_path) or os.path.getsize(file_path) <= 0:
        return None

    return file_path, title, duration, download_task

# ============================================================
# دخول الحساب المساعد التلقائي لأي جروب يدخله البوت
# ============================================================

def _is_call_not_active_error(e):
    """بيحدد لو الخطأ سببه ان المكالمة الصوتية مقفولة/مش متبدية أصلاً،
    أو ان الحساب المساعد مش أدمن فمقدرش يبدأ المكالمة (CreateGroupCallRequest)"""
    if isinstance(e, (NoActiveGroupCall, GroupCallNotFoundError)):
        return True
    text = str(e).lower()
    name = type(e).__name__.lower()
    markers = (
        "noactivegroupcall", "groupcall_invalid", "no active group call",
        "group_call_invalid", "not started", "call not found", "callnotfound",
        "groupcallnotfound",
        # حالة الحساب المساعد مش أدمن ومحاول يبدأ الكول بنفسه
        "chat admin privileges are required", "chat_admin_required",
        "creategroupcallrequest",
    )
    return any(mk in text or mk in name for mk in markers)

async def ensure_assistant_in_chat(client, chat_id, notify_join_request=True):
    """
    يتأكد ان الحساب المساعد داخل الجروب ده:
    - لو محظور، بيحاول يفك حظره تلقائي (لو البوت معاه صلاحية)، ولو مقدرش
      هيبعت رسالة للجروب يطلب من الأدمن يفك الحظر يدوي.
    - لو مش داخل (اتشال/مش عضو)، بيجرب يدخل بالرابط مباشرة.
    - لو الجروب مفعل فيه "الموافقة على طلبات الانضمام"، هيتبعت طلب انضمام
      للحساب المساعد والبوت هيحاول يوافق عليه تلقائي على طول.
    - لو البوت مالوش صلاحية يوافق على طلبات الانضمام، هيبعت رسالة
      للجروب يطلب من الأدمن يقبل طلب انضمام الحساب المساعد يدوي.
    """
    call_py, assistant_id, assistant_client = get_assistant()
    if not assistant_client or not assistant_id:
        return False

    try:
        member = await client.get_chat_member(chat_id, assistant_id)
        if member.status == ChatMemberStatus.BANNED:
            # الحساب المساعد محظور فعلاً في الجروب
            try:
                await client.unban_chat_member(chat_id, assistant_id)
            except Exception:
                if notify_join_request:
                    try:
                        await client.send_message(
                            chat_id,
                            "<b>الحساب المساعد محظور في هذه المجموعة، يرجى فك حظره أولاً عشان يقدر يشتغل معاكم.</b>"
                        )
                    except Exception:
                        pass
                return False
            # اتفك الحظر - كمل تحت عشان يدخل الجروب تاني
        else:
            return True  # المساعد داخل بالفعل ومش محظور
    except UserNotParticipant:
        pass
    except Exception:
        pass

    try:
        link = await client.export_chat_invite_link(chat_id)
    except Exception:
        return False

    invite = link.split("/")[-1].replace("+", "")

    try:
        await assistant_client(ImportChatInviteRequest(invite))
        return True
    except InviteRequestSentError:
        # الجروب مفعل فيه طلبات انضمام - اتبعت طلب، هنحاول نوافق عليه تلقائي
        await asyncio.sleep(2)
        try:
            await client.approve_chat_join_request(chat_id, assistant_id)
            return True
        except Exception:
            if notify_join_request:
                try:
                    await client.send_message(
                        chat_id,
                        "<b>يرجى قبول طلب انضمام الحساب المساعد يدويًا عشان يقدر يشتغل معاكم في المكالمات الصوتية.</b>"
                    )
                except Exception:
                    pass
            return False
    except Exception:
        return False

_bot_id_cache = {}

async def _get_bot_id(client):
    key = id(client)
    if key not in _bot_id_cache:
        try:
            me = await client.get_me()
            _bot_id_cache[key] = me.id
        except Exception:
            return None
    return _bot_id_cache[key]

@Client.on_message(filters.new_chat_members)
async def bot_added_to_group_handler(client, message):
    bot_id = await _get_bot_id(client)
    if not bot_id:
        return
    added_ids = [u.id for u in (message.new_chat_members or []) if u]
    if bot_id not in added_ids:
        return
    asyncio.create_task(ensure_assistant_in_chat(client, message.chat.id))

# ============================================================
# إعداد المهام التلقائية
# ============================================================
registered_tgcalls = set()

def init_bg_helpers(client):
    call_py, assistant_id, assistant_client = get_assistant()
    
    if call_py and id(call_py) not in registered_tgcalls:
        registered_tgcalls.add(id(call_py))
        @call_py.on_update()
        async def stream_ended_handler(_, update):
            if isinstance(update, StreamEnded):
                if changing_stream.get(update.chat_id):
                    return
                await play_next(client, update.chat_id)

# ============================================================
# دوال التشغيل (كليشة عريضة ومصممة بشكل ممتاز)
# ============================================================

def _build_track_caption(header, track):
    """كليشة موحدة (تشغيل / إضافة للطابور) - نفس الشكل والعنوان المختصر
    القابل للضغط ونفس الأزرار في الحالتين."""
    title = track.get("title", "غير معروف")
    duration = track.get("duration_str") or format_duration(track.get("duration", 0))
    requester = track.get("requester", "غير معروف")
    yt_id = track.get("yt_id")

    short_title = _escape_html(_short_title(title))
    if yt_id:
        title_display = f'<a href="https://www.youtube.com/watch?v={yt_id}">{short_title}</a>'
    else:
        title_display = f"<code>{short_title}</code>"

    return (
        f"<b>{header}</b>\n\n"
        f"<b>الـعـنـوان :</b> {title_display}\n"
        f"<b>الـمـده :</b> <code>{duration}</code>\n"
        f"<b>بـواسـطـة :</b> {requester}"
    )

# ============================================================
# مولد كارت "بيتشغل دلوقتي" (بستايل بلاير: خلفية مبلورة + كارت زجاجي +
# صورة الأغنية + سطر YouTube/المشاهدات + شريط تقدم بالمدة)
# بيتبنى بالكامل في الذاكرة (RAM) من غير ما يتكتب أي ملف على القرص
# ============================================================

def _rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([(0, 0), size], radius=radius, fill=255)
    return mask

def _load_font(bold, size):
    path = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def _load_script_font(size):
    """خط مزخرف (كورسيف) لاسم المطوّر تحت صورته. لازم يدعم العربي (أسماء
    كتير عربي) وكمان الرموز المزخرفة (زي 𝓼𝓽𝔂𝓵𝓲𝔃𝓮𝓭 𝓽𝓮𝔁𝓽) اللي بتيجي من
    مولّدات "الخط الفاخر" - دي مش أحرف عادية، دي رموز يونيكود من مجموعة
    اسمها Mathematical Alphanumeric Symbols، ومعظم الخطوط العادية مالهاش
    غطاء ليها. FreeSans/FreeSerif من أوسع الخطوط تغطية للرموز دي."""
    candidates = [
        "assets/fonts/script.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/kacst/KacstOne.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

def _prepare_display_text(text):
    """النصوص العربية محتاجة "إعادة تشكيل" (ربط الحروف ببعض بشكلها الصح)
    و"ترتيب من اليمين لليسار" قبل ما PIL يرسمها - من غيرهم بتطلع الحروف
    منفصلة ومقلوبة (رموز غريبة). لو المكتبات المطلوبة (arabic_reshaper و
    python-bidi) مش متاحة على السيرفر، بنرجع النص زي ما هو بدل ما نكسر
    الكود - النصوص الإنجليزية/غير العربية بترجع زي ما هي على طول."""
    if not text or not re.search(r'[\u0600-\u06FF]', text):
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except ImportError:
        return text

# ============================================================
# باچ المطوّر: صورة بروفايله على تليجرام + اسمه (بيتحط فوق كل كارت تلقائيًا)
# مخزّن (cache) في الذاكرة لمدة ساعة عشان ميحصلش طلب لتليجرام مع كل أغنية
# ============================================================
_dev_badge_cache = {"bytes": None, "name": None, "ts": 0}
DEV_BADGE_CACHE_TTL = 3600  # ثانية (ساعة)

def _dev_badge_target_id():
    # sudo_id ده نفسه الآيدي اللي main.py بياخده منك كـ "SUDO ID" وقت أول تشغيل
    # وبيحفظه تلقائي في config.py - يعني هو آيدي حساب المطوّر/المالك أصلاً
    # من غير ما نحتاج ندخل أي متغير جديد. Dev_Zaid بديل احتياطي بس لو مش موجود.
    return globals().get("sudo_id") or globals().get("Dev_ID") or globals().get("Dev_Zaid")

async def _get_dev_badge_info(client):
    """بيجيب صورة بروفايل واسم صاحب sudo_id مرة واحدة ويكاشهم (bytes + name) عشان
    ميحصلش طلب لتليجرام مع كل أغنية. الاسم بييجي مباشرة من حسابه على تليجرام
    (اسمه الأول أو يوزره) وبيترسم بخط الكورسيف في الكارت، فبيطلع مزغرف من غير
    ما نحتاج ندخله يدوي."""
    now = time.time()
    if _dev_badge_cache["bytes"] and (now - _dev_badge_cache["ts"] < DEV_BADGE_CACHE_TTL):
        return _dev_badge_cache["bytes"], _dev_badge_cache["name"]

    dev_id = _dev_badge_target_id()
    if not dev_id:
        return None, None
    try:
        chat = await client.get_chat(dev_id)
        name = chat.first_name or (f"@{chat.username}" if chat.username else None)

        photo_bytes = None
        if chat.photo:
            buf = await client.download_media(chat.photo.big_file_id, in_memory=True)
            if buf:
                buf.seek(0)
                photo_bytes = buf.read()

        _dev_badge_cache["bytes"] = photo_bytes
        _dev_badge_cache["name"] = name
        _dev_badge_cache["ts"] = now
        return photo_bytes, name
    except Exception as e:
        print(f"[dev_badge] فشل جلب بيانات المطوّر (sudo_id={dev_id}): {e}")
        return None, None

def _build_now_playing_card(thumb_url, duration_str="0:00", view_count=None, badge_photo_bytes=None, badge_name=None):
    """بيبني كارت بستايل البلاير بالكامل في الذاكرة (من غير ما يكتب أي ملف على القرص):
    خلفية مبلورة من صورة الأغنية، كارت زجاجي شفاف في النص فيه صورة الأغنية،
    سطر YouTube/المشاهدات، شريط تقدم بالمدة، وباچ المطوّر (صورة بروفايله + اسمه)
    فوق الركن الشمال العلوي من صورة الأغنية. بترجع BytesIO جاهز للإرسال مباشرة."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    resp = None
    last_err = None
    for candidate_url in (thumb_url, thumb_url.replace("hqdefault.jpg", "mqdefault.jpg"), thumb_url.replace("hqdefault.jpg", "default.jpg")):
        try:
            resp = requests.get(candidate_url, timeout=15, headers=headers)
            resp.raise_for_status()
            break
        except Exception as e:
            last_err = e
            resp = None
            continue
    if resp is None:
        raise RuntimeError(f"فشل تحميل صورة الأغنية من يوتيوب: {last_err}")
    thumb = Image.open(io.BytesIO(resp.content)).convert("RGB")

    W, H = 1280, 720
    bg = ImageOps.fit(thumb, (W, H), Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.55)
    canvas = bg.convert("RGBA")

    # الكارت الزجاجي الشفاف في النص
    panel_w, panel_h = 760, 560
    panel_x = (W - panel_w) // 2
    panel_y = (H - panel_h) // 2
    panel_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(panel_layer).rounded_rectangle(
        [panel_x, panel_y, panel_x + panel_w, panel_y + panel_h],
        radius=42, fill=(235, 235, 235, 60)
    )
    canvas.alpha_composite(panel_layer)

    # صورة الأغنية جوه الكارت
    thumb_w, thumb_h = panel_w - 80, 280
    thumb_x = panel_x + 40
    thumb_y = panel_y + 40
    square = ImageOps.fit(thumb, (thumb_w, thumb_h), Image.LANCZOS).convert("RGBA")
    square.putalpha(_rounded_mask((thumb_w, thumb_h), radius=22))
    canvas.alpha_composite(square, (thumb_x, thumb_y))

    # باچ المطوّر: صورة بروفايله في دايرة + اسمه بخط مزخرف تحتها،
    # برا الكارت الزجاجي بالكامل، على الشمال، فوق الخلفية المموهة مباشرة
    if badge_photo_bytes:
        try:
            avatar_d = int(thumb_h * 0.62)
            ring_pad = 5
            badge_gap = 25  # المسافة بين الباچ وحافة الكارت الزجاجي
            avatar_x = panel_x - ring_pad - badge_gap - avatar_d
            avatar_y = thumb_y

            avatar_img = Image.open(io.BytesIO(badge_photo_bytes)).convert("RGB")
            avatar_img = ImageOps.fit(avatar_img, (avatar_d, avatar_d), Image.LANCZOS).convert("RGBA")
            avatar_mask = Image.new("L", (avatar_d, avatar_d), 0)
            ImageDraw.Draw(avatar_mask).ellipse([0, 0, avatar_d, avatar_d], fill=255)
            avatar_img.putalpha(avatar_mask)

            ring_d = avatar_d + ring_pad * 2
            ring = Image.new("RGBA", (ring_d, ring_d), (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse([0, 0, ring_d, ring_d], fill=(255, 255, 255, 235))
            canvas.alpha_composite(ring, (avatar_x - ring_pad, avatar_y - ring_pad))
            canvas.alpha_composite(avatar_img, (avatar_x, avatar_y))

            if badge_name:
                name_font = _load_script_font(int(avatar_d * 0.26))
                badge_draw = ImageDraw.Draw(canvas)
                name_y = avatar_y + avatar_d + 4
                badge_draw.text((avatar_x, name_y), _prepare_display_text(badge_name), font=name_font, fill=(255, 255, 255, 255))
        except Exception as e:
            print(f"[dev_badge] فشل رسم الباچ على الكارت: {e}")

    draw = ImageDraw.Draw(canvas)
    font_small = _load_font(False, 26)
    font_time = _load_font(True, 26)

    # سطر المصدر وعدد المشاهدات
    info_y = thumb_y + thumb_h + 40
    views_text = f"YouTube  │  {view_count} Views" if view_count else "YouTube  │  Unknown Views"
    draw.text((thumb_x, info_y), views_text, font=font_small, fill=(60, 60, 60, 255))

    # شريط التقدم (يبدأ من الصفر لأن الأغنية لسه بادئة)
    bar_y = info_y + 60
    bar_x1, bar_x2 = thumb_x, thumb_x + thumb_w
    draw.line([(bar_x1, bar_y), (bar_x2, bar_y)], fill=(180, 180, 180, 255), width=6)
    draw.ellipse([bar_x1 - 9, bar_y - 9, bar_x1 + 9, bar_y + 9], fill=(225, 45, 45, 255))

    # 00:00 على الشمال والمدة الكاملة على اليمين
    time_y = bar_y + 25
    draw.text((bar_x1, time_y), "00:00", font=font_time, fill=(60, 60, 60, 255))
    dur_w = draw.textlength(duration_str, font=font_time)
    draw.text((bar_x2 - dur_w, time_y), duration_str, font=font_time, fill=(60, 60, 60, 255))

    buffer = io.BytesIO()
    canvas.convert("RGB").save(buffer, format="JPEG", quality=92)
    buffer.seek(0)
    buffer.name = "now_playing.jpg"
    return buffer

async def build_now_playing_card_async(client, yt_id, duration_str, view_count=None):
    thumb_url = f"https://i.ytimg.com/vi/{yt_id}/hqdefault.jpg"
    badge_photo_bytes, badge_name = await _get_dev_badge_info(client)
    return await asyncio.to_thread(
        _build_now_playing_card, thumb_url, duration_str, view_count, badge_photo_bytes, badge_name
    )

async def send_track_card(client, chat_id, track, header, reply_to_message_id=None, progress_text=None):
    """كارت موحد (صورة ملونة + كابشن + أزرار) - بيتستخدم لحالة التشغيل
    المباشر وحالة الإضافة للطابور على حد سواء، بنفس الشكل والألوان
    بالظبط، الفرق الوحيد هو نص الـ header. لو `progress_text` اتبعت،
    الصف اللي كان فيه زرار "اخفاء القائمة" بيتحول لشريط تقدم بدله."""
    caption = _build_track_caption(header, track)
    yt_id = track.get("yt_id")

    photo = None
    if yt_id:
        try:
            duration_str = track.get("duration_str") or format_duration(track.get("duration", 0))
            photo = await build_now_playing_card_async(client, yt_id, duration_str, track.get("view_count"))
        except Exception as e:
            print(f"[track_card] فشل توليد الكارت: {e}")
            photo = f"https://i.ytimg.com/vi/{yt_id}/hqdefault.jpg"  # فولباك لو التوليد فشل

    resp = None
    try:
        if photo:
            resp = await send_styled_photo(client, chat_id, photo, caption, get_play_buttons(progress_text), reply_to_message_id=reply_to_message_id)
        if resp is None:
            resp = await send_styled_message(client, chat_id, caption, get_play_buttons(progress_text), reply_to_message_id=reply_to_message_id)
    except:
        pass
    return resp

progress_bar_tasks = {}  # chat_id -> asyncio.Task بتاع تحديث شريط التقدم الحي

def _stop_progress_bar_task(chat_id):
    task = progress_bar_tasks.pop(chat_id, None)
    if task and not task.done():
        task.cancel()

async def _progress_bar_updater(client, chat_id, msg_id, track):
    """بيحدّث زرار شريط التقدم كل كام ثانية طول ما نفس الأغنية دي شغالة،
    عشان يدي إحساس إنه بيتحرك لوحده مع الأغنية - تليجرام مفيهوش تحريك
    حقيقي جوه الأزرار، فده أقرب حاجة ممكنة (تعديل دوري لنص الزرار).
    بيوقف لوحده أول ما الأغنية دي تتغير/تقف، أو الرسالة تتمسح."""
    duration = track.get("duration", 0) or 0
    try:
        while True:
            await asyncio.sleep(8)
            # الأغنية اتغيرت أو التشغيل وقف خالص - مفيش داعي نكمل
            if current_playing.get(chat_id) is not track or not is_playing_now.get(chat_id):
                return
            elapsed = playback_offset.get(chat_id, 0)
            if not is_paused.get(chat_id):
                elapsed += time.time() - playback_start_time.get(chat_id, time.time())
            progress_text = _build_progress_bar_text(elapsed, duration)
            await edit_styled_reply_markup(client, chat_id, msg_id, get_play_buttons(progress_text))
    except asyncio.CancelledError:
        pass

async def send_playing_caption(client, chat_id, track):
    _stop_progress_bar_task(chat_id)
    duration = track.get("duration", 0) or 0
    # نحسب الموضع الحالي الحقيقي بدل ما نفترضه صفر دايمًا - في حالة بداية
    # أغنية جديدة هيبقى قريب من الصفر أصلاً، لكن في حالة إعادة عرض الكارت
    # (أمر "التحكم") وهو نص الأغنية مثلاً، هيبان الموضع الصحيح من أول لحظة
    elapsed = playback_offset.get(chat_id, 0)
    if not is_paused.get(chat_id):
        elapsed += time.time() - playback_start_time.get(chat_id, time.time())
    initial_progress = _build_progress_bar_text(elapsed, duration)
    resp = await send_track_card(client, chat_id, track, "تـم الـتـشـغـيـل بـنـجـاح ♡", progress_text=initial_progress)
    msg_id = _extract_message_id(resp)
    _track_msg(chat_id, msg_id)
    if msg_id:
        progress_bar_tasks[chat_id] = asyncio.create_task(_progress_bar_updater(client, chat_id, msg_id, track))

def _cleanup_old_track_file(chat_id, old_track, next_track):
    """تنظيف ملفات الأغنية اللي خلصت تشغيلها (path و original_path مع بعض،
    لو مختلفين بسبب عملية تمرير سابقة)، بس لو مش هي نفسها اللي هتتشغل تاني
    (تكرار) ومش موجودة تاني في الطابور (نفس الأغنية اتكررت). كده منمسحش
    ملف لسه محتاجينه، ومنسيبش ملفات قديمة تتراكم على الهارد من غير داعي."""
    if not old_track:
        return

    still_referenced_paths = set()
    if next_track:
        still_referenced_paths.add(next_track.get("path"))
        still_referenced_paths.add(next_track.get("original_path"))
    for track in music_queue.get(chat_id, []):
        still_referenced_paths.add(track.get("path"))
        still_referenced_paths.add(track.get("original_path"))

    candidates = {old_track.get("path"), old_track.get("original_path")}
    for old_path in candidates:
        if not old_path or old_path in still_referenced_paths:
            continue
        if not os.path.exists(old_path):
            continue
        try: os.remove(old_path)
        except: pass

async def play_next(client, chat_id, force_skip=False):
    call_py, assistant_id, assistant_client = get_assistant()
    if not call_py:
        return

    old_track = current_playing.get(chat_id)

    if not force_skip and repeat_mode.get(chat_id) and current_playing.get(chat_id):
        next_track = current_playing[chat_id]
    elif chat_id in music_queue and len(music_queue[chat_id]) > 0:
        next_track = music_queue[chat_id].pop(0)
    else:
        current_playing[chat_id] = None
        is_playing_now[chat_id] = False
        is_paused[chat_id] = False
        repeat_mode[chat_id] = False
        changing_stream[chat_id] = False
        _cleanup_old_track_file(chat_id, old_track, None)
        # ===== خلص التشغيل خالص (مفيش طابور ولا تكرار) - نمسح كروت/ردود
        # التشغيل المتراكمة (كارت "دلوقتي بيشتغل"، أزرار التحكم، كروت
        # الإضافة للطابور... إلخ) عشان الشات ميفضلش فيه كليشة قديمة
        # لأغاني خلصت من زمان =====
        await _delete_playing_messages(client, chat_id)
        try: 
            await call_py.leave_call(chat_id)
        except: 
            pass
        return

    _cleanup_old_track_file(chat_id, old_track, next_track)

    current_playing[chat_id] = next_track
    is_playing_now[chat_id] = True
    is_paused[chat_id] = False
    playback_start_time[chat_id] = time.time()
    playback_offset[chat_id] = 0

    changing_stream[chat_id] = True
    try:
        track_type = next_track.get("type", "audio")
        media_path = next_track["path"]
        stream = MediaStream(media_path) if track_type == "video" else MediaStream(media_path, video_flags=MediaStream.Flags.IGNORE)
        
        await call_py.play(chat_id, stream)
        await send_playing_caption(client, chat_id, next_track)
    except Exception as e:
        print(f"[play_next Exception]: {repr(e)}")
        traceback.print_exc()
        changing_stream[chat_id] = False
        if _is_call_not_active_error(e):
            # مش عيب في الأغنية نفسها؛ المكالمة الصوتية مش شغالة. نرجّع
            # الأغنية لأول الطابور بدل ما نضيّعها، ونوقف من غير ما نكرر
            # المحاولة على باقي الطابور كله وهو أصلاً هيفشل بنفس السبب.
            music_queue.setdefault(chat_id, []).insert(0, next_track)
            current_playing[chat_id] = None
            is_playing_now[chat_id] = False
            is_paused[chat_id] = False
            try:
                await send_styled_message(client, chat_id, "<b>عذرًا، قم بتشغيل المكالمة الصوتية أولاً ثم جرب التشغيل تاني.</b>")
            except Exception:
                pass
        else:
            try:
                fail_title = next_track.get("title", "الأغنية")
                await send_styled_message(client, chat_id, f"<b>حصل خطأ أثناء تشغيل {_escape_html(_short_title(fail_title))}، جاري تخطيها...</b>")
            except Exception:
                pass
            await play_next(client, chat_id, force_skip=force_skip)
    finally:
        await asyncio.sleep(1.5)
        changing_stream[chat_id] = False

# ============================================================
# أوامر التشغيل
# ============================================================

@Client.on_message(music_command(["تشغيل", "شغل"]) & ~filters.private)
async def play_command(client, message):
    init_bg_helpers(client)
    call_py, assistant_id, assistant_client = get_assistant()
    if await check_disabled(client, message): return
    # أمر التشغيل مفتوح لكل الأعضاء، مش بس الأدمن (عكس باقي أوامر الميوزك)
    if not call_py or not assistant_id:
        return await message.reply("<b>المساعد غير متصل</b>")

    chat_id = message.chat.id
    user_mention = get_user_mention(message)

    # ===== نبدأ تأكيد وجود الحساب المساعد في الجروب فورًا كـ Task في
    # الخلفية - بالتوازي مع البحث/التحميل اللي جاي تحت، مش بعده. ده بيقلل
    # وقت انضمام المساعد للمكالمة الصوتية بشكل واضح، لأن قبل كده كان
    # بيستنى التحميل يخلص الأول وبعدين يبدأ يتأكد من وجوده في الجروب =====
    join_task = asyncio.create_task(ensure_assistant_in_chat(client, chat_id))

    # ===== لو الأمر رد على ملف صوتي/فيديو جاهز في تليجرام، نشغّله مباشرة =====
    # من غير أي بحث في يوتيوب خالص - ده بيشتغل في القنوات والجروبات عادي
    reply = message.reply_to_message
    if reply:
        reply_media = reply.audio or reply.voice or reply.video or reply.video_note or reply.document
        reply_duration = getattr(reply_media, "duration", 0) or 0 if reply_media else 0
        if reply_duration and reply_duration > get_max_play_duration_seconds():
            return await message.reply(f"<b>عذرا هذا الوقت غير مسموح به</b>")

    replied = await download_replied_media(client, message, is_video=False)
    if replied:
        file_path, title, duration, _dl_task = replied
        status_msg = await message.reply("<b>جاري تحميل الملف...</b>")
        dur_str = format_duration(duration)
        track_info = {
            "path": file_path,
            "original_path": file_path,
            "title": title,
            "type": "audio",
            "duration": duration,
            "duration_str": dur_str,
            "requester": user_mention,
            "yt_id": None,
        }

        was_playing = is_playing_now.get(chat_id, False)
        queue = music_queue.setdefault(chat_id, [])
        queue.append(track_info)
        position = len(queue)

        await join_task
        await status_msg.delete()

        if was_playing:
            header = f"تـمـت الإضـافـة لـلـطـابـور #{position} ♡"
            # ملحوظة: من غير reply_to_message_id، لأن رسالة الأمر نفسها
            # اتمسحت بالفعل قبل ما الـ handler يتنفذ (music_command)، ولو
            # بعتنا رد على رسالة ممسوحة، تليجرام بيرفض الطلب الخام (الملون)
            # فالكود يرجع للطريقة الاحتياطية اللي بتفقد تلوين الأزرار.
            resp = await send_track_card(client, chat_id, track_info, header)
            _track_msg(chat_id, _extract_message_id(resp))
        else:
            await play_next(client, chat_id)
        return

    if r.get(f':disableYT:{Dev_Zaid}'):
        return await message.reply("اليوتيوب معطل حالياً")
    if r.get(f'{message.chat.id}:disableYT:{Dev_Zaid}'):
        return await message.reply("اليوتيوب معطل في هذه المجموعة")
    if len(message.text.split()) < 2:
        return await _ask_for_query(message, "play")

    status_msg = await message.reply("<b>جاري البحث...</b>")
    query = message.text.split(" ", 1)[1].strip()

    download_for_play, upload_to_storage = get_downloader()
    if download_for_play is None:
        return await status_msg.edit("<b>وحدة التحميل غير متصلة</b>")

    # ===== نحل اسم الأغنية لنتيجة يوتيوب (id/title/duration) - من كاش
    # البحث لو اتطلب قبل كده، أو بحث حي لو أول مرة - عشان نعرف مدة
    # المقطع قبل ما نبدأ التحميل، ولو المدة أكبر من الحد المسموح، منكملش
    # خالص ونوفر وقت التحميل =====
    time_to_seconds = get_time_to_seconds()
    direct_result = await resolve_yt_result(query, is_video=False)
    if not direct_result:
        return await status_msg.edit("<b>لم يتم العثور على نتائج</b>")
    picked_duration = time_to_seconds(direct_result.get("duration", "0:00")) if time_to_seconds else 0
    if picked_duration and picked_duration > get_max_play_duration_seconds():
        return await status_msg.edit(f"<b>عذرا هذا الوقت غير مسموح به</b>")

    file_path, title, info, _dl_task = await download_for_play(client, query, is_video=False, direct_result=direct_result)
    
    if not file_path:
        return await status_msg.edit("<b>فشل التحميل</b>")

    dur_str = format_duration(info["duration"])
    track_info = {
        "path": file_path,
        "original_path": file_path,
        "title": title,
        "type": "audio",
        "duration": info["duration"],
        "duration_str": dur_str,
        "requester": user_mention,
        "yt_id": info["id"]
    }

    # ===== نضيف للطابور فورًا من غير أي await قبلها =====
    # ده مهم جدًا: لو حصل await (زي ensure_assistant_in_chat) قبل ما الأغنية
    # تتضاف للطابور، الـ Task اللي بيرفع الملف في الخلفية (upload_to_storage)
    # ممكن يشتغل في نفس اللحظة دي، يفحص الطابور، يلاقي الأغنية لسه مش مضافة،
    # فيعتبر الملف "مش محتاج" ويمسحه - وبعد كده لما تتضاف فعليًا تبقى بتشاور
    # على ملف ممسوح خالص (FileNotFoundError وقت التشغيل).
    was_playing = is_playing_now.get(chat_id, False)

    queue = music_queue.setdefault(chat_id, [])
    queue.append(track_info)
    position = len(queue)

    await join_task

    await status_msg.delete()

    if was_playing:
        header = f"تـمـت الإضـافـة لـلـطـابـور #{position} ♡"
        resp = await send_track_card(client, chat_id, track_info, header)
        _track_msg(chat_id, _extract_message_id(resp))
    else:
        await play_next(client, chat_id)

@Client.on_message(music_command(["فيديو", "فيد"]) & ~filters.private)
async def play_video_command(client, message):
    init_bg_helpers(client)
    call_py, assistant_id, assistant_client = get_assistant()
    if await check_disabled(client, message): return
    # أمر الفيديو مفتوح لكل الأعضاء، مش بس الأدمن (عكس باقي أوامر الميوزك)
    if not call_py or not assistant_id:
        return await message.reply("<b>المساعد غير متصل</b>")

    chat_id = message.chat.id
    user_mention = get_user_mention(message)

    # ===== نبدأ تأكيد وجود الحساب المساعد في الجروب فورًا كـ Task في
    # الخلفية - بالتوازي مع البحث/التحميل تحت، مش بعده =====
    join_task = asyncio.create_task(ensure_assistant_in_chat(client, chat_id))

    # ===== لو الأمر رد على فيديو/صوت جاهز في تليجرام، نشغّله مباشرة =====
    reply = message.reply_to_message
    if reply:
        reply_media = reply.audio or reply.voice or reply.video or reply.video_note or reply.document
        reply_duration = getattr(reply_media, "duration", 0) or 0 if reply_media else 0
        if reply_duration and reply_duration > get_max_play_duration_seconds():
            return await message.reply(f"<b>عذرا هذا الوقت غير مسموح به</b>")

    replied = await download_replied_media(client, message, is_video=True)
    if replied:
        file_path, title, duration, _dl_task = replied
        status_msg = await message.reply("<b>جاري تحميل الملف...</b>")
        dur_str = format_duration(duration)
        track_info = {
            "path": file_path,
            "original_path": file_path,
            "title": title,
            "type": "video",
            "duration": duration,
            "duration_str": dur_str,
            "requester": user_mention,
            "yt_id": None,
        }

        was_playing = is_playing_now.get(chat_id, False)
        queue = music_queue.setdefault(chat_id, [])
        queue.append(track_info)
        position = len(queue)

        await join_task
        await status_msg.delete()

        if was_playing:
            header = f"تـمـت الإضـافـة لـلـطـابـور #{position} ♡"
            resp = await send_track_card(client, chat_id, track_info, header)
            _track_msg(chat_id, _extract_message_id(resp))
        else:
            await play_next(client, chat_id)
        return

    if r.get(f':disableYT:{Dev_Zaid}'):
        return await message.reply("اليوتيوب معطل حالياً")
    if r.get(f'{message.chat.id}:disableYT:{Dev_Zaid}'):
        return await message.reply("اليوتيوب معطل في هذه المجموعة")
    if len(message.text.split()) < 2:
        return await _ask_for_query(message, "video")

    status_msg = await message.reply("<b>جاري البحث...</b>")
    query = message.text.split(" ", 1)[1].strip()

    download_for_play, upload_to_storage = get_downloader()
    if download_for_play is None:
        return await status_msg.edit("<b>وحدة التحميل غير متصلة</b>")

    time_to_seconds = get_time_to_seconds()
    direct_result = await resolve_yt_result(query, is_video=True)
    if not direct_result:
        return await status_msg.edit("<b>لم يتم العثور على نتائج</b>")
    picked_duration = time_to_seconds(direct_result.get("duration", "0:00")) if time_to_seconds else 0
    if picked_duration and picked_duration > get_max_play_duration_seconds():
        return await status_msg.edit(f"<b>عذرا هذا الوقت غير مسموح به</b>")

    file_path, title, info, _dl_task = await download_for_play(client, query, is_video=True, direct_result=direct_result)
    
    if not file_path:
        return await status_msg.edit("<b>فشل التحميل</b>")

    dur_str = format_duration(info["duration"])
    track_info = {
        "path": file_path,
        "original_path": file_path,
        "title": title,
        "type": "video",
        "duration": info["duration"],
        "duration_str": dur_str,
        "requester": user_mention,
        "yt_id": info["id"]
    }

    # ===== نضيف للطابور فورًا قبل أي await (نفس سبب التعديل في أمر الصوت) =====
    was_playing = is_playing_now.get(chat_id, False)

    queue = music_queue.setdefault(chat_id, [])
    queue.append(track_info)
    position = len(queue)

    await join_task

    await status_msg.delete()

    if was_playing:
        header = f"تـمـت الإضـافـة لـلـطـابـور #{position} ♡"
        resp = await send_track_card(client, chat_id, track_info, header)
        _track_msg(chat_id, _extract_message_id(resp))
    else:
        await play_next(client, chat_id)

# ============================================================
# حد أقصى لمدة المقطع في أوامر "يوت"/"تحميل" - بقى نفس حد أوامر التشغيل
# (get_max_play_duration_seconds)، يتغير بأمر "تغيير الحد" الموحّد
# ============================================================

def _build_source_markup():
    """زرار 'Source' مزخرف - بيظهر بس لو قناة السورس معينة فعلاً."""
    source_channel = r.get(f"{Dev_Zaid}:BotChannel")
    if not source_channel:
        return None
    return InlineKeyboardMarkup([[InlineKeyboardButton("𝓢𝓸𝓾𝓻𝓬𝓮", url=f"https://t.me/{source_channel}")]])

async def _yt_download_command(client, message, query, is_video):
    """منطق مشترك بين أمر 'يوت' (بيحمل ملف صوتي) وأمر 'تحميل' (بيحمل
    فيديو). قبل أي تحميل فعلي، بيدور بنفسه على الملف جاهز في Redis أو
    قناة التخزين - لو لقاه، بيبعته فورًا بالـ file_id (تليجرام بينسخه من
    سيرفراته لسيرفراته من غير أي تحميل محلي خالص، يعني بثانية واحدة تقريبًا).
    لو مش لاقيه في الاتنين، وقتها بس بيستخدم download_for_play عشان يحمله
    فعليًا من يوتيوب من الصفر، يحوّله للصيغة المطلوبة، ويبعته."""
    download_for_play, _ = get_downloader()
    time_to_seconds = get_time_to_seconds()
    if not (download_for_play and time_to_seconds):
        return await message.reply("<b>وحدة التحميل غير متصلة</b>")

    status_msg = await message.reply("🎬" if is_video else "🎵")

    try:
        res = await resolve_yt_result(query, is_video)
    except Exception as e:
        return await status_msg.edit(f"<b>حدث خطأ أثناء البحث: {e}</b>")

    if not res:
        return await status_msg.edit("❌ لم يتم العثور على نتائج")

    vid_id = res.get("id")
    title = res.get("title") or "غير معروف"
    duration_str = res.get("duration", "0:00")
    duration = time_to_seconds(duration_str)

    if duration and duration > get_max_play_duration_seconds():
        return await status_msg.edit("<b>عذرا هذا الوقت غير مسموح به</b>")

    download_markup = _build_source_markup()
    cache_key = f"yt_{'video' if is_video else 'audio'}_{vid_id}"

    # ===== 1. البحث في Redis - أسرع طريقة لو الملف اتبعت قبل كده =====
    cached_file_id = r.get(cache_key)
    if cached_file_id:
        try:
            if is_video:
                await message.reply_video(cached_file_id, duration=duration, reply_markup=download_markup)
            else:
                await message.reply_audio(cached_file_id, title=title, duration=duration, performer="YouTube", reply_markup=download_markup)
            return await status_msg.delete()
        except Exception as e:
            print(f"[yt_download] فشل الإرسال من كاش Redis، هيتم مسحه والمتابعة: {e}")
            r.delete(cache_key)

    # ===== 2. البحث في قناة التخزين - برضه إرسال مباشر بالـ file_id من
    # غير تحميل محلي خالص =====
    find_in_storage_channel = get_storage_finder()
    if find_in_storage_channel:
        try:
            msg_id = await find_in_storage_channel(vid_id, is_video=is_video)
            if msg_id:
                pyro_msg = await client.get_messages(f"@{STORAGE_CHANNEL}", msg_id)
                media = (pyro_msg.video if is_video else (pyro_msg.audio or pyro_msg.document)) if pyro_msg else None
                if media:
                    if is_video:
                        await message.reply_video(media.file_id, duration=duration, reply_markup=download_markup)
                    else:
                        await message.reply_audio(media.file_id, title=title, duration=duration, performer="YouTube", reply_markup=download_markup)
                    r.set(cache_key, media.file_id)
                    return await status_msg.delete()
        except Exception as e:
            print(f"[yt_download] فشل البحث/الإرسال من قناة التخزين: {e}")

    # ===== 3. مش موجود جاهز في أي مكان - تحميل فعلي من يوتيوب من الصفر =====
    file_path, title, dl_info, dl_task = await download_for_play(client, query, is_video=is_video, direct_result=res)

    if not file_path:
        return await status_msg.edit("<b>فشل التحميل، جرب اسم تاني</b>")

    # لازم ننتظر اكتمال التحميل بالكامل هنا (مش بس أول نسبة زي حالة الكول)
    # لأن الملف هيتبعت كملف كامل (صوت/فيديو) مش هيتشغل كبث تدريجي
    if dl_task:
        try:
            await dl_task
        except Exception:
            pass

    if not os.path.exists(file_path) or os.path.getsize(file_path) <= 0:
        return await status_msg.edit("<b>فشل التحميل، جرب اسم تاني</b>")

    # ===== تحويل الملف لصيغة قياسية حسب نوع الطلب قبل الإرسال =====
    # يوتيوب بيرجع الملف بأي صيغة متاحة (webm/m4a/opus إلخ حسب قيود
    # SABR على العملاء المتاحة) - مش بالضرورة mp3/mp4 حقيقية. هنا بنحول
    # فعليًا (مش مجرد تغيير امتداد): صوت بس لو "يوت"، فيديو عادي (صورة
    # وصوت) لو "تحميل". بنكتب الناتج لملف مؤقت بلاحقة "_dl" مختلفة عن
    # اللاحقة "_std" اللي بيستخدمها الرفع لقناة التخزين في الخلفية على
    # نفس الملف الأصلي، عشان الاتنين ما يتصادموش لو اشتغلوا في نفس الوقت.
    normalize = get_normalizer()
    send_path = file_path
    if normalize:
        try:
            send_path = await normalize(file_path, is_video, suffix="_dl")
        except Exception as e:
            print(f"[yt_download] فشل التحويل، هيترسل الأصلي: {e}")
            send_path = file_path

    dur_sec = dl_info.get("duration", duration)

    try:
        if is_video:
            await message.reply_video(send_path, duration=dur_sec, reply_markup=download_markup)
        else:
            await message.reply_audio(send_path, title=title, duration=dur_sec, performer="YouTube", reply_markup=download_markup)
    except Exception as e:
        print(f"[yt_download] فشل إرسال الملف: {e}")
        return await status_msg.edit("<b>فشل إرسال المقطع</b>")
    finally:
        if send_path != file_path:
            try: os.remove(send_path)
            except: pass
        try:
            await status_msg.delete()
        except Exception:
            pass

@Client.on_message(music_command(["يوت"]))
async def yt_audio_cmd(client, message):
    if r.get(f':disableYT:{Dev_Zaid}'):
        return await message.reply("اليوتيوب معطل حالياً")
    if r.get(f'{message.chat.id}:disableYT:{Dev_Zaid}'):
        return await message.reply("اليوتيوب معطل في هذه المجموعة")
    if await check_disabled(client, message): return
    if len(message.text.split()) < 2:
        return await _ask_for_query(message, "yt")

    query = message.text.split(" ", 1)[1].strip()
    await _yt_download_command(client, message, query, is_video=False)

@Client.on_message(music_command(["تحميل", "download"]))
async def yt_video_cmd(client, message):
    if r.get(f':disableYT:{Dev_Zaid}'):
        return await message.reply("اليوتيوب معطل حالياً")
    if r.get(f'{message.chat.id}:disableYT:{Dev_Zaid}'):
        return await message.reply("اليوتيوب معطل في هذه المجموعة")
    if await check_disabled(client, message): return
    if len(message.text.split()) < 2:
        return await _ask_for_query(message, "download")

    query = message.text.split(" ", 1)[1].strip()
    await _yt_download_command(client, message, query, is_video=True)

def _pending_query_filter(_, __, m):
    if not m.text or not m.from_user:
        return False
    key = (m.chat.id, m.from_user.id)
    pending = pending_music_request.get(key)
    if not pending:
        return False
    if time.time() > pending["expires"]:
        pending_music_request.pop(key, None)
        return False
    # الرسالة اللي هي نفسها سبب السؤال (زي "تشغيل" لوحدها) - مش ردها،
    # تستبعد هنا عشان ما تتحسبش هي إجابة نفسها
    if m.id == pending.get("origin_msg_id"):
        return False
    return True

@Client.on_message(filters.create(_pending_query_filter), group=5)
async def handle_pending_query_reply(client, message):
    """بيمسك رد الشخص بعد ما اتسأل 'عايز تشغل إيه؟' ويحوله لنفس أمر
    التشغيل/التحميل اللي طلبه أول مرة، وكأنه كتب الأمر كامل من الأول.
    مسجل في group=5 (بعد كل أوامر الميوزك العادية اللي في group=0
    الافتراضي)، فلو الرد نفسه صادف إنه أمر ميوزك تاني (زي 'وقف' مثلاً)،
    الأمر الأصلي بتاعه بياخده الأول ومحدش يوصل هنا خالص."""
    key = (message.chat.id, message.from_user.id)
    pending = pending_music_request.pop(key, None)
    if not pending:
        return

    async def _delete_prompt():
        prompt_id = pending.get("prompt_msg_id")
        if prompt_id:
            try:
                await client.delete_messages(message.chat.id, prompt_id)
            except Exception:
                pass

    query = message.text.strip()
    if not query:
        await _delete_prompt()
        return await message.reply("<b>اكتب اسم حاجة تشغلها</b>")

    keyword = _PENDING_KIND_KEYWORD[pending["kind"]]
    message.text = f"{keyword} {query}"

    await _delete_prompt()
    try:
        await message.delete()
    except Exception:
        pass

    handler_map = {
        "play": play_command,
        "video": play_video_command,
        "yt": yt_audio_cmd,
        "download": yt_video_cmd,
    }
    await handler_map[pending["kind"]](client, message)

# ============================================================
# أوامر التحكم
# ============================================================

@Client.on_message(music_command(["الغاء", "إلغاء"]) & ~filters.private)
async def cancel_command(client, message):
    if await check_disabled(client, message): return
    key = (message.chat.id, message.from_user.id if message.from_user else message.chat.id)
    pending = pending_music_request.pop(key, None)
    if pending:
        prompt_id = pending.get("prompt_msg_id")
        if prompt_id:
            try:
                await client.delete_messages(message.chat.id, prompt_id)
            except Exception:
                pass
        return await message.reply("<b>تم إلغاء الطلب</b>")
    await message.reply("<b>مفيش عملية معلّقة تلغيها حالياً</b>")

@Client.on_message(music_command(["إيقاف", "ايقاف", "اسكت"]) & ~filters.private)
async def stop_command(client, message):
    call_py, assistant_id, assistant_client = get_assistant()
    if await check_disabled(client, message): return
    if not await is_admin(client, message, check_player=True): return
    chat_id = message.chat.id
    if not is_playing_now.get(chat_id):
        return await message.reply("<b>لا يوجد شيء قيد التشغيل ♬</b>")
    music_queue[chat_id] = []
    repeat_mode[chat_id] = False
    current_playing[chat_id] = None
    is_playing_now[chat_id] = False
    is_paused[chat_id] = False
    changing_stream[chat_id] = False
    try: await call_py.leave_call(chat_id)
    except: pass
    await _delete_playing_messages(client, chat_id)
    stop_msg = await message.reply(f"<b>تم الإيقاف بواسطة {get_user_mention(message)}</b>")
    asyncio.create_task(_auto_delete_after(client, chat_id, stop_msg.id))

@Client.on_message(music_command(["تخطي", "تجاوز"]) & ~filters.private)
async def skip_cmd(client, message):
    if await check_disabled(client, message): return
    if not await is_admin(client, message, check_player=True): return
    chat_id = message.chat.id
    if not is_playing_now.get(chat_id):
        return await message.reply("<b>لا يوجد شيء للتخطي</b>")
    
    # فحص الطابور: لو فاضي ومافيش أغنية بعد الأغنية الحالية
    queue = music_queue.get(chat_id, [])
    if not queue or len(queue) == 0:
        return await message.reply("لا يمكن تشغيل التخطي")

    skip_msg = await message.reply(f"تم تخطي بواسطة {get_user_mention(message)}")
    _track_msg(chat_id, skip_msg.id)
    await play_next(client, chat_id, force_skip=True)

@Client.on_message(music_command(["كرر", "تكرار"]) & ~filters.private)
async def repeat_cmd(client, message):
    if await check_disabled(client, message): return
    if not await is_admin(client, message, check_player=True): return
    chat_id = message.chat.id
    current = current_playing.get(chat_id)
    if not current: 
        return await message.reply("<b>لا يوجد شيء قيد التشغيل ♬</b>")
    if chat_id not in music_queue: 
        music_queue[chat_id] = []
    music_queue[chat_id].append(current)
    position = len(music_queue[chat_id])

    header = f"تـمـت الإضـافـة لـلـطـابـور #{position} ♡"
    resp = await send_track_card(client, chat_id, current, header)
    _track_msg(chat_id, _extract_message_id(resp))

@Client.on_message(music_command(["وقف", "pause"]) & ~filters.private)
async def pause_cmd(client, message):
    call_py, assistant_id, assistant_client = get_assistant()
    if await check_disabled(client, message): return
    if not await is_admin(client, message, check_player=True): return
    chat_id = message.chat.id
    if not is_playing_now.get(chat_id):
        return await message.reply("<b>لا يوجد شيء قيد التشغيل ♬</b>")
    if is_paused.get(chat_id):
        return await message.reply("<b>البث متوقف بالفعل</b>")
    try:
        await call_py.pause(chat_id)
        playback_offset[chat_id] = playback_offset.get(chat_id, 0) + (time.time() - playback_start_time.get(chat_id, time.time()))
        is_paused[chat_id] = True
        pause_msg = await message.reply(f"<b>تم الإيقاف المؤقت بواسطة {get_user_mention(message)}</b>")
        _track_msg(chat_id, pause_msg.id)
    except: 
        await message.reply("<b>حدث خطأ أثناء تنفيذ الأمر.</b>")

@Client.on_message(music_command(["كمل", "resume"]) & ~filters.private)
async def resume_cmd(client, message):
    call_py, assistant_id, assistant_client = get_assistant()
    if await check_disabled(client, message): return
    if not await is_admin(client, message, check_player=True): return
    chat_id = message.chat.id
    if not is_playing_now.get(chat_id):
        return await message.reply("<b>لا يوجد شيء قيد التشغيل ♬</b>")
    if not is_paused.get(chat_id):
        return await message.reply("<b>البث يعمل بالفعل</b>")
    try:
        await call_py.resume(chat_id)
        playback_start_time[chat_id] = time.time()
        is_paused[chat_id] = False
        resume_msg = await message.reply(f"<b>تم الاستئناف بواسطة {get_user_mention(message)}</b>")
        _track_msg(chat_id, resume_msg.id)
    except: 
        await message.reply("<b>حدث خطأ أثناء تنفيذ الأمر.</b>")

@Client.on_message(music_command(["مرر", "رجع"]) & ~filters.private)
async def seek_cmd(client, message):
    call_py, assistant_id, assistant_client = get_assistant()
    if await check_disabled(client, message): return
    if not await is_admin(client, message, check_player=True): return
    chat_id = message.chat.id
    if not call_py or not is_playing_now.get(chat_id):
        return await message.reply("<b>لا يوجد شيء قيد التشغيل ♬</b>")

    text = message.text.strip()
    for p in ("/", "!"):
        if text.startswith(p):
            text = text[len(p):]
            break
    parts = text.split(None, 1)
    if len(parts) < 2:
        return await message.reply("يرجى كتابة عدد الثواني بعد الأمر، مثلاً: مرر 50")
    try:
        seconds = int(parts[1].strip())
    except:
        return await message.reply("يرجى كتابة عدد الثواني بعد الأمر، مثلاً: مرر 50")

    cmd_word = _translate_command_word(message, parts[0])
    current_time = playback_offset.get(chat_id, 0) + (time.time() - playback_start_time.get(chat_id, time.time()))

    if cmd_word == "مرر":
        target = current_time + seconds
        direction = "تقديم"
    else:
        target = max(0, current_time - seconds)
        direction = "إرجاع"

    msg = await message.reply(f"<b>جاري {direction} الأغنية...</b>")
    _track_msg(chat_id, msg.id)
    await perform_seek(client, chat_id, target, msg, get_user_mention(message))

async def perform_seek(client, chat_id, target_time, msg, user_mention, callback_query=None):
    track = current_playing.get(chat_id)
    if not track: return
    duration = track.get("duration", 0)

    if duration > 0 and target_time >= duration:
        await msg.edit(f"التمرير تخطى مدة الأغنية، تم التخطي بواسطة {user_mention}")
        if callback_query:
            try: await msg.delete()
            except: pass
            await callback_query.answer("تم التخطي")
        return await play_next(client, chat_id, force_skip=True)

    original_path = track.get("original_path", track["path"])
    if not os.path.exists(original_path):
        if callback_query:
            try: await msg.delete()
            except: pass
            await callback_query.answer("حدث خطأ أثناء التمرير", show_alert=True)
        else:
            try: await msg.edit("<b>حدث خطأ أثناء التمرير، الأغنية مستمرة زي ما هي</b>")
            except: pass
        return

    is_vid = track.get("type") == "video"
    ext = "mkv"
    temp_path = f"downloads/seek_{chat_id}_{int(target_time)}.{ext}"

    if is_vid:
        cmd = f'ffmpeg -hide_banner -loglevel error -y -ss {target_time} -i "{original_path}" -map 0 -c copy -avoid_negative_ts make_zero -fflags +genpts "{temp_path}"'
    else:
        cmd = f'ffmpeg -hide_banner -loglevel error -y -ss {target_time} -i "{original_path}" -c copy "{temp_path}"'

    try:
        process = await asyncio.create_subprocess_shell(cmd)
        await asyncio.wait_for(process.communicate(), timeout=15)
    except Exception:
        if callback_query:
            try: await msg.delete()
            except: pass
            await callback_query.answer("حدث خطأ أثناء التمرير", show_alert=True)
        else:
            try: await msg.edit("<b>حدث خطأ أثناء التمرير، الأغنية مستمرة زي ما هي</b>")
            except: pass
        return

    call_py, assistant_id, assistant_client = get_assistant()

    if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
        is_seeking[chat_id] = True
        changing_stream[chat_id] = True
        try:
            stream_obj = MediaStream(temp_path) if is_vid else MediaStream(temp_path, video_flags=MediaStream.Flags.IGNORE)
            await call_py.play(chat_id, stream_obj)

            playback_offset[chat_id] = target_time
            playback_start_time[chat_id] = time.time()
            current_playing[chat_id]["path"] = temp_path
            reached = format_duration(target_time)
            if callback_query:
                try: await msg.delete()
                except: pass
                await callback_query.answer(f"تم التمرير بنجاح ووصل {reached}")
            else:
                await msg.edit(f"<b>تم التمرير بنجاح ووصل {reached} بواسطة {user_mention}</b>")
        except:
            try: os.remove(temp_path)
            except: pass
            if callback_query:
                try: await msg.delete()
                except: pass
                await callback_query.answer("حدث خطأ أثناء التمرير، الأغنية مستمرة زي ما هي", show_alert=True)
            else:
                try: await msg.edit("<b>حدث خطأ أثناء التمرير، الأغنية مستمرة زي ما هي</b>")
                except: pass
        finally:
            await asyncio.sleep(1.5)
            changing_stream[chat_id] = False
            is_seeking[chat_id] = False
    else:
        if callback_query:
            try: await msg.delete()
            except: pass
            await callback_query.answer("حدث خطأ أثناء التمرير", show_alert=True)
        else:
            try: await msg.edit("<b>حدث خطأ أثناء التمرير، الأغنية مستمرة زي ما هي</b>")
            except: pass

# ============================================================
# أمر التحكم (إعادة عرض كليشة التشغيل العريضة بالأزرار والصورة)
# ============================================================

@Client.on_message(music_command(["التحكم", "تحكم"]) & ~filters.private)
async def control_cmd(client, message):
    if await check_disabled(client, message): return
    chat_id = message.chat.id
    if not is_playing_now.get(chat_id) or not current_playing.get(chat_id):
        return await message.reply("مافيش حاجة شغالة أصلاً")
    
    await send_playing_caption(client, chat_id, current_playing[chat_id])

# ============================================================
# أمر مين مشغل (عرض الأغنية الشغالة واسم اللي شغلها قابل للضغط)
# ============================================================

@Client.on_message(music_command(["مين مشغل", "مين شغل"]) & ~filters.private)
async def who_played_cmd(client, message):
    if await check_disabled(client, message): return
    chat_id = message.chat.id
    if not is_playing_now.get(chat_id) or not current_playing.get(chat_id):
        return await message.reply("مافيش حاجة شغالة أصلاً يا عم")
    
    track = current_playing[chat_id]
    requester = track.get("requester", "غير معروف")

    text = f"<b>هـو ده الـفـنـان الـلـي مـشـغـل :</b> {requester}"
    await send_styled_message(client, chat_id, text, reply_to_message_id=message.id)

# ============================================================
# أمر مين في الكول (روابط قابلة للضغط لكل الأشخاص بالترتيب)
# ============================================================

def _mic_status_label(p):
    """بيرجع نص 'يتحدث' لو المشترك شغال المايك، أو 'يستمع' لو مكتوم المايك.
    لو الحساب المساعد بيرجع بيانات المشارك من غير معلومة الكتم أصلاً بيرجع
    نص فاضي عشان الاسم يفضل بيظهر عادي من غير حالة غلط."""
    muted = getattr(p, "muted", None)
    if muted is None:
        muted = getattr(p, "is_muted", None)
    if muted is True:
        return " — 🔇 يستمع"
    if muted is False:
        return " — 🎙 يتحدث"
    return ""

@Client.on_message(music_command(["مين في الكول", "مين في الكول؟"]) & ~filters.private)
async def who_is_in_call(client, message):
    if await check_disabled(client, message): return
    call_py, assistant_id, assistant_client = get_assistant()
    chat_id = message.chat.id
    
    if not call_py or not assistant_id:
        return await message.reply("<b>المساعد غير متصل</b>")

    status_msg = await message.reply("<b>جاري فحص المكالمة الصوتية...</b>")

    # لو مفيش أغنية شغالة (الكول فاضي)
    if not is_playing_now.get(chat_id):
        try:
            record_path = CALL_RECORD_PATH
            if os.path.exists(record_path):
                stream = MediaStream(record_path, video_flags=MediaStream.Flags.IGNORE)
                await call_py.play(chat_id, stream)
            
            await asyncio.sleep(3)
            
            participants = await call_py.get_participants(chat_id)
            
            if not participants:
                await status_msg.edit("المكالمة مقفولة يا عم")
                try: await call_py.leave_call(chat_id)
                except: pass
                return

            text = "✯ ⦅ قـائـمـة الـمـتـواجـديـن فـي الـمـكـالـمـة ⦆ ✯\n\n"
            count = 0
            for p in participants:
                u_id = getattr(p, "user_id", None)
                if not u_id or u_id == assistant_id:
                    continue # إخفاء الحساب المساعد
                mic_label = _mic_status_label(p)
                try:
                    user = await client.get_users(u_id)
                    name = user.first_name or "مستخدم"
                    name = name.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
                    text += f"↫ ⦗ <a href=\"tg://user?id={u_id}\">{name}</a> ⦘{mic_label}\n"
                    count += 1
                except Exception:
                    text += f"↫ ⦗ <a href=\"tg://user?id={u_id}\">مستخدم ({u_id})</a> ⦘{mic_label}\n"
                    count += 1
            
            if count > 0:
                await status_msg.edit(text, disable_web_page_preview=True)
            else:
                await status_msg.edit("مفيش حد في المكالمة غير الحساب المساعد.")
            
            await asyncio.sleep(3)
            await call_py.leave_call(chat_id)
            
        except Exception:
            await status_msg.edit("المكالمة مقفولة يا عم")
            try: await call_py.leave_call(chat_id)
            except: pass
            
    # لو في أغنية شغالة (المساعد موجود بالفعل في الكول)
    else:
        try:
            participants = await call_py.get_participants(chat_id)
            if not participants:
                return await status_msg.edit("المكالمة مقفولة يا عم")

            text = "✯ ⦅ قـائـمـة الـمـتـواجـديـن فـي الـمـكـالـمـة ⦆ ✯\n\n"
            count = 0
            for p in participants:
                u_id = getattr(p, "user_id", None)
                if not u_id or u_id == assistant_id:
                    continue # إخفاء الحساب المساعد
                mic_label = _mic_status_label(p)
                try:
                    user = await client.get_users(u_id)
                    name = user.first_name or "مستخدم"
                    name = name.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
                    text += f"↫ ⦗ <a href=\"tg://user?id={u_id}\">{name}</a> ⦘{mic_label}\n"
                    count += 1
                except Exception:
                    text += f"↫ ⦗ <a href=\"tg://user?id={u_id}\">مستخدم ({u_id})</a> ⦘{mic_label}\n"
                    count += 1
            
            if count > 0:
                await status_msg.edit(text, disable_web_page_preview=True)
            else:
                await status_msg.edit("مفيش حد في المكالمة غير الحساب المساعد.")
                
        except Exception:
            await status_msg.edit("المكالمة مقفولة يا عم")

# ============================================================
# أزرار التحكم
# ============================================================

@Client.on_callback_query(filters.regex(r"^music_(pause|resume|stop|skip|repeat|back15|fwd15|back30|fwd30|hide_menu|progress_noop)$"))
async def music_buttons_handler(client, callback_query):
    init_bg_helpers(client)
    call_py, assistant_id, assistant_client = get_assistant()
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    user_name = callback_query.from_user.first_name or "مجهول"
    user_name = user_name.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
    user = f'<a href="tg://user?id={callback_query.from_user.id}">{user_name}</a>'
    
    if not await check_privilege(client, chat_id, user_id, check_player=True):
        await callback_query.answer("❥ عذرا هذا الامر لايخصك ", show_alert=True)
        return

    if data == "music_progress_noop":
        track = current_playing.get(chat_id)
        if not track or not is_playing_now.get(chat_id):
            return await callback_query.answer("مافيش حاجة شغالة أصلاً")
        elapsed = playback_offset.get(chat_id, 0)
        if not is_paused.get(chat_id):
            elapsed += time.time() - playback_start_time.get(chat_id, time.time())
        duration = track.get("duration", 0) or 0
        return await callback_query.answer(f"{_format_mmss(elapsed)} / {_format_mmss(duration)}")

    if data == "music_hide_menu":
        try:
            await callback_query.message.delete()
        except:
            pass
        return await callback_query.answer()

    if not is_playing_now.get(chat_id):
        await callback_query.answer("لا يوجد شيء قيد التشغيل ♬ً", show_alert=True)
        return

    if data == "music_pause":
        if is_paused.get(chat_id):
            await callback_query.answer("البث متوقف بالفعل", show_alert=True)
            return
        try:
            await call_py.pause(chat_id)
            playback_offset[chat_id] = playback_offset.get(chat_id, 0) + (time.time() - playback_start_time.get(chat_id, time.time()))
            is_paused[chat_id] = True
            await callback_query.answer("تم الإيقاف المؤقت")
            pause_msg = await callback_query.message.reply(f"<b>تم إيقاف البث مؤقتاً بواسطة {user}</b>")
            _track_msg(chat_id, pause_msg.id)
        except:
            await callback_query.answer("خطأ في الإيقاف المؤقت", show_alert=True)

    elif data == "music_resume":
        if not is_paused.get(chat_id):
            await callback_query.answer("البث يعمل بالفعل", show_alert=True)
            return
        try:
            await call_py.resume(chat_id)
            playback_start_time[chat_id] = time.time()
            is_paused[chat_id] = False
            await callback_query.answer("تم الاستئناف")
            resume_msg = await callback_query.message.reply(f"<b>تم استئناف البث بواسطة {user}</b>")
            _track_msg(chat_id, resume_msg.id)
        except:
            await callback_query.answer("خطأ في الاستئناف", show_alert=True)

    elif data == "music_stop":
        music_queue[chat_id] = []
        current_playing[chat_id] = None
        is_playing_now[chat_id] = False
        repeat_mode[chat_id] = False
        changing_stream[chat_id] = False
        is_paused[chat_id] = False
        try: await call_py.leave_call(chat_id)
        except: pass
        await _delete_playing_messages(client, chat_id)
        await callback_query.answer("تم الإيقاف")
        stop_msg = await callback_query.message.reply(f"<b>تم إيقاف التشغيل بواسطة {user}</b>")
        asyncio.create_task(_auto_delete_after(client, chat_id, stop_msg.id))

    elif data == "music_skip":
        if not is_playing_now.get(chat_id):
            return await callback_query.answer("لا يوجد شيء للتخطي", show_alert=True)
        
        queue = music_queue.get(chat_id, [])
        if not queue or len(queue) == 0:
            return await callback_query.answer("لا يوجد شيء للتخطي", show_alert=True)

        await callback_query.answer("تم التخطي")
        skip_msg = await callback_query.message.reply(f"تم تخطي بواسطة {user}")
        _track_msg(chat_id, skip_msg.id)
        await play_next(client, chat_id, force_skip=True)

    elif data == "music_repeat":
        if not is_playing_now.get(chat_id):
            return await callback_query.answer("لا يوجد شيء قيد التشغيل ♬", show_alert=True)
        current = current_playing.get(chat_id)
        if chat_id not in music_queue:
            music_queue[chat_id] = []
        music_queue[chat_id].append(current)
        position = len(music_queue[chat_id])

        header = f"تـمـت الإضـافـة لـلـطـابـور #{position} ♡"
        resp = await send_track_card(client, chat_id, current, header)
        _track_msg(chat_id, _extract_message_id(resp))
        await callback_query.answer("تم التكرار")

    elif data in ("music_back15", "music_fwd15", "music_back30", "music_fwd30"):
        current_time = playback_offset.get(chat_id, 0) + (time.time() - playback_start_time.get(chat_id, time.time()))
        seek_amount = 30 if data in ("music_back30", "music_fwd30") else 15
        if data in ("music_fwd15", "music_fwd30"):
            target = current_time + seek_amount
        else:
            target = max(0, current_time - seek_amount)
        msg = await callback_query.message.reply("<b>جاري التمرير...</b>")
        await perform_seek(client, chat_id, target, msg, user, callback_query=callback_query)

# ============================================================
# أحداث المكالمات
# ============================================================

@Client.on_message(filters.video_chat_started)
async def vc_started_handler(client, message):
    await message.reply("<b>تم بدء محادثة مرئية.</b>")

@Client.on_message(filters.video_chat_ended)
async def vc_ended_handler(client, message):
    call_py, assistant_id, assistant_client = get_assistant()
    chat_id = message.chat.id
    music_queue[chat_id] = []
    current_playing[chat_id] = None
    is_playing_now[chat_id] = False
    is_paused[chat_id] = False
    repeat_mode[chat_id] = False
    changing_stream[chat_id] = False
    try: await call_py.leave_call(chat_id)
    except: pass
    
    dur_text = "0:00"
    if message.video_chat_ended and hasattr(message.video_chat_ended, "duration"):
        total_seconds = message.video_chat_ended.duration
        days, remainder = divmod(total_seconds, 86400)
        dur_text = format_duration(remainder)
        if days > 0:
            dur_text = f"{days}:{dur_text}"
    await message.reply(f"<b>تم إنهاء محادثة مرئية مدتها {dur_text}</b>")

def _from_assistant_filter(_, __, m):
    _, aid, _ = get_assistant()
    return bool(aid) and bool(m.from_user) and m.from_user.id == aid

@Client.on_message(
    filters.private
    & filters.create(_from_assistant_filter)
    & (filters.audio | filters.video | filters.document)
)
async def relay_assistant_media_to_storage(client, message):
    if not STORAGE_CHANNEL:
        return

    target = f"@{STORAGE_CHANNEL}"
    caption_id = (message.caption or "").strip() or None

    try:
        if message.audio:
            sent = await client.send_audio(target, audio=message.audio.file_id, caption=caption_id)
            key_type = "audio"
        elif message.video:
            sent = await client.send_video(target, video=message.video.file_id, caption=caption_id)
            key_type = "video"
        else:
            sent = await client.send_document(target, document=message.document.file_id, caption=caption_id)
            key_type = "audio"

        if caption_id:
            bot_cache.setdefault(key_type, {})
            bot_cache[key_type][caption_id] = sent.id
            save_cache()
    except Exception as e:
        print(f"[Relay to storage error] {e}")

# ============================================================
# أمر جلب السجل (منقول هنا لملف music.py مباشرة عشان يستخدم
# bot_cache و save_cache و get_assistant المحليين هنا نفسهم،
# من غير أي اعتماد على البحث في sys.modules من ملف تاني ممكن يفشل بصمت)
# ============================================================

_HIDDEN_CHARS_RE = re.compile(r"[\u200b\u200c\u200d\u200e\u200f\ufeff]")

def _normalize_command_text(text):
    if not text:
        return ""
    text = _HIDDEN_CHARS_RE.sub("", text)
    text = text.strip()
    for p in ("/", "!"):
        if text.startswith(p):
            text = text[len(p):]
            break
    text = re.sub(r"\s+", " ", text).strip()
    return text

_CHANGE_LIMIT_RE = re.compile(r"^تغيير الحد\s+(\d+)$")

def _change_limit_filter(_, __, m):
    if not m.text or not m.from_user:
        return False
    if not dev_pls(m.from_user.id, m.chat.id):
        return False
    return bool(_CHANGE_LIMIT_RE.match(_normalize_command_text(m.text)))

@Client.on_message(filters.group & filters.create(_change_limit_filter))
async def change_max_play_duration(client, message):
    """أمر للمطور بس: 'تغيير الحد <رقم بالدقايق>' - بيغير الحد الأقصى
    لمدة المقطع المسموح تشغيله بأوامر تشغيل/شغل/فيديو/فيد. أي حاجة فوق
    الرقم ده بيترفض بنفس رسالة 'عذرا هذا الوقت غير مسموح به' المعتادة."""
    match = _CHANGE_LIMIT_RE.match(_normalize_command_text(message.text))
    new_minutes = int(match.group(1))

    if new_minutes <= 0:
        return await message.reply("<b>اكتب رقم دقايق أكبر من صفر</b>")

    r.set(f"{Dev_Zaid}:MaxPlayMinutes", new_minutes)
    await message.reply(f"<b>تم تغيير الحد الأقصى للتشغيل إلى {new_minutes} دقيقة</b>")

def _fetch_log_filter(_, __, m):
    if not m.text or not m.from_user:
        return False
    if not dev_pls(m.from_user.id, m.chat.id):
        return False
    return _normalize_command_text(m.text) == "جلب السجل"

@Client.on_message(filters.group & filters.create(_fetch_log_filter))
async def fetch_storage_log(client, message):
    call_py, assistant_id, assistant_client = get_assistant()

    if not STORAGE_CHANNEL:
        return await message.reply("<b>لم يتم تعيين قناة تخزين</b>")

    if not assistant_client:
        return await message.reply("<b>الحساب المساعد غير متصل. يرجى إضافة المساعد أولاً ليتمكن من سحب السجل.</b>")

    target = f"@{STORAGE_CHANNEL}"

    # تأكيد إن البوت والمساعد الاتنين وصولهم للقناة سليم
    try:
        await client.get_chat(target)
    except Exception as e:
        return await message.reply(
            f"<b>البوت مش عضو/أدمن في قناة التخزين ({STORAGE_CHANNEL}) أو الاسم غلط.\n"
            f"تأكد إن البوت أدمن في القناة.\nالخطأ: {e}</b>"
        )

    try:
        await assistant_client.get_entity(target)
    except Exception as e:
        return await message.reply(
            f"<b>الحساب المساعد مش عضو/أدمن في قناة التخزين ({STORAGE_CHANNEL}) أو الاسم غلط.\n"
            f"تأكد إن الحساب المساعد أدمن في القناة.\nالخطأ: {e}</b>"
        )

    msg_wait = await message.reply("<b>جاري فحص قناة التخزين بواسطة المساعد وبناء ذاكرة البوت...</b>")

    count_audio = 0
    count_video = 0
    count_checked = 0
    last_id = 0  # نكمل من هنا لو حصل انقطاع (FloodWait)، عشان نمسح القناة كلها من غير ما نفوت حاجة

    bot_cache.setdefault("audio", {})
    bot_cache.setdefault("video", {})

    while True:
        try:
            # فحص القناة كاملة من غير أي حد أقصى (limit=None)
            async for m in assistant_client.iter_messages(
                target, limit=None, offset_id=last_id, reverse=True
            ):
                last_id = m.id
                count_checked += 1

                if m.audio or m.video or m.document:
                    # في Telethon: m.text = caption
                    yt_id = m.text if m.text else None

                    if yt_id:
                        yt_id = yt_id.strip()
                        if len(yt_id) <= 15:
                            if m.video:
                                if yt_id not in bot_cache["video"]:
                                    bot_cache["video"][yt_id] = m.id
                                    count_video += 1
                            elif m.audio or m.document:
                                if yt_id not in bot_cache["audio"]:
                                    bot_cache["audio"][yt_id] = m.id
                                    count_audio += 1

                if count_checked % 500 == 0:
                    try:
                        await msg_wait.edit(
                            "<b>جاري الفحص...\n"
                            f"تم فحص: {count_checked} رسالة\n"
                            f"{count_audio} مقطع صوتي | {count_video} مقطع فيديو</b>"
                        )
                    except Exception:
                        pass

            break  # خلصنا فحص القناة كلها من غير أي مقاطعة

        except FloodWaitError as fw:
            await asyncio.sleep(fw.seconds + 1)
            continue  # هنكمل من عند آخر رسالة اتفحصت (last_id)
        except Exception as e:
            return await msg_wait.edit(
                f"<b>خطأ أثناء الفحص: {e}\n"
                f"(تم فحص {count_checked} رسالة لحد دلوقتي، والنتائج اللي اتجمعت اتحفظت)</b>"
            )

    save_cache()
    await msg_wait.edit(
        f"<b>تم الانتهاء من فحص السجل بنجاح! ♡\n\n"
        f"تم فحص: {count_checked} رسالة\n"
        f"{count_audio} مقطع صوتي\n"
        f"{count_video} مقطع فيديو\n\n"
        f"البوت الآن يفرق بينهم بدقة وسيجلبهم من القناة مباشرة.</b>"
    )
