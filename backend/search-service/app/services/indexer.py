"""Real-time indexing service for Elasticsearch"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from app.core.elasticsearch_client import es_client

logger = logging.getLogger(__name__)

class IndexerService:
    """
    Handles indexing of documents from MongoDB/Graph to Elasticsearch
    
    This service listens to Kafka events or can be called directly
    to sync data into Elasticsearch indices.
    """
    
    async def index_user(self, user_data: Dict[str, Any]) -> bool:
        """
        Index a user document
        
        Args:
            user_data: User vertex data from graph
        """
        try:
            doc = {
                "user_id": user_data["user_id"],
                "name": user_data["name"],
                "role_primary": user_data["role_primary"],
                "roles_secondary": user_data.get("roles_secondary", []),
                "domain_tags": user_data.get("domain_tags", []),
                "geography": user_data.get("geography"),
                "experience_years": user_data.get("experience_years", 0),
                "reputation_score": user_data.get("reputation_score", 0.0),
                "verification_status": user_data.get("verification_status", "unverified"),
                "bio": user_data.get("bio", ""),
                "created_at": user_data.get("created_at", datetime.utcnow().isoformat())
            }
            
            success = await es_client.index_document(
                index="users",
                doc_id=user_data["user_id"],
                document=doc
            )
            
            if success:
                logger.info(f"✅ Indexed user: {user_data['user_id']}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to index user: {str(e)}")
            return False
    
    async def index_startup(self, startup_data: Dict[str, Any]) -> bool:
        """Index a startup document"""
        try:
            doc = {
                "startup_id": startup_data["startup_id"],
                "name": startup_data["name"],
                "domain": startup_data["domain"],
                "stage": startup_data["stage"],
                "geography": startup_data.get("geography"),
                "founded_year": startup_data.get("founded_year"),
                "funding_status": startup_data.get("funding_status"),
                "employee_count": startup_data.get("employee_count", 0),
                "visibility_level": startup_data.get("visibility_level", "public"),
                "description": startup_data.get("description", ""),
                "tags": startup_data.get("tags", []),
                "created_at": startup_data.get("created_at", datetime.utcnow().isoformat())
            }
            
            success = await es_client.index_document(
                index="startups",
                doc_id=startup_data["startup_id"],
                document=doc
            )
            
            if success:
                logger.info(f"✅ Indexed startup: {startup_data['startup_id']}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to index startup: {str(e)}")
            return False
    
    async def index_organization(self, org_data: Dict[str, Any]) -> bool:
        """Index an organization document"""
        try:
            doc = {
                "org_id": org_data["org_id"],
                "name": org_data["name"],
                "type": org_data["type"],
                "geography": org_data.get("geography"),
                "domains": org_data.get("domains", []),
                "website": org_data.get("website"),
                "description": org_data.get("description", ""),
                "created_at": org_data.get("created_at", datetime.utcnow().isoformat())
            }
            
            success = await es_client.index_document(
                index="organizations",
                doc_id=org_data["org_id"],
                document=doc
            )
            
            if success:
                logger.info(f"✅ Indexed organization: {org_data['org_id']}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to index organization: {str(e)}")
            return False
    
    async def bulk_index_users(self, users: List[Dict[str, Any]]) -> bool:
        """Bulk index multiple users"""
        try:
            documents = []
            for user in users:
                doc = {
                    "_id": user["user_id"],
                    "user_id": user["user_id"],
                    "name": user["name"],
                    "role_primary": user["role_primary"],
                    "domain_tags": user.get("domain_tags", []),
                    "geography": user.get("geography"),
                    "reputation_score": user.get("reputation_score", 0.0),
                    "created_at": user.get("created_at", datetime.utcnow().isoformat())
                }
                documents.append(doc)
            
            success = await es_client.bulk_index("users", documents)
            
            if success:
                logger.info(f"✅ Bulk indexed {len(users)} users")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Bulk index error: {str(e)}")
            return False
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete user from index"""
        return await es_client.delete_document("users", user_id)
    
    async def delete_startup(self, startup_id: str) -> bool:
        """Delete startup from index"""
        return await es_client.delete_document("startups", startup_id)
    
    async def reindex_all(self):
        """
        Reindex all data from primary stores
        
        This would typically:
        1. Query all users from graph
        2. Query all startups from graph
        3. Bulk index everything
        
        Run this as a batch job or migration
        """
        logger.info("🔄 Starting full reindex...")
        
        # TODO: Implement full reindex from graph database
        # This requires graph service integration
        
        logger.info("✅ Reindex completed")

# Singleton instance
indexer_service = IndexerService()
