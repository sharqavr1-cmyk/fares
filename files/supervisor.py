# files/supervisor.py

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ChatMembersFilter
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from files import config

@Client.on_chat_member_updated(filters.group)
async def bot_added_or_promoted(client, update):
    user = update.new_chat_member.user if update.new_chat_member else (update.old_chat_member.user if update.old_chat_member else None)
    if not user or not user.is_self:
        return

    old_status = update.old_chat_member.status if update.old_chat_member else None
    new_status = update.new_chat_member.status if update.new_chat_member else None
    chat = update.chat

    if new_status == ChatMemberStatus.MEMBER and old_status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        warning_text = "لقد قمت بإضافة البوت كعضو لا يمكن للبوت البقاء، الرجاء إدخال البوت كمشرف للاستمرار في العمل."
        try:
            await client.send_message(chat.id, warning_text)
            await client.leave_chat(chat.id)
            if hasattr(config, "assistant_client") and config.assistant_client:
                if hasattr(config, "call_py") and config.call_py:
                    await config.call_py.leave_call(chat.id)
                from telethon.functions.channels import LeaveChannelRequest
                await config.assistant_client(LeaveChannelRequest(chat.id))
        except:
            pass
        return

    if old_status == ChatMemberStatus.ADMINISTRATOR and new_status != ChatMemberStatus.ADMINISTRATOR:
        leave_text = f"⚙️ **غادر البوت مجموعة:**\n\n📌 **الاسم:** {chat.title}\n🆔 **الايدي:** `{chat.id}`\n⚠️ **السبب:** تم تنزيله من الإشراف أو طرده."
        try:
            await client.send_message(config.OWNER_ID, leave_text)
        except:
            pass

        if new_status == ChatMemberStatus.MEMBER:
            try:
                await client.send_message(chat.id, "⚠️ تم تنزيلي من الإشراف، لا يمكنني البقاء كعضو عادي. سأغادر الآن.")
                await client.leave_chat(chat.id)
                if hasattr(config, "assistant_client") and config.assistant_client:
                    if hasattr(config, "call_py") and config.call_py:
                        await config.call_py.leave_call(chat.id)
                    from telethon.functions.channels import LeaveChannelRequest
                    await config.assistant_client(LeaveChannelRequest(chat.id))
            except:
                pass
        return

    if new_status == ChatMemberStatus.ADMINISTRATOR and old_status != ChatMemberStatus.ADMINISTRATOR:
        
        dev_url = None
        try:
            dev_user = await client.get_users(config.OWNER_ID)
            if dev_user.username:
                dev_url = f"https://t.me/{dev_user.username}"
        except:
            pass

        group_photo_id = chat.photo.big_file_id if chat.photo else None
        
        owner_url = None
        owner_mention = "غير معروف"
        try:
            async for admin in client.get_chat_members(chat.id, filter=ChatMembersFilter.ADMINISTRATORS):
                if admin.status == ChatMemberStatus.OWNER:
                    owner_mention = admin.user.mention
                    if admin.user.username:
                        owner_url = f"https://t.me/{admin.user.username}"
                    break
        except:
            pass

        # 🔴 التعديل هنا: جلب يوزر الجروب أو إنشاء رابط دعوة "جديد" لتجنب انتهاء الصلاحية
        group_link = None
        try:
            if chat.username:
                group_link = f"https://t.me/{chat.username}"
            else:
                invite = await client.create_chat_invite_link(chat.id)
                group_link = invite.invite_link
        except:
            pass

        text_group = f"🌹 **شكراً لتفعيل البوت في مجموعة ( {chat.title} )**\n\nأنا الآن مشرف وجاهز للعمل، يمكنك استخدام الأوامر الآن بكل حرية 🎧\n👤 **للتواصل مع المطور:** [اضغط هنا](tg://user?id={config.OWNER_ID})"
        
        group_buttons = []
        if dev_url:
            group_buttons.append([InlineKeyboardButton("المطور", url=dev_url)])
        group_markup = InlineKeyboardMarkup(group_buttons) if group_buttons else None
        
        try:
            if group_photo_id:
                try:
                    await client.send_photo(chat.id, photo=group_photo_id, caption=text_group, reply_markup=group_markup)
                except:
                    await client.send_message(chat.id, text_group, reply_markup=group_markup)
            else:
                await client.send_message(chat.id, text_group, reply_markup=group_markup)
        except:
            pass
            
        dev_text = (
            f"🚀 **تم تفعيل البوت في مجموعة جديدة!**\n\n"
            f"📌 **الاسم:** {chat.title}\n"
            f"🆔 **الايدي:** `{chat.id}`\n"
            f"👤 **المالك:** {owner_mention}\n"
        )
        if group_link:
            dev_text += f"🔗 **الرابط:** متاح في الزر بالأسفل"
        else:
            dev_text += "🔗 **الرابط:** (لا أملك صلاحية لإنشاء رابط)"
        
        dev_buttons = []
        if group_link:
            dev_buttons.append(InlineKeyboardButton("الجروب", url=group_link))
        if owner_url:
            dev_buttons.append(InlineKeyboardButton("مالك الجروب", url=owner_url))
            
        dev_markup = InlineKeyboardMarkup([dev_buttons]) if dev_buttons else None
        
        try:
            if group_photo_id:
                try:
                    await client.send_photo(config.OWNER_ID, photo=group_photo_id, caption=dev_text, reply_markup=dev_markup)
                except:
                    await client.send_message(config.OWNER_ID, dev_text, reply_markup=dev_markup)
            else:
                await client.send_message(config.OWNER_ID, dev_text, reply_markup=dev_markup)
        except:
            pass
