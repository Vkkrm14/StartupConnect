"""Vertex CRUD operations"""

from typing import Optional, List
import uuid
from datetime import datetime
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.graph_client import graph_client
from app.schemas.vertex_schemas import (
    UserCreate, UserResponse,
    StartupCreate, StartupResponse,
    OrganizationCreate, OrganizationResponse
)

logger = logging.getLogger(__name__)

# Thread pool for running synchronous Gremlin operations
executor = ThreadPoolExecutor(max_workers=10)

def _create_user_sync(user_data: UserCreate, user_id: str, created_at: datetime) -> UserResponse:
    """Synchronous user creation (runs in thread pool)"""
    g = graph_client.get_traversal()
    
    try:
        # Create vertex
        vertex = (
            g.addV('User')
            .property('user_id', user_id)
            .property('name', user_data.name)
            .property('role_primary', user_data.role_primary.value)
            .property('geography', user_data.geography or '')
            .property('experience_years', user_data.experience_years)
            .property('reputation_score', 0.5)  # Default reputation
            .property('verification_status', user_data.verification_status.value)
            .property('created_at', int(created_at.timestamp()))
            .next()
        )
        
        # Add domain tags (multi-valued property)
        for tag in user_data.domain_tags:
            g.V(vertex).property('domain_tags', tag).iterate()
        
        # Add secondary roles
        for role in user_data.roles_secondary:
            g.V(vertex).property('roles_secondary', role.value).iterate()
        
        logger.info(f"✅ Created User: {user_id} - {user_data.name}")
        
        return UserResponse(
            user_id=user_id,
            name=user_data.name,
            role_primary=user_data.role_primary,
            roles_secondary=user_data.roles_secondary,
            domain_tags=user_data.domain_tags,
            geography=user_data.geography,
            experience_years=user_data.experience_years,
            reputation_score=0.5,
            verification_status=user_data.verification_status,
            created_at=created_at
       )
        
    except Exception as e:
        logger.error(f"❌ Failed to create user: {str(e)}")
        raise

class VertexService:
    """Service for managing graph vertices"""
    
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new User vertex"""
        user_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            executor,
            _create_user_sync,
            user_data,
            user_id,
            created_at
        )
    
    async def get_user(self, user_id: str) -> Optional[UserResponse]:
        """Get User vertex by ID"""
        g = graph_client.get_traversal()
        
        try:
            vertex_data = (
                g.V()
                .has('User', 'user_id', user_id)
                .valueMap(True)
                .next()
            )
            
            return self._vertex_to_user_response(vertex_data)
            
        except StopIteration:
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get user {user_id}: {str(e)}")
            raise
    
    async def create_startup(self, startup_data: StartupCreate) -> StartupResponse:
        """Create a new Startup vertex"""
        g = graph_client.get_traversal()
        
        startup_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        try:
            vertex = (
                g.addV('Startup')
                .property('startup_id', startup_id)
                .property('name', startup_data.name)
                .property('domain', startup_data.domain)
                .property('stage', startup_data.stage.value)
                .property('geography', startup_data.geography or '')
                .property('founded_year', startup_data.founded_year or 0)
                .property('funding_status', startup_data.funding_status or '')
                .property('employee_count', startup_data.employee_count or 0)
                .property('visibility_level', startup_data.visibility_level.value)
                .property('created_at', int(created_at.timestamp()))
                .next()
            )
            
            logger.info(f"✅ Created Startup: {startup_id} - {startup_data.name}")
            
            return StartupResponse(
                startup_id=startup_id,
                name=startup_data.name,
                domain=startup_data.domain,
                stage=startup_data.stage,
                geography=startup_data.geography,
                founded_year=startup_data.founded_year,
                funding_status=startup_data.funding_status,
                employee_count=startup_data.employee_count,
                visibility_level=startup_data.visibility_level,
                created_at=created_at
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to create startup: {str(e)}")
            raise
    
    def _vertex_to_user_response(self, vertex_data: dict) -> UserResponse:
        """Convert vertex data to UserResponse"""
        return UserResponse(
            user_id=vertex_data.get('user_id', [''])[0],
            name=vertex_data.get('name', [''])[0],
            role_primary=vertex_data.get('role_primary', ['founder'])[0],
            roles_secondary=vertex_data.get('roles_secondary', []),
            domain_tags=vertex_data.get('domain_tags', []),
            geography=vertex_data.get('geography', [''])[0],
            experience_years=vertex_data.get('experience_years', [0])[0],
            reputation_score=float(vertex_data.get('reputation_score', [0.5])[0]),
            verification_status=vertex_data.get('verification_status', ['unverified'])[0],
            created_at=datetime.fromtimestamp(vertex_data.get('created_at', [0])[0])
        )
