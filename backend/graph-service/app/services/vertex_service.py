"""Vertex CRUD operations"""

from typing import Optional, List
import uuid
from datetime import datetime
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from gremlin_python.process.graph_traversal import __

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
    try:
        g = graph_client.get_traversal()
        
        # Create vertex with all properties in one go
        g.addV('User') \
            .property('user_id', user_id) \
            .property('name', user_data.name) \
            .property('email', user_data.email or '') \
            .property('password_hash', user_data.password_hash or '') \
            .property('role_primary', user_data.role_primary.value) \
            .property('geography', user_data.geography or '') \
            .property('experience_years', user_data.experience_years) \
            .property('reputation_score', 0.0) \
            .property('is_verified', False) \
            .property('profile_completeness', 0.0) \
            .property('verification_status', user_data.verification_status.value) \
            .property('created_at', int(created_at.timestamp())) \
            .iterate()
        
        # Add domain tags (multi-valued property)
        if user_data.domain_tags:
            for tag in user_data.domain_tags:
                g.V().has('user_id', user_id).property('domain_tags', tag).iterate()
        
        # Add secondary roles
        if user_data.roles_secondary:
            for role in user_data.roles_secondary:
                g.V().has('user_id', user_id).property('roles_secondary', role.value).iterate()
        
        logger.info(f"✅ Created User: {user_id} - {user_data.name}")
        
        return UserResponse(
            user_id=user_id,
            name=user_data.name,
            email=user_data.email,
            password_hash=user_data.password_hash,
            role_primary=user_data.role_primary,
            roles_secondary=user_data.roles_secondary,
            domain_tags=user_data.domain_tags,
            geography=user_data.geography,
            experience_years=user_data.experience_years,
            reputation_score=0.0,
            verification_status=user_data.verification_status,
            created_at=created_at
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to create user: {str(e)}")
        logger.exception("Full traceback:")
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
    
    async def list_users(self, role: Optional[str] = None, limit: int = 100):
        """List all User vertices, optionally filtered by role.
        Returns the live reputation_score from the graph (not a stale cached value).
        """
        g = graph_client.get_traversal()

        def list_vertices():
            t = g.V().hasLabel('User')
            if role:
                t = t.has('role_primary', role)
            # Project vertex properties alongside a live reputation score computed
            # as the average outgoing TRUSTS trust_score (accepted edges only).
            # Falls back to the stored reputation_score property when no edges exist.
            return (
                t.project('props', 'live_reputation')
                .by(__.valueMap(True))
                .by(
                    __.coalesce(
                        __.outE('TRUSTS').has('status', 'accepted')
                          .values('trust_score')
                          .mean(),
                        __.values('reputation_score')
                    )
                )
                .toList()
            )

        try:
            loop = asyncio.get_event_loop()
            rows = await loop.run_in_executor(executor, list_vertices)
            results = []
            for row in rows[:limit]:
                props = row['props']
                live_rep = row.get('live_reputation', None)
                user = self._vertex_to_user_response(props)
                if live_rep is not None:
                    # Override with live value so discover page always shows current score
                    user = user.model_copy(update={'reputation_score': round(float(live_rep), 4)})
                results.append(user)
            return results
        except Exception as e:
            logger.error(f"❌ Failed to list users: {str(e)}")
            raise

    async def get_user(self, user_id: str) -> Optional[UserResponse]:
        """Get User vertex by ID"""
        g = graph_client.get_traversal()
        
        def get_vertex():
            try:
                return (
                    g.V()
                    .has('User', 'user_id', user_id)
                    .valueMap(True)
                    .next()
                )
            except StopIteration:
                return None
        
        try:
            loop = asyncio.get_event_loop()
            vertex_data = await loop.run_in_executor(executor, get_vertex)
            
            if vertex_data is None:
                return None
            
            return self._vertex_to_user_response(vertex_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to get user {user_id}: {str(e)}")
            raise
    
    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """Get User vertex by email"""
        g = graph_client.get_traversal()
        
        def get_vertex():
            try:
                return (
                    g.V()
                    .has('User', 'email', email)
                    .valueMap(True)
                    .next()
                )
            except StopIteration:
                return None
        
        try:
            loop = asyncio.get_event_loop()
            vertex_data = await loop.run_in_executor(executor, get_vertex)
            
            if vertex_data is None:
                return None
            
            return self._vertex_to_user_response(vertex_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to get user by email {email}: {str(e)}")
            raise
    
    async def create_startup(self, startup_data: StartupCreate) -> StartupResponse:
        """Create a new Startup vertex"""
        g = graph_client.get_traversal()
        
        startup_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        try:
            g.addV('Startup') \
                .property('startup_id', startup_id) \
                .property('name', startup_data.name) \
                .property('domain', startup_data.domain) \
                .property('stage', startup_data.stage.value) \
                .property('geography', startup_data.geography or '') \
                .property('founded_year', startup_data.founded_year or 0) \
                .property('funding_status', startup_data.funding_status or '') \
                .property('employee_count', startup_data.employee_count or 0) \
                .property('visibility_level', startup_data.visibility_level.value) \
                .property('created_at', int(created_at.timestamp())) \
                .iterate()
            
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
    
    async def get_connections(self, user_id: str) -> List[UserResponse]:
        """Get all mutually connected users with accepted TRUSTS edges."""
        g = graph_client.get_traversal()

        def fetch():
            try:
                return (
                    g.V()
                    .has('User', 'user_id', user_id)
                    .bothE('TRUSTS').has('status', 'accepted')
                    .where(__.values('is_mutual').is_(True))
                    .otherV()
                    .hasLabel('User')
                    .dedup()
                    .valueMap(True)
                    .toList()
                )
            except StopIteration:
                return []

        try:
            loop = asyncio.get_event_loop()
            vertices = await loop.run_in_executor(executor, fetch)
            return [self._vertex_to_user_response(v) for v in vertices]
        except Exception as e:
            logger.error(f"❌ Failed to get connections for {user_id}: {str(e)}")
            raise

    def _vertex_to_user_response(self, vertex_data: dict) -> UserResponse:
        """Convert vertex data to UserResponse"""
        return UserResponse(
            user_id=vertex_data.get('user_id', [''])[0],
            name=vertex_data.get('name', [''])[0],
            email=vertex_data.get('email', [''])[0] or None,
            password_hash=vertex_data.get('password_hash', [''])[0] or None,
            role_primary=vertex_data.get('role_primary', ['founder'])[0],
            roles_secondary=vertex_data.get('roles_secondary', []),
            domain_tags=vertex_data.get('domain_tags', []),
            geography=vertex_data.get('geography', [''])[0],
            experience_years=vertex_data.get('experience_years', [0])[0],
            reputation_score=float((vertex_data.get('reputation_score') or [0.0])[0]),
            verification_status=vertex_data.get('verification_status', ['unverified'])[0],
            created_at=datetime.fromtimestamp(vertex_data.get('created_at', [0])[0])
        )
