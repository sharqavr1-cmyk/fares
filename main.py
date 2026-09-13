import time, redis, os, json, re, requests, asyncio, sys
from pyrogram import *

# ===== قيم ثابتة (Hardcoded) بدل متغيرات البيئة — للاستضافة اللي مفيهاش خاصية تخزين متغيرات =====
os.environ['BOT_TOKEN'] = '8684384582:AAFz2AHkIRxPIDEB_hY6Zx_zldcIWiBrDK4'
os.environ['SUDO_ID'] = '7532687479'
os.environ['STORAGE_CHANNEL'] = 'djhdkdndkdjdkddkfj'
os.environ['REDIS_HOST'] = 'classic-grub-153966.upstash.io'
os.environ['REDIS_PORT'] = '6379'
os.environ['REDIS_PASSWORD'] = 'gQAAAAAAAlluAAIgcDE1NTUzZjRmOWIyMWQ0ZDE1YjMwMjk1NmYxY2EyODZmZg'

r = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    password=os.environ.get('REDIS_PASSWORD') or None,
    ssl=os.environ.get('REDIS_SSL', 'true').lower() == 'true',
    decode_responses=True
)

import pyrogram.raw.types

# قائمة الكلاسات القديمة المعروف إنها اتشالت من pyrogram.raw.types وبتحاول
# PyTgCalls تستوردها. بنحقنها فورًا كخط دفاع أول وسريع.
_known_missing_raw_types = [
    'InputGroupCallSlug',
    'PhoneCallDiscardReasonMigrateConferenceCall',
    'GroupCallParticipantVideo',
    'GroupCallParticipantVideoSourceGroup',
]
for _cls_name in _known_missing_raw_types:
    if not hasattr(pyrogram.raw.types, _cls_name):
        setattr(pyrogram.raw.types, _cls_name, type(_cls_name, (object,), {}))

# ===== ترقيع توافق: PyTgCalls (2.2.11) بيحاول يستورد كلاسات قديمة
# اتشالت أو اتغيرت من pyrogram.errors ومن pyrogram.raw.types (زي
# GroupcallForbidden، أو InputGroupCallSlug/PhoneCallDiscardReasonMigrateConferenceCall
# بتوع المكالمات الجماعية القديمة) بعد ما بايروجرام حدّث الـ API الخاص
# بالمكالمات. من غير الترقيع ده، مجرد استيراد PyTgCalls بيوقع بـ
# ImportError حتى لو الحساب المساعد شغال بتليثون مش بايجرام. بدل ما
# نحدد أسامي معينة، الدالة دي بتجرب تستورد PyTgCalls، ولو فشلت بسبب
# اسم ناقص من pyrogram.errors أو pyrogram.raw.types، بتحقن كلاس وهمي
# بنفس الاسم في المكان الصح وتعيد المحاولة تلقائيًا لحد ما الاستيراد
# ينجح أو يفشل لسبب تاني خالص. =====
def _ensure_pytgcalls_importable(max_tries=50):
    import pyrogram.errors as _pyrogram_errors
    import pyrogram.raw.types as _pyrogram_raw_types
    _import_err_re = re.compile(r"cannot import name '(\w+)' from 'pyrogram\.(errors|raw\.types)'")
    for _ in range(max_tries):
        # لازم نمسح أي جزء اتحمل جزئيًا من محاولة فاشلة قبل ما نعيد المحاولة
        for _mod_name in list(sys.modules):
            if _mod_name == "pytgcalls" or _mod_name.startswith("pytgcalls."):
                del sys.modules[_mod_name]
        try:
            import pytgcalls  # noqa: F401
            from pytgcalls import PyTgCalls  # noqa: F401
            return
        except ImportError as e:
            m = _import_err_re.search(str(e))
            if not m:
                raise
            missing_name, missing_module = m.group(1), m.group(2)
            target = _pyrogram_errors if missing_module == "errors" else _pyrogram_raw_types
            base = Exception if missing_module == "errors" else object
            if hasattr(target, missing_name):
                raise  # الاسم ده متضاف بالفعل ولسه بيفشل - المشكلة حاجة تانية
            setattr(target, missing_name, type(missing_name, (base,), {}))
    raise Exception("فشل ترقيع توافق pyrogram بعد محاولات كتير")


_ensure_pytgcalls_importable()

to_config = """
import redis, os
r = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'classic-grub-153966.upstash.io'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    password=os.environ.get('REDIS_PASSWORD', 'gQAAAAAAAlluAAIgcDE1NTUzZjRmOWIyMWQ0ZDE1YjMwMjk1NmYxY2EyODZmZg'),
    ssl=True,
    decode_responses=True
)
"""

print('''
Loading…
█▒▒▒▒▒▒▒▒▒''')
print('\n\n')

# ===== أولاً: نطلب التوكن والـ SUDO ID =====
if os.environ.get('BOT_TOKEN') and os.environ.get('SUDO_ID'):
  token = os.environ.get('BOT_TOKEN')
  owner_id = int(os.environ.get('SUDO_ID'))
  Dev_Zaid = token.split(':')[0]
  r.set(f'{Dev_Zaid}botowner', owner_id)
else:
  try:
    from information import *
    Dev_Zaid = token.split(':')[0]
    r.set(f'{Dev_Zaid}botowner', owner_id)
  except Exception as e:
    with open ('information.py','w+') as www:
       token = input ('[+] Enter the bot token : ')
       Dev_Zaid = token.split(':')[0]
       if not r.get(f'{Dev_Zaid}botowner'):
         owner_id = int(input('[+] Enter SUDO ID : '))
         r.set(f'{Dev_Zaid}botowner', owner_id)
       else:
          owner_id = int(r.get(f'{Dev_Zaid}botowner'))
       text = 'token = "{}"\nowner_id = {}'
       www.write(text.format(token, owner_id))

  if not r.get(f'{Dev_Zaid}botowner'):
      owner_id = int(input('[+] Enter SUDO ID : '))
      r.set(f'{Dev_Zaid}botowner', owner_id)
  else:
      owner_id = int(r.get(f'{Dev_Zaid}botowner'))

print('''
10% 
███▒▒▒▒▒▒▒ ''')

# ===== ثانياً: نطلب قناة التخزين بس (السيشن بقى بيتضاف من لوحة المطور) =====
if os.environ.get('STORAGE_CHANNEL'):
    STORAGE_CHANNEL = os.environ.get('STORAGE_CHANNEL').strip()
else:
    try:
        from config import STORAGE_CHANNEL
        print("✅ المتغيرات موجودة في config.py")
    except:
        print("\n🚀 يرجى إدخال متغيرات المساعد:")
        STORAGE_CHANNEL = input('[+] Enter STORAGE_CHANNEL : ').strip()
        print("✅ تم حفظ المتغيرات في config.py")

to_config += f'\nSTORAGE_CHANNEL = "{STORAGE_CHANNEL}"'

# ===== بقية الكود =====
to_config += f"\ntoken = '{token}'"
to_config += f"\nDev_Zaid = token.split(':')[0]"
to_config += f"\nDev_Asyuti = Dev_Zaid"
to_config += f"\nsudo_id = {owner_id}"
username = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()["result"]["username"]
to_config += f"\nbotUsername = '{username}'"
to_config += "\nfrom kvsqlite.sync import Client as DB"
to_config += "\nytdb = DB('ytdb.sqlite')"
to_config += "\nsounddb = DB('sounddb.sqlite')"
to_config += "\nwsdb = DB('wsdb.sqlite')"

print('''
30% 
█████▒▒▒▒▒ ''')
with open('config.py','w+') as w:
  w.write(to_config)
print('''
50% 
███████▒▒▒ ''')

# ===== ثالثاً: نظام الحسابات المساعدة المتعددة =====
# بدل حساب مساعد واحد ثابت، دلوقتي البوت بيدعم أكتر من حساب مساعد مع بعض
# (بيتضافوا وبيتمسحوا مباشرة من لوحة المطور، من غير ما نحتاج نعمل ريستارت
# للبوت). كل حساب بيتخزن في Redis برقمه (1، 2، 3...)، ونوعه (تليثون أو
# بايجرام)، وكود الجلسة بتاعه. ASSISTANTS هي القايمة الحية بكل حساب شغال
# فعليًا دلوقتي، وهي اللي بيقرا منها باقي البوت (music.py وغيره).
#
# ملحوظة: كل حساب مساعد بيشتغل بالمكتبة اللي جلسته منها أصلاً (تليثون أو
# بايجرام) - البوت بيجرب الاتنين تلقائي لما تضيف جلسة جديدة ومايهمكش
# مصدرها. البوت الأساسي (app) لسه شغال بـ Pyrogram زي ما هو من غير تغيير.

ASSISTANTS = []
ASSISTANTS_KEY = f'{Dev_Zaid}:assistants'
assistant_client = None
assistant_id = None
call_py = None

# ===== البوت الأساسي (Pyrogram) - بننشئه هنا الأول عشان ناخد نسخة من
# الـ event loop الرئيسي بتاعه (MAIN_LOOP)، ونستخدم نفس اللوب ده بالظبط في
# أي اتصال تليثون/بايجرام/PyTgCalls خاص بالحسابات المساعدة - سواء وقت
# التشغيل الأول أو وقت إضافة/مسح حساب لايف من لوحة المطور (اللي بتتنفذ من
# Thread تاني مختلف). الخلط بين أكتر من event loop هو اللي كان بيسبب
# "asyncio event loop must not change after connection". =====
app = Client(f'{Dev_Zaid}r3d', 24217199, '11c12a66dbd23da592211771db1bce6b',
  bot_token=token,
    plugins={"root": "Plugins"},
    max_concurrent_transmissions=8,  # تسريع تحميل/رفع الملفات (كان 1 بالديفولت وده سبب البطء)
  )

MAIN_LOOP = asyncio.get_event_loop()


async def _async_start_telethon_session(session_string):
    from telethon import TelegramClient as TelethonClientAsync
    from telethon.sessions import StringSession
    client = TelethonClientAsync(StringSession(session_string), 24217199, '11c12a66dbd23da592211771db1bce6b', loop=MAIN_LOOP)
    await client.connect()
    if not await client.is_user_authorized():
        raise Exception("الجلسة غير صالحة أو منتهية")
    me = await client.get_me()
    return client, me.id


async def _async_start_pyrogram_session(session_string):
    from pyrogram import Client as PyroAssistantClient
    client = PyroAssistantClient(
        name=f":memory:{session_string[:8]}",
        api_id=24217199,
        api_hash='11c12a66dbd23da592211771db1bce6b',
        session_string=session_string,
        in_memory=True,
    )
    await client.start()
    me = await client.get_me()
    return client, me.id


async def _async_start_assistant_session(session_string):
    """بتجرب تليثون الأول (زي التصميم القديم)، ولو فشلت بتجرب بايجرام.
    بترجع (النوع, الكلاينت, الآيدي) لو نجحت، أو بترفع Exception لو فشل الاتنين."""
    try:
        client, uid = await _async_start_telethon_session(session_string)
        return "telethon", client, uid
    except Exception as e1:
        try:
            client, uid = await _async_start_pyrogram_session(session_string)
            return "pyrogram", client, uid
        except Exception as e2:
            raise Exception(f"فشل كتليثون ({e1}) وفشل كبايجرام ({e2})")


async def _async_make_call_py(client, max_tries=50):
    import pyrogram.errors as _pyrogram_errors
    _import_err_re = re.compile(r"cannot import name '(\w+)' from 'pyrogram\.errors'")
    for _ in range(max_tries):
        try:
            from pytgcalls import PyTgCalls
            call_py_obj = PyTgCalls(client)
            await call_py_obj.start()
            return call_py_obj
        except ImportError as e:
            m = _import_err_re.search(str(e))
            if not m:
                raise
            missing_name = m.group(1)
            if hasattr(_pyrogram_errors, missing_name):
                raise  # الاسم ده متضاف بالفعل ولسه بيفشل - المشكلة حاجة تانية
            setattr(_pyrogram_errors, missing_name, type(missing_name, (Exception,), {}))
            # لازم نمسح أي جزء من pytgcalls اتحمل جزئيًا عشان يعيد التحميل صح
            for _mod_name in list(sys.modules):
                if _mod_name == "pytgcalls" or _mod_name.startswith("pytgcalls."):
                    del sys.modules[_mod_name]
    raise Exception("فشل ترقيع توافق pyrogram.errors بعد محاولات كتير")


def _sync_legacy_globals():
    global assistant_client, assistant_id, call_py
    if ASSISTANTS:
        assistant_client = ASSISTANTS[0]["client"]
        assistant_id = ASSISTANTS[0]["id"]
        call_py = ASSISTANTS[0]["call_py"]
    else:
        assistant_client = None
        assistant_id = None
        call_py = None


async def _async_stop_one(item):
    try:
        await item["call_py"].stop()
    except Exception:
        pass
    try:
        if item["type"] == "telethon":
            await item["client"].disconnect()
        else:
            await item["client"].stop()
    except Exception:
        pass


async def _async_add_assistant(session_string):
    # لو فيه حساب شغال قبل كده، نقفله الأول قبل ما نضيف الجديد - حساب واحد بس دايمًا
    for old in list(ASSISTANTS):
        await _async_stop_one(old)
        ASSISTANTS.remove(old)
    kind, client, uid = await _async_start_assistant_session(session_string)
    try:
        call_py_obj = await _async_make_call_py(client)
    except ImportError as e:
        try:
            if kind == "telethon":
                await client.disconnect()
            else:
                await client.stop()
        except Exception:
            pass
        if kind == "pyrogram":
            raise Exception(
                "مكتبة PyTgCalls عندك مش متوافقة مع Pyrogram كحساب مساعد "
                "(تعارض إصدارات على السيرفر). استخدم جلسة تليثون بدل كده.\n"
                f"[تفصيل تقني: {e}]"
            ) from e
        raise
    ASSISTANTS.append({
        "type": kind,
        "client": client,
        "call_py": call_py_obj,
        "id": uid,
        "session": session_string,
    })
    r.set(ASSISTANTS_KEY, json.dumps({"type": kind, "session": session_string}))
    _sync_legacy_globals()
    return uid


async def _async_remove_assistant():
    if not ASSISTANTS:
        return False
    for item in list(ASSISTANTS):
        await _async_stop_one(item)
        ASSISTANTS.remove(item)
    r.delete(ASSISTANTS_KEY)
    _sync_legacy_globals()
    return True


def add_assistant(session_string):
    """بتضيف الحساب المساعد وتشغله فورًا (بتقفل أي حساب قديم لو موجود)،
    وترجع آيديه، أو ترفع Exception فيها سبب الفشل. آمنة تتنادى من أي Thread
    (بتنفذ الشغل الفعلي على نفس الـ event loop الرئيسي بتاع البوت عشان
    منوقعش في تعارض لوبات)."""
    future = asyncio.run_coroutine_threadsafe(_async_add_assistant(session_string), MAIN_LOOP)
    return future.result(timeout=60)


def remove_assistant():
    """بتوقف وتفصل الحساب المساعد الحالي، وتمسح جلسته نهائيًا من الذاكرة
    والـ Redis. آمنة تتنادى من أي Thread زي add_assistant بالظبط."""
    future = asyncio.run_coroutine_threadsafe(_async_remove_assistant(), MAIN_LOOP)
    return future.result(timeout=30)


print("🚀 جاري تشغيل الحساب المساعد...")
try:
    stored = r.get(ASSISTANTS_KEY)
    if stored:
        data = json.loads(stored)
        kind = data.get("type")
        session_string = data.get("session")
        try:
            if kind == "telethon":
                client, uid = MAIN_LOOP.run_until_complete(_async_start_telethon_session(session_string))
            else:
                client, uid = MAIN_LOOP.run_until_complete(_async_start_pyrogram_session(session_string))
            call_py_obj = MAIN_LOOP.run_until_complete(_async_make_call_py(client))
            ASSISTANTS.append({
                "type": kind,
                "client": client,
                "call_py": call_py_obj,
                "id": uid,
                "session": session_string,
            })
            print(f"✅ المساعد يعمل: {uid}")
        except Exception as e:
            print(f"❌ فشل تشغيل المساعد: {e}")
    _sync_legacy_globals()
    if not ASSISTANTS:
        print("⚠️ مفيش أي حساب مساعد شغال - ضيفه من لوحة المطور (اضيف مساعد)")
except Exception as e:
    print(f"❌ خطأ أثناء تحميل الحسابات المساعدة: {e}")

if not r.get(f'{Dev_Zaid}:botkey'):
    r.set(f'{Dev_Zaid}:botkey', '⇜')

if not r.get(f'{Dev_Zaid}botname'):
    r.set(f'{Dev_Zaid}botname', 'رعد')

if not r.get(f'{Dev_Zaid}botchannel'):
    r.set(f'{Dev_Zaid}botname', 'eFFb0t')

def Find(text):
  m = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s!()\[\]{};:'\".,<>?«»“”‘’]))"
  url = re.findall(m,text)  
  return [x[0] for x in url]

app.start()
print("✅ البوت يعمل")

print('''
[===========================]

█▀█▀█▀█░█░█▀█▀█▀█░█░█▀█▀█▀█░█
█▀█▄▄█▀█▄▄▄▄█▀█▄▄█▀█▄▄▄▄█▀█▄▄
█▀█▀█▀█▄▄█░█▀█▀█▀█▄▄█░█▀█▀█▄▄
█▀█▄▄█▀█░█▄▄▄▄█▀█▄▄█░█▀█▀█▄▄
█▀█▀█▀█▄▄█▀█▀█▀█▀█▄▄█▀█▀█▀█▄▄
▄▄█▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄

[===========================]

🔣 Your bot started successfully on FARES ☘ Source 🔣

•••••••• @AY_WV - @AY_WV ••••••••


''')
print('''

100% 
██████████''')
if r.get(f'DevGroup:{Dev_Zaid}'):
  id = int(r.get(f'DevGroup:{Dev_Zaid}'))
  try:
    app.send_message(id, "تم اتشغيل البوت بنجاح ✔️")
  except:
    pass
idle()
