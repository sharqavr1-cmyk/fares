import asyncio
import random
import os
import threading
from flask import Flask
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession

# ==================== Flask server لـ Railway ====================
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
    print("[!] لازم تضيف API_ID, API_HASH, SESSION_STRING")
    exit(1)

print("[✓] جاري استخدام String Session")
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== مخزون الكلمات لتوليد شتايم عشوائية جديدة ====================
# للإناث (الأم، الأخت، البنت، المرة)
female_subjects = ["أمك", "أختك", "مراتك", "بنتك", "خالتك", "عمتك"]
female_body_parts = ["كس", "طيز"]
female_verbs = ["بتتناك", "بتتنيك", "بتتشرموط", "بتتخول", "بتتعرص", "بتتمتع", "بتتاخد"]

# للذكور (الأب، الأخ، الجد، العم، الخال)
male_subjects = ["أبوك", "أخوك", "جدك", "عمك", "خالك"]
male_body_parts = ["زبر", "طيز"]
male_verbs = ["بيتناك", "بيتنيك", "بيتشرموط", "بيتخول", "بيتعرص", "بيتمتع"]

# مشتركة
general_subjects = ["أمك", "أختك", "أبوك", "أخوك"]
general_verbs = ["بيتناك", "بتتناك", "بيتنيك", "بتتنيك", "بيتشرموط", "بتتشرموط", "بيتخول", "بتتخول"]
adjectives = ["الوسخة", "النجسة", "القذرة", "المتعفنة", "الزبالة", "الخرة", "النتنة"]
places = [
    "الشارع", "الزقاق", "الحارة", "البلد", "القاهرة", "الإسكندرية", "كوبري قصر النيل", 
    "شارع محمد علي", "مدينة نصر", "مصر الجديدة", "شبرا", "حلوان", "التحرير", "رمسيس", 
    "العتبة", "بولاق", "الزمالك", "المعادي", "المنتزه", "شرم الشيخ", "الغردقة", "الأهرامات",
    "سوق العصر", "وسط البلد", "مول العرب", "سيتي ستارز", "الحسين", "السيدة زينب", "حمامات قصر النيل"
]
persons = [
    "عادل إمام", "محمد هنيدي", "أحمد حلمي", "محمد صلاح", "عمرو دياب", "تامر حسني", 
    "جمال عبد الناصر", "السيسي", "مبارك", "السادات", "الشيف هاني", "عمرو أديب", 
    "البردوي", "سعد النجار", "بكار", "فطوطة"
]
insults_list = [
    "يا ابن المتناكة", "يا ابن الشرموطة", "يا ابن القحبة", "يا ابن العاهرة", "يا عرص", 
    "يا خول", "يا ديوث", "يا قواد", "يا متناك", "يا منيك", "يا شرموط", "يا لبوة", "يا أحبى"
]

# منع تكرار آخر شتيمة
last_insult = ""

def generate_insult():
    global last_insult
    new_insult = ""
    
    # اختيار نمط الشتيمة عشوائياً
    style = random.choice([1, 2, 3, 4, 5, 6, 7, 8])
    
    if style == 1:  # النمط: كس أمك الوسخة في المكان
        subject = random.choice(female_subjects)
        body = random.choice(female_body_parts)
        adj = random.choice(adjectives)
        place = random.choice(places)
        new_insult = f"{body} {subject} {adj} في {place}"
    
    elif style == 2:  # النمط: أمك بتتناك مع الشخص في المكان
        subject = random.choice(general_subjects)
        verb = random.choice(general_verbs)
        person = random.choice(persons)
        place = random.choice(places)
        new_insult = f"{subject} {verb} مع {person} في {place}"
    
    elif style == 3:  # النمط: يا ابن المتناكة يا عرص
        insult1 = random.choice(insults_list)
        insult2 = random.choice(insults_list)
        new_insult = f"{insult1} {insult2}"
    
    elif style == 4:  # النمط: طيز أختك في وشك
        subject = random.choice(female_subjects)
        body = random.choice(female_body_parts)
        new_insult = f"{body} {subject} في وشك"
    
    elif style == 5:  # النمط: أبوك زبره بيتناك في المكان
        subject = random.choice(male_subjects)
        body = random.choice(male_body_parts)
        verb = random.choice(male_verbs)
        place = random.choice(places)
        new_insult = f"{subject} {body} {verb} في {place}"
    
    elif style == 6:  # النمط: أمك شرموطة يا ابن المتناكة
        subject = random.choice(female_subjects)
        insult = random.choice(insults_list)
        new_insult = f"{subject} {random.choice(['شرموطة', 'قحبة', 'عاهرة'])} {insult}"
    
    elif style == 7:  # النمط: أختك أحبى من الحمار
        subject = random.choice(female_subjects)
        animal = random.choice(["الحمار", "التيس", "الكلب", "الخنزير", "الثور"])
        new_insult = f"{subject} أحبى من {animal}"
    
    else:  # النمط: كس أمك يبن المتناكة
        body = random.choice(female_body_parts)
        subject = random.choice(female_subjects)
        insult = random.choice(insults_list)
        new_insult = f"{body} {subject} {insult}"
    
    # التأكد من عدم تكرار الشتيمة مرتين ورا بعض
    while new_insult == last_insult:
        # إعادة توليد واحدة جديدة
        style = random.choice([1, 2, 3, 4, 5, 6, 7, 8])
        if style == 1:
            subject = random.choice(female_subjects)
            body = random.choice(female_body_parts)
            adj = random.choice(adjectives)
            place = random.choice(places)
            new_insult = f"{body} {subject} {adj} في {place}"
        elif style == 2:
            subject = random.choice(general_subjects)
            verb = random.choice(general_verbs)
            person = random.choice(persons)
            place = random.choice(places)
            new_insult = f"{subject} {verb} مع {person} في {place}"
        elif style == 3:
            insult1 = random.choice(insults_list)
            insult2 = random.choice(insults_list)
            new_insult = f"{insult1} {insult2}"
        elif style == 4:
            subject = random.choice(female_subjects)
            body = random.choice(female_body_parts)
            new_insult = f"{body} {subject} في وشك"
        elif style == 5:
            subject = random.choice(male_subjects)
            body = random.choice(male_body_parts)
            verb = random.choice(male_verbs)
            place = random.choice(places)
            new_insult = f"{subject} {body} {verb} في {place}"
        elif style == 6:
            subject = random.choice(female_subjects)
            insult = random.choice(insults_list)
            new_insult = f"{subject} {random.choice(['شرموطة', 'قحبة', 'عاهرة'])} {insult}"
        elif style == 7:
            subject = random.choice(female_subjects)
            animal = random.choice(["الحمار", "التيس", "الكلب", "الخنزير", "الثور"])
            new_insult = f"{subject} أحبى من {animal}"
        else:
            body = random.choice(female_body_parts)
            subject = random.choice(female_subjects)
            insult = random.choice(insults_list)
            new_insult = f"{body} {subject} {insult}"
    
    last_insult = new_insult
    return new_insult

stop_insult = "#تم_الختم_علي_كسمك_يبن_الشرموطة_من_عمك_حمو_يخول"

active = {}
tasks = {}
authorized = {}

async def delete_message(msg):
    try:
        await client.delete_messages(msg.chat_id, [msg.id])
    except:
        pass

def get_name_from_entity(entity):
    """تجلب اسم المستخدم مع رابط قابل للضغط للملف الشخصي"""
    try:
        user_id = entity.id
        first_name = entity.first_name or ""
        last_name = entity.last_name or ""
        full_name = f"{first_name} {last_name}".strip()
        
        if not full_name:
            full_name = "المستخدم"
        
        return f'<a href="tg://user?id={user_id}">{full_name}</a>'
    except:
        return str(entity.id)

async def send_with_retry(chat, text, max_retries=10, delay=900):
    for attempt in range(max_retries):
        try:
            await client.send_message(chat, text, parse_mode='html')
            return True
        except FloodWaitError as e:
            wait_time = e.seconds
            print(f"[!] الحساب واخد تأخير {wait_time} ثانية من تيليجرام")
            if wait_time < delay:
                wait_time = delay
            print(f"[!] هستنى {wait_time // 60} دقيقة (محاولة {attempt + 1}/{max_retries})...")
            await asyncio.sleep(wait_time)
        except Exception as e:
            error_msg = str(e).lower()
            if "flood" in error_msg or "wait" in error_msg or "too many" in error_msg or "spam" in error_msg:
                wait_time = delay
                print(f"[!] الحساب واخد تأخير بسبب السبام. هستنى {wait_time // 60} دقيقة (محاولة {attempt + 1}/{max_retries})...")
                await asyncio.sleep(wait_time)
            else:
                print(f"[DEBUG] خطأ غير متوقع: {e}")
                return False
    print(f"[!] فشل إرسال الرسالة بعد {max_retries} محاولات")
    return False

@client.on(events.NewMessage)
async def attack(e):
    me = await client.get_me()
    
    if ".خلص" in e.raw_text:
        if e.sender_id != me.id and e.sender_id not in authorized.get(me.id, []):
            return
        
        await delete_message(e.message)
        
        for target, task in tasks.items():
            if not task.done():
                task.cancel()
            
            try:
                entity = await client.get_entity(target)
                name = get_name_from_entity(entity)
            except:
                name = str(target)
            
            await client.send_message(e.chat_id, f"{name} {stop_insult}", parse_mode='html')
        
        tasks.clear()
        active.clear()
        print("[✓] تم الإيقاف ومسح الكل")
        return
    
    if ".رفع مشرف" in e.raw_text:
        if e.sender_id != me.id and e.sender_id not in authorized.get(me.id, []):
            return
        
        await delete_message(e.message)
        
        if not e.message.reply_to:
            return
        
        replied = await e.message.get_reply_message()
        if not replied or not replied.sender_id:
            return
        
        admin_id = replied.sender_id
        
        if me.id not in authorized:
            authorized[me.id] = []
        
        if admin_id not in authorized[me.id]:
            authorized[me.id].append(admin_id)
            await client.send_message(e.chat_id, f"✓ تم رفع {replied.sender.username or admin_id} كمشرف")
            print(f"[✓] تم رفع {admin_id} كمشرف")
        else:
            await client.send_message(e.chat_id, f"هو أصلاً مشرف")
        return
    
    if not e.message.reply_to:
        return
    
    replied = await e.message.get_reply_message()
    if not replied or not replied.sender_id:
        return
    
    target = replied.sender_id
    target_entity = replied.sender
    name = get_name_from_entity(target_entity)
    
    if ".يلا" in e.raw_text:
        await delete_message(e.message)
        
        if e.sender_id != me.id and e.sender_id not in authorized.get(me.id, []):
            return
        
        if target in active:
            return
        
        active[target] = True
        
        if target in tasks and not tasks[target].done():
            tasks[target].cancel()
        
        tasks[target] = asyncio.create_task(spam(target, name, e.chat_id))

async def spam(target, name, chat):
    count = 0
    while active.get(target):
        insult = generate_insult()
        text = f"{name} {insult}"
        success = await send_with_retry(chat, text)
        if not success:
            break
        count += 1
        await asyncio.sleep(0.7)
    
    if target in active:
        del active[target]
    if target in tasks:
        del tasks[target]

async def main():
    print("[✓] جاري الاتصال بتليجرام...")
    
    if not SESSION_STRING:
        print("[!] خطأ: متغير SESSION_STRING مش موجود")
        return
    
    try:
        await client.start()
        me = await client.get_me()
        print(f"[✓] تم الدخول كـ: {me.first_name} (ID: {me.id})")
        print("[✓] نظام توليد الشتايم التلقائي شغال (ده هيألف شتايم جديدة من الكلمات)")
        print("[✓] البوت شغال وجاهز 24/7")
        print("[✓] الأوامر: .يلا (بعد الرد) | .خلص | .رفع مشرف (بعد الرد)")
        await client.run_until_disconnected()
    except Exception as e:
        print(f"[!] خطأ: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    asyncio.run(main())