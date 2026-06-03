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

if not API_ID or not API_HASH or not SESSION_STRING:
    print("[!] خطأ: متغيرات البيئة مش موجودة")
    exit(1)

# ==================== المطور ====================
DEV = 7532687479  # أيدي المطور

print("[✓] جاري التشغيل")
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== الملفات ====================
AUTH_FILE = "authorized.json"
BLACK_FILE = "blacklist.json"

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

auth = load_auth()
black = load_black()

# ==================== دوال التحقق ====================
def is_dev(s):
    return s == DEV

def is_owner(s, m):
    return s == m

def is_admin(s, m):
    return m in auth and s in auth[m]

def can_use(s, m):
    # المطور دايم عنده صلاحية
    if is_dev(s):
        return True
    # لو في القائمة السوداء -> ممنوع
    if s in black:
        return False
    # صاحب الجلسة
    if is_owner(s, m):
        return True
    # مشرف مرفوع
    if is_admin(s, m):
        return True
    return False

def can_manage(s, m):
    # رفع وتنزيل المشرفين: للمطور وصاحب الجلسة بس
    if is_dev(s):
        return True
    if is_owner(s, m):
        return True
    return False

# ==================== 1000 شتيمة ====================
insults = [
    "كس أمك", "طيز أمك", "أمك شرموطة", "أمك قحبة", "أمك عاهرة", "أمك زانية", "أمك متناكة",
    "كس أختك", "طيز أختك", "أختك شرموطة", "أختك قحبة", "أختك عاهرة", "أختك زانية",
    "كس مراتك", "طيز مراتك", "مراتك شرموطة", "مراتك قحبة", "مراتك عاهرة",
    "أبوك عرص", "أبوك ديوث", "أبوك قواد", "أخوك عرص", "أخوك ديوث", "جدك خول",
    "يا ابن المتناكة", "يا ابن الشرموطة", "يا ابن القحبة", "يا ابن العاهرة", "يا ابن الزانية",
    "يا عرص", "يا خول", "يا ديوث", "يا قواد", "يا متناك", "يا منيك", "يا شرموط", "يا قحبة",
    "كس أمك الوسخة", "طيز أختك النجسة", "أمك الزبالة", "أختك القذرة", "مراتك المتسخة",
    "أمك بتتناك في الشارع", "أختك بتتناك في الزقاق", "مراتك بتتناك في الحارة",
    "أمك بتتشرموط في البلد", "أختك بتتشرموط في القاهرة", "مراتك بتتشرموط في الأسكندرية",
    "كس أمك في التحرير", "طيز أختك في رمسيس", "أمك بتتناك في العتبة", "أختك بتتناك في بولاق",
    "مراتك بتتناك في الزمالك", "بنتك بتتناك في المعادي", "كس أمك في مدينة نصر",
    "طيز أختك في مصر الجديدة", "أمك بتتناك في شبرا", "أختك بتتناك في حلوان",
    "كس أمك في شرم الشيخ", "طيز أختك في الغردقة", "أمك بتتناك في الأقصر", "أختك بتتناك في أسوان",
    "أمك بتتنيك مع عادل إمام", "أختك بتتناك مع محمد هنيدي", "مراتك بتتناك مع أحمد حلمي",
    "أمك بتتناك مع محمد صلاح", "أختك بتتناك مع تريزيجيه", "مراتك بتتناك مع كهربا",
    "أمك بتتنيك مع عمرو دياب", "أختك بتتناك مع تامر حسني", "مراتك بتتناك مع حماقي",
    "أمك بتتنيك مع السيسي", "أختك بتتناك مع مبارك", "مراتك بتتناك مع مرسي",
    "أمك لبوة", "أختك أحبى", "انت متناك يا ابن اللبوة", "يا أحبى يا ابن الشرموطة",
    "أمك بتتشرمط مع اللبوة", "أختك بتتناك مع الأحبى", "كس أمك اللبوة", "طيز أختك الأحبى",
    "أمك لبوة وأختك أحبى", "أختك أحبى من الحمار", "أمك بتتنيك على قبر قصر النيل",
    "أمك شرموطة من أيام محمد علي", "كس أمك يبن المتناكة", "طيز أختك يبن الشرموطة",
    "أمك بتتنيك على المسطرة", "أختك بتتناك في الحمامات", "كس أمك في شارع محمد علي",
    "طيز أختك في حمامات قصر النيل", "زبر أبوك في طيز أمك", "كس أمك والخنزير",
    "أمك بتتناك من الكلب", "أختك بتتناك من الحمار", "مراتك بتتناك من التيس",
    "أمك شرموطة معتمدة", "أختك قحبة مسجلة", "مراتك عاهرة محترفة",
    "كس أمك يا ابن الكلبة", "طيز أختك يا ابن الخنزيرة", "أمك شرموطة من أيام مبارك",
    "أختك قحبة من زمان عبد الناصر", "مراتك عاهرة من وقت جمال عبد الناصر",
    "كس أمك وعبده موتة", "طيز أختك وشيكابالا", "أمك في حضن رامز جلال",
    "أختك مع بيومي فؤاد", "مراتك مع محمد هنيدي", "أمك بتتنيك في فيلم",
    "أختك بتتناك في مسلسل", "مراتك بتتشرموط في برنامج", "كس أمك يابن الأيام الصعبة",
    "طيز أختك يا ابن الليل الطويل", "أمك بتتنيك في العاصفة", "أختك بتتناك في الزلزال",
    "كس أمك والشدة", "طيز أختك والنيلة", "أمك في القاع", "أختك في القبر", "مراتك في النار",
    "كس أمك يابن الحقارة", "طيز أختك يا ابن الدناءة", "أمك أرخص من الكلب",
    "أختك أرخص من الحمار", "مراتك أرخص من الخنزير", "كس أمك والعار",
    "طيز أختك والفضيحة", "أمك عار على جبين الزمن", "أختك فضيحة في سجلات التاريخ",
    "كس أمك للابد", "طيز أختك للدهر", "أمك خالدة في الشرموطة", "أختك باقية في القحبة",
    "إحنا عارفين أمك يا ديوث", "الكل عارف أختك يا قواد", "البلد كلها عارفة مراتك يا عرص",
    "أمك ناكها الشغالين", "أختك ركبها التلاميذ", "مراتك صطلعت على العساكر",
    "أمك عاملينها نظام", "أختك ماشية على القايمة", "مراتك في القايمة بالعافية",
    "أمك قفلت الدكان", "أختك كسرت الرقم القياسي", "مراتك فازت بجائزة",
    "أمك على رأس العمل", "أختك في الخدمة", "مراتك في الانتظار",
    "كس أمك والمشوار", "طيز أختك والطريق الطويل", "أمك في الضلمة", "أختك في العتمة",
    "كس أمك يابن الجبانة", "طيز أختك يا ابن الخزي", "أمك في الزبالة", "أختك في القمامة",
    "كس أمك والكتاب", "طيز أختك والسطر", "أمك قصة", "أختك رواية", "مراتك ملحمة",
    "كس أمك والذكرى", "طيز أختك والخاطر", "أمك في الذاكرة", "أختك في الضمير",
]

# تكملة للألف
while len(insults) < 1000:
    for i in insults[:50]:
        insults.append(i + " يا عرص")
        insults.append(i + " يا خول")
insults = insults[:1000]
random.shuffle(insults)

stop_txt = "#تم_الختم_علي_كسمك_يبن_الشرموطة"
active = {}
tasks = {}

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
    
    # أمر فصل - للمطور بس (يفصل أي حد حتى صاحب الجلسة)
    if e.raw_text.startswith(".فصل"):
        if not is_dev(sid):
            await client.send_message(e.chat_id, "❌ الأمر ده للمطور بس")
            return
        await del_msg(e.message)
        p = e.raw_text.split()
        if len(p) != 2:
            await client.send_message(e.chat_id, "❌ استخدم: `.فصل [ايدي]`")
            return
        try:
            tid = int(p[1])
            if tid == DEV:
                await client.send_message(e.chat_id, "❌ مش تقدر تفصل المطور نفسه")
                return
            if tid not in black:
                black.append(tid)
                save_black()
                await client.send_message(e.chat_id, f"✅ تم فصل `{tid}`")
                print(f"[✓] تم فصل {tid}")
            else:
                await client.send_message(e.chat_id, f"❌ `{tid}` مفصول بالفعل")
        except:
            await client.send_message(e.chat_id, "❌ الأيدي مش صحيح")
        return
    
    # أمر تشغيل - للمطور بس (يرجع الصلاحية لأي حد)
    if e.raw_text.startswith(".تشغيل"):
        if not is_dev(sid):
            await client.send_message(e.chat_id, "❌ الأمر ده للمطور بس")
            return
        await del_msg(e.message)
        p = e.raw_text.split()
        if len(p) != 2:
            await client.send_message(e.chat_id, "❌ استخدم: `.تشغيل [ايدي]`")
            return
        try:
            tid = int(p[1])
            if tid in black:
                black.remove(tid)
                save_black()
                await client.send_message(e.chat_id, f"✅ تم تشغيل `{tid}`")
                print(f"[✓] تم تشغيل {tid}")
            else:
                await client.send_message(e.chat_id, f"❌ `{tid}` مش مفصول")
        except:
            await client.send_message(e.chat_id, "❌ الأيدي مش صحيح")
        return
    
    # التحقق من الصلاحية الأساسية (القائمة السوداء)
    if not can_use(sid, me.id):
        return
    
    # أمر خلص
    if ".خلص" in e.raw_text:
        await del_msg(e.message)
        for t, tk in tasks.items():
            if not tk.done():
                tk.cancel()
            try:
                ent = await client.get_entity(t)
                nm = get_name(ent)
            except:
                nm = str(t)
            await client.send_message(e.chat_id, f"{nm} {stop_txt}", parse_mode='html')
        tasks.clear()
        active.clear()
        return
    
    # أمر رفع مشرف - للمطور وصاحب الجلسة بس
    if ".رفع مشرف" in e.raw_text:
        if not can_manage(sid, me.id):
            return
        await del_msg(e.message)
        if not e.message.reply_to:
            return
        r = await e.message.get_reply_message()
        if not r or not r.sender_id:
            return
        aid = r.sender_id
        if me.id not in auth:
            auth[me.id] = []
        if aid not in auth[me.id]:
            auth[me.id].append(aid)
            save_auth()
            await client.send_message(e.chat_id, f"✅ تم رفع {r.sender.username or aid} كمشرف")
        else:
            await client.send_message(e.chat_id, f"❌ هو أصلاً مشرف")
        return
    
    # أمر تنزيل مشرف - للمطور وصاحب الجلسة بس
    if ".تنزيل مشرف" in e.raw_text:
        if not can_manage(sid, me.id):
            return
        await del_msg(e.message)
        if not e.message.reply_to:
            return
        r = await e.message.get_reply_message()
        if not r or not r.sender_id:
            return
        aid = r.sender_id
        if me.id in auth and aid in auth[me.id]:
            auth[me.id].remove(aid)
            save_auth()
            await client.send_message(e.chat_id, f"✅ تم تنزيل {r.sender.username or aid} من المشرفين")
        else:
            await client.send_message(e.chat_id, f"❌ مش موجود في المشرفين")
        return
    
    # أمر يلا (يحتاج رد)
    if not e.message.reply_to:
        return
    
    r = await e.message.get_reply_message()
    if not r or not r.sender_id:
        return
    
    tgt = r.sender_id
    tgt_e = r.sender
    nm = get_name(tgt_e)
    
    if ".يلا" in e.raw_text:
        await del_msg(e.message)
        if tgt in active:
            return
        active[tgt] = True
        if tgt in tasks and not tasks[tgt].done():
            tasks[tgt].cancel()
        tasks[tgt] = asyncio.create_task(spam(tgt, nm, e.chat_id))

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
        print(f"[✓] المطور ID: {DEV}")
        print("[✓] البوت شغال 24/7")
        print("[✓] الأوامر: .يلا | .خلص | .رفع مشرف | .تنزيل مشرف | .فصل [ايدي] | .تشغيل [ايدي]")
        await client.run_until_disconnected()
    except Exception as e:
        print(f"[!] خطأ: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
