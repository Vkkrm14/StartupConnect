"""Search Service - Core search logic with graph-aware ranking"""

from typing import List, Dict, Any, Optional
import logging

from app.core.elasticsearch_client import es_client

logger = logging.getLogger(__name__)

class SearchService:
    """
    Core search service with Elasticsearch integration
    and graph-aware ranking
    """
    
    async def search_users(
        self,
        query: str,
        role: Optional[str] = None,
        domain: Optional[str] = None,
        geography: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search for users with multi-field fuzzy matching
        
        Args:
            query: Search query string
            role: Filter by role (founder/investor/connector)
            domain: Filter by domain tag
            geography: Filter by location
            limit: Max results
            offset: Pagination offset
        
        Returns:
            Search results with scores
        """
        
        # Build Elasticsearch query
        must_clauses = []
        filter_clauses = []
        
        # Multi-match query on name, domain_tags, bio
        if query:
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": ["name^3", "domain_tags^2", "bio"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                    "operator": "or"
                }
            })
        
        # Filters
        if role:
            filter_clauses.append({"term": {"role_primary": role}})
        
        if domain:
            filter_clauses.append({"term": {"domain_tags": domain.lower()}})
        
        if geography:
            filter_clauses.append({"term": {"geography": geography}})
        
        # Boost by reputation score
        es_query = {
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "must": must_clauses if must_clauses else [{"match_all": {}}],
                            "filter": filter_clauses
                        }
                    },
                    "functions": [
                        {
                            "field_value_factor": {
                                "field": "reputation_score",
                                "factor": 1.5,
                                "modifier": "sqrt",
                                "missing": 0.5
                            }
                        }
                    ],
                    "boost_mode": "multiply"
                }
            },
            "sort": [
                {"_score": {"order": "desc"}},
                {"reputation_score": {"order": "desc"}}
            ]
        }
        
        try:
            response = await es_client.search(
                index="users",
                query=es_query,
                size=limit,
                from_=offset
            )
            
            # Format results
            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                results.append({
                    "user_id": source["user_id"],
                    "name": source["name"],
                    "role": source["role_primary"],
                    "domain_tags": source.get("domain_tags", []),
                    "geography": source.get("geography"),
                    "reputation_score": source.get("reputation_score", 0.5),
                    "verification_status": source.get("verification_status", "unverified"),
                    "score": hit["_score"]
                })
            
            return {
                "query": query,
                "total": response["hits"]["total"]["value"],
                "results": results,
                "offset": offset,
                "limit": limit
            }
            
        except Exception as e:
            logger.error(f"User search error: {str(e)}")
            return {
                "query": query,
                "total": 0,
                "results": [],
                "error": str(e)
            }
    
    async def search_startups(
        self,
        query: str,
        stage: Optional[str] = None,
        domain: Optional[str] = None,
        geography: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Search for startups"""
        
        must_clauses = []
        filter_clauses = []
        
        if query:
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": ["name^4", "domain^2", "description", "tags"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            })
        
        if stage:
            filter_clauses.append({"term": {"stage": stage}})
        
        if domain:
            must_clauses.append({"match": {"domain": domain}})
        
        if geography:
            filter_clauses.append({"term": {"geography": geography}})
        
        es_query = {
            "query": {
                "bool": {
                    "must": must_clauses if must_clauses else [{"match_all": {}}],
                    "filter": filter_clauses
                }
            },
            "sort": [
                {"_score": {"order": "desc"}}
            ]
        }
        
        try:
            response = await es_client.search(
                index="startups",
                query=es_query,
                size=limit,
                from_=offset
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                results.append({
                    "startup_id": source["startup_id"],
                    "name": source["name"],
                    "domain": source["domain"],
                    "stage": source["stage"],
                    "geography": source.get("geography"),
                    "funding_status": source.get("funding_status"),
                    "score": hit["_score"]
                })
            
            return {
                "query": query,
                "total": response["hits"]["total"]["value"],
                "results": results,
                "offset": offset,
                "limit": limit
            }
            
        except Exception as e:
            logger.error(f"Startup search error: {str(e)}")
            return {
                "query": query,
                "total": 0,
                "results": [],
                "error": str(e)
            }
    
    async def autocomplete(
        self,
        query: str,
        entity_type: str = "users",
        limit: int = 5
    ) -> List[Dict[str, str]]:
        """
        Autocomplete suggestions
        
        Args:
            query: Partial search string
            entity_type: "users" or "startups"
            limit: Max suggestions
        """
        
        if len(query) < 2:
            return []
        
        es_query = {
            "query": {
                "match_phrase_prefix": {
                    "name": {
                        "query": query,
                        "max_expansions": 10
                    }
                }
            }
        }
        
        try:
            response = await es_client.search(
                index=entity_type,
                query=es_query,
                size=limit,
                from_=0
            )
            
            suggestions = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                suggestions.append({
                    "id": source.get(f"{entity_type[:-1]}_id"),
                    "name": source["name"],
                    "type": entity_type
                })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Autocomplete error: {str(e)}")
            return []
    
    async def advanced_search(
        self,
        filters: Dict[str, Any],
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Advanced search with multiple filters
        
        Supports:
        - Investor thesis matching
        - Startup similarity
        - Domain expertise
        """
        
        # Build complex query based on filters
        # This is a placeholder for advanced filtering logic
        
        return {
            "results": [],
            "total": 0,
            "message": "Advanced search implementation"
        }
