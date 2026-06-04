import asyncio
import random
import os
import threading
import json
from flask import Flask
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession

# ==================== Flask server ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))

# ==================== متغيرات البيئة ====================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

# ==================== المطورين ====================
MASTER_DEV = 7532687479
SECONDARY_DEVS = [8770453771]
ALL_DEVS = [MASTER_DEV] + SECONDARY_DEVS

def is_dev(s):
    return s in ALL_DEVS

# ==================== التحقق من DEV ====================
try:
    DEV_CHECK = int(os.getenv("DEV"))
except:
    DEV_CHECK = None

if DEV_CHECK != MASTER_DEV:
    print("[!] خطأ: متغير DEV غير مطابق للمطور الأساسي")
    print("[!] البوت لن يعمل")
    exit(1)

if not API_ID or not API_HASH or not SESSION_STRING:
    print("[!] خطأ: متغيرات البيئة الأساسية مش موجودة")
    exit(1)

print("[✓] جاري التشغيل...")
print(f"[✓] المطور الأساسي: {MASTER_DEV}")
print(f"[✓] المطورون الثانويون: {SECONDARY_DEVS}")
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== الملفات ====================
AUTH_FILE = "authorized.json"
BLACK_FILE = "blacklist.json"
CUSTOM_STOP_FILE = "custom_stop.json"
DEVS_CONTROL_FILE = "devs_control.json"

def load_auth():
    if os.path.exists(AUTH_FILE):
        try:
            with open(AUTH_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
        except:
            return {}
    return {}

def save_auth():
    try:
        with open(AUTH_FILE, 'w', encoding='utf-8') as f:
            json.dump(auth, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_black():
    if os.path.exists(BLACK_FILE):
        try:
            with open(BLACK_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_black():
    try:
        with open(BLACK_FILE, 'w', encoding='utf-8') as f:
            json.dump(black, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_custom_stop():
    if os.path.exists(CUSTOM_STOP_FILE):
        try:
            with open(CUSTOM_STOP_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_custom_stop():
    try:
        with open(CUSTOM_STOP_FILE, 'w', encoding='utf-8') as f:
            json.dump(custom_stop, f, ensure_ascii=False, indent=2)
    except:
        pass

# التحكم - دايمن نبدأ بقاموس فاضي (كل التحكم مقفول في البداية)
def load_devs_control():
    return {}

def save_devs_control():
    try:
        with open(DEVS_CONTROL_FILE, 'w', encoding='utf-8') as f:
            json.dump(devs_control, f, ensure_ascii=False, indent=2)
    except:
        pass

auth = load_auth()
black = load_black()
custom_stop = load_custom_stop()
devs_control = load_devs_control()

# ==================== ختم الإيقاف الافتراضي ====================
DEFAULT_STOP_TXT = "#تم_الختم_علي_كسمك_يبن_الشرموطة"

# ==================== قائمة الأوامر ====================
ALL_COMMANDS = [".يلا", ".خلص", ".فصل", ".تشغيل", ".رفع مشرف", ".تنزيل مشرف", ".تعيين ختم", ".حذف ختم", ".فحص", ".اوامر", ".commands", ".تفعيل تحكم", ".ايقاف تحكم"]
CONTROL_COMMANDS = [".تفعيل تحكم", ".ايقاف تحكم"]

# ==================== دوال الصلاحيات ====================
def is_owner(s, m):
    return s == m

def is_admin(s, m):
    return m in auth and s in auth[m]

def can_use(s, m):
    # المطورين دايمن مسموح لهم
    if is_dev(s):
        return True
    
    # أي شخص في القائمة السوداء - ممنوع حتى لو كان صاحب الجلسة
    if s in black:
        return False
    
    # صاحب الجلسة والمشرفين
    if is_owner(s, m) or is_admin(s, m):
        return True
    
    return False

def can_manage(s, m):
    return is_dev(s) or is_owner(s, m)

def get_user_role(s, m):
    if is_dev(s):
        return "مطور"
    if s in black:
        return "مفصول"
    if is_owner(s, m):
        return "صاحب جلسة"
    if is_admin(s, m):
        return "مشرف"
    return "عادي"

def can_control_target(target_id):
    """التحقق من إمكانية التحكم في شخص معين (للمطورين فقط)"""
    return devs_control.get(str(target_id), False)

# ==================== 1000 شتيمة ====================
insults = [
    "كس أمك", "طيز أمك", "أمك شرموطة", "أمك قحبة", "أختك شرموطة", "كس أختك", "يا ابن المتناكة",
    "كس أمك الوسخة", "طيز أختك النجسة", "أمك بتتناك في الشارع", "أختك بتتناك في الزقاق",
    "كس أمك في التحرير", "طيز أختك في رمسيس", "أمك بتتنيك مع عادل إمام", "أختك بتتناك مع محمد صلاح",
    "أمك لبوة", "أختك أحبى", "انت متناك يا ابن اللبوة", "يا أحبى يا ابن الشرموطة",
    "أمك بتتشرمط مع اللبوة", "أختك بتتناك مع الأحبى", "كس أمك اللبوة", "طيز أختك الأحبى",
    "أمك لبوة وأختك أحبى", "أختك أحبى من الحمار", "أمك بتتنيك على قبر قصر النيل",
    "أمك شرموطة من أيام محمد علي", "كس أمك يبن المتناكة", "طيز أختك يبن الشرموطة",
    "أمك بتتنيك على المسطرة", "أختك بتتناك في الحمامات", "كس أمك في شارع محمد علي",
    "طيز أختك في حمامات قصر النيل", "زبر أبوك في طيز أمك", "كس أمك والخنزير", "أمك شرموطة معتمدة",
    "أختك قحبة مسجلة", "كس أمك يا ابن الكلبة", "طيز أختك يا ابن الخنزيرة", "أمك شرموطة من أيام مبارك",
    "أختك قحبة من زمان عبد الناصر", "أمك في حضن رامز جلال", "أختك مع بيومي فؤاد", "أمك بتتنيك في فيلم",
    "أختك بتتناك في مسلسل", "كس أمك يابن الأيام الصعبة", "طيز أختك يا ابن الليل الطويل", "أمك في القاع",
    "أختك في القبر", "كس أمك يابن الحقارة", "طيز أختك يا ابن الدناءة", "أمك أرخص من الكلب",
    "أختك أرخص من الحمار", "كس أمك والعار", "طيز أختك والفضيحة", "أمك عار على جبين الزمن",
    "أختك فضيحة في سجلات التاريخ", "كس أمك للابد", "طيز أختك للدهر", "أمك خالدة في الشرموطة",
    "أختك باقية في القحبة", "إحنا عارفين أمك يا ديوث", "الكل عارف أختك يا قواد", "أمك ناكها الشغالين",
    "أختك ركبها التلاميذ", "أمك عاملينها نظام", "أختك ماشية على القايمة", "أمك قفلت الدكان",
    "أختك كسرت الرقم القياسي", "أمك على رأس العمل", "أختك في الخدمة", "كس أمك والمشوار",
    "طيز أختك والطريق الطويل", "أمك في الضلمة", "أختك في العتمة", "كس أمك يابن الجبانة",
    "طيز أختك يا ابن الخزي", "أمك في الزبالة", "أختك في القمامة", "كس أمك والكتاب", "طيز أختك والسطر",
    "أمك قصة", "أختك رواية", "كس أمك والذكرى", "طيز أختك والخاطر", "أمك في الذاكرة", "أختك في الضمير"
]

while len(insults) < 1000:
    for i in insults[:50]:
        insults.append(i + " يا عرص")
        insults.append(i + " يا خول")
insults = insults[:1000]
random.shuffle(insults)

active = {}
tasks = {}
waiting_for_stop = {}

async def del_msg(m):
    try:
        await client.delete_messages(m.chat_id, [m.id])
    except:
        pass

def get_name(e):
    try:
        uid = e.id
        fn = e.first_name or ""
        ln = e.last_name or ""
        full = f"{fn} {ln}".strip()
        if not full:
            full = "المستخدم"
        return f'<a href="tg://user?id={uid}">{full}</a>'
    except:
        return str(e.id)

async def send_retry(chat, text, max_r=10, d=900):
    for a in range(max_r):
        try:
            await client.send_message(chat, text, parse_mode='html')
            return True
        except FloodWaitError as e:
            w = e.seconds
            if w < d:
                w = d
            await asyncio.sleep(w)
        except:
            await asyncio.sleep(d)
    return False

@client.on(events.NewMessage)
async def attack(e):
    me = await client.get_me()
    sid = e.sender_id
    
    # ==================== انتظار الختم الجديد ====================
    if sid in waiting_for_stop:
        custom_stop[str(me.id)] = e.raw_text
        save_custom_stop()
        await client.send_message(e.chat_id, "✅ تم تعيين الختم الجديد")
        del waiting_for_stop[sid]
        return
    
    # ==================== التحقق من المطور على بوت تاني ====================
    # إذا كان المرسل مطور والبوت المستهدف مش بوتّه (يعني مطور بيحكم على بوت تاني)
    if is_dev(sid) and sid != me.id:
        # الأمرين دول مسموح بيهم دايمن (تفعيل تحكم وايقاف تحكم)
        if ".تفعيل تحكم" in e.raw_text or ".ايقاف تحكم" in e.raw_text:
            pass  # هنكمل وننفذ الأمر
        elif any(cmd in e.raw_text for cmd in ALL_COMMANDS):
            # دي أوامر محتاجة تفعيل تحكم
            if not can_control_target(me.id):
                # ما نردش خالص (لا نرسل رسالة "فعّل التحكم")
                return
        else:
            # أي كلمة عادية مش أمر - ما يردش عليها خالص
            return
    
    # ==================== أوامر التحكم (شغالة دايمن لأي مطور) ====================
    if ".تفعيل تحكم" in e.raw_text:
        if not is_dev(sid):
            return
        await del_msg(e.message)
        if not e.message.reply_to:
            await client.send_message(e.chat_id, "❌ استخدم الأمر بالرد على رسالة الشخص")
            return
        replied = await e.message.get_reply_message()
        if not replied or not replied.sender_id:
            return
        target_id = replied.sender_id
        devs_control[str(target_id)] = True
        save_devs_control()
        await client.send_message(e.chat_id, f"✅ تم تفعيل التحكم على {replied.sender.username or target_id}")
        return
    
    if ".ايقاف تحكم" in e.raw_text:
        if not is_dev(sid):
            return
        await del_msg(e.message)
        if not e.message.reply_to:
            await client.send_message(e.chat_id, "❌ استخدم الأمر بالرد على رسالة الشخص")
            return
        replied = await e.message.get_reply_message()
        if not replied or not replied.sender_id:
            return
        target_id = replied.sender_id
        devs_control[str(target_id)] = False
        save_devs_control()
        await client.send_message(e.chat_id, f"✅ تم إيقاف التحكم على {replied.sender.username or target_id}")
        return
    
    # ==================== أمر فحص ====================
    if ".فحص" in e.raw_text:
        await del_msg(e.message)
        # المفصول ما ياخدش رد
        if sid in black and not is_dev(sid):
            return
        role = get_user_role(sid, me.id)
        if role == "عادي":
            return
        if sid in black:
            await client.send_message(e.chat_id, "🚫 أنت مفصول من استخدام البوت")
        else:
            if role == "مطور":
                await client.send_message(e.chat_id, "🔰 أنت مطور، عندك صلاحية مطلقة")
            elif role == "صاحب جلسة":
                await client.send_message(e.chat_id, "👑 أنت صاحب الجلسة، عندك صلاحية مطلقة")
            elif role == "مشرف":
                await client.send_message(e.chat_id, "⭐ أنت مشرف، تقدر تستخدم .يلا و .خلص")
        return
    
    # ==================== أمر اوامر ====================
    if ".اوامر" in e.raw_text or ".commands" in e.raw_text:
        await del_msg(e.message)
        # المفصول ما ياخدش رد
        if sid in black and not is_dev(sid):
            return
        role = get_user_role(sid, me.id)
        if role == "عادي":
            return
        
        if role == "مطور":
            msg = """.يلا
.خلص
.رفع مشرف
.تنزيل مشرف
.فحص
.اوامر
.فصل
.تشغيل
.تعيين ختم
.حذف ختم
.تفعيل تحكم
.ايقاف تحكم"""
        elif role == "صاحب جلسة":
            msg = """.يلا
.خلص
.رفع مشرف
.تنزيل مشرف
.فحص
.اوامر
.تعيين ختم
.حذف ختم"""
        elif role == "مشرف":
            msg = """.يلا
.خلص
.فحص
.اوامر"""
        else:
            return
        
        await client.send_message(e.chat_id, msg)
        return
    
    # ==================== التحقق من الصلاحية لباقي الأوامر ====================
    if not can_use(sid, me.id):
        return
    
    # ==================== أوامر تحتاج رد ====================
    if e.message.reply_to:
        r = await e.message.get_reply_message()
        if r and r.sender_id:
            target_id = r.sender_id
            
            # أمر يلا
            if ".يلا" in e.raw_text:
                if is_dev(sid) and target_id != sid:
                    if not can_control_target(target_id):
                        await client.send_message(e.chat_id, f"❌ التحكم مقفول على هذا الشخص. استخدم .تفعيل تحكم بالرد عليه أولا")
                        return
                await del_msg(e.message)
                if is_dev(target_id):
                    await client.send_message(e.chat_id, "❌ يا وغد بدك تشتم المطور؟ تبا لك ولأمثالك أيها اللعين")
                    return
                if target_id in active:
                    return
                active[target_id] = True
                if target_id in tasks and not tasks[target_id].done():
                    tasks[target_id].cancel()
                tasks[target_id] = asyncio.create_task(spam(target_id, get_name(r.sender), e.chat_id))
                return
            
            # أمر فصل
            if ".فصل" in e.raw_text:
                if not is_dev(sid):
                    return
                if target_id != sid and not can_control_target(target_id):
                    await client.send_message(e.chat_id, f"❌ التحكم مقفول على هذا الشخص. استخدم .تفعيل تحكم بالرد عليه أولا")
                    return
                await del_msg(e.message)
                if is_dev(target_id):
                    await client.send_message(e.chat_id, "❌ لا يمكن فصل مطور")
                    return
                if target_id not in black:
                    black.append(target_id)
                    save_black()
                    await client.send_message(e.chat_id, f"✅ تم فصل {r.sender.username or target_id}")
                else:
                    await client.send_message(e.chat_id, f"❌ مفصول بالفعل")
                return
            
            # أمر تشغيل
            if ".تشغيل" in e.raw_text:
                if not is_dev(sid):
                    return
                if target_id != sid and not can_control_target(target_id):
                    await client.send_message(e.chat_id, f"❌ التحكم مقفول على هذا الشخص. استخدم .تفعيل تحكم بالرد عليه أولا")
                    return
                await del_msg(e.message)
                if target_id in black:
                    black.remove(target_id)
                    save_black()
                    await client.send_message(e.chat_id, f"✅ تم تشغيل {r.sender.username or target_id}")
                else:
                    await client.send_message(e.chat_id, f"❌ مش مفصول")
                return
            
            # أمر رفع مشرف
            if ".رفع مشرف" in e.raw_text:
                if not (is_dev(sid) or is_owner(sid, me.id)):
                    return
                if is_dev(sid) and target_id != sid and not can_control_target(target_id):
                    await client.send_message(e.chat_id, f"❌ التحكم مقفول على هذا الشخص. استخدم .تفعيل تحكم بالرد عليه أولا")
                    return
                await del_msg(e.message)
                if is_dev(target_id):
                    await client.send_message(e.chat_id, "❌ لا يمكن رفع مطور كمشرف")
                    return
                if me.id not in auth:
                    auth[me.id] = []
                if target_id not in auth[me.id]:
                    auth[me.id].append(target_id)
                    save_auth()
                    await client.send_message(e.chat_id, f"✅ تم رفع {r.sender.username or target_id} كمشرف")
                else:
                    await client.send_message(e.chat_id, f"❌ هو أصلاً مشرف")
                return
            
            # أمر تنزيل مشرف
            if ".تنزيل مشرف" in e.raw_text:
                if not (is_dev(sid) or is_owner(sid, me.id)):
                    return
                if is_dev(sid) and target_id != sid and not can_control_target(target_id):
                    await client.send_message(e.chat_id, f"❌ التحكم مقفول على هذا الشخص. استخدم .تفعيل تحكم بالرد عليه أولا")
                    return
                await del_msg(e.message)
                if me.id in auth and target_id in auth[me.id]:
                    auth[me.id].remove(target_id)
                    save_auth()
                    await client.send_message(e.chat_id, f"✅ تم تنزيل {r.sender.username or target_id} من المشرفين")
                else:
                    await client.send_message(e.chat_id, f"❌ مش موجود في المشرفين")
                return
    
    # ==================== أوامر بدون رد ====================
    # أمر خلص
    if ".خلص" in e.raw_text:
        if not (is_owner(sid, me.id) or is_admin(sid, me.id) or is_dev(sid)):
            return
        if is_dev(sid) and sid != me.id and not can_control_target(me.id):
            await client.send_message(e.chat_id, f"❌ التحكم مقفول على هذا البوت. استخدم .تفعيل تحكم بالرد على صاحب الجلسة أولا")
            return
        await del_msg(e.message)
        current_stop = custom_stop.get(str(me.id), DEFAULT_STOP_TXT)
        for t, tk in tasks.items():
            if not tk.done():
                tk.cancel()
            try:
                ent = await client.get_entity(t)
                nm = get_name(ent)
            except:
                nm = str(t)
            await client.send_message(e.chat_id, f"{nm} {current_stop}", parse_mode='html')
        tasks.clear()
        active.clear()
        return
    
    # أمر تعيين ختم
    if ".تعيين ختم" in e.raw_text:
        if not (is_dev(sid) or is_owner(sid, me.id)):
            return
        await del_msg(e.message)
        waiting_for_stop[sid] = True
        await client.send_message(e.chat_id, "📝 أرسل الختم الجديد")
        return
    
    # أمر حذف ختم
    if ".حذف ختم" in e.raw_text:
        if not (is_dev(sid) or is_owner(sid, me.id)):
            return
        await del_msg(e.message)
        if str(me.id) in custom_stop:
            del custom_stop[str(me.id)]
            save_custom_stop()
        await client.send_message(e.chat_id, "✅ تم حذف الختم المخصص، سيتم استخدام الختم الافتراضي")
        return

async def spam(t, n, c):
    while active.get(t):
        txt = f"{n} {random.choice(insults)}"
        ok = await send_retry(c, txt)
        if not ok:
            break
        await asyncio.sleep(0.7)
    if t in active:
        del active[t]
    if t in tasks:
        del tasks[t]

async def main():
    print("[✓] جاري الاتصال بتليجرام...")
    try:
        await client.start()
        m = await client.get_me()
        print(f"[✓] تم الدخول: {m.first_name} (ID: {m.id})")
        print(f"[✓] عدد الشتايم: {len(insults)}")
        print(f"[✓] المطور الأساسي: {MASTER_DEV}")
        print(f"[✓] المطورون الثانويون: {SECONDARY_DEVS}")
        print("[✓] البوت شغال 24/7")
        await client.run_until_disconnected()
    except Exception as e:
        print(f"[!] خطأ: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
