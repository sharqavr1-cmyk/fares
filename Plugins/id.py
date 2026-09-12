import random, re, time, os
from threading import Thread
from pyrogram import *
from pyrogram.enums import *
from pyrogram.types import *
from config import *
from helpers.Ranks import *
from helpers.get_create import get_creation_date
from pyrogram.raw.functions.users import GetFullUser
from io import BytesIO
from pyrogram.file_id import FileId, FileType, ThumbnailSource
from pyrogram.raw.functions.channels import GetFullChannel
from .games import get_emoji_bank
from helpers.Ranks import isLockCommand
from .all import resolve_user, edit_colored_markup, send_colored_message
def get_top(users):
   users = [tuple(i.items()) for i in users]
   top = sorted(users, key=lambda i: i[-1][-1], reverse=True)
   top = [dict(i) for i in top]
   return top
def _id_likers_key(owner_id):
   return f'{Dev_Zaid}:idlikers:{owner_id}'

def _id_likes_bonus_key(owner_id):
   return f'{Dev_Zaid}:idlikesbonus:{owner_id}'

def _id_likers_backup_key(owner_id):
   return f'{Dev_Zaid}:idlikersbackup:{owner_id}'

def get_id_likes_total(owner_id):
   real = r.scard(_id_likers_key(owner_id))
   bonus = r.get(_id_likes_bonus_key(owner_id))
   return real + (int(bonus) if bonus else 0)

def _blue_like_button(owner_id, likes_count):
   return [[{"text": f"❤️ {likes_count}", "callback_data": f"idlike:{owner_id}", "style": "primary"}]]

def _send_id_card_reply(c, sent, owner_id, likes_count):
   """بترجع نفس الرسالة بعد ما تلوّن زرار اللايك أزرق."""
   try:
      edit_colored_markup(c, sent.chat.id, sent.id, _blue_like_button(owner_id, likes_count))
   except Exception:
      pass
   return sent

custom_ids = ['''
- ᴜѕᴇʀɴᴀᴍᴇ ➣ {اليوزر} .
- ᴍѕɢѕ ➣ {الرسائل} .
- ѕᴛᴀᴛѕ ➣ {الرتبه} .
- ʏᴏᴜʀ ɪᴅ ➣ {الايدي} .
- ᴇᴅɪᴛ ᴍsɢ ➣ {التعديل} .
- ᴅᴇᴛᴀɪʟs ➣ {التفاعل} .
-  ɢᴀᴍᴇ ➣ {المجوهرات} .
{البايو}
''','''
• USE 𖦹 {اليوزر}
• MSG 𖥳 {الرسائل}
• STA 𖦹 {الرتبه}
• iD 𖥳 {الايدي}
{البايو}
''','''
➞: 𝒔𝒕𝒂𓂅 {اليوزر} 𓍯
➞: 𝒖𝒔𝒆𝒓𓂅 {المعرف} 𓍯
➞: 𝒎𝒔𝒈𝒆𓂅 {الرسائل} 𓍯
➞: 𝒊𝒅 𓂅 {الايدي} 𓍯
{البايو}
''','''
♡ : 𝐼𝐷 𖠀 {الايدي} .
♡ : 𝑈𝑆𝐸𝑅 𖠀 {اليوزر} .
♡ : 𝑀𝑆𝐺𝑆 𖠀 {الرسائل} .
♡ : 𝑆𝑇𝐴𝑇𝑆 𖠀 {الرتبه} .
♡ : 𝐸𝐷𝐼𝑇  𖠀 {التعديل} .
{البايو}
''', '''
- الايـدي || {الايدي}.
• الاسـم  || {الاسم}.
• المُعرف || {اليوزر}.
• الرُتبـه || {الرتبه}.
• الرسائل || {الرسائل}.
{البايو}
''', '''
⌁ NaMe ⇨ {الاسم}
⌁ Use ⇨ {اليوزر}
⌁ Msg ⇨ {الرسائل}
⌁ Sta ⇨ {الرتبه}
⌁ iD ⇨ {الايدي}
{البايو}
''', '''
📋¦ ɴᴀᴍᴇ ➺ {الاسم}
🗞¦ ʏᴏᴜʀ ɪᴅ ➺ {الايدي}
🔦¦ ᴜѕᴇʀɴᴀᴍᴇ ➺ {اليوزر}
🕹¦ ѕᴛᴀᴛѕ ➺ {الرتبه}
🔭¦ ᴅᴇᴛᴀɪʟs ➺ {التفاعل}
📨¦  ᴍѕɢѕ ➺ {الرسائل}
🎰¦ ɢᴀᴍᴇ ➺ {المجوهرات}
{البايو}
''', '''
✾ 𝐔𝐒𝐄 ⤷ {اليوزر}
✾ 𝐌𝐒𝐆 ⤷ {الرسائل}
✾ 𝐒𝐓𝐀 ⤷ {الرتبه}
✾ 𝐈𝐃 ⤷ {الايدي}
✾ 𝐁𝐈𝐎 ⤷ {البايو}
''', '''
𓆰 𝑼𝑬𝑺 : {اليوزر}
𓆰 𝑺𝑻𝑨 : {الرتبه}
𓆰 𝑰𝑫 : {الايدي}
𓆰 𝑴𝑺𝑮 : {الرسائل}
{البايو}'''
]


comments = [
  'تيكفه لاتكتب ايدي',
  'يع',
  'جبر',
  'احلى من يكتب ايدي',
  'افخم ايدي',
  'لحد يرسل ايدي من بعده',
  'يلبييه اطلق ايدي',
  'ازق ايدي',
  'لعد تكتب ايدي',
  'للاسف ايديك تلوث بصري ):',
  'جابك الله انت وأيديك على شكل جبر خاطر لقلبّي'
]

@Client.on_message(filters.group, group=9)
def addmsgCount(c,m):

   if not m.from_user: return
   if r.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):  return
   if not r.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}'):
      r.set(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}', 1)
   else:
      get = int(r.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}'))
      r.set(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}', get+1)
   r.set(f"{m.from_user.id}:bankName", m.from_user.first_name[:25])

@Client.on_edited_message(filters.group, group=10)
def addeditedmsgCount(c,m):

   if not m.from_user: return
   if r.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):  return
   if not r.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'):
      r.set(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}', 1)
   else:
      get = int(r.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'))
      r.set(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}', get+1)

@Client.on_message(filters.text & filters.group, group=11)
def rankGetHandler(c,m):
   k = r.get(f'{Dev_Zaid}:botkey')
   Thread(target=get_my_rank,args=(c,m,k)).start()



def get_my_rank(c,m,k):
   if not r.get(f'{m.chat.id}:enable:{Dev_Zaid}'):  return
   if not m.from_user: return
   if r.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not admin_pls(m.from_user.id,m.chat.id):  return
   if r.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):  return
   if r.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):  return
   if r.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):  return
   if r.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):  return
   if r.get(f'{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}') or r.get(f'{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}'):  return
   text = m.text
   name = r.get(f'{Dev_Zaid}:BotName') if r.get(f'{Dev_Zaid}:BotName') else 'رعد'
   if text.startswith(f'{name} '):
      text = text.replace(f'{name} ','')
   if r.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}'):
       text = r.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}')
   if r.get(f'Custom:{Dev_Zaid}&text={text}'):
       text = r.get(f'Custom:{Dev_Zaid}&text={text}')
   if isLockCommand(m.from_user.id, m.chat.id, text): return
   if text == 'مجموعاتي':
     if not r.smembers(f'{m.from_user.id}:groups'):
       return m.reply(f'{k} ماعندك مجموعات')
     else:
       groups = len(r.smembers(f'{m.from_user.id}:groups'))
       return m.reply(f'{k} عدد مجموعاتك ↼ ( {groups} )')

   if text == 'انشائي':
      create_date = get_creation_date(m.from_user.id)
      return m.reply(f'{k} الانشاء ( {create_date} )')

   if text == 'الانشاء' and not m.reply_to_message:
      create_date = get_creation_date(m.from_user.id)
      return m.reply(f'{k} الانشاء ( {create_date} )')

   if (text == 'الانشاء' or text == 'انشائه') and m.reply_to_message:
      create_date = get_creation_date(m.reply_to_message.from_user.id)
      return m.reply(f'{k} الانشاء ( {create_date} )')

   if text == 'اسمي':
     return m.reply(m.from_user.first_name, disable_web_page_preview=True)

   if text == 'معلوماتي':
      msgs = int(r.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}'))
      if msgs > 50:
        tfa3l = 'شد حيلك'
      if msgs > 500:
        tfa3l = 'يجي منك'
      if msgs > 750:
        tfa3l = 'تفاعل متوسط'
      if msgs > 2500:
        tfa3l = 'متفاعل'
      if msgs > 5000:
        tfa3l = 'اسطورة التفاعل'
      if msgs > 10000:
        tfa3l = 'كنق التلي'
      else:
        tfa3l = 'تفاعل صفر'
      if not r.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'):
         edits = 0
      else:
         edits= int(r.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'))
      if not r.get(f'{m.chat.id}TotalContacts{m.from_user.id}{Dev_Zaid}'):
         contacts = 0
      else:
         contacts = int(r.get(f'{m.chat.id}TotalContacts{m.from_user.id}{Dev_Zaid}'))
      if m.from_user.username:
         username = f'@{m.from_user.username}'
      elif getattr(m.from_user, 'usernames', None):
         username = ''
         for i in getattr(m.from_user, 'usernames', None): username += f"@{i.username} "
      else:
         username = 'مافي يوزر'
      rank = get_rank(m.from_user.id,m.chat.id)
      text = f'''
⚘ المعلومات
❁ الاسم ↼ {m.from_user.mention}
❁ اليوزر ↼ {username}
❁ الايدي  ↼ {m.from_user.id}
❁ الرتبه ↼ {rank}
┄─┅═ـ═┅─┄
⚘ احصائيات الرسايل
❁ الرسايل ↼ {msgs}
❁ التعديل ↼ {edits}
❁ التفاعل ↼ {tfa3l}
'''
      return m.reply(text)

   if text == 'بايو' and m.reply_to_message and m.reply_to_message.from_user:
      if r.get(f'{m.chat.id}:disableBio:{Dev_Zaid}'):  return
      get = c.get_chat(m.reply_to_message.from_user.id)
      if not get.bio:
        return m.reply(f'{k} ماعنده بايو')
      else:
        return m.reply(f'`{get.bio}`')

   if text == 'بايو' and not m.reply_to_message:
      if r.get(f'{m.chat.id}:disableBio:{Dev_Zaid}'):  return
      get = c.get_chat(m.from_user.id)
      if not get.bio:
        return m.reply(f'{k} ماعندك بايو')
      else:
        return m.reply(f'`{get.bio}`')


   if text == 'المجموعه' or text == 'المجموعة':
      get = c.invoke(GetFullChannel(channel=c.resolve_peer(m.chat.id)))
      if get.full_chat.exported_invite:
        link = get.full_chat.exported_invite.link
      else:
        link = 'مافي رابط'
      admins = get.full_chat.admins_count
      kicked = get.full_chat.kicked_count
      count = get.full_chat.participants_count
      if m.chat.photo:
        type = 'photo'
        if m.chat.username:
          photo = f'https://t.me/{m.chat.username}'
        else:
          photo = c.download_media(m.chat.photo.big_file_id)
      else:
        type = 'text'
      text = f'معلومات المجموعة:\n\n{k} الاسم ↢ {m.chat.title}\n{k} الايدي ↢ {m.chat.id}\n{k} عدد الاعضاء ↢ ( {count} )\n{k} عدد المشرفين ↢ ( {admins} )\n{k} عدد المحظورين ↢ ( {kicked} )\n{k} الرابط ↢ {link} '
      if type == 'photo':
         m.reply_photo(photo, caption=text)
         try:
           os.remove(photo)
         except:
           pass
         return
      else:
         return m.reply(text, disable_web_page_preview=True)

   if text == 'جهاتي':
     if not r.get(f'{m.chat.id}TotalContacts{m.from_user.id}{Dev_Zaid}'):
       contacts = 0
     else:
       contacts = int(r.get(f'{m.chat.id}TotalContacts{m.from_user.id}{Dev_Zaid}'))
     return m.reply(f'{k} عدد جهاتك ↢ {contacts}')

   if text == 'افتاري':
     if r.get(f'{m.chat.id}:disableAV:{Dev_Zaid}'): return False
     if not m.from_user.photo:
       return m.reply(f'{k} ماقدر اجيب افتارك ارسل نقطه خاص وارجع جرب')
     else:
       if m.from_user.username:
         photo = f'http://t.me/{m.from_user.username}'
       else:
         for p in c.get_chat_photos(m.from_user.id,limit=1):
           photo = p.file_id
       get_bio = c.get_chat(m.from_user.id).bio
       if not get_bio:
         caption=None
       else:
         caption = f'`{get_bio}`'
       return m.reply_photo(photo,caption=caption)

   if text == 'افتار' and m.reply_to_message and m.reply_to_message.from_user:
     if r.get(f'{m.chat.id}:disableAV:{Dev_Zaid}'): return False
     if not m.reply_to_message.from_user.photo:
       return m.reply(f'{k} مقدر اجيب افتاره يمكن حاظرني')
     else:
       if m.reply_to_message.from_user.username:
         photo = f'http://t.me/{m.reply_to_message.from_user.username}'
       else:
         for p in c.get_chat_photos(m.reply_to_message.from_user.id,limit=1):
           photo = p.file_id
       get_bio = c.get_chat(m.reply_to_message.from_user.id).bio
       if not get_bio:
         caption=None
       else:
         caption = f'`{get_bio}`'
       return m.reply_photo(photo,caption=caption)

   if text == 'ايديي':
     return m.reply(f'( `{m.from_user.id}` )')

   if text.startswith('افتار') and len(text.split()) == 2:
     if r.get(f'{m.chat.id}:disableAV:{Dev_Zaid}'): return False
     try:
       user = int(text.split()[1])
     except:
       user = text.split()[1]
     try:
       get = c.get_chat(user)
       if get.photo:
         for p in c.get_chat_photos(get.id,limit=1):
           photo = p.file_id
         if get.bio:
           caption = f'`{get.bio}`'
         else:
           caption = None
         return m.reply_photo(photo,caption=caption)
     except Exception as e:
       print (e)
       return


   if text == 'رتبتي':
      rank = get_rank(m.from_user.id, m.chat.id)
      m.reply(f'{k} رتبتك ↢ {rank}')

   if text == 'مسح رسائلي' or text == 'مسح رسايلي':
      msgs = int(r.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}'))
      r.delete(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}')
      return m.reply(f'{k} ابشر مسحت ( {msgs} ) من رسائلك')

   if text == 'مسح تكليجاتي':
      if not r.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'):
        return m.reply(f'{k} عدد تكليجاتك ↢ 0')
      msgs = int(r.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'))
      r.delete(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}')
      return m.reply(f'{k} ابشر مسحت ( {msgs} ) من تكليجاتك')

   if text == 'تكليجاتي' or text == 'تعديلاتي':
      if not r.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'):
        return m.reply(f'{k} عدد تكليجاتك ↢ 0')
      msgs = int(r.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'))
      return m.reply(f'{k} عدد تكليجاتك ↢ {msgs}')

   if text == 'رسايلي' or text == 'رسائلي':
      msgs = int(r.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}'))
      return m.reply(f'{k} عدد رسايلك ↢ {msgs}')
      
   if (text == 'رسايله' or text == 'رسائلة') and m.reply_to_message and m.reply_to_message.from_user:
      msgs = int(r.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.reply_to_message.from_user.id}'))
      return m.reply(f'{k} عدد رسايله ↢ {msgs}')




   if text == 'رتبته' and m.reply_to_message and m.reply_to_message.from_user:
      rank = get_rank(m.reply_to_message.from_user.id, m.chat.id)
      status = m.chat.get_member(m.reply_to_message.from_user.id).status
      if status == ChatMemberStatus.OWNER:
        rank2 = 'المالك'
      if status == ChatMemberStatus.ADMINISTRATOR:
        rank2 = 'مشرف'
      if status == ChatMemberStatus.RESTRICTED:
        rank2 = 'مقيد'
      if status == ChatMemberStatus.LEFT:
        rank2 = 'طالع'
      if status == ChatMemberStatus.MEMBER:
        rank2 = 'عضو'
      if status == ChatMemberStatus.BANNED:
        rank2 = 'لاقم حظر'
      m.reply(f'رتبته:\n{k} في البوت ( {rank} )\n{k} في المجموعة ( {rank2} )\n-')

   if text == 'نقل ملكية' or text == 'نقل ملكيه' or text.startswith('نقل ملكية ') or text.startswith('نقل ملكيه '):
     if not r.get(f'{m.chat.id}:rankGOWNER:{m.from_user.id}{Dev_Zaid}'):
       return m.reply(f'{k} عذراً الامر يخص ↤〖 المالك 〗فقط .')
     target_id = None
     if m.reply_to_message and m.reply_to_message.from_user:
       target_id = m.reply_to_message.from_user.id
     else:
       parts = text.split()
       raw = parts[-1] if len(parts) > 2 else ''
       target_id = resolve_user(c, raw.lstrip('@'))
     if not target_id:
       return m.reply(f'{k} حدد الشخص بالرد أو باليوزر أو بالآيدي')
     if target_id == m.from_user.id:
       return m.reply(f'{k} انت مالك القروب')
     try:
       mention = c.get_users(target_id).mention
     except Exception:
       mention = f'`{target_id}`'
     r.delete(f'{m.chat.id}:rankGOWNER:{m.from_user.id}{Dev_Zaid}')
     r.srem(f'{m.chat.id}:listGOWNER:{Dev_Zaid}', m.from_user.id)
     r.set(f'{m.chat.id}:rankGOWNER:{target_id}{Dev_Zaid}', 1)
     r.sadd(f'{m.chat.id}:listGOWNER:{Dev_Zaid}', target_id)
     return m.reply(f'「 {mention} 」\n{k} نقلت له ملكية المجموعة')

   if text == "مسح المتفاعلين" or text == "تصفير المتفاعلين":
     if not owner_pls(m.from_user.id, m.chat.id):
       return m.reply(f'{k} عذراً الامر يخص ↤〖 المالك 〗فقط .')
     else:
       keys = r.keys(f"{Dev_Zaid}{m.chat.id}:TotalMsgs:*")
       for _ in keys: r.delete(_)
       return m.reply(f"{k} ابشر مسحت كل المتفاعلين")

   if text == "مسح القروبات" or text == "تصفير القروبات":
     if not devp_pls(m.from_user.id, m.chat.id):
       return m.reply(f'{k} عذراً الامر يخص ↤〖 Dev🎖️ 〗فقط .')
     else:
       keys = r.keys(f"{Dev_Zaid}:TotalGroupMsgs:*")
       for _ in keys: r.delete(_)
       return m.reply(f"{k} ابشر مسحت توب القروبات")

   if text == "ترتيبي" or text == "تفاعلي":
     users = r.keys(f"{Dev_Zaid}{m.chat.id}:TotalMsgs:*")
     jj = []
     for user in users:
          try:
            id = int(user.split("TotalMsgs:")[1])
            msgs = r.get(user)
            jj.append({"id": id, "msgs": int(msgs)})
          except:
            pass
     top = get_top(jj)
     ids = [i["id"] for i in top]
     rank = ids.index(m.from_user.id) + 1
     msgs = int(r.get(f"{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}"))
     return m.reply(f"{k} ترتيبك بالمتفاعلين ↢ {rank}\n{k} رسائلك بالتفاعل ↢ {msgs:,}\n-")

   if text == "المتفاعلين" or text == "توب المتفاعلين":
        users = r.keys(f"{Dev_Zaid}{m.chat.id}:TotalMsgs:*")
        # print(users)
        jj = []
        for user in users:
                  try:
                    id = int(user.split("TotalMsgs:")[1])
                    # print(id)
                    msgs = r.get(user)
                    name = r.get(f"{id}:bankName") or str(id)
                    jj.append({"name": name, "id": id, "msgs": int(msgs)})
                  except:
                    pass
        top = get_top(jj)
        text = "- توب اكثر 20 متفاعل :\n━━━━━━━━━\n"
        count = 1
        for i in top:
            if count == 21: break
            emoji = get_emoji_bank(count)
            text += f"{emoji}{i['msgs']:,} l [{i['name']}](tg://user?id={i['id']})\n"
            count +=1
        return c.send_message(m.chat.id, text, disable_web_page_preview=True, reply_to_message_id=m.id)

   if text == "القروبات" or text == "توب القروبات":
        groups = r.keys(f"{Dev_Zaid}:TotalGroupMsgs:*")
        result = []

        for group in groups:
            try:
                chat_id = int(group.split("TotalGroupMsgs:")[1])
                msgs = r.get(group)
                group_title = c.get_chat(chat_id).title
                result.append({"group_title": group_title, "chat_id": chat_id, "msgs": int(msgs)})
            except:
                pass

        top_groups = get_top(result)
        response_text = "- توب اكثر 20 قروب متفاعل:\n━━━━━━━━━\n"
        count = 1

        for group in top_groups:
            if count == 21:
                break
            emoji = get_emoji_bank(count)
            response_text += f"{emoji}{group['msgs']:,} l {group['group_title']}\n"
            count += 1

        return c.send_message(m.chat.id, response_text, disable_web_page_preview=True, reply_to_message_id=m.id)


   if text == 'كشف' and m.reply_to_message and m.reply_to_message.from_user:
       try:
           get = m.chat.get_member(m.reply_to_message.from_user.id)
           rank = get_rank(m.reply_to_message.from_user.id, m.chat.id)
           name = m.reply_to_message.from_user.first_name
           msgs = int(r.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.reply_to_message.from_user.id}'))
           id = m.reply_to_message.from_user.id
           if m.reply_to_message.from_user.username:
               username = f'@{m.reply_to_message.from_user.username}'
           elif getattr(m.reply_to_message.from_user, 'usernames', None):
               username = ''
               for i in getattr(m.reply_to_message.from_user, 'usernames', None): username += f"@{i.username} "
           else:
               username = 'مافي يوزر'
           status = m.chat.get_member(m.reply_to_message.from_user.id).status
           if status == ChatMemberStatus.OWNER:
               rank2 = 'المالك'
           if status == ChatMemberStatus.ADMINISTRATOR:
               rank2 = 'مشرف'
           if status == ChatMemberStatus.RESTRICTED:
               rank2 = 'مقيد'
           if status == ChatMemberStatus.LEFT:
               rank2 = 'طالع'
           if status == ChatMemberStatus.MEMBER:
               rank2 = 'عضو'
           if status == ChatMemberStatus.BANNED:
               rank2 = 'لاقم حظر'
           text = f'''
{k} الاسم ↢ {name}
{k} الايدي ↢ {id}
{k} اليوزر : ( {username} ) 
{k} الرتبه ↢ ( {rank} )
{k} الرسائل ↢ ( {msgs} )
{k} بالمجموعة ↢ ( {rank2} )
{k} نوع الكشف ↢ بالرد
-
'''
           return m.reply(text, disable_web_page_preview=True)
       except:
           return m.reply(f'{k} العضو مو بالمجموعة')

   if text.startswith('كشف') and len(text.split()) > 1 and 'tg://user?id=' in m.text.html:
       print(m.text.html)
       user = user = int(re.search(r'href="([^"]+)', m.text.html).group(1).split('=')[1])
       ks = 'بالمنشن'
       try:
           get = m.chat.get_member(user)
           name = get.user.first_name
           id = get.user.id
           msgs = int(r.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{get.user.id}'))
           if get.user.username:
               username = f'@{get.user.username}'
           elif getattr(get.user, 'usernames', None):
               username = ""
               for i in getattr(get.user, 'usernames', None): username += f"@{i.username} "
           else:
               username = 'ماعنده يوزر'
           status = get.status
           if status == ChatMemberStatus.OWNER:
               rank = 'المالك'
           if status == ChatMemberStatus.ADMINISTRATOR:
               rank = 'مشرف'
           if status == ChatMemberStatus.RESTRICTED:
               rank = 'مقيد'
           if status == ChatMemberStatus.LEFT:
               rank = 'طالع'
           if status == ChatMemberStatus.MEMBER:
               rank = 'عضو'
           if status == ChatMemberStatus.BANNED:
               rank = 'لاقم حظر'
       except:
           rank = 'طالع'
           try:
               get = c.get_chat(user)
               name = get.first_name
               id = get.id
               msgs = int(r.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{get.id}'))
               if get.user.username:
                   username = f'@{get.user.username}'
               elif getattr(get.user, 'usernames', None):
                   username = ""
                   for i in getattr(get.user, 'usernames', None): username += f"@{i.username} "
               else:
                   username = 'ماعنده يوزر'
           except Exception as e:
               print(e)
               return
       rank2 = get_rank(id, m.chat.id)
       text = f'''
{k} الاسم ↢ {name}
{k} الايدي ↢{id}
{k} اليوزر : ↢ ( {username} )
{k} الرتبه ↢ ({rank2} )
{k} الرسائل ↢ ( {msgs} )
{k} بالمجموعة ↢ ( {rank} )
{k} نوع الكشف ↢ {ks}
-
        '''
       return m.reply(text, disable_web_page_preview=True)

   if text.startswith('كشف') and len(text.split()) == 2:
       try:
           user = int(text.split()[1])
           ks = 'بالايدي'
       except:
           user = text.split()[1].replace('@', '')
           ks = 'باليوزر'
       try:
           get = m.chat.get_member(user)
           name = get.user.first_name
           id = get.user.id
           msgs = int(r.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{get.user.id}'))
           if get.user.username:
               username = f'@{get.user.username}'
           elif getattr(get.user, 'usernames', None):
               username = ""
               for i in getattr(get.user, 'usernames', None): username += f"@{i.username} "
           else:
               username = 'ماعنده يوزر'
           status = get.status
           if status == ChatMemberStatus.OWNER:
               rank = 'المالك'
           if status == ChatMemberStatus.ADMINISTRATOR:
               rank = 'مشرف'
           if status == ChatMemberStatus.RESTRICTED:
               rank = 'مقيد'
           if status == ChatMemberStatus.LEFT:
               rank = 'طالع'
           if status == ChatMemberStatus.MEMBER:
               rank = 'عضو'
           if status == ChatMemberStatus.BANNED:
               rank = 'لاقم حظر'
       except:
           rank = 'طالع'
           try:
               get = c.get_chat(user)
               name = get.first_name
               id = get.id
               msgs = int(r.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{get.id}'))
               if get.user.username:
                   username = f'@{get.user.username}'
               elif getattr(get.user, 'usernames', None):
                   username = ""
                   for i in getattr(get.user, 'usernames', None): username += f"@{i.username} "
               else:
                   username = 'ماعنده يوزر'
           except Exception as e:
               print(e)
               return
       rank2 = get_rank(id, m.chat.id)
       text = f'''
{k} الاسم ↢ {name}
{k} الايدي ↢{id}
{k} اليوزر : ↢ ( {username} )
{k} الرتبه ↢ ({rank2} )
{k} الرسائل ↢ ( {msgs} )
{k} بالمجموعة ↢ ( {rank} )
{k} نوع الكشف ↢ {ks}
-
        '''
       return m.reply(text, disable_web_page_preview=True)


   if text == 'صلاحياته' and m.reply_to_message and m.reply_to_message.from_user:
      get = m.chat.get_member(m.reply_to_message.from_user.id)
      if not get.status in [ChatMemberStatus.ADMINISTRATOR,ChatMemberStatus.OWNER]:
         return m.reply(f'{k} هو العضو وما عنده صلاحيات')
      if get.status == ChatMemberStatus.OWNER:
         return m.reply(f'{k} هو المالك وعنده كل الصلاحيات')
      if get.status == ChatMemberStatus.ADMINISTRATOR:
         p = get.privileges
         p1 = "✔️" if p.can_manage_chat else "✖️"
         p2 = "✔️" if p.can_delete_messages else "✖️"
         p3 = "✔️" if p.can_manage_video_chats else "✖️"
         p4 = "✔️" if p.can_restrict_members else "✖️"
         p5 = "✔️" if p.can_promote_members else "✖️"
         p6 = "✔️" if p.can_change_info else "✖️"
         p7 = "✔️" if p.can_pin_messages else "✖️"
         text = f'''
{k} هو مشرف وهذي صلاحياته :

1) - ادارة المجموعة ↼ ( {p1} )
2) - مسح الرسائل ↼ ( {p2} )
3) - ادارة مكالمات ↼ ( {p3} )
4) - تقييد الأعضاء وحظرهم ↼ ( {p4} )
5) - رفع المشرفين ↼ ( {p5} )
6) - تعديل معلومات المجموعة ↼ ( {p6} )
7) - تثبيت الرسايل ↼ ( {p7} )


'''
         return m.reply(text)

   if text == 'صلاحياتي':
      get = m.chat.get_member(m.from_user.id)
      if not get.status in [ChatMemberStatus.ADMINISTRATOR,ChatMemberStatus.OWNER]:
         return m.reply(f'{k} انت العضو وماعندك صلاحيات')
      if get.status == ChatMemberStatus.OWNER:
         return m.reply(f'{k} انت المالك وعندك كل الصلاحيات')
      if get.status == ChatMemberStatus.ADMINISTRATOR:
         p = get.privileges
         p1 = "✔️" if p.can_manage_chat else "✖️"
         p2 = "✔️" if p.can_delete_messages else "✖️"
         p3 = "✔️" if p.can_manage_video_chats else "✖️"
         p4 = "✔️" if p.can_restrict_members else "✖️"
         p5 = "✔️" if p.can_promote_members else "✖️"
         p6 = "✔️" if p.can_change_info else "✖️"
         p7 = "✔️" if p.can_pin_messages else "✖️"
         text = f'''
{k} انت مشرف وهذي صلاحياتك :

1) - ادارة المجموعة ↼ ( {p1} )
2) - مسح الرسائل ↼ ( {p2} )
3) - ادارة مكالمات ↼ ( {p3} )
4) - تقييد الأعضاء وحظرهم ↼ ( {p4} )
5) - رفع المشرفين ↼ ( {p5} )
6) - تعديل معلومات المجموعة ↼ ( {p6} )
7) - تثبيت الرسايل ↼ ( {p7} )


'''
         return m.reply(text)


   if r.get(f'{m.chat.id}:addCustomID:{m.from_user.id}{Dev_Zaid}') and text == 'الغاء':
     r.delete(f'{m.chat.id}:addCustomID:{m.from_user.id}{Dev_Zaid}')
     m.reply(f'{k} ابشر تم الغاء تعيين الايدي ')
     return

   if r.get(f'{m.chat.id}:addCustomIDG:{m.from_user.id}{Dev_Zaid}') and text == 'الغاء':
     r.delete(f'{m.chat.id}:addCustomIDG:{m.from_user.id}{Dev_Zaid}')
     m.reply(f'{k} ابشر تم الغاء تعيين الايدي عام')
     return

   if r.get(f'{m.chat.id}:addCustomIDG:{m.from_user.id}{Dev_Zaid}') and dev_pls(m.from_user.id, m.chat.id):
      r.set(f'customID:{Dev_Zaid}', m.text)
      m.reply(f'{k} وسوينا الايدي العام\n{k} يمديك تجرب شكل الايدي الجديد الحين')
      r.delete(f'{m.chat.id}:addCustomIDG:{m.from_user.id}{Dev_Zaid}')
      return

   if r.get(f'{m.chat.id}:addCustomID:{m.from_user.id}{Dev_Zaid}') and mod_pls(m.from_user.id, m.chat.id):
      r.set(f'{m.chat.id}:customID:{Dev_Zaid}', m.text)
      m.reply(f'{k} وسوينا الايدي\n{k} يمديك تجرب شكل الايدي الجديد الحين')
      r.delete(f'{m.chat.id}:addCustomID:{m.from_user.id}{Dev_Zaid}')
      return

   if text == 'مسح الايدي':
      if not mod_pls(m.from_user.id, m.chat.id):
        return m.reply(f'{k} عذراً الامر يخص ↤〖 المدير 〗فقط .')
      if not r.get(f'{m.chat.id}:customID:{Dev_Zaid}'):
        return m.reply(f'{k} الايدي مو معدل')
      else:
        m.reply(f'{k} ابشر مسحت الايدي')
        r.delete(f'{m.chat.id}:customID:{Dev_Zaid}')
        return

   if text == 'مسح الايدي العام' or text == 'مسح الايدي عام':
      if not dev2_pls(m.from_user.id, m.chat.id):
        return m.reply(f'{k} عذراً الامر يخص ↤〖 Dev²🎖 〗فقط .')
      if not r.get(f'customID:{Dev_Zaid}'):
        return m.reply(f'{k} الايدي العام مو معدل')
      else:
        m.reply(f'{k} ابشر مسحت الايدي العام')
        r.delete(f'customID:{Dev_Zaid}')

   if text == 'الايدي':
      if not mod_pls(m.from_user.id, m.chat.id):
        return
      if not r.get(f'{m.chat.id}:customID:{Dev_Zaid}'):
        return m.reply(f'{k} الايدي مو معدل')
      else:
        id = r.get(f'{m.chat.id}:customID:{Dev_Zaid}')
        return m.reply(f'`{id}`')

   if text == 'الايدي العام':
      if not dev2_pls(m.from_user.id, m.chat.id):
        return
      if not r.get(f'customID:{Dev_Zaid}'):
        return m.reply(f'{k} الايدي العام مو معدل')
      else:
        id = r.get(f'customID:{Dev_Zaid}')
        return m.reply(f'`{id}`')

   if text == 'تغيير الايدي':
      if not mod_pls(m.from_user.id, m.chat.id):
        return m.reply(f'{k} عذراً الامر يخص ↤〖 المدير 〗فقط .')
      else:
        id = random.choice(custom_ids)
        r.set(f'{m.chat.id}:customID:{Dev_Zaid}', id)
        m.reply(f'{k} وسوينا الايدي\n{k} يمديك تجرب شكل الايدي الجديد الحين')

   if text == 'تعيين الايدي':
      if not mod_pls(m.from_user.id, m.chat.id):
        return m.reply(f'{k} عذراً الامر يخص ↤〖 المدير 〗فقط .')
      reply = '''
تمام , الحين ارسل شكل الايدي الجديد

- الاختصارات:

{الاسم} ↼ يطلع اسم الشخص
{الايدي} ↼ يطلع ايدي الشخص
{اليوزر} ↼ يطلع يوزر الشخص
{الرتبه} ↼ يطلع رتبته الشخص
{التفاعل} ↼ يطلع تفاعل الشخص
{الرسائل} ↼ يطلع كم رسالة عند الشخص
{التعديل} ↼ يطلع كم مره عدل الشخص
{البايو} ↼ يطلع البايو اللي كاتبه
{تعليق} ↼ يطلع تعليق عشوائي
{الانشاء} ↼ يطلع انشاء الحساب

قناة اشكال الايدي https://t.me/EFFB0T/187

'''
      m.reply(reply)
      r.set(f'{m.chat.id}:addCustomID:{m.from_user.id}{Dev_Zaid}', 1)
      return
   if text == 'تعيين الايدي عام':
      if not dev2_pls(m.from_user.id, m.chat.id):
        return m.reply(f'{k} عذراً الامر يخص ↤〖 Dev²🎖 〗فقط .')
      reply = '''
تمام , الحين ارسل شكل الايدي الجديد

- الاختصارات:

{الاسم} ↼ يطلع اسم الشخص
{الايدي} ↼ يطلع ايدي الشخص
{اليوزر} ↼ يطلع يوزر الشخص
{الرتبه} ↼ يطلع رتبته الشخص
{التفاعل} ↼ يطلع تفاعل الشخص
{الرسائل} ↼ يطلع كم رسالة عند الشخص
{التعديل} ↼ يطلع كم مره عدل الشخص
{البايو} ↼ يطلع البايو اللي كاتبه
{تعليق} ↼ يطلع تعليق عشوائي
{الانشاء} ↼ يطلع انشاء الحساب

قناة اشكال الايدي https://t.me/EFFB0T/187
'''
      m.reply(reply)
      r.set(f'{m.chat.id}:addCustomIDG:{m.from_user.id}{Dev_Zaid}', 1)
      return True


   if text == 'تفعيل الايدي':
     if not admin_pls(m.from_user.id,m.chat.id):
       return m.reply(f'{k} عذراً الامر يخص ↤〖 الادمن 〗فقط .')
     else:
       if not r.get(f'{m.chat.id}:disableID:{Dev_Zaid}'):
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} الايدي مفعل من قبل')
       else:
         r.delete(f'{m.chat.id}:disableID:{Dev_Zaid}')
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ابشر فعلت الايدي')

   if text == 'تعطيل الايدي':
     if not admin_pls(m.from_user.id,m.chat.id):
       return m.reply(f'{k} عذراً الامر يخص ↤〖 الادمن 〗فقط .')
     else:
       if r.get(f'{m.chat.id}:disableID:{Dev_Zaid}'):
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} الايدي معطل من قبل')
       else:
         r.set(f'{m.chat.id}:disableID:{Dev_Zaid}',1)
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ابشر عطلت الايدي')

   if text == 'تفعيل ايدي الاعضاء':
     if not admin_pls(m.from_user.id,m.chat.id):
       return m.reply(f'{k} عذراً الامر يخص ↤〖 الادمن 〗فقط .')
     else:
       if not r.get(f'{m.chat.id}:disableIDMembers:{Dev_Zaid}'):
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ايدي الاعضاء مفعل من قبل')
       else:
         r.delete(f'{m.chat.id}:disableIDMembers:{Dev_Zaid}')
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ابشر فعلت ايدي الاعضاء')

   if text == 'تعطيل ايدي الاعضاء':
     if not admin_pls(m.from_user.id,m.chat.id):
       return m.reply(f'{k} عذراً الامر يخص ↤〖 الادمن 〗فقط .')
     else:
       if r.get(f'{m.chat.id}:disableIDMembers:{Dev_Zaid}'):
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ايدي الاعضاء معطل من قبل')
       else:
         r.set(f'{m.chat.id}:disableIDMembers:{Dev_Zaid}',1)
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ابشر عطلت ايدي الاعضاء (الادمن بس هو اللي هيقدر يستخدم الايدي)')

   if text == 'تفعيل ايدي الادمن':
     if not (owner_pls(m.from_user.id,m.chat.id) or dev_pls(m.from_user.id,m.chat.id)):
       return m.reply(f'{k} عذراً الامر يخص ↤〖 مالك الجروب أو المطور 〗فقط .')
     else:
       if not r.get(f'{m.chat.id}:disableIDAdmins:{Dev_Zaid}'):
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ايدي الادمن مفعل من قبل')
       else:
         r.delete(f'{m.chat.id}:disableIDAdmins:{Dev_Zaid}')
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ابشر فعلت ايدي الادمن')

   if text == 'تعطيل ايدي الادمن':
     if not (owner_pls(m.from_user.id,m.chat.id) or dev_pls(m.from_user.id,m.chat.id)):
       return m.reply(f'{k} عذراً الامر يخص ↤〖 مالك الجروب أو المطور 〗فقط .')
     else:
       if r.get(f'{m.chat.id}:disableIDAdmins:{Dev_Zaid}'):
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ايدي الادمن معطل من قبل')
       else:
         r.set(f'{m.chat.id}:disableIDAdmins:{Dev_Zaid}',1)
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ابشر عطلت ايدي الادمن')

   if text == 'المعجبين' or text == 'فانزاتي' or text == 'فنزاتي':
     likers_key = f'{Dev_Zaid}:idlikers:{m.from_user.id}'
     likers = r.smembers(likers_key)
     if not likers:
       return m.reply(f'{k} معندكش حد معجب بيك للأسف 💔')
     buttons = []
     row = []
     for uid in likers:
       try:
         fan = c.get_users(int(uid))
         fan_name = fan.first_name or 'مستخدم'
       except Exception:
         fan_name = 'مستخدم'
       # رابط tg://user بدل user_id= مباشرة، عشان الزرار يشتغل حتى لو
       # البوت لسه ما "قابلش" الشخص ده قبل كده (مش محتاج الـpeer يكون
       # متخزن عنده أصلاً زي ما بيحصل مع user_id=).
       row.append(InlineKeyboardButton(fan_name, url=f"tg://user?id={uid}"))
       if len(row) == 2:
         buttons.append(row)
         row = []
     if row:
       buttons.append(row)
     try:
       return m.reply(f'{k} المعجبين بيك ↢ ( {len(likers)} )', reply_markup=InlineKeyboardMarkup(buttons))
     except Exception:
       return m.reply(f'{k} المعجبين بيك ↢ ( {len(likers)} )')

   if text.startswith('اضف عدد لايكات'):
     if not dev_pls(m.from_user.id,m.chat.id):
       return m.reply(f'{k} عذراً الامر يخص ↤〖 المطور 〗فقط .')
     if not (m.reply_to_message and m.reply_to_message.from_user):
       return m.reply(f'{k} لازم ترد على الشخص وتكتب: اضف عدد لايكات 50')
     parts = text.split()
     amount_txt = parts[-1] if parts else ''
     if not amount_txt.lstrip('-').isdigit():
       return m.reply(f'{k} اكتب الرقم في الآخر كده: اضف عدد لايكات 50')
     amount = int(amount_txt)
     target = m.reply_to_message.from_user
     bonus_key = _id_likes_bonus_key(target.id)
     current_bonus = int(r.get(bonus_key) or 0)
     r.set(bonus_key, current_bonus + amount)
     total = get_id_likes_total(target.id)
     return m.reply(
       f'{k} بواسطة ↤ {m.from_user.mention}\n'
       f'{k} تم زيادة لايكات {target.mention} بـ ( {amount} )\n'
       f'{k} إجمالي لايكاته دلوقتي ↢ ( {total} )'
     )

   if text == 'مسح عدد لايكات':
     if not dev_pls(m.from_user.id,m.chat.id):
       return m.reply(f'{k} عذراً الامر يخص ↤〖 المطور 〗فقط .')
     if not (m.reply_to_message and m.reply_to_message.from_user):
       return m.reply(f'{k} لازم ترد على الشخص وتكتب: مسح عدد لايكات')
     target = m.reply_to_message.from_user
     r.delete(_id_likes_bonus_key(target.id))
     total = get_id_likes_total(target.id)
     return m.reply(
       f'{k} بواسطة ↤ {m.from_user.mention}\n'
       f'{k} تم مسح اللايكات الوهمية عن {target.mention}\n'
       f'{k} فضل اللايكات الحقيقية بس ↢ ( {total} )'
     )

   if text.startswith('تصفير لايكاته') or text.startswith('تصفير لايكات'):
     if not dev_pls(m.from_user.id,m.chat.id):
       return m.reply(f'{k} عذراً الامر يخص ↤〖 المطور 〗فقط .')
     target_id = None
     if m.reply_to_message and m.reply_to_message.from_user:
       target_id = m.reply_to_message.from_user.id
     else:
       parts = text.split()
       raw = parts[-1] if len(parts) > 1 else ''
       target_id = resolve_user(c, raw.lstrip('@'))
     if not target_id:
       return m.reply(f'{k} حدد الشخص بالرد أو باليوزر أو بالآيدي')
     try:
       mention = c.get_users(target_id).mention
     except Exception:
       mention = f'`{target_id}`'
     likers = r.smembers(_id_likers_key(target_id))
     if likers:
       r.sadd(_id_likers_backup_key(target_id), *likers)
       r.delete(_id_likers_key(target_id))
     r.delete(_id_likes_bonus_key(target_id))
     return m.reply(
       f'{k} بواسطة ↤ {m.from_user.mention}\n'
       f'{k} تم تصفير لايكات {mention} بالكامل\n☆'
     )

   if text.startswith('الغاء تصفير لايكاته') or text.startswith('الغاء تصفير لايكات'):
     if not dev_pls(m.from_user.id,m.chat.id):
       return m.reply(f'{k} عذراً الامر يخص ↤〖 المطور 〗فقط .')
     target_id = None
     if m.reply_to_message and m.reply_to_message.from_user:
       target_id = m.reply_to_message.from_user.id
     else:
       parts = text.split()
       raw = parts[-1] if len(parts) > 1 else ''
       target_id = resolve_user(c, raw.lstrip('@'))
     if not target_id:
       return m.reply(f'{k} حدد الشخص بالرد أو باليوزر أو بالآيدي')
     try:
       mention = c.get_users(target_id).mention
     except Exception:
       mention = f'`{target_id}`'
     backup = r.smembers(_id_likers_backup_key(target_id))
     if not backup:
       return m.reply(f'{k} مفيش لايكات حقيقية محفوظة لـ {mention}')
     r.sadd(_id_likers_key(target_id), *backup)
     r.delete(_id_likers_backup_key(target_id))
     total = get_id_likes_total(target_id)
     return m.reply(
       f'{k} بواسطة ↤ {m.from_user.mention}\n'
       f'{k} تم إرجاع اللايكات الحقيقية لـ {mention}\n'
       f'{k} إجمالي لايكاته دلوقتي ↢ ( {total} )'
     )

   if text == 'تفعيل افتاري':
     if not admin_pls(m.from_user.id,m.chat.id):
       return m.reply(f'{k} عذراً الامر يخص ↤〖 الادمن 〗فقط .')
     else:
       if not r.get(f'{m.chat.id}:disableAV:{Dev_Zaid}'):
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} افتار مفعل من قبل')
       else:
         r.delete(f'{m.chat.id}:disableAV:{Dev_Zaid}')
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ابشر فعلت افتار')

   if text == 'تعطيل افتاري':
     if not admin_pls(m.from_user.id,m.chat.id):
       return m.reply(f'{k} عذراً الامر يخص ↤〖 الادمن 〗فقط .')
     else:
       if r.get(f'{m.chat.id}:disableAV:{Dev_Zaid}'):
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} افتار معطل من قبل')
       else:
         r.set(f'{m.chat.id}:disableAV:{Dev_Zaid}',1)
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ابشر عطلت افتار')

   if text == 'تعطيل الايدي بالصوره':
     if not admin_pls(m.from_user.id,m.chat.id):
       return m.reply(f'{k} عذراً الامر يخص ↤〖 الادمن 〗فقط .')
     else:
       if r.get(f'{m.chat.id}:disableIDPHOTO:{Dev_Zaid}'):
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} الايدي بالصوره معطل من قبل')
       else:
         r.set(f'{m.chat.id}:disableIDPHOTO:{Dev_Zaid}',1)
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ابشر عطلت الايدي بالصوره')

   if text == 'تفعيل الايدي بالصوره':
     if not admin_pls(m.from_user.id,m.chat.id):
       return m.reply(f'{k} عذراً الامر يخص ↤〖 الادمن 〗فقط .')
     else:
       if not r.get(f'{m.chat.id}:disableIDPHOTO:{Dev_Zaid}'):
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} الايدي بالصوره مفعل من قبل')
       else:
         r.delete(f'{m.chat.id}:disableIDPHOTO:{Dev_Zaid}')
         return m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ابشر فعلت الايدي بالصوره')

   if text == "لقبي":
     title = m.chat.get_member(m.from_user.id).custom_title
     if not title:
       return m.reply(f"{k} ماعندك لقب")
     else:
       return m.reply(f"{k} لقبك ↢ ( {title} )")

   if (text == 'ايدي' or text.lower() == 'ا') and m.reply_to_message and m.reply_to_message.from_user:
       if admin_pls(m.from_user.id,m.chat.id):
         if r.get(f'{m.chat.id}:disableIDAdmins:{Dev_Zaid}'):  return
       else:
         if r.get(f'{m.chat.id}:disableIDMembers:{Dev_Zaid}'):  return
       return m.reply(f'الايدي ↢ ( `{m.reply_to_message.from_user.id}` )')

   if (text == 'ايدي' or text.lower() == 'id') and not m.reply_to_message:
      if r.get(f'{m.chat.id}:disableID:{Dev_Zaid}'):  return
      if admin_pls(m.from_user.id,m.chat.id):
        if r.get(f'{m.chat.id}:disableIDAdmins:{Dev_Zaid}'):  return
      else:
        if r.get(f'{m.chat.id}:disableIDMembers:{Dev_Zaid}'):  return
      if r.get(f'{m.chat.id}:customID:{Dev_Zaid}'):
         id = r.get(f'{m.chat.id}:customID:{Dev_Zaid}')
      else:
         if r.get(f'customID:{Dev_Zaid}'):
           id = r.get(f'customID:{Dev_Zaid}')
         else:
           id = '''
𖡋 𝐔𝐒𝐄 ⌯  {اليوزر}
𖡋 𝐌𝐒𝐆 ⌯  {الرسائل}
𖡋 𝐒𝐓𝐀 ⌯  {الرتبه}
𖡋 𝐈𝐃 ⌯  {الايدي}
𖡋 𝐄𝐃𝐈𝐓 ⌯  {التعديل}
𖡋 𝐂𝐑  ⌯  {الانشاء}
{البايو}'''
      if getattr(m.from_user, 'usernames', None):
         username = ''
         for i in getattr(m.from_user, 'usernames', None): username += f"@{i.username} "
      elif m.from_user.username:
         username = f'@{m.from_user.username}'
      else:
         username = 'مافي يوزر'
      rank = get_rank(m.from_user.id, m.chat.id)
      msg = int(r.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}'))
      msgs = f"{msg}"
      iD = f'`{m.from_user.id}`'
      if not r.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'):
         edits = 0
      else:
         edit= int(r.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'))
         edits = f"{edit}"
      name = m.from_user.first_name
      create = get_creation_date(m.from_user.id)
      get_chat = c.get_chat(m.from_user.id)
      if get_chat.bio :
         bio = get_chat.bio
      else:
         bio = 'مافي بايو'
      if msg > 50:
        tfa3l = 'شد حيلك'
      if msg > 500:
        tfa3l = 'يجي منك'
      if msg > 750:
        tfa3l = 'تفاعل متوسط'
      if msg > 2500:
        tfa3l = 'متفاعل'
      if msg > 5000:
        tfa3l = 'اسطورة التفاعل'
      if msg > 10000:
        tfa3l = 'اسطورة التلي'
      else:
        tfa3l = 'تفاعل صفر'
      comment = random.choice(comments)
      text = id.replace('{الاسم}', name).replace('{اليوزر}', username).replace('{الرسائل}',str(msgs)).replace('{التعديل}', str(edits)).replace('{الانشاء}', create).replace('{البايو}', f'{bio}').replace('{الايدي}', iD).replace('{الرتبه}', rank).replace('{التفاعل}', tfa3l).replace('{تعليق}', comment)
      likes_count = get_id_likes_total(m.from_user.id)
      id_markup = InlineKeyboardMarkup([[InlineKeyboardButton(f"❤️ {likes_count}", callback_data=f"idlike:{m.from_user.id}")]])
      if r.get(f'{m.chat.id}:disableIDPHOTO:{Dev_Zaid}'):
         return _send_id_card_reply(c, m.reply(text, disable_web_page_preview=True, reply_markup=id_markup), m.from_user.id, likes_count)
      else:
         if m.from_user.photo:
           get_user = c.invoke(GetFullUser(id=(c.resolve_peer(m.from_user.id))))
           photo = get_user.full_user.profile_photo
           if not photo:
             return _send_id_card_reply(c, m.reply(text, disable_web_page_preview=True, reply_markup=id_markup), m.from_user.id, likes_count)
           video = photo.video_sizes
           if video:
             if len(video) == 3:
               video = video[-2]
             else:
               video = video[-1]
           if video:
              file = BytesIO()
              hash = photo.access_hash
              if r.get(f"{hash}:{m.from_user.id}"):
                cached_bytes = c.download_media(r.get(f"{hash}:{m.from_user.id}"), in_memory=True)
                cached_bytes.name = f'{m.from_user.id}vid{m.chat.id}.mp4'
                return _send_id_card_reply(c, m.reply_animation(cached_bytes, caption=text, reply_markup=id_markup, has_spoiler=True), m.from_user.id, likes_count)
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
              file.name = f'{m.from_user.id}vid{m.chat.id}.mp4'
              send = m.reply_animation(file, caption=text, reply_markup=id_markup, has_spoiler=True)
              r.set(f"{hash}:{m.from_user.id}",send.animation.file_id,ex=3600)
              _send_id_card_reply(c, send, m.from_user.id, likes_count)
              return True
           else:
              file_id=FileId(
                        file_type=FileType.PHOTO,
                        dc_id=photo.dc_id,
                        media_id=photo.id,
                        access_hash=photo.access_hash,
                        file_reference=photo.file_reference,
                        thumbnail_source=ThumbnailSource.THUMBNAIL,
                        thumbnail_file_type=FileType.PHOTO,
                        thumbnail_size=photo.sizes[-1].type,
                        volume_id=0,
                        local_id=0
                    ).encode()
              photo_bytes = c.download_media(file_id, in_memory=True)
              photo_bytes.name = f'{m.from_user.id}pic{m.chat.id}.jpg'
              return _send_id_card_reply(c, m.reply_photo(photo_bytes, caption=text, reply_markup=id_markup, has_spoiler=True), m.from_user.id, likes_count)
         else:
           return _send_id_card_reply(c, m.reply(text, disable_web_page_preview=True, reply_markup=id_markup), m.from_user.id, likes_count)


@Client.on_message(filters.new_chat_members, group=1)
def addContact(c,m):
  for me in m.new_chat_members:
    if not m.from_user.id == me.id:
      if not r.get(f'{m.chat.id}TotalContacts{m.from_user.id}{Dev_Zaid}'):
        r.set(f'{m.chat.id}TotalContacts{m.from_user.id}{Dev_Zaid}',1)
      else:
        co = int(r.get(f'{m.chat.id}TotalContacts{m.from_user.id}{Dev_Zaid}'))
        r.set(f'{m.chat.id}TotalContacts{m.from_user.id}{Dev_Zaid}',co+1)


@Client.on_callback_query(filters.regex(r"^idlike:(-?\d+)$"))
async def id_like_callback(c, callback_query):
    owner_id = int(callback_query.matches[0].group(1))
    presser = callback_query.from_user

    if presser.id == owner_id:
        return await callback_query.answer("مينفعش تعجب بنفسك يا غبي 😅", show_alert=True)

    likers_key = f'{Dev_Zaid}:idlikers:{owner_id}'

    if r.sismember(likers_key, presser.id):
        r.srem(likers_key, presser.id)
        await callback_query.answer("💔 شلت اعجابك")
    else:
        r.sadd(likers_key, presser.id)
        await callback_query.answer("❤️ اتعجبت")
        try:
            await c.send_message(owner_id, f"{presser.mention} سولك قلب ❤️")
        except Exception:
            pass

    count = get_id_likes_total(owner_id)
    try:
        edit_colored_markup(c, callback_query.message.chat.id, callback_query.message.id, _blue_like_button(owner_id, count))
    except Exception:
        pass


'''

@Client.on_message(filters.text & filters.group, group=17)
def setIDHandler(c,m):
    k = r.get(f'{Dev_Zaid}:botkey')
    set_id(c,m,k)


def set_id(c,m,k):
   if not r.get(f'{m.chat.id}:enable:{Dev_Zaid}'):  return
   if not m.from_user: return
   if r.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):  return
   if r.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):  return
   if r.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):  return
   if r.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):  return
   text = m.text
   if r.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}'):
       text = r.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}')
   if r.get(f'Custom:{Dev_Zaid}&text={text}'):
       text = r.get(f'Custom:{Dev_Zaid}&text={text}')

'''



