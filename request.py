import re 
import asyncio
from datetime import datetime
from bson import ObjectId
import uuid
import logging
from pyrogram import filters, Client
from pyrogram.enums import ParseMode
from pyrogram.types import (
    Message, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    CallbackQuery
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class RequestSystem:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.config = bot.config
        self.cooldown = 300  # 5 minutes cooldown
        self.pending_requests = {}
        
    async def handle_request(self, client: Client, message: Message):
        try:
            # Extract anime name with command validation
            try:
                command, anime_name = message.text.split(' ', 1)
                anime_name = anime_name.strip()
                if len(anime_name) < 3:
                    await message.reply_text("❌ Anime name must be at least 3 characters")
                    return
            except:
                await message.reply_text("❌ Usage: /request <anime name>")
                return

            # Check if anime already exists (90% match threshold)
            existing_anime = await self._find_similar_anime(anime_name, similarity_threshold=0.9)
            if existing_anime:
                await message.reply_text(
                    f"ℹ️ This anime already exists in our database:\n\n"
                    f"🎬 {existing_anime['title']}\n"
                    f"📺 Episodes: {existing_anime.get('episodes', 'N/A')}\n\n"
                    f"Try searching with /search {anime_name}",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Process new request
            request_id = str(uuid.uuid4())
            request_data = {
                "request_id": request_id,
                "user_id": message.from_user.id,
                "anime_name": anime_name,
                "status": "pending",
                "timestamp": datetime.now(),
                "processed_by": None,
                "processed_date": None,
                "is_notified": False,
                "is_uploaded": False
            }
            
            await self.db.requests_collection.insert_one(request_data)
            
            # Improved admin notification
            admin_keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_req:{request_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_req:{request_id}")
                ],
                [InlineKeyboardButton("❌ Close", callback_data=f"close_req:{request_id}")]
            ])

            for admin_id in self.config.ADMINS:
                try:
                    await client.send_message(
                        admin_id,
                        f"📝 *New Anime Request*\n\n"
                        f"👤 User: {message.from_user.mention}\n"
                        f"🆔 ID: `{message.from_user.id}`\n"
                        f"🎬 Anime: `{anime_name}`\n"
                        f"📌 Request ID: `{request_id}`\n\n"
                        f"⏰ Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        reply_markup=admin_keyboard,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"Error notifying admin {admin_id}: {e}")

            await message.reply_text(
                "✅ *Request Submitted!*\n\n"
                f"🎬 Anime: `{anime_name}`\n"
                f"🆔 Request ID: `{request_id}`\n\n"
                "We'll notify you when it's processed.",
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            await message.reply_text("⚠️ An error occurred. Please try again later.")

    async def _find_similar_anime(self, search_query: str, similarity_threshold: float = 0.8):
        """Find similar anime using fuzzy matching"""
        try:
            # First try exact match
            for client in self.db.anime_clients:
                db = client[self.db.db_name]
                exact_match = await db.anime.find_one(
                    {"title": {"$regex": f"^{re.escape(search_query)}$", "$options": "i"}}
                )
                if exact_match:
                    return exact_match

            # Then try fuzzy matching
            all_anime = []
            for client in self.db.anime_clients:
                db = client[self.db.db_name]
                cluster_anime = await db.anime.find(
                    {"title": {"$regex": f".*{re.escape(search_query)}.*", "$options": "i"}}
                ).to_list(None)
                all_anime.extend(cluster_anime)

            # Use fuzzywuzzy for better matching
            from fuzzywuzzy import fuzz
            best_match = None
            highest_ratio = 0
            
            for anime in all_anime:
                ratio = fuzz.ratio(search_query.lower(), anime['title'].lower())
                if ratio > highest_ratio:
                    highest_ratio = ratio
                    best_match = anime
                    if highest_ratio >= 100:  # Exact match found
                        break

            if best_match and highest_ratio >= (similarity_threshold * 100):
                return best_match
            return None

        except Exception as e:
            logger.error(f"Error in _find_similar_anime: {e}")
            return None

    async def view_requests_page(self, client: Client, callback_query: CallbackQuery, page: int = 1):
        try:
            per_page = 5
            skip = (page - 1) * per_page
            
            total_requests = await self.db.requests_collection.count_documents({})
            requests = await self.db.requests_collection.find().sort("timestamp", -1).skip(skip).limit(per_page).to_list(None)
            
            if not requests:
                await callback_query.answer("No requests found", show_alert=True)
                return
                
            keyboard = []
            for req in requests:
                request_id = req.get('request_id', str(uuid.uuid4()))
                status = req.get('status', 'pending')
                anime_name = req.get('anime_name', 'Unknown Anime')
                
                display_name = (anime_name[:20] + '...') if len(anime_name) > 20 else anime_name
                emoji = "🟢" if status == 'approved' else "🔴" if status == 'rejected' else "🟡"
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"{emoji} {display_name}",
                        callback_data=f"request_detail:{request_id}"
                    )
                ])
            
            # Pagination
            total_pages = (total_requests + per_page - 1) // per_page
            pagination = []
            if page > 1:
                pagination.append(
                    InlineKeyboardButton(
                        "⬅️ Prev", 
                        callback_data=f"requests_page:{page-1}"
                    )
                )
            if page < total_pages:
                pagination.append(
                    InlineKeyboardButton(
                        "Next ➡️", 
                        callback_data=f"requests_page:{page+1}"
                    )
                )
            
            if pagination:
                keyboard.append(pagination)
            keyboard.append([
                InlineKeyboardButton("🔙 Back", callback_data="admin_panel"),
                InlineKeyboardButton("❌ Close", callback_data="close_message"),
                InlineKeyboardButton("🗑️ Delete All", callback_data="confirm_delete_all")
            ])
            
            message_text = (
                f"📝 *Anime Requests* (Page {page}/{total_pages})\n"
                f"🟢 Approved | 🟡 Pending | 🔴 Rejected\n"
                f"Total Requests: {total_requests}"
            )
            
            try:
                await callback_query.message.edit_text(
                    message_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
                await callback_query.answer()
            except Exception as e:
                logger.error(f"Error editing requests page: {e}")
                await callback_query.answer("Error loading requests", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in view_requests_page: {e}")
            await callback_query.answer("Error loading requests", show_alert=True)

    async def handle_request_callbacks(self, client: Client, callback_query: CallbackQuery):
        try:
            data = callback_query.data

            if data == "confirm_delete_all" or data == "cancel_delete_all":
                await self.handle_delete_confirmation(client, callback_query)
            elif data.startswith("req_page:"):
                page = int(data.split(":")[1])
                await self.view_requests_page(client, callback_query, page)
            elif data.startswith("request_detail:"):
                request_id = data.split(":")[1]
                await self.show_request_info(client, callback_query, request_id)
            elif data.startswith("requests_page:"):
                page = int(data.split(":")[1])
                await self.view_requests_page(client, callback_query, page)
            elif data.startswith("approve_req:"):
                request_id = data.split(":")[1]
                await self.handle_approval(client, callback_query, request_id)
            elif data.startswith("reject_req:"):
                request_id = data.split(":")[1]
                await self.handle_rejection(client, callback_query, request_id)
            elif data.startswith("mark_uploaded:"):
                request_id = data.split(":")[1]
                await self.mark_as_uploaded(client, callback_query, request_id)
            elif data.startswith("close_req:"):
                await callback_query.message.delete()
                await callback_query.answer("Closed")
            elif data == "close_notification":
                await callback_query.message.delete()
                await callback_query.answer()
            else:
                await callback_query.answer("⚠️ Action not available", show_alert=True)
                
        except Exception as e:
            logger.error(f"Callback error: {str(e)}")
            await callback_query.answer("❌ Error processing request", show_alert=True)

    async def show_request_info(self, client: Client, callback_query: CallbackQuery, request_id: str):
        try:
            req = await self.db.requests_collection.find_one({"request_id": request_id})
            if not req:
                await callback_query.answer("Request not found", show_alert=True)
                return
                
            user = await client.get_users(req['user_id'])
            processed_by = await client.get_users(req['processed_by']) if req.get('processed_by') else None
            
            message = (
                f"📝 *Request Details*\n\n"
                f"🆔 *ID:* `{req['request_id']}`\n"
                f"👤 *User:* {user.mention}\n"
                f"📅 *Submitted:* {req['timestamp'].strftime('%Y-%m-%d %H:%M')}\n"
                f"🎬 *Anime:* `{req.get('anime_name', 'Unknown')}`\n"
                f"📛 *Status:* `{req['status'].upper()}`\n"
            )
            
            if req['status'] != 'pending':
                message += (
                    f"👮 *Processed by:* {processed_by.mention if processed_by else 'N/A'}\n"
                    f"⏰ *Processed on:* {req['processed_date'].strftime('%Y-%m-%d %H:%M') if req.get('processed_date') else 'N/A'}\n"
                )
            
            if req.get('is_uploaded'):
                message += "\n✅ *This anime has been uploaded*\n"
            
            keyboard = []
            if req['status'] == 'pending':
                keyboard.extend([
                    [
                        InlineKeyboardButton("✅ Approve", callback_data=f"approve_req:{request_id}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"reject_req:{request_id}")
                    ]
                ])
            elif req['status'] == 'approved' and not req.get('is_uploaded'):
                keyboard.append([
                    InlineKeyboardButton("📤 Mark as Uploaded", callback_data=f"mark_uploaded:{request_id}")
                ])
            
            keyboard.append([
                InlineKeyboardButton("🔙 Back", callback_data="requests_page:1"),
                InlineKeyboardButton("❌ Close", callback_data="close_message")
            ])
            
            await callback_query.message.edit_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error showing request: {e}")
            await callback_query.answer("Error loading request", show_alert=True)

    async def mark_as_uploaded(self, client: Client, callback_query: CallbackQuery, request_id: str):
        """Mark a request as uploaded and notify the user"""
        try:
            # Update request status
            await self.db.requests_collection.update_one(
                {"request_id": request_id},
                {
                    "$set": {
                        "is_uploaded": True,
                        "is_notified": True,
                        "processed_by": callback_query.from_user.id,
                        "processed_date": datetime.now()
                    }
                }
            )
            
            # Get the request details
            req = await self.db.requests_collection.find_one({"request_id": request_id})
            if not req:
                await callback_query.answer("Request not found", show_alert=True)
                return
                
            # Notify the user who made the request
            try:
                user = await client.get_users(req['user_id'])
                await client.send_message(
                    user.id,
                    f"🎉 *Your requested anime has been uploaded!*\n\n"
                    f"📺 Anime: `{req.get('anime_name', 'Unknown')}`\n"
                    f"🆔 Request ID: `{request_id}`\n\n"
                    f"You can now search and watch it in the bot. Thank you for your patience!",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Error notifying user: {e}")

            # Update the requests list view
            await callback_query.answer("✅ Marked as uploaded", show_alert=True)
            await self.show_request_info(client, callback_query, request_id)
            
        except Exception as e:
            logger.error(f"Error marking as uploaded: {e}", exc_info=True)
            await callback_query.answer("❌ Error marking as uploaded", show_alert=True)

    async def handle_approval(self, client: Client, callback_query: CallbackQuery, request_id: str):
        """Handle approval of a request"""
        try:
            # Update request status to approved
            await self.db.requests_collection.update_one(
                {"request_id": request_id},
                {
                    "$set": {
                        "status": "approved",
                        "processed_by": callback_query.from_user.id,
                        "processed_date": datetime.now()
                    }
                }
            )
            
            # Get the request details
            req = await self.db.requests_collection.find_one({"request_id": request_id})
            if not req:
                await callback_query.answer("Request not found", show_alert=True)
                return
                
            # Notify the user who made the request
            try:
                user = await client.get_users(req['user_id'])
                await client.send_message(
                    user.id,
                    f"🎉 *Your request has been approved!*\n\n"
                    f"📺 Anime: `{req.get('anime_name', 'Unknown')}`\n"
                    f"🆔 Request ID: `{request_id}`\n\n"
                    f"Thank you for your patience! We'll notify you when it's available.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Error notifying user: {e}")

            # Update the requests list view
            await callback_query.answer("✅ Request approved", show_alert=True)
            await self.show_request_info(client, callback_query, request_id)
            
        except Exception as e:
            logger.error(f"Error approving request: {e}", exc_info=True)
            await callback_query.answer("❌ Error approving request", show_alert=True)

    async def handle_rejection(self, client: Client, callback_query: CallbackQuery, request_id: str):
        """Handle rejection of a request"""
        try:
            # Update request status to rejected
            await self.db.requests_collection.update_one(
                {"request_id": request_id},
                {
                    "$set": {
                        "status": "rejected",
                        "processed_by": callback_query.from_user.id,
                        "processed_date": datetime.now()
                    }
                }
            )
            
            # Get the request details
            req = await self.db.requests_collection.find_one({"request_id": request_id})
            if not req:
                await callback_query.answer("Request not found", show_alert=True)
                return
                
            # Notify the user who made the request
            try:
                user = await client.get_users(req['user_id'])
                await client.send_message(
                    user.id,
                    f"❌ *Your request has been rejected*\n\n"
                    f"📺 Anime: `{req.get('anime_name', 'Unknown')}`\n"
                    f"🆔 Request ID: `{request_id}`\n\n"
                    f"Please check our existing collection or request a different anime.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Error notifying user: {e}")

            # Update the requests list view
            await callback_query.answer("❌ Request rejected", show_alert=True)
            await self.show_request_info(client, callback_query, request_id)
            
        except Exception as e:
            logger.error(f"Error rejecting request: {e}", exc_info=True)
            await callback_query.answer("❌ Error rejecting request", show_alert=True)

    async def check_and_notify_available(self, client: Client):
        """Check if requested anime become available and notify users"""
        try:
            # Get all approved but not notified requests
            requests = await self.db.requests_collection.find({
                "status": "approved",
                "is_notified": False
            }).to_list(None)
            
            for req in requests:
                anime_name = req.get('anime_name')
                if not anime_name:
                    continue
                    
                # Search across all clusters
                anime_found = False
                for db_client in self.bot.db.anime_clients:
                    try:
                        db = db_client[self.bot.db.db_name]
                        if await db.anime.count_documents({"title": {"$regex": anime_name, "$options": "i"}}) > 0:
                            anime_found = True
                            break
                    except Exception as e:
                        logger.warning(f"Error checking anime in cluster: {e}")
                
                if anime_found:
                    try:
                        user = await client.get_users(req['user_id'])
                        await client.send_message(
                            user.id,
                            f"🎉 *Good news! Your requested anime is now available!*\n\n"
                            f"🎬 *{anime_name}*\n\n"
                            f"You can now search and watch it in the bot.\n"
                            f"Thank you for your patience!",
                            parse_mode=ParseMode.MARKDOWN
                        )
                        
                        # Mark as notified
                        await self.db.requests_collection.update_one(
                            {"request_id": req['request_id']},
                            {"$set": {"is_notified": True}}
                        )
                    except Exception as e:
                        logger.error(f"Error notifying user {req['user_id']}: {e}")
                        
        except Exception as e:
            logger.error(f"Error in check_and_notify_available: {e}")

    async def delete_all_requests(self, client: Client, message: Message):
        try:
            if message.from_user.id not in self.config.ADMINS:
                await message.reply_text("❌ Only admins can use this command")
                return

            confirm_keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Yes", callback_data="confirm_delete_all"),
                    InlineKeyboardButton("❌ No", callback_data="cancel_delete_all")
                ]
            ])
            
            await message.reply_text(
                "⚠️ Are you sure you want to delete ALL requests?",
                reply_markup=confirm_keyboard
            )
            
        except Exception as e:
            logger.error(f"Delete all error: {str(e)}")
            await message.reply_text("❌ Error processing command")

    async def handle_delete_confirmation(self, client: Client, callback_query: CallbackQuery):
        try:
            if callback_query.from_user.id not in self.config.ADMINS:
                await callback_query.answer("Only admins can do this")
                return

            if callback_query.data == "confirm_delete_all":
                result = await self.db.requests_collection.delete_many({})
                await callback_query.message.edit_text(
                    f"✅ Deleted {result.deleted_count} requests",
                    reply_markup=None
                )
            else:
                await callback_query.message.edit_text(
                    "❌ Deletion cancelled",
                    reply_markup=None
                )
                
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"Delete confirm error: {str(e)}")
            await callback_query.answer("Error processing deletion")

    async def notify_on_upload(self, anime_title: str):
        """Notify users when an anime is uploaded"""
        try:
            # Find all requests for this anime
            requests = await self.db.requests_collection.find({
                "anime_name": {"$regex": anime_title, "$options": "i"},
                "is_notified": False
            }).to_list(None)
            
            for req in requests:
                try:
                    await self.bot.send_message(
                        req['user_id'],
                        f"🎉 *Your requested anime is now available!*\n\n"
                        f"🎬 *{anime_title}*\n\n"
                        f"You can now search and watch it in the bot.\n"
                        f"Thank you for your patience!",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    # Mark as notified
                    await self.db.requests_collection.update_one(
                        {"request_id": req['request_id']},
                        {"$set": {"is_notified": True, "is_uploaded": True}}
                    )
                except Exception as e:
                    logger.error(f"Error notifying user {req['user_id']}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in notify_on_upload: {e}")
