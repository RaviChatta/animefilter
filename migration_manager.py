
from pyrogram import Client, filters, enums ,  __version__
from bson import json_util, ObjectId
import os
import json
import asyncio
import logging
from datetime import datetime
import asyncio
import logging
from datetime import datetime
from bson import ObjectId
import uuid

logger = logging.getLogger(__name__)

class FileMigration:
    def __init__(self, db, bot_instance):
        self.db = db
        self.bot = bot_instance
        self.migration_errors = []
    
    async def migrate_all_files_to_deep_links(self, batch_size=100):
        """Migrate all existing files to use deep links"""
        logger.info("Starting file migration to deep links...")
        
        total_migrated = 0
        total_processed = 0
        total_already_migrated = 0
        
        # Process each cluster
        for cluster_idx, client in enumerate(self.db.anime_clients):
            try:
                db = client[self.db.db_name]
                
                # Get total count for progress tracking
                total_files = await db.files.estimated_document_count()
                logger.info(f"Cluster {cluster_idx}: Found {total_files} files to migrate")
                
                # Process in batches
                skip = 0
                batch_count = 0
                
                while True:
                    # Get batch of files
                    files_batch = await db.files.find({}).skip(skip).limit(batch_size).to_list(None)
                    if not files_batch:
                        break
                    
                    # Process each file in batch
                    migrated_in_batch = 0
                    already_migrated_in_batch = 0
                    
                    for file_data in files_batch:
                        try:
                            # Check if file already has a deep link
                            if file_data.get('deep_link_id'):
                                already_migrated_in_batch += 1
                                total_already_migrated += 1
                                continue
                            
                            success = await self.migrate_single_file(file_data, cluster_idx)
                            if success:
                                migrated_in_batch += 1
                                total_migrated += 1
                            
                            total_processed += 1
                            
                            # Log progress every 100 files
                            if total_processed % 100 == 0:
                                logger.info(f"Processed {total_processed} files, migrated {total_migrated}, already migrated {total_already_migrated}")
                                
                        except Exception as e:
                            error_msg = f"Error migrating file {file_data.get('_id')} in cluster {cluster_idx}: {e}"
                            logger.error(error_msg)
                            self.migration_errors.append(error_msg)
                            continue
                    
                    batch_count += 1
                    logger.info(f"Cluster {cluster_idx} Batch {batch_count}: {migrated_in_batch} migrated, {already_migrated_in_batch} already migrated")
                    skip += batch_size
                    
                    # Small delay to avoid overwhelming the database
                    await asyncio.sleep(0.1)
                
                logger.info(f"Completed Cluster {cluster_idx}: {total_migrated} migrated, {total_already_migrated} already had deep links")
                
            except Exception as e:
                error_msg = f"Error processing cluster {cluster_idx}: {e}"
                logger.error(error_msg)
                self.migration_errors.append(error_msg)
                continue
        
        logger.info(f"Migration completed! Processed {total_processed} files, migrated {total_migrated}, already had deep links: {total_already_migrated}")
        return {
            "total_processed": total_processed,
            "total_migrated": total_migrated,
            "total_already_migrated": total_already_migrated,
            "errors": self.migration_errors
        }
    
    async def migrate_single_file(self, file_data, cluster_idx):
        """Migrate a single file to use deep links"""
        try:
            # Create deep link data
            deep_link_id = str(uuid.uuid4())
            
            # Prepare deep link data for database
            deep_link_data = {
                "deep_link_id": deep_link_id,
                "anime_id": file_data["anime_id"],
                "anime_title": file_data.get("anime_title", ""),
                "episode": file_data["episode"],
                "quality": file_data.get("quality", ""),
                "language": file_data.get("language", ""),
                "file_size": file_data.get("file_size", ""),
                "file_type": file_data.get("file_type", ""),
                "chat_id": file_data["chat_id"],
                "message_id": file_data["message_id"],
                "is_adult": file_data.get("is_adult", False),
                "created_at": datetime.now(),
                "access_count": 0,
                "original_file_id": str(file_data.get("_id", "")),
                "migrated_at": datetime.now(),
                "source_cluster": cluster_idx
            }
            
            # Store deep link in database
            await self.db.deep_links_collection.insert_one(deep_link_data)
            
            # Update the file with deep link ID
            client = self.db.anime_clients[cluster_idx]
            db = client[self.db.db_name]
            
            result = await db.files.update_one(
                {"_id": file_data["_id"]},
                {"$set": {"deep_link_id": deep_link_id}}
            )
            
            if result.modified_count > 0:
                logger.debug(f"Successfully migrated file {file_data['_id']} with deep link {deep_link_id}")
                return True
            else:
                logger.warning(f"File {file_data['_id']} not updated in cluster {cluster_idx}")
                return False
                
        except Exception as e:
            error_msg = f"Error migrating file {file_data.get('_id')} in cluster {cluster_idx}: {e}"
            logger.error(error_msg)
            self.migration_errors.append(error_msg)
            return False
    
    async def check_migration_status(self):
        """Check the current migration status"""
        status = {
            "total_files": 0,
            "migrated_files": 0,
            "not_migrated_files": 0,
            "clusters": []
        }
        
        for cluster_idx, client in enumerate(self.db.anime_clients):
            try:
                db = client[self.db.db_name]
                total_files = await db.files.estimated_document_count()
                migrated_files = await db.files.count_documents({"deep_link_id": {"$exists": True}})
                
                status["total_files"] += total_files
                status["migrated_files"] += migrated_files
                status["not_migrated_files"] += (total_files - migrated_files)
                
                status["clusters"].append({
                    "cluster_index": cluster_idx,
                    "total_files": total_files,
                    "migrated_files": migrated_files,
                    "not_migrated_files": total_files - migrated_files,
                    "completion_percentage": (migrated_files / total_files * 100) if total_files > 0 else 0
                })
                
            except Exception as e:
                error_msg = f"Error checking cluster {cluster_idx}: {e}"
                logger.error(error_msg)
                status["clusters"].append({
                    "cluster_index": cluster_idx,
                    "error": str(e)
                })
        
        return status

    async def get_migration_progress(self):
        """Get detailed migration progress"""
        progress = {
            "clusters": [],
            "overall": {
                "total_files": 0,
                "migrated_files": 0,
                "not_migrated_files": 0
            }
        }
        
        for cluster_idx, client in enumerate(self.db.anime_clients):
            try:
                db = client[self.db.db_name]
                total_files = await db.files.estimated_document_count()
                migrated_files = await db.files.count_documents({"deep_link_id": {"$exists": True}})
                
                progress["overall"]["total_files"] += total_files
                progress["overall"]["migrated_files"] += migrated_files
                progress["overall"]["not_migrated_files"] += (total_files - migrated_files)
                
                progress["clusters"].append({
                    "cluster_index": cluster_idx,
                    "total_files": total_files,
                    "migrated_files": migrated_files,
                    "not_migrated_files": total_files - migrated_files,
                    "completion_percentage": (migrated_files / total_files * 100) if total_files > 0 else 0
                })
                
            except Exception as e:
                progress["clusters"].append({
                    "cluster_index": cluster_idx,
                    "error": str(e)
                })
        
        return progress
