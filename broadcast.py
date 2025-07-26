from pyrogram import Client, filters
from pyrogram.types import Message
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

class Broadcast:
    def __init__(self, db,config):
        self.db = db
        self.config = config
       
    
    async def broadcast_message(self, client: Client, message: Message):
        if not message.reply_to_message:
            await message.reply_text("Please reply to a message to broadcast it.")
            return
        
        reply_msg = message.reply_to_message
        users = await self.db.users_collection.find({}).to_list(None)
        
        success = 0
        failed = 0
        processing_msg = await message.reply_text(f"📢 Broadcasting to {len(users)} users...")
        
        for user in users:
            try:
                if reply_msg.text:
                    await client.send_message(user['user_id'], reply_msg.text)
                elif reply_msg.photo:
                    await client.send_photo(
                        user['user_id'], 
                        reply_msg.photo.file_id,
                        caption=reply_msg.caption
                    )
                elif reply_msg.video:
                    await client.send_video(
                        user['user_id'],
                        reply_msg.video.file_id,
                        caption=reply_msg.caption
                    )
                elif reply_msg.document:
                    await client.send_document(
                        user['user_id'],
                        reply_msg.document.file_id,
                        caption=reply_msg.caption
                    )
                else:
                    failed += 1
                    continue
                    
                success += 1
                await asyncio.sleep(0.1)  # Rate limiting
                
                if success % 20 == 0:
                    await processing_msg.edit_text(
                        f"📢 Broadcasting...\n"
                        f"✅ Success: {success}\n"
                        f"❌ Failed: {failed}"
                    )
                    
            except Exception as e:
                failed += 1
                logger.error(f"Broadcast failed for {user['user_id']}: {e}")
        
        await processing_msg.edit_text(
            f"📢 Broadcast Complete!\n"
            f"✅ Success: {success}\n"
            f"❌ Failed: {failed}"
        )
