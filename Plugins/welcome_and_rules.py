"""


███████╗░█████╗░██████╗░███████╗░██████╗
██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝
█████╗░░███████║██████╔╝█████╗░░╚█████╗░
██╔══╝░░██╔══██║██╔══██╗██╔══╝░░░╚═══██╗
██║░░░░░██║░░██║██║░░██║███████╗██████╔╝
╚═╝░░░░░╚═╝░░╚═╝╚═╝░░╚═╝╚══════╝╚═════╝░


[ = This plugin is a part from FARES Source code = ]
{"Developer":"https://t.me/AY_WV"}

"""

import random, re, time, pytz
from datetime import datetime
from threading import Thread
from pyrogram import *
from pyrogram.enums import *
from pyrogram.types import *
from config import *
from helpers.Ranks import *
from helpers.Ranks import isLockCommand

default_welcome = """لا تُسِئ اللفظ وإن ضَاق عليك الرَّد

ɴᴀᴍᴇ ⌯ {الاسم}
ᴜѕᴇʀɴᴀᴍᴇ ⌯ {اليوزر}
𝖣𝖺𝗍𝖾 ⌯ {التاريخ}"""


@Client.on_message(filters.group & (filters.text | filters.photo | filters.video), group=29)
def setWelcomeHandler(c, m):
    k = r.get(f"{Dev_Zaid}:botkey")
    Thread(target=welcomeFunc, args=(c, m, k)).start()


def welcomeFunc(c, m, k):
    if not r.get(f"{m.chat.id}:enable:{Dev_Zaid}"):
        return
    if not m.from_user:
        return
    if r.get(f"{m.chat.id}:mute:{Dev_Zaid}") and not admin_pls(
        m.from_user.id, m.chat.id
    ):
        return
    if r.get(f"{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}"):
        return
    if r.get(f"{m.from_user.id}:mute:{Dev_Zaid}"):
        return
    if r.get(f"{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}"):
        return
    if r.get(f"{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}"):
        return
    if r.get(f"{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}") or r.get(
        f"{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}"
    ):
        return
    text = m.text or m.caption or ""
    name = r.get(f"{Dev_Zaid}:BotName") if r.get(f"{Dev_Zaid}:BotName") else "رعد"
    if text.startswith(f"{name} "):
        text = text.replace(f"{name} ", "")
    if r.get(f"{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}"):
        text = r.get(f"{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}")
    if r.get(f"Custom:{Dev_Zaid}&text={text}"):
        text = r.get(f"Custom:{Dev_Zaid}&text={text}")
    if isLockCommand(m.from_user.id, m.chat.id, text):
        return
    if text == "الغاء" and r.get(f"{m.chat.id}:setWelcome:{m.from_user.id}{Dev_Zaid}"):
        r.delete(f"{m.chat.id}:setWelcome:{m.from_user.id}{Dev_Zaid}")
        return m.reply(f"{k} ابشر لغيت وضع الترحيب")

    if text == "الغاء" and r.get(f"setWelcomeGlobal:{m.from_user.id}{Dev_Zaid}"):
        r.delete(f"setWelcomeGlobal:{m.from_user.id}{Dev_Zaid}")
        return m.reply(f"{k} ابشر لغيت وضع الترحيب العام")

    if text == "الغاء" and r.get(f"{m.chat.id}:setRules:{m.from_user.id}{Dev_Zaid}"):
        r.delete(f"{m.chat.id}:setRules:{m.from_user.id}{Dev_Zaid}")
        return m.reply(f"{k} ابشر لغيت وضع القوانين")

    if r.get(f"{m.chat.id}:setRules:{m.from_user.id}{Dev_Zaid}") and mod_pls(
        m.from_user.id, m.chat.id
    ):
        if not m.text:
            return m.reply(f"{k} القوانين لازم تكون نص بس")
        r.set(f"{m.chat.id}:CustomRules:{Dev_Zaid}", m.text.html)
        r.delete(f"{m.chat.id}:setRules:{m.from_user.id}{Dev_Zaid}")
        return m.reply(f"{k} تم حطيتها")

    if r.get(f"{m.chat.id}:setWelcome:{m.from_user.id}{Dev_Zaid}") and mod_pls(
        m.from_user.id, m.chat.id
    ):
        if m.photo:
            r.set(f"{m.chat.id}:CustomWelcome:{Dev_Zaid}", m.caption.html if m.caption else "")
            r.set(f"{m.chat.id}:CustomWelcomeMedia:{Dev_Zaid}", m.photo.file_id)
            r.set(f"{m.chat.id}:CustomWelcomeMediaType:{Dev_Zaid}", "photo")
        elif m.video:
            r.set(f"{m.chat.id}:CustomWelcome:{Dev_Zaid}", m.caption.html if m.caption else "")
            r.set(f"{m.chat.id}:CustomWelcomeMedia:{Dev_Zaid}", m.video.file_id)
            r.set(f"{m.chat.id}:CustomWelcomeMediaType:{Dev_Zaid}", "video")
        else:
            r.set(f"{m.chat.id}:CustomWelcome:{Dev_Zaid}", m.text.html)
            r.delete(f"{m.chat.id}:CustomWelcomeMedia:{Dev_Zaid}")
            r.delete(f"{m.chat.id}:CustomWelcomeMediaType:{Dev_Zaid}")
        r.delete(f"{m.chat.id}:setWelcome:{m.from_user.id}{Dev_Zaid}")
        return m.reply(f"{k} تم وسوينا الترحيب ياعيني")

    if r.get(f"setWelcomeGlobal:{m.from_user.id}{Dev_Zaid}") and dev_pls(
        m.from_user.id, m.chat.id
    ):
        if m.photo:
            r.set(f"GlobalCustomWelcome:{Dev_Zaid}", m.caption.html if m.caption else "")
            r.set(f"GlobalCustomWelcomeMedia:{Dev_Zaid}", m.photo.file_id)
            r.set(f"GlobalCustomWelcomeMediaType:{Dev_Zaid}", "photo")
        elif m.video:
            r.set(f"GlobalCustomWelcome:{Dev_Zaid}", m.caption.html if m.caption else "")
            r.set(f"GlobalCustomWelcomeMedia:{Dev_Zaid}", m.video.file_id)
            r.set(f"GlobalCustomWelcomeMediaType:{Dev_Zaid}", "video")
        else:
            r.set(f"GlobalCustomWelcome:{Dev_Zaid}", m.text.html)
            r.delete(f"GlobalCustomWelcomeMedia:{Dev_Zaid}")
            r.delete(f"GlobalCustomWelcomeMediaType:{Dev_Zaid}")
        r.delete(f"setWelcomeGlobal:{m.from_user.id}{Dev_Zaid}")
        return m.reply(f"{k} تم وسوينا الترحيب العام لكل الجروبات")

    if text == "مسح القوانين":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            r.delete(f"{m.chat.id}:CustomRules:{Dev_Zaid}")
            return m.reply(f"{k} من عيوني مسحت القوانين")

    if text == "وضع قوانين":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            r.set(f"{m.chat.id}:setRules:{m.from_user.id}{Dev_Zaid}", 1)
            return m.reply(f"{k} ارسل القوانين الحين")

    if text == "الترحيب":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            if not r.get(f"{m.chat.id}:CustomWelcome:{Dev_Zaid}"):
                return m.reply(f"`{default_welcome}`")
            else:
                welcome = r.get(f"{m.chat.id}:CustomWelcome:{Dev_Zaid}")
                return m.reply(f"`{welcome}`")

    if text == "مسح الترحيب":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            r.delete(f"{m.chat.id}:CustomWelcome:{Dev_Zaid}")
            r.delete(f"{m.chat.id}:CustomWelcomeMedia:{Dev_Zaid}")
            r.delete(f"{m.chat.id}:CustomWelcomeMediaType:{Dev_Zaid}")
            return m.reply(f"{k} مسحت الترحيب")

    if text == "وضع الترحيب" or text == "ضع الترحيب":
        if not mod_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        else:
            r.set(f"{m.chat.id}:setWelcome:{m.from_user.id}{Dev_Zaid}", 1)
            return m.reply("""⇜ تمام عيني  
⇜ ارسل رسالة الترحيب الحين (تقدر تبعت فيديو او صورة مع كتابة)

⇜ ملاحظة تقدر تضيف دوال للترحيب مثلا :
⇜ اظهار قوانين المجموعه  ⇠ {القوانين}  
⇜ اظهار اسم العضو ⇠ {الاسم}
⇜ اظهار اليوزر العضو ⇠ {اليوزر}
⇜ اظهار اسم المجموعه ⇠ {المجموعه} 
⇜ اظهار تاريخ دخول العضو ⇠ {التاريخ} 
⇜ اظهار وقت دخول العضو ⇠ {الوقت} 
☆
""")

    if text == "الترحيب العام":
        if not dev_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص المطور بس")
        else:
            g = r.get(f"GlobalCustomWelcome:{Dev_Zaid}")
            if g is None:
                return m.reply(f"{k} مفيش ترحيب عام متحدد")
            return m.reply(f"`{g}`")

    if text == "مسح الترحيب العام":
        if not dev_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص المطور بس")
        else:
            r.delete(f"GlobalCustomWelcome:{Dev_Zaid}")
            r.delete(f"GlobalCustomWelcomeMedia:{Dev_Zaid}")
            r.delete(f"GlobalCustomWelcomeMediaType:{Dev_Zaid}")
            return m.reply(f"{k} مسحت الترحيب العام")

    if text == "وضع ترحيب عام" or text == "ضع ترحيب عام":
        if not dev_pls(m.from_user.id, m.chat.id):
            return m.reply(f"{k} هذا الامر يخص المطور بس")
        else:
            r.set(f"setWelcomeGlobal:{m.from_user.id}{Dev_Zaid}", 1)
            return m.reply("""⇜ تمام يا مطور
⇜ ارسل رسالة الترحيب العام الحين (تقدر تبعت فيديو او صورة مع كتابة)
⇜ هيتطبق تلقائيًا على كل الجروبات اللي معملتش وضع ترحيب خاص بيها
☆
""")


def _resolve_welcome_config(chat_id):
    """بيحدد نص وميديا الترحيب المستخدمة لجروب معين: ترحيب الجروب الخاص
    لو محدد (نص أو ميديا)، وإلا الترحيب العام لكل الجروبات لو محدد،
    وإلا الترحيب الافتراضي."""
    text = r.get(f"{chat_id}:CustomWelcome:{Dev_Zaid}")
    media = r.get(f"{chat_id}:CustomWelcomeMedia:{Dev_Zaid}")
    media_type = r.get(f"{chat_id}:CustomWelcomeMediaType:{Dev_Zaid}")
    if text is None and not media:
        text = r.get(f"GlobalCustomWelcome:{Dev_Zaid}")
        media = r.get(f"GlobalCustomWelcomeMedia:{Dev_Zaid}")
        media_type = r.get(f"GlobalCustomWelcomeMediaType:{Dev_Zaid}")
    if text is None:
        text = default_welcome
    return text, media, media_type


def _send_welcome_for_user(c, chat, me, k, channel):
    """ترحيب عضو واحد - نفس منطق welcomeRespons بالظبط، بس مستخرج في دالة
    مستقلة عشان تتنادى من أكتر من مكان (انضمام مباشر، أو قبول طلب انضمام)."""
    if r.get(f"{chat.id}:disableWelcome:{Dev_Zaid}"):
        return
    if me.id == int(Dev_Zaid):
        return
    # قفل بسيط لمدة قصيرة عشان نمنع ترحيبين لنفس العضو لو تليجرام بعت
    # أكتر من إشعار انضمام لنفس اللحظة (انضمام مباشر + تحديث عضوية)
    lock_key = f"{chat.id}:welcomed:{me.id}:{Dev_Zaid}"
    if r.get(lock_key):
        return
    r.set(lock_key, 1, ex=15)

    welcome, media_id, media_type = _resolve_welcome_config(chat.id)
    if r.get(f"{chat.id}:enableVerify:{Dev_Zaid}") and not pre_pls(me.id, chat.id):
        return
    photo = None
    if not r.get(f"{chat.id}:disableWelcomep:{Dev_Zaid}") and me.photo:
        for photo in c.get_chat_photos(me.id, limit=1):
            photo = photo.file_id
    title = chat.title
    name = me.first_name
    if me.username:
        username = f"@{me.username}"
    else:
        username = f"@{channel}"
    TIME_ZONE = "Asia/Riyadh"
    ZONE = pytz.timezone(TIME_ZONE)
    TIME = datetime.now(ZONE)
    clock = TIME.strftime("%I:%M %p")
    date = TIME.strftime("%d/%m/%Y")
    if r.get(f"{chat.id}:CustomRules:{Dev_Zaid}"):
        rules = r.get(f"{chat.id}:CustomRules:{Dev_Zaid}")
    else:
        rules = """{k} ممنوع نشر الروابط 
{k} ممنوع التكلم او نشر صور اباحيه 
{k} ممنوع اعاده توجيه 
{k} ممنوع العنصرية بكل انواعها 
{k} الرجاء احترام المدراء والادمنيه"""
    w = (
        welcome.replace("{القوانين}", rules)
        .replace("{الاسم}", name)
        .replace("{المجموعه}", title)
        .replace("{الوقت}", clock)
        .replace("{التاريخ}", date)
        .replace("{اليوزر}", username)
    )
    try:
        if media_id and media_type == "video":
            c.send_video(chat.id, media_id, caption=w)
        elif media_id and media_type == "photo":
            c.send_photo(chat.id, media_id, caption=w)
        elif not photo:
            c.send_message(chat.id, w, disable_web_page_preview=True)
        else:
            c.send_photo(chat.id, photo, caption=w)
    except:
        pass


@Client.on_message(filters.new_chat_members, group=4)
def welcomeRespons(c: Client, m: Message):
    if not r.get(f"{m.chat.id}:enable:{Dev_Zaid}"):
        return
    k = r.get(f"{Dev_Zaid}:botkey")
    channel = (
        r.get(f"{Dev_Zaid}:BotChannel") if r.get(f"{Dev_Zaid}:BotChannel") else "eFFb0t"
    )
    print("member")
    if m.new_chat_members:
        for me in m.new_chat_members:
            _send_welcome_for_user(c, m.chat, me, k, channel)


# ====================== ترحيب عند قبول طلب انضمام ======================
# الجروبات الخاصة أو اللي بتطلب موافقة على الانضمام (Join Requests) تليجرام
# مابيبعتش فيها رسالة "انضم فلان" العادية، فـ new_chat_members مايتفعلش خالص.
# الهاندلر ده بيمسك لحظة تحول العضو من غير عضو لعضو (بعد ما يتوافق عليه)
# ويستخدم نفس دالة الترحيب، مع قفل مشترك يمنع تكرار الترحيب لو الحالتين
# اتفعلوا مع بعض لنفس العضو.
def _is_active_member(member):
    """بترجع True لو العضو ده فعليًا موجود جوه الجروب - سواء كانت حالته
    MEMBER عادي، أو مشرف/مالك، أو RESTRICTED بس بصلاحيات افتراضية
    (is_member=True) وده اللي بيحصل غالبًا لما تليجرام يبلغ عن قبول طلب
    انضمام. أي حالة من دول تعتبر "موجود بالفعل" - مش انضمام جديد."""
    if not member:
        return False
    if member.status in (
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.OWNER,
    ):
        return True
    if member.status == ChatMemberStatus.RESTRICTED and getattr(member, "is_member", False):
        return True
    return False


@Client.on_chat_member_updated(filters.group, group=30)
def welcomeOnApprovedJoin(c: Client, u: ChatMemberUpdated):
    if not _is_active_member(u.new_chat_member):
        return
    if _is_active_member(u.old_chat_member):
        return
    if not r.get(f"{u.chat.id}:enable:{Dev_Zaid}"):
        return
    me = u.new_chat_member.user
    if not me or me.is_bot:
        return
    k = r.get(f"{Dev_Zaid}:botkey")
    channel = (
        r.get(f"{Dev_Zaid}:BotChannel") if r.get(f"{Dev_Zaid}:BotChannel") else "eFFb0t"
    )
    _send_welcome_for_user(c, u.chat, me, k, channel)


"""
def welcomeRespons(c,m):
   if not r.get(f'{m.chat.id}:enable:{Dev_Zaid}'):  return
   k = r.get(f'{Dev_Zaid}:botkey')
   channel = r.get(f'{Dev_Zaid}:BotChannel') if r.get(f'{Dev_Zaid}:BotChannel') else 'Y88F8'
   print("member")
   if not r.get(f'{m.chat.id}:disableWelcome:{Dev_Zaid}') and m.new_chat_members:
     if not r.get(f'{m.chat.id}:CustomWelcome:{Dev_Zaid}'):
        welcome = default_welcome
     else:
        welcome = r.get(f'{m.chat.id}:CustomWelcome:{Dev_Zaid}')
     for me in m.new_chat_members:
      if not me.id == int(Dev_Zaid):
        if r.get(f'{m.chat.id}:enableVerify:{Dev_Zaid}') and not pre_pls(me.id,m.chat.id):
          return
        title = m.chat.title
        name = me.first_name
        if me.username:
          username = f'@{me.username}'
        else:
          username = f'@{channel}'
        TIME_ZONE = "Asia/Riyadh"
        ZONE = pytz.timezone(TIME_ZONE)
        TIME = datetime.now(ZONE)
        clock = TIME.strftime("%I:%M %p")
        date = TIME.strftime("%d/%m/%Y")
        if r.get(f'{m.chat.id}:CustomRules:{Dev_Zaid}'):
          rules = r.get(f'{m.chat.id}:CustomRules:{Dev_Zaid}')
        else:
          rules = '''{k} ممنوع نشر الروابط 
{k} ممنوع التكلم او نشر صور اباحيه 
{k} ممنوع اعاده توجيه 
{k} ممنوع العنصرية بكل انواعها 
{k} الرجاء احترام المدراء والادمنيه'''
        w = welcome.replace('{القوانين}',rules).replace('{الاسم}',name).replace('{المجموعه}',title).replace('{الوقت}', clock).replace('{التاريخ}',date).replace('{اليوزر}',username)
        try:
          c.send_message(m.chat.id,w, disable_web_page_preview=True,reply_to_message_id=m.id)
        except:
          c.send_message(m.chat.id,w, disable_web_page_preview=True)
        return True
"""
