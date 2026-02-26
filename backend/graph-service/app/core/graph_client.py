from gremlin_python.driver import client, serializer
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class GraphClient:
    """JanusGraph client wrapper with connection pooling"""
    
    def __init__(self):
        self.connection: Optional[DriverRemoteConnection] = None
        self.g = None
        
    async def connect(self):
        """Establish connection to JanusGraph"""
        try:
            self.connection = DriverRemoteConnection(
                settings.JANUSGRAPH_URL,
                settings.JANUSGRAPH_TRAVERSAL_SOURCE,
                message_serializer=serializer.GraphSONSerializersV3d0()
            )
            self.g = traversal().withRemote(self.connection)
            logger.info(f"✅ Connected to JanusGraph at {settings.JANUSGRAPH_URL}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to JanusGraph: {str(e)}")
            raise
    
    async def close(self):
        """Close connection to JanusGraph"""
        if self.connection:
            self.connection.close()
            logger.info("🔌 Closed JanusGraph connection")
    
    def get_traversal(self):
        """Get graph traversal source"""
        if not self.g:
            raise RuntimeError("Graph client not connected. Call connect() first.")
        return self.g

# Singleton instance
graph_client = GraphClient()
