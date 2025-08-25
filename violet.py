import os
import sys
import re
import uuid
import random
import time 
import html
import logging
import aiohttp
import asyncio
import json
import base64
import psutil
import signal
from aiohttp import web
from typing import Dict, List, Optional, Tuple , Union, Set
from collections import defaultdict
from datetime import datetime, timedelta
from pyrogram import Client as PyroClient
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import ClientSession, ClientTimeout
from pyrogram.enums import ParseMode
from aiohttp import web
from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    Message, 
    CallbackQuery,
    InputMediaPhoto,
    InlineQueryResultArticle,
    InputTextMessageContent
)
from broadcast import Broadcast
from premium import *
from request import RequestSystem
from pyrogram.handlers import MessageHandler  # Add this import
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid
from pyrogram import idle
from pyrogram import enums
from pyrogram.enums import ChatType , ParseMode
from dotenv import load_dotenv
from bson import ObjectId
from settings import config
from scripts import Scripts
from anime_quotes import AnimeQuotes
from force_sub import ForceSub



MAX_FREE_TIER_SPACE = 500 * 1024 * 1024  # 500 MB cap for MongoDB Atlas free tier

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)



# Database Configuration
class Database:
    def __init__(self):
        self.anime_uris = [
            os.getenv("PRIMARY_MONGO_URI"),
            os.getenv("SECONDARY_MONGO_URI"),
            os.getenv("TERTIARY_MONGO_URI"),
            os.getenv("FOURTH_MONGO_URI"),
            os.getenv("FIFTH_MONGO_URI"),
            os.getenv("SIXTH_MONGO_URI"),
            os.getenv("SEVENTH_MONG0_URI"),
            os.getenv("BACKUP_MONGO_URI")
        ]
        self.users_uri = os.getenv("USERS_MONGO_URI")
        self.db_name = os.getenv("DB_NAME", "AnimeFilterBot")
        
        self.anime_clients = []
        self.users_client = None
        self.users_db = None
        self.users_collection = None
        self.stats_collection = None
        self.watchlist_collection = None
        self.requests_collection = None  # Add this line
        self.premium_users = None  # Add this line
        self.current_insert_client = -1
        self.cluster_status = {}
        self.cluster_order = []  # Will store the order of clusters to use
        self.insert_stats = {
            'total_inserts': 0,
            'cluster_counts': {},
            'last_reset': datetime.now()
        }
       # Full One Piece saga data in clean format
        self.one_piece_sagas = {
            6284053604036871611: {  # One Piece anime ID
                "sagas": [
                    {
                        "id": 1,
                        "name": "East Blue Saga",
                        "year_range": "1999–2001",
                        "episode_range": "1–61",
                        "description": "The beginning of Luffy's journey to become Pirate King",
                        "arcs": [
                            {"id": 1, "name": "Romance Dawn", "episode_range": "1–3", "description": "Luffy begins his journey and recruits Zoro"},
                            {"id": 2, "name": "Orange Town", "episode_range": "4–8", "description": "Luffy and Zoro battle Buggy the Clown"},
                            {"id": 3, "name": "Syrup Village", "episode_range": "9–18", "description": "The crew meets Usopp and battles Kuro"},
                            {"id": 4, "name": "Baratie", "episode_range": "19–30", "description": "Luffy battles Don Krieg and recruits Sanji"},
                            {"id": 5, "name": "Arlong Park", "episode_range": "31–44", "description": "Nami's backstory and battle with Arlong"},
                            {"id": 6, "name": "Loguetown", "episode_range": "45–53", "description": "The crew visits Loguetown before heading to the Grand Line"},
                            {"id": 7, "name": "Warship Island (Filler)", "episode_range": "54–61", "description": "The crew helps Apis and a dragon escape the Marines"}
                        ]
                    },
                    {
                        "id": 2,
                        "name": "Alabasta Saga",
                        "year_range": "2001–2002",
                        "episode_range": "62–135",
                        "description": "The Straw Hats help Princess Vivi save her kingdom",
                        "arcs": [
                            {"id": 8, "name": "Reverse Mountain", "episode_range": "62–63", "description": "The crew enters the Grand Line"},
                            {"id": 9, "name": "Whisky Peak", "episode_range": "64–69", "description": "The crew battles Baroque Works agents"},
                            {"id": 10, "name": "Little Garden", "episode_range": "70–77", "description": "The crew encounters giants Dorry and Brogy"},
                            {"id": 11, "name": "Drum Island", "episode_range": "78–91", "description": "The crew recruits Chopper as their doctor"},
                            {"id": 12, "name": "Alabasta", "episode_range": "92–130", "description": "The crew battles Crocodile and Baroque Works to save Alabasta"},
                            {"id": 13, "name": "Post-Alabasta (Filler)", "episode_range": "131–135", "description": "Episodic adventures after Alabasta"}
                        ]
                    },
                    {
                        "id": 3,
                        "name": "Sky Island Saga",
                        "year_range": "2002–2004",
                        "episode_range": "136–206",
                        "description": "The Straw Hats travel to the sky and battle Enel",
                        "arcs": [
                            {"id": 14, "name": "Jaya", "episode_range": "136–152", "description": "The crew learns of Skypiea and encounters Blackbeard"},
                            {"id": 15, "name": "Skypiea", "episode_range": "153–195", "description": "The crew battles Enel and saves Skypiea"},
                            {"id": 16, "name": "G-8 (Filler)", "episode_range": "196–206", "description": "The crew infiltrates a Marine base to recover the Going Merry"}
                        ]
                    },
                    {
                        "id": 4,
                        "name": "Water 7 Saga",
                        "year_range": "2004–2007",
                        "episode_range": "207–325",
                        "description": "The crew faces CP9 and declares war on the World Government",
                        "arcs": [
                            {"id": 17, "name": "Long Ring Long Land", "episode_range": "207–226", "description": "The crew faces Foxy in the Davy Back Fight"},
                            {"id": 18, "name": "Water 7", "episode_range": "227–263", "description": "The crew is betrayed and Robin leaves"},
                            {"id": 19, "name": "Enies Lobby", "episode_range": "264–312", "description": "The crew fights CP9 to rescue Robin"},
                            {"id": 20, "name": "Post-Enies Lobby", "episode_range": "313–325", "description": "The crew gains new bounties and allies"}
                        ]
                    },
                    {
                        "id": 5,
                        "name": "Thriller Bark Saga",
                        "year_range": "2007–2009",
                        "episode_range": "326–384",
                        "description": "The crew battles Gecko Moria on Thriller Bark",
                        "arcs": [
                            {"id": 21, "name": "Thriller Bark", "episode_range": "326–384", "description": "The crew defeats Gecko Moria and Brook joins the crew"}
                        ]
                    },
                    {
                        "id": 6,
                        "name": "Summit War Saga",
                        "year_range": "2009–2011",
                        "episode_range": "385–516",
                        "description": "The crew is separated, and Luffy faces the greatest war in the seas",
                        "arcs": [
                            {"id": 22, "name": "Sabaody Archipelago", "episode_range": "385–405", "description": "The crew faces the Celestial Dragons and Pacifistas"},
                            {"id": 23, "name": "Amazon Lily", "episode_range": "406–417", "description": "Luffy meets Boa Hancock"},
                            {"id": 24, "name": "Impel Down", "episode_range": "418–452", "description": "Luffy infiltrates Impel Down to rescue Ace"},
                            {"id": 25, "name": "Marineford", "episode_range": "453–489", "description": "The great war between Whitebeard and the Marines"},
                            {"id": 26, "name": "Post-War", "episode_range": "490–516", "description": "Luffy mourns Ace and trains for two years"}
                        ]
                    },
                    {
                        "id": 7,
                        "name": "Fish-Man Island Saga",
                        "year_range": "2011–2012",
                        "episode_range": "517–574",
                        "description": "The crew reunites after two years and travels to Fish-Man Island",
                        "arcs": [
                            {"id": 27, "name": "Return to Sabaody", "episode_range": "517–522", "description": "The crew reunites after training"},
                            {"id": 28, "name": "Fish-Man Island", "episode_range": "523–574", "description": "The crew battles Hody Jones and saves Fish-Man Island"}
                        ]
                    },
                    {
                        "id": 8,
                        "name": "Dressrosa Saga",
                        "year_range": "2012–2016",
                        "episode_range": "575–746",
                        "description": "The crew challenges Doflamingo in Dressrosa",
                        "arcs": [
                            {"id": 29, "name": "Punk Hazard", "episode_range": "575–628", "description": "The crew allies with Law against Caesar Clown"},
                            {"id": 30, "name": "Dressrosa", "episode_range": "629–746", "description": "The crew defeats Doflamingo and liberates Dressrosa"}
                        ]
                    },
                    {
                        "id": 9,
                        "name": "Whole Cake Island Saga",
                        "year_range": "2016–2019",
                        "episode_range": "747–889",
                        "description": "The crew rescues Sanji from Big Mom's territory",
                        "arcs": [
                            {"id": 31, "name": "Zou", "episode_range": "747–779", "description": "The crew learns about Raftel and the Road Poneglyphs"},
                            {"id": 32, "name": "Whole Cake Island", "episode_range": "780–877", "description": "The crew battles Big Mom to rescue Sanji"},
                            {"id": 33, "name": "Levely", "episode_range": "878–889", "description": "The world's leaders gather to discuss global affairs"}
                        ]
                    },
                    {
                        "id": 10,
                        "name": "Wano Country Saga",
                        "year_range": "2019–2023",
                        "episode_range": "890–1085",
                        "description": "The Straw Hats lead the raid to free Wano from Kaido and Orochi",
                        "arcs": [
                            {"id": 34, "name": "Wano Country Act 1", "episode_range": "890–916", "description": "The crew arrives in Wano and begins forming alliances"},
                            {"id": 35, "name": "Wano Country Act 2", "episode_range": "917–958", "description": "Preparations for the Fire Festival and conflicts escalate"},
                            {"id": 36, "name": "Wano Country Act 3", "episode_range": "959–1085", "description": "The Raid on Onigashima and final battles against Kaido and Big Mom"}
                        ]
                    },
                    {
                        "id": 11,
                        "name": "Final Saga",
                        "year_range": "2023–Ongoing",
                        "episode_range": "1086–Present",
                        "description": "The Straw Hats explore Egghead and face new challenges",
                        "arcs": [
                            {"id": 37, "name": "Egghead", "episode_range": "1086–Present", "description": "Ongoing adventures on Egghead Island"}
                        ]
                    }
                ]
            }
        }

    async def initialize(self):
        """Initialize all database connections and collections"""
        try:
            # Initialize users database
            await self._initialize_users_db()
            
            # Initialize anime clusters
            await self._initialize_anime_clusters()
            self.cluster_order = list(range(len(self.anime_clients)))
            random.shuffle(self.cluster_order)
            self.current_insert_client = -1
            logger.info("Database initialization complete")
            await self.users_collection.update_many(
                {"access_level": {"$exists": False}},
                {"$set": {"access_level": 0}}  # Default to normal
            )

              # Run migrations
              
            # Run migrations
        #    await self.migrate_premium_users()
        
            # If premium mode is off, ensure all users have normal access
            if not Config.PREMIUM_MODE:
                await self.users_collection.update_many(
                    {},
                    {"$set": {"access_level": 0}}
                )
            
            # Create indexes
            await self._create_indexes()
            
            
            # Initialize statistics
           
            logger.info("Database initialization completed successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    async def _initialize_users_db(self):
        """Initialize the users database connection"""
        try:
            self.users_client = AsyncIOMotorClient(self.users_uri)
            await self.users_client.server_info()
            self.users_db = self.users_client[self.db_name]
            self.users_collection = self.users_db.users
            self.stats_collection = self.users_db.stats
            self.admins_collection = self.users_db.admins
            self.owners_collection = self.users_db.owners
            await self.admins_collection.create_index("user_id", unique=True)
            await self.owners_collection.create_index("user_id", unique=True)
            self.watchlist_collection = self.users_db.watchlists
            self.requests_collection = self.users_db.requests  # ✅ Add this
            self.premium_users = self.users_db.premium_users   # ✅ Add this
            await self._create_premium_indexes()
    
            logger.info(f"Connected to Users MongoDB at {self.users_uri[:30]}...")
        except Exception as e:
            logger.error(f"Failed to connect to Users MongoDB: {e}")
            raise

    async def _initialize_anime_clusters(self):
        """Connect to all MongoDB anime clusters"""
        self.anime_clients = []
        self.cluster_status = {}

        for i, uri in enumerate(self.anime_uris):
            if not uri:
                logger.warning(f"Cluster {i} skipped - URI not provided")
                continue

            try:
                client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=20000)  # 15 seconds
                await client.admin.command("ping")
                self.anime_clients.append(client)
                self.cluster_status[i] = {
                    "status": "online",
                    "last_checked": datetime.now()
                }
                logger.info(f"Cluster {i} connected successfully")
            except Exception as e:
                self.cluster_status[i] = {
                    "status": "offline",
                    "error": str(e)[:200],
                    "last_checked": datetime.now()
                }
                logger.error(f"Failed to connect to cluster {i}: {e}")

    async def _create_premium_indexes(self):
        await self.premium_users.create_index([("user_id", 1)], unique=True)
        await self.premium_users.create_index([("expiry_date", 1)])

    async def _create_indexes(self):
        """Create necessary indexes for all collections"""
        try:
            # Users collection indexes
            await self.users_collection.create_index([("user_id", 1)], unique=True)
            await self.watchlist_collection.create_index([("user_id", 1), ("anime_id", 1)], unique=True)
            await self.requests_collection.create_index([("user_id", 1)])
            await self.premium_users.create_index([("user_id", 1)], unique=True)
            await self.users_collection.create_index([("user_id", 1)], unique=True)
            await self.users_collection.create_index([("last_download_date", 1)])
            await self.users_collection.create_index([("download_count", 1)])
            await self.premium_users.create_index("access_level")
            # In your database initialization
            await self.premium_users.create_index([("user_id", 1)], unique=True)
            await self.premium_users.create_index([("access_level", 1)])
            await self.premium_users.update_many(
                {"access_level": {"$nin": ["normal", "premium", "hpremium"]}},
                {"$set": {"access_level": "premium"}}
            )
            # Anime collection indexes (on all clusters)
            for i, client in enumerate(self.anime_clients):
                try:
                    db = client[self.db_name]
                    await db.anime.create_index([("title", "text")])
                    await db.anime.create_index([("id", 1)], unique=True)
                    await db.anime.create_index([("sequel_id", 1)])
                    await db.requests.create_index([("user_id", 1)])
                    await db.requests.create_index([("is_notified", 1)])
                    await db.requests.create_index([("anime_name", "text")])
                    await db.requests.create_index([("status", 1)])
                    await self.requests_collection.create_index("request_id", unique=True)   
                    await db.requests.create_index([("timestamp", -1)])
                    await db.anime.create_index([("prequel_id", 1)])
                    await db.anime.create_index([("last_updated", -1)])
                    await db.files.create_index([("anime_id", 1), ("episode", 1)])
                    logger.info(f"Created indexes for cluster {i}")
                except Exception as e:
                    logger.error(f"Failed to create indexes for cluster {i}: {e}")
            
            logger.info("All indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            raise
    async def _initialize_stats(self):
        """Initialize statistics collection"""
        try:
            if not await self.stats_collection.find_one({"type": "global"}):
                await self.stats_collection.insert_one({
                "type": "global",
                "stats": {
                    "total_anime": 0,
                    "total_files": 0,
                    "total_users": 0,
                    "total_downloads": 0,
                    "total_searches": 0
                },
                "settings": {
                    "delete_timer": 1,
                    "max_results": 10,
                    "max_episodes": 30,
                    "pm_search": True,
                    "protect_content": False,
                    "rate_limit": 5
                },
                "created_at": datetime.now()
                
            })
            stats = await self.stats_collection.find_one({"type": "global"})
            if stats and 'settings' in stats:
                settings = stats['settings']
                Config.PREMIUM_MODE = settings.get('premium_mode', False)
                Config.RESTRICT_ADULT = settings.get('restrict_adult', True)
                Config.MAX_DAILY_DOWNLOADS = {
                    0: settings.get('download_limits', {}).get('normal', 24),
                    1: settings.get('download_limits', {}).get('premium', -1),
                    2: settings.get('download_limits', {}).get('hpremium', -1)
                }
            logger.info("Initialized statistics with default settings")
        except Exception as e:
            logger.error(f"Error initializing stats: {e}")
            raise

    async def get_insert_cluster(self) -> AsyncIOMotorClient:
        """Round-robin cluster selection for inserts with health check"""
        if not self.anime_clients:
            raise Exception("No MongoDB clusters available")

        max_attempts = len(self.anime_clients)
        attempts = 0

        while attempts < max_attempts:
            attempts += 1
            self.current_insert_client = (self.current_insert_client + 1) % len(self.anime_clients)
            cluster_idx = self.cluster_order[self.current_insert_client]

            try:
                client = self.anime_clients[cluster_idx]
                await client.admin.command("ping")

                # Update metrics
                self.insert_stats['total_inserts'] += 1
                self.insert_stats['cluster_counts'][cluster_idx] = \
                    self.insert_stats['cluster_counts'].get(cluster_idx, 0) + 1

                # Rotate clusters every 100 inserts
                if self.insert_stats['total_inserts'] % 100 == 0:
                    random.shuffle(self.cluster_order)

                # Reset stats daily
                if (datetime.now() - self.insert_stats['last_reset']).days >= 1:
                    self.insert_stats = {
                        'total_inserts': 0,
                        'cluster_counts': {},
                        'last_reset': datetime.now()
                    }

                return client

            except Exception as e:
                logger.warning(f"Cluster {cluster_idx} unavailable: {e}")
                continue

        raise Exception("No available MongoDB clusters for inserts")

    async def insert_anime(self, anime_data):
        """Insert or update anime document using round-robin"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                client = await self.get_insert_cluster()
                db = client[self.db_name]

                # Check for existing anime across all clusters
                existing = await self.find_anime(anime_data["id"])
                if existing:
                    logger.info(f"Anime {anime_data['id']} exists — updating")
                    updated = False
                    for c in self.anime_clients:
                        try:
                            db = c[self.db_name]
                            result = await db.anime.update_one(
                                {"id": anime_data["id"]},
                                {"$set": anime_data}
                            )
                            if result.modified_count > 0:
                                updated = True
                        except Exception:
                            continue
                    return updated

                await db.anime.insert_one(anime_data)
                logger.info(f"Inserted anime into cluster {self.current_insert_client}")
                return True

            except Exception as e:
                logger.error(f"Insert attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(1)

        return False
    # In your Database class, fix the check_duplicate_file method:
    async def check_duplicate_file(self, file_data):
        """Check for duplicate files across all clusters"""
        query = {
            "anime_id": file_data["anime_id"],
            "episode": file_data["episode"],
            "quality": file_data.get("quality", "").lower()
        }
        
        # Only add language if it exists in file_data
        if "language" in file_data and file_data["language"]:
            query["language"] = file_data["language"].lower()
        
        logger.info(f"Checking for duplicates with query: {query}")
        
        for i, client in enumerate(self.anime_clients):
            try:
                db = client[self.db_name]
                count = await db.files.count_documents(query)
                if count > 0:
                    logger.info(f"Duplicate found in cluster {i} for episode {file_data['episode']}")
                    # Log what files already exist
                    existing_files = await db.files.find(query).to_list(3)  # Get first 3 matches
                    for f in existing_files:
                        logger.info(f"Existing file: {f.get('file_name', 'Unknown')}")
                    return True
            except Exception as e:
                logger.warning(f"Error checking duplicates in cluster {i}: {str(e)[:200]}")
        
        return False

    async def insert_file(self, file_data):
        """Insert file into anime's cluster or fallback via round-robin"""
        # First check for duplicates globally
        if await self.check_duplicate_file(file_data):
            logger.info("Duplicate file detected, skipping insertion")
            # DEBUG: See what's causing the duplicate detection
            await self.debug_duplicate_check(file_data)
            return False
    # FIX: Call categorize_episode correctly
        file_data = await self.categorize_episode(file_data["anime_id"], file_data["episode"], file_data)
        for i, client in enumerate(self.anime_clients):
            try:
                if not hasattr(client, '__getitem__'):
                    logger.error(f"Cluster {i} client is not subscriptable")
                    continue

                db = client[self.db_name]

                # Check if anime exists in this cluster
                anime_exists = await db.anime.count_documents({"id": file_data["anime_id"]}) > 0

                if anime_exists:
                    await db.files.insert_one(file_data)
                    logger.info(f"Inserted file into existing anime cluster {i}")

                    return True
            except Exception as e:
                logger.warning(f"Cluster {i} operation failed: {str(e)[:200]}")
                continue

        # Anime not found in any cluster - insert new anime first
        # Anime not found in any cluster - insert new anime first
        anime_data = {
            "id": file_data["anime_id"],
            "title": file_data["anime_title"],
            "type": file_data.get("type", "TV"),
            "episodes": file_data.get("episodes", 1),
            "last_updated": datetime.now()
        }

        # Special handling for One Piece
        if file_data["anime_id"] == 6284053604036871611:
            anime_data["episodes"] = None
            anime_data["episodes_display"] = "Ongoing"
            anime_data["status"] = "RELEASING"
            anime_data["is_ongoing"] = True

        if await self.insert_anime(anime_data):
            # Retry file insertion after anime is inserted
            return await self.insert_file(file_data)

        return False

    async def update_anime(self, anime_id, update_data):
        """Update anime across all clusters"""
        updated = False
        for client in self.anime_clients:  # Use consistent naming
            try:
                db = client[self.db_name]  # Use the same variable name
                result = await db.anime.update_one(
                    {"id": anime_id},
                    {"$set": update_data}
                )
                if result.modified_count > 0:
                    updated = True
            except Exception as e:
                logger.warning(f"Cluster update failed: {e}")
        return updated
    async def find_anime(self, anime_id):
        """Search for an anime by ID across all clusters"""
        for i, db_client in enumerate(self.anime_clients):  # Use db_client
            try:
                db = db_client[self.db_name]  # Correct - using database client
                anime = await db.anime.find_one({"id": anime_id})
                if anime:
                    return anime
            except Exception as e:
                logger.warning(f"Cluster {i} search failed: {e}")
        return None

    async def search_anime(self, query, limit=10):
        """Parallel search across all clusters with text and regex fallback"""
        results = []

        async def search_single_cluster(client):
            try:
                db = client[self.db_name]
                # 1. Try full-text search
                cursor = db.anime.find(
                    {"$text": {"$search": query}},
                    {"score": {"$meta": "textScore"}}
                ).sort([("score", {"$meta": "textScore"})]).limit(limit)

                cluster_results = await cursor.to_list(None)

                # 2. Fallback: regex if text search fails
                if not cluster_results:
                    cursor = db.anime.find(
                        {"title": {"$regex": query, "$options": "i"}}
                    ).limit(limit)
                    cluster_results = await cursor.to_list(None)

                return cluster_results

            except Exception as e:
                logger.warning(f"Search error in cluster (type={type(client)}): {e}")
                return []

        # Launch search in all clusters in parallel
        tasks = [search_single_cluster(client) for client in self.anime_clients]
        cluster_results = await asyncio.gather(*tasks)

        # Merge, deduplicate, and respect result limit
        seen_ids = set()
        for cluster in cluster_results:
            for anime in cluster:
                if anime["id"] not in seen_ids:
                    seen_ids.add(anime["id"])
                    results.append(anime)
                    if len(results) >= limit:
                        return results[:limit]

        return results[:limit]

    # In Database class
    async def add_premium_user(self, user_id: int, plan_type: str, duration_days: int):
        """Properly add or update premium user with validation"""
        try:
            if plan_type not in ['premium', 'hpremium']:
                raise ValueError(f"Invalid plan type: {plan_type}")
            
            expiry_date = datetime.now() + timedelta(days=duration_days)
            
            result = await self.premium_users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "plan_type": plan_type,
                    "access_level": plan_type,  # Make sure access_level matches
                    "expiry_date": expiry_date,
                    "granted_at": datetime.now(),
                    "granted_by": "system"  # Or actual admin ID
                }},
                upsert=True
            )
            
            # Verify the update was successful
            if not result.acknowledged:
                raise Exception("Database operation not acknowledged")
                
            # Clear any cache for this user
            if hasattr(self, 'premium_cache') and user_id in self.premium_cache:
                del self.premium_cache[user_id]
                
            return True
            
        except Exception as e:
            logger.error(f"Error adding premium user {user_id}: {e}")
            return False
    async def get_premium_user(self, user_id: int):
        """Get premium user info"""
        return await self.premium_users.find_one({"user_id": user_id})

    async def remove_premium_user(self, user_id: int):
        """Remove premium access"""
        await self.premium_users.delete_one({"user_id": user_id})

    async def get_all_premium_users(self, filter_type="active"):
        """Get properly formatted list of premium users with accurate counts"""
        query = {}
        
        if filter_type == "active":
            query = {"expiry_date": {"$gt": datetime.now()}}
        elif filter_type == "expired":
            query = {"expiry_date": {"$lte": datetime.now()}}
        elif filter_type == "all":
            query = {}
        
        try:
            users = await self.premium_users.find(query).sort("expiry_date", 1).to_list(None)
            
            # Fix any documents missing required fields
            valid_users = []
            for user in users:
                # Ensure document has all required fields
                if not all(key in user for key in ['user_id', 'plan_type', 'expiry_date']):
                    continue
                    
                valid_users.append({
                    'user_id': user['user_id'],
                    'plan_type': user.get('plan_type', 'premium'),
                    'access_level': user.get('access_level', user.get('plan_type', 'premium')),
                    'expiry_date': user['expiry_date'],
                    'granted_at': user.get('granted_at', datetime.now())
                })
            
            return valid_users
            
        except Exception as e:
            logger.error(f"Error getting premium users: {e}")
            return []
    async def find_files(self, anime_id: int, episode: int = None):
        """Enhanced file search with better error handling"""
        results = []
        query = {"anime_id": anime_id}
        if episode is not None:
            query["episode"] = episode
            
        for i, client in enumerate(self.anime_clients):
            try:
                db = client[self.db_name]
                # Sort by quality (assuming quality is stored as 360p, 480p, 720p, 1080p etc.)
                cursor = db.files.find(query).sort("quality", -1)
                cluster_files = await cursor.to_list(None)
                
                # Add cluster info to each file for debugging
                for file in cluster_files:
                    if not isinstance(file, dict):  # Skip non-dict entries
                        continue
                    file['cluster_source'] = i
                    file.setdefault('quality', '')  # Ensure quality field exists
                results.extend(cluster_files)
            except Exception as e:
                logger.warning(f"Find files error in cluster {i}: {e}")
        
        # Sort all results by quality (best quality first)
        return sorted(
            [f for f in results if isinstance(f, dict)],  # Filter out non-dict entries
            key=lambda x: self._parse_quality(x.get('quality', '')),
            reverse=True
        )
    async def count_episodes(self, anime_id: int, count_unique=True):
            """
            Count episodes across all clusters
            :param anime_id: Anime ID to count episodes for
            :param count_unique: If True, counts unique episodes (ignores quality)
                                If False, counts all files (including different qualities)
            """
            if count_unique:
                # Count distinct episodes
                pipeline = [
                    {"$match": {"anime_id": anime_id}},
                    {"$group": {"_id": "$episode"}},
                    {"$count": "unique_episodes"}
                ]
            else:
                # Count all files
                pipeline = [
                    {"$match": {"anime_id": anime_id}},
                    {"$count": "total_files"}
                ]

            total = 0
            for client in self.anime_clients:
                try:
                    db = client.get_database(self.db_name)  # Correct access method
                    result = await db.files.aggregate(pipeline).to_list(1)
                    if result and result[0].get('unique_episodes' if count_unique else 'total_files'):
                        total += result[0]['unique_episodes' if count_unique else 'total_files']
                except Exception as e:
                    logger.warning(f"Error counting episodes in cluster: {e}")
            return total

   

    def _parse_quality(self, quality_str):
        """Helper to parse quality strings for sorting (360p -> 360, 720p -> 720 etc.)
        Returns:
            int: parsed quality (0 if parsing fails)
        """
        if not quality_str or not isinstance(quality_str, str):
            return 0
        
        try:
            # Extract first sequence of digits and convert to int
            digits = ''.join(c for c in quality_str if c.isdigit())
            return int(digits) if digits else 0
        except (ValueError, TypeError):
            return 0
    async def update_stats(self, stat_type: str, increment: int = 1):
        """Update statistics in the users database"""
        try:
            await self.stats_collection.update_one(
                {"type": "global"},
                {"$inc": {stat_type: increment}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error updating stats: {e}")

    async def add_to_watchlist(self, user_id: int, anime_id: int):
        """Add anime to user's watchlist"""
        try:
            anime = await self.find_anime(anime_id)
            if not anime:
                return False
            
            await self.watchlist_collection.update_one(
                {"user_id": user_id, "anime_id": anime_id},
                {"$set": {
                    "title": anime["title"],
                    "added_at": datetime.now()
                }},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error adding to watchlist: {e}")
            return False
    async def load_admins_and_owners(self):
        """Load admins and owners from database"""
        Config.ADMINS = [1047253913]
        Config.OWNERS = [1047253913]
        
            # Load owners first
        async for owner in self.owners_collection.find():
            Config.OWNERS.append(owner['user_id'])
        
        # Then load admins (including owners)
        async for admin in self.admins_collection.find():
            if admin['user_id'] not in Config.ADMINS:
                Config.ADMINS.append(admin['user_id'])
        
        # Ensure owners are admins too
        Config.ADMINS = list(set(Config.ADMINS + Config.OWNERS))
        
        # Update environment variables
        os.environ["ADMINS"] = ",".join(map(str, Config.ADMINS))
        os.environ["OWNERS"] = ",".join(map(str, Config.OWNERS))
        
    async def remove_from_watchlist(self, user_id: int, anime_id: int):
        """Remove anime from user's watchlist"""
        try:
            result = await self.watchlist_collection.delete_one(
                {"user_id": user_id, "anime_id": anime_id}
            )
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error removing from watchlist: {e}")
            return False

    async def get_watchlist(self, user_id: int, limit: int = 50):
        """Get user's watchlist"""
        try:
            watchlist = await self.watchlist_collection.find(
                {"user_id": user_id},
                {"anime_id": 1, "title": 1}
            ).sort("added_at", -1).limit(limit).to_list(None)
            return watchlist
        except Exception as e:
            logger.error(f"Error getting watchlist: {e}")
            return []

    async def is_in_watchlist(self, user_id: int, anime_id: int):
        """Check if anime is in user's watchlist"""
        try:
            return await self.watchlist_collection.count_documents(
                {"user_id": user_id, "anime_id": anime_id}
            ) > 0
        except Exception as e:
            logger.error(f"Error checking watchlist: {e}")
            return False
    async def migrate_requests(self):
        """Fix any requests missing required fields"""
        async for req in self.requests_collection.find({"request_id": {"$exists": False}}):
            await self.requests_collection.update_one(
                {"_id": req["_id"]},
                {"$set": {"request_id": str(uuid.uuid4())}}
            )
    async def add_database_channel(self, channel_id: int):
        """Add a database channel to the settings"""
        try:
            await self.stats_collection.update_one(
                {"type": "global"},
                {"$addToSet": {"settings.database_channels": channel_id}}
            )
            return True
        except Exception as e:
            logger.error(f"Error adding database channel: {e}")
            return False

    async def remove_database_channel(self, channel_id: int):
        """Remove a database channel from the settings"""
        try:
            await self.stats_collection.update_one(
                {"type": "global"},
                {"$pull": {"settings.database_channels": channel_id}}
            )
            return True
        except Exception as e:
            logger.error(f"Error removing database channel: {e}")
            return False

    async def get_database_channels(self):
        """Get list of database channels"""
        try:
            stats = await self.stats_collection.find_one({"type": "global"})
            return stats.get("settings", {}).get("database_channels", [])
        except Exception as e:
            logger.error(f"Error getting database channels: {e}")
            return []
    # In Database class
    async def delete_episode(self, anime_id: int, episode: int = None, quality: str = None):
        """Delete specific episode(s) from database"""
        try:
            query = {"anime_id": anime_id}
            if episode is not None:
                query["episode"] = episode
            if quality is not None:
                query["quality"] = quality.lower()
            
            deleted_count = 0
            # Delete from all clusters
            for client in self.anime_clients:
                try:
                    db = client[self.db_name]
                    result = await db.files.delete_many(query)
                    deleted_count += result.deleted_count
                except Exception as e:
                    logger.error(f"Error deleting from cluster: {e}")
                    continue
            
            # Update anime episode count if needed
            if episode and deleted_count > 0:
                for client in self.anime_clients:
                    try:
                        db = client[self.db_name]
                        # Get current max episode
                        max_ep = await db.files.find(
                            {"anime_id": anime_id},
                            {"episode": 1}
                        ).sort("episode", -1).limit(1).to_list(1)
                        
                        new_max = max_ep[0]["episode"] if max_ep else 0
                        await db.anime.update_one(
                            {"id": anime_id},
                            {"$set": {"episodes": new_max}}
                        )
                    except Exception:
                        continue
            
            return deleted_count
        except Exception as e:
            logger.error(f"Error deleting episodes: {e}")
            return 0
    async def unlink_sequel(self, anime_id: int):
        """Remove sequel/prequel links for an anime"""
        try:
            # Update across all clusters
            for client in self.anime_clients:
                try:
                    db = client[self.db_name]
                    # Remove sequel link from prequel
                    await db.anime.update_many(
                        {"sequel_id": anime_id},
                        {"$set": {"sequel_id": None}}
                    )
                    # Remove prequel link from sequel
                    await db.anime.update_many(
                        {"prequel_id": anime_id},
                        {"$set": {"prequel_id": None, "is_sequel": False}}
                    )
                except Exception as e:
                    logger.warning(f"Error updating in cluster: {e}")
            return True
        except Exception as e:
            logger.error(f"Error unlinking sequels: {e}")
            return False
    async def reset_database(self):
        """Reset all databases (admin only)"""
        try:
            # Clear anime collections across all clusters
            for client in self.anime_clients:
                db = client[self.db_name]
                await db.anime.drop()
                await db.files.drop()
            
            # Clear users collections (except admins)
            await self.users_collection.delete_many({"user_id": {"$nin": Config.ADMINS}})
            await self.watchlist_collection.drop()
            await self.stats_collection.drop()
            
            # Reinitialize
            await self._create_indexes()
            await self._initialize_stats()
            return True
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            return False
    # Add to Database class
    async def get_anime_sagas(self, anime_id: int):
        """Get saga information for a specific anime"""
        return self.one_piece_sagas.get(anime_id, {}).get("sagas", [])

    async def get_saga_arcs(self, anime_id: int, saga_id: int):
        """Get arcs for a specific saga"""
        sagas = self.one_piece_sagas.get(anime_id, {}).get("sagas", [])
        for saga in sagas:
            if saga["id"] == saga_id:
                return saga.get("arcs", [])
        return []

    async def get_arc_episodes(self, anime_id: int, saga_id: int, arc_id: int):
        """Get episode range for a specific arc"""
        arcs = await self.get_saga_arcs(anime_id, saga_id)
        for arc in arcs:
            if arc["id"] == arc_id:
                return arc["episode_range"]
        return "1-1"  # Default if not found

    async def get_current_arc(self, anime_id: int):
        """Get the current arc for ongoing anime"""
        # This would need to be updated as new episodes are added
        return {
            "saga_id": 10,  # Final Saga
            "arc_id": 1,    # Egghead Arc
            "arc_name": "Egghead",
            "episode_range": "1086-Present"
        }
   # Add this to your Database class, not AnimeBot class
    # In your Database class
    async def categorize_episode(self, anime_id: int, episode: int, file_data: dict):
        """Automatically categorize episodes into arcs and sagas for One Piece"""
        if anime_id != 6284053604036871611:  # Only for One Piece
            return file_data
        
        sagas = self.one_piece_sagas.get(anime_id, {}).get("sagas", [])
        for saga in sagas:
            for arc in saga.get("arcs", []):
                if "episode_range" in arc:
                    try:
                        # Handle different range formats: "1–10", "1-10", "1 to 10"
                        if "–" in arc["episode_range"]:
                            start_ep, end_ep = map(int, arc["episode_range"].split("–"))
                        elif "-" in arc["episode_range"]:
                            start_ep, end_ep = map(int, arc["episode_range"].split("-"))
                        elif " to " in arc["episode_range"]:
                            start_ep, end_ep = map(int, arc["episode_range"].split(" to "))
                        else:
                            continue
                            
                        if start_ep <= episode <= end_ep:
                            file_data["saga_id"] = saga["id"]
                            file_data["saga_name"] = saga["name"]
                            file_data["arc_id"] = arc["id"]
                            file_data["arc_name"] = arc["name"]
                            logger.info(f"Categorized episode {episode} as {saga['name']} - {arc['name']}")
                            break
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Error parsing episode range {arc['episode_range']}: {e}")
                        continue
        
        return file_data

    async def debug_duplicate_check(self, file_data):
        """Debug method to see what's causing duplicate detection"""
        logger.info(f"Checking for duplicates with: {file_data}")
        
        for i, client in enumerate(self.anime_clients):
            try:
                db = client[self.db_name]
                query = {
                    "anime_id": file_data["anime_id"],
                    "episode": file_data["episode"],
                    "quality": file_data["quality"].lower() if "quality" in file_data else ""
                }
                
                if "language" in file_data and file_data["language"]:
                    query["language"] = file_data["language"].lower()
                    
                logger.info(f"Cluster {i} query: {query}")
                
                # Check what documents actually exist
                existing_files = await db.files.find(query).to_list(None)
                if existing_files:
                    logger.info(f"Found {len(existing_files)} existing files in cluster {i}:")
                    for f in existing_files:
                        logger.info(f"  - {f.get('file_name', 'Unknown')}")
                        
            except Exception as e:
                logger.error(f"Debug error in cluster {i}: {e}")
# Bot Configuration
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set")
    
    API_ID = os.getenv("API_ID")
    if not API_ID:
        raise ValueError("API_ID environment variable is not set")
    
    API_HASH = os.getenv("API_HASH")
    if not API_HASH:
        raise ValueError("API_HASH environment variable is not set")
    
    ADMINS = list(map(int, os.getenv("ADMINS", "").split(","))) if os.getenv("ADMINS") else []
    DATABASE_CHANNEL_ID = int(os.getenv("DATABASE_CHANNEL_ID", -1002448203068))
    GROUP_ID = int(os.getenv("GROUP_ID")) if os.getenv("GROUP_ID") else None
    GROUP_LINK = os.getenv("GROUP_LINK", "https://t.me/TFIBOTS_SUPPORT")
    DELETE_TIMER_MINUTES = int(os.getenv("DELETE_TIMER_MINUTES", 1))
    BOT_NAME = os.getenv("BOT_NAME", "Anime Downloader Bot")
    MAX_EPISODES_PER_PAGE = 30
    EPISODES_PER_PAGE = 50  # you can tune this to 50/100 safely delete episodes 
    MAX_SEARCH_RESULTS = 30
    DEVELOPER_USERNAME = "https://t.me/sun_godnika_bot"
    MAX_BATCH_FILES = 100
    PM_SEARCH = os.getenv("PM_SEARCH", "True") == "True"
    PROTECT_CONTENT = os.getenv("PROTECT_CONTENT", "False") == "True"
    START_PIC = os.getenv("START_PIC", "https://i.ibb.co/pB8SMVfz/x.png")
    COVER_PIC = os.getenv("COVER_PIC", "https://files.catbox.moe/roj8a1.jpg")
    ANILIST_API = "https://graphql.anilist.co"
    RATE_LIMIT = 8  # Messages per second
    REQUEST_TIMEOUT = 10  # Seconds
    MAX_WATCHLIST_ITEMS = 100
    PREMIUM_MODE = os.getenv("PREMIUM_MODE", "False") == "True"
    RESTRICT_ADULT = os.getenv("RESTRICT_ADULT", "True") == "True"
    OWNERS = list(map(int, os.getenv("OWNERS", "").split(","))) if os.getenv("OWNERS") else []
    ACCESS_LEVELS = {
        'normal': 0,    # Free tier with limitations
        'premium': 1,   # Unlimited downloads + higher quality
        'hpremium': 2   # All premium features + adult content
    }
    
    # Daily download limits
    MAX_DAILY_DOWNLOADS = {
        0: 24,   # Normal users: 3 downloads/day
        1: -1,  # Premium: unlimited (-1)
        2: -1   # H-Premium: unlimited
    }

    ANIME_TYPES = {
        'TV': {'name': 'TV Series', 'has_episodes': True, 'default_episodes': 12},
        'MOVIE': {'name': 'Movie', 'has_episodes': False, 'default_episodes': 1},
        'OVA': {'name': 'OVA', 'has_episodes': 'optional', 'default_episodes': 1},
        'ONA': {'name': 'ONA', 'has_episodes': 'optional', 'default_episodes': 1},
        'SPECIAL': {'name': 'Special', 'has_episodes': 'optional', 'default_episodes': 1},
        'MUSIC': {'name': 'Music', 'has_episodes': False, 'default_episodes': 1},
        'ADULT': {'name': 'Adult', 'has_episodes': True, 'default_episodes': 1},
        'HENTAI': {'name': 'Hentai', 'has_episodes': True, 'default_episodes': 1},
        'ANIME': {'name': 'Anime', 'has_episodes': True, 'default_episodes': 12}  # Added generic ANIME type
    }
    @property
    def MULTI_EPISODE_TYPES(self):
        return [k for k, v in self.ANIME_TYPES.items() if v['has_episodes'] is True]

    @property
    def SINGLE_EPISODE_TYPES(self):
        return [k for k, v in self.ANIME_TYPES.items() if v['has_episodes'] is False]

    @property
    def OPTIONAL_EPISODE_TYPES(self):
        return [k for k, v in self.ANIME_TYPES.items() if v['has_episodes'] == 'optional']
    
    ADULT_CONTENT_TYPES = ['ADULT', 'HENTAI']

async def encode(string: str) -> str:
    string_bytes = string.encode("utf-8")  # ✅ utf-8 supports all chars
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    return base64_bytes.decode("utf-8")

async def decode(base64_string: str) -> str:
    base64_bytes = base64_string.encode("utf-8")
    string_bytes = base64.urlsafe_b64decode(base64_bytes)
    return string_bytes.decode("utf-8")
# Add this class definition near your other class definitions
# Add these imports at the top of your file
# Add this class definition near your other class definitions
class NotificationManager:
    def __init__(self, bot_instance):
        self.bot_instance = bot_instance  # Reference to the main bot instance
        self.pending_notifications = defaultdict(lambda: defaultdict(set))  # anime_id -> episode -> set(user_ids)
        self.notification_lock = asyncio.Lock()
        self.processing_task = None
        
    async def start(self):
        """Start the notification processing task"""
        self.processing_task = asyncio.create_task(self.process_notifications_periodically())
        
    async def stop(self):
        """Stop the notification processing task"""
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
    
    async def add_notification(self, anime_id: int, episode: int, user_id: int):
        """Add a user to be notified about a new episode"""
        async with self.notification_lock:
            self.pending_notifications[anime_id][episode].add(user_id)
    
    async def process_notifications_periodically(self):
        """Periodically process notifications with a cooldown"""
        while True:
            await asyncio.sleep(60)  # Process every minute
            await self.process_notifications()
    
    async def process_notifications(self):
        """Process all pending notifications"""
        if not self.pending_notifications:
            return
            
        async with self.notification_lock:
            # Create a copy and clear the notifications
            notifications_to_send = dict(self.pending_notifications)
            self.pending_notifications.clear()
        
        # Process notifications for each anime and episode
        for anime_id, episodes in notifications_to_send.items():
            for episode, user_ids in episodes.items():
                if user_ids:  # Only process if there are users to notify
                    await self.send_bulk_notification(anime_id, episode, user_ids)
    
    async def send_bulk_notification(self, anime_id: int, episode: int, user_ids: Set[int]):
        """Send a notification to multiple users about a new episode"""
        try:
            # Get anime details
            anime = await self.bot_instance.db.find_anime(anime_id)
            if not anime:
                return
                
            # Get available qualities for this episode
            files = await self.bot_instance.db.find_files(anime_id, episode)
            qualities = set()
            for file in files:
                if 'quality' in file:
                    qualities.add(file['quality'].upper())
            
            # Prepare the notification message
            quality_text = f" [{', '.join(sorted(qualities))}]" if qualities else ""
            
            message = (
                "<blockquote>\n"
                "📢 <b>New Episode Available!</b>\n"
                "</blockquote>\n"
                "<blockquote>\n"
                f"🎬 <b>{anime.get('title', 'Unknown Anime')}</b>\n"
                f"📺 <b>Episode {episode}</b>{quality_text}\n"
                "</blockquote>\n"
                "✨ Use <code>/watchlist</code> to view your saved anime\n"
                f"🔍 Or search <code>{anime.get('title', '')}</code> to watch now!"
            )

            
            # Send notifications with HTML parse mode
            semaphore = asyncio.Semaphore(8)
            
            async def send_single_notification(user_id):
                async with semaphore:
                    try:
                        await self.bot_instance.app.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode=enums.ParseMode.HTML
                        )

                        # Small delay to avoid flooding
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        if "blocked" not in str(e).lower() and "deactivated" not in str(e).lower():
                            logger.warning(f"Failed to send notification to {user_id}: {e}")
            
            # Create all tasks
            tasks = [send_single_notification(user_id) for user_id in user_ids]
            
            # Wait for all tasks to complete with a timeout
            await asyncio.gather(*tasks, return_exceptions=True)
            
            logger.info(f"Sent episode {episode} notifications for {anime['title']} to {len(user_ids)} users")
            
        except Exception as e:
            logger.error(f"Error in bulk notification: {e}")
class AnimeBot:
    def __init__(self):
        self.config = Config()
        self.db = Database()
        self.notification_manager = NotificationManager(self)
        self.app = None  # We'll set this when the client starts
        self.force_sub = ForceSub(self.db, self)  # Pass self as bot_instance
        self.broadcast = Broadcast(self.db, self.config)
        self.request_system = RequestSystem(self)
        self.user_sessions = {}
        self.pending_files = {}
        self.file_lists = {}
        self.rate_limit = {}
        self.premium = Premium(self.db, self.config, self)
        self.quotes = AnimeQuotes(self)  # No initialize needed here

        self.settings = {
            'delete_timer': {
                'name': 'Delete Timer',
                'type': int,
                'min': 1,
                'max': 1440,
                'unit': 'minutes',
                'config_attr': 'DELETE_TIMER_MINUTES'
            },
            'max_results': {
                'name': 'Max Results',
                'type': int,
                'min': 5,
                'max': 50,
                'unit': 'results',
                'config_attr': 'MAX_SEARCH_RESULTS'
            },
            'max_episodes': {
                'name': 'Max Episodes',
                'type': int,
                'min': 5,
                'max': 100,
                'unit': 'episodes',
                'config_attr': 'MAX_EPISODES_PER_PAGE'
            },
            'pm_search': {
                'name': 'PM Search',
                'type': bool,
                'options': ['Enable', 'Disable'],
                'config_attr': 'PM_SEARCH'
            },
            'protect_content': {
                'name': 'Protect Content',
                'type': bool,
                'options': ['Enable', 'Disable'],
                'config_attr': 'PROTECT_CONTENT'
            },
            'rate_limit': {
                'name': 'Rate Limit',
                'type': int,
                'min': 1,
                'max': 60,
                'unit': 'msg/sec',
                'config_attr': 'RATE_LIMIT'
            }
        }
        
        self.quality_patterns = [
            r'\[(\d{3,4}[pP])\]', 
            r'\((\d{3,4}[pP])\)',
            r'\{(\d{3,4}[pP])\}',
            r'(\d{3,4}[pP])',
            r'\[(HD|FHD|UHD)\]',
            r'\[(hdrip|HDRip|HDRIP)\]',        # [hdrip], [HDRip], [HDRIP]
            r'\((hdrip|HDRip|HDRIP)\)',        # (hdrip), (HDRip)
            r'\b(hdrip|HDRip|HDRIP)\b',        # hdrip, HDRip
            r'\[(webrip|WebRip|WEBRIP)\]',     # [webrip], [WebRip]
            r'\((webrip|WebRip|WEBRIP)\)',     # (webrip), (WebRip)
            r'\b(webrip|WebRip|WEBRIP)\b',     # webrip, WebRip
            r'\((HD|FHD|UHD)\)'
        ]

        self.episode_patterns =  [
            r'\[S\d+\s*[-~]\s*E(\d+)\]',     # [S01-E13]
            r'\bS\d+\s*[-~]\s*E(\d+)\b',     # S01 - E13 (no brackets)
            r'\[E(\d+)\]',                   # [E13]
            r'S\d+E(\d+)',                   # S01E13
            r'OVA\s*[-~]?\s*(\d{1,3})',      # OVA - 05
            r'Episode\s*(\d+)',              # Episode 13
            r'Ep\s*(\d+)',                   # Ep 13
            r'-\s*(\d{2,3})\s*-',            # - 13 -
            r'_\s*(\d{2,3})\s*_',            # _13_
            r'\[\s*(\d+)\s*\]',              # [13]
            r'\(\s*(\d+)\s*\)',              # (13)
            r'\b(\d{2,3})\b',                # Standalone 13
            r'第(\d+)話',                    # Japanese notation
            r'第(\d+)集',                     # Chinese notation

                # NEW PATTERNS TO ADD:
            r'\[S(\d+)\s+E(\d+)\]',          # [S01 E17] - NEW
            r'\[Season\s*(\d+)\s*Episode\s*(\d+)\]',  # [Season 1 Episode 5]
            r'\bS(\d+)\s*E(\d+)\b',          # S01 E17 - NEW
            r'\[(\d+)\s*of\s*\d+\]',         # [01 of 12]
            r'\[S(\d+)\s+EP?(\d+)\]',          # [S01 EP11] or [S01 E11] - NEW
            r'\bS(\d+)\s+EP?(\d+)\b',          # S01 EP11 or S01 E11 - NEW
            r'\[EP?(\d+)\]',                   # [EP11] or [E11] - NEW
            r'\bEP?(\d+)\b',                   # EP11 or E11 - NEW
            r'\[Episode\s*(\d+)\]',            # [Episode 11] - NEW
            r'Movie',                        # Movie keyword - NEW
            r'\[Movie\]',                    # [Movie] - NEW
            r'\(\s*Movie\s*\)',              # (Movie) - NEW
            r'Complete\s*Movie',             # Complete Movie - NEW
            r'Full\s*Movie',                 # Full Movie - NEW
            r'劇場版',                       # Japanese for "Movie Edition"
            r'Feature\s*Film'               # Feature Film
        
        ]
        self.season_patterns = [
            r'Season\s*(\d+)',
            r'S(\d+)',
            r'\[\s*S(\d+)\s*\]',
            r'\(\s*S(\d+)\s*\)'
        ]
        self.language_patterns = [
            r'\[(EN|ENG|JP|JAP|ES|FR|DE|HIN|TEL|SUB|DUB|DUAL|MULTI)\]',
            r'\((EN|ENG|JP|JAP|ES|FR|DE|HIN|TEL|SUB|DUB|DUAL|MULTI)\)',
            r'\{(EN|ENG|JP|JAP|ES|FR|DE|HIN|TEL|SUB|DUB|DUAL|MULTI)\}'
        ]


    async def initialize(self, app=None):
        if app:
            self.app = app  # Store the Pyrogram client
        await self.db.initialize()
        await self.force_sub.initialize()  # Add this line
        await self.notification_manager.start() # Start notification processing
        asyncio.create_task(self.premium.validate_cache_periodically())
        asyncio.create_task(self.auto_update_ongoing_series())  # Add this line

    def get_user_session(self, user_id: int, message_id: int = None):
        """Get user session data with automatic cleanup"""
        now = datetime.now()
        
        # First clean up expired sessions
        expired_keys = []
        for key, session in self.user_sessions.items():
            if isinstance(key, int):  # User ID based session
                last_active = session.get('last_active')
                if last_active and (now - last_active).total_seconds() > 300:  # 5 minutes
                    expired_keys.append(key)
            elif isinstance(key, tuple):  # Message ID based session
                last_active = session.get('last_active')
                if last_active and (now - last_active).total_seconds() > 300:
                    expired_keys.append(key)
        
        for key in expired_keys:
            del self.user_sessions[key]
        
        # Now get the requested session
        if message_id:
            return self.user_sessions.get((user_id, message_id), {}).get('data', {})
        return self.user_sessions.get(user_id, {})

    def set_user_session(self, user_id: int, data: dict, message_id: int = None):
        data['last_active'] = datetime.now()

        if message_id:
            self.user_sessions[message_id] = {
                'data': data,
                'original_user': user_id,
                'last_active': datetime.now()
            }
        else:
            self.user_sessions[user_id] = data

    def clear_user_session(self, user_id: int, message_id: int = None):
        """Clear user session"""
        if message_id:
            if (user_id, message_id) in self.user_sessions:
                del self.user_sessions[(user_id, message_id)]
        elif user_id in self.user_sessions:
            del self.user_sessions[user_id]

    async def session_cleanup_task(self):
        while True:
            now = datetime.now()
            expired_keys = []

            for key, session in self.user_sessions.items():
                last_active = session.get('last_active')
                if last_active and (now - last_active).total_seconds() > 300:
                    expired_keys.append(key)

            for key in expired_keys:
                try:
                    original_user = self.user_sessions[key].get('original_user')
                    if original_user:
                        try:
                            await self.bot.send_message(
                                chat_id=original_user,
                                text="⌛ Your session has expired due to inactivity. Please start again."
                            )
                        except:
                            pass
                    del self.user_sessions[key]
                except Exception as e:
                    logger.error(f"Error cleaning session {key}: {e}")

            await asyncio.sleep(60)


    async def check_rate_limit(self, user_id: int, chat_id: int = None) -> bool:
        key = f"{user_id}:{chat_id}" if chat_id else str(user_id)
        now = datetime.now()
        
        if key not in self.rate_limit:
            self.rate_limit[key] = []
        
        # Remove old timestamps
        self.rate_limit[key] = [
            t for t in self.rate_limit[key] 
            if (now - t).total_seconds() < Config.REQUEST_TIMEOUT
        ]
        
        if len(self.rate_limit[key]) >= Config.RATE_LIMIT:
            return False
        
        self.rate_limit[key].append(now)
        return True

    async def update_stats(self, stat_type: str, increment: int = 1):
        await self.db.update_stats(stat_type, increment)
    async def count_total_episodes(self, count_unique=True):
        total = 0
        if not hasattr(self.db, 'anime_clients') or not self.db.anime_clients:
            logger.warning("No anime_clients available in Database instance")
            return 0
            
        for client in self.db.anime_clients:
            try:
                db = client[self.db.db_name]  # Use subscription syntax
                if count_unique:
                    pipeline = [
                        {"$group": {"_id": "$episode"}},
                        {"$count": "unique_episodes"}
                    ]
                else:
                    pipeline = [{"$count": "total_files"}]
                    
                result = await db.files.aggregate(pipeline).to_list(1)
                if result and result[0].get('unique_episodes' if count_unique else 'total_files'):
                    total += result[0]['unique_episodes' if count_unique else 'total_files']
            except Exception as e:
                logger.warning(f"Error counting episodes in cluster: {e}")
        return total
    async def status_command(self, client: Client, message: Message):
        """Enhanced status command with clean metrics and robust formatting"""
        try:
            from datetime import datetime, timedelta
            import psutil
            import asyncio
    
            def format_timedelta(td: timedelta) -> str:
                days = td.days
                hours, remainder = divmod(td.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                return f"{days}d {hours}h {minutes}m {seconds}s"
    
            def format_mb(bytes_value):
                return f"{bytes_value / 1024 / 1024:.2f}MB"
    
            async def get_uptime() -> timedelta:
                try:
                    with open('/proc/uptime', 'r') as f:
                        uptime_seconds = float(f.readline().split()[0])
                    return timedelta(seconds=int(uptime_seconds))
                except Exception:
                    return datetime.now() - datetime.fromtimestamp(psutil.boot_time())
    
            # 🖥️ System info
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_percent = psutil.cpu_percent(interval=0.5)
            uptime = await get_uptime()
    
            # 👥 User stats
            stats = await self.db.stats_collection.find_one({"type": "global"}) or {}
            total_users = await self.db.users_collection.count_documents({})
            premium_users = await self.db.premium_users.count_documents({
                "expiry_date": {"$gt": datetime.now()}
            })
    
            # 📦 Cluster stats
            cluster_info = []
            total_anime = 0
            total_files = 0
    
            if not hasattr(self.db, 'anime_clients') or not self.db.anime_clients:
                cluster_info.append("🔹 No database clusters configured or initialized")
            else:
                for i, cluster_client in enumerate(self.db.anime_clients):
                    try:
                        db = cluster_client[self.db.db_name]
                        anime_count = await db.anime.estimated_document_count()
                        files_count = await db.files.estimated_document_count()
                        total_anime += anime_count
                        total_files += files_count
    
                        db_stats = await db.command("dbStats")
                        data_size_mb = db_stats.get('dataSize', 0) / (1024 * 1024)
                        index_size_mb = db_stats.get('indexSize', 0) / (1024 * 1024)
    
                        cluster_info.append(
                            f"🔹 <b>Cluster {i}</b><br>"
                            f"   • Status: ✅ Online<br>"
                            f"   • Anime: <code>{anime_count}</code><br>"
                            f"   • Files: <code>{files_count}</code><br>"
                            f"   • Data Size: <code>{data_size_mb:.2f} MB</code><br>"
                            f"   • Index Size: <code>{index_size_mb:.2f} MB</code>"
                        )
                    except Exception as e:
                        cluster_info.append(
                            f"🔹 <b>Cluster {i}</b><br>"
                            f"   • Status: ❌ Offline<br>"
                            f"   • Error: <code>{str(e)[:100]}</code>"
                        )
    
            total_episodes = await self.count_total_episodes(count_unique=True)
    
            # 👤 User DB status
            try:
                user_stats = await self.db.users_client[self.db.db_name].command("dbStats")
                user_data_size = user_stats.get('dataSize', 0) / (1024 * 1024)
                user_index_size = user_stats.get('indexSize', 0) / (1024 * 1024)
    
                user_db_info = (
                    f"👤 <b>Users Database</b><br>"
                    f"   • Status: ✅ Online<br>"
                    f"   • Users: <code>{total_users}</code><br>"
                    f"   • Premium: <code>{premium_users}</code><br>"
                    f"   • Data Size: <code>{user_data_size:.2f} MB</code><br>"
                    f"   • Index Size: <code>{user_index_size:.2f} MB</code>"
                )
            except Exception as e:
                user_db_info = (
                    f"👤 <b>Users Database</b><br>"
                    f"   • Status: ❌ Offline<br>"
                    f"   • Error: <code>{str(e)[:100]}</code>"
                )
    
            # 📊 Insert distribution
            insert_stats = getattr(self.db, 'insert_stats', {})
            total_inserts = insert_stats.get('total_inserts', 0)
            cluster_counts = insert_stats.get('cluster_counts', {})
    
            if total_inserts > 0:
                cluster_dist = [
                    f"🔹 Cluster {i}: <code>{count}</code> inserts "
                    f"({(count / total_inserts) * 100:.1f}%)"
                    for i, count in cluster_counts.items()
                ]
            else:
                cluster_dist = ["No insert activity yet."]
    
            # 📄 Final message
            message_text = (
                f"<b>📊 {Config.BOT_NAME} Status</b>\n\n"
            
                f"<b>🖥️ System Info</b>\n"
                f"• CPU Usage: <code>{cpu_percent}%</code>\n"
                f"• Memory: <code>{memory.percent}%</code> "
                f"({format_mb(memory.used)} / {format_mb(memory.total)})\n"
                f"• Disk: <code>{disk.percent}%</code> "
                f"({format_mb(disk.used)} / {format_mb(disk.total)})\n"
                f"• Uptime: <code>{format_timedelta(uptime)}</code>\n\n"
            
                f"<b>📈 Bot Statistics</b>\n"
                f"• Total Anime: <code>{total_anime}</code>\n"
                f"• Total Files: <code>{total_files}</code>\n"
                f"• Episodes: <code>{total_episodes}</code>\n\n"
                f"• Users: <code>{total_users}</code>\n"
                f"• Premium Users: <code>{premium_users}</code>\n\n"
                f"• Searches: <code>{stats.get('total_searches', 0)}</code>\n"
                f"• Downloads: <code>{stats.get('total_downloads', 0)}</code>\n\n"
            
                f"<b>🗃️ Cluster Databases</b>\n"
                + "\n\n".join(cluster_info) +
                "\n\n"
            
                f"{user_db_info}\n\n"
            
                f"<b>📦 Insert Distribution</b>\n"
                + "\n".join(cluster_dist)
            )

    
            sent_msg = await message.reply_text(
                message_text,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True
            )
            await asyncio.sleep(120)
            await sent_msg.delete()
    
        except Exception as e:
            logger.error(f"Status command error: {e}", exc_info=True)
            await message.reply_text("⚠️ Error retrieving status information.")

    async def get_anime_title(self, anime_id: int) -> str:
        anime = await self.db.find_anime(anime_id)
        return anime["title"] if anime else "Unknown Anime"

    async def update_message(self, client: Client, message: Message, text: str, 
                            reply_markup: InlineKeyboardMarkup = None, 
                            photo: str = None,
                            parse_mode: ParseMode = ParseMode.HTML) -> Message:
        try:
            if photo:
                if message.photo:
                    return await message.edit_media(
                        InputMediaPhoto(photo, caption=text, parse_mode=parse_mode),
                        reply_markup=reply_markup
                    )
                else:
                    await message.delete()
                    return await client.send_photo(
                        chat_id=message.chat.id,
                        photo=photo,
                        caption=text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode
                    )
            else:
                return await message.edit_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
        except MessageNotModified:
            return message
        except Exception as e:
            logger.error(f"Error updating message: {e}")
            try:
                if photo:
                    return await client.send_photo(
                        chat_id=message.chat.id,
                        photo=photo,
                        caption=text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode
                    )
                else:
                    return await message.reply_text(
                        text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode
                    )
            except Exception as e:
                logger.error(f"Fallback message send failed: {e}")
                raise

    async def browse_command(self, client: Client, message: Message):
        try:
            keyboard = []
            row = []
            for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                row.append(InlineKeyboardButton(char, callback_data=f"browse_{char}"))
                if len(row) == 6:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)

            keyboard.append([
                InlineKeyboardButton("🔙 Back", callback_data="start_menu"),
                InlineKeyboardButton("❌ Close", callback_data="close_message")
            ])

            # Use a different picture for browse if available, or fallback to START_PIC
            browse_pic = "https://files.catbox.moe/qqa869.jpg"  # Replace with your actual browse picture URL
            try:
                await message.reply_photo(
                    photo=browse_pic,
                    caption="📚 Browse Anime by Letter\nSelect a letter to browse anime:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception:
                # Fallback to text if photo fails
                await message.reply_text(
                    "📚 Browse Anime by Letter\nSelect a letter to browse anime:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            logger.error(f"Error in browse command: {e}")
            await message.reply_text("⚠️ Error loading anime list. Please try again.")

  

    async def watchlist_command(self, client: Client, message: Message):
        try:
            user_id = message.from_user.id
            watchlist = await self.db.get_watchlist(user_id, Config.MAX_WATCHLIST_ITEMS)
    
            if not watchlist:
                await message.reply_text(
                    "⭐ Your watchlist is empty.\n"
                    "Easily add anime to your watchlist from their details page.\n\n"
                    "<blockquote>📝 Note: Add <b>ongoing anime</b> to your watchlist to get notified when new episodes are added!</blockquote>\n"
                    "<blockquote>💡 Tip: Use the <code>/ongoing</code> command to see the current list of ongoing anime.</blockquote>",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📜 Browse Anime", callback_data="available_anime")]
                    ]),
                    parse_mode=enums.ParseMode.HTML
                )
                return
    
            # --- Fetch releasing anime (for later use in ongoing command) ---
            releasing_anime = []
            for db_client in self.db.anime_clients:
                try:
                    db = db_client[self.db.db_name]
                    cluster_results = await db.anime.find(
                        {"status": "RELEASING"},
                        {"id": 1, "title": 1, "episodes": 1, "last_updated": 1}
                    ).sort("last_updated", -1).to_list(None)
                    releasing_anime.extend(cluster_results)
                except Exception as e:
                    logger.warning(f"Error fetching releasing anime from cluster: {e}")
                    continue
    
            # --- Enhance watchlist with status and episode counts ---
            enhanced_watchlist = []
            for item in watchlist:
                anime = await self.db.find_anime(item["anime_id"])
                if anime:
                    status = anime.get("status", "").upper()
                    try:
                        total_uploaded = await self.db.count_episodes(anime["id"], count_unique=True)
                    except Exception as e:
                        logger.warning(f"Error counting episodes for anime {anime['id']}: {e}")
                        total_uploaded = 0
    
                    anime_data = {
                        "anime_id": anime["id"],
                        "title": anime["title"],
                        "status": status,
                        "episodes": anime.get("episodes", "?"),
                        "uploaded": total_uploaded
                    }
                    enhanced_watchlist.append(anime_data)
    
            # --- Build keyboard ---
            keyboard = []
            for item in enhanced_watchlist:
                status_indicator = "🔄 " if item.get("status") == "RELEASING" else ""
    
                if item.get("status") == "RELEASING":
                    btn_text = f"{status_indicator}{item['title']} ({item['uploaded']}/{item['episodes']})"
                else:
                    btn_text = f"{status_indicator}{item['title']}"
    
                keyboard.append([
                    InlineKeyboardButton(
                        btn_text,
                        callback_data=f"anime_{item['anime_id']}"
                    )
                ])
    
            # Pagination if more than 10
            if len(watchlist) > 10:
                keyboard.append([
                    InlineKeyboardButton("◀️ Previous", callback_data="watchlist_prev"),
                    InlineKeyboardButton("▶️ Next", callback_data="watchlist_next")
                ])
    
            # Back & Close buttons
            keyboard.append([
                InlineKeyboardButton("🔙 Back", callback_data="start_menu"),
                InlineKeyboardButton("❌ Close", callback_data="close_message")
            ])
    
            # --- Final reply ---
            await message.reply_text(
                "<blockquote>⭐ <b>Your Watchlist</b></blockquote>\n\n"
                "<blockquote>🔄 = Currently releasing new episodes</blockquote>\n"
                "Select an anime to view details:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=enums.ParseMode.HTML
            )

        except Exception as e:
            logger.error(f"Error in watchlist command: {e}")
            await message.reply_text("⚠️ Error loading your watchlist. Please try again.")

    def clean_filename(filename):
        """Clean and normalize filename for better parsing"""
        # Remove release group tags
        filename = re.sub(r'\[@.*?\]', '', filename)
        # Replace special separators with spaces
        filename = re.sub(r'[\[\](){}_]', ' ', filename)
        # Remove multiple spaces
        filename = ' '.join(filename.split())
        return filename.strip()

    async def extract_episode_number(self, message: Message, anime_type: str) -> Optional[int]:
        # Get filename and caption
        file_name = message.document.file_name if message.document else message.video.file_name if message.video else ""
        caption = message.caption or ""
        combined_text = f"{file_name} {caption}".lower()

        logger.info(f"Extracting episode from: {combined_text}")

        # Check if this is non-episodic content
        type_info = Config.ANIME_TYPES.get(anime_type.upper(), {})
        if not type_info.get('has_episodes', True):
            return 1  # Default to episode 1 for movies/OVA/etc.

        # Movie detection patterns
        movie_patterns = [
            r'\bmovie\b', r'\bfilm\b', r'complete movie', r'full movie',
            r'劇場版', r'movie edition', r'feature film', r'\[movie\]',
            r'\(movie\)', r'-\s*movie\s*-'
        ]
        if any(re.search(pattern, combined_text) for pattern in movie_patterns):
            return 1

        # Episode patterns (your original order, enhanced for padded numbers)
        patterns = [
        r'\[(\d{3,4})\s*-\s*[^\]]+\]',   # [0055 - One Piece]
        r'\[\s*(\d{3,4})\s*\]',          # [0055]
        r'\b(\d{3,4})\s*-\s*[^\[]',      # 0055 - One Piece
    
        r'\[[^\]]*E(\d+)[^\]]*\]',       # [Onepiece - E1127], [Anime - Ep12 - Sub]
        r'\bS\d+E(\d+)\b',               # S01E13
    
        r'[-_\( ]E(\d+)[-_ \)]',         # -E1127-, _E1127_, (E1127)
        r'\bE(\d+)\b',                   # plain E1127
        r'\bEP(\d+)\b',                  # EP1125 / Ep1125 / ep1125
    
        r'\[S\d+\s*[-~]\s*E(\d+)\]',     # [S01-E13]
        r'\bS\d+\s*[-~]\s*E(\d+)\b',     # S01 - E13
        r'\[E(\d+)\]',                   # [E13]
    
        r'OVA\s*[-~]?\s*(\d{1,3})',      # OVA - 05
        r'Episode\s*(\d+)',              # Episode 13
        r'Ep\s*(\d+)',                   # Ep 13
        r'-\s*(\d{2,3})\s*-',            # - 13 -
        r'_\s*(\d{2,3})\s*_',            # _13_
        r'\(\s*(\d+)\s*\)',              # (13)
        r'\b(\d{2,3})\b',                # Standalone 13
        r'第(\d+)話',                     # Japanese
        r'第(\d+)集'                      # Chinese
    ]


        for pattern in patterns:
            matches = re.finditer(pattern, combined_text, re.IGNORECASE)
            for match in matches:
                try:
                    for group in match.groups():
                        if group and group.isdigit():
                            episode_num = int(group)
                            # Handle padded numbers
                            if episode_num > 1000:  # Likely padded 4-digit
                                # Remove leading zeros but keep actual number
                                episode_num = int(group.lstrip("0") or "0")
                            elif group.startswith("0") and len(group) > 1:
                                episode_num = int(group.lstrip("0"))
                            return episode_num
                except (ValueError, IndexError, AttributeError):
                    continue

        # Season marker without episode → default 1
        if re.search(r'S\d+', combined_text, re.IGNORECASE):
            return 1

        if result is None:
            logger.warning(f"Could not extract episode number from: {combined_text}")
    
        return result
    async def send_formatted_message(client, chat_id, text, reply_markup=None):
        try:
            return await client.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=enums.ParseMode.HTML,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            # Fallback to unformatted text
            return await client.send_message(
                chat_id=chat_id,
                text=html.unescape(re.sub('<[^<]+?>', '', text)),
                reply_markup=reply_markup
            )
    async def start(self, client: Client, message: Message):
        user_id = message.from_user.id

        # Force subscription check
        if self.force_sub.force_sub_enabled and self.force_sub.force_sub_channels:
            if not await self.force_sub.check_member(client, user_id):
                force_sub_msg, keyboard = await self.force_sub.get_force_sub_message(client)
                await client.send_photo(
                    chat_id=message.chat.id,
                    photo=self.force_sub.force_sub_image,  # configurable image
                    caption=force_sub_msg,
                    reply_markup=keyboard
                )
                return

        # Safely get command args
        text = message.text or message.caption
        args = text.split(" ", 1) if text else []

        if len(args) > 1:
            try:
                base64_string = args[1]
                string = await decode(base64_string)

                if string.startswith("file_"):
                    file_id = string[5:]
                    await self.process_file_download(client, message, file_id)
                    return
                elif string.startswith("bulk_"):
                    parts = string.split('_')
                    if len(parts) >= 3:
                        quality = parts[1]
                        anime_id = int(parts[2])
                        await self.process_file_download(client, message, f"bulk_{quality}_{anime_id}")
                        return
            except Exception as e:
                logger.error(f"Error decoding start parameter: {e}")

        user = message.from_user

        
        update_data = {
            "$setOnInsert": {
                "user_id": user.id,
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "join_date": datetime.now()
            },
            "$set": {
                "username": user.username if user.username else None,
                "last_active": datetime.now()
            },
            "$inc": {
                "downloads": 0,
                "searches": 0
            },
        }
        
        update_data["$set"] = {k: v for k, v in update_data["$set"].items() if v is not None}
    
        await self.db.users_collection.update_one(
            {"user_id": user.id},
            update_data,
            upsert=True
        )
        await self.update_stats("total_users")

        if Config.GROUP_ID:
            try:
                member = await client.get_chat_member(Config.GROUP_ID, user.id)
                if member.status in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED]:
                    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Join Group", url=Config.GROUP_LINK)]])
                    await message.reply_text(
                        f"⚠️ Please join our group first to use this bot:\n{Config.GROUP_LINK}",
                        reply_markup=keyboard)
                    return
            except Exception as e:
                logger.error(f"Error checking group membership for user {user.id}: {e}")


        # Assuming you have access to `user` and `message` and other context
        welcome_text = Scripts.WELCOME_TEXT.format(first_name=user.first_name)


        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📢 ᴜᴘᴅᴀᴛᴇꜱ", url="https://t.me/TFIBOTS")
            ],
            [
                InlineKeyboardButton("📜 ʙʀᴏᴡꜱᴇ ᴀɴɪᴍᴇ", callback_data="available_anime"),
                InlineKeyboardButton("⭐ ᴡᴀᴛᴄʜʟɪꜱᴛ", callback_data="view_watchlist")
            ],
            [
                InlineKeyboardButton("• ᴄʟᴏꜱᴇ •", callback_data="close_message")
            ]
        ])

        if user.id in Config.ADMINS:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")
            ])

        try:
                await message.reply_photo(
                photo=Config.START_PIC,
                caption=welcome_text,
                reply_markup=keyboard,
                parse_mode=enums.ParseMode.HTML  # Make sure this is set!

                
            )

        except Exception as e:
            logger.error(f"Error sending start message: {e}")
            await message.reply_text("⚠️ Error starting bot. Please try again.")

    async def search_anime(self, client: Client, message: Message):
        try:
            await message.reply_text("🔍 *Enter the anime name to search:*")
            self.user_sessions[message.from_user.id] = {'awaiting_search': True}
        except Exception as e:
            logger.error(f"Error in search_anime: {e}")
            await message.reply_text("⚠️ Error initiating search. Please try again.")


    async def view_watchlist(self, client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        try:
            watchlist = await self.db.get_watchlist(user_id, Config.MAX_WATCHLIST_ITEMS)
            if not watchlist:
                await callback_query.answer("Your watchlist is empty.", show_alert=True)
                return
    
            keyboard = []
            for item in watchlist:
                keyboard.append([
                    InlineKeyboardButton(
                        item["title"],
                        callback_data=f"anime_{item['anime_id']}"
                    )
                ])
    
            keyboard.append([
                InlineKeyboardButton("🔙 Back", callback_data="start_menu"),
                InlineKeyboardButton("❌ Close", callback_data="close_message")
            ])
    
            reply_markup = InlineKeyboardMarkup(keyboard)
    
            text = (
                "⭐ <b>Your Watchlist</b>\n\n"
                "Select an anime to view details:\n\n"
                "<blockquote>📝 Note: Add <b>ongoing anime</b> to your watchlist to get notified when new episodes are added!</blockquote>\n"
                "<blockquote>💡 Tip: Use the <code>/ongoing</code> command to see the current list of ongoing anime.</blockquote>"
            )
    
            await self.update_message(
                client,
                callback_query.message,
                text,
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error viewing watchlist: {e}")
            await callback_query.answer("Error viewing watchlist.", show_alert=True)

    async def toggle_watchlist(self, client: Client, callback_query: CallbackQuery, anime_id: int):
        user_id = callback_query.from_user.id
        try:
            anime = await self.db.find_anime(anime_id)
            if not anime:
                await callback_query.answer("Anime not found.", show_alert=True)
                return
            
            in_watchlist = await self.db.is_in_watchlist(user_id, anime_id)
            
            if in_watchlist:
                await self.db.remove_from_watchlist(user_id, anime_id)
                action = "removed from"
            else:
                count = await self.db.watchlist_collection.count_documents({"user_id": user_id})
                if count >= Config.MAX_WATCHLIST_ITEMS:
                    await callback_query.answer(
                        f"Watchlist limit reached ({Config.MAX_WATCHLIST_ITEMS}). Remove some items first.",
                        show_alert=True)
                    return
                
                await self.db.add_to_watchlist(user_id, anime_id)
                action = "added to"
            
            await callback_query.answer(
                f"{anime['title']} {action} your watchlist!",
                show_alert=True)
            
            if user_id in self.user_sessions and 'current_anime' in self.user_sessions[user_id]:
                await self.show_anime_details(client, callback_query, anime_id)
                
        except Exception as e:
            logger.error(f"Error toggling watchlist: {e}")
            await callback_query.answer("Error updating watchlist.", show_alert=True)

    async def show_saga_list(self, client: Client, callback_query: CallbackQuery, anime_id: int):
        """Show list of sagas for One Piece"""
        try:
            sagas = await self.db.get_anime_sagas(anime_id)
            if not sagas:
                await callback_query.answer("No sagas found for this anime.", show_alert=True)
                return

            keyboard = []
            for saga in sagas:
                btn_text = f"{saga['name']} ({saga['episode_range']})"
                keyboard.append([
                    InlineKeyboardButton(btn_text, callback_data=f"saga_{anime_id}_{saga['id']}")
                ])

            # Add back button
            keyboard.append([
                InlineKeyboardButton("🔙 Back to Anime", callback_data=f"anime_{anime_id}"),
                InlineKeyboardButton("❌ Close", callback_data="close_message")
            ])

            anime = await self.db.find_anime(anime_id)
            await self.update_message(
                client,
                callback_query.message,
                f"📚 <b>Sagas of {anime['title']}</b>\n\n"
                "Select a saga to view its arcs:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Error showing saga list: {e}")
            await callback_query.answer("Error loading sagas.", show_alert=True)

    async def show_saga_arcs(self, client: Client, callback_query: CallbackQuery, anime_id: int, saga_id: int):
        """Show arcs for a specific saga"""
        try:
            sagas = await self.db.get_anime_sagas(anime_id)
            saga = next((s for s in sagas if s["id"] == saga_id), None)
            
            if not saga:
                await callback_query.answer("Saga not found.", show_alert=True)
                return

            arcs = await self.db.get_saga_arcs(anime_id, saga_id)
            if not arcs:
                await callback_query.answer("No arcs found for this saga.", show_alert=True)
                return

            keyboard = []
            for arc in arcs:
                btn_text = f"{arc['name']} ({arc['episode_range']})"
                keyboard.append([
                    InlineKeyboardButton(btn_text, callback_data=f"arc_{anime_id}_{saga_id}_{arc['id']}")
                ])

            # Add bulk download button for the entire saga
            keyboard.append([
                InlineKeyboardButton("📥 Download Entire Saga", callback_data=f"bulk_saga_{anime_id}_{saga_id}")
            ])

            # Add navigation buttons
            keyboard.append([
                InlineKeyboardButton("🔙 Back to Sagas", callback_data=f"sagas_{anime_id}"),
                InlineKeyboardButton("❌ Close", callback_data="close_message")
            ])

            anime = await self.db.find_anime(anime_id)
            await self.update_message(
                client,
                callback_query.message,
                f"📖 <b>{saga['name']}</b>\n"
                f"📅 {saga['year_range']} | 📺 {saga['episode_range']}\n\n"
                f"{saga['description']}\n\n"
                "Select an arc to view episodes:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Error showing saga arcs: {e}")
            await callback_query.answer("Error loading arcs.", show_alert=True)

    async def show_arc_episodes(self, client: Client, callback_query: CallbackQuery, anime_id: int, saga_id: int, arc_id: int):
        """Show episodes for a specific arc"""
        try:
            # Get arc information
            # First check if files exist for this arc
            files_exist, message = await self.check_saga_arc_files_exist(anime_id, saga_id, arc_id)
            if not files_exist:
                await callback_query.answer(message, show_alert=True)
                return
            
            # FIX: You need to get the arc information here!
            sagas = await self.db.get_anime_sagas(anime_id)
            saga = next((s for s in sagas if s["id"] == saga_id), None)
            if not saga:
                await callback_query.answer("Saga not found.", show_alert=True)
                return
                
            arc = next((a for a in saga["arcs"] if a["id"] == arc_id), None)  # ← This was missing!
            
            if not arc:
                await callback_query.answer("Arc not found.", show_alert=True)
                return

            # FIX: Handle "Present" in episode range (e.g., "1086–Present")
            episode_range = arc["episode_range"]
            if "–" in episode_range:
                start_end = episode_range.split("–")
                try:
                    start_ep = int(start_end[0].strip())
                    # Handle "Present" as the end value
                    if start_end[1].strip().lower() == "present":
                        # For ongoing arcs, get the current max episode from database
                        end_ep = await self.get_max_episode(anime_id)
                        # If no episodes found, use start_ep as both start and end
                        if end_ep < start_ep:
                            end_ep = start_ep
                    else:
                        end_ep = int(start_end[1].strip())
                except ValueError:
                    await callback_query.answer("Invalid episode range format.", show_alert=True)
                    return
            else:
                await callback_query.answer("Invalid episode range format.", show_alert=True)
                return
            
            # Create episode selection buttons
            keyboard = []
            row = []
            for ep in range(start_ep, end_ep + 1):
                row.append(InlineKeyboardButton(str(ep), callback_data=f"ep_{anime_id}_{ep}"))
                if len(row) == 5:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)

            # Add bulk download for the arc
            keyboard.append([
                InlineKeyboardButton("📥 Download Entire Arc", callback_data=f"bulk_arc_{anime_id}_{saga_id}_{arc_id}")
            ])

            # Add navigation buttons
            keyboard.append([
                InlineKeyboardButton("🔙 Back to Arcs", callback_data=f"saga_{anime_id}_{saga_id}"),
                InlineKeyboardButton("❌ Close", callback_data="close_message")
            ])

            anime = await self.db.find_anime(anime_id)
            
            # Update episode range display for ongoing arcs
            display_range = f"{start_ep}–{end_ep}" if end_ep > start_ep else f"{start_ep}"
            if "Present" in episode_range:
                display_range += " (Ongoing)"
                
            await self.update_message(
                client,
                callback_query.message,
                f"🎬 <b>{arc['name']}</b>\n"
                f"📺 Episodes: {display_range}\n\n"
                f"{arc['description']}\n\n"
                "Select an episode to download:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Error showing arc episodes: {e}")
            await callback_query.answer("Error loading episodes.", show_alert=True)
        
    async def show_anime_details(self, client: Client, callback_query: CallbackQuery, anime_id: int):
        try:
            user_id = callback_query.from_user.id
            # Search across all clusters for the anime
            anime = None
            for db_client in self.db.anime_clients:  # Changed variable name from client to db_client
                try:
                    db = db_client[self.db.db_name]  # Use db_client instead of client
                    found = await db.anime.find_one({"id": anime_id})
                    if found:
                        anime = found
                        break
                except Exception as e:
                    logger.warning(f"Error finding anime in cluster: {e}")
                    continue
            if not anime:
                # If not found in DB, search AniList
                ani_data = await self.search_anilist({'id': anime_id})
                if not ani_data:
                    await callback_query.answer("Anime not found.", show_alert=True)
                    return
                
                anime = {
                    'id': ani_data['id'],
                    'title': ani_data['title'].get('english') or ani_data['title'].get('romaji'),
                    'description': await self.format_description(ani_data.get('description')),
                    'score': ani_data.get('averageScore'),
                    'episodes': ani_data.get('episodes'),
                    'status': ani_data.get('status', 'N/A').replace('_', ' ').title(),
                    'duration': f"{ani_data.get('duration', 0)} mins" if ani_data.get('duration') else "N/A",
                    'genres': ani_data.get('genres', []),
                    'studio': ", ".join([s['name'] for s in ani_data['studios']['nodes']]) if ani_data.get('studios') else "N/A",
                    'cover_url': ani_data['coverImage'].get('extraLarge') or ani_data['coverImage'].get('large') or Config.COVER_PIC,
                    'url': ani_data.get('siteUrl'),
                    'is_adult': ani_data.get('isAdult', False),
                    'year': ani_data.get('startDate', {}).get('year') or "Unknown",
                    'type': ani_data.get('format', 'TV')
                }
                await self.db.insert_anime(anime)


            # 🚫 Adult content restriction
            if anime.get('is_adult'):
                if self.config.RESTRICT_ADULT:
                    if not await self.premium.check_access(user_id, 'hpremium'):
                        await callback_query.answer(
                            "🔞 Adult content requires H-Premium subscription!",
                            show_alert=True
                        )
                        return
                elif self.config.PREMIUM_MODE:
                    if not await self.premium.check_access(user_id, 'premium'):
                        await callback_query.answer(
                            "🔒 Content requires premium subscription!",
                            show_alert=True
                        )
                        return

                await callback_query.answer(
                    "⚠️ This anime contains mature content (18+). Viewer discretion is advised.",
                    show_alert=True
                )
            sequel = await self.db.find_anime(anime.get('sequel_id')) if anime.get('sequel_id') else None
            prequel = await self.db.find_anime(anime.get('prequel_id')) if anime.get('prequel_id') else None
            # Track user session
            self.user_sessions[user_id] = {
                'current_anime': anime,
                'current_episode': 1
            }

            # ✅ Type formatting
            anime_type_key = anime.get('type', 'TV').upper()
            type_info = Config.ANIME_TYPES.get(anime_type_key, {})
            type_display = type_info.get('name', anime_type_key)

            # ✅ Episode display
            # In your show_anime_details method:
         # ✅ Episode display formatting
          # ✅ Episode display
            ep_text = ""
            if type_info.get('has_episodes'):
                total_uploaded = await self.db.count_episodes(anime_id, count_unique=True)

                # ✅ Only add (uploaded/total) if status is RELEASING
                if anime.get('status', '').strip().upper() == 'RELEASING':
                    ep_text = f" ({total_uploaded}/{anime.get('episodes', '?')})"

            # Watch callback
            if type_info.get('has_episodes'):
                if anime.get('episodes') is None:
                    # Special case for unknown/ongoing anime like One Piece
                    watch_callback = f"ongoing_{anime_id}_1"
                else:
                    # Normal episodic series
                    watch_callback = f"episodes_{anime_id}_1"
            else:
                # Non-episodic content (movies, specials)
                watch_callback = f"ep_{anime_id}_1"

            # ✅ Genres, description, etc.
            genres = ", ".join(anime.get('genres', [])) or "Not specified"
            description = anime.get('description', "No description available.")
            status = anime.get('status', 'N/A').capitalize()
            year = anime.get('year', 'Unknown')

            # ✅ Rating (without stars)
            score_html = ""
            score = anime.get('score')
            if score is not None:
                try:
                    score_value = float(score) / 10
                    score_html = "<b>Rating:</b> {:.1f}/10".format(score_value)
                except (TypeError, ValueError):
                    logger.warning(f"Invalid score format: {score}")
                    score_html = ""

            # ✅ Build the message
            message_text = Scripts.ANIME_INFO_TEXT.format(
                title=anime.get("title", "Unknown"),
                type_display=type_display,
                status=status,
                episodes=anime.get("episodes", "?"),  # Use display field
                ep_text=ep_text,
                year=year,
                genres=genres,
                score_html=score_html,
                synopsis=description[:500] + ("..." if len(description) > 500 else "")
            )

      
            buttons = []
            if anime_id == 6284053604036871611:  # One Piece ID
                buttons.append([
                    InlineKeyboardButton("📚 Browse by Sagas", callback_data=f"sagas_{anime_id}")
                ])

            if prequel:
                buttons.append([
                    InlineKeyboardButton("🧩 ᴘʀᴇQᴜᴇʟ ", callback_data=f"anime_{prequel['id']}")
                ])
            buttons.append([
                InlineKeyboardButton("👀 ᴡᴀᴛᴄʜ ɴᴏᴡ", callback_data=watch_callback)
            ])

            in_watchlist = await self.db.is_in_watchlist(user_id, anime_id)
            watchlist_text = "🗑️ ʀᴇᴍᴏᴠᴇ ꜰʀᴏᴍ ᴡᴀᴛᴄʜʟɪꜱᴛ" if in_watchlist else "🌟 ᴀᴅᴅ ᴛᴏ ᴡᴀᴛᴄʜʟɪꜱᴛ"
            buttons.append([
                InlineKeyboardButton(watchlist_text, callback_data=f"toggle_watchlist_{anime_id}")
            ])

            if sequel:
                buttons.append([
                    InlineKeyboardButton("🎥 ꜱᴇQᴜᴇʟ " , callback_data=f"anime_{sequel['id']}")
                ])

            # Add Delete Episodes and Add Episodes buttons for admins
            if user_id in Config.ADMINS:
                buttons.append([
                    InlineKeyboardButton("🗑️ Delete Episodes", callback_data=f"del_menu_{anime_id}_1")
                ])
                buttons.append([
                    InlineKeyboardButton("📁 Add Episodes", callback_data=f"admin_add_episodes_{anime_id}")
                ])

            buttons.append([
                InlineKeyboardButton("🧭 ʙᴀᴄᴋ", callback_data="available_anime"),
                InlineKeyboardButton("• ᴄʟᴏꜱᴇ •", callback_data="close_message")
            ])

            if user_id in Config.ADMINS:
                buttons.append([
                    InlineKeyboardButton("✏️ Edit", callback_data=f"admin_edit_anime_{anime_id}"),
                    InlineKeyboardButton("🗑️ Delete", callback_data=f"admin_delete_anime_{anime_id}"),
                    InlineKeyboardButton("🆔 ID", callback_data=f"show_id_{anime_id}")
                ])


            keyboard = InlineKeyboardMarkup(buttons)
            cover_url = anime.get('cover_url', Config.COVER_PIC)
            await self.update_message(
                client,  # This must be the Pyrogram Client
                callback_query.message,
                message_text,
                reply_markup=keyboard,
                parse_mode= ParseMode.HTML,
                photo=cover_url
            )
        except Exception as e:
            logger.error(f"Error in show_anime_details: {e}")
            await callback_query.answer("An error occurred. Please try again.", show_alert=True)

    async def show_episodes(self, client: Client, callback_query: CallbackQuery, anime_id: int, page: int = 1):
        try:
            anime = await self.db.find_anime(anime_id)
        except Exception as e:
            logger.error(f"Error fetching anime ID {anime_id}: {e}")
            await callback_query.answer("⚠️ Error fetching anime.", show_alert=True)
            return
            
        if not anime:
            await callback_query.answer("Anime not found.", show_alert=True)
            return

        # FIX: Handle None episode count (for ongoing series like One Piece)
        if anime.get('episodes') is None:
            # For ongoing series, get the actual count of uploaded episodes
            episodes = await self.db.count_episodes(anime_id, count_unique=True)
            # If no episodes uploaded yet, default to 1
            episodes = episodes if episodes > 0 else 1
        else:
            episodes = anime.get('episodes', 1)
            
        start_ep = (page - 1) * Config.MAX_EPISODES_PER_PAGE + 1
        end_ep = min(page * Config.MAX_EPISODES_PER_PAGE, episodes)
        
        user_id = callback_query.from_user.id
        self.user_sessions[user_id] = {
            'current_anime': anime,
            'episodes_page': page
        }
        
        keyboard = []
        row = []
        for ep in range(start_ep, end_ep + 1):
            row.append(InlineKeyboardButton(str(ep), callback_data=f"ep_{anime_id}_{ep}"))
            if len(row) == 5:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
            
        # Navigation
        # Show "Download All Episodes" button (always visible)
        # Navigation
        # Show "Download All Episodes" button (always visible except for anime_id 6284053604036871611)
        if anime_id != 6284053604036871611:
            keyboard.append([
                InlineKeyboardButton(
                    "• ᴅᴏᴡɴʟᴏᴀᴅ ᴀʟʟ ᴇᴘɪꜱᴏᴅᴇꜱ •",
                    callback_data=f"download_all_{anime_id}"
                )
            ])

        
        # Navigation buttons
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"ep_page_{anime_id}_{page-1}"))
        if end_ep < episodes:
            nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"ep_page_{anime_id}_{page+1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)
            
        # Back & Close
        keyboard.append([
            InlineKeyboardButton("• ʙᴀᴄᴋ •", callback_data=f"anime_{anime_id}"),
            InlineKeyboardButton("• ᴄʟᴏꜱᴇ •", callback_data="close_message")
        ])
        
        # FIX: Handle display for ongoing series
        if anime.get('episodes') is None:
            total_uploaded = await self.db.count_episodes(anime_id, count_unique=True)
            episode_text = f"Select episode ({start_ep}-{end_ep} of {total_uploaded} uploaded):"
        else:
            episode_text = f"Select episode ({start_ep}-{end_ep} of {episodes}):"
        
        await self.update_message(
            client,
            callback_query.message,
            f"<blockquote>📺 <b>{anime['title']}</b></blockquote>\n"
            f"<b>{episode_text}</b>",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    async def check_saga_arc_files_exist(self, anime_id: int, saga_id: int = None, arc_id: int = None):
        # ... existing code ...
        """Check if files exist for a specific saga or arc"""
        all_files = await self.db.find_files(anime_id)
        if not all_files:
            return False, "No files available for this anime."
        
        if saga_id is not None:
            # Check for saga
            sagas = await self.db.get_anime_sagas(anime_id)
            saga = next((s for s in sagas if s["id"] == saga_id), None)
            if not saga:
                return False, "Saga not found."
            
            # Parse episode range
            episode_range = saga["episode_range"]
            if "–" in episode_range:
                start_end = episode_range.split("–")
                try:
                    start_ep = int(start_end[0].strip())
                    if start_end[1].strip().lower() == "present":
                        end_ep = await self.get_max_episode(anime_id)
                        if end_ep < start_ep:
                            end_ep = start_ep
                    else:
                        end_ep = int(start_end[1].strip())
                except ValueError:
                    return False, "Invalid episode range format."
            
            # Check if any files exist in this range
            saga_files = [f for f in all_files if start_ep <= f['episode'] <= end_ep]
            if not saga_files:
                return False, f"No files found for saga: {saga['name']} ({episode_range})"
            
            return True, f"Found {len(saga_files)} files for {saga['name']}"
        elif arc_id is not None:
            # Check for arc
            sagas = await self.db.get_anime_sagas(anime_id)
            saga = next((s for s in sagas if s["id"] == saga_id), None)
            if not saga:
                return False, "Saga not found."
            
            # FIX: Use get_saga_arcs instead of assuming arcs are in saga dict
            arcs = await self.db.get_saga_arcs(anime_id, saga_id)  # ← Changed this line
            arc = next((a for a in arcs if a["id"] == arc_id), None)  # ← And this line
            
            if not arc:
                return False, "Arc not found."
            
            # Parse episode range
            episode_range = saga["episode_range"]
            if "–" in episode_range:
                start_end = episode_range.split("–")
                try:
                    start_ep = int(start_end[0].strip())
                    if start_end[1].strip().lower() == "present":
                        end_ep = await self.get_max_episode(anime_id)
                        if end_ep < start_ep:
                            end_ep = start_ep
                    else:
                        end_ep = int(start_end[1].strip())
                except ValueError:
                    return False, "Invalid episode range format."
            
            # Check if any files exist in this range
            saga_files = [f for f in all_files if start_ep <= f['episode'] <= end_ep]
            if not saga_files:
                return False, f"No files found for saga: {saga['name']} ({episode_range})"
            
            return True, f"Found {len(saga_files)} files for {saga['name']}"
        
        elif arc_id is not None:
            # Check for arc
            sagas = await self.db.get_anime_sagas(anime_id)
            saga = next((s for s in sagas if s["id"] == saga_id), None)
            if not saga:
                return False, "Saga not found."
            
            arc = next((a for a in saga["arcs"] if a["id"] == arc_id), None)
            if not arc:
                return False, "Arc not found."
            
            # Parse episode range
            episode_range = arc["episode_range"]
            if "–" in episode_range:
                start_end = episode_range.split("–")
                try:
                    start_ep = int(start_end[0].strip())
                    if start_end[1].strip().lower() == "present":
                        end_ep = await self.get_max_episode(anime_id)
                        if end_ep < start_ep:
                            end_ep = start_ep
                    else:
                        end_ep = int(start_end[1].strip())
                except ValueError:
                    return False, "Invalid episode range format."
            
            # Check if any files exist in this range
            arc_files = [f for f in all_files if start_ep <= f['episode'] <= end_ep]
            if not arc_files:
                return False, f"No files found for arc: {arc['name']} ({episode_range})"
            
            return True, f"Found {len(arc_files)} files for {arc['name']}"
        
        return False, "Invalid parameters."


    # Use this consistent parsing function throughout your code:
    async def parse_episode_range(self, episode_range: str, anime_id: int = None):
        """Parse episode range, handling 'Present' and different dash types"""
        if "–" in episode_range:  # en dash
            start_end = episode_range.split("–")
        elif "-" in episode_range:  # regular hyphen
            start_end = episode_range.split("-")
        else:
            return None, None, "Invalid episode range format"

        try:
            start_ep = int(start_end[0].strip())
            # Handle "Present" as the end value
            if start_end[1].strip().lower() == "present":
                if anime_id:
                    end_ep = await self.get_max_episode(anime_id)
                    if end_ep < start_ep:
                        end_ep = start_ep
                else:
                    end_ep = start_ep  # fallback
            else:
                end_ep = int(start_end[1].strip())

            return start_ep, end_ep, None
        except ValueError:
            return None, None, "Invalid episode range format"

    async def show_bulk_quality_menu(
        self, 
        client: Client, 
        callback_query: CallbackQuery, 
        anime_id: int, 
        bulk_data: str = None
    ):
        """Show quality options for bulk download - with saga/arc support"""
        try:
            # Parse bulk_data to determine if this is for saga/arc or entire anime
            is_saga = bulk_data and bulk_data.startswith("bulk_saga_")
            is_arc = bulk_data and bulk_data.startswith("bulk_arc_")
            
            # Get anime info
            anime = await self.db.find_anime(anime_id)
            if not anime:
                await callback_query.answer("Anime not found.", show_alert=True)
                return

            # Get all files for this anime across all clusters
            all_files = await self.db.find_files(anime_id)
            if not all_files:
                await callback_query.answer("No files available for this anime.", show_alert=True)
                return

            # Filter files based on saga/arc if specified
            filtered_files = []
            context_info = ""  # For displaying what we're filtering for
            
            if is_saga:
                # Extract saga_id from bulk_data: "bulk_saga_{anime_id}_{saga_id}"
                parts = bulk_data.split('_')
                saga_id = int(parts[3])
                
                # Get saga episode range
                sagas = await self.db.get_anime_sagas(anime_id)
                saga = next((s for s in sagas if s["id"] == saga_id), None)
                
                if saga:
                    # Parse episode range (handle "Present")
                    episode_range = saga["episode_range"]
                    if "–" in episode_range:
                        start_end = episode_range.split("–")
                        try:
                            start_ep = int(start_end[0].strip())
                            # Handle "Present" as the end value
                            if start_end[1].strip().lower() == "present":
                                end_ep = await self.get_max_episode(anime_id)
                                if end_ep < start_ep:
                                    end_ep = start_ep
                            else:
                                end_ep = int(start_end[1].strip())
                        except ValueError:
                            await callback_query.answer("Invalid episode range format.", show_alert=True)
                            return
                    
                    filtered_files = [f for f in all_files if start_ep <= f['episode'] <= end_ep]
                    context_info = f"saga {saga['name']}"
            
            elif is_arc:
                # Extract saga_id and arc_id from bulk_data: "bulk_arc_{anime_id}_{saga_id}_{arc_id}"
                parts = bulk_data.split('_')
                saga_id = int(parts[3])
                arc_id = int(parts[4])
                
                # Get arc episode range
                sagas = await self.db.get_anime_sagas(anime_id)
                saga = next((s for s in sagas if s["id"] == saga_id), None)
                if saga:
                    arc = next((a for a in saga["arcs"] if a["id"] == arc_id), None)
                    if arc:
                        # Parse episode range (handle "Present")
                        episode_range = arc["episode_range"]
                        if "–" in episode_range:
                            start_end = episode_range.split("–")
                            try:
                                start_ep = int(start_end[0].strip())
                                # Handle "Present" as the end value
                                if start_end[1].strip().lower() == "present":
                                    end_ep = await self.get_max_episode(anime_id)
                                    if end_ep < start_ep:
                                        end_ep = start_ep
                                else:
                                    end_ep = int(start_end[1].strip())
                            except ValueError:
                                await callback_query.answer("Invalid episode range format.", show_alert=True)
                                return
                        
                        filtered_files = [f for f in all_files if start_ep <= f['episode'] <= end_ep]
                        context_info = f"arc {arc['name']}"
            
            else:
                # Regular bulk download for entire anime
                filtered_files = all_files
                context_info = anime['title']

            # FIX: If no filtered files found, show helpful message instead of error
            if not filtered_files:
                if is_saga or is_arc:
                    # For sagas/arcs, show which episodes are missing
                    if is_saga:
                        sagas = await self.db.get_anime_sagas(anime_id)
                        saga = next((s for s in sagas if s["id"] == int(parts[3])), None)
                        episode_range = saga["episode_range"] if saga else "unknown"
                        message = f"No files found for saga: {saga['name']} ({episode_range})"
                    else:
                        sagas = await self.db.get_anime_sagas(anime_id)
                        saga = next((s for s in sagas if s["id"] == int(parts[3])), None)
                        if saga:
                            arc = next((a for a in saga["arcs"] if a["id"] == int(parts[4])), None)
                            episode_range = arc["episode_range"] if arc else "unknown"
                            message = f"No files found for arc: {arc['name']} ({episode_range})"
                    
                    # Show what episodes ARE available
                    available_episodes = sorted(list({f['episode'] for f in all_files}))
                    if available_episodes:
                        message += f"\n\nAvailable episodes: {available_episodes[0]}-{available_episodes[-1]}"
                    
                    await callback_query.answer(message, show_alert=True)
                else:
                    await callback_query.answer("No files available for this selection.", show_alert=True)
                return

            # Group filtered files by quality
            quality_groups = {}
            for file in filtered_files:
                quality = file.get('quality', 'unknown').lower()
                if quality not in quality_groups:
                    quality_groups[quality] = []
                quality_groups[quality].append(file)

            # Create buttons for each quality
            buttons = []
            for quality, files in quality_groups.items():
                episodes = len({f['episode'] for f in files})
                btn_text = f"{quality.upper()} ({episodes} eps)"
                
                # Pass bulk_data in callback_data
                cb_data = f"{bulk_data}_{quality}" if bulk_data else f"bulk_{quality}_{anime_id}"
                buttons.append([InlineKeyboardButton(btn_text, callback_data=cb_data)])

            # Add back button - different based on context
            if is_saga or is_arc:
                # For saga/arc, go back to the arc list
                parts = bulk_data.split('_')
                saga_id = int(parts[3])
                back_data = f"saga_{anime_id}_{saga_id}" if is_saga else f"arc_{anime_id}_{saga_id}_{parts[4]}"
                buttons.append([
                    InlineKeyboardButton("🔙 Back", callback_data=back_data),
                    InlineKeyboardButton("❌ Close", callback_data="close_message")
                ])
            else:
                # For regular bulk, go back to anime
                buttons.append([
                    InlineKeyboardButton("🔙 Back", callback_data=f"anime_{anime_id}"),
                    InlineKeyboardButton("❌ Close", callback_data="close_message")
                ])

            reply_markup = InlineKeyboardMarkup(buttons)
            
            await self.update_message(
                client,
                callback_query.message,
                f"<b>Choose quality for {context_info}:</b>\n"
                "All available episodes will be sent to your PM",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error in show_bulk_quality_menu: {e}")
            await callback_query.answer("Error loading quality options.", show_alert=True)

    async def process_bulk_download(self, client: Client, callback_query: CallbackQuery, data: str):
        """Handle bulk download with saga/arc support"""
        user_id = callback_query.from_user.id
        
        try:
            # Parse the callback data to determine what type of bulk download this is
            parts = data.split('_')
            
            if data.startswith("bulk_saga_") and len(parts) >= 5:
                # Format: bulk_saga_{anime_id}_{saga_id}_{quality}
                anime_id = int(parts[2])
                saga_id = int(parts[3])
                quality = parts[4]
                await self.process_bulk_saga_download(client, callback_query, anime_id, saga_id, quality)
                
            elif data.startswith("bulk_arc_") and len(parts) >= 6:
                # Format: bulk_arc_{anime_id}_{saga_id}_{arc_id}_{quality}
                anime_id = int(parts[2])
                saga_id = int(parts[3])
                arc_id = int(parts[4])
                quality = parts[5]
                await self.process_bulk_arc_download(client, callback_query, anime_id, saga_id, arc_id, quality)
                
            elif data.startswith("bulk_") and len(parts) >= 3:
                # Format: bulk_{quality}_{anime_id}
                quality = parts[1]
                anime_id = int(parts[2])
                await self._process_regular_bulk_download(client, callback_query, anime_id, quality)
                
            else:
                await callback_query.answer("Invalid bulk download request.", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error in process_bulk_download: {e}")
            await callback_query.answer("Error processing bulk download.", show_alert=True)


    async def process_bulk_saga_download(self, client: Client, callback_query: CallbackQuery, anime_id: int, saga_id: int, quality: str):
        """Process bulk download for a specific saga"""
        user_id = callback_query.from_user.id
        files_exist, message = await self.check_saga_arc_files_exist(anime_id, saga_id)
        if not files_exist:
            await callback_query.answer(message, show_alert=True)
            return
        # Check download limits first
        if self.config.PREMIUM_MODE:
            can_download, limit_msg = await self.check_download_limit(user_id)
            if not can_download:
                await callback_query.answer(limit_msg, show_alert=True)
                return
        
        # Get saga information
        sagas = await self.db.get_anime_sagas(anime_id)
        saga = next((s for s in sagas if s["id"] == saga_id), None)
        
        if not saga:
            await callback_query.answer("Saga not found.", show_alert=True)
            return
        
        # Parse episode range
        start_ep, end_ep = map(int, saga["episode_range"].split("–"))
        
        # Get all files for this saga and quality
        all_files = []
        for db_client in self.db.anime_clients:
            try:
                db = db_client[self.db.db_name]
                files = await db.files.find({
                    "anime_id": anime_id,
                    "episode": {"$gte": start_ep, "$lte": end_ep},
                    "quality": quality.lower()
                }).sort("episode", 1).to_list(None)
                if files:
                    all_files.extend(files)
            except Exception as e:
                logger.error(f"Error fetching files from cluster: {str(e)}")
                continue

        if not all_files:
            await callback_query.answer(f"No {quality.upper()} episodes found for this saga!", show_alert=True)
            return
        
        # Continue with the download process (use your existing download logic)
        await self._execute_bulk_download(client, callback_query, anime_id, quality, all_files)


    async def process_bulk_arc_download(self, client: Client, callback_query: CallbackQuery, anime_id: int, saga_id: int, arc_id: int, quality: str):
        """Process bulk download for a specific arc"""
        user_id = callback_query.from_user.id
        files_exist, message = await self.check_saga_arc_files_exist(anime_id, saga_id, arc_id)
        if not files_exist:
            await callback_query.answer(message, show_alert=True)
            return
        # Check download limits first
        if self.config.PREMIUM_MODE:
            can_download, limit_msg = await self.check_download_limit(user_id)
            if not can_download:
                await callback_query.answer(limit_msg, show_alert=True)
                return
        
        # Get arc information
        sagas = await self.db.get_anime_sagas(anime_id)
        saga = next((s for s in sagas if s["id"] == saga_id), None)
        if not saga:
            await callback_query.answer("Saga not found.", show_alert=True)
            return
            
        arc = next((a for a in saga["arcs"] if a["id"] == arc_id), None)
        if not arc:
            await callback_query.answer("Arc not found.", show_alert=True)
            return
        
        # Parse episode range
        start_ep, end_ep = map(int, arc["episode_range"].split("–"))
        
        # Get all files for this arc and quality
        all_files = []
        for db_client in self.db.anime_clients:
            try:
                db = db_client[self.db.db_name]
                files = await db.files.find({
                    "anime_id": anime_id,
                    "episode": {"$gte": start_ep, "$lte": end_ep},
                    "quality": quality.lower()
                }).sort("episode", 1).to_list(None)
                if files:
                    all_files.extend(files)
            except Exception as e:
                logger.error(f"Error fetching files from cluster: {str(e)}")
                continue

        if not all_files:
            await callback_query.answer(f"No {quality.upper()} episodes found for this arc!", show_alert=True)
            return
        
        # Continue with the download process
        await self._execute_bulk_download(client, callback_query, anime_id, quality, all_files)


    async def _process_regular_bulk_download(self, client: Client, callback_query: CallbackQuery, anime_id: int, quality: str):
        """Process regular bulk download for entire anime"""
        user_id = callback_query.from_user.id
        
        # Check download limits first
        if self.config.PREMIUM_MODE:
            can_download, limit_msg = await self.check_download_limit(user_id)
            if not can_download:
                await callback_query.answer(limit_msg, show_alert=True)
                return
        
        # Get all files for this anime and quality
        all_files = []
        for db_client in self.db.anime_clients:
            try:
                db = db_client[self.db.db_name]
                files = await db.files.find({
                    "anime_id": anime_id,
                    "quality": quality.lower()
                }).sort("episode", 1).to_list(None)
                if files:
                    all_files.extend(files)
            except Exception as e:
                logger.error(f"Error fetching files from cluster: {str(e)}")
                continue

        if not all_files:
            await callback_query.answer(f"No {quality.upper()} episodes found!", show_alert=True)
            return
        
        # Continue with the download process
        await self._execute_bulk_download(client, callback_query, anime_id, quality, all_files)


    async def _execute_bulk_download(self, client: Client, callback_query: CallbackQuery, anime_id: int, quality: str, files: list):
        """Execute the actual bulk download process"""
        user_id = callback_query.from_user.id
        anime = await self.db.find_anime(anime_id)

        # Send processing message
        processing_msg = await callback_query.message.reply_text(
            f"⏳ Preparing to send {len(files)} {quality.upper()} episodes of {anime['title']}..."
        )

        success_count = 0
        errors = []

        for file_info in files:
            try:
                # Adult/premium check per file
                if file_info.get('is_adult'):
                    if self.config.RESTRICT_ADULT and not await self.premium.check_access(user_id, 'hpremium'):
                        errors.append(f"Ep {file_info.get('episode')} (Adult)")
                        continue
                    elif self.config.PREMIUM_MODE and not await self.premium.check_access(user_id, 'premium'):
                        errors.append(f"Ep {file_info.get('episode')} (Premium)")
                        continue

                # Fetch the original message containing the file
                msg = await client.get_messages(
                    chat_id=file_info['chat_id'],
                    message_ids=file_info['message_id']
                )
                if not msg:
                    errors.append(f"Ep {file_info.get('episode')} (Missing)")
                    continue

                # Caption
                caption = (
                    f"🎬 <b>{anime['title']} - Episode {file_info['episode']} "
                    f"[{file_info['quality'].upper()}]</b>\n"
                    f"💾 <b>Size:</b> {file_info['file_size']}"
                )

                # Send file
                try:
                    if file_info['file_type'] == 'video':
                        sent_msg = await client.send_video(
                            chat_id=user_id,
                            video=msg.video.file_id,
                            caption=caption,
                            parse_mode=enums.ParseMode.HTML,
                            protect_content=Config.PROTECT_CONTENT
                        )
                    else:
                        sent_msg = await client.send_document(
                            chat_id=user_id,
                            document=msg.document.file_id,
                            caption=caption,
                            parse_mode=enums.ParseMode.HTML,
                            protect_content=Config.PROTECT_CONTENT
                        )

                    # Schedule auto-deletion
                    asyncio.create_task(
                        self.delete_message_after_delay(
                            client,
                            user_id,
                            sent_msg.id,
                            Config.DELETE_TIMER_MINUTES * 60
                        )
                    )

                    # Update stats
                    await self.update_stats("total_downloads")
                    success_count += 1
                    await self.db.users_collection.update_one(
                        {"user_id": user_id},
                        {"$inc": {"download_count": 1}}
                    )

                    # Small delay between sends
                    await asyncio.sleep(0.5)

                except Exception as send_error:
                    logger.error(f"Failed to send episode {file_info.get('episode')}: {send_error}")
                    errors.append(f"Ep {file_info.get('episode')} (Send Failed)")
                    continue

            except Exception as file_error:
                logger.error(f"Error processing file {file_info.get('_id')}: {file_error}")
                errors.append(f"Ep {file_info.get('episode')} (Error)")
                continue

        # Send final summary
        try:
            await processing_msg.delete()

            result_msg = (
                f"<blockquote>\n"
                f"Successfully sent {success_count}/{len(files)} episodes!<br>\n"
                f"Files will auto-delete in {Config.DELETE_TIMER_MINUTES} minute(s).\n"
                f"</blockquote>"
            )

            if errors:
                result_msg += f"\n\nFailed episodes: {', '.join(errors[:10])}" + ("..." if len(errors) > 10 else "")

            await client.send_message(chat_id=user_id, text=result_msg)

            if callback_query.message.chat.type != ChatType.PRIVATE:
                await callback_query.answer(
                    f"📤 Sent {success_count}/{len(files)} episodes to your PM!",
                    show_alert=True
                )

        except Exception as final_error:
            logger.error(f"Error sending final message: {final_error}")
    async def _process_bulk_saga_download(self, client: Client, callback_query: CallbackQuery, anime_id: int, saga_id: int, quality: str):
        """Process bulk download for a specific saga with quality"""
        user_id = callback_query.from_user.id
        
        # Check download limits first
        if self.config.PREMIUM_MODE:
            can_download, limit_msg = await self.check_download_limit(user_id)
            if not can_download:
                await callback_query.answer(limit_msg, show_alert=True)
                return
        
        # Get saga information
        sagas = await self.db.get_anime_sagas(anime_id)
        saga = next((s for s in sagas if s["id"] == saga_id), None)
        
        if not saga:
            await callback_query.answer("Saga not found.", show_alert=True)
            return
        
        # Parse episode range (handle "Present")
        episode_range = saga["episode_range"]
        if "–" in episode_range:
            start_end = episode_range.split("–")
            try:
                start_ep = int(start_end[0].strip())
                # Handle "Present" as the end value
                if start_end[1].strip().lower() == "present":
                    # For ongoing sagas, get the current max episode from database
                    end_ep = await self.get_max_episode(anime_id)
                    # If no episodes found, use start_ep as both start and end
                    if end_ep < start_ep:
                        end_ep = start_ep
                else:
                    end_ep = int(start_end[1].strip())
            except ValueError:
                await callback_query.answer("Invalid episode range format.", show_alert=True)
                return
        else:
            await callback_query.answer("Invalid episode range format.", show_alert=True)
            return
        
        # Get all files for this saga and quality
        all_files = []
        for db_client in self.db.anime_clients:
            try:
                db = db_client[self.db.db_name]
                files = await db.files.find({
                    "anime_id": anime_id,
                    "episode": {"$gte": start_ep, "$lte": end_ep},
                    "quality": quality.lower()
                }).sort("episode", 1).to_list(None)
                if files:
                    all_files.extend(files)
            except Exception as e:
                logger.error(f"Error fetching files from cluster: {str(e)}")
                continue

        if not all_files:
            await callback_query.answer(f"No {quality.upper()} episodes found for this saga!", show_alert=True)
            return
        
        # Continue with the download process
        await self._execute_bulk_download(client, callback_query, anime_id, quality, all_files)


    async def _process_bulk_arc_download(self, client: Client, callback_query: CallbackQuery, anime_id: int, saga_id: int, arc_id: int, quality: str):
        """Process bulk download for a specific arc with quality"""
        user_id = callback_query.from_user.id
        
        # Check download limits first
        if self.config.PREMIUM_MODE:
            can_download, limit_msg = await self.check_download_limit(user_id)
            if not can_download:
                await callback_query.answer(limit_msg, show_alert=True)
                return
        
        # Get arc information
        sagas = await self.db.get_anime_sagas(anime_id)
        saga = next((s for s in sagas if s["id"] == saga_id), None)
        if not saga:
            await callback_query.answer("Saga not found.", show_alert=True)
            return
            
        arc = next((a for a in saga["arcs"] if a["id"] == arc_id), None)
        if not arc:
            await callback_query.answer("Arc not found.", show_alert=True)
            return
        
        # Parse episode range (handle "Present")
        episode_range = arc["episode_range"]
        if "–" in episode_range:
            start_end = episode_range.split("–")
            try:
                start_ep = int(start_end[0].strip())
                # Handle "Present" as the end value
                if start_end[1].strip().lower() == "present":
                    # For ongoing arcs, get the current max episode from database
                    end_ep = await self.get_max_episode(anime_id)
                    # If no episodes found, use start_ep as both start and end
                    if end_ep < start_ep:
                        end_ep = start_ep
                else:
                    end_ep = int(start_end[1].strip())
            except ValueError:
                await callback_query.answer("Invalid episode range format.", show_alert=True)
                return
        else:
            await callback_query.answer("Invalid episode range format.", show_alert=True)
            return
        
        # Get all files for this arc and quality
        all_files = []
        for db_client in self.db.anime_clients:
            try:
                db = db_client[self.db.db_name]
                files = await db.files.find({
                    "anime_id": anime_id,
                    "episode": {"$gte": start_ep, "$lte": end_ep},
                    "quality": quality.lower()
                }).sort("episode", 1).to_list(None)
                if files:
                    all_files.extend(files)
            except Exception as e:
                logger.error(f"Error fetching files from cluster: {str(e)}")
                continue

        if not all_files:
            await callback_query.answer(f"No {quality.upper()} episodes found for this arc!", show_alert=True)
            return
        
        # Continue with the download process
        await self._execute_bulk_download(client, callback_query, anime_id, quality, all_files)
    async def show_episode_options(self, client: Client, callback_query: CallbackQuery, anime_id: int, episode: int):
        user_id = callback_query.from_user.id
        if user_id not in self.user_sessions or 'current_anime' not in self.user_sessions[user_id]:
            await callback_query.answer("Session expired. Please search again.", show_alert=True)
            return
        
        anime = self.user_sessions[user_id]['current_anime']
        
        try:
            episode_files = await self.db.find_files(anime_id, episode)
            
            if not episode_files:
                await callback_query.answer("No files available for this episode.", show_alert=True)
                return
            
            self.user_sessions[user_id]['current_episode'] = episode
            
            quality_groups = {}
            for file in episode_files:
                quality = file['quality'].lower()
                if quality not in quality_groups:
                    quality_groups[quality] = []
                quality_groups[quality].append(file)
            
            buttons = []
            for quality, files in quality_groups.items():
                lang_text = f" [{files[0].get('language', '').upper()}]" if files[0].get('language') else ""
                btn_text = f"{quality.upper()}{lang_text} ({files[0]['file_size']})"
                
                buttons.append([
                    InlineKeyboardButton(
                        f"▶️ {btn_text} ",
                        callback_data=f"dl_{files[0]['_id']}"
                    )
                ])
            
            nav_buttons = []
            if episode > 1:
                nav_buttons.append(InlineKeyboardButton("• ⬅️ ᴘʀᴇᴠ ᴇᴘ •", callback_data=f"ep_{anime_id}_{episode-1}"))
            if episode < (anime.get('episodes', episode + 1)):
                nav_buttons.append(InlineKeyboardButton("• ➡️ ɴᴇxᴛ ᴇᴘ •", callback_data=f"ep_{anime_id}_{episode+1}"))
            if nav_buttons:
                buttons.append(nav_buttons)
            
            buttons.append([
                InlineKeyboardButton(
                    "• 🔙 ʙᴀᴄᴋ ᴛᴏ ᴇᴘ •", 
                    callback_data=f"episodes_{anime_id}_{self.user_sessions[user_id].get('episodes_page', 1)}"
                ),
                InlineKeyboardButton("• ᴄʟᴏꜱᴇ •", callback_data="close_message")
            ])
            
            await self.update_message(
                client,
                callback_query.message,
                f"<blockquote>📺 <b>{anime['title']} - Episode {episode}</b></blockquote>\n"
                "<b>Select quality to download:</b>",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            logger.error(f"Error fetching episode files: {e}")
            await callback_query.answer("⚠️ Error fetching files.", show_alert=True)   
    async def process_file_download(self, client: Client, message: Message, file_id: str):
        """Handle file downloads with proper restrictions and error handling"""
        user_id = message.from_user.id
        
        try:
            # Search for the file across all clusters
            file_info = None
            for db_client in self.db.anime_clients:
                try:
                    db = db_client[self.db.db_name]
                    found = await db.files.find_one({"_id": ObjectId(file_id)})
                    if found:
                        file_info = found
                        break
                except Exception as e:
                    logger.warning(f"Error searching for file in cluster {db_client}: {str(e)}")
                    continue

            if not file_info:
                await message.reply("❌ File not found or link expired")
                return

            # Check adult content restrictions
            if file_info.get('is_adult'):
                if self.config.RESTRICT_ADULT:
                    if not await self.premium.check_access(user_id, 'hpremium'):
                        await message.reply(
                            "🔞 Adult content requires H-Premium subscription!",
                            disable_web_page_preview=True
                        )
                        return
                elif self.config.PREMIUM_MODE:
                    if not await self.premium.check_access(user_id, 'premium'):
                        await message.reply(
                            "🔒 Content requires premium subscription!",
                            disable_web_page_preview=True
                        )
                        return
            
            # Check download limits if premium mode is ON
            if self.config.PREMIUM_MODE:
                can_download, limit_msg = await self.check_download_limit(user_id)
                if not can_download:
                    await message.reply(limit_msg, disable_web_page_preview=True)
                    return

            # Fetch original message
            try:
                msg = await client.get_messages(
                    chat_id=file_info['chat_id'],
                    message_ids=file_info['message_id']
                )
                if not msg:
                    raise ValueError("Original message not found")
            except Exception as e:
                logger.error(f"Error fetching original message: {str(e)}")
                await message.reply("❌ Error fetching file. Please try again.")
                return

            # Prepare caption
            file_caption = (
                f"<b>🎬 {file_info.get('anime_title', 'Unknown')} - Episode {file_info['episode']} "
                f"[{file_info['quality'].upper()}]</b>\n"
                f"<b>💾 Size:</b> {file_info['file_size']}"
            )

            # Function to send file
            async def send_file(chat_id):
                try:
                    if file_info['file_type'] == 'video':
                        return await client.send_video(
                            chat_id=chat_id,
                            video=msg.video.file_id,
                            caption=file_caption,
                            parse_mode=enums.ParseMode.HTML,
                            protect_content=Config.PROTECT_CONTENT
                        )
                    else:
                        return await client.send_document(
                            chat_id=chat_id,
                            document=msg.document.file_id,
                            caption=file_caption,
                            parse_mode=enums.ParseMode.HTML,
                            protect_content=Config.PROTECT_CONTENT
                        )
                except Exception as e:
                    logger.error(f"Error sending file: {str(e)}")
                    raise

            # Try sending to private chat first
            try:
                sent_file_msg = await send_file(user_id)
                warning_msg = await client.send_message(
                    chat_id=user_id,
                    text = f"""
                        <blockquote>
                        ⚠️ This file will auto-delete in {Config.DELETE_TIMER_MINUTES} minute(s).
                        </blockquote>
                        """,
                    parse_mode=enums.ParseMode.HTML
                )

                if message.chat.type != ChatType.PRIVATE:
                    await message.reply("📤 File sent to your private chat!")

            except Exception as private_error:
                logger.warning(f"Failed to send to PM ({str(private_error)}), trying group...")
                try:
                    sent_file_msg = await send_file(message.chat.id)
                    warning_msg = await client.send_message(
                        chat_id=message.chat.id,
                        text=f"⚠️ This file will auto-delete in {Config.DELETE_TIMER_MINUTES} minute(s).",
                        parse_mode=enums.ParseMode.HTML
                    )
                except Exception as group_error:
                    logger.error(f"Failed to send to group: {str(group_error)}")
                    await message.reply("❌ Failed to send file. Please try again.")
                    return

            # Schedule deletion
            async def delete_messages():
                try:
                    await asyncio.sleep(Config.DELETE_TIMER_MINUTES * 60)
                    await sent_file_msg.delete()
                    await warning_msg.delete()
                except Exception as e:
                    logger.warning(f"Error deleting messages: {str(e)}")

            asyncio.create_task(delete_messages())

            # Update stats
            await self.db.users_collection.update_one(
                {"user_id": user_id},
                {"$inc": {"download_count": 1}}
            )

            await self.update_stats("total_downloads")

        except Exception as main_error:
            logger.error(f"File download failed: {str(main_error)}")
            await message.reply("❌ An error occurred while processing your download")

          
    async def download_episode_file(self, client: Client, callback_query: CallbackQuery, file_id: str):
        """Handle file downloads from callback queries"""
        user_id = callback_query.from_user.id
        # Force sub check
        if not await check_force_sub(client, user_id, callback_query.message):
            return
        try:
            # Handle bulk download requests
            if file_id.startswith("bulk_"):
                parts = file_id.split('_')
                if len(parts) >= 3:
                    quality = parts[1]
                    anime_id = int(parts[2])
                    anime = await self.db.find_anime(anime_id)
                    if not anime:
                        await callback_query.answer("❌ Anime not found!", show_alert=True)
                        return

                    if anime.get('is_releasing'):
                        await callback_query.answer(
                            "⚠️ This anime is still releasing. Episodes may be added later.",
                            show_alert=True
                        )
                    return await self.process_bulk_download(client, callback_query, anime_id, quality)
                else:
                    await callback_query.answer("⚠️ Invalid bulk download link", show_alert=True)
                    return

            # Search for file across all clusters
            file_info = None
            for db_client in self.db.anime_clients:
                try:
                    db = db_client[self.db.db_name]
                    found = await db.files.find_one({"_id": ObjectId(file_id)})
                    if found:
                        file_info = found
                        break
                except Exception as e:
                    logger.warning(f"Error searching in cluster {db_client}: {str(e)}")
                    continue

            if not file_info:
                await callback_query.answer("❌ File not found", show_alert=True)
                return

            # Check restrictions
            if file_info.get('is_adult'):
                if self.config.RESTRICT_ADULT:
                    if not await self.premium.check_access(user_id, 'hpremium'):
                        await callback_query.answer(
                            "🔞 Adult content requires H-Premium!",
                            show_alert=True
                        )
                        return
                elif self.config.PREMIUM_MODE:
                    if not await self.premium.check_access(user_id, 'premium'):
                        await callback_query.answer(
                            "🔒 Premium subscription required!",
                            show_alert=True
                        )
                        return

            if self.config.PREMIUM_MODE:
                can_download, limit_msg = await self.check_download_limit(user_id)
                if not can_download:
                    await callback_query.answer(limit_msg, show_alert=True)
                    return

            # Fetch and send file
            try:
                msg = await client.get_messages(
                    chat_id=file_info['chat_id'],
                    message_ids=file_info['message_id']
                )
                if not msg:
                    raise ValueError("Original message missing")

                caption = (
                    f"<b>🎬 {file_info.get('anime_title', 'Unknown')} - Episode {file_info['episode']} "
                    f"[{file_info['quality'].upper()}]</b>\n"
                    f"<b>💾 Size:</b> {file_info['file_size']}"
                )

                # Try private chat first
                try:
                    if file_info['file_type'] == 'video':
                        sent_msg = await client.send_video(
                            chat_id=user_id,
                            video=msg.video.file_id,
                            caption=caption,
                            parse_mode=enums.ParseMode.HTML,
                            protect_content=Config.PROTECT_CONTENT
                        )
                    else:
                        sent_msg = await client.send_document(
                            chat_id=user_id,
                            document=msg.document.file_id,
                            caption=caption,
                            parse_mode=enums.ParseMode.HTML,
                            protect_content=Config.PROTECT_CONTENT
                        )

                    warning_msg = await client.send_message(
                        chat_id=user_id,
                        text = f"""
                        <blockquote>
                        ⚠️ This file will auto-delete in {Config.DELETE_TIMER_MINUTES} minute(s).
                        </blockquote>
                        """,
                        parse_mode=enums.ParseMode.HTML
                    )

                    if callback_query.message.chat.type != ChatType.PRIVATE:
                        await callback_query.answer("📤 Sent to your private chat!", show_alert=True)

                except Exception as private_error:
                    logger.warning(f"PM send failed ({str(private_error)}), trying group...")
                    if file_info['file_type'] == 'video':
                        sent_msg = await client.send_video(
                            chat_id=callback_query.message.chat.id,
                            video=msg.video.file_id,
                            caption=caption,
                            parse_mode=enums.ParseMode.HTML
                        )
                    else:
                        sent_msg = await client.send_document(
                            chat_id=callback_query.message.chat.id,
                            document=msg.document.file_id,
                            caption=caption,
                            parse_mode=enums.ParseMode.HTML
                        )

                    warning_msg = await client.send_message(
                        chat_id=callback_query.message.chat.id,
                        text = f"""
                        <blockquote>
                        ⚠️ This file will auto-delete in {Config.DELETE_TIMER_MINUTES} minute(s).
                        </blockquote>
                        """,
                        parse_mode=enums.ParseMode.HTML
                    )

                # Schedule deletion
                async def delete_messages():
                    await asyncio.sleep(Config.DELETE_TIMER_MINUTES * 60)
                    try:
                        await sent_msg.delete()
                        await warning_msg.delete()
                    except:
                        pass

                asyncio.create_task(delete_messages())

                # Update stats
                await self.db.users_collection.update_one(
                    {"user_id": user_id},
                    {"$inc": {"download_count": 1}}
                )

                await self.update_stats("total_downloads")

            except Exception as e:
                logger.error(f"File send failed: {str(e)}")
                await callback_query.answer("❌ Failed to send file", show_alert=True)

        except Exception as main_error:
            logger.critical(f"Download failed: {str(main_error)}")
            await callback_query.answer("❌ Download error occurred", show_alert=True)

    async def ongoing_command(self, client: Client, message: Message, page: int = 1):
        """Show paginated list of currently releasing anime"""
        try:
            ITEMS_PER_PAGE = 10  # Number of items per page
            
            # Search across all clusters for anime with status "RELEASING"
            releasing_anime = []
            for db_client in self.db.anime_clients:
                try:
                    db = db_client[self.db.db_name]
                    cluster_results = await db.anime.find(
                        {"status": "RELEASING"},
                        {"id": 1, "title": 1, "episodes": 1, "last_updated": 1}
                    ).sort("last_updated", -1).to_list(None)
                    releasing_anime.extend(cluster_results)
                except Exception as e:
                    logger.warning(f"Error fetching releasing anime from cluster: {e}")
                    continue

            # Deduplicate
            seen_ids = set()
            unique_anime = []
            for anime in releasing_anime:
                if anime["id"] not in seen_ids:
                    seen_ids.add(anime["id"])
                    unique_anime.append(anime)

            if not unique_anime:
                await message.reply_text("ℹ️ No currently releasing anime found.")
                return

            # Calculate pagination
            total_pages = (len(unique_anime) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
            page = max(1, min(page, total_pages))  # Clamp page to valid range
            start_idx = (page - 1) * ITEMS_PER_PAGE
            end_idx = start_idx + ITEMS_PER_PAGE
            page_anime = unique_anime[start_idx:end_idx]

            # Create keyboard buttons
            keyboard = []
            for anime in page_anime:
                try:
                    total_uploaded = await self.db.count_episodes(anime["id"], count_unique=True)
                except Exception as e:
                    logger.warning(f"Error counting episodes for anime {anime['id']}: {e}")
                    total_uploaded = 0

                btn_text = f"{anime['title']} ({total_uploaded}/{anime.get('episodes', '?')})"
                keyboard.append([
                    InlineKeyboardButton(btn_text, callback_data=f"anime_{anime['id']}")
                ])
            # Pagination controls
            pagination_buttons = []
            if page > 1:
                pagination_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"ongoing_page_{page-1}"))
            
            pagination_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
            
            if page < total_pages:
                pagination_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"ongoing_page_{page+1}"))

            if pagination_buttons:
                keyboard.append(pagination_buttons)

            keyboard.append([
                InlineKeyboardButton("🔙 Back", callback_data="start_menu"),
                InlineKeyboardButton("❌ Close", callback_data="close_message")
            ])

            # Try to edit if it's a callback, otherwise send new message
            if isinstance(message, CallbackQuery):
                await self.update_message(
                    client,
                    message.message,
                    f"<blockquote>🔄 Currently Releasing Anime (Page {page}/{total_pages}):</blockquote>\n"
                    f"<blockquote>Numbers show uploaded/total episodes</blockquote>\n"
                    f"<blockquote>Select an anime to view details:</blockquote>",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await message.reply_text(
                    f"<blockquote>🔄 Currently Releasing Anime (Page {page}/{total_pages}):</blockquote>\n"
                    f"<blockquote>Numbers show uploaded/total episodes</blockquote>\n"
                    f"<blockquote>Select an anime to view details:</blockquote>",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )


        except Exception as e:
            logger.error(f"Error in ongoing_command: {e}")
            error_msg = "⚠️ Error loading ongoing anime list. Please try again."
            if isinstance(message, CallbackQuery):
                await message.answer(error_msg, show_alert=True)
            else:
                await message.reply_text(error_msg)
    async def admin_panel(self, client: Client, callback_query: CallbackQuery):
        try:
            if callback_query.from_user.id not in Config.ADMINS:
                await callback_query.answer("You don't have permission", show_alert=True)
                return

            keyboard = [
                [
                    InlineKeyboardButton("➕ Add Anime", callback_data="admin_add_anime"),
                    InlineKeyboardButton("✏️ Edit Anime", callback_data="admin_edit_anime")
                ],
                [
                    InlineKeyboardButton("🗑️ Delete Anime", callback_data="admin_delete_anime"),
                    InlineKeyboardButton("📁 Add Episodes", callback_data="admin_add_episodes")
                ],
                [
                    InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")
                ],
                [
                    InlineKeyboardButton("💎 Premium", callback_data="premium_management"),
                    InlineKeyboardButton("🔒 Restrictions", callback_data="restrict_settings")
                ],
                [
                    InlineKeyboardButton("📂 Add DB Channel", callback_data="admin_add_db_channel"),
                    InlineKeyboardButton("🗑 Remove DB Channel", callback_data="admin_remove_db_channel")
                ],
                [
                    InlineKeyboardButton("📮 View Requests", callback_data="requests_page:1"),
                    InlineKeyboardButton("📢 Force Subscription", callback_data="force_sub_settings")

                ],
                [
                    InlineKeyboardButton("🔗 Link Sequel", callback_data="admin_link_sequel"),
                    InlineKeyboardButton("🆔 View IDs", callback_data="admin_view_ids")
                ]
            ]

            if callback_query.from_user.id in Config.OWNERS:
                keyboard.append([
                    InlineKeyboardButton("👑 Owner Tools", callback_data="owner_tools")
                ])

            keyboard.append([
                InlineKeyboardButton("🔙 Back", callback_data="start_menu"),
                InlineKeyboardButton("❌ Close", callback_data="close_message")
            ])

            await self.update_message(
                client,
                callback_query.message,
                "👑 Admin Panel - Select an option:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Error showing admin panel: {e}")
            await callback_query.answer("Error opening admin panel", show_alert=True)

    async def owner_tools(self, client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        if user_id not in Config.OWNERS:
            await callback_query.answer("❌ Owner only", show_alert=True)
            return

        try:
            message = "👑 Owner Tools\n\n"
            message += "⚠️ These actions are powerful and irreversible!\n\n"
            message += f"Current Owners: {len(Config.OWNERS)}\n"
            message += f"Current Admins: {len(Config.ADMINS)}\n"
            message += f"To unlink sequals use /unlinksequel\n"
            message += f"use /restart to restart bot \n"
            message += f"use /setlimit to set limits \n"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("👑 Add Owner", callback_data="owner_add"),
                 InlineKeyboardButton("🚫 Remove Owner", callback_data="owner_remove")],

                [InlineKeyboardButton("👑 Add Admin", callback_data="admin_add_admin"),
                 InlineKeyboardButton("❌ Remove Admin", callback_data="admin_remove_admin")],

                [InlineKeyboardButton("📜 List Owners", callback_data="list_owners"),
                 InlineKeyboardButton("👥 List Admins", callback_data="owner_list_admins")],

       #         [InlineKeyboardButton("📨 Rate Limit", callback_data="set_rate_limit")],
          #       InlineKeyboardButton("♻️ Reset Database", callback_data="owner_reset_db")],

                [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel"),
                 InlineKeyboardButton("❌ Close", callback_data="close_message")]
            ])

            await callback_query.message.edit_text(
                message,
                reply_markup=keyboard
            )
            await callback_query.answer()

        except Exception as e:
            logger.error(f"Owner tools error: {e}")
            await callback_query.answer("⚠️ Error loading owner tools", show_alert=True)
    async def admin_settings(self, client: Client, callback_query: CallbackQuery):
        """Display settings menu"""
        if callback_query.from_user.id not in self.config.ADMINS:
            await callback_query.answer("❌ Admin only", show_alert=True)
            return
        
        # Get current settings from DB
        stats = await self.db.stats_collection.find_one({"type": "global"})
        settings = stats.get("settings", {})
        
        # Build settings message
        message = ["⚙️ <b>Bot Settings</b>\n"]
        for key, meta in self.settings.items():
            current = getattr(self.config, meta['config_attr'], settings.get(key))
            if meta['type'] == bool:
                message.append(f"• {meta['name']}: {'✅ Enabled' if current else '❌ Disabled'}")
            else:
                message.append(f"• {meta['name']}: {current} {meta.get('unit', '')}")
        
        # Create buttons for each setting
        keyboard = []
        row = []
        for i, key in enumerate(self.settings.keys()):
            row.append(InlineKeyboardButton(self.settings[key]['name'], callback_data=f"set_{key}"))
            if (i + 1) % 2 == 0 or i == len(self.settings) - 1:
                keyboard.append(row)
                row = []
        
        # Add navigation buttons
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_settings"),
            InlineKeyboardButton("🔙 Back", callback_data="admin_panel")
        ])
        
        await callback_query.message.edit_text(
            "\n".join(message),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=enums.ParseMode.HTML
        )
    async def handle_setting_text(self, client: Client, message: Message):
        user_id = message.from_user.id
        session = self.user_sessions.get(user_id, {})
        
        if session.get('action') != 'changing_setting':
            return
            
        if message.text == '/cancel':
            await self.clear_user_session(user_id)
            await message.reply_text("❌ Setting change cancelled")
            return await self.admin_settings(client, message)
            
        setting_key = session.get('setting')
        if not setting_key:
            return
            
        try:
            new_value = await self.save_setting(user_id, setting_key, message.text)
            meta = self.settings[setting_key]
            
            reply = (f"✅ Successfully updated:\n\n"
                    f"{meta['name']} → {new_value} {meta.get('unit', '')}")
            
            await self.clear_user_session(user_id)
            
            await message.reply_text(
                reply,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Settings", callback_data="admin_settings")]
                ])
            )
        except ValueError as e:
            await message.reply_text(f"❌ Invalid value: {str(e)}\nPlease try again or /cancel")
        except Exception as e:
            logger.error(f"Error saving setting: {e}")
            await message.reply_text("❌ Error saving setting. Please try again.")
    async def change_setting(self, client: Client, callback_query: CallbackQuery, setting_key: str):
        if callback_query.from_user.id not in Config.ADMINS:
            await callback_query.answer("❌ Admin only", show_alert=True)
            return
        
        if setting_key not in self.settings:
            await callback_query.answer("⚠️ Invalid setting", show_alert=True)
            return
        
        meta = self.settings[setting_key]
        current = getattr(self.config, meta['config_attr'])
        
        self.user_sessions[callback_query.from_user.id] = {
            'action': 'changing_setting',
            'setting': setting_key
        }
        
        if meta['type'] == bool:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Enable", callback_data=f"setval_{setting_key}_True"),
                    InlineKeyboardButton("❌ Disable", callback_data=f"setval_{setting_key}_False")
                ],
                [InlineKeyboardButton("🔙 Cancel", callback_data="admin_settings")]
            ])
            
            message = (
                f"⚙️ <b>{meta['name']}</b>\n\n"
                f"Current: {'✅ Enabled' if current else '❌ Disabled'}\n\n"
                f"Select new value:"
            )
        else:
            message = (
                f"⚙️ <b>{meta['name']}</b>\n\n"
                f"Current: {current} {meta.get('unit', '')}\n"
                f"Range: {meta['min']}-{meta['max']}\n\n"
                f"Please send the new value or /cancel"
            )
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="admin_settings")]])
        
        await callback_query.message.edit_text(
            message,
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.HTML
        )
    async def save_setting(self, user_id: int, setting_key: str, value):
        """Save setting to database and update config"""
        if setting_key not in self.settings:
            raise ValueError("Invalid setting key")
        
        meta = self.settings[setting_key]

        # Validate value
        if meta['type'] == bool:
            lowered = str(value).strip().lower()
            if lowered in ('1', 'true', 'on', 'yes'):
                value = True
            elif lowered in ('0', 'false', 'off', 'no'):
                value = False
            else:
                raise ValueError("Enter a valid boolean value: on/off, true/false, 1/0")
        else:
            value = meta['type'](value)
            if not (meta['min'] <= value <= meta['max']):
                raise ValueError(f"Value must be between {meta['min']}-{meta['max']}")
        
        # Update database
        await self.db.stats_collection.update_one(
            {"type": "global"},
            {"$set": {f"settings.{setting_key}": value}},
            upsert=True
        )
        
        # Update config
        setattr(self.config, meta['config_attr'], value)
        
        return value


    async def handle_setting_callback(self, client: Client, callback_query: CallbackQuery):
        """Handle setting-related callbacks"""
        data = callback_query.data
        user_id = callback_query.from_user.id
        
        if data.startswith("set_"):
            setting_key = data[4:]
            await self.change_setting(client, callback_query, setting_key)
        
        elif data.startswith("setval_"):
            _, setting_key, value = data.split("_")
            try:
                new_value = await self.save_setting(user_id, setting_key, value)
                meta = self.settings[setting_key]
                
                if meta['type'] == bool:
                    value_display = '✅ Enabled' if new_value else '❌ Disabled'
                else:
                    value_display = f"{new_value} {meta.get('unit', '')}"
                
                await callback_query.message.edit_text(
                    f"✅ Successfully updated:\n\n"
                    f"{meta['name']} → {value_display}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back to Settings", callback_data="admin_settings")]
                    ])
                )
                
            except Exception as e:
                logger.error(f"Error saving setting: {e}")
                await callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)
        
        elif data == "admin_settings":
            await self.admin_settings(client, callback_query)
    async def handle_admin_text(self, client: Client, message: Message):
        user_id = message.from_user.id
        session = self.user_sessions.get(user_id, {})
        
        if session.get('action') != 'changing_setting':
            return  # Not in setting change mode
        
        if message.text == '/cancel':
            del self.user_sessions[user_id]
            await message.reply_text("❌ Setting change cancelled")
            return await self.admin_settings(client, message)
        
        setting_key = session['setting']
        try:
            new_value = await self.save_setting(user_id, setting_key, message.text)
            meta = self.settings[setting_key]
            
            reply = (f"✅ Successfully updated:\n\n"
                    f"{meta['name']} → {new_value} {meta.get('unit', '')}")
            
            del self.user_sessions[user_id]  # Clear the session
            
            await message.reply_text(
                reply,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Settings", callback_data="admin_settings")]
                ])
            )
            
        except ValueError as e:
            await message.reply_text(f"❌ Invalid value: {str(e)}\nPlease try again or /cancel")
        except Exception as e:
            logger.error(f"Error saving setting: {e}")
            await message.reply_text("❌ Error saving setting. Please try again.")  
    async def add_admin_start(self, client: Client, callback_query: CallbackQuery):
        if callback_query.from_user.id not in Config.OWNERS:
            await callback_query.answer("You don't have permission to access this.", show_alert=True)
            return
        
        await self.update_message(
            client,
            callback_query.message,
            "👑 *Add New Admin*\n\n"
            "Send the user ID or username of the user you want to make admin.\n"
            "Use /cancel to abort."
        )
        self.user_sessions[callback_query.from_user.id] = {'state': 'adding_admin'}
    async def remove_admin_command(self, client: Client, message: Message):
        """Properly remove admin with confirmation and database updates"""
        if message.from_user.id not in Config.OWNERS:
            await message.reply_text("❌ Owner only command")
            return

        if len(message.command) < 2:
            # Show list of removable admins
            removable_admins = []
            async for admin in self.db.admins_collection.find():
                if admin['user_id'] not in Config.OWNERS:  # Can't remove owners
                    try:
                        user = await client.get_users(admin['user_id'])
                        name = f"@{user.username}" if user.username else user.first_name
                        removable_admins.append((admin['user_id'], name))
                    except:
                        removable_admins.append((admin['user_id'], str(admin['user_id'])))

            if not removable_admins:
                await message.reply_text("No removable admins found.")
                return

            # Create keyboard
            keyboard = []
            for admin_id, name in removable_admins:
                keyboard.append([InlineKeyboardButton(
                    f"Remove {name} (ID: {admin_id})",
                    callback_data=f"confirm_remove_admin_{admin_id}"
                )])
            
            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_remove_admin")])

            await message.reply_text(
                "🗑 Select admin to remove:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        try:
            admin_id = int(message.command[1])
            await self._remove_admin(client, message, admin_id)
        except ValueError:
            await message.reply_text("Invalid admin ID. Must be a number.")

    async def _remove_admin(self, client: Client, message: Message, admin_id: int):
        """Internal method to handle admin removal"""
        # Verify not removing self
        if admin_id == message.from_user.id:
            await message.reply_text("❌ You cannot remove yourself!")
            return

        # Verify not removing owner
        if admin_id in Config.OWNERS:
            await message.reply_text("❌ Cannot remove owners using this command!")
            return

        # Verify admin exists
        admin = await self.db.admins_collection.find_one({"user_id": admin_id})
        if not admin:
            await message.reply_text("❌ User is not an admin!")
            return

        # Get user info for confirmation
        try:
            user = await client.get_users(admin_id)
            username = f"@{user.username}" if user.username else user.first_name
        except:
            username = str(admin_id)

        # Confirmation keyboard
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm Remove", callback_data=f"final_remove_admin_{admin_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_remove_admin")
            ]
        ])

        await message.reply_text(
            f"⚠️ Are you sure you want to remove admin privileges from:\n"
            f"👤 User: {username}\n"
            f"🆔 ID: {admin_id}\n\n"
            f"This action cannot be undone!",
            reply_markup=keyboard
        )

    async def handle_remove_admin_callback(self, client: Client, callback_query: CallbackQuery):
        """Handle admin removal confirmation"""
        data = callback_query.data
        
        if data == "cancel_remove_admin":
            await callback_query.message.delete()
            await callback_query.answer("Admin removal cancelled")
            return

        if data.startswith("final_remove_admin_"):
            admin_id = int(data.split("_")[-1])
            
            # Double-check not removing owner
            if admin_id in Config.OWNERS:
                await callback_query.answer("Cannot remove owners!", show_alert=True)
                return

            # Remove from database
            result = await self.db.admins_collection.delete_one({"user_id": admin_id})
            
            if result.deleted_count > 0:
                # Reload admins
                await self.db.load_admins_and_owners()
                
                try:
                    user = await client.get_users(admin_id)
                    username = f"@{user.username}" if user.username else user.first_name
                except:
                    username = str(admin_id)
                
                await callback_query.message.edit_text(
                    f"✅ Successfully removed admin privileges from:\n"
                    f"👤 {username}\n"
                    f"🆔 {admin_id}"
                )
            else:
                await callback_query.answer("Admin not found!", show_alert=True)

    # In AnimeBot class
    async def admin_delete_episode_menu(self, client: Client, callback_query: CallbackQuery, anime_id: int, page: int = 1):
        """Show paginated menu for deleting episodes"""
        try:
            if callback_query.from_user.id not in Config.ADMINS:
                await callback_query.answer("❌ Admin only", show_alert=True)
                return
    
            anime = await self.db.find_anime(anime_id)
            if not anime:
                await callback_query.answer("Anime not found", show_alert=True)
                return
    
            # Collect all episodes
            all_episodes = set()
            for db_client in self.db.anime_clients:
                try:
                    db = db_client[self.db.db_name]
                    episodes = await db.files.distinct("episode", {"anime_id": anime_id})
                    all_episodes.update(episodes)
                except Exception:
                    continue
    
            if not all_episodes:
                await callback_query.answer("No episodes found", show_alert=True)
                return
    
            sorted_eps = sorted(all_episodes)
            total_eps = len(sorted_eps)
    
            # Pagination
            total_pages = (total_eps + Config.EPISODES_PER_PAGE - 1) // Config.EPISODES_PER_PAGE
            page = max(1, min(page, total_pages))
            start = (page - 1) * Config.EPISODES_PER_PAGE
            end = start + Config.EPISODES_PER_PAGE
            current_eps = sorted_eps[start:end]
    
            keyboard = []
            row = []
            for ep in current_eps:
                row.append(InlineKeyboardButton(f"Ep {ep}", callback_data=f"del_ep_{anime_id}_{ep}"))
                if len(row) == 5:
                    keyboard.append(row)
                    row = []
            if row:  # append last row if not empty
                keyboard.append(row)
    
            # 🔥 Always show Bulk Delete options
            keyboard.append([
                InlineKeyboardButton("🗑 Delete ALL", callback_data=f"del_all_{anime_id}"),
                InlineKeyboardButton("🔍 Select Range", callback_data=f"del_range_{anime_id}")
            ])
    
            # 🔥 Always show page indicator (even for 1 page)
            nav_buttons = []
            if page > 1:
                nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"del_menu_{anime_id}_{page-1}"))
            nav_buttons.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
            if page < total_pages:
                nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"del_menu_{anime_id}_{page+1}"))
            keyboard.append(nav_buttons)
    
            # 🔙 Back / Close row
            keyboard.append([
                InlineKeyboardButton("🔙 Back", callback_data=f"anime_{anime_id}"),
                InlineKeyboardButton("❌ Close", callback_data="close_message")
            ])

    
            await callback_query.message.edit_text(
                f"🗑 <b>Delete Episodes for:</b>\n{anime['title']}\n\n"
                f"Page {page}/{total_pages} • Total Episodes: {total_eps}\n"
                "Select episode to delete:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=enums.ParseMode.HTML
            )
    
        except Exception as e:
            logger.error(f"Error in delete episode menu: {e}")
            await callback_query.answer("Error loading menu", show_alert=True)
    async def confirm_delete_episode(self, client: Client, callback_query: CallbackQuery, anime_id: int, episode: int):
        """Show confirmation before deleting episode"""
        try:
            anime = await self.db.find_anime(anime_id)
            if not anime:
                await callback_query.answer("Anime not found", show_alert=True)
                return
            
            # Get files for this episode
            files = await self.db.find_files(anime_id, episode)
            file_count = len(files) if files else 0
            
            await callback_query.message.edit_text(
                f"⚠️ <b>Confirm Deletion</b>\n\n"
                f"Anime: <b>{anime['title']}</b>\n"
                f"Episode: <b>{episode}</b>\n"
                f"Files to delete: <b>{file_count}</b>\n\n"
                "This action cannot be undone!",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Confirm Delete", callback_data=f"confirm_del_{anime_id}_{episode}"),
                        InlineKeyboardButton("❌ Cancel", callback_data=f"del_menu_{anime_id}_1")  # 🔧 fixed
                    ]
                ]),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error in confirm delete: {e}")
            await callback_query.answer("Error confirming deletion", show_alert=True)

    async def delete_episode(self, client: Client, callback_query: CallbackQuery, anime_id: int, episode: int):
        """Actually delete the episode"""
        try:
            deleted = await self.db.delete_episode(anime_id, episode)
            
            await callback_query.message.edit_text(
                f"✅ Successfully deleted {deleted} files for episode {episode}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Anime", callback_data=f"anime_{anime_id}")]
                ])
            )
            
            # Log the deletion
            logger.info(f"Admin {callback_query.from_user.id} deleted episode {episode} from anime {anime_id}")
        except Exception as e:
            logger.error(f"Error deleting episode: {e}")
            await callback_query.answer("Error deleting episode", show_alert=True)

    async def delete_all_episodes(self, client: Client, callback_query: CallbackQuery, anime_id: int):
        """Delete all episodes for an anime"""
        try:
            anime = await self.db.find_anime(anime_id)
            if not anime:
                await callback_query.answer("Anime not found", show_alert=True)
                return
            
            # Get total file count
            total_files = 0
            for client in self.db.anime_clients:
                try:
                    db = client[self.db.db_name]
                    count = await db.files.count_documents({"anime_id": anime_id})
                    total_files += count
                except Exception:
                    continue
            
            await callback_query.message.edit_text(
                f"⚠️ <b>Confirm Delete ALL Episodes</b>\n\n"
                f"Anime: <b>{anime['title']}</b>\n"
                f"Total files to delete: <b>{total_files}</b>\n\n"
                "This will remove ALL episodes and cannot be undone!",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Confirm Delete ALL", callback_data=f"confirm_del_all_{anime_id}"),
                        InlineKeyboardButton("❌ Cancel", callback_data=f"del_menu_{anime_id}")
                    ]
                ]),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error in delete all confirmation: {e}")
            await callback_query.answer("Error preparing deletion", show_alert=True)

    async def delete_all_episodes(self, client: Client, callback_query: CallbackQuery, anime_id: int):
        """Delete all episodes for an anime"""
        try:
            anime = await self.db.find_anime(anime_id)
            if not anime:
                await callback_query.answer("Anime not found", show_alert=True)
                return
            
            # Count total files
            total_files = 0
            for db_client in self.db.anime_clients:
                try:
                    db = db_client[self.db.db_name]
                    count = await db.files.count_documents({"anime_id": anime_id})
                    total_files += count
                except Exception:
                    continue
            
            await callback_query.message.edit_text(
                f"⚠️ <b>Confirm Delete ALL Episodes</b>\n\n"
                f"Anime: <b>{anime['title']}</b>\n"
                f"Total files to delete: <b>{total_files}</b>\n\n"
                "This will remove ALL episodes and cannot be undone!",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Confirm Delete ALL", callback_data=f"confirm_del_all_{anime_id}"),
                        InlineKeyboardButton("❌ Cancel", callback_data=f"del_menu_{anime_id}_1")  # 🔧 fixed
                    ]
                ]),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error in delete all confirmation: {e}")
            await callback_query.answer("Error preparing deletion", show_alert=True)

    async def add_owner_start(self, client: Client, callback_query: CallbackQuery):
        """Start process to add an owner"""
        if callback_query.from_user.id not in self.config.OWNERS:
            await callback_query.answer("❌ Owner only", show_alert=True)
            return
            
        await self.update_message(
            client,
            callback_query.message,
            "👑 Add New Owner\n\n"
            "Send the user ID or username of the user you want to make owner:",
        )
        self.user_sessions[callback_query.from_user.id] = {'state': 'adding_owner'}


    async def add_owner_process(self, client: Client, message: Message):
        """Process adding an owner"""
        user_id = message.from_user.id
        if user_id not in self.user_sessions or self.user_sessions[user_id].get('state') != 'adding_owner':
            return
            
        try:
            text = message.text.strip()
            try:
                new_owner_id = int(text)
                user = await client.get_users(new_owner_id)
            except ValueError:
                if text.startswith('@'):
                    text = text[1:]
                user = await client.get_users(text)
                new_owner_id = user.id
                
            if new_owner_id in self.config.OWNERS:
                await message.reply_text("This user is already an owner")
            else:
                self.config.OWNERS.append(new_owner_id)
                os.environ["OWNERS"] = ",".join(map(str, self.config.OWNERS))
                
                await message.reply_text(
                    f"✅ Successfully added owner:\n\n"
                    f"👤 User: {user.mention()}\n"
                    f"🆔 ID: {new_owner_id}\n"
                    f"📛 Username: @{user.username or 'N/A'}"
                )
                
        except Exception as e:
            logger.error(f"Error adding owner: {e}")
            await message.reply_text(
                "❌ Error adding owner!\n"
                "Please make sure you entered a valid user ID or username.\n"
                "Use /cancel and try again."
            )
        finally:
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
    async def remove_owner_start(self, client: Client, callback_query: CallbackQuery):
        """Start process to remove an owner"""
        if callback_query.from_user.id not in self.config.OWNERS:
            await callback_query.answer("❌ Owner only", show_alert=True)
            return
            
        if len(self.config.OWNERS) <= 1:
            await callback_query.answer("Cannot remove last owner", show_alert=True)
            return
            
        keyboard = []
        for owner_id in self.config.OWNERS:
            if owner_id == callback_query.from_user.id:
                continue  # Can't remove yourself
            try:
                user = await client.get_users(owner_id)
                btn_text = f"{user.first_name} (@{user.username})" if user.username else user.first_name
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"remove_owner_{owner_id}")])
            except:
                keyboard.append([InlineKeyboardButton(f"User {owner_id}", callback_data=f"remove_owner_{owner_id}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="owner_tools")])
        
        await self.update_message(
            client,
            callback_query.message,
            "⚠️ Select owner to remove:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def list_admins(self, client: Client, callback_query: CallbackQuery):
        """List all admins"""
        if callback_query.from_user.id not in self.config.OWNERS:
            await callback_query.answer("❌ Owner only", show_alert=True)
            return
            
        message = "👥 List of Admins\n\n"
        for admin_id in self.config.ADMINS:
            try:
                user = await client.get_users(admin_id)
                message += f"- {user.mention()} (@{user.username})\n" if user.username else f"- {user.mention()}\n"
            except:
                message += f"- User ID: {admin_id}\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="owner_tools")]
        ])
        
        await self.update_message(
            client,
            callback_query.message,
            message,
            reply_markup=keyboard
        )
    async def add_admin_process(self, client: Client, message: Message):
        user_id = message.from_user.id
        if user_id not in self.user_sessions or self.user_sessions[user_id].get('state') != 'adding_admin':
            return

        text = message.text.strip()

        try:
            try:
                new_admin_id = int(text)
                user = await client.get_users(new_admin_id)
            except ValueError:
                if text.startswith('@'):
                    text = text[1:]
                user = await client.get_users(text)
                new_admin_id = user.id

            # Save to database
            await self.db.admins_collection.update_one(
                {"user_id": new_admin_id},
                {"$set": {
                    "user_id": new_admin_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "added_by": user_id,
                    "added_at": datetime.now()
                }},
                upsert=True
            )

            await self.db.load_admins_and_owners()

            await message.reply_text(
                f"✅ *Successfully added admin:*\n\n"
                f"👤 *User:* {user.mention()}\n"
                f"🆔 *ID:* `{new_admin_id}`\n"
                f"📛 *Username:* @{user.username or 'N/A'}"
            )
        except Exception as e:
            logger.error(f"Error adding admin: {e}")
            await message.reply_text(
                "❌ *Error adding admin!*\n"
                "Please make sure you entered a valid user ID or username.\n"
                "Use /cancel and try again."
            )
        finally:
            self.user_sessions.pop(user_id, None)

    async def remove_admin_process(self, client: Client, message: Message):
        user_id = message.from_user.id
        if user_id not in Config.OWNERS:
            await message.reply_text("❌ Owner only")
            return

        text = message.text.strip()
        try:
            if text.startswith('@'):
                user = await client.get_users(text[1:])
                target_id = user.id
            else:
                target_id = int(text)

            if target_id not in Config.ADMINS:
                await message.reply_text("⚠️ This user is not an admin.")
                return

            # Remove from DB
            await self.db.admins_collection.delete_one({"user_id": target_id})
            await self.db.load_admins_and_owners()

            await message.reply_text(f"✅ Removed admin with ID: `{target_id}`")
        except Exception as e:
            logger.error(f"Error removing admin: {e}")
            await message.reply_text(f"❌ Error: {str(e)}")

    async def update_setting(self, setting: str, value):
        await self.db.stats_collection.update_one(
            {"type": "global"},
            {"$set": {f"settings.{setting}": value}}
        )
        
        if setting == "delete_timer":
            Config.DELETE_TIMER_MINUTES = value
        elif setting == "max_results":
            Config.MAX_SEARCH_RESULTS = value
        elif setting == "max_episodes":
            Config.MAX_EPISODES_PER_PAGE = value
        elif setting == "pm_search":
            Config.PM_SEARCH = value
        elif setting == "protect_content":
            Config.PROTECT_CONTENT = value

    async def change_setting(self, client: Client, callback_query: CallbackQuery, setting: str):
        if callback_query.from_user.id not in Config.ADMINS:
            await callback_query.answer("You don't have permission to access this.", show_alert=True)
            return
        
        setting_info = {
            "delete_timer": {
                "name": "Delete Timer (minutes)",
                "current": Config.DELETE_TIMER_MINUTES,
                "type": "number"
            },
            "max_results": {
                "name": "Max Search Results",
                "current": Config.MAX_SEARCH_RESULTS,
                "type": "number"
            },
            "max_episodes": {
                "name": "Max Episodes Per Page",
                "current": Config.MAX_EPISODES_PER_PAGE,
                "type": "number"
            },
            "pm_search": {
                "name": "PM Search",
                "current": Config.PM_SEARCH,
                "type": "boolean"
            },
            "protect_content": {
                "name": "Content Protection",
                "current": Config.PROTECT_CONTENT,
                "type": "boolean"
            }
        }.get(setting)
        
        if not setting_info:
            await callback_query.answer("Invalid setting.", show_alert=True)
            return
        
        self.user_sessions[callback_query.from_user.id] = {
            'state': 'changing_setting',
            'setting': setting
        }
        
        message_text = (
            f"⚙️ *Change {setting_info['name']}*\n\n"
            f"Current value: `{setting_info['current']}`\n\n"
        )
        
        if setting_info['type'] == 'boolean':
            message_text += "Send 'on' to enable or 'off' to disable."
        else:
            message_text += f"Send the new {setting_info['name']} value."
        
        message_text += "\nUse /cancel to abort."
        
        await self.update_message(
            client,
            callback_query.message,
            message_text
        )

    async def process_setting_change(self, client: Client, message: Message):
        user_id = message.from_user.id
        if user_id not in self.user_sessions or self.user_sessions[user_id].get('state') != 'changing_setting':
            return
        
        setting = self.user_sessions[user_id]['setting']
        text = message.text.strip().lower()
        
        try:
            setting_info = {
                "delete_timer": {
                    "name": "Delete Timer (minutes)",
                    "type": "number",
                    "min": 1,
                    "max": 60
                },
                "max_results": {
                    "name": "Max Search Results",
                    "type": "number",
                    "min": 1,
                    "max": 20
                },
                "max_episodes": {
                    "name": "Max Episodes Per Page",
                    "type": "number",
                    "min": 1,
                    "max": 50
                },
                "pm_search": {
                    "name": "PM Search",
                    "type": "boolean"
                },
                "protect_content": {
                    "name": "Content Protection",
                    "type": "boolean"
                }
            }.get(setting)
            
            if not setting_info:
                await message.reply_text("❌ Invalid setting. Operation cancelled.")
                return
            
            if setting_info['type'] == 'boolean':
                if text in ['on', 'true', 'yes', 'enable']:
                    new_value = True
                elif text in ['off', 'false', 'no', 'disable']:
                    new_value = False
                else:
                    raise ValueError("Please enter 'on' or 'off'")
            else:
                new_value = int(text)
                if new_value < setting_info['min'] or new_value > setting_info['max']:
                    raise ValueError(f"Value must be between {setting_info['min']} and {setting_info['max']}")
            
            await self.update_setting(setting, new_value)
            
            await message.reply_text(
                f"✅ *{setting_info['name']} updated to:* `{new_value}`"
            )
            
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
                
        except ValueError as e:
            await message.reply_text(
                f"❌ *Invalid value:* {str(e)}\nPlease try again or /cancel."
            )
        except Exception as e:
            logger.error(f"Error updating setting: {e}")
            await message.reply_text(
                "❌ *Error updating setting!*\nPlease try again or contact developer."
            )

    async def close_message(self, client: Client, callback_query: CallbackQuery):
        try:
            await callback_query.message.delete()
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            await callback_query.answer("Error closing message.", show_alert=True)
    async def restart_command(self, client: Client, message: Message):
        if message.from_user.id not in self.config.OWNERS:
            await message.reply_text("❌ Owner only")
            return
        
        await message.reply_text("🔄 Restarting bot...")
        os.execv(sys.executable, [sys.executable] + sys.argv)
    async def add_db_channel_start(self, client: Client, callback_query: CallbackQuery):
        if callback_query.from_user.id not in Config.ADMINS:
            await callback_query.answer("You don't have permission to access this.", show_alert=True)
            return
        
        await self.update_message(
            client,
            callback_query.message,
            "📂 *Add Database Channel*\n\n"
            "Send the channel ID you want to add as a database channel.\n"
            "Use /cancel to abort."
        )
        self.user_sessions[callback_query.from_user.id] = {'state': 'adding_db_channel'}

    async def remove_db_channel_start(self, client: Client, callback_query: CallbackQuery):
        if callback_query.from_user.id not in Config.ADMINS:
            await callback_query.answer("You don't have permission to access this.", show_alert=True)
            return
        
        try:
            channels = await self.db.get_database_channels()
            if not channels:
                await callback_query.answer("No database channels found.", show_alert=True)
                return
            
            keyboard = []
            for channel_id in channels:
                try:
                    chat = await client.get_chat(channel_id)
                    title = chat.title
                except Exception:
                    title = f"Channel {channel_id}"
                
                keyboard.append([
                    InlineKeyboardButton(title, callback_data=f"select_remove_db_channel_{channel_id}")
                ])
            
            keyboard.append([
                InlineKeyboardButton("🔙 Back", callback_data="admin_panel"),
                InlineKeyboardButton("❌ Close", callback_data="close_message")
            ])
            
            await self.update_message(
                client,
                callback_query.message,
                "🗑 *Remove Database Channel*\n\n"
                "Select a channel to remove:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Error starting remove DB channel: {e}")
            await callback_query.answer("Error starting DB channel removal.", show_alert=True)

    async def process_db_channel_add(self, client: Client, message: Message):
        user_id = message.from_user.id
        if user_id not in self.user_sessions or self.user_sessions[user_id].get('state') != 'adding_db_channel':
            return
        
        text = message.text.strip()
        
        try:
            # Handle both channel IDs (with -100 prefix and without)
            if text.startswith('-100'):
                channel_id = int(text)
            else:
                channel_id = int(f"-100{text}")
                
            try:
                chat = await client.get_chat(channel_id)
                if chat.type not in [ChatType.CHANNEL, ChatType.SUPERGROUP]:
                    raise ValueError("Only channels and supergroups can be database channels")
                    
                success = await self.db.add_database_channel(channel_id)
                if not success:
                    raise Exception("Failed to add channel to database")
                    
                await message.reply_text(
                    f"✅ Successfully added database channel:\n\n"
                    f"📛 Title: {chat.title}\n"
                    f"🆔 ID: {channel_id}"
                )
                
            except Exception as e:
                await message.reply_text(f"Error: {str(e)}")
                
        except ValueError:
            await message.reply_text("Invalid channel ID. Must be a numeric ID.")
        
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
    async def remove_db_channel(self, client: Client, callback_query: CallbackQuery, channel_id: int):
        try:
            success = await self.db.remove_database_channel(channel_id)
            if not success:
                raise Exception("Failed to remove channel from database")
            
            try:
                chat = await client.get_chat(channel_id)
                title = chat.title
            except Exception:
                title = f"Channel {channel_id}"
            
            await self.update_message(
                client,
                callback_query.message,
                f"✅ *Successfully removed database channel:*\n\n"
                f"📛 *Title:* {title}\n"
                f"🆔 *ID:* `{channel_id}`"
            )
        except Exception as e:
            logger.error(f"Error removing DB channel: {e}")
            await callback_query.answer("Error removing database channel.", show_alert=True)
    async def add_anime_start(self, client: Client, callback_query: CallbackQuery):
        if callback_query.from_user.id not in Config.ADMINS:
            await callback_query.answer("You don't have permission to access this.", show_alert=True)
            return
        
        # Clear any existing session
        self.user_sessions[callback_query.from_user.id] = {'state': 'adding_anime'}
        
        await self.update_message(
            client,
            callback_query.message,
            "📝 *Add New Anime*\n\n"
            "Send details in this format:\n\n"
            "`Title | Type (TV/MOVIE/OVA/ADULT) | Episodes | Studio | Status (Finished/Releasing/Upcoming) | Genres (comma separated) | Description | Cover URL | AniList URL | Year`\n\n"
            "*Examples:*\n"
            "• `Attack on Titan | TV | 75 | Wit Studio | Finished | Action, Drama, Fantasy | In a world where humanity lives... | https://example.com/cover.jpg | https://anilist.co/anime/16498 | 2013`\n"
            "• `One Piece | TV | None | Toei Animation | Releasing | Action, Adventure, Comedy | Gold Roger was known as the Pirate King... | https://img.anili.st/media/6284053604036871611 | https://anilist.co/anime/6284053604036871611 | 1999`\n\n"
            "*Episode Options:*\n"
            "• Use actual number for completed series (e.g., `24`)\n"
            "• Use `None`, `Ongoing`, or `Unknown` for ongoing series\n\n"
            "*Required Fields:* Title, Type, Episodes, Studio, Status\n"
            "Use /cancel to abort.",
            parse_mode=enums.ParseMode.MARKDOWN
        )

    async def send_file_to_pm(self, client: Client, callback_query: CallbackQuery, file_id: str):
        try:
            # Get file info
            file_info = await self.db.files_collection.find_one({"_id": ObjectId(file_id)})
            
            # Send to PM
            await client.send_message(
                chat_id=callback_query.from_user.id,
                text=f"Here's your requested file: {file_info['file_name']}"
            )
            
            # Then send the actual file using the process_file_download method
            await self.process_file_download(client, callback_query.message, file_id)
            
        except Exception as e:
            logger.error(f"PM send error: {e}")
            await callback_query.answer("Failed to send to PM", show_alert=True)
   
    async def add_anime_process(self, client: Client, message: Message):
        user_id = message.from_user.id
        if user_id not in self.user_sessions or self.user_sessions[user_id].get('state') != 'adding_anime':
            return
        
        try:
            text = message.text.strip()
            parts = [part.strip() for part in text.split('|')]
            
            if len(parts) < 5:  # Minimum required fields
                await message.reply_text(
                    "❌ *Invalid format!*\n\n"
                    "Minimum required: `Title | Type (TV/MOVIE/OVA/ADULT) | Episodes | Studio | Status (Finished/Releasing/Upcoming)`\n"
                    "Use /cancel and try again.",
                    parse_mode=enums.ParseMode.MARKDOWN
                )
                return
            
            # Handle episode count - can be number or "Ongoing" or "Unknown"
            episodes_input = parts[2].lower()
            if episodes_input in ['ongoing', 'unknown', 'none', 'tba']:
                episodes = None
                episodes_display = "Ongoing" if parts[4].upper() == "RELEASING" else "Unknown"
                is_ongoing = parts[4].upper() == "RELEASING"
            else:
                try:
                    episodes = int(episodes_input)
                    episodes_display = str(episodes)
                    is_ongoing = parts[4].upper() == "RELEASING"
                except ValueError:
                    await message.reply_text(
                        "❌ *Invalid episode format!*\n\n"
                        "Episodes must be a number or 'Ongoing' for releasing series.\n"
                        "Use /cancel and try again.",
                        parse_mode=enums.ParseMode.MARKDOWN
                    )
                    return
            
            # Generate a unique ID using title + current timestamp
            title = parts[0]
            unique_id = abs(hash(f"{title.lower()}{datetime.now().timestamp()}"))
            
            # Validate status
            valid_statuses = ["FINISHED", "RELEASING", "UPCOMING"]
            status = parts[4].upper()
            if status not in valid_statuses:
                await message.reply_text(
                    f"❌ *Invalid status!*\n\n"
                    f"Valid statuses: {', '.join(valid_statuses)}\n"
                    f"Use /cancel and try again.",
                    parse_mode=enums.ParseMode.MARKDOWN
                )
                return
            
            anime_data = {
                "id": unique_id,
                "title": title,
                "type": parts[1].upper(),
                "episodes": episodes,  # Can be None for ongoing series
                "episodes_display": episodes_display,  # User-friendly display
                "studio": parts[3],
                "status": status,
                "is_ongoing": is_ongoing,
                "is_releasing": status == "RELEASING",
                "genres": [g.strip() for g in parts[5].split(',')] if len(parts) > 5 and parts[5] else [],
                "description": parts[6] if len(parts) > 6 and parts[6] else "",
                "cover_url": parts[7] if len(parts) > 7 and parts[7] else Config.COVER_PIC,
                "url": parts[8] if len(parts) > 8 and parts[8] else "",
                "year": int(parts[9]) if len(parts) > 9 and parts[9].strip() and parts[9].strip().isdigit() else None,
                "added_by": user_id,
                "added_date": datetime.now(),
                "last_updated": datetime.now()
            }
            
            # Check for duplicates across all clusters
            duplicate = False
            for db_client in self.db.anime_clients:
                try:
                    db = db_client[self.db.db_name]
                    if await db.anime.count_documents({"title": {"$regex": f"^{re.escape(title)}$", "$options": "i"}}) > 0:
                        duplicate = True
                        break
                except Exception as e:
                    logger.warning(f"Error checking duplicates in cluster: {e}")
            
            if duplicate:
                await message.reply_text("❌ An anime with this title already exists!")
                return
            
            success = await self.db.insert_anime(anime_data)
            if not success:
                raise Exception("Failed to insert anime into database")
            
            await self.update_stats("total_anime")
            
            # Notify users who requested this anime
            try:
                await self.request_system.notify_on_upload(title)
            except Exception as e:
                logger.error(f"Error notifying users about new anime: {e}")
            
            reply_text = (
                f"✅ *Successfully added anime:*\n\n"
                f"🎬 *Title:* {anime_data['title']}\n"
                f"📺 *Type:* {anime_data['type']}\n"
                f"📺 *Episodes:* {anime_data['episodes_display']}\n"
                f"🏢 *Studio:* {anime_data['studio']}\n"
                f"📊 *Status:* {anime_data['status'].capitalize()}\n"
                f"🏷️ *Genres:* {', '.join(anime_data['genres']) if anime_data['genres'] else 'None'}\n"
                f"📅 *Year:* {anime_data['year'] or 'Not specified'}\n"
                f"🔗 *AniList URL:* {anime_data['url'] or 'Not provided'}\n"
                f"🆔 *Anime ID:* `{anime_data['id']}`"
            )
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("➕ Add Episodes", callback_data=f"admin_add_episodes_{anime_data['id']}"),
                    InlineKeyboardButton("📺 View Anime", callback_data=f"anime_{anime_data['id']}")
                ]
            ])
            
            await message.reply_text(
                reply_text,
                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
            
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
                
        except ValueError as e:
            await message.reply_text(
                f"❌ *Invalid input:* {str(e)}\nUse /cancel and try again.",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Error adding anime: {e}")
            await message.reply_text(
                "❌ *Error saving anime!*\nPlease try again or contact developer.",
                parse_mode=enums.ParseMode.MARKDOWN
            )

    async def update_episode_count(self, anime_id: int, new_episode_count: int = None):
        """Update episode count for an anime, especially useful for ongoing series"""
        try:
            # If no new_episode_count provided, count the actual episodes in database
            if new_episode_count is None:
                new_episode_count = await self.db.count_episodes(anime_id, count_unique=True)
            
            update_data = {
                "episodes": new_episode_count,
                "episodes_display": str(new_episode_count),
                "last_updated": datetime.now()
            }
            
            # Update across all clusters
            updated = False
            for client in self.db.anime_clients:
                try:
                    db = client[self.db.db_name]
                    result = await db.anime.update_one(
                        {"id": anime_id},
                        {"$set": update_data}
                    )
                    if result.modified_count > 0:
                        updated = True
                except Exception as e:
                    logger.warning(f"Error updating episode count in cluster: {e}")
            
            return updated
            
        except Exception as e:
            logger.error(f"Error updating episode count: {e}")
            return False

    async def auto_update_ongoing_series(self):
        """Automatically update episode counts for ongoing series"""
        while True:
            try:
                # Find all ongoing series
                for db_client in self.db.anime_clients:
                    try:
                        db = db_client[self.db.db_name]
                        ongoing_anime = await db.anime.find(
                            {"is_ongoing": True},
                            {"id": 1, "title": 1}
                        ).to_list(None)
                        
                        for anime in ongoing_anime:
                            # Count actual episodes in database
                            episode_count = await self.db.count_episodes(anime["id"], count_unique=True)
                            
                            # Update if count has changed
                            await self.update_episode_count(anime["id"], episode_count)
                            
                    except Exception as e:
                        logger.warning(f"Error updating ongoing series in cluster: {e}")
                
                # Run once per day
                await asyncio.sleep(24 * 60 * 60)
                
            except Exception as e:
                logger.error(f"Error in auto_update_ongoing_series: {e}")
                await asyncio.sleep(60 * 60)  # Retry after 1 hour on error
    async def edit_anime_start(self, client: Client, callback_query: CallbackQuery, anime_id: Optional[int] = None):
        if callback_query.from_user.id not in Config.ADMINS:
            await callback_query.answer("You don't have permission to access this.", show_alert=True)
            return

        if anime_id:
            try:
                anime = await self.db.find_anime(anime_id)
                if not anime:
                    await callback_query.message.reply_text("❌ *Anime not found!*", parse_mode=enums.ParseMode.MARKDOWN)
                    return

                self.user_sessions[callback_query.from_user.id] = {
                    'state': 'editing_anime',
                    'edit_anime_id': anime_id,
                    'edit_anime_title': anime['title']
                }

                await self.update_message(
                    client,
                    callback_query.message,
                    "📝 *Edit Anime*\n\n"
                    "Send details in this format:\n\n"
                    "`Title | Type (TV/MOVIE/OVA/ADULT) | Episodes | Studio | Status (Finished/Releasing/Upcoming) | Genres (comma separated) | Description | Cover URL | AniList URL | Year`\n\n"
                    "*Example:*\n"
                    "`Attack on Titan | TV | 75 | Wit Studio | Releasing | Action, Drama, Fantasy | In a world where humanity lives... | https://example.com/cover.jpg | https://anilist.co/anime/16498 | 2013`\n\n"
                    "Leave fields empty to keep current values.",
                    parse_mode=enums.ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Error starting edit anime {anime_id}: {e}")
                await callback_query.answer("Error starting anime edit.", show_alert=True)
        else:
            # Show anime selection like before (no major change needed)
            await self.show_edit_anime_selection(client, callback_query)

    async def edit_anime_process(self, client: Client, message: Message):
        user_id = message.from_user.id
        if user_id not in self.user_sessions or self.user_sessions[user_id].get('state') != 'editing_anime':
            return

        anime_id = self.user_sessions[user_id]['edit_anime_id']
        anime_title = self.user_sessions[user_id]['edit_anime_title']

        try:
            text = message.text.strip()
            parts = [part.strip() for part in text.split('|')]

            if len(parts) < 5:  # Minimum required fields
                await message.reply_text(
                    "❌ *Invalid format!*\nMinimum required: `Title | Type | Episodes | Studio | Status`\nUse /cancel and try again.",
                    parse_mode=enums.ParseMode.MARKDOWN
                )
                return

            # Validate status
            valid_statuses = ["FINISHED", "RELEASING", "UPCOMING"]
            status = parts[4].upper()
            if status not in valid_statuses:
                await message.reply_text(
                    f"❌ *Invalid status!*\nValid statuses: {', '.join(valid_statuses)}\nUse /cancel and try again.",
                    parse_mode=enums.ParseMode.MARKDOWN
                )
                return

            # Handle episodes
            episodes_input = parts[2].lower()
            if episodes_input in ['ongoing', 'unknown', 'none', 'tba']:
                episodes = None
                episodes_display = "Ongoing" if status == "RELEASING" else "Unknown"
                is_ongoing = status == "RELEASING"
            else:
                try:
                    episodes = int(episodes_input)
                    episodes_display = str(episodes)
                    is_ongoing = status == "RELEASING"
                except ValueError:
                    await message.reply_text(
                        "❌ *Invalid episode format!*\nEpisodes must be a number or 'Ongoing'.\nUse /cancel and try again.",
                        parse_mode=enums.ParseMode.MARKDOWN
                    )
                    return

            update_data = {
                "title": parts[0],
                "type": parts[1].upper(),
                "episodes": episodes,
                "episodes_display": episodes_display,
                "studio": parts[3],
                "status": status,
                "is_ongoing": is_ongoing,
                "is_releasing": status == "RELEASING",
                "genres": [g.strip() for g in parts[5].split(',')] if len(parts) > 5 and parts[5] else [],
                "description": parts[6] if len(parts) > 6 and parts[6] else "",
                "cover_url": parts[7] if len(parts) > 7 and parts[7] else Config.COVER_PIC,
                "url": parts[8] if len(parts) > 8 and parts[8] else "",
                "year": int(parts[9]) if len(parts) > 9 and parts[9].strip().isdigit() else None,
                "last_updated": datetime.now()
            }

            # Update across all clusters
            success = False
            for db_client in self.db.anime_clients:
                try:
                    db = db_client[self.db.db_name]
                    result = await db.anime.update_one({"id": anime_id}, {"$set": update_data})
                    if result.modified_count > 0:
                        success = True
                except Exception as e:
                    logger.warning(f"Error updating anime in cluster: {e}")

            if success:
                reply_text = f"✅ Successfully updated {anime_title}:\n\n"
                for key, value in update_data.items():
                    if key != 'last_updated':
                        reply_text += f"• {key.capitalize()}: {value}\n"
                reply_text += f"\n🆔 Anime ID: `{anime_id}`"

                await message.reply_text(reply_text, parse_mode=enums.ParseMode.MARKDOWN)
            else:
                await message.reply_text("⚠️ No changes were made or failed to update.")

            self.user_sessions.pop(user_id, None)

        except ValueError as e:
            await message.reply_text(f"❌ Invalid input: {str(e)}\nUse /cancel and try again.", parse_mode=enums.ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Error editing anime {anime_id}: {e}")
            await message.reply_text("❌ Error updating anime!", parse_mode=enums.ParseMode.MARKDOWN)

 
    async def delete_anime_start(self, client: Client, callback_query: CallbackQuery, anime_id: Optional[int] = None):
        if callback_query.from_user.id not in Config.ADMINS:
            await callback_query.answer("You don't have permission to access this.", show_alert=True)
            return

        if anime_id:
            try:
                anime = await self.db.find_anime(anime_id)
                if not anime:
                    await callback_query.message.reply_text("❌ *Anime not found!*")
                    return
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Confirm Delete", callback_data=f"confirm_delete_anime_{anime_id}"),
                        InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")
                    ]
                ])
                await self.update_message(
                    client,
                    callback_query.message,
                    f"🗑️ *Confirm deletion of {anime['title']}*\n\n"
                    "This will delete the anime and all associated files.\nThis action cannot be undone!",
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Error starting delete anime {anime_id}: {e}")
                await callback_query.answer("Error starting anime deletion.", show_alert=True)
        else:
            try:
                # Search across all clusters for anime list
                anime_list = []
                for db_client in self.db.anime_clients:
                    try:
                        db = client[self.db.db_name]
                        cluster_results = await db.anime.find(
                            {},
                            {"id": 1, "title": 1, "episodes": 1}
                        ).sort("title", 1).limit(50).to_list(None)
                        anime_list.extend(cluster_results)
                    except Exception as e:
                        logger.warning(f"Error fetching anime from cluster: {e}")
                
                # Deduplicate
                seen_ids = set()
                unique_anime = []
                for anime in anime_list:
                    if anime["id"] not in seen_ids:
                        seen_ids.add(anime["id"])
                        unique_anime.append(anime)
                
                if not unique_anime:
                    await self.update_message(
                        client,
                        callback_query.message,
                        "ℹ️ *No anime found in database!*"
                    )
                    return
                
                keyboard = []
                for anime in unique_anime:
                    btn_text = f"{anime['title']} ({anime.get('episodes', '?')} eps)"
                    keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"admin_delete_anime_{anime['id']}")])
                
                keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")])
                await self.update_message(
                    client,
                    callback_query.message,
                    "🗑️ *Select Anime to Delete*",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                logger.error(f"Error fetching anime list for delete: {e}")
                await callback_query.answer("Error fetching anime list.", show_alert=True)

    async def delete_anime_confirm(self, client: Client, callback_query: CallbackQuery, anime_id: int):
        if callback_query.from_user.id not in Config.ADMINS:
            await callback_query.answer("You don't have permission to access this.", show_alert=True)
            return
        
        try:
            # First find the anime to get its title
            anime = None
            for db_client in self.db.anime_clients:  # Use database client
                try:
                    db = db_client[self.db.db_name]  # Correct - using database client
                    found = await db.anime.find_one({"id": anime_id})
                    if found:
                        anime = found
                        break
                except Exception as e:
                    logger.warning(f"Error finding anime in cluster: {e}")
            
            if not anime:
                await callback_query.message.reply_text("❌ *Anime not found!*")
                return
            
            # Delete across all clusters
            file_count = 0
            for db_client in self.db.anime_clients:  # Use database client
                try:
                    db = db_client[self.db.db_name]  # Correct - using database client
                    # Count files first
                    file_count += await db.files.count_documents({"anime_id": anime_id})
                    # Delete files
                    await db.files.delete_many({"anime_id": anime_id})
                    # Delete anime
                    await db.anime.delete_one({"id": anime_id})
                    
                    # Update related anime (sequels/prequels)
                    await db.anime.update_many(
                        {"prequel_id": anime_id},
                        {"$set": {"prequel_id": None, "is_sequel": False}}
                    )
                    await db.anime.update_many(
                        {"sequel_id": anime_id},
                        {"$set": {"sequel_id": None}}
                    )
                except Exception as e:
                    logger.warning(f"Error deleting in cluster: {e}")
            
            await self.update_stats("total_anime", -1)
            await self.update_stats("total_files", -file_count)
            
            await self.update_message(
                client,  # Telegram client for messaging
                callback_query.message,
                f"🗑️ *Successfully deleted {anime['title']} and {file_count} associated files.*"
            )
        except Exception as e:
            logger.error(f"Error deleting anime {anime_id}: {e}")
            await self.update_message(
                client,  # Telegram client for messaging
                callback_query.message,
                "❌ *Error deleting anime!*"
            )

    async def add_episodes_start(self, client: Client, callback_query: CallbackQuery, page: int = 1):
        if callback_query.from_user.id not in Config.ADMINS:
            await callback_query.answer("❌ Admin only", show_alert=True)
            return

        try:
            per_page = 10
            anime_list = []
            total_anime = 0

            # Get total count and collect all anime first
            for db_client in self.db.anime_clients:
                try:
                    db = db_client[self.db.db_name]
                    count = await db.anime.count_documents({})
                    total_anime += count
                    cursor = db.anime.find({}, {"id": 1, "title": 1, "type": 1, "episodes": 1}).sort("title", 1)
                    async for anime in cursor:
                        anime_list.append(anime)
                except Exception as e:
                    logger.warning(f"Cluster error: {e}")

            # Remove duplicates
            seen_ids = set()
            unique_anime = []
            for anime in anime_list:
                if anime['id'] not in seen_ids:
                    seen_ids.add(anime['id'])
                    unique_anime.append(anime)

            total_pages = max(1, (len(unique_anime) + per_page - 1) // per_page)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            page_anime = unique_anime[start_idx:end_idx]

            if not page_anime:
                await callback_query.answer("No more anime found", show_alert=True)
                return

            keyboard = []
            for anime in page_anime:
                type_info = Config.ANIME_TYPES.get(anime.get('type', 'TV').upper(), {})
                ep_text = f" ({anime.get('episodes', '?')} eps)" if type_info.get('has_episodes') else ""
                btn_text = f"{anime['title']} [{type_info.get('name', 'TV')}{ep_text}]"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"admin_select_anime_{anime['id']}")])

            # Simple pagination - only show prev/next if available
            nav_buttons = []
            if page > 1:
                nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin_episodes_page_{page-1}"))
            if end_idx < len(unique_anime):
                nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin_episodes_page_{page+1}"))
            
            if nav_buttons:
                keyboard.append(nav_buttons)

            keyboard.append([
                InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel"),
                InlineKeyboardButton("❌ Close", callback_data="close_message")
            ])

            await self.update_message(
                client,
                callback_query.message,
                f"📁 <b>Select Anime to Add Episodes</b>\n"
                f"📦 Total: <b>{len(unique_anime)}</b> | Page: <b>{page}/{total_pages}</b>",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Add episodes error: {e}")
            await callback_query.answer("❌ Error loading list", show_alert=True)

    async def select_anime_for_episodes(self, client: Client, callback_query: CallbackQuery, anime_id: int):
        try:
            anime = await self.db.find_anime(anime_id)
            if not anime:
                await callback_query.answer("❌ Anime not found", show_alert=True)
                return
                
            anime_type = anime.get('type', 'TV').upper()
            type_info = Config.ANIME_TYPES.get(anime_type, {})
            
            self.user_sessions[callback_query.from_user.id] = {
                'state': 'adding_episodes',
                'add_episodes': {
                    'anime_id': anime_id,
                    'anime_title': anime['title'],
                    'anime_type': anime_type,
                    'type_info': type_info
                }
            }
            
            examples = ""
            if type_info.get('has_episodes'):
                examples = (
                    "\n\n📝 *File Naming Examples:*\n"
                    "• `[AnimeName] - Episode 01 [720p].mkv`\n"
                    "• `AnimeName_S01E02_[1080p].mp4`\n"
                    "• `AnimeName - 03 [HD].avi`"
                )
            else:
                examples = (
                    "\n\n📝 *File Naming Examples:*\n"
                    "• `Anime Movie [2023] [1080p].mkv`\n"
                    "• `Anime_OVA_[720p].mp4`\n"
                    "• `Special_Episode_[HD].avi`"
                )
                
            message = (
                f"🎬 <b>{html.escape(anime['title'])}</b>\n"
                f"📁 <i>{type_info.get('name', anime_type)}</i>\n"
                f"{examples}\n\n"
                "Send files with proper naming or reply with /episode <number> first."
            )
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to List", callback_data="admin_episodes_page_1")],
                [InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]
            ]
            
            await self.update_message(
                client,
                callback_query.message,
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Select anime error: {e}")
            await callback_query.answer("❌ Selection failed", show_alert=True)
    async def process_episode_file(self, client: Client, message: Message):
        user_id = message.from_user.id
        if user_id not in self.user_sessions or 'add_episodes' not in self.user_sessions[user_id]:
            return
        try:
            # Get forwarding info
            forward_from = message.forward_from_chat.id if message.forward_from_chat else \
                        message.forward_from.id if message.forward_from else None
    
            db_channels = await self.db.get_database_channels()
            if forward_from not in db_channels:
                await message.reply_text("⚠️ Files must be forwarded from an approved database channel!")
                return
    
            user_session = self.user_sessions[user_id]['add_episodes']
            anime_id = user_session['anime_id']
            anime_title = user_session['anime_title']
    
            # Default to "TV" type if not specified
            anime_type = user_session.get('anime_type', 'TV').upper()
            if anime_type not in Config.ANIME_TYPES:
                await message.reply_text(
                    f"❌ Invalid anime type: {anime_type}\n"
                    f"Valid types: {', '.join(Config.ANIME_TYPES.keys())}"
                )
                return
            is_adult = anime_type in Config.ADULT_CONTENT_TYPES
    
            file_name = ""
            file_type = ""
            if message.document:
                file_name = message.document.file_name or ""
                file_type = "document"
            elif message.video:
                file_name = message.video.file_name or ""
                file_type = "video"
            else:
                await message.reply_text(
                    "❌ *Unsupported file type!*\n"
                    "Only videos and documents are supported.",
                    parse_mode=enums.ParseMode.MARKDOWN
                )
                return
    
            caption = message.caption or ""
                    # Get anime info to check if it has unknown episode count
            anime = await self.db.find_anime(anime_id)
            has_unknown_episodes = anime.get('episodes') is None
            # Use the dedicated extract_episode_number method
            episode = await self.extract_episode_number(message, anime_type)
    
            if episode is None:
                await message.reply_text(
                    "⚠️ *Could not parse episode number!*\n"
                    f"Filename: `{file_name}`\n"
                    f"Caption: `{caption}`\n\n",
                    parse_mode=enums.ParseMode.MARKDOWN
                )
                self.user_sessions[user_id]['awaiting_episode'] = True
                return
            if has_unknown_episodes:
                # Check if this is a new highest episode
                current_max = await self.get_max_episode(anime_id)
                if episode > current_max:
                    # Update the episodes_display to show the new max
                    await self.db.update_anime(
                        anime_id,
                        {
                            "episodes_display": f"Ongoing (Up to {episode})",
                            "last_updated": datetime.now()
                        }
                    )
            quality = "unknown"
            for pattern in self.quality_patterns:
                match = re.search(pattern, file_name, re.IGNORECASE)
                if match:
                    quality = match.group(1).lower()
                    break
    
            season = None
            for pattern in self.season_patterns:
                match = re.search(pattern, file_name, re.IGNORECASE)
                if match:
                    try:
                        season = int(match.group(1))
                        break
                    except (IndexError, ValueError):
                        continue
    
            language = None
            for pattern in self.language_patterns:
                match = re.search(pattern, file_name, re.IGNORECASE)
                if match:
                    language = match.group(1).upper()
                    break
    
            file_size = ""
            if message.document:
                size_bytes = message.document.file_size
                file_size = f"{size_bytes / (1024 * 1024):.2f}MB"
            elif message.video:
                size_bytes = message.video.file_size
                file_size = f"{size_bytes / (1024 * 1024):.2f}MB"
    
            file_data = {
                "_id": ObjectId(),
                "anime_id": anime_id,
                "anime_title": anime_title,
                "season": season or 1,
                "episode": episode,
                "quality": quality,
                "language": language,
                "message_id": message.id,
                "chat_id": message.chat.id,
                "file_name": file_name,
                "file_size": file_size,
                "file_type": file_type,
                "type": anime_type,
                "is_adult": is_adult,
                "added_by": user_id,
                "added_date": datetime.now()
            }
    
            # Check for duplicates
            duplicate = False
            for db_client in self.db.anime_clients:
                try:
                    db = client[self.db.db_name]
                    existing = await db.files.count_documents({
                        "anime_id": anime_id,
                        "episode": episode,
                        "quality": quality,
                        "chat_id": message.chat.id,
                        "language": language
                    })
                    if existing > 0:
                        duplicate = True
                        break
                except Exception as e:
                    logger.warning(f"Error checking duplicates in cluster: {e}")
    
            if duplicate:
                await message.reply_text(
                    f"⚠️ *File already exists for*:\n"
                    f"Anime: {anime_title}\n"
                    f"Episode: {episode}\n"
                    f"Quality: {quality.upper()}\n"
                    f"Language: {language or 'Default'}\n\n"
                    "Skipping duplicate.",
                    parse_mode=enums.ParseMode.MARKDOWN
                )
                return
    
            success = await self.db.insert_file(file_data)
            if not success:
                raise Exception("Failed to insert file into database")
    
            logger.info(f"Inserted file data: {file_data}")
            await self.update_stats("total_files")
    
            await message.reply_text(
                f"✅ *Added file for*:\n"
                f"Anime: {anime_title}\n"
                f"Episode: {episode}\n"
                f"Quality: {quality.upper()}\n"
                f"Language: {language or 'Default'}\n"
                f"Size: {file_size}\n"
                f"Season: {season or 1}\n"
                f"Type: {file_type.capitalize()}\n"
                f"🆔 *File ID:* `{file_data['_id']}`",
                parse_mode=enums.ParseMode.MARKDOWN
            )
                    
            # Notify users in watchlist
            watchlist_users = await self.db.watchlist_collection.distinct(
                "user_id", 
                {"anime_id": file_data["anime_id"]}
            )
            
            # Add notifications for all users
            for user_id in watchlist_users:
                await self.notification_manager.add_notification(
                    file_data["anime_id"], 
                    file_data["episode"], 
                    user_id
                )
    
        except Exception as e:
            logger.error(f"File processing error: {e}")
            await message.reply_text("⚠️ Error processing file. Please try again.")

    async def get_max_episode(self, anime_id: int) -> int:
        """Get the maximum episode number available for an anime"""
        max_episode = 0
        for db_client in self.db.anime_clients:
            try:
                db = db_client[self.db.db_name]
                # Find the highest episode number
                max_file = await db.files.find_one(
                    {"anime_id": anime_id},
                    sort=[("episode", -1)]
                )
                if max_file and max_file.get('episode', 0) > max_episode:
                    max_episode = max_file['episode']
            except Exception as e:
                logger.error(f"Error getting max episode from cluster: {e}")
                continue
        return max_episode
    async def handle_media(self, client: Client, message: Message):
        user_id = message.from_user.id
        if user_id not in Config.ADMINS:
            return

        # Check if forwarded from approved channel
        forward_from = None
        if message.forward_from_chat:
            forward_from = message.forward_from_chat.id
        elif message.forward_from:
            forward_from = message.forward_from.id
            
        db_channels = await self.db.get_database_channels()
        if forward_from and forward_from not in db_channels:
            await message.reply_text("⚠️ Files must be forwarded from an approved database channel!")
            return
            
        if user_id in self.user_sessions and self.user_sessions[user_id].get('state') == 'adding_episodes':
            try:
                session_data = self.user_sessions[user_id]['add_episodes']
                anime_id = session_data['anime_id']
                anime_title = session_data['anime_title']
                anime_type = session_data['anime_type']
                
                # Extract episode number
                episode = await self.extract_episode_number(message, anime_type)
                if episode is None:
                    # Store the message for later processing after getting episode number
                    self.user_sessions[user_id]['pending_file'] = {
                        'message_id': message.id,
                        'chat_id': message.chat.id
                    }
                    await message.reply_text(
                        "⚠️ Could not detect episode number.\n"
                        "Please reply with /episode <number>",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("❌ Cancel", callback_data=f"anime_{anime_id}")]
                        ])
                    )
                    return

                # Process the file
                file_data = {
                    'anime_id': anime_id,
                    'anime_title': anime_title,
                    'episode': episode,
                    'message_id': message.id,
                    'chat_id': message.chat.id,
                    'added_by': user_id,
                    'added_date': datetime.now()
                }

                # Add quality, language, etc. from filename
                file_name = ""
                if message.document:
                    file_name = message.document.file_name or ""
                    file_data['file_type'] = 'document'
                    file_data['file_size'] = f"{message.document.file_size/(1024*1024):.2f}MB"
                elif message.video:
                    file_name = message.video.file_name or ""
                    file_data['file_type'] = 'video'
                    file_data['file_size'] = f"{message.video.file_size/(1024*1024):.2f}MB"

                # Extract quality
                quality = "unknown"
                for pattern in self.quality_patterns:
                    match = re.search(pattern, file_name, re.IGNORECASE)
                    if match:
                        quality = match.group(1).lower()
                        break
                file_data['quality'] = quality

                # Extract language
                language = None
                for pattern in self.language_patterns:
                    match = re.search(pattern, file_name, re.IGNORECASE)
                    if match:
                        language = match.group(1).upper()
                        break
                file_data['language'] = language

                # Insert into database
                success = await self.db.insert_file(file_data)
                if not success:
                    raise Exception("Failed to insert file into database")

                await self.update_stats("total_files")
                
                # Send success message
                reply_msg = (
                    f"✅ Successfully added file for:\n"
                    f"🎬 Anime: {anime_title}\n"
                    f"📺 Episode: {episode}\n"
                    f"🖼️ Quality: {quality.upper()}\n"
                    f"🗣️ Language: {language or 'Default'}"
                )
                
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "➕ Add Another", 
                            callback_data=f"admin_add_episodes_{anime_id}"
                        ),
                        InlineKeyboardButton(
                            "📺 View Anime", 
                            callback_data=f"anime_{anime_id}"
                        )
                    ]
                ])
                
                await message.reply_text(reply_msg, reply_markup=keyboard)
                
            except Exception as e:
                logger.error(f"Error processing episode file: {e}")
                await message.reply_text(
                    "❌ Error processing file. Please try again.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back", callback_data=f"admin_add_episodes_{anime_id}")]
                    ])
                )

    async def cancel(self, client: Client, message: Message):
        user_id = message.from_user.id
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
            await message.reply_text(
                "✅ *Operation cancelled.*\nYou can start a new action.",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await message.reply_text(
                "ℹ️ *No active operation to cancel.*",
                parse_mode=enums.ParseMode.MARKDOWN
            )

    async def show_stats(self, client: Client, callback_query: CallbackQuery):
        if callback_query.from_user.id not in Config.ADMINS:
            await callback_query.answer("You don't have permission to access this.", show_alert=True)
            return
        
        try:
            stats = await self.db.stats_collection.find_one({"type": "global"})
            total_users = await self.db.users_collection.count_documents({})
            
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_percent = psutil.cpu_percent()
            
            recent_users = await self.db.users_collection.find(
                {},
                {"user_id": 1, "username": 1, "downloads": 1, "searches": 1}
            ).sort("last_active", -1).limit(5).to_list(None)
            
            # Get recent anime from all clusters
            recent_anime = []
            for db_client in self.db.anime_clients:
                try:
                    db = client[self.db.db_name]
                    cluster_results = await db.anime.find(
                        {},
                        {"title": 1, "episodes": 1, "added_date": 1}
                    ).sort("added_date", -1).limit(5).to_list(None)
                    recent_anime.extend(cluster_results)
                except Exception as e:
                    logger.warning(f"Error fetching recent anime from cluster: {e}")
            
            # Deduplicate and sort
            seen_ids = set()
            unique_anime = []
            for anime in recent_anime:
                if "id" in anime and anime["id"] not in seen_ids:
                    seen_ids.add(anime["id"])
                    unique_anime.append(anime)
            
            unique_anime.sort(key=lambda x: x.get("added_date", datetime.min), reverse=True)
            recent_anime = unique_anime[:5]
            
            message = (
                f"📊 *Bot Statistics*\n\n"
                f"• Total Anime: `{stats.get('total_anime', 0)}`\n"
                f"• Total Files: `{stats.get('total_files', 0)}`\n"
                f"• Total Users: `{total_users}`\n"
                f"• Total Downloads: `{stats.get('total_downloads', 0)}`\n"
                f"• Total Searches: `{stats.get('total_searches', 0)}`\n\n"
                f"🖥️ *System Stats*\n"
                f"• CPU Usage: `{cpu_percent}%`\n"
                f"• Memory Usage: `{memory.percent}%`\n"
                f"• Disk Usage: `{disk.percent}%`\n\n"
                f"👥 *Recent Users:*\n"
            )
            
            for user in recent_users:
                message += f"- {user.get('username', 'N/A')} (DLs: {user.get('downloads', 0)}, Searches: {user.get('searches', 0)})\n"
            
            message += "\n🎬 *Recently Added Anime:*\n"
            for anime in recent_anime:
                message += f"- {anime['title']} ({anime.get('episodes', '?')} eps)\n"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")],
                [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
            ])
            
            await self.update_message(
                client,
                callback_query.message,
                message,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
            await self.update_message(
                client,
                callback_query.message,
                "❌ *Error fetching statistics!*"
            )

    async def show_settings(self, client: Client, callback_query: CallbackQuery):
        if callback_query.from_user.id not in Config.ADMINS:
            await callback_query.answer("You don't have permission to access this.", show_alert=True)
            return
        
        message = (
            f"⚙️ *Bot Settings*\n\n"
            f"• Delete Timer: `{Config.DELETE_TIMER_MINUTES} minutes`\n"
            f"• Max Results Per Page: `{Config.MAX_SEARCH_RESULTS}`\n"
            f"• Max Episodes Per Page: `{Config.MAX_EPISODES_PER_PAGE}`\n"
            f"• Group Requirement: `{'Enabled' if Config.GROUP_ID else 'Disabled'}`\n"
            f"• PM Search: `{'Enabled' if Config.PM_SEARCH else 'Disabled'}`\n"
            f"• Content Protection: `{'Enabled' if Config.PROTECT_CONTENT else 'Disabled'}`\n"
            f"• Start Picture: `{'Set' if Config.START_PIC else 'Not set'}`\n"
            f"• Cover Picture: `{'Set' if Config.COVER_PIC else 'Not set'}`\n\n"
            f"*Current Admins:*\n"
        )
        
        for admin_id in Config.ADMINS:
            try:
                user = await client.get_users(admin_id)
                message += f"- {user.first_name} (@{user.username or 'N/A'})\n"
            except Exception:
                message += f"- ID: {admin_id}\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_settings")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
        ])
        
        await self.update_message(
            client,
            callback_query.message,
            message,
            reply_markup=keyboard
        )

    async def link_sequel_start(self, client: Client, callback_query: CallbackQuery, page: int = 1):
        if callback_query.from_user.id not in Config.ADMINS:
            await callback_query.answer("❌ Admin only", show_alert=True)
            return
        
        try:
            ITEMS_PER_PAGE = 8
            all_anime = []
            
            # Search across all clusters
            for db_client in self.db.anime_clients:
                try:
                    db = db_client[self.db.db_name]
                    cluster_anime = await db.anime.find(
                        {},
                        {"id": 1, "title": 1, "episodes": 1, "is_sequel": 1}
                    ).sort("title", 1).to_list(None)
                    all_anime.extend(cluster_anime)
                except Exception as e:
                    logger.error(f"Error fetching anime from cluster: {e}")
                    continue
            
            # Remove duplicates
            seen_ids = set()
            unique_anime = []
            for anime in all_anime:
                if anime["id"] not in seen_ids:
                    seen_ids.add(anime["id"])
                    unique_anime.append(anime)
            
            if not unique_anime:
                await callback_query.answer("❌ No anime found in database", show_alert=True)
                return
            
            # Pagination
            total_pages = (len(unique_anime) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
            page = max(1, min(page, total_pages))
            start_idx = (page - 1) * ITEMS_PER_PAGE
            end_idx = start_idx + ITEMS_PER_PAGE
            page_anime = unique_anime[start_idx:end_idx]

            keyboard = []
            for anime in page_anime:
                btn_text = f"{anime['title']} ({anime.get('episodes', '?')} eps)"
                if anime.get('is_sequel'):
                    btn_text += " (Sequel)"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"select_sequel_{anime['id']}")])
            
            # Pagination buttons
            nav_buttons = []
            if page > 1:
                nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"link_sequel_{page-1}"))
            if page < total_pages:
                nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"link_sequel_{page+1}"))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
            
            keyboard.append([
                InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel"),
                InlineKeyboardButton("❌ Close", callback_data="close_message")
            ])
            
            await callback_query.message.edit_text(
                f"🔗 <b>Select Anime to Link as Sequel (Page {page}/{total_pages})</b>",
                reply_markup=InlineKeyboardMarkup(keyboard))
                
        except Exception as e:
            logger.error(f"Error in link_sequel_start: {e}")
            await callback_query.answer("❌ Error loading anime list", show_alert=True)

    async def select_sequel_anime(self, client: Client, callback_query: CallbackQuery, sequel_id: int, page: int = 1):
        try:
            # Find the sequel anime
            sequel = None
            for db_client in self.db.anime_clients:
                try:
                    db = db_client[self.db.db_name]
                    found = await db.anime.find_one({"id": sequel_id})
                    if found:
                        sequel = found
                        break
                except Exception as e:
                    logger.error(f"Error finding anime in cluster: {e}")
                    continue

            if not sequel:
                await callback_query.answer("❌ Anime not found", show_alert=True)
                return

            if sequel.get('is_sequel'):
                await callback_query.answer("⚠️ This anime is already a sequel!", show_alert=True)
                return

            # Store session
            self.user_sessions[callback_query.from_user.id] = {
                'linking_sequel': {
                    'sequel_id': sequel_id,
                    'sequel_title': sequel['title']
                }
            }

            limit = 10
            skip = (page - 1) * limit
            all_anime = []
            total_count = 0

            for db_client in self.db.anime_clients:
                try:
                    db = db_client[self.db.db_name]
                    total_count += await db.anime.count_documents({"id": {"$ne": sequel_id}})
                    cluster_anime = await db.anime.find(
                        {"id": {"$ne": sequel_id}},
                        {"id": 1, "title": 1, "episodes": 1}
                    ).sort("title", 1).skip(skip).limit(limit).to_list(None)
                    all_anime.extend(cluster_anime)
                except Exception as e:
                    logger.error(f"Error fetching anime from cluster: {e}")
                    continue

            # Remove duplicates
            seen_ids = set()
            unique_anime = []
            for anime in all_anime:
                if anime["id"] not in seen_ids:
                    seen_ids.add(anime["id"])
                    unique_anime.append(anime)

            if not unique_anime:
                await callback_query.answer("❌ No anime found", show_alert=True)
                return

            # Build keyboard
            keyboard = []
            for anime in unique_anime:
                btn_text = f"{anime['title']} ({anime.get('episodes', '?')} eps)"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"select_prequel_{anime['id']}")])

            # Pagination buttons
            pagination_buttons = []
            if page > 1:
                pagination_buttons.append(InlineKeyboardButton("⏮ Prev", callback_data=f"sequel_page_{sequel_id}_{page-1}"))
            if skip + limit < total_count:
                pagination_buttons.append(InlineKeyboardButton("Next ⏭", callback_data=f"sequel_page_{sequel_id}_{page+1}"))
            if pagination_buttons:
                keyboard.append(pagination_buttons)

            # Back / Cancel
            keyboard.append([
                InlineKeyboardButton("🔙 Back", callback_data="link_sequel_1"),
                InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")
            ])

            await callback_query.message.edit_text(
                f"🔗 <b>Select Prequel for:</b> {sequel['title']}\n📄 Page {page}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Error in select_sequel_anime: {e}")
            await callback_query.answer("❌ Error selecting sequel", show_alert=True)


    async def select_prequel_anime(self, client: Client, callback_query: CallbackQuery, prequel_id: int):
        try:
            user_id = callback_query.from_user.id
            if user_id not in self.user_sessions or 'linking_sequel' not in self.user_sessions[user_id]:
                await callback_query.answer("❌ Session expired", show_alert=True)
                return
            
            sequel_id = self.user_sessions[user_id]['linking_sequel']['sequel_id']
            sequel_title = self.user_sessions[user_id]['linking_sequel']['sequel_title']
            
            # Find prequel across all clusters
            prequel = None
            for db_client in self.db.anime_clients:
                try:
                    db = db_client[self.db.db_name]
                    found = await db.anime.find_one({"id": prequel_id})
                    if found:
                        prequel = found
                        break
                except Exception as e:
                    logger.error(f"Error finding anime in cluster: {e}")
                    continue
            
            if not prequel:
                await callback_query.answer("❌ Prequel not found", show_alert=True)
                return
            
            # Update both anime in all clusters
            updated = False
            for db_client in self.db.anime_clients:
                try:
                    db = db_client[self.db.db_name]
                    # Update sequel
                    await db.anime.update_one(
                        {"id": sequel_id},
                        {"$set": {
                            "prequel_id": prequel_id,
                            "is_sequel": True
                        }}
                    )
                    # Update prequel
                    await db.anime.update_one(
                        {"id": prequel_id},
                        {"$set": {"sequel_id": sequel_id}}
                    )
                    updated = True
                except Exception as e:
                    logger.error(f"Error updating cluster: {e}")
                    continue
            
            if not updated:
                raise Exception("Failed to update any cluster")
            
            # Clear session
            if user_id in self.user_sessions and 'linking_sequel' in self.user_sessions[user_id]:
                del self.user_sessions[user_id]['linking_sequel']
            
            await callback_query.message.edit_text(
                f"✅ <b>Successfully linked sequels:</b>\n\n"
                f"⏮️ <b>Prequel:</b> {prequel['title']}\n"
                f"🔜 <b>Sequel:</b> {sequel_title}\n\n"
                f"🆔 <b>Prequel ID:</b> <code>{prequel_id}</code>\n"
                f"🆔 <b>Sequel ID:</b> <code>{sequel_id}</code>",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
                ]))
                
        except Exception as e:
            logger.error(f"Error in select_prequel_anime: {e}")
            await callback_query.answer("❌ Error linking sequels", show_alert=True)
    async def view_anime_ids(self, client: Client, callback_query: CallbackQuery, page: int = 1):
        if callback_query.from_user.id not in Config.ADMINS:
            await callback_query.answer("❌ Admin only", show_alert=True)
            return
        
        try:
            ITEMS_PER_PAGE = 10
            all_anime = []
            
            # Search across all clusters
            for db_client in self.db.anime_clients:
                try:
                    db = db_client[self.db.db_name]
                    cluster_anime = await db.anime.find(
                        {},
                        {"id": 1, "title": 1, "episodes": 1, "is_sequel": 1, "prequel_id": 1, "sequel_id": 1}
                    ).sort("title", 1).to_list(None)
                    all_anime.extend(cluster_anime)
                except Exception as e:
                    logger.error(f"Error fetching anime from cluster: {e}")
                    continue
            
            # Remove duplicates
            seen_ids = set()
            unique_anime = []
            for anime in all_anime:
                if anime["id"] not in seen_ids:
                    seen_ids.add(anime["id"])
                    unique_anime.append(anime)
            
            if not unique_anime:
                await callback_query.answer("❌ No anime found in database", show_alert=True)
                return
            
            # Pagination
            total_pages = (len(unique_anime) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
            page = max(1, min(page, total_pages))
            start_idx = (page - 1) * ITEMS_PER_PAGE
            end_idx = start_idx + ITEMS_PER_PAGE
            page_anime = unique_anime[start_idx:end_idx]

            message = "🆔 <b>Anime IDs</b>\n\n"
            for anime in page_anime:
                message += f"• <b>{anime['title']}</b> ({anime.get('episodes', '?')} eps)\n"
                message += f"  🆔 <code>{anime['id']}</code>\n"
                if anime.get('is_sequel'):
                    message += f"  ⏮️ Prequel ID: <code>{anime.get('prequel_id', 'None')}</code>\n"
                if anime.get('sequel_id'):
                    message += f"  🔜 Sequel ID: <code>{anime.get('sequel_id', 'None')}</code>\n"
                message += "\n"
            
            # Pagination buttons
            keyboard = []
            if page > 1:
                keyboard.append([InlineKeyboardButton("⬅️ Previous", callback_data=f"view_ids_{page-1}")])
            if page < total_pages:
                if not keyboard:
                    keyboard.append([])
                keyboard[0].append(InlineKeyboardButton("Next ➡️", callback_data=f"view_ids_{page+1}"))
            
            keyboard.append([
                InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel"),
                InlineKeyboardButton("❌ Close", callback_data="close_message")
            ])
            
            await self.update_message(
                client,
                callback_query.message,
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )    
        except Exception as e:
            logger.error(f"Error in view_anime_ids: {e}")
            await callback_query.answer("❌ Error loading anime IDs", show_alert=True)

    async def show_anime_id(self, client: Client, callback_query: CallbackQuery, anime_id: int):
        try:
            anime = await self.db.find_anime(anime_id)
            if not anime:
                await callback_query.answer("Anime not found.", show_alert=True)
                return
            
            message = f"🆔 *Anime ID*\n\n"
            message += f"• *Title:* {anime['title']}\n"
            message += f"• *ID:* `{anime_id}`\n"
            if anime.get('is_sequel'):
                message += f"• ⏮️ *Prequel ID:* `{anime.get('prequel_id', 'None')}`\n"
            if anime.get('sequel_id'):
                message += f"• 🔜 *Sequel ID:* `{anime.get('sequel_id', 'None')}`\n"
            
            await callback_query.answer(message, show_alert=True)
        except Exception as e:
            logger.error(f"Error fetching anime ID {anime_id}: {e}")
            await callback_query.answer("Error fetching anime ID.", show_alert=True)

    async def reset_database_confirm(self, client: Client, callback_query: CallbackQuery):
        if callback_query.from_user.id not in Config.ADMINS:
            await callback_query.answer("You don't have permission to access this.", show_alert=True)
            return
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm Reset", callback_data="confirm_reset_db"),
                InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")
            ]
        ])
        
        await self.update_message(
            client,
            callback_query.message,
            "♻️ *Confirm Database Reset*\n\n"
            "⚠️ This will delete ALL data including:\n"
            "- All anime entries\n"
            "- All episode files\n"
            "- All user data\n"
            "- All statistics\n\n"
            "This action cannot be undone!",
            reply_markup=keyboard
        )

    async def reset_database(self, client: Client, callback_query: CallbackQuery):
        if callback_query.from_user.id not in Config.ADMINS:
            await callback_query.answer("You don't have permission to access this.", show_alert=True)
            return
        
        try:
            success = await self.db.reset_database()
            if success:
                await self.update_message(
                    client,
                    callback_query.message,
                    "✅ *Database reset successfully!*\n"
                    "All data has been cleared."
                )
            else:
                await self.update_message(
                    client,
                    callback_query.message,
                    "❌ *Error resetting database!*\n"
                    "Please check logs for details."
                )
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            await self.update_message(
                client,
                callback_query.message,
                "❌ *Error resetting database!*"
            )

    async def process_search(self, client: Client, message: Union[Message, CallbackQuery], page: int = 1):
        # Add force sub check
        user_id = message.from_user.id if isinstance(message, Message) else message.from_user.id
    
        # Force sub check
        if not await check_force_sub(client, user_id, message if isinstance(message, Message) else message.message):
            return
        try:
            user_id = message.from_user.id
            
            # Get search query - different handling for Message vs CallbackQuery
            if isinstance(message, Message):
                search_query = message.text.strip()
                if not search_query:
                    await message.reply_text("🔍 Please enter a valid anime name.")
                    return
            else:  # CallbackQuery
                # Extract search query from callback data (format: "search_[prev/next]_query_page")
                parts = message.data.split('_')
                direction = parts[1]
                search_query = '_'.join(parts[2:-1])  # Handle queries with underscores
                current_page = int(parts[-1])
                
                # Adjust page based on direction
                if direction == 'prev':
                    page = max(1, current_page - 1)
                else:
                    page = current_page + 1

            # Search across all clusters
            results = await self.db.search_anime(search_query, limit=100)  # Get more results for pagination
            
            if not results:
                # Fallback to regex search if no results from text search
                similar_anime = []
                for db_client in self.db.anime_clients:
                    try:
                        db = db_client[self.db.db_name]
                        cluster_results = await db.anime.find(
                            {"title": {"$regex": f".*{re.escape(search_query)}.*", "$options": "i"}},
                            {"id": 1, "title": 1, "episodes": 1}
                        ).limit(50).to_list(None)
                        similar_anime.extend(cluster_results)
                    except Exception as e:
                        logger.warning(f"Error searching anime in cluster: {e}")
                
                # Deduplicate
                seen_ids = set()
                unique_anime = []
                for anime in similar_anime:
                    if anime["id"] not in seen_ids:
                        seen_ids.add(anime["id"])
                        unique_anime.append(anime)
                results = unique_anime

            if not results:
                reply_method = message.reply_text if isinstance(message, Message) else message.message.edit_text
                await reply_method("🔍 No results found. Try a different search term.")
                return

            # Pagination
            ITEMS_PER_PAGE = 10
            total_pages = (len(results) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
            page = max(1, min(page, total_pages))
            start_idx = (page - 1) * ITEMS_PER_PAGE
            end_idx = start_idx + ITEMS_PER_PAGE
            page_results = results[start_idx:end_idx]

            # Create keyboard
            keyboard = []
            for anime in page_results:
                btn_text = f"{anime['title']} ({anime.get('episodes', '?')} eps)"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"anime_{anime['id']}")])

            # Add pagination buttons if needed
            pagination_buttons = []
            if page > 1:
                pagination_buttons.append(
                    InlineKeyboardButton("⬅️", callback_data=f"search_prev_{search_query}_{page-1}")
                )
            if end_idx < len(results):
                pagination_buttons.append(
                    InlineKeyboardButton("➡️", callback_data=f"search_next_{search_query}_{page+1}")
                )
            
            if pagination_buttons:
                keyboard.append(pagination_buttons)

            keyboard.append([
                InlineKeyboardButton("• ʙᴀᴄᴋ •", callback_data="start_menu"),
                InlineKeyboardButton("• ᴄʟᴏꜱᴇ •", callback_data="close_message")
            ])

            # Create caption
            caption = (
                f"🔍 <b>Search results for:</b> <code>{html.escape(search_query)}</code>\n"
                f"📄 <b>Page:</b> {page}/{total_pages}\n"
                f"📋 <b>Total results:</b> {len(results)}"
            )

            # Handle message differently based on input type
            if isinstance(message, CallbackQuery):
                # Edit existing message for pagination
                await self.update_message(
                    client,
                    message.message,
                    caption,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    photo=Config.START_PIC
                )
            else:
                # Send new message for initial search
                await message.reply_photo(
                    photo=Config.START_PIC,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=enums.ParseMode.HTML
                )

            # Update user stats
            await self.db.users_collection.update_one(
                {"user_id": user_id},
                {"$inc": {"searches": 1}, "$set": {"last_active": datetime.now()}}
            )
            await self.update_stats("total_searches")

        except Exception as e:
            logger.error(f"Error in process_search: {e}")
            error_msg = "⚠️ Error processing search. Please try again."
            if isinstance(message, CallbackQuery):
                await message.answer(error_msg, show_alert=True)
            else:
                await message.reply_text(error_msg)
    async def check_expiry_and_revoke(self):
        """Check and revoke expired premium access"""
        expired_users = []
        async for user in self.db.premium_users.find({"expiry_date": {"$lt": datetime.now()}}):
            expired_users.append(user['user_id'])
            await self.db.premium_users.delete_one({"_id": user['_id']})
        
        return expired_users

    async def search_anilist(self, title: str) -> Optional[Dict]:
        query = """
        query ($search: String) {
            Media(search: $search, type: ANIME) {
                id
                title {
                    romaji
                    english
                    native
                }
                description(asHtml: false)
                averageScore
                episodes
                status
                duration
                startDate {
                    year
                    month
                    day
                }
                endDate {
                    year
                    month
                    day
                }
                genres
                studios {
                    nodes {
                        name
                    }
                }
                coverImage {
                    extraLarge
                    large
                }
                trailer {
                    id
                    site
                }
                siteUrl
                isAdult
            }
        }
        """
        variables = {'search': title}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(Config.ANILIST_API, json={'query': query, 'variables': variables}) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('data', {}).get('Media')
                    return None
        except Exception as e:
            logger.error(f"Error fetching from AniList: {e}")
            return None

    async def format_description(self, description: str) -> str:
        if not description:
            return "No description available"
        
        clean = re.sub(r'<[^>]+>', '', description)
        clean = re.sub(r'\s+', ' ', clean).strip()
        if len(clean) > 500:
            clean = clean[:497] + "..."
        return clean

    async def format_date(self, date: Dict) -> str:
        if not date or not date.get('year'):
            return "N/A"
        return f"{date.get('day', '?')}/{date.get('month', '?')}/{date['year']}"

    async def delete_message_after_delay(self, client: Client, chat_id: int, message_id: int, delay: int):
        await asyncio.sleep(delay)
        try:
            await client.delete_messages(chat_id, message_id)
        except Exception as e:
            logger.error(f"Error deleting message: {e}")

    async def show_available_anime(self, client: Client, message: Message):
        try:
            keyboard = []
            row = []
            for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                row.append(InlineKeyboardButton(char, callback_data=f"letter_{char}"))
                if len(row) == 6:
                    keyboard.append(row)
                    row = []
            
            keyboard.append([
                InlineKeyboardButton("🔙 Back", callback_data="start_menu"),
                InlineKeyboardButton("❌ Close", callback_data="close_message")
            ])
            
            if isinstance(message, CallbackQuery):
                await self.update_message(
                    client,
                    message.message,
                    "🔤 Select a letter to view anime:",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    photo=Config.START_PIC
                )
            else:
                await message.reply_photo(
                    photo=Config.START_PIC,
                    caption="🔤 Select a letter to view anime:",
                    reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Show anime error: {e}")
            await message.reply_text("Error loading anime list")

    async def show_start_menu(self, client: Client, callback_query: CallbackQuery):
        user = callback_query.from_user
        welcome_text = Scripts.WELCOME_TEXT.format(first_name=user.first_name)


        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📢 ᴜᴘᴅᴀᴛᴇꜱ", url="https://t.me/TFIBOTS")
            ],
            [
                InlineKeyboardButton("📜 ʙʀᴏᴡꜱᴇ ᴀɴɪᴍᴇ", callback_data="available_anime"),
                InlineKeyboardButton("⭐ ᴡᴀᴛᴄʜʟɪꜱᴛ", callback_data="view_watchlist")
            ],
            [
                InlineKeyboardButton("❌ ᴄʟᴏꜱᴇ", callback_data="close_message")
            ]
        ])

        
        if user.id in Config.ADMINS:
            keyboard.inline_keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")])
        
        try:
            await self.update_message(
                client,
                callback_query.message,
                welcome_text,
                reply_markup=keyboard,
                photo=Config.START_PIC
            )
        except Exception as e:
            logger.error(f"Error showing start menu: {e}")
            await callback_query.answer("Error returning to start menu.")
    async def get_anime_title(self, anime_id: int) -> str:
        anime = await self.db.find_anime(anime_id)
        return anime.get('title', f"Anime {anime_id}")

    async def get_anime_type(self, anime_id: int) -> str:
        anime = await self.db.find_anime(anime_id)
        return anime.get('type', 'TV')

    async def get_episode_count(self, anime_id: int) -> int:
        anime = await self.db.find_anime(anime_id)
        return anime.get('episodes', 1)
    async def show_anime_by_letter(self, client: Client, callback_query: CallbackQuery, letter: str, page: int = 1):
        try:
            ITEMS_PER_PAGE = 8  # Number of items per page
            
            # Search across all clusters for anime starting with the letter
            anime_list = []
            for db_client in self.db.anime_clients:
                try:
                    db = db_client[self.db.db_name]
                    cluster_results = await db.anime.find(
                        {"title": {"$regex": f"^{letter}", "$options": "i"}},
                        {"id": 1, "title": 1, "episodes": 1, "studio": 1}
                    ).sort("title", 1).to_list(None)
                    anime_list.extend(cluster_results)
                except Exception as e:
                    logger.warning(f"Error searching anime in cluster {db_client}: {e}")
            
            # Deduplicate
            seen_ids = set()
            unique_anime = []
            for anime in anime_list:
                if anime["id"] not in seen_ids:
                    seen_ids.add(anime["id"])
                    unique_anime.append(anime)
            
            if not unique_anime:
                await callback_query.answer(f"No anime found starting with '{letter}'.", show_alert=True)
                return

            # Calculate pagination
            total_pages = (len(unique_anime) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
            page = max(1, min(page, total_pages))  # Clamp page to valid range
            start_idx = (page - 1) * ITEMS_PER_PAGE
            end_idx = start_idx + ITEMS_PER_PAGE
            page_anime = unique_anime[start_idx:end_idx]

            keyboard = []
            for anime in page_anime:
                btn_text = f"{anime['title']} ({anime.get('episodes', '?')} eps)"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"anime_{anime['id']}")])

            # Add pagination controls if needed
            pagination_buttons = []
            if page > 1:
                pagination_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"letter_{letter}_{page-1}"))
            if end_idx < len(unique_anime):
                pagination_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"letter_{letter}_{page+1}"))
            
            if pagination_buttons:
                keyboard.append(pagination_buttons)

            keyboard.append([
                InlineKeyboardButton("• ʙᴀᴄᴋ •", callback_data="available_anime"),
                InlineKeyboardButton("• ᴄʟᴏꜱᴇ •", callback_data="close_message")
            ])
            
            await self.update_message(
                client,
                callback_query.message,
                f"🌀 <b>Anime starting with '{letter}' (Page {page}/{total_pages}):</b>",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Error fetching anime by letter {letter}: {e}")
            await callback_query.answer("⚠️ Error fetching anime list. Please try again.", show_alert=True)
    async def today_schedule_command(self, client: Client, message: Message):
        """Show today's anime schedule with auto-delete"""
        try:
            # Show loading message that will auto-delete
            processing_msg = await message.reply_text("⌛ Fetching today's releases...")
            
            # Fetch schedule data
            schedule_data = await self.fetch_schedule()
            if not schedule_data:
                await processing_msg.edit_text("⚠️ Failed to fetch schedule. Try again later.")
                await asyncio.sleep(10)
                await processing_msg.delete()
                return
                
            # Format the schedule
            message_text = await self.format_schedule_message(schedule_data)
            
            # Delete processing message first
            await processing_msg.delete()
            
            # Send the schedule message
            sent_msg = await message.reply_text(
                message_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            
            # Auto-delete after 1 hour (3600 seconds)
            await asyncio.sleep(3600)
            await sent_msg.delete()
                
        except Exception as e:
            logger.error(f"Schedule error: {e}")
            error_msg = await message.reply_text("❌ Error loading schedule.")
            await asyncio.sleep(10)
            await error_msg.delete()

    async def fetch_schedule(self):
        """Fetch schedule data from subsplease API"""
        url = "https://subsplease.org/api/?f=schedule&h=true&tz=Asia/Kolkata"
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        }
        
        try:
            async with ClientSession(timeout=ClientTimeout(total=15)) as session:
                async with session.get(url, headers=headers) as response:
                    text = await response.text()
                    if response.status == 200:
                        try:
                            data = json.loads(text)
                            return data.get("schedule", [])
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON: {text[:200]}")
                            return None
        except Exception as e:
            logger.error(f"Fetch error: {e}")
        return None

    async def format_schedule_message(self, schedule_data):
        """Format the schedule with clean styling"""
        today = datetime.now().strftime("%A")
        current_time = datetime.now().strftime("%I:%M %p")
        
        # Clean styles without ratings
        styles = [
            lambda t, time: f"• <b>{t}</b> ━ <code>{time}</code>",
            lambda t, time: f"▷ <b>{t}</b> • <code>{time}</code>",
            lambda t, time: f"‣ <b>{t}</b> │ <code>{time}</code>",
            lambda t, time: f"◇ <b>{t}</b> ━━ <code>{time}</code>",

            # NEW STYLES BELOW:
            lambda t, time: f"⭐ <b>{t}</b>\n⏰ <code>{time}</code>",
            lambda t, time: f"🔹 <b>{t}</b> — <code>{time}</code>",
            lambda t, time: f"🕒 <b>{t}</b>\n<code>{time}</code>",
            lambda t, time: f"🔸 <b>{t}</b> • <code>{time}</code>",
            lambda t, time: f"✦ <b>{t}</b> ─ <code>{time}</code>",
            lambda t, time: f"📺 <b>{t}</b>\n🕐 <code>{time}</code>",
            lambda t, time: f"🎬 <b>{t}</b> • <code>{time}</code>",
            lambda t, time: f"📌 <b>{t}</b> ━ <code>{time}</code>",
            lambda t, time: f"📍 <b>{t}</b>\n<code>{time}</code>",
            lambda t, time: f"🎯 <b>{t}</b> │ <code>{time}</code>"
        ]

        # Process shows (limited to 12)
        entries = []
        for anime in schedule_data[:12]:
            title = anime.get("title", "Unknown")
            time_str = anime.get("time", "?")
            style = random.choice(styles)
            entries.append(style(title, time_str))
        
        # Modern header/footer design
        header = (
            f"🌸 <b>ANIME SCHEDULE</b> 🌸\n"
            f"🗓️ <b>{today.upper()}</b>\n"
            f"🕒 <i>Last updated:</i> <code>{current_time} IST</code>\n\n"
        )

        
        footer = (
            f"\n🌸 <b>That's all for today!</b>\n"
            f"📡 <b>Total Releases:</b> <code>{len(entries)}</code>"
        )


        
        return header + "\n".join(entries) + footer
        
    async def check_download_limit(self, user_id: int) -> Tuple[bool, str]:
        """Check if user has reached daily download limit"""
        try:
            # If premium mode is OFF, no limits apply
            if not self.config.PREMIUM_MODE:
                return True, ""
                
            user = await self.db.users_collection.find_one({"user_id": user_id})
            if not user:
                return True, ""  # New user has no limits
                
            today = datetime.now().date().isoformat()
            last_download_date = user.get('last_download_date')
            
            # Reset counter if new day
            if last_download_date != today:
                await self.db.users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"download_count": 0, "last_download_date": today}}
                )
                return True, ""
                
            # Get user's access level
            access_level = 0  # Default to normal
            premium_user = await self.db.premium_users.find_one({"user_id": user_id})
            
            if premium_user:
                if premium_user.get('plan_type') == 'hpremium':
                    access_level = 2
                else:
                    access_level = 1
                    
            max_downloads = self.config.MAX_DAILY_DOWNLOADS.get(access_level, 30)
            
            # Unlimited downloads (-1 means unlimited)
            if max_downloads == -1:
                return True, ""
                
            if user.get('download_count', 0) >= max_downloads:
                reset_time = datetime.combine(
                    datetime.now().date() + timedelta(days=1),
                    datetime.min.time()
                )
                time_left = reset_time - datetime.now()
                hours = time_left.seconds // 3600
                minutes = (time_left.seconds % 3600) // 60
                return False, (
                    f"⚠️ Daily download limit reached ({max_downloads}).\n"
                    f"Resets in {hours}h {minutes}m.\n"
                    "Upgrade to premium for unlimited downloads."
                )
            return True, ""
        except Exception as e:
            logger.error(f"Error checking download limit: {e}")
            return True, ""  # Fail open to avoid blocking downloadsoid blocking downloads

    async def daily_reset_task(self):
        """Reset daily counters and perform maintenance"""
        while True:
            try:
                now = datetime.now()
                # Calculate time until midnight
                next_day = now + timedelta(days=1)
                midnight = datetime(next_day.year, next_day.month, next_day.day)
                wait_seconds = (midnight - now).total_seconds()
                
                await asyncio.sleep(wait_seconds)
                
                # Reset download counters
                await self.db.users_collection.update_many(
                    {},
                    {"$set": {"download_count": 0, "last_download_date": datetime.now().date().isoformat()}}
                )
                
                logger.info("Daily counters reset completed")
                
            except Exception as e:
                logger.error(f"Daily reset error: {e}")
                await asyncio.sleep(3600)  # Retry after 1 hour if error occurs    
    async def handle_callback_query(self, client: Client, callback_query: CallbackQuery):
        try:
            data = callback_query.data
            user_id = callback_query.from_user.id
            message = callback_query.message

            # ⛔ Reject other users in group menus
            if message and message.chat and message.chat.type != ChatType.PRIVATE:
                session = self.user_sessions.get(message.id)
                if session:
                    original_user = session.get("original_user")
                    if original_user and user_id != original_user:
                        await callback_query.answer("⚠️ This menu is not for you.", show_alert=True)
                        return

            # ⏱️ Rate limiting check
            if not await self.check_rate_limit(user_id):
                await callback_query.answer("Please wait before performing another action.", show_alert=True)
                return


            # ========================
            # 🔐 Premium System Handlers
            # ========================
 
        
            if data == "premium_management":
                if user_id in self.config.OWNERS:
                    await self.premium.premium_management(client, callback_query)
                else:
                    await callback_query.answer("❌ Admin/Owner only", show_alert=True)

            elif data == "grant_premium_menu":
                if user_id in self.config.OWNERS:
                    await self.premium.grant_premium_menu(client, callback_query)
                else:
                    await callback_query.answer("❌ Admin/Owner only", show_alert=True)

            elif data == "revoke_premium_menu":
                if user_id in self.config.OWNERS:
                    await self.premium.revoke_premium_menu(client, callback_query)
                else:
                    await callback_query.answer("❌ Admin/Owner only", show_alert=True)

            elif data in ["grant_premium", "grant_hpremium"]:
                if user_id in self.config.OWNERS:
                    plan_type = data.split("_")[1]
                    await self.premium.start_grant_process(client, callback_query, plan_type)
                else:
                    await callback_query.answer("❌ Admin/Owner only", show_alert=True)

            elif data.startswith("grant_premium_") or data.startswith("grant_hpremium_"):
                if user_id in self.config.OWNERS:
                    parts = data.split("_")
                    plan_type = parts[1]
                    duration = parts[2]
                    await self.premium.process_grant_callback(client, callback_query, plan_type, duration)
                else:
                    await callback_query.answer("❌ Admin/Owner only", show_alert=True)

            elif data == "grant_custom":
                if user_id in self.config.OWNERS:
                    self.user_sessions[user_id] = {
                        'action': 'grant_custom',
                        'message_id': callback_query.message.id
                    }
                    await callback_query.message.edit_text(
                        "⏳ **Enter Custom Grant Command**\n\n"
                        "Format: `/grant <user_id/username> <duration> <plan_type>`\n\n"
                        "Examples:\n"
                        "• `/grant @username 7d premium`\n"
                        "• `/grant 123456789 1M hpremium`\n"
                        "• `/grant @user 0 premium` (for lifetime)\n\n"
                        "Duration formats:\n"
                        "- Minutes: 30m\n"
                        "- Hours: 12h\n"
                        "- Days: 7d\n"
                        "- Weeks: 2w\n"
                        "- Months: 3M\n"
                        "- Years: 1y\n"
                        "- 0 for lifetime",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Back", callback_data="grant_premium_menu")]
                        ])
                    )
                else:
                    await callback_query.answer("❌ Admin/Owner only", show_alert=True)

            elif data == "grant_lifetime":
                if user_id in self.config.OWNERS:
                    self.user_sessions[user_id] = {
                        'action': 'grant_lifetime',
                        'message_id': callback_query.message.id
                    }
                    await callback_query.message.edit_text(
                        "♾️ **Enter Lifetime Grant Command**\n\n"
                        "Format: `/grant <user_id/username> 0 <plan_type>`\n\n"
                        "Examples:\n"
                        "• `/grant @username 0 premium`\n"
                        "• `/grant 123456789 0 hpremium`",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Back", callback_data="grant_premium_menu")]
                        ])
                    )
                else:
                    await callback_query.answer("❌ Admin/Owner only", show_alert=True)

            elif data.startswith("list_premium_"):
                if user_id in self.config.ADMINS + self.config.OWNERS:
                    parts = data.split("_")
                    filter_type = parts[2] if len(parts) > 2 else "active"
                    await self.premium.list_premium_users(client, callback_query, filter_type)
                else:
                    await callback_query.answer("❌ Admin/Owner only", show_alert=True)
            elif data.startswith("premium_list_"):
                try:
                    page = int(callback_query.data.split("_")[-1])
                    await self.premium_users_menu(client, callback_query.message)
                    await callback_query.answer()
                except Exception as e:
                    logger.error(f"Error in premium_list_callback: {e}")
                    await callback_query.answer("Error refreshing list", show_alert=True)
            elif data.startswith("revoke_"):
                if user_id in self.config.OWNERS:
                    try:
                        target_id = int(data.split("_")[1])
                        await self.premium.revoke_access(target_id)
                        await callback_query.answer(f"Revoked premium for user {target_id}")
                        await self.premium.list_premium_users(client, callback_query, "active")
                    except (IndexError, ValueError):
                        await callback_query.answer("❌ Invalid user ID", show_alert=True)
                else:
                    await callback_query.answer("❌ Owner only", show_alert=True)

            elif data == "premium_plans":
                await self.premium.show_premium_plans(client, callback_query)

            elif data == "hpremium_plans":
                await self.premium.show_hpremium_plans(client, callback_query)

            elif data.startswith("premium_benefits"):
                try:
                    plan_type = data.split("_")[2] if len(data.split("_")) > 2 else "premium"
                    await self.premium.show_premium_benefits(client, callback_query, plan_type)
                except Exception as e:
                    logger.error(f"Error showing benefits: {e}")
                    await callback_query.answer("❌ Error showing benefits", show_alert=True)

            elif data == "premium_faq":
                await self.premium.show_premium_faq(client, callback_query)

            elif data == "premium_stats":
                if user_id in self.config.OWNERS:
                    await self.premium.show_premium_stats(client, callback_query)
                else:
                    await callback_query.answer("❌ Owner only", show_alert=True)

            elif data == "toggle_premium_mode":
                if user_id in self.config.OWNERS:
                    await self.premium.toggle_premium_mode(client, callback_query)
                else:
                    await callback_query.answer("❌ Owner only", show_alert=True)

            elif data == "revoke_by_id":
                if user_id in self.config.OWNERS:
                    await callback_query.message.edit_text(
                        "Enter user ID/username to revoke:\n\n"
                        "Example: `/revoke @username` or `/revoke 123456789`",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Back", callback_data="revoke_premium_menu")]
                        ])
                    )
                else:
                    await callback_query.answer("❌ Owner only", show_alert=True)

            elif data == "list_to_revoke":
                if user_id in self.config.OWNERS:
                    await self.premium.list_premium_users(client, callback_query, "active")
                else:
                    await callback_query.answer("❌ Owner only", show_alert=True)

            elif data.startswith(("renew_", "purchase_")):
                await callback_query.answer("💳 Payment system coming soon!", show_alert=True)

            elif data == "my_plan_back":
                if callback_query.message:
                    await callback_query.message.delete()
                await self.premium.show_my_plan(client, callback_query.message)
            # ========================
            #  Forcesub Handlers
            # ========================


                # Add force subscription handlers
            elif data == "check_force_sub":
                joined = await self.force_sub.check_member(client, user_id)
                if joined:
                    await callback_query.answer("✅ Thanks for joining!", show_alert=True)
                    await callback_query.message.delete()
                    # Restart the command they were trying to access
                    await self.start(client, callback_query.message)
                else:
                    await callback_query.answer("❗ You're still missing one or more channels.", show_alert=True)
                return
                
            elif data == "force_sub_settings":
                await self.force_sub.show_settings(client, callback_query.message)
                return
                
            elif data == "toggle_force_sub":
                await self.force_sub.toggle_force_sub(not self.force_sub.force_sub_enabled)
                await self.force_sub.show_settings(client, callback_query.message)
                return
                
            elif data == "add_force_sub_channel":
                await callback_query.message.delete()
                await self.force_sub.add_channel_start(client, callback_query.message)
                return
                
            elif data == "remove_force_sub_channel":
                await callback_query.message.delete()
                await self.force_sub.remove_channel_start(client, callback_query.message)
                return
            # ========================
            # ⚙️ Settings Handlers
            # ========================
            elif data == "admin_settings" or data.startswith(("set_", "setval_")):
                await self.handle_setting_callback(client, callback_query)
                
            elif data == "change_download_limits":
                await self.change_download_limits(client, callback_query)
                
            elif data.startswith("set_limit_"):
                level = data.split("_")[2]
                await self.set_download_limit_start(client, callback_query, level)
            elif data == "set_rate_limit":
                await self.rate_limit_setting(client, callback_query)

            elif data.startswith("setval_rate_limit_"):
                try:
                    new_value = int(data.split("_")[-1])
                    if not (1 <= new_value <= 60):
                        raise ValueError("Value must be between 1-60")
                    
                    await self.db.stats_collection.update_one(
                        {"type": "global"},
                        {"$set": {"settings.rate_limit": new_value}},
                        upsert=True
                    )
                    
                    Config.RATE_LIMIT = new_value
                    await callback_query.message.edit_text(
                        f"✅ Rate limit set to {new_value} messages/second",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Back to Settings", callback_data="admin_settings")]
                        ])
                    )
                except Exception as e:
                    await callback_query.answer(f"Invalid value: {str(e)}", show_alert=True)  
            elif data == "restrict_settings":
                await self.show_restrict_settings(client, callback_query)
            elif data == "toggle_premium_mode":
                await self.toggle_premium_mode(client, callback_query)
            elif data == "toggle_restrict_adult":
                if user_id in self.config.OWNERS:
                    await self.toggle_restrict_adult(client, callback_query)
                else:
                    await callback_query.answer("❌ Owner only", show_alert=True)
            # In your callback query handler
            # In your callback query handler
            elif data.startswith("del_menu_"):
                _, _, anime_id, page = data.split("_")  # always 4 parts now
                await self.admin_delete_episode_menu(client, callback_query, int(anime_id), int(page))



            elif data.startswith("del_ep_"):
                parts = data.split("_")
                anime_id = int(parts[2])
                episode = int(parts[3])
                await self.confirm_delete_episode(client, callback_query, anime_id, episode)
            elif data.startswith("confirm_del_all_"):
                anime_id = int(data.split("_")[3])
                await self.confirm_delete_all_episodes(client, callback_query, anime_id)
            elif data.startswith("confirm_del_"):
                parts = data.split("_")
                anime_id = int(parts[2])
                episode = int(parts[3])
                await self.delete_episode(client, callback_query, anime_id, episode)
            elif data.startswith("del_all_"):
                anime_id = int(data.split("_")[2])
                await self.delete_all_episodes(client, callback_query, anime_id)
            # ========================
            # ⚙️ saga Handlers
            # ========================

            # In handle_callback_query method, add these cases:
            elif data.startswith("sagas_"):
                anime_id = int(data.split("_")[1])
                await self.show_saga_list(client, callback_query, anime_id)

         # In your handle_callback_query method, add these checks:
            elif data.startswith("saga_"):
                parts = data.split("_")
                anime_id = int(parts[1])
                saga_id = int(parts[2])
                
                # Check if files exist before showing arcs
                files_exist, message = await self.check_saga_arc_files_exist(anime_id, saga_id)
                if not files_exist:
                    await callback_query.answer(message, show_alert=True)
                    return
                    
                await self.show_saga_arcs(client, callback_query, anime_id, saga_id)

            elif data.startswith("arc_"):
                parts = data.split("_")
                anime_id = int(parts[1])
                saga_id = int(parts[2])
                arc_id = int(parts[3])
                
                # Check if files exist before showing episodes
                files_exist, message = await self.check_saga_arc_files_exist(anime_id, saga_id, arc_id)
                if not files_exist:
                    await callback_query.answer(message, show_alert=True)
                    return
                    
                await self.show_arc_episodes(client, callback_query, anime_id, saga_id, arc_id)

           # Add this new case to handle the actual bulk download with quality
     # In your main callback query handler
            elif data.startswith("bulk_saga_"):
                parts = data.split('_')
                if len(parts) >= 5:
                    anime_id = int(parts[2])
                    saga_id = int(parts[3])
                    quality = parts[4]
                    await self._process_bulk_saga_download(client, callback_query, anime_id, saga_id, quality)
                else:
                    await callback_query.answer("Invalid bulk saga request.", show_alert=True)

            elif data.startswith("bulk_arc_"):
                parts = data.split('_')
                if len(parts) >= 6:
                    anime_id = int(parts[2])
                    saga_id = int(parts[3])
                    arc_id = int(parts[4])
                    quality = parts[5]
                    await self._process_bulk_arc_download(client, callback_query, anime_id, saga_id, arc_id, quality)
                else:
                    await callback_query.answer("Invalid bulk arc request.", show_alert=True)
            # ========================
            # 👑 Owner Tools Handlers
            # ========================
            elif data == "owner_tools":
                await self.owner_tools(client, callback_query)
                
            elif data == "owner_add":
                await self.add_owner_start(client, callback_query)
                
            elif data == "owner_remove":
                await self.remove_owner_start(client, callback_query)
                
            elif data == "owner_list_admins":
                await self.list_admins(client, callback_query)
                
            elif data == "owner_reset_db":
                await self.reset_database_confirm(client, callback_query)
                
            elif data == "confirm_reset_db":
                await self.reset_database(client, callback_query)

            # ========================
            # 📺 Anime Browsing Handlers
            # ========================
            elif data == "start_menu":
                await self.show_start_menu(client, callback_query)
                
            elif data == "close_message":
                await self.close_message(client, callback_query)
                
            elif data == "available_anime":
                await self.show_available_anime(client, callback_query)
                
            elif data.startswith("browse_"):
                letter = data.split("_")[1]
                await self.show_anime_by_letter(client, callback_query, letter)
                
            elif data.startswith("letter_"):
                parts = callback_query.data.split("_")
                letter = parts[1]
                page = int(parts[2]) if len(parts) > 2 else 1
                await self.show_anime_by_letter(client, callback_query, letter, page)
            elif data.startswith("anime_"):
                anime_id = int(data.split("_")[1])
                await self.show_anime_details(client, callback_query, anime_id)
                
            elif data.startswith("episodes_"):
                parts = data.split("_")
                anime_id = int(parts[1])
                page = int(parts[2]) if len(parts) > 2 else 1
                await self.show_episodes(client, callback_query, anime_id, page)
                
            elif data.startswith("ep_page_"):
                parts = data.split("_")
                anime_id = int(parts[2])
                page = int(parts[3])
                await self.show_episodes(client, callback_query, anime_id, page)
            elif data.startswith("recent_page_"):
                page = int(data.split("_")[-1])  # ✅ Use 'data', not 'callback_data'
                await self.show_recent_updates(client, callback_query, page)
            elif data.startswith("ep_"):
                parts = data.split("_")
                anime_id = int(parts[1])
                episode = int(parts[2])
                await self.show_episode_options(client, callback_query, anime_id, episode)
                
            elif data.startswith("dl_"):
                file_id = data.split("_")[1]
                await self.download_episode_file(client, callback_query, file_id)
            elif data.startswith("download_all_"):
                anime_id = int(data.split("_")[-1])  
                await self.show_bulk_quality_menu(client, callback_query, anime_id)
                
            elif data.startswith("back_to_episodes_"):
                anime_id = int(data.split("_")[-1])
                await self.show_episodes(client, callback_query, anime_id)

            # In your handle_callback_query method, update the bulk download handling:
            elif data.startswith("bulk_"):
                # Let the new process_bulk_download method handle all bulk download types
                await self.process_bulk_download(client, callback_query, data)

            elif data.startswith("toggle_watchlist_"):
                anime_id = int(data.split("_")[2])
                await self.toggle_watchlist(client, callback_query, anime_id)
                
            elif data == "view_watchlist":
                await self.view_watchlist(client, callback_query)
                
            elif data.startswith("ongoing_page_"):
                page = int(data.split("_")[-1])
                await bot.ongoing_command(client, callback_query, page)    
            elif data == "recent_updates":
                await self.show_recent_updates(client, callback_query)
                
            elif data == "search_anime":
                await self.search_anime(client, callback_query.message)
            elif data.startswith(("search_prev_", "search_next_")):
                await self.process_search(client, callback_query)
            # ========================
            # 👮 Admin Panel Handlers
            # ========================
            elif data == "admin_panel":
                await self.admin_panel(client, callback_query)
                
            elif data == "admin_stats":
                await self.show_stats(client, callback_query)
                
            elif data == "admin_add_anime":
                await self.add_anime_start(client, callback_query)
                
            elif data.startswith("admin_edit_anime_"):
                anime_id = int(data.split("_")[3]) if len(data.split("_")) > 3 else None
                await self.edit_anime_start(client, callback_query, anime_id)
                
            elif data.startswith("admin_delete_anime_"):
                anime_id = int(data.split("_")[3]) if len(data.split("_")) > 3 else None
                await self.delete_anime_start(client, callback_query, anime_id)
                
            elif data.startswith("confirm_delete_anime_"):
                anime_id = int(data.split("_")[3])
                await self.delete_anime_confirm(client, callback_query, anime_id)
                
            elif data.startswith("confirm_delete_episodes_"):
                anime_id = int(data.split("_")[3])
                await self.confirm_delete_episodes(client, callback_query, anime_id)
                
            elif data.startswith("cancel_delete_episodes_"):
                anime_id = int(data.split("_")[3])
                await self.cancel_delete_episodes(client, callback_query, anime_id)
                
            elif data == "admin_add_episodes":
                await self.add_episodes_start(client, callback_query)
                
            elif data.startswith("admin_add_episodes_"):
                anime_id = int(data.split("_")[-1])
                user_id = callback_query.from_user.id
                
                # Store in session
                self.user_sessions[user_id] = {
                    'state': 'adding_episodes',
                    'add_episodes': {
                        'anime_id': anime_id,
                        'anime_title': await self.get_anime_title(anime_id),
                        'anime_type': await self.get_anime_type(anime_id)
                    }
                }
                
                # Show instructions
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data=f"anime_{anime_id}")]
                ])
                
                anime_type = await self.get_anime_type(anime_id)
                type_info = Config.ANIME_TYPES.get(anime_type, {})
                
                if not type_info.get('has_episodes'):
                    message = (
                        f"🎬 <b>{await self.get_anime_title(anime_id)}</b>\n"
                        f"📁 <i>{type_info.get('name', anime_type)}</i>\n\n"
                        "This is a single-file release. Just send the file now."
                    )
                else:
                    message = (
                        f"🎬 <b>{await self.get_anime_title(anime_id)}</b>\n"
                        f"📺 <i>{await self.get_episode_count(anime_id)} episodes</i>\n\n"
                        "You can:\n"
                        "1. Send files with episode numbers in filename\n"
                        "2. Or reply with /episode <number> first\n"
                        "3. Or /done when finished"
                    )
                
                await self.update_message(
                    client,
                    callback_query.message,
                    message,
                    reply_markup=keyboard
                )
                await callback_query.answer()
                
            elif data.startswith("admin_episodes_page_"):
                page = int(data.split("_")[-1])
                await self.add_episodes_start(client, callback_query, page)
                
            elif data.startswith("admin_select_anime_"):
                anime_id = int(data.split("_")[-1])
                await self.select_anime_for_episodes(client, callback_query, anime_id)
                
            elif data == "admin_link_sequel":
                await self.link_sequel_start(client, callback_query)
            elif data.startswith("link_sequel_page_"):
                page = int(data.split("_")[-1])
                await self.link_sequel_start(client, callback_query, page)
            elif data.startswith("select_sequel_"):
                sequel_id = int(data.split("_")[2])
                await self.select_sequel_anime(client, callback_query, sequel_id, page=1)  # default to page 1

            elif data.startswith("select_prequel_"):
                prequel_id = int(data.split("_")[2])
                await self.select_prequel_anime(client, callback_query, prequel_id)

            elif data.startswith("sequel_page_"):
                parts = data.split("_")
                if len(parts) == 4:
                    sequel_id = int(parts[2])
                    page = int(parts[3])
                    await self.select_sequel_anime(client, callback_query, sequel_id, page)

            elif data.startswith("link_sequel"):
                page = int(data.split("_")[2]) if len(data.split("_")) > 2 else 1
                await self.link_sequel_start(client, callback_query, page)
                
            elif data == "admin_view_ids":
                await self.view_anime_ids(client, callback_query, page=1)
            elif data.startswith("show_id_"):
                anime_id = int(data.split("_")[2])
                anime = await self.db.find_anime(anime_id)
                if anime:
                    msg = (
                        f"🆔 Anime ID: <code>{anime_id}</code>\n"
                        f"📺 Title: {anime.get('title', 'Unknown')}\n"
                        f"🔗 Type: {anime.get('type', 'TV')}\n"
                    )
                    if anime.get('prequel_id'):
                        msg += f"⏮️ Prequel ID: <code>{anime['prequel_id']}</code>\n"
                    if anime.get('sequel_id'):
                        msg += f"⏭️ Sequel ID: <code>{anime['sequel_id']}</code>"
                    await callback_query.answer(msg, show_alert=True)
                else:
                    await callback_query.answer("Anime not found", show_alert=True)
            elif data.startswith("view_ids_"):
                try:
                    page = int(data.split("_")[2])
                    await self.view_anime_ids(client, callback_query, page=page)
                except Exception as e:
                    logger.error(f"Error parsing view_ids page: {e}")
                    await callback_query.answer("❌ Invalid page", show_alert=True)

            elif data == "admin_add_admin":
                await self.add_admin_start(client, callback_query)
                
            elif data == "admin_remove_admin":
                await self.remove_admin_start(client, callback_query)
                
            elif data == "admin_add_db_channel":
                await self.add_db_channel_start(client, callback_query)
                
            elif data == "admin_remove_db_channel":
                await self.remove_db_channel_start(client, callback_query)
                
            elif data.startswith("select_remove_db_channel_"):
                channel_id = int(data.split("_")[4])
                await self.remove_db_channel(client, callback_query, channel_id)

            # ========================
            # 📝 Request System Handlers
            # ========================
           
            elif data.startswith(("request_detail:", "requests_page:", "approve_req:", "reject_req:", "close_notification","close_req","mark_uploaded",
                           "confirm_delete_all", "cancel_delete_all")):
                await self.request_system.handle_request_callbacks(client, callback_query)
        
            # ========================
            # ❓ Unknown Callback
            # ========================
            else:
                await callback_query.answer("Unknown action", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error handling callback query: {e}", exc_info=True)
            await callback_query.answer("An error occurred. Please try again.", show_alert=True)

    def get_back_button(self, back_to: str) -> InlineKeyboardButton:
        """Returns a consistent back button"""
        back_targets = {
            "admin": ("admin_panel", "🔙 Admin Panel"),
            "start": ("start_menu", "🔙 Main Menu"),
            "premium": ("premium_management", "🔙 Premium Panel"),
            "anime": ("available_anime", "🔙 Anime List"),
            "settings": ("admin_settings", "🔙 Settings"),
            "owner": ("owner_tools", "🔙 Owner Tools")
        }
        return InlineKeyboardButton(back_targets[back_to][1], 
                                callback_data=back_targets[back_to][0])
    # In the main bot class (where toggle_restrict_adult is defined)
    async def toggle_restrict_adult(self, client: Client, callback_query: CallbackQuery):
        """Toggle adult content restriction"""
        if callback_query.from_user.id in self.config.OWNERS:
            self.config.RESTRICT_ADULT = not self.config.RESTRICT_ADULT
            os.environ["RESTRICT_ADULT"] = str(self.config.RESTRICT_ADULT)
            status = "ON" if self.config.RESTRICT_ADULT else "OFF"
            await callback_query.answer(f"Adult restriction {status}")
            # Refresh the settings menu
            await self.show_restrict_settings(client, callback_query)
        else:
            await callback_query.answer("❌ Owner only", show_alert=True)

    async def show_restrict_settings(self, client: Client, callback_query: CallbackQuery):
        """Show restriction settings panel"""
        if callback_query.from_user.id not in self.config.ADMINS:
            await callback_query.answer("❌ Admin only", show_alert=True)
            return
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"💎 Premium Mode: {'ON' if self.config.PREMIUM_MODE else 'OFF'}",
                    callback_data="toggle_premium_mode"
                )
            ],
            [
                InlineKeyboardButton(
                    f"🔞 Adult Restriction: {'ON' if self.config.RESTRICT_ADULT else 'OFF'}",
                    callback_data="toggle_restrict_adult"
                )
            ],
            [self.get_back_button("admin")]
        ])
        
        await self.update_message(
            client,
            callback_query.message,
            "⚙️ *Restriction Settings*\n\n"
            "Control access to sensitive content:",
            reply_markup=keyboard
        )

    async def set_limit_command(self, client: Client, message: Message):
        """Set daily download limits for user tiers"""
        if message.from_user.id not in Config.OWNERS:
            await message.reply_text("❌ Owner only command")
            return
            
        if len(message.command) < 3:
            await message.reply_text(
                "Usage: /setlimit <level> <amount>\n\n"
                "Levels:\n"
                "• normal - Free users\n"
                "• premium - Premium users\n"
                "• hpremium - H-Premium users\n\n"
                "Use -1 for unlimited downloads\n"
                "Use 0 to disable downloads for this level"
            )
            return
            
        level = message.command[1].lower()
        try:
            amount = int(message.command[2])
            
            # Validate level
            if level not in ['normal', 'premium', 'hpremium']:
                raise ValueError("Invalid level. Use normal/premium/hpremium")
                
            # Validate amount
            if amount < -1:
                raise ValueError("Amount must be -1 (unlimited) or 0+")
                
            # Update config
            if level == "normal":
                Config.MAX_DAILY_DOWNLOADS[0] = amount
            elif level == "premium":
                Config.MAX_DAILY_DOWNLOADS[1] = amount
            elif level == "hpremium":
                Config.MAX_DAILY_DOWNLOADS[2] = amount
                
            # Save to database
            await self.db.stats_collection.update_one(
                {"type": "global"},
                {"$set": {f"settings.download_limits.{level}": amount}},
                upsert=True
            )
            
            await message.reply_text(
                f"✅ Set {level} daily download limit to {amount} "
                f"({'unlimited' if amount == -1 else str(amount)})"
            )
        except Exception as e:
            await message.reply_text(f"❌ Error: {str(e)}")

    async def rate_limit_setting(self, client: Client, callback_query: CallbackQuery):
        """Proper rate limit setting handler"""
        try:
            # Get current value
            stats = await self.db.stats_collection.find_one({"type": "global"})
            current_limit = stats.get("settings", {}).get("rate_limit", Config.RATE_LIMIT)
            
            # Create keyboard with options
            keyboard = []
            for limit in [5, 10, 15, 20, 30, 60]:
                selected = "✅" if limit == current_limit else ""
                keyboard.append(
                    [InlineKeyboardButton(
                        f"{selected} {limit} msg/sec", 
                        callback_data=f"set_rate_{limit}"
                    )]
                )
            
            keyboard.append([self.get_back_button("settings")])
            
            await callback_query.message.edit_text(
                "⚙️ **Set Rate Limit**\n\n"
                "Select maximum messages per second:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Rate limit setting error: {e}")
            await callback_query.answer("Error loading rate limit settings", show_alert=True)
    async def remove_admin_command(self, client: Client, message: Message):
        """Remove an admin"""
        if message.from_user.id not in Config.OWNERS:
            await message.reply_text("❌ Owner only command")
            return

        if len(message.command) < 2:
            await message.reply_text("Usage: /removeadmin <user_id>")
            return

        try:
            user_id = int(message.command[1])
            
            # Can't remove owners
            if user_id in Config.OWNERS:
                await message.reply_text("❌ Cannot remove owners using this command")
                return
                
            # Remove from database
            result = await self.db.admins_collection.delete_one({"user_id": user_id})
            
            if result.deleted_count > 0:
                # Reload admins
                await self.db.load_admins_and_owners()
                await message.reply_text(f"✅ Removed admin {user_id}")
            else:
                await message.reply_text("⚠️ User not found or not an admin")
        except Exception as e:
            await message.reply_text(f"❌ Error: {str(e)}")
    # Add these methods to your AnimeBot class
    async def start_health_server(self):
        self.health_server = HealthCheckServer()
        await self.health_server.start()
    
    async def stop_health_server(self):
        if hasattr(self, 'health_server'):
            await self.health_server.stop()

async def check_force_sub(client: Client, user_id: int, message: Message = None) -> bool:
    """Check if user has joined all required channels"""
    if not bot.force_sub.force_sub_enabled or not bot.force_sub.force_sub_channels:
        return True

    is_member = await bot.force_sub.check_member(client, user_id)

    if not is_member and message:
        force_sub_msg, keyboard = await bot.force_sub.get_force_sub_message(client)
        await client.send_photo(
            chat_id=message.chat.id,
            photo="https://files.catbox.moe/ujbe17.jpeg",  # force start image
            caption=force_sub_msg,
            reply_markup=keyboard
        )

    return is_member


async def check_expiry_periodically():
    """Periodically check and revoke expired premium access"""
    while True:
        try:
            await asyncio.sleep(3600)  # Check every hour
            expired_users = await bot.premium.check_and_revoke_expired()
            if expired_users:
                logger.info(f"Revoked premium access for {len(expired_users)} expired users")
        except Exception as e:
            logger.error(f"Error in check_expiry_periodically: {e}")
            await asyncio.sleep(600)

async def check_session_timeouts():
    """Periodically clear expired user sessions"""
    while True:
        now = datetime.now()
        to_remove = []
        for user_id, session in bot.user_sessions.items():
            if now - session.get('timestamp', now) > timedelta(minutes=5):
                to_remove.append(user_id)

        for user_id in to_remove:
            await bot.clear_user_session(user_id)

        await asyncio.sleep(60)

async def check_available_periodically(client):
    """Periodically check for available requests"""
    while True:
        try:
            await asyncio.sleep(3600)  # Check every hour
            await bot.request_system.check_and_notify_available(client)
        except Exception as e:
            logger.error(f"Error in check_available_periodically: {e}")
            await asyncio.sleep(600)

class HealthCheckServer:
    def __init__(self):
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.port = 8000

    async def health_check(self, request):
        return web.Response(text="OK", status=200)

    async def start(self):
        self.app.add_routes([web.get('/healthz', self.health_check)])
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await self.site.start()
        print(f"Health check server running on port {self.port}")

    async def stop(self):
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
async def shutdown(stop_event):
    """Cleanup tasks tied to the service's shutdown."""
    print("Shutting down gracefully...")

    # Signal all tasks to stop
    stop_event.set()

    # Close health server
    await bot.stop_health_server()

    # Close database connections
    if hasattr(bot, 'db'):
        for client in bot.db.anime_clients:
            client.close()
        if hasattr(bot.db, 'users_client'):
            bot.db.users_client.close()

    print("Cleanup complete")

async def run_until_stopped(client: Client, stop_event: asyncio.Event):
    """Run the client until stop event is set"""
    try:
        await client.start()
        print("Bot started successfully")
        await stop_event.wait()
    finally:
        if client.is_connected:
            await client.stop()

async def main():
    global bot
    bot = AnimeBot()
    
    # Initialize everything first
    await bot.initialize()
    await bot.db.load_admins_and_owners()

    # Start health server
    await bot.start_health_server()

    # Create the Pyrogram client
    app = Client(
        "AnimeFilterBot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN
    )
    await bot.initialize(app)


    # Register all handlers BEFORE starting the client
    register_handlers(app)

    try:
        # Start the client
        await app.start()
        print("Bot started successfully")

        # Start background tasks
        tasks = [
            asyncio.create_task(check_expiry_periodically()),
            asyncio.create_task(check_session_timeouts()),
            asyncio.create_task(check_available_periodically(app)),
            asyncio.create_task(bot.daily_reset_task())
        ]

        # Keep the bot running
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        # Cleanup
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await app.stop()
        await bot.stop_health_server()
        print("Bot shutdown complete")

def register_handlers(app: Client):
    """Register all message and callback handlers"""
    # Command handlers
    @app.on_message(filters.command("start") & (filters.private | (filters.group & filters.chat(Config.GROUP_ID) if Config.GROUP_ID else filters.group)))
    async def start_command(client: Client, message: Message):
        # 🔹 Check Force Sub first
        # Force sub check for all private messages
        if not await check_force_sub(client, message.from_user.id, message):
            return
        
        # ✅ Continue normal start flow
        await bot.start(client, message)
    @ app.on_message(filters.command("testforcesub") & filters.user(Config.ADMINS))
    async def test_force_sub(client: Client, message: Message):
        user_id = message.from_user.id
        if len(message.command) > 1:
            test_user_id = int(message.command[1])
            user_id = test_user_id
        
        is_member = await bot.force_sub.check_member(client, user_id)
        status = "✅ Subscribed" if is_member else "❌ Not subscribed"
        
        await message.reply_text(
            f"Force Sub Test for user {user_id}:\n"
            f"Status: {status}\n"
            f"Enabled: {bot.force_sub.force_sub_enabled}\n"
            f"Channels: {len(bot.force_sub.force_sub_channels)}"
        )
            
    @app.on_message(filters.command("broadcast") & filters.user(Config.ADMINS))
    async def broadcast_handler(client: Client, message: Message):
        await bot.broadcast.broadcast_message(client, message)

    @app.on_message(filters.command("restart") & filters.user(Config.ADMINS))
    async def restart_handler(client: Client, message: Message):
        await bot.restart_command(client, message)

    @app.on_message(filters.command("request"))
    async def request_handler(client: Client, message: Message):
        await bot.request_system.handle_request(client, message)
   
    @app.on_message(filters.command(["grant"]) & filters.user(Config.OWNERS))
    async def grant_command(client: Client, message: Message):
        if len(message.command) < 3:
            await message.reply_text("Usage: /grant <user_id> <duration> [type]\nExample: /grant 12345678 1d premium")
            return
        
        try:
            target_id = int(message.command[1])
            duration = message.command[2]
            access_type = message.command[3] if len(message.command) > 3 else "premium"
            
            # Parse duration (like 1d, 1M, 30d, etc.)
            if duration.endswith('d'):
                days = int(duration[:-1])
            elif duration.endswith('M'):
                days = int(duration[:-1]) * 30  # Approximate month to days
            else:
                days = int(duration)  # Assume days if no suffix
                
            await bot.premium.grant_access(target_id, access_type, days)
            await message.reply_text(f"✅ Granted {access_type} access for {duration}!")
        except Exception as e:
            logger.error(f"Grant command error: {e}")
            await message.reply_text("Invalid format. Use: /grant <user_id> <duration> [type]")

    @app.on_message(filters.command("revoke") & filters.user(Config.OWNERS))
    async def revoke_premium_command(client: Client, message: Message):
        if len(message.command) < 2:
            await message.reply_text("Usage: /revoke <user_id>")
            return
        
        try:
            user_id = int(message.command[1])
            result = await bot.db.premium_users.delete_one({"user_id": user_id})
            
            if result.deleted_count > 0:
                await message.reply_text(f"✅ Revoked premium access for user {user_id}")
            else:
                await message.reply_text("⚠️ User not found or not premium")
        except ValueError:
            await message.reply_text("Invalid user ID")

    @app.on_message(filters.command("myplan"))
    async def my_plan_handler(client: Client, message: Message):
        await bot.premium.show_my_plan(client, message)
    @app.on_message(filters.command("ongoing") & (filters.private | (filters.group & filters.chat(Config.GROUP_ID) if Config.GROUP_ID else filters.group)))
    async def ongoing_handler(client: Client, message: Message):
        await bot.ongoing_command(client, message)
    
    @app.on_message(filters.command("unlinksequel") & filters.private & filters.user(Config.ADMINS))
    async def unlink_sequel_command(client: Client, message: Message):
        if len(message.command) < 2:
            await message.reply_text(
                "Usage: /unlinksequel <anime_id>\n"
                "Example: /unlinksequel 12345"
            )
            return
        try:
            anime_id = int(message.command[1])
            success = await bot.db.unlink_sequel(anime_id)
            if success:
                await message.reply_text("✅ Successfully unlinked sequels!")
            else:
                await message.reply_text("❌ Failed to unlink sequels")
        except Exception as e:
            logger.error(f"Error unlinking sequels: {e}")
            await message.reply_text("❌ Error unlinking sequels")

    @app.on_message(filters.command(["index", "watchlist", "recent", "admin", "stats"]))
    async def handle_commands(client: Client, message: Message):
        try:
            # Basic rate-limiting check
            if not await bot.check_rate_limit(message.from_user.id):
                await message.reply_text("⏳ Please wait before using another command.")
                return

            command = message.command[0].lower()

            # Command handling logic
            if command == "index":
                await bot.browse_command(client, message)

            elif command == "watchlist":
                await bot.watchlist_command(client, message)

            elif command == "admin":
                if message.from_user.id in Config.ADMINS:
                    await bot.admin_panel(client, message)

            elif command == "stats":
                if message.from_user.id in Config.ADMINS:
                    await bot.status_command(client, message)

      
        except Exception as e:
            logger.error(f"Command error: {e}")
            await message.reply_text("⚠️ Command failed. Please try again.")

    @app.on_message(filters.command("cancel") & filters.private)
    async def cancel_command(client: Client, message: Message):
        await bot.clear_user_session(message.from_user.id)
        await message.reply_text("✅ Operation cancelled")

    @app.on_message(filters.command("done") & filters.private & filters.user(Config.ADMINS))
    async def done_command(client: Client, message: Message):
        await bot.done_adding_episodes(client, message)
    @app.on_message(filters.command("delete_all_requests"))
    async def delete_all_requests_handler(client: Client, message: Message):
        await request_system.delete_all_requests(client, message)
    @app.on_message(filters.command("status") & filters.private & filters.user(Config.ADMINS))
    async def status_command(client: Client, message: Message):
        await bot.status_command(client, message)
    @app.on_message(filters.command("todayschedule") & (filters.private | (filters.group & filters.chat(Config.GROUP_ID) if Config.GROUP_ID else filters.group)))
    async def today_schedule_handler(client: Client, message: Message):
        await bot.today_schedule_command(client, message)
    @app.on_message(filters.command("setlimit") & filters.user(Config.OWNERS))
    async def set_limit_handler(client: Client, message: Message):
        await bot.set_limit_command(client, message)
    @app.on_message(filters.command("search") & (filters.group & (filters.chat(Config.GROUP_ID) if Config.GROUP_ID else filters.group)))
    async def group_search_command(client: Client, message: Message):
        if len(message.command) > 1:
            search_query = " ".join(message.command[1:])
            message.text = search_query
            await bot.process_search(client, message)
        else:
            await bot.search_anime(client, message)

    @app.on_message(filters.command("help") & (filters.private | (filters.group & filters.chat(Config.GROUP_ID) if Config.GROUP_ID else filters.group)))
    async def help_command(client: Client, message: Message):
        help_text = Scripts.HELP_TEXT.format(
            bot_name=Config.BOT_NAME, 
            group_link=Config.GROUP_LINK,
            delete_timer=Config.DELETE_TIMER_MINUTES,
            developer_link=Config.DEVELOPER_USERNAME
        )

        await message.reply_text(
            help_text,
            parse_mode=enums.ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
              #  [InlineKeyboardButton("🔙 Back to Start", callback_data="start_menu")],
                [InlineKeyboardButton("❌ Close", callback_data="close_message")]
            ])
        )
        # React to the user's message with a random emoji
    @ app.on_message(filters.command("forcesub") & filters.user(Config.ADMINS))
    async def force_sub_command(client: Client, message: Message):
        if len(message.command) > 1:
            subcommand = message.command[1].lower()
            
            if subcommand == "on":
                await bot.force_sub.toggle_force_sub(True)
                await message.reply_text("✅ Force subscription enabled")
                
            elif subcommand == "off":
                await bot.force_sub.toggle_force_sub(False)
                await message.reply_text("✅ Force subscription disabled")
                
            elif subcommand == "add" and len(message.command) > 2:
                channel_id = message.command[2]
                try:
                    chat = await client.get_chat(channel_id)
                    added = await bot.force_sub.add_channel(chat.id)
                    if added:
                        await message.reply_text(f"✅ Added channel: {chat.title}")
                    else:
                        await message.reply_text("ℹ️ Channel already in list")
                except Exception as e:
                    await message.reply_text(f"❌ Error: {e}")
                    
            elif subcommand == "remove" and len(message.command) > 2:
                try:
                    channel_id = int(message.command[2])
                    removed = await bot.force_sub.remove_channel(channel_id)
                    if removed:
                        await message.reply_text("✅ Channel removed")
                    else:
                        await message.reply_text("❌ Channel not found")
                except:
                    await message.reply_text("❌ Invalid channel ID")
                    
            elif subcommand == "list":
                await bot.force_sub.show_settings(client, message)
                
        else:
            await message.reply_text(
                "Usage: /forcesub <command>\n\n"
                "Commands:\n"
                "• on - Enable force sub\n"
                "• off - Disable force sub\n"
                "• add <channel> - Add channel\n"
                "• remove <id> - Remove channel\n"
                "• list - Show settings"
            )
        
    @app.on_message(filters.command("linksequel") & filters.private & filters.user(Config.ADMINS))
    async def link_sequel_command(client: Client, message: Message):
        if len(message.command) < 3:
            await message.reply_text(
                "Usage: /linksequel <prequel_id> <sequel_id>\n"
                "Example: /linksequel 12345 67890"
            )
            return
        
        try:
            prequel_id = int(message.command[1])
            sequel_id = int(message.command[2])
            
            # Update across all clusters
            success = False
            for client in bot.db.anime_clients:
                try:
                    db = client[bot.db.db_name]
                    # Update sequel
                    await db.anime.update_one(
                        {"id": sequel_id},
                        {"$set": {"is_sequel": True, "prequel_id": prequel_id}}
                    )
                    # Update prequel
                    await db.anime.update_one(
                        {"id": prequel_id},
                        {"$set": {"sequel_id": sequel_id}}
                    )
                    success = True
                except Exception as e:
                    logger.warning(f"Error updating in cluster: {e}")
            
            if not success:
                raise Exception("Failed to update any cluster")
            
            await message.reply_text("✅ Successfully linked the sequels!")
        except Exception as e:
            logger.error(f"Error linking sequels: {e}")
    @app.on_message(filters.command("resetdb") & filters.private & filters.user(Config.OWNERS))
    async def reset_db_command(client: Client, message: Message):
        class FakeCallbackQuery:
            def __init__(self, message):
                self.from_user = message.from_user
                self.message = message
                self.data = 'admin_reset_db'
                
            async def answer(self, *args, **kwargs):
                pass
                
        fake_query = FakeCallbackQuery(message)
        await bot.reset_database_confirm(client, fake_query)
    @app.on_message(filters.command("quote") & ( filters.group))
    async def quote_command(client: Client, message: Message):
        await bot.quotes.send_quote(client, message)
 
    @app.on_message(filters.command("addadmin") & filters.private & filters.user(Config.ADMINS))
    async def add_admin_command(client: Client, message: Message):
        if len(message.command) < 2:
            await message.reply_text("Usage: /addadmin <user_id or username>")
            return
        
        target = " ".join(message.command[1:])
        message.text = target
        await bot.add_admin_process(client, message)
    @app.on_message(filters.command("removeadmin") & filters.user(Config.OWNERS))
    async def remove_admin_handler(client: Client, message: Message):
        await bot.remove_admin_command(client, message)

    @app.on_callback_query(filters.regex(r"^(confirm_remove_admin_|final_remove_admin_|cancel_remove_admin)"))
    async def remove_admin_callback_handler(client: Client, callback_query: CallbackQuery):
        await bot.handle_remove_admin_callback(client, callback_query)
    @app.on_callback_query(filters.regex(r"^random_anime_direct$"))
    async def handle_random_anime_direct(self, client: Client, callback_query: CallbackQuery):
        await callback_query.answer()
        await self.random_command(client, callback_query.message)

    @app.on_message(filters.command("addowner") & filters.user(Config.OWNERS))
    async def add_owner_command(client: Client, message: Message):
        if len(message.command) < 2:
            await message.reply_text("Usage: /addowner <user_id>")
            return
        
        try:
            new_owner = int(message.command[1])
            if new_owner in Config.OWNERS:
                await message.reply_text("User is already an owner")
                return
                
            Config.OWNERS.append(new_owner)
            os.environ["OWNERS"] = ",".join(map(str, Config.OWNERS))
            
            await message.reply_text(f"✅ Added {new_owner} as owner")
        except Exception as e:
            logger.error(f"Add owner error: {e}")
            await message.reply_text("Invalid user ID")

    @app.on_message(filters.command("removeowner") & filters.user(Config.OWNERS))
    async def remove_owner_command(client: Client, message: Message):
        if len(message.command) < 2:
            await message.reply_text("Usage: /removeowner <user_id>")
            return
        
        try:
            owner_id = int(message.command[1])
            if owner_id not in Config.OWNERS:
                await message.reply_text("User is not an owner")
                return
                
            Config.OWNERS.remove(owner_id)
            os.environ["OWNERS"] = ",".join(map(str, Config.OWNERS))
            
            await message.reply_text(f"✅ Removed {owner_id} from owners")
        except Exception as e:
            logger.error(f"Remove owner error: {e}")
            await message.reply_text("Invalid user ID")
    @app.on_callback_query(filters.regex("^rate_limit_settings$"))
    async def handle_rate_limit_setting(client: Client, callback_query: CallbackQuery):
        await handler_instance.rate_limit_setting(client, callback_query)
    # Text and media handlers
    @app.on_message(filters.text & filters.private)
    async def handle_text_input(client: Client, message: Message):
        user_id = message.from_user.id

        # First check if we're in a setting change session
        if user_id in bot.user_sessions and bot.user_sessions[user_id].get('action') == 'changing_setting':
            await bot.handle_setting_text(client, message)
            return

        # Then check other session states
        if user_id in bot.user_sessions:
            state = bot.user_sessions[user_id].get('state')
            if state == "adding_anime":
                await bot.add_anime_process(client, message)
                return
            elif state == "editing_anime":
                await bot.edit_anime_process(client, message)
                return
            elif state == "adding_admin":
                await bot.add_admin_process(client, message)
                return
            elif state == "changing_setting":
                await bot.process_setting_change(client, message)
                return
            elif state == "adding_db_channel":
                await bot.process_db_channel_add(client, message)
                return
            elif state == "adding_force_sub_channel":
                await bot.force_sub.process_add_channel(client, message)
                return
                
            elif state == "removing_force_sub_channel":
                await bot.force_sub.process_remove_channel(client, message)
                return
        
            # Handle session awaiting search
         # Check if user is awaiting search input
      
            if user_id in bot.user_sessions and bot.user_sessions[user_id].get('awaiting_search'):
                del bot.user_sessions[user_id]['awaiting_search']
                await bot.process_search(client, message)
                return

        # Fallback: Handle regular private messages
        if Config.PM_SEARCH:
            await bot.process_search(client, message)
        else:
            bot_username = (await client.get_me()).username
            await message.reply_text(
                "🔍 *Search Instructions*\n\n"
                "To search for anime:\n"
                f"1. Type `@{bot_username} [query]` in any chat using inline mode\n"
                "2. Or use the /search command in our group\n\n"
                f"Join our group: {Config.GROUP_LINK}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Join Group", url=Config.GROUP_LINK)],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="start_menu")]
                ]),
                disable_web_page_preview=True
            )

    @app.on_message((filters.document | filters.video) & filters.private & filters.user(Config.ADMINS))
    async def handle_media(client: Client, message: Message):
        user_id = message.from_user.id
        if user_id in bot.user_sessions and bot.user_sessions[user_id].get('state') == 'adding_episodes':
            await bot.process_episode_file(client, message)

    # Callback query handler
    @app.on_callback_query()
    async def callback_query(client: Client, callback_query: CallbackQuery):
        await bot.handle_callback_query(client, callback_query)
 
    # Inline query handler

    @app.on_inline_query()
    async def inline_query(client: Client, inline_query):
        try:
            query = inline_query.query.strip()
            if not query:
                await inline_query.answer([], cache_time=1, is_personal=True)
                return

            results = []

            anime_list = await bot.db.search_anime(query, Config.MAX_SEARCH_RESULTS)

            for anime in anime_list:
                title = f"{anime['title']} ({anime.get('episodes', '?')} eps)"

                results.append(
                    InlineQueryResultArticle(
                        title=title,
                        input_message_content=InputTextMessageContent(
                            f"🔍 *Search result for '{query}':*\n\n"
                            f"🎬 *{anime['title']}*\n"
                            f"📺 *Episodes:* {anime.get('episodes', '?')}\n"
                            f"🏢 *Studio:* {anime.get('studio', 'Unknown')}\n",
                          
                            parse_mode=enums.ParseMode.MARKDOWN
                        ),
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("📺 View Anime", callback_data=f"anime_{anime['id']}")
                        ]])
                    )
                )

            await inline_query.answer(
                results or [],
                cache_time=60,
                is_personal=True,
                switch_pm_text="No results found. Search in PM",
                switch_pm_parameter="start"
            )

        except Exception as e:
            print(f"Inline query error: {e}")
            logger.error(f"Error handling inline query: {e}")



if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('bot.log')
        ]
    )
    
    # Start the bot with auto-restart
    while True:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            asyncio.run(self.notification_manager.stop())

            break
        except Exception as e:
            logger.error(f"Bot crashed: {e}", exc_info=True)
            logger.info("Restarting in 10 seconds...")
            time.sleep(10)
