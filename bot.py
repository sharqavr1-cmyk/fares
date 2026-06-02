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

# ==================== قايمة الشتايم المصرية الكاملة ====================
egyptian_insults = [
    # الشتايم الأساسية
    "يا ابن المرأة المتناكة",
    "يا ابن الزنية",
    "يا ابن الشرموطة",
    "يا ابن الأحبة",
    "يا اللي أختك أحبة",
    "يا اللي أختك شرموطة",
    "أمك بتتنيك على قبر قصر النيل",
    "أمك شرموطة من أيام محمد علي",
    "أمك لبوة يا ابن المتناكة",
    "أمك أحبة يا ابن الزنية",
    "أمك شرموطة يا ابن الشرموطة",
    "أمك لبوة وانت متناك يا خول",
    "أختك أحبى من الحمار يا عرص",
    "أمك بتتشرمط مع اللبوة في الزريبة",
    "أختك بتتناك مع الأحبى في الزقاق",
    "انت متناك يا ابن اللبوة",
    "يا أحبى يا ابن الشرموطة",
    "يا لبوة يا ابن المتناكة",
    "كس أمك اللبوة يبن الأحبى",
    "طيز أمك الأحبى في وشك يا متناك",
    "أمك بتتناك في الحمامات يا خول",
    "أختك بتتشرمط على المسطرة يا عرص",
    "أمك لبوة في الحمامات",
    "أختك أحبى على المسطرة",
    "كس أمك والحمامات يبن المتناكة",
    "طيز أختك والمسطرات يبن الشرموطة",
    "أمك راكبة الحمامات كلها",
    "أختك ماسكة المسطرة وبتتناك",
    "أمك لبوة وأختك أحبى وانت متناك يا خول",
    "كس أمك اللبوة الحماماتية يبن الشرموطة",
    "أختك الأحبى المسطراتية بتتشرموط في الشارع",
    "أمك بتتنيك على قبر محمد علي يا ابن الزنية",
    "أختك بتتناك في حمامات قصر النيل",
    "انت متناك يا ابن اللبوة الشرموطة",
    "يا أحبى يا ابن المتناكة الوسخة",
    "يا لبوة يا ابن الزنية القحبة",
    "أمك بتتشرمط مع الكلاب الضالة",
    "أختك بتتناك من الحمير في الزريبة",
    "مراتك بتتخول مع اللبوة في العشة",
    "أمك بتتنيك على المسطرة قدام الناس",
    "أختك بتتشرموط في الحمامات على قبر أبوك",
    "انت متناك يا ابن الشرموطة النجسة",
    "يا أحبى يا ابن القحبة المسجلة",
    "يا لبوة يا ابن العاهرة المحترمة",
    
    # شتايم بأسماء أماكن في القاهرة
    "كس أمك في التحرير يا عرص",
    "أختك بتتناك في رمسيس يا خول",
    "أمك بتتشرموط في العتبة يا ديوث",
    "مراتك بتتناك في بولاق يا ابن المتناكة",
    "بنتك بتتخول في مصر الجديدة",
    "كس أختك في الزمالك يا شرموط",
    "طيز أمك في المعادي يا عرص",
    "أمك بتتنيك في شبرا",
    "أختك بتتناك في حلوان",
    
    # شتايم بأسماء أماكن في الأسكندرية
    "أمك بتتشرموط في سيدي جابر",
    "أختك بتتناك في الرمل يا خول",
    "كس أمك في المنشية يا عرص",
    "طيز أختك في بحري يا ابن المتناكة",
    "مراتك بتتناك في سبورتنج",
    "بنتك بتتخول في لوران",
    
    # شتايم بمدن مصرية تانية
    "أمك بتتنيك في طنطا على السكة",
    "أختك بتتناك في المنصورة على النيل",
    "كس أمك في السويس يا عرص",
    "طيز أختك في بورسعيد يا خول",
    "أمك بتتشرموط في الأقصر بين الأعمدة",
    "مراتك بتتناك في أسوان على السد",
    
    # شتايم بأماكن مشهورة
    "أمك بتتنيك في الأهرامات يا خول",
    "أختك بتتناك على الكورنيش يا عرص",
    "كس أمك في سوق العصر يا ابن الشرموطة",
    "طيز أختك في وسط البلد يا متناك",
    "أمك بتتشرموط في مول العرب يا ديوث",
    "مراتك بتتناك في سيتي ستارز",
    "بنتك بتتخول في ستاد القاهرة",
    
    # شتايم بشخصيات حقيقية
    "أمك بتتنيك مع جمال عبد الناصر",
    "أختك بتتناك مع السادات",
    "كس أمك مع مبارك يا عرص",
    "طيز أختك مع مرسي يا خول",
    "أمك بتتشرموط مع السيسي",
    "مراتك بتتناك مع أحمد شفيق",
    
    # شتايم بممثلين
    "أمك بتتنيك مع عادل إمام",
    "أختك بتتناك مع محمد هنيدي",
    "كس أمك مع أحمد حلمي يا عرص",
    "طيز أختك مع كريم عبد العزيز",
    "أمك بتتشرموط مع محمد سعد",
    "مراتك بتتناك مع تامر حسني",
    
    # شتايم بملاعيب
    "أمك بتتنيك مع محمد صلاح",
    "أختك بتتناك مع تريزيجيه",
    "كس أمك مع عصام الحضري يا عرص",
    "طيز أختك مع ميدو",
    "أمك بتتشرموط مع عمرو زكي",
    "مراتك بتتناك مع أبو تريكة",
    
    # ==================== 300 شتيمة جديدة مصححة ====================
    
    "كس أمك في مدينة نصر يا عرص",
    "طيز أختك في مصر الجديدة يا خول",
    "أمك بتتناك في شبرا الخيمة",
    "أختك بتتشرموط في المعادي الجديدة",
    "مراتك بتتناك في التجمع الخامس",
    "بنتك بتتخول في الرحاب",
    "كس أختك في مدينتي",
    "طيز أمك في زايد",
    "أمك بتتنيك في الشيخ زايد",
    "أختك بتتناك في 6 أكتوبر",
    "أختك بتتناك في أبو قير",
    "كس أمك في ميامي يا عرص",
    "طيز أختك في سان استيفانو",
    "أمك بتتشرموط في الصفا",
    "مراتك بتتناك في المنتزه",
    "بنتك بتتخول في برج العرب",
    "كس أختك في العجمي",
    "طيز أمك في الدخيلة",
    "أمك بتتنيك في المحلة الكبرى",
    "أختك بتتناك في كفر الشيخ",
    "كس أمك في بنها يا عرص",
    "طيز أختك في الزقازيق",
    "أمك بتتشرموط في دمنهور",
    "مراتك بتتناك في سوهاج",
    "بنتك بتتخول في قنا",
    "كس أختك في أسيوط",
    "طيز أمك في سمالوط",
    "أمك بتتنيك في المنيا",
    "أمك بتتنيك في شرم الشيخ",
    "أختك بتتناك في دهب",
    "كس أمك في الغردقة يا عرص",
    "طيز أختك في مرسى علم",
    "أمك بتتشرموط في نويبع",
    "مراتك بتتناك في طابا",
    "بنتك بتتخول في سانت كاترين",
    "كس أمك في رأس سدر",
    "طيز أختك في العريش",
    "أمك بتتنيك في رفح",
    "أمك بتتنيك في باب الشعرية",
    "أختك بتتناك في السيدة زينب",
    "كس أمك في الحسين يا عرص",
    "طيز أختك في الجمالية",
    "أمك بتتشرموط في الخليفة",
    "مراتك بتتناك في الدرب الأحمر",
    "بنتك بتتخول في الأزهر",
    "كس أمك في بولاق أبو العلا",
    "طيز أختك في وسط البلد",
    "أمك بتتنيك في الأوبرا",
    "أمك بتتنيك مع سعد زغلول",
    "أختك بتتناك مع مصطفى النحاس",
    "كس أمك مع مكرم عبيد يا عرص",
    "طيز أختك مع الوفد",
    "أمك بتتشرموط مع جمال عبد الناصر",
    "مراتك بتتناك مع السادات",
    "بنتك بتتخول مع مبارك",
    "كس أمك مع مرسي",
    "طيز أختك مع السيسي",
    "أمك بتتنيك مع حازم إمام",
    "أختك بتتناك مع شيكابالا",
    "كس أمك مع زيزو يا عرص",
    "طيز أختك مع السولية",
    "أمك بتتشرموط مع أفشة",
    "مراتك بتتناك مع كهربا",
    "بنتك بتتخول مع رمضان صبحي",
    "كس أمك مع نجم",
    "طيز أختك مع مصطفى محمد",
    "أمك بتتنيك مع أبو جبل",
    "أمك بتتنيك مع حماقي",
    "أختك بتتناك مع تامر عاشور",
    "كس أمك مع عمرو دياب يا عرص",
    "طيز أختك مع محمد منير",
    "أمك بتتشرموط مع شيرين",
    "مراتك بتتناك مع أصالة",
    "بنتك بتتخول مع مي عز الدين",
    "كس أمك مع يسرا",
    "طيز أختك مع إلهام شاهين",
    "أمك بتتنيك مع نانسي عجرم",
    "أمك بتتنيك مع البردوي",
    "أختك بتتناك مع سعد النجار",
    "كس أمك مع كريم عزمي يا عرص",
    "طيز أختك مع الشيف هاني",
    "أمك بتتشرموط مع تامر أمين",
    "مراتك بتتناك مع خالد سعد",
    "بنتك بتتخول مع منة عرفة",
    "أمك بتتنيك مع عادل إمام في مدينة نصر",
    "أختك بتتناك مع محمد صلاح في شرم الشيخ",
    "كس أمك مع عمرو أديب في المهندسين",
    "طيز أختك مع هنيدي في وسط البلد",
    "أمك بتتشرموط مع أحمد حلمي في مول العرب",
    "مراتك بتتناك مع تامر حسني في سيتي ستارز",
    "بنتك بتتخول مع عمرو دياب في أكتوبر",
    "كس أمك مع يحيى الفخراني في الزمالك",
    "طيز أختك مع نور الشريف في المعادي",
    "أمك بتتنيك مع صلاح السعدني في شبرا",
    "أمك بتتنيك في قسم الشرطة",
    "أختك بتتناك في سجن طرة",
    "كس أمك في الأقسام يا عرص",
    "طيز أختك في سجن العقرب",
    "أمك بتتشرموط في النيابة",
    "مراتك بتتناك في المحكمة",
    "بنتك بتتخول في السجن الحربي",
    "أمك بتتنيك في مستشفى القصر العيني",
    "أختك بتتناك في معهد ناصر",
    "كس أمك في مستشفى السلام يا عرص",
    "طيز أختك في مستشفى الشرطة",
    "أمك بتتشرموط في مستشفى الناس",
    "مراتك بتتناك في مستشفى الأطفال",
    "أمك بتتنيك مع بكار",
    "أختك بتتناك مع ونيس",
    "كس أمك مع بوجي يا عرص",
    "طيز أختك مع فطوطة",
    "أمك بتتشرموط مع ميكي",
    "مراتك بتتناك مع منصور",
    "بنتك بتتخول مع سندباد",
    "أمك بتتنيك في الجامع الأزهر",
    "أختك بتتناك في الكنيسة المرقصية",
    "كس أمك في مسجد الحسين يا عرص",
    "طيز أختك في كاتدرائية العباسية",
    "أمك بتتشرموط في مسجد محمد علي",
    "مراتك بتتناك في دير سانت كاترين",
]

stop_insult = "#تم_الختم_علي_كسمك_يبن_الشرموطة_من_عمك_حمو_يخول"

def generate_insult():
    return random.choice(egyptian_insults)

active = {}
tasks = {}
authorized = {}

async def delete_message(msg):
    try:
        await client.delete_messages(msg.chat_id, [msg.id])
    except:
        pass

def get_name_from_entity(entity):
    try:
        username = entity.username
        if username:
            return f"@{username}"
        else:
            first_name = entity.first_name or ""
            last_name = entity.last_name or ""
            full_name = f"{first_name} {last_name}".strip()
            if full_name:
                return f'<a href="tg://user?id={entity.id}">{full_name}</a>'
            else:
                return f'<a href="tg://user?id={entity.id}">المستخدم</a>'
    except:
        return str(entity.id)

async def send_with_retry(chat, text, max_retries=10, delay=900):
    for attempt in range(max_retries):
        try:
            await client.send_message(chat, text)
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
            
            await client.send_message(e.chat_id, f"{name} {stop_insult}")
        
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
        print(f"[✓] عدد الشتايم المحملة: {len(egyptian_insults)}")
        print("[✓] البوت شغال وجاهز 24/7")
        print("[✓] الأوامر: .يلا (بعد الرد) | .خلص | .رفع مشرف (بعد الرد)")
        await client.run_until_disconnected()
    except Exception as e:
        print(f"[!] خطأ: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    asyncio.run(main())