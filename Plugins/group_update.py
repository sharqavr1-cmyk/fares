import random, re, time
import aiohttp
import asyncio
from threading import Thread
from pyrogram import *
from pyrogram.enums import *
from pyrogram.types import *
from config import *
from .all import list_UwU
from helpers.Ranks import *
from helpers.quran import *
from helpers.memes import *
from pyrogram.raw.functions.users import GetFullUser
from io import BytesIO
from pyrogram.file_id import FileId, FileType, ThumbnailSource

def send_bot_reaction_sync(client, chat_id, message_id, emoji):
    """دالة الريأكت المتزامنة (تشتغل من غير asyncio)"""
    token = client.bot_token
    if not token:
        return
    url = f"https://api.telegram.org/bot{token}/setMessageReaction"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reaction": [{"type": "emoji", "emoji": emoji}],
        "is_big": False
    }
    try:
        import requests
        requests.post(url, json=payload, timeout=5)
    except:
        pass

@Client.on_message(filters.text & filters.group, group=1)
def globalHandler(c,m):
   Thread(target=global_filter,args=(c,m)).start()

def global_filter(c,m):
   if not r.get(f'{m.chat.id}:enable:{Dev_Zaid}'):  return
   if not m.from_user: return
   if r.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not admin_pls(m.from_user.id,m.chat.id):  return 
   if r.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):  return 
   if r.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):  return 
   if r.get(f'{m.chat.id}:lock_global:{Dev_Zaid}'):  return 
   if r.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):  return 
   if r.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):  return 
   if r.get(f'{m.chat.id}:addFilterG:{m.from_user.id}{Dev_Zaid}'):  return
   if r.get(f'{m.chat.id}:delFilterG:{m.from_user.id}{Dev_Zaid}'):  return 
   if r.get(f'{m.chat.id}:addFilter2GG:{m.from_user.id}{Dev_Zaid}'):  return 
   text = m.text
   name = r.get(f'{Dev_Zaid}:BotName') if r.get(f'{Dev_Zaid}:BotName') else 'رعد'
   if text.startswith(f'{name} '):
      text = text.replace(f'{name} ','')
   if r.get(f'{text}:filter:{Dev_Zaid}'):
     get = r.get(f'{text}:filter:{Dev_Zaid}')
     type = re.search(r'type=([^&]+)', get).group(1)
     userID = str(m.from_user.id)
     userNAME = str(m.from_user.first_name)
     userUSERNAME = "@"+m.from_user.username if m.from_user.username else "مافي يوزر"
     userMENTION = m.from_user.mention(userNAME[:25])
     if type == 'text':
        return m.reply(get.split('&text=')[1].replace("<USER_ID>",userID).replace("<USER_NAME>",userNAME).replace("<USER_USERNAME>",userUSERNAME).replace("<USER_MENTION>",userMENTION), disable_web_page_preview=True)
     
     if type == 'photo':
        photo = re.search(r'photo=([^&]+)', get).group(1)
        caption = get.split('&caption=')[1].replace("<USER_ID>",userID).replace("<USER_NAME>",userNAME).replace("<USER_USERNAME>",userUSERNAME).replace("<USER_MENTION>",userMENTION)
        if caption == 'None':
           cpt = None
        else:
           cpt = caption
        return m.reply_photo(photo, caption=cpt)
     
     if type == 'video':
        video = re.search(r'video=([^&]+)', get).group(1)
        caption = get.split('&caption=')[1].replace("<USER_ID>",userID).replace("<USER_NAME>",userNAME).replace("<USER_USERNAME>",userUSERNAME).replace("<USER_MENTION>",userMENTION)
        if caption == 'None':
           cpt = None
        else:
           cpt = caption
        return m.reply_video(video, caption=cpt)
     
     if type == 'voice':
        voice = re.search(r'voice=([^&]+)', get).group(1)
        caption = get.split('&caption=')[1].replace("<USER_ID>",userID).replace("<USER_NAME>",userNAME).replace("<USER_USERNAME>",userUSERNAME).replace("<USER_MENTION>",userMENTION)
        if caption == 'None':
           cpt = None
        else:
           cpt = caption
        return m.reply_voice(voice, caption=cpt)
     
     if type == 'animation':
        animation = re.search(r'animation=([^&]+)', get).group(1)
        caption = get.split('&caption=')[1].replace("<USER_ID>",userID).replace("<USER_NAME>",userNAME).replace("<USER_USERNAME>",userUSERNAME).replace("<USER_MENTION>",userMENTION)
        if caption == 'None':
           cpt = None
        else:
           cpt = caption
        return m.reply_animation(animation, caption=cpt)
     
     if type == 'audio':
        audio = re.search(r'audio=([^&]+)', get).group(1)
        caption = get.split('&caption=')[1].replace("<USER_ID>",userID).replace("<USER_NAME>",userNAME).replace("<USER_USERNAME>",userUSERNAME).replace("<USER_MENTION>",userMENTION)
        if caption == 'None':
           cpt = None
        else:
           cpt = caption
        return m.reply_audio(audio, caption=cpt)
     
     if type == 'doc':
        doc = re.search(r'doc=([^&]+)', get).group(1)
        caption = get.split('&caption=')[1].replace("<USER_ID>",userID).replace("<USER_NAME>",userNAME).replace("<USER_USERNAME>",userUSERNAME).replace("<USER_MENTION>",userMENTION)
        if caption == 'None':
           cpt = None
        else:
           cpt = caption
        return m.reply_document(doc, caption=cpt)

     if type == 'sticker':
        return m.reply_sticker(get.split('&sticker=')[1])
   
   if text == 'المطور':
     id = int(r.get(f'{Dev_Zaid}botowner'))
     get = c.get_chat(id)
     if not get.bio:
       bio = None
     else:
       bio = get.bio
     reply_markup= InlineKeyboardMarkup (
       [[InlineKeyboardButton (get.first_name, url=f"tg://user?id={id}")]]
     )
     if not get.photo:
       return m.reply_animation('https://telegra.ph/file/d9127c65922817d127f04.mp4',caption=bio,reply_markup=reply_markup)
     else:
       get_user = c.invoke(GetFullUser(id=(c.resolve_peer(id))))
       photo = get_user.full_user.profile_photo
       if not photo:
         for photo in c.get_chat_photos(id, limit=1):
           return m.reply_photo(photo.file_id, caption=bio, reply_markup=reply_markup)
         return m.reply_animation('https://telegra.ph/file/d9127c65922817d127f04.mp4',caption=bio,reply_markup=reply_markup)
       video = photo.video_sizes[0] if photo.video_sizes else None
       if video:
         file = BytesIO()
         for byte in c.stream_media(
                message=FileId(
                  file_type=FileType.PHOTO,
                  dc_id=photo.dc_id, media_id=photo.id,
                  access_hash=photo.access_hash,
                  file_reference=photo.file_reference,
                  thumbnail_source=ThumbnailSource.THUMBNAIL,
                  thumbnail_file_type=FileType.PHOTO,
                  thumbnail_size=video.type,
                  volume_id=0, local_id=0
                ).encode()
         ):
           file.write(byte)
           file.name = f'{id}vid.mp4'
           return m.reply_animation(file, caption=bio,reply_markup=reply_markup)
       else:
         for photo in c.get_chat_photos(id, limit=1):
           return m.reply_photo(photo.file_id, caption=bio, reply_markup=reply_markup)

@Client.on_message(filters.text & filters.group, group=2)
def filtersHandler(c,m):
   Thread(target=get_filter,args=(c,m)).start()

def get_filter(c,m):
   if not r.get(f'{m.chat.id}:enable:{Dev_Zaid}'):  return
   if not m.from_user: return
   if r.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not admin_pls(m.from_user.id,m.chat.id):  return 
   if r.get(f'{m.chat.id}:addFilter:{m.from_user.id}{Dev_Zaid}'):  return
   if r.get(f'{m.chat.id}:delFilter:{m.from_user.id}{Dev_Zaid}'):  return 
   if r.get(f'{m.chat.id}:addFilter2:{m.from_user.id}{Dev_Zaid}'):  return 
   if r.get(f'{m.chat.id}:lock_filter:{Dev_Zaid}'):  return 
   if r.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):  return 
   if r.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):  return 
   if r.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):  return 
   if r.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):  return 
   text = m.text
   name = r.get(f'{Dev_Zaid}:BotName') if r.get(f'{Dev_Zaid}:BotName') else 'رعد'
   if text.startswith(f'{name} '):
      text = text.replace(f'{name} ','')
   if r.get(f'{text}:filter:{Dev_Zaid}{m.chat.id}'):
     get = r.get(f'{text}:filter:{Dev_Zaid}{m.chat.id}')
     type = re.search(r'type=([^&]+)', get).group(1)
     userID = str(m.from_user.id)
     userNAME = str(m.from_user.first_name)
     userUSERNAME = "@"+m.from_user.username if m.from_user.username else "مافي يوزر"
     userMENTION = m.from_user.mention(userNAME[:25])
     if type == 'text':
         m.reply(get.split('&text=')[1].replace("<USER_ID>",userID).replace("<USER_NAME>",userNAME).replace("<USER_USERNAME>",userUSERNAME).replace("<USER_MENTION>",userMENTION), disable_web_page_preview=True)
     
     if type == 'photo':
        photo = re.search(r'photo=([^&]+)', get).group(1)
        caption = get.split('&caption=')[1].replace("<USER_ID>",userID).replace("<USER_NAME>",userNAME).replace("<USER_USERNAME>",userUSERNAME).replace("<USER_MENTION>",userMENTION)
        if caption == 'None':
           cpt = None
        else:
           cpt = caption
        m.reply_photo(photo, caption=cpt)
     
     if type == 'video':
        video = re.search(r'video=([^&]+)', get).group(1)
        caption = get.split('&caption=')[1].replace("<USER_ID>",userID).replace("<USER_NAME>",userNAME).replace("<USER_USERNAME>",userUSERNAME).replace("<USER_MENTION>",userMENTION)
        if caption == 'None':
           cpt = None
        else:
           cpt = caption
        m.reply_video(video, caption=cpt)
     
     if type == 'voice':
        voice = re.search(r'voice=([^&]+)', get).group(1)
        caption = get.split('&caption=')[1].replace("<USER_ID>",userID).replace("<USER_NAME>",userNAME).replace("<USER_USERNAME>",userUSERNAME).replace("<USER_MENTION>",userMENTION)
        if caption == 'None':
           cpt = None
        else:
           cpt = caption
        m.reply_voice(voice, caption=cpt)
     
     if type == 'animation':
        animation = re.search(r'animation=([^&]+)', get).group(1)
        caption = get.split('&caption=')[1].replace("<USER_ID>",userID).replace("<USER_NAME>",userNAME).replace("<USER_USERNAME>",userUSERNAME).replace("<USER_MENTION>",userMENTION)
        if caption == 'None':
           cpt = None
        else:
           cpt = caption
        m.reply_animation(animation, caption=cpt)
     
     if type == 'audio':
        audio = re.search(r'audio=([^&]+)', get).group(1)
        caption = get.split('&caption=')[1].replace("<USER_ID>",userID).replace("<USER_NAME>",userNAME).replace("<USER_USERNAME>",userUSERNAME).replace("<USER_MENTION>",userMENTION)
        if caption == 'None':
           cpt = None
        else:
           cpt = caption
        m.reply_audio(audio, caption=cpt)
    
     if type == 'doc':
        doc = re.search(r'doc=([^&]+)', get).group(1)
        caption = get.split('&caption=')[1].replace("<USER_ID>",userID).replace("<USER_NAME>",userNAME).replace("<USER_USERNAME>",userUSERNAME).replace("<USER_MENTION>",userMENTION)
        if caption == 'None':
           cpt = None
        else:
           cpt = caption
        m.reply_document(doc, caption=cpt)

     if type == 'sticker':
         m.reply_sticker(get.split('&sticker=')[1])
        
   if r.get(f'{text}:filterMEM:{Dev_Zaid}{m.chat.id}') and not r.get(f'{m.chat.id}:lock_filterMEM:{Dev_Zaid}'):
     id = int(r.get(f'{text}:filterMEM:{Dev_Zaid}{m.chat.id}'))
     get = c.get_chat(id)
     cap = f"𖡋 𝐍𝐀𝐌𝐄 ⌯ [{get.first_name}](tg://user?id={get.id})\n𖡋 𝐈𝐃 ⌯ `{get.id}`"
     if not get.bio:
       pass
     else:
       cap+=f"\n`{get.bio}`"
     if get.username:
       reply_markup= InlineKeyboardMarkup (
       [[InlineKeyboardButton (get.first_name, url=f"tg://user?id={id}")]]
       )
     else:
       reply_markup=None
     if not get.photo:
       return m.reply(cap,reply_markup=reply_markup)
     else:
       get_user = c.invoke(GetFullUser(id=(c.resolve_peer(id))))
       photo = get_user.full_user.profile_photo
       hash = photo.access_hash
       if r.get(f"{hash}:{id}"):
         return m.reply_animation(r.get(f"{hash}:{id}"), caption=cap, reply_markup=reply_markup) 
       video = photo.video_sizes[0] if photo.video_sizes else None
       if video:
         file = BytesIO()
         for byte in c.stream_media(
                message=FileId(
                  file_type=FileType.PHOTO,
                  dc_id=photo.dc_id, media_id=photo.id,
                  access_hash=photo.access_hash,
                  file_reference=photo.file_reference,
                  thumbnail_source=ThumbnailSource.THUMBNAIL,
                  thumbnail_file_type=FileType.PHOTO,
                  thumbnail_size=video.type,
                  volume_id=0, local_id=0
                ).encode()
         ):
           file.write(byte)
           file.name = f'{id}vid.mp4'
           a= m.reply_animation(file, caption=cap,reply_markup=reply_markup)
           return r.set(f"{hash}:{id}", a.animation.file_id, ex=120)
       else:
         for photo in c.get_chat_photos(id, limit=1):
           return m.reply_photo(photo.file_id, caption=cap, reply_markup=reply_markup)

@Client.on_message(filters.text & filters.group, group=3)
def globalRandomupdate(c,m):
   Thread(target=get_rngp,args=(c,m)).start()
   
def get_rngp(c,m):
   if not r.get(f'{m.chat.id}:enable:{Dev_Zaid}'):  return
   if not m.from_user: return
   if m.from_user.id == c.me.id: return
   if r.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not admin_pls(m.from_user.id,m.chat.id):  return
   if r.get(f'{m.chat.id}:lock_global:{Dev_Zaid}'):  return 
   
   if m.from_user:
     if r.get(f'{m.chat.id}:addFilterRG:{m.from_user.id}{Dev_Zaid}') or r.get(f'{m.chat.id}:delFilterRG:{m.from_user.id}{Dev_Zaid}'):  return 
     if r.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):  return
     if r.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):  return 
   
   text = m.text
   name = r.get(f'{Dev_Zaid}:BotName') if r.get(f'{Dev_Zaid}:BotName') else 'رعد'
   if text.startswith(f'{name} '):
      text = text.replace(f'{name} ','')
   userID = str(m.from_user.id)
   userNAME = str(m.from_user.first_name)
   userUSERNAME = "@"+m.from_user.username if m.from_user.username else "مافي يوزر"
   userMENTION = m.from_user.mention(userNAME[:25])
   if r.get(f'{text}:randomFilter:{Dev_Zaid}'):
     if r.smembers(f'{text}:randomfilter:{Dev_Zaid}'):
       list = r.smembers(f'{text}:randomfilter:{Dev_Zaid}')
       return m.reply(random.sample(list,1)[0].replace('{اسم_البوت}',name).replace("<USER_ID>",userID).replace("<USER_NAME>",userNAME).replace("<USER_USERNAME>",userUSERNAME).replace("<USER_MENTION>",userMENTION), disable_web_page_preview=True)
   name2 = ' '.join(i for i in name)
   
   sb = [
"عييييييييب","عيب","ياكلب عيب","يا قليل التربيه","يا قليل الادب","؟؟؟؟؟؟","ياليت تتأدب","بقص لسانك","حاضر","ياخي عيب","؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟","استغفر الله",
   ]
   lovem = [
"يلبيييه",
"اكثر",
"يعمري",
"اعشقك",
"بدينا كذب",
"احلى من يحبني",
"يحظي والله",
"اكثر اكثر اكثرر",
"يروحي",
"اموت فيك",]
   zg = [
"عييييييييب","عيب","زق بوجهك","يا قليل التربيه","يا قليل الادب","؟؟؟؟؟؟","ياليت تتأدب","بقص لسانك","حاضر","ياخي عيب","؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟",]
   mm = [
"ابركها من ساعة","احبك","اكثر","ترا ازعجتنا","انقلع","طيب","مو اكثر مني","وبعدين ؟","جت من الله","توكل بس"]
   
   # الرد على كلمة بوت مع تفاعل - بتتفعل لو "بوت" او "البوت" جت لوحدها
   # في الجملة (مش بس لما الرسالة كلها تبقى "بوت" بالظبط)
   words = text.split()
   if text == 'بوت' or text == 'البوت' or 'بوت' in words or 'البوت' in words:
       Thread(target=send_bot_reaction_sync, args=(c, m.chat.id, m.id, "❤️")).start()
       bot_name = r.get(f'{Dev_Zaid}:BotName') if r.get(f'{Dev_Zaid}:BotName') else 'رعد'
       replies = [f"أنا مو بوت، أنا اسمي {bot_name}"] + sb
       m.reply(random.choice(replies))
   
   # الرد على اسم البوت مع تفاعل
   if text == name:
       Thread(target=send_bot_reaction_sync, args=(c, m.chat.id, m.id, "❤️")).start()
       replies = ["لبيك", "هلا حب؟", "معك حبيبي", "شيتريد", "أمرني", "تحت أمرك"]
       m.reply(random.choice(replies))
   
   if text == 'احبك':
     m.reply(random.choice(lovem))
   
   if text == 'اكرهك':
     m.reply(random.choice(mm))
   
   if text == 'كليزق' or text == 'كلزق':
     m.reply(random.choice(zg))
   
   if text.startswith('سورة ') or text.startswith('سوره '):
      soura = text.split(None,1)[1].replace('أ','ا').replace('إ','ا').replace('آ','ا').replace('ٰ','').replace('ة','ه')
      if f'سورة {soura}' in TheHolyQuran:
        title = random.choice(["﴿ سَبِّحِ اسمَ رَبِّكَ الأَعلَى ﴾","﴿ وَلَلآخِرَةُ خَيرٌ لَكَ مِنَ الأولى ﴾","﴿ وَكانَ ذلِكَ عَلَى اللَّهِ يَسيرًا ﴾","﴿ لِمَن شاءَ مِنكُم أَن يَتَقَدَّمَ أَو يَتَأَخَّرَ ﴾","﴿ فَمَن عَفا وَأَصلَحَ فَأَجرُهُ عَلَى اللَّهِ ﴾","﴿ هُوَ أَهلُ التَّقوى وَأَهلُ المَغفِرَةِ ﴾","﴿ هَل جَزاءُ الإِحسانِ إِلَّا الإِحسانُ ﴾","﴿ وَلا يَظلِمُ رَبُّكَ أَحَدًا ﴾","﴿ وَمَن يُؤمِن بِاللَّهِ يَهدِ قَلبَهُ ﴾","﴿ وَكانَ رَبُّكَ قَديرًا ﴾","﴿ وَتَطمَئِنُّ قُلوبُهُم بِذِكرِ اللَّهِ ﴾","﴿ سَيَهديهِم وَيُصلِحُ بالَهُم ﴾","﴿ وَوَجَدَكَ ضالًّا فَهَدى ﴾","﴿ فَاسعَوا إِلى ذِكرِ اللَّهِ ﴾","( إِنّ السّاعَةَ آتِيَةٌ أَكَادُ أُخْفِيهَا )","﴿وَلا تَكونوا كَالَّذينَ نَسُوا اللَّهَ فَأَنساهُم أَنفُسَهُم﴾."," ‏﴿أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ﴾ ","﴿ وَقُلْ رَبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا ﴾♡.","‏{وَعَسَىٰ أَن تَكْرَهُوا شَيْئًا وَهُوَ خَيْرٌ لَّكُمْ}","{ لاتحزَن إِنَّ الله مَعَنا }"])
        return m.reply_audio(
          MaherAlmaikulai[f"سورة {soura}"],
          caption=f'سورة {soura}',
          reply_markup=InlineKeyboardMarkup (
            [
            [
              InlineKeyboardButton (title,url='t.me/P_V_R')
            ],
            [
              InlineKeyboardButton ('بصوت سعد الغامدي',callback_data=f'{m.from_user.id}quSaad={MaherAlmaikulai[f"سورة {soura}"].split("MaherSounds/")[1]}')
            ],
            [
              InlineKeyboardButton ('بصوت عبد الباسط عبد الصمد',callback_data=f'{m.from_user.id}quBaset={MaherAlmaikulai[f"سورة {soura}"].split("MaherSounds/")[1]}')
            ],
            [
              InlineKeyboardButton ('بصوت مشاري راشد العفاسي',callback_data=f'{m.from_user.id}qu3fasy={MaherAlmaikulai[f"سورة {soura}"].split("MaherSounds/")[1]}')
            ]
            ]
          )
        )
   
   if text == 'ميمز':
     randomMeme = random.choice(memes_sa)
     return m.reply_audio(
     randomMeme["url"],caption=randomMeme["title"],
     reply_markup=InlineKeyboardMarkup (
       [
         [InlineKeyboardButton ('🇸🇾',callback_data=f'{m.from_user.id}memes_sy'),InlineKeyboardButton ('🇪🇬',callback_data=f'{m.from_user.id}memes_eg')],
         [InlineKeyboardButton ('🇸🇦',callback_data=f'{m.from_user.id}memes_sa'),InlineKeyboardButton ('🇦🇪',callback_data=f'{m.from_user.id}memes_ae')],
         [InlineKeyboardButton ('🇺🇸',callback_data=f'{m.from_user.id}memes_us'),InlineKeyboardButton ('🇮🇶',callback_data=f'{m.from_user.id}memes_iq'),],
         [InlineKeyboardButton ('🧚‍♀️',url='t.me/P_V_R')],
       ]
     )
     )
   
   if (text.startswith('قرآن ') or text.startswith('قران ')) and re.findall('[0-9]+', text):
     page = int(re.findall('[0-9]+', text)[0])
     if page <= 604:
        title = random.choice(["﴿ سَبِّحِ اسمَ رَبِّكَ الأَعلَى ﴾","﴿ وَلَلآخِرَةُ خَيرٌ لَكَ مِنَ الأولى ﴾","﴿ وَكانَ ذلِكَ عَلَى اللَّهِ يَسيرًا ﴾","﴿ لِمَن شاءَ مِنكُم أَن يَتَقَدَّمَ أَو يَتَأَخَّرَ ﴾","﴿ فَمَن عَفا وَأَصلَحَ فَأَجرُهُ عَلَى اللَّهِ ﴾","﴿ هُوَ أَهلُ التَّقوى وَأَهلُ المَغفِرَةِ ﴾","﴿ هَل جَزاءُ الإِحسانِ إِلَّا الإِحسانُ ﴾","﴿ وَلا يَظلِمُ رَبُّكَ أَحَدًا ﴾","﴿ وَمَن يُؤمِن بِاللَّهِ يَهدِ قَلبَهُ ﴾","﴿ وَكانَ رَبُّكَ قَديرًا ﴾","﴿ وَتَطمَئِنُّ قُلوبُهُم بِذِكرِ اللَّهِ ﴾","﴿ سَيَهديهِم وَيُصلِحُ بالَهُم ﴾","﴿ وَوَجَدَكَ ضالًّا فَهَدى ﴾","﴿ فَاسعَوا إِلى ذِكرِ اللَّهِ ﴾","( إِنّ السّاعَةَ آتِيَةٌ أَكَادُ أُخْفِيهَا )","﴿وَلا تَكونوا كَالَّذينَ نَسُوا اللَّهَ فَأَنساهُم أَنفُسَهُم﴾."," ‏﴿أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ﴾ ","﴿ وَقُلْ رَبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا ﴾♡.","‏{وَعَسَىٰ أَن تَكْرَهُوا شَيْئًا وَهُوَ خَيْرٌ لَّكُمْ}","{ لاتحزَن إِنَّ الله مَعَنا }"])
        return m.reply_photo(f'https://raw.githubusercontent.com/maknon/Quran/main/pages-douri/{page}.png',reply_markup=InlineKeyboardMarkup (
          [[
            InlineKeyboardButton (title,url='t.me/P_V_R')
          ]]
        ))

@Client.on_callback_query(filters.regex('memes'))
def memes(c,m):
   if not m.from_user: return
   if str(m.from_user.id) in m.data:
     if m.data.endswith('sy'):
       list = memes_sy
     if m.data.endswith('eg'):
       list = memes_eg
     if m.data.endswith('sa'):
       list = memes_sa
     if m.data.endswith('ae'):
       list = memes_ae
     if m.data.endswith('us'):
       list = memes_us
     if m.data.endswith('iq'):
       list = memes_iq
     randomMeme = random.choice(list)
     try:
       return m.edit_message_media(media=InputMediaAudio(media=randomMeme["url"],caption=randomMeme["title"],),
       reply_markup=m.message.reply_markup)
     except:
       m.message.reply_to_message.reply_audio(randomMeme["url"],caption=randomMeme["title"],reply_markup=m.message.reply_markup)
       return m.message.delete()

@Client.on_callback_query(filters.regex('quSaad'))
def quSaad(c,m):
   if not m.from_user: return
   if m.data.startswith(f'{m.from_user.id}quSaad'):
      soura = m.data.split('=')[1]
      title = random.choice(["﴿ سَبِّحِ اسمَ رَبِّكَ الأَعلَى ﴾","﴿ وَلَلآخِرَةُ خَيرٌ لَكَ مِنَ الأولى ﴾","﴿ وَكانَ ذلِكَ عَلَى اللَّهِ يَسيرًا ﴾","﴿ لِمَن شاءَ مِنكُم أَن يَتَقَدَّمَ أَو يَتَأَخَّرَ ﴾","﴿ فَمَن عَفا وَأَصلَحَ فَأَجرُهُ عَلَى اللَّهِ ﴾","﴿ هُوَ أَهلُ التَّقوى وَأَهلُ المَغفِرَةِ ﴾","﴿ هَل جَزاءُ الإِحسانِ إِلَّا الإِحسانُ ﴾","﴿ وَلا يَظلِمُ رَبُّكَ أَحَدًا ﴾","﴿ وَمَن يُؤمِن بِاللَّهِ يَهدِ قَلبَهُ ﴾","﴿ وَكانَ رَبُّكَ قَديرًا ﴾","﴿ وَتَطمَئِنُّ قُلوبُهُم بِذِكرِ اللَّهِ ﴾","﴿ سَيَهديهِم وَيُصلِحُ بالَهُم ﴾","﴿ وَوَجَدَكَ ضالًّا فَهَدى ﴾","﴿ فَاسعَوا إِلى ذِكرِ اللَّهِ ﴾","( إِنّ السّاعَةَ آتِيَةٌ أَكَادُ أُخْفِيهَا )","﴿وَلا تَكونوا كَالَّذينَ نَسُوا اللَّهَ فَأَنساهُم أَنفُسَهُم﴾."," ‏﴿أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ﴾ ","﴿ وَقُلْ رَبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا ﴾♡.","‏{وَعَسَىٰ أَن تَكْرَهُوا شَيْئًا وَهُوَ خَيْرٌ لَّكُمْ}","{ لاتحزَن إِنَّ الله مَعَنا }"])
      return m.edit_message_media(
        media=InputMediaAudio(
          media=f'https://t.me/SaadSounds/{soura}',
          caption=m.message.caption
        ),
        reply_markup=InlineKeyboardMarkup (
            [
            [
              InlineKeyboardButton (title,url='t.me/P_V_R')
            ],
            [
              InlineKeyboardButton ('بصوت ماهر المعيقلي',callback_data=f'{m.from_user.id}quMaher={soura}')
            ],
            [
              InlineKeyboardButton ('بصوت عبد الباسط عبد الصمد',callback_data=f'{m.from_user.id}quBaset={soura}')
            ],
            [
              InlineKeyboardButton ('بصوت مشاري راشد العفاسي',callback_data=f'{m.from_user.id}qu3fasy={soura}')
            ]
            ]
          )
        )

@Client.on_callback_query(filters.regex('quMaher'))
def quMaher(c,m):
   if not m.from_user: return
   if m.data.startswith(f'{m.from_user.id}quMaher'):
      soura = m.data.split('=')[1]
      title = random.choice(["﴿ سَبِّحِ اسمَ رَبِّكَ الأَعلَى ﴾","﴿ وَلَلآخِرَةُ خَيرٌ لَكَ مِنَ الأولى ﴾","﴿ وَكانَ ذلِكَ عَلَى اللَّهِ يَسيرًا ﴾","﴿ لِمَن شاءَ مِنكُم أَن يَتَقَدَّمَ أَو يَتَأَخَّرَ ﴾","﴿ فَمَن عَفا وَأَصلَحَ فَأَجرُهُ عَلَى اللَّهِ ﴾","﴿ هُوَ أَهلُ التَّقوى وَأَهلُ المَغفِرَةِ ﴾","﴿ هَل جَزاءُ الإِحسانِ إِلَّا الإِحسانُ ﴾","﴿ وَلا يَظلِمُ رَبُّكَ أَحَدًا ﴾","﴿ وَمَن يُؤمِن بِاللَّهِ يَهدِ قَلبَهُ ﴾","﴿ وَكانَ رَبُّكَ قَديرًا ﴾","﴿ وَتَطمَئِنُّ قُلوبُهُم بِذِكرِ اللَّهِ ﴾","﴿ سَيَهديهِم وَيُصلِحُ بالَهُم ﴾","﴿ وَوَجَدَكَ ضالًّا فَهَدى ﴾","﴿ فَاسعَوا إِلى ذِكرِ اللَّهِ ﴾","( إِنّ السّاعَةَ آتِيَةٌ أَكَادُ أُخْفِيهَا )","﴿وَلا تَكونوا كَالَّذينَ نَسُوا اللَّهَ فَأَنساهُم أَنفُسَهُم﴾."," ‏﴿أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ﴾ ","﴿ وَقُلْ رَبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا ﴾♡.","‏{وَعَسَىٰ أَن تَكْرَهُوا شَيْئًا وَهُوَ خَيْرٌ لَّكُمْ}","{ لاتحزَن إِنَّ الله مَعَنا }"])
      return m.edit_message_media(
        media=InputMediaAudio(
          media=f'https://t.me/MaherSounds/{soura}',
          caption=m.message.caption
        ),
        reply_markup=InlineKeyboardMarkup (
            [
            [
              InlineKeyboardButton (title,url='t.me/AY_WV')
            ],
            [
              InlineKeyboardButton ('بصوت سعد الغامدي',callback_data=f'{m.from_user.id}quSaad={soura}')
            ],
            [
              InlineKeyboardButton ('بصوت عبد الباسط عبد الصمد',callback_data=f'{m.from_user.id}quBaset={soura}')
            ],
            [
              InlineKeyboardButton ('بصوت مشاري راشد العفاسي',callback_data=f'{m.from_user.id}qu3fasy={soura}')
            ]
            ]
          )
        )

@Client.on_callback_query(filters.regex('qu3fasy'))
def qu3fasy(c,m):
   if not m.from_user: return
   if m.data.startswith(f'{m.from_user.id}qu3fasy'):
      soura = m.data.split('=')[1]
      title = random.choice(["﴿ سَبِّحِ اسمَ رَبِّكَ الأَعلَى ﴾","﴿ وَلَلآخِرَةُ خَيرٌ لَكَ مِنَ الأولى ﴾","﴿ وَكانَ ذلِكَ عَلَى اللَّهِ يَسيرًا ﴾","﴿ لِمَن شاءَ مِنكُم أَن يَتَقَدَّمَ أَو يَتَأَخَّرَ ﴾","﴿ فَمَن عَفا وَأَصلَحَ فَأَجرُهُ عَلَى اللَّهِ ﴾","﴿ هُوَ أَهلُ التَّقوى وَأَهلُ المَغفِرَةِ ﴾","﴿ هَل جَزاءُ الإِحسانِ إِلَّا الإِحسانُ ﴾","﴿ وَلا يَظلِمُ رَبُّكَ أَحَدًا ﴾","﴿ وَمَن يُؤمِن بِاللَّهِ يَهدِ قَلبَهُ ﴾","﴿ وَكانَ رَبُّكَ قَديرًا ﴾","﴿ وَتَطمَئِنُّ قُلوبُهُم بِذِكرِ اللَّهِ ﴾","﴿ سَيَهديهِم وَيُصلِحُ بالَهُم ﴾","﴿ وَوَجَدَكَ ضالًّا فَهَدى ﴾","﴿ فَاسعَوا إِلى ذِكرِ اللَّهِ ﴾","( إِنّ السّاعَةَ آتِيَةٌ أَكَادُ أُخْفِيهَا )","﴿وَلا تَكونوا كَالَّذينَ نَسُوا اللَّهَ فَأَنساهُم أَنفُسَهُم﴾."," ‏﴿أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ﴾ ","﴿ وَقُلْ رَبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا ﴾♡.","‏{وَعَسَىٰ أَن تَكْرَهُوا شَيْئًا وَهُوَ خَيْرٌ لَّكُمْ}","{ لاتحزَن إِنَّ الله مَعَنا }"])
      return m.edit_message_media(
        media=InputMediaAudio(
          media=f'https://t.me/Al3afasy/{soura}',
          caption=m.message.caption
        ),
        reply_markup=InlineKeyboardMarkup (
            [
            [
              InlineKeyboardButton (title,url='t.me/AY_WV')
            ],
            [
              InlineKeyboardButton ('بصوت سعد الغامدي',callback_data=f'{m.from_user.id}quSaad={soura}')
            ],
            [
              InlineKeyboardButton ('بصوت عبد الباسط عبد الصمد',callback_data=f'{m.from_user.id}quBaset={soura}')
            ],
            [
              InlineKeyboardButton ('بصوت ماهر المعيقلي',callback_data=f'{m.from_user.id}quMaher={soura}')
            ]
            ]
          )
        )

@Client.on_callback_query(filters.regex('quBaset'))
def quBaset(c,m):
   if not m.from_user: return
   if m.data.startswith(f'{m.from_user.id}quBaset'):
      soura = m.data.split('=')[1]
      title = random.choice(["﴿ سَبِّحِ اسمَ رَبِّكَ الأَعلَى ﴾","﴿ وَلَلآخِرَةُ خَيرٌ لَكَ مِنَ الأولى ﴾","﴿ وَكانَ ذلِكَ عَلَى اللَّهِ يَسيرًا ﴾","﴿ لِمَن شاءَ مِنكُم أَن يَتَقَدَّمَ أَو يَتَأَخَّرَ ﴾","﴿ فَمَن عَفا وَأَصلَحَ فَأَجرُهُ عَلَى اللَّهِ ﴾","﴿ هُوَ أَهلُ التَّقوى وَأَهلُ المَغفِرَةِ ﴾","﴿ هَل جَزاءُ الإِحسانِ إِلَّا الإِحسانُ ﴾","﴿ وَلا يَظلِمُ رَبُّكَ أَحَدًا ﴾","﴿ وَمَن يُؤمِن بِاللَّهِ يَهدِ قَلبَهُ ﴾","﴿ وَكانَ رَبُّكَ قَديرًا ﴾","﴿ وَتَطمَئِنُّ قُلوبُهُم بِذِكرِ اللَّهِ ﴾","﴿ سَيَهديهِم وَيُصلِحُ بالَهُم ﴾","﴿ وَوَجَدَكَ ضالًّا فَهَدى ﴾","﴿ فَاسعَوا إِلى ذِكرِ اللَّهِ ﴾","( إِنّ السّاعَةَ آتِيَةٌ أَكَادُ أُخْفِيهَا )","﴿وَلا تَكونوا كَالَّذينَ نَسُوا اللَّهَ فَأَنساهُم أَنفُسَهُم﴾."," ‏﴿أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ﴾ ","﴿ وَقُلْ رَبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا ﴾♡.","‏{وَعَسَىٰ أَن تَكْرَهُوا شَيْئًا وَهُوَ خَيْرٌ لَّكُمْ}","{ لاتحزَن إِنَّ الله مَعَنا }"])
      return m.edit_message_media(
        media=InputMediaAudio(
          media=f'https://t.me/AbdAlbasetS/{soura}',
          caption=m.message.caption
        ),
        reply_markup=InlineKeyboardMarkup (
            [
            [
              InlineKeyboardButton (title,url='t.me/AY_WV')
            ],
            [
              InlineKeyboardButton ('بصوت سعد الغامدي',callback_data=f'{m.from_user.id}quSaad={soura}')
            ],
            [
              InlineKeyboardButton ('بصوت مشاري راشد العفاسي',callback_data=f'{m.from_user.id}qu3fasy={soura}')
            ],
            [
              InlineKeyboardButton ('بصوت ماهر المعيقلي',callback_data=f'{m.from_user.id}quMaher={soura}')
            ]
            ]
          )
        )

@Client.on_message(filters.text & filters.group, group=4)
def randomfiltersHandler(c,m):
   Thread(target=get_rn_filter,args=(c,m)).start()
   
def get_rn_filter(c,m):
   if not r.get(f'{m.chat.id}:enable:{Dev_Zaid}'):  return
   if r.get(f'{m.chat.id}:lock_filter:{Dev_Zaid}'):  return 
   if not m.from_user: return
   if r.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not admin_pls(m.from_user.id,m.chat.id):  return
   if m.from_user:
     if r.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):  return
     if r.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):  return 
     if r.get(f'{m.chat.id}:addFilter:{m.from_user.id}{Dev_Zaid}'):  return
     if r.get(f'{m.chat.id}:delFilter:{m.from_user.id}{Dev_Zaid}'):  return 
     if r.get(f'{m.chat.id}:addFilter2:{m.from_user.id}{Dev_Zaid}'):  return 
     if r.get(f'{m.chat.id}:delFilterR:{m.from_user.id}{Dev_Zaid}') or r.get(f'{m.chat.id}:addFilterR:{m.from_user.id}{Dev_Zaid}') or r.get(f'{m.chat.id}:addFilterR2:{m.from_user.id}{Dev_Zaid}'):  return 
   text = m.text
   name = r.get(f'{Dev_Zaid}:BotName') if r.get(f'{Dev_Zaid}:BotName') else 'رعد'
   userID = str(m.from_user.id)
   userNAME = str(m.from_user.first_name)
   userUSERNAME = "@"+m.from_user.username if m.from_user.username else "مافي يوزر"
   userMENTION = m.from_user.mention(userNAME[:25])
   if text.startswith(f'{name} '):
      text = text.replace(f'{name} ','')
   if r.get(f'{text}:randomFilter:{m.chat.id}{Dev_Zaid}'):
       list = r.smembers(f'{text}:randomfilter:{m.chat.id}{Dev_Zaid}')
       return m.reply(random.sample(list,1)[0].replace("<USER_ID>",userID).replace("<USER_NAME>",userNAME).replace("<USER_USERNAME>",userUSERNAME).replace("<USER_MENTION>",userMENTION), disable_web_page_preview=True)

@Client.on_message(filters.left_chat_member)
def kick_from_gp(c,m):
   if m.left_chat_member.id == int(Dev_Zaid):
        k = r.get(f'{Dev_Zaid}:botkey')
        if not m.from_user: return
        text = f'{k} من「 {m.from_user.mention} 」\n'
        usrr = '@'+m.from_user.username if m.from_user.username else 'مافيه'
        text += f'{k} يوزره : {usrr}\n'
        text += f'{k} ايديه : `{m.from_user.id}`\n'
        text += f'\n{k} قام بطرد البوت من المجموعة :\n\n'
        text += f'{k} اسم المجموعة : {m.chat.title}\n'
        chatusr = '@'+m.chat.username if m.chat.username else 'مافيه'
        text += f'{k} يوزر المجموعة : {chatusr}\n'
        text += f'{k} ايدي المجموعة : `{m.chat.id}`'
        r.srem(f'enablelist:{Dev_Zaid}', m.chat.id)
        r.delete(f'{m.chat.id}:enable:{Dev_Zaid}')
        if r.smembers(f'enablelist:{Dev_Zaid}'):
          text += f'\n{k} عدد المجموعات الآن : {len(r.smembers(f"enablelist:{Dev_Zaid}"))}\n'
        text += f'\n{k} تم مسح جميع بيانات المجموعة'
        text += '\n\n☆'
        if r.get(f'DevGroup:{Dev_Zaid}'):
          c.send_message(int(r.get(f'DevGroup:{Dev_Zaid}')),text,disable_web_page_preview=True)
        else:
          for dev in get_devs_br():
                 try:
                    c.send_message(int(dev), text, disable_web_page_preview=True)
                    time.sleep(3)
                 except:
                    pass

@Client.on_chat_member_updated(filters.group, group=5)
def ChatMemberUpdate(c,m):
    k = r.get(f'{Dev_Zaid}:botkey')
    get_bot_status(c,m,k)
    
def get_bot_status(c,m,k):
  try:
    if m.new_chat_member.status == ChatMemberStatus.MEMBER:
       if m.new_chat_member.user.id == c.me.id:
         if r.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
             if not m.from_user: return
             text = f'{k} من「 {m.from_user.mention} 」\n'
             text += f'{k} تم تعطيل المجموعة تلقائياً\n☆'
             c.send_message(m.chat.id, text)
             text = f'{k} من「 {m.from_user.mention} 」\n'
             usrr = '@'+m.from_user.username if m.from_user.username else 'مافيه'
             text += f'{k} يوزره : {usrr}\n'
             text += f'{k} ايديه : `{m.from_user.id}`\n'
             text += f'\n{k} قام بتنزيل البوت من الأدمن :\n\n'
             text += f'{k} اسم المجموعة : {m.chat.title}\n'
             chatusr = '@'+m.chat.username if m.chat.username else 'مافيه'
             text += f'{k} يوزر المجموعة : {chatusr}\n'
             text += f'{k} ايدي المجموعة : `{m.chat.id}`'             
             r.srem(f'enablelist:{Dev_Zaid}', m.chat.id)
             r.delete(f'{m.chat.id}:enable:{Dev_Zaid}')
             if r.smembers(f'enablelist:{Dev_Zaid}'):
               text += f'\n{k} عدد المجموعات الآن : {len(r.smembers(f"enablelist:{Dev_Zaid}"))}\n'
             text += f'\n{k} تم مسح جميع بيانات المجموعة'
             text += '\n\n☆'
             if r.get(f'DevGroup:{Dev_Zaid}'):
                   c.send_message(int(r.get(f'DevGroup:{Dev_Zaid}')),text)
             else:
               for dev in get_devs_br():
                 try:
                    c.send_message(int(dev), text, disable_web_page_preview=True)
                    time.sleep(3)
                 except:
                    pass
              
                
    if m.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
       if m.new_chat_member.user.id == c.me.id:
          if r.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
             priv = m.new_chat_member.privileges
             if not priv.can_manage_chat or not priv.can_delete_messages or not priv.can_restrict_members or not priv.can_pin_messages or not priv.can_invite_users:
                text = f'{k} من「 {m.from_user.mention} 」\n'
                text += f'{k} تم تعطيل المجموعة تلقائياً\n☆'
                c.send_message(m.chat.id, text)
                r.delete(f'{m.chat.id}:enable:{Dev_Zaid}')
                text = f'{k} من「 {m.from_user.mention} 」\n'
                usrr = '@'+m.from_user.username if m.from_user.username else 'مافيه'
                text += f'{k} يوزره : {usrr}\n'
                text += f'{k} ايديه : `{m.from_user.id}`\n'
                text += f'\n{k} قام بتعديل صلاحية البوت بمجموعة :\n\n'
                text += f'{k} اسم المجموعة : {m.chat.title}\n'
                chatusr = '@'+m.chat.username if m.chat.username else 'مافيه'
                text += f'{k} يوزر المجموعة : {chatusr}\n'
                text += f'{k} ايدي المجموعة : `{m.chat.id}`'
                if r.smembers(f'enablelist:{Dev_Zaid}'):
                  text += f'\n{k} عدد المجموعات الآن : {len(r.smembers(f"enablelist:{Dev_Zaid}"))}\n'
                text += f'\n{k} تم مسح جميع بيانات المجموعة'
                text += '\n\n☆'
                if r.get(f'DevGroup:{Dev_Zaid}'):
                   c.send_message(int(r.get(f'DevGroup:{Dev_Zaid}')),text,disable_web_page_preview=True)
                else:
                  for dev in get_devs_br():
                    try:
                      c.send_message(int(dev), text, disable_web_page_preview=True)
                      time.sleep(3)
                    except:
                      pass
                return True
                
          if not r.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
             if r.get(f'DisableBot:{Dev_Zaid}'):
               return c.send_message(m.chat.id, f'{k} تم تعطيل البوت الخدمي من المطور')
             priv = m.new_chat_member.privileges
             if priv.can_manage_chat and priv.can_delete_messages and priv.can_restrict_members and priv.can_pin_messages and priv.can_invite_users:
                text = f'{k} من「 {m.from_user.mention} 」\n'
                text += f'{k} تم تفعيل المجموعة تلقائياً\n☆'
                c.send_message(m.chat.id, text, reply_markup=InlineKeyboardMarkup ([[InlineKeyboardButton ('Commands', url=f'https://t.me/{botUsername}?start=Commands')]]))
                r.set(f'{m.chat.id}:enable:{Dev_Zaid}', 1)
                r.sadd(f'enablelist:{Dev_Zaid}', m.chat.id)
                r.set(f'{m.chat.id}:rankOWNER:{m.from_user.id}{Dev_Zaid}', 1)
                r.sadd(f'{m.chat.id}:listOWNER:{Dev_Zaid}', m.from_user.id)
                for member in m.chat.get_members(filter=ChatMembersFilter.ADMINISTRATORS):
                   if not member.user.is_bot and not member.user.is_deleted:
                      if member.status == ChatMemberStatus.OWNER:
                         r.set(f'{m.chat.id}:rankGOWNER:{member.user.id}{Dev_Zaid}', 1)
                         r.sadd(f'{m.chat.id}:listGOWNER:{Dev_Zaid}', member.user.id)
                         r.sadd(f'{member.user.id}:groups', m.chat.id)
                      if member.status == ChatMemberStatus.ADMINISTRATOR:
                         r.set(f'{m.chat.id}:rankADMIN:{member.user.id}{Dev_Zaid}', 1)
                         r.sadd(f'{m.chat.id}:listADMIN:{Dev_Zaid}', member.user.id)
                get = c.get_chat(m.chat.id)
                text = f'{k} من「 {m.from_user.mention} 」\n'
                usrr = '@'+m.from_user.username if m.from_user.username else 'مافيه'
                text += f'{k} يوزره : {usrr}\n'
                text += f'{k} ايديه : `{m.from_user.id}`\n'
                text += f'\n{k} تم تفعيل البوت بمجموعة جديدة :\n\n'
                text += f'{k} اسم المجموعة : {m.chat.title}\n'
                chatusr = '@'+m.chat.username if m.chat.username else 'مافيه'
                text += f'{k} يوزر المجموعة : {chatusr}\n'
                text += f'{k} ايدي المجموعة : `{m.chat.id}`'
                if get.invite_link:
                  reply_markup=InlineKeyboardMarkup ([[InlineKeyboardButton (m.chat.title,url=get.invite_link)]])
                else:
                  reply_markup=None
                if r.smembers(f'enablelist:{Dev_Zaid}'):
                   text += f'\n{k} عدد المجموعات الآن : {len(r.smembers(f"enablelist:{Dev_Zaid}"))}\n'
                text += '\n\n☆'
                if r.get(f'DevGroup:{Dev_Zaid}'):
                   c.send_message(int(r.get(f'DevGroup:{Dev_Zaid}')),text,reply_markup=reply_markup,disable_web_page_preview=True)
                else:
                  for dev in get_devs_br():
                    try:
                      c.send_message(int(dev), text, disable_web_page_preview=True,reply_markup=reply_markup)  
                      time.sleep(3)
                    except:
                      pass
  except:
    pass

@Client.on_message((filters.group | filters.channel) & filters.text, group=6)
async def EnableAndDisablegroup(c,m):
  text = m.text
  k = r.get(f'{Dev_Zaid}:botkey')
  if not text:
      return

  # ====================== تفعيل/تعطيل يدوي للقنوات ======================
  # التفعيل التلقائي للقنوات بيحصل لوحده لما البوت يتضاف أدمن (my_chat_member)،
  # لكن لو البوت "نسي" القناة (البيانات اتمسحت من الداتابيز مثلاً)، الأمر ده
  # بيدي وسيلة يدوية لإعادة التفعيل بنفس طريقة الجروب - بالكتابة بس.
  # مفيش يوزر معروف هنا لأن تليجرام مايسمحش غير للمشرفين يبعتوا في فيد
  # القناة، فبنثق إن اللي كتب مشرف بدل ما نطلب هوية تليجرام مش هيديها.
  if m.chat.type == ChatType.CHANNEL:
    if text == 'تفعيل':
      if r.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return await m.reply(f'{k} القناة مفعلة من قبل يالطيب')
      if r.get(f'DisableBot:{Dev_Zaid}'):
        return await c.send_message(m.chat.id, f'{k} تم تعطيل البوت الخدمي من المطور')
      get = await c.get_chat_member(m.chat.id, c.me.id)
      priv = get.privileges
      if not priv or not (priv.can_post_messages or priv.can_edit_messages or priv.can_manage_chat):
        return await m.reply(f'{k} عطيني صلاحيات الأدمن بعدين ارسل تفعيل')
      r.set(f'{m.chat.id}:enable:{Dev_Zaid}', 1)
      r.sadd(f'channelslist:{Dev_Zaid}', m.chat.id)
      await c.send_message(m.chat.id, f'{k} ابشر تم تفعيل القناة\n☆')
      text2 = f'{k} تم تفعيل البوت بقناة (يدويًا عن طريق أمر تفعيل):\n\n'
      text2 += f'{k} اسم القناة : {m.chat.title}\n'
      chatusr = '@'+m.chat.username if m.chat.username else 'مافيه'
      text2 += f'{k} يوزر القناة : {chatusr}\n'
      text2 += f'{k} ايدي القناة : `{m.chat.id}`'
      if r.smembers(f'channelslist:{Dev_Zaid}'):
        text2 += f'\n{k} عدد القنوات الآن : {len(r.smembers(f"channelslist:{Dev_Zaid}"))}\n'
      text2 += '\n\n☆'
      if r.get(f'DevGroup:{Dev_Zaid}'):
        try:
          await c.send_message(int(r.get(f'DevGroup:{Dev_Zaid}')), text2, disable_web_page_preview=True)
        except:
          pass
      else:
        for dev in get_devs_br():
          try:
            await c.send_message(int(dev), text2, disable_web_page_preview=True)
            time.sleep(3)
          except:
            pass
      return
    if text == 'تعطيل':
      if not r.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return
      r.delete(f'{m.chat.id}:enable:{Dev_Zaid}', 1)
      r.srem(f'channelslist:{Dev_Zaid}', m.chat.id)
      await c.send_message(m.chat.id, f'{k} تم تعطيل القناة\n☆')
      return
    return
  # ============================================================

  if not m.from_user: return
  if r.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):  return 
  if text == 'تفعيل':
    if not (await m.chat.get_member(m.from_user.id)).status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR] and not owner_pls(m.from_user.id,m.chat.id):
       return await m.reply(f'ادري حلم الاعضاء تفعيل البوتات بس اسف')
    if r.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return await m.reply(f'{k} المجموعة مفعلة من قبل يالطيب')
    if r.get(f'DisableBot:{Dev_Zaid}'):
       return await c.send_message(m.chat.id, f'{k} تم تعطيل البوت الخدمي من المطور')
    get = await c.get_chat_member(m.chat.id, c.me.id)
    priv = get.privileges
    if not priv.can_manage_chat or not priv.can_delete_messages or not priv.can_pin_messages or not priv.can_invite_users:
      return await m.reply(f'{k} عطيني كل الصلاحيات بعدين ارسل تفعيل')
    else:
        r.set(f'{m.chat.id}:enable:{Dev_Zaid}', 1)
        r.sadd(f'enablelist:{Dev_Zaid}', m.chat.id)
        r.set(f'{m.chat.id}:rankOWNER:{m.from_user.id}{Dev_Zaid}', 1)
        r.sadd(f'{m.chat.id}:listOWNER:{Dev_Zaid}', m.from_user.id)
        await m.reply(f'{k} من「 {m.from_user.mention} 」\n{k} ابشر تم تفعيل المجموعة ورفعت كل الادمن\n☆', reply_markup=InlineKeyboardMarkup ([[InlineKeyboardButton ('Commands', url=f'https://t.me/{botUsername}?start=Commands')]]))
        async for member in m.chat.get_members(filter=ChatMembersFilter.ADMINISTRATORS):
          if not member.user.is_bot and not member.user.is_deleted:
            if member.status == ChatMemberStatus.OWNER:
              r.set(f'{m.chat.id}:rankGOWNER:{member.user.id}{Dev_Zaid}', 1)
              r.sadd(f'{m.chat.id}:listGOWNER:{Dev_Zaid}', member.user.id)
              r.sadd(f'{member.user.id}:groups',m.chat.id)
            if member.status == ChatMemberStatus.ADMINISTRATOR:
              r.set(f'{m.chat.id}:rankADMIN:{member.user.id}{Dev_Zaid}', 1)
              r.sadd(f'{m.chat.id}:listADMIN:{Dev_Zaid}', member.user.id)
        get = await c.get_chat(m.chat.id)
        text = f'{k} من「 {m.from_user.mention} 」\n'
        usrr = '@'+m.from_user.username if m.from_user.username else 'مافيه'
        text += f'{k} يوزره : {usrr}\n'
        text += f'{k} ايديه : `{m.from_user.id}`\n'
        text += f'\n{k} تم تفعيل البوت بمجموعة جديدة :\n\n'
        text += f'{k} اسم المجموعة : {m.chat.title}\n'
        chatusr = '@'+m.chat.username if m.chat.username else 'مافيه'
        text += f'{k} يوزر المجموعة : {chatusr}\n'
        text += f'{k} ايدي المجموعة : `{m.chat.id}`'
        if r.smembers(f'enablelist:{Dev_Zaid}'):
           text += f'\n{k} عدد المجموعات الآن : {len(r.smembers(f"enablelist:{Dev_Zaid}"))}\n'
        text += '\n\n☆'
        if get.invite_link:
           reply_markup=InlineKeyboardMarkup ([[InlineKeyboardButton (m.chat.title,url=get.invite_link)]])
        else:
           reply_markup=None
        if r.get(f'DevGroup:{Dev_Zaid}'):
                   await c.send_message(int(r.get(f'DevGroup:{Dev_Zaid}')),text,reply_markup=reply_markup,disable_web_page_preview=True)
        else:
               for dev in get_devs_br():
                 try:
                    await c.send_message(int(dev), text, disable_web_page_preview=True,reply_markup=reply_markup)
                    time.sleep(3)
                 except:
                    pass
  
  if text == 'تعطيل':
    if not (await m.chat.get_member(m.from_user.id)).status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR] and not owner_pls(m.from_user.id,m.chat.id):
       return await m.reply('ادري حلم الاعضاء تعطيل البوتات بس اسف')
    else:
      if not r.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return False
      else:
        r.delete(f'{m.chat.id}:enable:{Dev_Zaid}', 1)
        r.srem(f'enablelist:{Dev_Zaid}', m.chat.id)
        await m.reply(f'{k} من「 {m.from_user.mention} 」\n{k} تم تعطيل المجموعة\n☆')
        text = f'{k} من「 {m.from_user.mention} 」\n'
        usrr = '@'+m.from_user.username if m.from_user.username else 'مافيه'
        text += f'{k} يوزره : {usrr}\n'
        text += f'{k} ايديه : `{m.from_user.id}`\n'
        text += f'\n{k} تم تعطيل البوت بمجموعة جديدة :\n\n'
        text += f'{k} اسم المجموعة : {m.chat.title}\n'
        chatusr = '@'+m.chat.username if m.chat.username else 'مافيه'
        text += f'{k} يوزر المجموعة : {chatusr}\n'
        text += f'{k} ايدي المجموعة : `{m.chat.id}`'
        if r.smembers(f'enablelist:{Dev_Zaid}'):
           text += f'\n{k} عدد المجموعات الآن : {len(r.smembers(f"enablelist:{Dev_Zaid}"))}\n'
        text += '\n\n☆'
        if r.get(f'DevGroup:{Dev_Zaid}'):
                   await c.send_message(int(r.get(f'DevGroup:{Dev_Zaid}')),text)
        else:
               for dev in get_devs_br():
                 try:
                    await c.send_message(int(dev), text, disable_web_page_preview=True)
                    time.sleep(3)
                 except:
                    pass
  
  name = r.get(f'{Dev_Zaid}:BotName') if r.get(f'{Dev_Zaid}:BotName') else 'رعد'
  if text == f'{name} اطلعي' or text == f'{name} اطلع':
    leave_vids = [
  {'vid':'https://t.me/D7BotResources/154','caption':'غدرتو فيني'},
  {'vid':'https://t.me/D7BotResources/155','caption':':('},
  {'vid':'https://t.me/D7BotResources/156','caption':'يلا خلي البوتات الثانيه تدلعكم'},
  {'vid':'https://t.me/D7BotResources/157','caption':'اسف لي'},
  {'vid':'https://t.me/D7BotResources/158','caption':'قلي منهو لجل عينه تغيرت'},
  {'vid':'https://t.me/D7BotResources/159','caption':'واخيرا برتاح منكم يا نشبه العمر'},]
    if owner_pls(m.from_user.id,m.chat.id):
      r.delete(f'{m.chat.id}:enable:{Dev_Zaid}', 1)
      r.srem(f'enablelist:{Dev_Zaid}', m.chat.id)
      vid = random.choice(leave_vids)
      await m.reply_video(vid['vid'], caption=vid['caption'])
      text = f'{k} من「 {m.from_user.mention} 」\n'
      usrr = '@'+m.from_user.username if m.from_user.username else 'مافيه'
      text += f'{k} يوزره : {usrr}\n'
      text += f'{k} ايديه : `{m.from_user.id}`\n'
      text += f'\n{k} طلعت من المجموعة بأمر منه :\n\n'
      text += f'{k} اسم المجموعة : {m.chat.title}\n'
      chatusr = '@'+m.chat.username if m.chat.username else 'مافيه'
      text += f'{k} يوزر المجموعة : {chatusr}\n'
      text += f'{k} ايدي المجموعة : `{m.chat.id}`'
      if r.smembers(f'enablelist:{Dev_Zaid}'):
        text += f'\n{k} عدد المجموعات الآن : {len(r.smembers(f"enablelist:{Dev_Zaid}"))}\n'
      text += '\n\n☆'
      await c.leave_chat(m.chat.id)
      if r.get(f'DevGroup:{Dev_Zaid}'):
        await c.send_message(int(r.get(f'DevGroup:{Dev_Zaid}')),text)
      else:
        for dev in get_devs_br():
          try:
            await c.send_message(int(dev), text, disable_web_page_preview=True)
          except:
            pass