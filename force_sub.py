import os
from datetime import datetime
from typing import List
from pyrogram import Client
from pyrogram.errors import UserNotParticipant
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from violet import config 
class ForceSub:
    def __init__(self, db, bot_instance):  # Add bot_instance parameter
        self.db = db
        self.bot = bot_instance  # Store bot instance
        self.force_sub_enabled = False
        self.force_sub_channels: List[int] = []
        self.load_config()


    def load_config(self):
        """Load settings from environment"""
        self.force_sub_enabled = os.getenv("FORCE_SUB_ENABLED", "False").lower() == "true"
        channels = os.getenv("FORCE_SUB_CHANNELS", "")
        self.force_sub_channels = [int(c.strip()) for c in channels.split(",") if c.strip()]

    async def save_config(self):
        """Save to env and DB"""
        os.environ["FORCE_SUB_ENABLED"] = str(self.force_sub_enabled)
        os.environ["FORCE_SUB_CHANNELS"] = ",".join(map(str, self.force_sub_channels))
        await self.db.stats_collection.update_one(
            {"type": "force_sub_settings"},
            {
                "$set": {
                    "enabled": self.force_sub_enabled,
                    "channels": self.force_sub_channels,
                    "last_updated": datetime.utcnow()
                }
            },
            upsert=True
        )

    async def initialize(self):
        """Load from DB"""
        settings = await self.db.stats_collection.find_one({"type": "force_sub_settings"})
        if settings:
            self.force_sub_enabled = settings.get("enabled", False)
            self.force_sub_channels = settings.get("channels", [])
            await self.save_config()

    async def check_member(self, client: Client, user_id: int) -> bool:
        if not self.force_sub_enabled or not self.force_sub_channels:
            return True
            
        for channel_id in self.force_sub_channels:
            try:
                member = await client.get_chat_member(channel_id, user_id)
                if member.status in ["left", "kicked", "restricted"]:
                    return False
            except UserNotParticipant:
                return False
            except (ChannelInvalid, ChannelPrivate, ChatAdminRequired):
                # Channel doesn't exist or bot doesn't have access
                logger.warning(f"Force sub channel {channel_id} is inaccessible")
                continue
            except Exception as e:
                logger.error(f"Error checking channel {channel_id}: {e}")
                continue
                
        return True

    async def get_force_sub_message(self, client: Client):
        if not self.force_sub_channels:
            return "Force subscribe is enabled but no channels are set!", None

        message = "📢 **Join these channels to use the bot:**\n"
        buttons = []
        valid_channels = 0
        
        for channel_id in self.force_sub_channels:
            try:
                chat = await client.get_chat(channel_id)
                link = chat.invite_link or await chat.export_invite_link()
                message += f"🔹 {chat.title}\n"
                buttons.append([InlineKeyboardButton(f" {chat.title}", url=link)])
                valid_channels += 1
            except Exception as e:
                logger.warning(f"Could not get info for channel {channel_id}: {e}")
                continue
                
        if valid_channels == 0:
            return "❌ Force subscription is enabled but all channels are invalid!", None
            
        buttons.append([InlineKeyboardButton("✅ I've Joined", callback_data="check_force_sub")])
        return message, InlineKeyboardMarkup(buttons)
    async def toggle_force_sub(self, enable: bool):
        self.force_sub_enabled = enable
        await self.save_config()

    async def add_channel(self, channel_id: int) -> bool:
        if channel_id not in self.force_sub_channels:
            self.force_sub_channels.append(channel_id)
            await self.save_config()
            return True
        return False

    async def remove_channel(self, channel_id: int) -> bool:
        if channel_id in self.force_sub_channels:
            self.force_sub_channels.remove(channel_id)
            await self.save_config()
            return True
        return False

    async def show_settings(self, client: Client, message: Message):
        status = "✅ Enabled" if self.force_sub_enabled else "❌ Disabled"
        message_text = f"⚙️ **Force Subscription Settings**\n\nStatus: {status}\nChannels ({len(self.force_sub_channels)}):\n"
        channel_list = []

        for channel_id in self.force_sub_channels:
            try:
                chat = await client.get_chat(channel_id)
                channel_list.append(f"🔹 {chat.title} (`{channel_id}`)")
            except:
                channel_list.append(f"🔹 Unknown Channel (`{channel_id}`)")

        if channel_list:
            message_text += "\n".join(channel_list)
        else:
            message_text += "No channels set."

        keyboard = [
            [InlineKeyboardButton("✅ Enable" if not self.force_sub_enabled else "❌ Disable", callback_data="toggle_force_sub")],
            [InlineKeyboardButton("➕ Add Channel", callback_data="add_force_sub_channel")],
            [InlineKeyboardButton("🗑 Remove Channel", callback_data="remove_force_sub_channel")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_settings")]
        ]

        await message.reply_text(message_text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def add_channel_start(self, client: Client, message: Message):
            await message.reply_text(
                "📢 **Add Force Subscription Channel**\n\n"
                "Send the channel ID or @username (bot must be admin there).\n"
                "Example: `-100123456789` or `@channelusername`\n\n"
                "Use /cancel to abort.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="force_sub_settings")]])
            )
            self.bot.user_sessions[message.from_user.id] = {"state": "adding_force_sub_channel"}

    async def remove_channel_start(self, client: Client, message: Message):
        if not self.force_sub_channels:
            await message.reply_text("❌ No channels to remove.")
            return

        await message.reply_text(
            "🗑 **Remove Force Subscription Channel**\n\n"
            "Send the Channel ID you want to remove.\n\nUse /cancel to abort.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="force_sub_settings")]])
        )
        self.bot.user_sessions[message.from_user.id] = {"state": "removing_force_sub_channel"}
    async def process_add_channel(self, client: Client, message: Message):
        user_id = message.from_user.id
        text = message.text.strip()

        try:
            # Determine if input is username or numeric ID
            if text.startswith("@"):
                chat = await client.get_chat(text)
            else:
                chat_id = int(text)
                chat = await client.get_chat(chat_id)
        except ValueError:
            await message.reply_text("❌ Invalid channel ID. Make sure you include the -100 prefix for channels.")
            return
        except Exception as e:
            await message.reply_text(f"❌ Cannot access chat: `{e}`\n"
                                    "Make sure the bot is added to the channel or supergroup and is an admin.")
            return

        # Only allow channels or supergroups
        if chat.type not in ["channel", "supergroup"]:
            await message.reply_text("❌ Only channels or supergroups can be added.")
            return

        # Check if bot is admin
        try:
            bot_member = await client.get_chat_member(chat.id, (await client.get_me()).id)
            if bot_member.status not in ["administrator", "creator"]:
                await message.reply_text("❌ Bot must be admin in that channel or supergroup.")
                return
        except Exception as e:
            await message.reply_text(f"❌ Cannot verify bot permissions: `{e}`")
            return

        # Add the channel
        added = await self.add_channel(chat.id)
        if added:
            await message.reply_text(
                f"✅ Added channel: **{chat.title}**\n🆔 `{chat.id}`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="force_sub_settings")]])
            )
        else:
            await message.reply_text("ℹ️ Channel already exists in force sub list.")

        # Clear user session
        self.bot.user_sessions.pop(user_id, None)

    async def process_remove_channel(self, client: Client, message: Message):
        user_id = message.from_user.id
        text = message.text.strip()

        try:
            channel_id = int(text)
            removed = await self.remove_channel(channel_id)
            if removed:
                await message.reply_text(f"✅ Removed channel `{channel_id}`.")
            else:
                await message.reply_text("❌ Channel not found in list.")
        except Exception as e:
            await message.reply_text(f"❌ Error: `{e}`")

        # Use self.bot instead of bot
        self.bot.user_sessions.pop(user_id, None)
    async def handle_callback(self, client: Client, callback_query):
        data = callback_query.data
        user_id = callback_query.from_user.id

        if data == "force_sub_settings":
            await self.show_settings(client, callback_query.message)

        elif data == "toggle_force_sub":
            await self.toggle_force_sub(not self.force_sub_enabled)
            await self.show_settings(client, callback_query.message)

        elif data == "add_force_sub_channel":
            await callback_query.message.delete()
            await self.add_channel_start(client, callback_query.message)

        elif data == "remove_force_sub_channel":
            await callback_query.message.delete()
            await self.remove_channel_start(client, callback_query.message)

        elif data == "check_force_sub":
            joined = await self.check_member(client, user_id)
            if joined:
                await callback_query.answer("✅ Thanks for joining!", show_alert=True)
                await callback_query.message.delete()
            else:
                await callback_query.answer("❗ You're still missing one or more channels.", show_alert=True)
