import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    Message, 
    CallbackQuery
)
from pyrogram.enums import ParseMode
from dotenv import load_dotenv
from settings import config
from t5 import *
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class Premium:
    def __init__(self, db, config, bot):
        self.db = db
        self.config = config
        self.bot = bot
        self.user_sessions = {}
        self.premium_cache = {}  # Add this cache dictionary
        self.premium_plans = {
            'premium': {
                'name': 'Premium',
                'levels': {
                    '7d': {'days': 7, 'price': 40},
                    '1M': {'days': 30, 'price': 120},
               #     '3M': {'days': 90, 'price': 40},
               #     '6M': {'days': 180, 'price': 70},
              #      '1y': {'days': 365, 'price': 120},
             #       '0': {'days': 9999, 'price': 200, 'name': 'Lifetime'}
                }
            },
            'hpremium': {
                'name': 'H-Premium',
                'levels': {
                    '7d': {'days': 7, 'price': 90},
                    '1M': {'days': 30, 'price': 250},
               #     '3M': {'days': 90, 'price': 60},
                #    '6M': {'days': 180, 'price': 100},
               #     '1y': {'days': 365, 'price': 180},
              #      '0': {'days': 9999, 'price': 300, 'name': 'Lifetime'}
                }
            }
        }

    async def validate_premium_users(self):
        """Validate all premium users and revoke expired ones"""
        expired = await self.check_and_revoke_expired()
        if expired:
            logger.info(f"Revoked premium access for {len(expired)} expired users")

    async def check_and_revoke_expired(self):
        """Check and revoke expired premium access"""
        expired_users = []
        async for user in self.db.premium_users.find({"expiry_date": {"$lt": datetime.now()}}):
            expired_users.append(user['user_id'])
            await self.db.premium_users.delete_one({"_id": user['_id']})
        
        return expired_users

    async def validate_cache_periodically(self):
        """Periodically validate premium user cache"""
        while True:
            await asyncio.sleep(3600)  # Check every hour
            await self.validate_premium_users()
    async def check_access(self, user_id: int, required_level: str = 'normal', content_type: str = None) -> bool:
        """
        Check if user has required access level and content access based on premium mode and adult restrictions.

        Args:
            user_id: Telegram user ID
            required_level: Access level needed ('normal', 'premium', 'hpremium')
            content_type: Optional content type (e.g., 'adult', 'hentai')

        Returns:
            bool: True if access is granted, False otherwise
        """

        # Owners always have access
        if user_id in self.config.OWNERS:
            return True

        is_adult = content_type and content_type.upper() in ['ADULT', 'HENTAI']

        # PREMIUM MODE OFF
        if not self.config.PREMIUM_MODE:
            if self.config.ADULT_CONTENT_ENABLED and is_adult:
                user_data = await self._get_user_data(user_id)
                return self._has_hpremium(user_data)
            else:
                return True  # Everyone can access non-adult content

        # PREMIUM MODE ON
        user_data = await self._get_user_data(user_id)
        if not user_data:
            return False

        if is_adult:
            if not self.config.ADULT_CONTENT_ENABLED:
                return self._check_access_level(user_data, 'premium')
            else:
                return self._has_hpremium(user_data)

        return self._check_access_level(user_data, required_level)


    async def _get_user_data(self, user_id: int) -> Dict:
        """
        Fetch user access data with caching.

        Returns:
            dict: user access data or None if not found or expired
        """
        cached = self.premium_cache.get(user_id)
        if cached and (time.time() - cached.get('cache_time', 0)) < self.cache_timeout:
            user_data = cached['data']
            if user_data.get('expiry_date') and user_data['expiry_date'] < datetime.now():
                await self.revoke_access(user_id)
                return None
            return user_data

        user = await self.db.premium_users.find_one({"user_id": user_id})
        if not user:
            return None

        expiry = user.get('expiry_date')
        if expiry and expiry < datetime.now():
            await self.revoke_access(user_id)
            return None

        self.premium_cache[user_id] = {
            'data': {
                'access_level': user.get('access_level', 'normal'),
                'plan_type': user.get('plan_type', 'normal'),
                'expiry_date': expiry,
                'granted_at': user.get('granted_at')
            },
            'cache_time': time.time()
        }

        return self.premium_cache[user_id]['data']


    def _check_access_level(self, user_data: dict, required_level: str) -> bool:
        """
        Compare user level with required level based on ACCESS_LEVELS config.

        Returns:
            bool: True if user meets or exceeds the level
        """
        user_level = user_data.get('access_level', 'normal')
        user_val = self.config.ACCESS_LEVELS.get(user_level, 0)
        required_val = self.config.ACCESS_LEVELS.get(required_level, 0)
        return user_val >= required_val


    def _has_hpremium(self, user_data: dict) -> bool:
        """
        Check if user has H-Premium access.

        Returns:
            bool: True if plan_type or access_level is 'hpremium'
        """
        if not user_data:
            return False
        return user_data.get('plan_type') == 'hpremium' or user_data.get('access_level') == 'hpremium'


    async def get_user_status(self, user_id: int) -> Dict:
        """
        Get user’s premium status for display or logic purposes.

        Returns:
            dict: status including access level and plan name
        """
        user_data = await self._get_user_data(user_id)
        if not user_data:
            return {'is_premium': False, 'access_level': 'normal'}

        return {
            'is_premium': True,
            'access_level': user_data['plan_type'],
            'expiry_date': user_data['expiry_date'],
            'plan_name': self.premium_plans.get(user_data['plan_type'], {}).get('name', 'Unknown')
        }
    async def premium_users_menu(self, client: Client, message: Message):
        """Interactive premium users listing menu"""
        try:
            args = message.text.split()
            page = int(args[1]) if len(args) > 1 else 1
            per_page = 10
            skip = (page - 1) * per_page
            
            # Get accurate counts
            total_active = await self.db.premium_users.count_documents({
                "expiry_date": {"$gt": datetime.now()}
            })
            total_expired = await self.db.premium_users.count_documents({
                "expiry_date": {"$lte": datetime.now()}
            })
            
            # Get current page users
            users = await self.db.premium_users.find({
                "expiry_date": {"$gt": datetime.now()}
            }).sort("expiry_date", 1).skip(skip).limit(per_page).to_list(None)
            
            if not users:
                buttons = [
                    [InlineKeyboardButton("Refresh", callback_data=f"premium_list_1")]
                ]
                reply_markup = InlineKeyboardMarkup(buttons)
                return await message.reply(
                    "No active premium users found\n\n"
                    f"Total Active: {total_active}\n"
                    f"Total Expired: {total_expired}",
                    reply_markup=reply_markup
                )
            
            # Format user list
            user_list = []
            for idx, user in enumerate(users, start=skip+1):
                days_left = (user['expiry_date'] - datetime.now()).days
                user_list.append(
                    f"{idx}. ID: {user['user_id']} | {user.get('plan_type', 'premium').upper()}\n"
                    f"   ⏳ {days_left} days left | Until: {user['expiry_date'].strftime('%Y-%m-%d')}"
                )
            
            # Create pagination buttons
            buttons = []
            if page > 1:
                buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"premium_list_{page-1}"))
            if len(users) == per_page:
                buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"premium_list_{page+1}"))
            
            buttons.append([InlineKeyboardButton("Refresh", callback_data=f"premium_list_{page}")])
            reply_markup = InlineKeyboardMarkup([buttons] if buttons else None)
            
            await message.reply(
                f"🌟 Active Premium Users (Page {page}) 🌟\n\n" +
                "\n".join(user_list) +
                f"\n\n📊 Total Active: {total_active} | Total Expired: {total_expired}",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in premium_users_menu: {e}", exc_info=True)
            await message.reply("❌ Error displaying premium users list")
    async def grant_access(self, user_id: int, plan_type: str, duration_days: Optional[int] = None):
        """Grant premium access to a user"""
        if plan_type not in ['premium', 'hpremium']:
            raise ValueError("Invalid plan type")
            
        if duration_days is None:
            duration_days = 30  # Default 1 month
            
        await self.db.add_premium_user(user_id, plan_type, duration_days)

    async def revoke_access(self, user_id: int):
        """Revoke premium access from a user"""
        await self.db.remove_premium_user(user_id)

    async def premium_management(self, client: Client, callback_query: CallbackQuery):
        """Show premium management menu"""
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ Grant Premium", callback_data="grant_premium_menu"),
                InlineKeyboardButton("➖ Revoke Premium", callback_data="revoke_premium_menu")
            ],
            [
                InlineKeyboardButton("📜 List Premium Users", callback_data="list_premium_active"),
                InlineKeyboardButton("📊 Stats", callback_data="premium_stats")
            ],
            [
                InlineKeyboardButton("💎 Plans", callback_data="premium_plans"),
                InlineKeyboardButton("🔒 Toggle Mode", callback_data="toggle_premium_mode")
            ],
            [self.get_back_button("admin")]
        ])
        
        mode_status = "✅ ON" if self.config.PREMIUM_MODE else "❌ OFF"
        
        await self.bot.update_message(
            client,
            callback_query.message,
            f"💎 *Premium Management*\n\n"
            f"Current Mode: {mode_status}\n"
            "Manage premium subscriptions and settings:",
            reply_markup=keyboard
        )

    async def grant_premium_menu(self, client: Client, callback_query: CallbackQuery):
        """Show grant premium options menu"""
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💎 Grant Premium", callback_data="grant_premium"),
                InlineKeyboardButton("🔞 Grant H-Premium", callback_data="grant_hpremium")
            ],
            [
                InlineKeyboardButton("🛠 Custom Grant", callback_data="grant_custom"),
                InlineKeyboardButton("♾ Lifetime", callback_data="grant_lifetime")
            ],
            [self.get_back_button("premium")]
        ])
        
        await self.bot.update_message(
            client,
            callback_query.message,
            "➕ *Grant Premium Access*\n\n"
            "Select the type of premium access to grant:",
            reply_markup=keyboard
        )

    async def revoke_premium_menu(self, client: Client, callback_query: CallbackQuery):
        """Show revoke premium options menu"""
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📜 List to Revoke", callback_data="list_to_revoke"),
                InlineKeyboardButton("🆔 By ID", callback_data="revoke_by_id")
            ],
            [self.get_back_button("premium")]
        ])
        
        await self.bot.update_message(
            client,
            callback_query.message,
            "➖ *Revoke Premium Access*\n\n"
            "Select how you want to revoke premium access:",
            reply_markup=keyboard
        )

    async def start_grant_process(self, client: Client, callback_query: CallbackQuery, plan_type: str):
        """Start the premium grant process for a specific plan type"""
        if plan_type not in self.premium_plans:
            await callback_query.answer("Invalid plan type", show_alert=True)
            return
            
        keyboard = []
        row = []
        for duration, details in self.premium_plans[plan_type]['levels'].items():
            btn_text = f"{details.get('name', duration)} - ${details['price']}"
            row.append(InlineKeyboardButton(btn_text, callback_data=f"grant_{plan_type}_{duration}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
            
        keyboard.append([self.get_back_button("premium")])
        
        await self.bot.update_message(
            client,
            callback_query.message,
            f"⏳ *Grant {self.premium_plans[plan_type]['name']}*\n\n"
            "Select duration:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def process_grant_callback(self, client: Client, callback_query: CallbackQuery, plan_type: str, duration: str):
        """Process the grant premium callback"""
        if plan_type not in self.premium_plans or duration not in self.premium_plans[plan_type]['levels']:
            await callback_query.answer("Invalid selection", show_alert=True)
            return
            
        self.bot.user_sessions[callback_query.from_user.id] = {
            'action': 'granting_premium',
            'plan_type': plan_type,
            'duration': duration,
            'days': self.premium_plans[plan_type]['levels'][duration]['days']
        }
        
        await self.bot.update_message(
            client,
            callback_query.message,
            f"⏳ *Grant {self.premium_plans[plan_type]['name']}*\n\n"
            f"Duration: {duration}\n"
            f"Days: {self.premium_plans[plan_type]['levels'][duration]['days']}\n\n"
            "Please reply with the user ID or username:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data=f"grant_{plan_type}")]
            ])
        )
    async def grant_premium(self, client: Client, message: Message):
        """Properly handle premium granting with verification"""
        try:
            # Parse command arguments
            args = message.text.split()
            if len(args) < 3:
                return await message.reply("Usage: /grant_premium <user_id> <plan_type> <duration_days>")
            
            user_id = int(args[1])
            plan_type = args[2].lower()
            duration = int(args[3]) if len(args) > 3 else 30  # Default 30 days
            
            # Validate plan type
            if plan_type not in ['premium', 'hpremium']:
                return await message.reply("Invalid plan type. Use 'premium' or 'hpremium'")
            
            # Grant premium access
            success = await self.db.add_premium_user(user_id, plan_type, duration)
            
            if not success:
                return await message.reply("❌ Failed to grant premium access")
            
            # Verify the user was actually added
            premium_user = await self.db.premium_users.find_one({"user_id": user_id})
            if not premium_user:
                return await message.reply("❌ Verification failed - user not found in premium collection")
            
            # Update user cache
            await self.premium.update_user_cache(user_id)
            
            # Send success message with details
            expiry_date = premium_user['expiry_date'].strftime('%Y-%m-%d')
            await message.reply(
                f"✅ Successfully granted {plan_type} access to user {user_id}\n"
                f"📅 Expires on: {expiry_date}\n"
                f"🔍 Verify with: /check_premium {user_id}"
            )
            
            # Optional: Notify the user
            try:
                await client.send_message(
                    user_id,
                    f"🎉 You've been granted {plan_type} access!\n"
                    f"⏳ Expires: {expiry_date}\n"
                    f"💎 Features unlocked!"
                )
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error in grant_premium: {e}", exc_info=True)
            await message.reply("❌ Error processing your request")
    async def list_premium_users(self, client: Client, callback_query: CallbackQuery, filter_type: str = "active"):
        """
        List premium users with optional filtering (active, expired, all).
        Shows user name, premium tier tag, and expiration info.
        """
        if filter_type not in ["active", "expired", "all"]:
            filter_type = "active"
            
        users = await self.db.get_all_premium_users(filter_type)

        if not users:
            await callback_query.answer(f"No {filter_type} premium users found", show_alert=True)
            return

        message = f"📜 *Premium Users ({filter_type.capitalize()})*\n\n"
        keyboard = []

        for user in users[:10]:  # Limit to 10 users shown
            user_id = user['user_id']
            plan_type = user.get('plan_type', 'normal')
            plan_name = self.premium_plans.get(plan_type, {}).get('name', plan_type.capitalize())

            # Tag based on plan
            tag = {
                'normal': '[Normal]',
                'premium': '[Premium]',
                'hpremium': '[H-Premium]'
            }.get(plan_type, '[Unknown]')

            # Try to fetch username/full name
            try:
                user_info = await client.get_users(user_id)
                display_name = f"{user_info.first_name or ''} {user_info.last_name or ''}".strip()
                if user_info.username:
                    display_name += f" (@{user_info.username})"
            except Exception:
                display_name = "Unknown User"

            # Expiry handling
            expiry = user.get('expiry_date')
            days_left = (expiry - datetime.now()).days if expiry and filter_type == "active" else 0
            expires_str = expiry.strftime('%Y-%m-%d') if expiry else "N/A"

            # Compose message block
            message += (
                f"{tag} 👤 *{display_name}* (`{user_id}`)\n"
                f"💎 Plan: {plan_name}\n"
                f"📅 Expires: {expires_str}"
            )

            message += f" (in {days_left} days)\n\n" if days_left > 0 else " (Expired)\n\n"

            if filter_type == "active":
                keyboard.append([
                    InlineKeyboardButton(
                        f"Revoke {user_id}",
                        callback_data=f"revoke_{user_id}"
                    )
                ])

        # Add filter buttons
        filter_buttons = [
            InlineKeyboardButton("Active", callback_data="list_premium_active"),
            InlineKeyboardButton("Expired", callback_data="list_premium_expired"),
            InlineKeyboardButton("All", callback_data="list_premium_all"),
        ]

        keyboard.append(filter_buttons)
        keyboard.append([self.get_back_button("premium")])

        await self.bot.update_message(
            client,
            callback_query.message,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_premium_plans(self, client: Client, callback_query: CallbackQuery):
        message = "💎 *Premium Plans*\n\n"
        message += "🔹 *Premium Features:*\n"
        message += "- Unlimited downloads\n"
        message += "- One-click download for all \n"

        message += "- Priority support\n\n"
        message += "🔞 *H-Premium Features:*\n"
        message += "- All Premium features\n"
        message += "- Access to H@ntai/A content\n\n"
        message += "Select a plan to view details:"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💎 Premium", callback_data="premium_benefits_premium"),
                InlineKeyboardButton("🔞 H-Premium", callback_data="premium_benefits_hpremium")
            ],
            [
                InlineKeyboardButton("❓ FAQ", callback_data="premium_faq"),
                InlineKeyboardButton("💳 Purchase", callback_data="purchase_menu")
            ],
            [self.get_back_button("start")]
        ])
        
        await self.bot.update_message(
            client,
            callback_query.message,
            message,
            reply_markup=keyboard
        )

    async def show_premium_benefits(self, client: Client, callback_query: CallbackQuery, plan_type: str):
        """Show benefits of a specific premium plan"""
        if plan_type not in self.premium_plans:
            await callback_query.answer("Invalid plan type", show_alert=True)
            return
            
        plan = self.premium_plans[plan_type]
        message = f"🌟 *{plan['name']} Benefits*\n\n"
        
        if plan_type == 'premium':
            message += "✅ Unlimited downloads\n"
            message += "✅ No limits\n"
            message += "✅ Priority support\n"
            message += "✅ Early access to new features\n"
        else:
            message += "🔞 Includes all Premium benefits PLUS:\n"
            message += "✅ Access to adult content\n"
            message += "✅ Exclusive content\n"
        
        message += "\n💵 *Pricing:*\n"
        for duration, details in plan['levels'].items():
            message += f"- {details.get('name', duration)}: ₹{details['price']}\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Purchase Now", callback_data=f"purchase_{plan_type}")],
            [InlineKeyboardButton("❌ Close", callback_data="close_message")]
        ])
        
        await self.bot.update_message(
            client,
            callback_query.message,
            message,
            reply_markup=keyboard
        )

    async def show_premium_faq(self, client: Client, callback_query: CallbackQuery):
        """Show premium FAQ"""
        faq = (
            "❓ *Premium FAQ*\n\n"
            "🔹 *How do I purchase premium?*\n"
            "Currently premium can only be granted by admins. Contact @admin for details.\n\n"
            "🔹 *What payment methods are accepted?*\n"
            "We accept PayPal, cryptocurrency, and other payment methods.\n\n"
            "🔹 *How do I check my premium status?*\n"
            "Use /myplan command to see your current subscription details.\n\n"
            "🔹 *What's the difference between Premium and H-Premium?*\n"
            "H-Premium includes access to adult content in addition to all Premium features."
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 View Plans", callback_data="premium_plans")],
            [self.get_back_button("start")]
        ])
        
        await self.bot.update_message(
            client,
            callback_query.message,
            faq,
            reply_markup=keyboard
        )

    async def show_premium_stats(self, client: Client, callback_query: CallbackQuery):
        """Show premium statistics"""
        active = await self.db.premium_users.count_documents({"expiry_date": {"$gt": datetime.now()}})
        expired = await self.db.premium_users.count_documents({"expiry_date": {"$lt": datetime.now()}})
        
        premium = await self.db.premium_users.count_documents({
            "plan_type": "premium",
            "expiry_date": {"$gt": datetime.now()}
        })
        
        hpremium = await self.db.premium_users.count_documents({
            "plan_type": "hpremium",
            "expiry_date": {"$gt": datetime.now()}
        })
        
        message = (
            "📊 *Premium Statistics*\n\n"
            f"🔹 Active Subscriptions: {active}\n"
            f"   - Premium: {premium}\n"
            f"   - H-Premium: {hpremium}\n"
            f"🔹 Expired Subscriptions: {expired}\n"
            f"🔹 Premium Mode: {'✅ ON' if self.config.PREMIUM_MODE else '❌ OFF'}\n"
            f"🔹 Adult Restriction: {'✅ ON' if self.config.RESTRICT_ADULT else '❌ OFF'}"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="premium_stats")],
            [self.get_back_button("plans")]
        ])
        
        await self.bot.update_message(
            client,
            callback_query.message,
            message,
            reply_markup=keyboard
        )

    async def toggle_premium_mode(self, client: Client, callback_query: CallbackQuery):
        """Toggle premium mode on/off"""
        self.config.PREMIUM_MODE = not self.config.PREMIUM_MODE
        os.environ["PREMIUM_MODE"] = str(self.config.PREMIUM_MODE)
        
        status = "✅ ON" if self.config.PREMIUM_MODE else "❌ OFF"
        await callback_query.answer(f"Premium mode is now {status}")
        
        # Refresh the current view
        if "premium" in callback_query.data:
            await self.premium_management(client, callback_query)
        else:
            await self.show_premium_stats(client, callback_query)


    async def show_my_plan(self, client: Client, message: Message):
        """Show user their current premium status"""
        user_id = message.from_user.id
        user_status = await self.get_user_status(user_id)

        # Fetch user's download info
        user = await self.db.users_collection.find_one({"user_id": user_id}) or {}
        today = datetime.now().date().isoformat()

        # Reset if it's a new day (optional safeguard)
        if user.get("last_download_date") != today:
            await self.db.users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"download_count": 0, "last_download_date": today}},
                upsert=True
            )
            download_count = 0
        else:
            download_count = user.get("download_count", 0)

        # Determine user access level and max downloads
        if user_status['is_premium']:
            premium_user = await self.db.premium_users.find_one({"user_id": user_id})
            plan_type = premium_user.get("plan_type") if premium_user else "unknown"
            access_level = 2 if plan_type == "hpremium" else 1
        else:
            access_level = 0

        max_downloads = self.config.MAX_DAILY_DOWNLOADS.get(access_level, 24)

        # Non-premium users
        if not user_status['is_premium']:
            # Calculate reset time
            reset_time = datetime.combine(
                datetime.now().date() + timedelta(days=1),
                datetime.min.time()
            )
            time_left = reset_time - datetime.now()
            hours = time_left.seconds // 3600
            minutes = (time_left.seconds % 3600) // 60

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Get Premium", callback_data="premium_plans")],
                [InlineKeyboardButton("❌ Close", callback_data="close_message")]
            ])

            msg = (
                "🔓 *You don't have an active premium subscription*\n\n"
                f"📥 *Today's Downloads:* `{download_count}/{max_downloads}`\n"
                f"⏳ *Resets in:* `{hours}h {minutes}m`\n\n"
                "Upgrade to premium for unlimited downloads and exclusive features!"
            )

            await message.reply_text(msg, reply_markup=keyboard)
            return

        # Premium users
        expiry_date = user_status['expiry_date'].strftime("%Y-%m-%d")
        days_left = (user_status['expiry_date'] - datetime.now()).days

        msg = (
            f"🌟 *Your {user_status['plan_name']} Subscription*\n\n"
            f"🔹 Status: ✅ Active\n"
            f"🔹 Expiry Date: {expiry_date}\n"
            f"🔹 Days Remaining: {days_left}\n"
            f"📥 Unlimited daily downloads\n\n"
        )

        if days_left < 7:
            msg += "⚠️ Your subscription is expiring soon! Renew to maintain access.\n\n"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Renew", callback_data="premium_plans")],
            [InlineKeyboardButton("❌ Close", callback_data="close_message")]
        ])

        await message.reply_text(msg, reply_markup=keyboard)

    def get_back_button(self, back_to: str) -> InlineKeyboardButton:
        """Returns a consistent back button"""
        back_targets = {
            "admin": ("admin_panel", "🔙 Admin Panel"),
            "start": ("start_menu", "🔙 Main Menu"),
            "premium": ("premium_management", "🔙 Premium Panel"),
            "plans": ("premium_plans","🔙 Premium Plans")
        }
        return InlineKeyboardButton(back_targets[back_to][1], callback_data=back_targets[back_to][0])
