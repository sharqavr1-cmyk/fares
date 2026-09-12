###############################
# ███████╗░█████╗░██╗██████╗░ #
# ╚════██║██╔══██╗██║██╔══██╗ #
# ░░███╔═╝███████║██║██║░░██║ #
# ██╔══╝░░██╔══██║██║██║░░██║ #
# ███████╗██║░░██║██║██████╔╝ #
# ╚══════╝╚═╝░░╚═╝╚═╝╚═════╝░ #
##############################
#   https://t.me/DevZaid      #
###############################
import asyncio
import redis.asyncio as redis
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from datetime import datetime, timedelta
from config import token

chats_db = {}
db = redis.Redis(decode_responses=True)

DevZaid = Client(
    "cleaner",
    24217199,
    "11c12a66dbd23da592211771db1bce6b",
    bot_token=token,
    in_memory=True
)
ZAID = token.split(':')[0]


@DevZaid.on_message(filters.group & filters.media, group=1)
async def add_messages(c: Client, m: Message):
    chat_id = str(m.chat.id)
    if m.from_user:
        id = m.from_user.id
        mention = m.from_user.mention
    elif m.sender_chat:
        id = m.sender_chat.id
        mention = m.sender_chat.title
    
    if m.chat.id not in chats_db:
        chats_db[m.chat.id]=[]
    
    if (m.media) and not m.audio and not m.voice and not m.game:
        if await db.hget(ZAID+str(m.chat.id), "ena-clean"):
            secs = int(await db.hget(ZAID+chat_id, "clean-secs") or "60")
            time_now = datetime.now()
            data = {"id":m.id, "time":time_now + timedelta(seconds=secs)}
            chats_db[m.chat.id].append(data)
            
    
    if m.media_group_id and await db.hget(ZAID+str(m.chat.id), "ena-clean"):
        secs = int(await db.hget(ZAID+chat_id, "clean-secs") or "60")
        time_now = datetime.now()
        msgs = await c.get_media_group(m.chat.id, m.id)
        for msg in msgs:
            data = {"id":msg.id, "time":time_now + timedelta(seconds=secs)}
            chats_db[m.chat.id].append(data)
    
    # print(chats_db)

async def auto_clean_function():
    while not await asyncio.sleep(1.7):
        try:
            for chat_id in chats_db:
                msgs_ids = []
                for msg in chats_db[chat_id]:
                    if datetime.now() > msg["time"]:
                        msgs_ids.append(msg['id'])
                        chats_db[chat_id].remove(msg)
                try:
                    await DevZaid.delete_messages(chat_id, msgs_ids)
                except FloodWait as flood:
                    await asyncio.sleep(flood.value)
                except Exception:
                    continue
        except Exception as e:
            print(e)

async def main():
    await DevZaid.start()
    print(DevZaid.me.username)
    asyncio.create_task(auto_clean_function())
    await idle()
    
if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())

