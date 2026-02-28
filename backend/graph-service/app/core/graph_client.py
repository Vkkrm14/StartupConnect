from gremlin_python.driver import client
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.driver.serializer import GraphSONSerializersV3d0
from typing import Optional
import logging
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)

class GraphClient:

    def __init__(self):
        self.connection: Optional[DriverRemoteConnection] = None
        self.g = None

    async def connect(self):
        # Connect directly to pre-bound traversal source 'g'
        # Run in executor to avoid blocking the async event loop
        def create_connection():
            connection = DriverRemoteConnection(
                settings.JANUSGRAPH_URL,
                "g",
                message_serializer=GraphSONSerializersV3d0()
            )
            return connection, traversal().withRemote(connection)
        
        loop = asyncio.get_running_loop()
        self.connection, self.g = await loop.run_in_executor(None, create_connection)
        logger.info("Janusgraph: %s", settings.JANUSGRAPH_URL)
        logger.info("✅ Connected to JanusGraph (using GraphSON v3)")

    async def close(self):
        if self.connection:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.connection.close)
            self.connection = None
            self.g = None
            logger.info("🔌 Connection closed")

    def get_traversal(self):
        if not self.g:
            raise RuntimeError("Graph not connected")
        return self.g


graph_client = GraphClient()