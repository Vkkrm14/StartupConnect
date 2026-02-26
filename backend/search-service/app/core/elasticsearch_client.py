"""Elasticsearch Client for TrustGraph"""

from typing import Optional, List, Dict, Any
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import NotFoundError
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class ElasticsearchClient:
    """Elasticsearch client wrapper with index management"""
    
    def __init__(self):
        self.client: Optional[AsyncElasticsearch] = None
        
    async def connect(self):
        """Connect to Elasticsearch"""
        try:
            self.client = AsyncElasticsearch([settings.ELASTICSEARCH_URL])
            
            # Test connection
            info = await self.client.info()
            logger.info(f"✅ Connected to Elasticsearch: {info['version']['number']}")
            
            # Initialize indices
            await self._initialize_indices()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Elasticsearch: {str(e)}")
            raise
    
    async def close(self):
        """Close Elasticsearch connection"""
        if self.client:
            await self.client.close()
            logger.info("🔌 Closed Elasticsearch connection")
    
    async def _initialize_indices(self):
        """Create indices if they don't exist"""
        
        # Users index
        users_mapping = {
            "mappings": {
                "properties": {
                    "user_id": {"type": "keyword"},
                    "name": {"type": "text", "analyzer": "standard"},
                    "role_primary": {"type": "keyword"},
                    "roles_secondary": {"type": "keyword"},
                    "domain_tags": {"type": "keyword"},
                    "geography": {"type": "keyword"},
                    "experience_years": {"type": "integer"},
                    "reputation_score": {"type": "float"},
                    "verification_status": {"type": "keyword"},
                    "bio": {"type": "text"},
                    "created_at": {"type": "date"}
                }
            }
        }
        
        # Startups index
        startups_mapping = {
            "mappings": {
                "properties": {
                    "startup_id": {"type": "keyword"},
                    "name": {"type": "text", "analyzer": "standard"},
                    "domain": {"type": "text"},
                    "stage": {"type": "keyword"},
                    "geography": {"type": "keyword"},
                    "founded_year": {"type": "integer"},
                    "funding_status": {"type": "text"},
                    "employee_count": {"type": "integer"},
                    "visibility_level": {"type": "keyword"},
                    "description": {"type": "text"},
                    "tags": {"type": "keyword"},
                    "created_at": {"type": "date"}
                }
            }
        }
        
        # Organizations index
        organizations_mapping = {
            "mappings": {
                "properties": {
                    "org_id": {"type": "keyword"},
                    "name": {"type": "text", "analyzer": "standard"},
                    "type": {"type": "keyword"},
                    "geography": {"type": "keyword"},
                    "domains": {"type": "keyword"},
                    "website": {"type": "keyword"},
                    "description": {"type": "text"},
                    "created_at": {"type": "date"}
                }
            }
        }
        
        # Create indices
        for index_name, mapping in [
            ("users", users_mapping),
            ("startups", startups_mapping),
            ("organizations", organizations_mapping)
        ]:
            try:
                exists = await self.client.indices.exists(index=index_name)
                if not exists:
                    await self.client.indices.create(
                        index=index_name,
                        body=mapping
                    )
                    logger.info(f"✅ Created index: {index_name}")
            except Exception as e:
                logger.error(f"❌ Failed to create index {index_name}: {str(e)}")
    
    async def index_document(
        self,
        index: str,
        doc_id: str,
        document: Dict[str, Any]
    ) -> bool:
        """Index a document"""
        try:
            await self.client.index(
                index=index,
                id=doc_id,
                body=document
            )
            logger.debug(f"📝 Indexed document {doc_id} in {index}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to index document: {str(e)}")
            return False
    
    async def search(
        self,
        index: str,
        query: Dict[str, Any],
        size: int = 10,
        from_: int = 0
    ) -> Dict[str, Any]:
        """Execute search query"""
        try:
            response = await self.client.search(
                index=index,
                body=query,
                size=size,
                from_=from_
            )
            return response
        except NotFoundError:
            logger.warning(f"Index {index} not found")
            return {"hits": {"total": {"value": 0}, "hits": []}}
        except Exception as e:
            logger.error(f"❌ Search error: {str(e)}")
            return {"hits": {"total": {"value": 0}, "hits": []}}
    
    async def bulk_index(
        self,
        index: str,
        documents: List[Dict[str, Any]]
    ) -> bool:
        """Bulk index documents"""
        try:
            from elasticsearch.helpers import async_bulk
            
            actions = [
                {
                    "_index": index,
                    "_id": doc.get("_id"),
                    "_source": doc
                }
                for doc in documents
            ]
            
            success, failed = await async_bulk(self.client, actions)
            logger.info(f"✅ Bulk indexed {success} documents, {failed} failed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Bulk index error: {str(e)}")
            return False
    
    async def delete_document(self, index: str, doc_id: str) -> bool:
        """Delete a document"""
        try:
            await self.client.delete(index=index, id=doc_id)
            return True
        except NotFoundError:
            logger.warning(f"Document {doc_id} not found in {index}")
            return False
        except Exception as e:
            logger.error(f"❌ Delete error: {str(e)}")
            return False
    
    def get_client(self) -> AsyncElasticsearch:
        """Get raw Elasticsearch client"""
        if not self.client:
            raise RuntimeError("Elasticsearch client not connected")
        return self.client

# Singleton instance
es_client = ElasticsearchClient()
