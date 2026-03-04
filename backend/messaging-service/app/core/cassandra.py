import logging
from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement, ConsistencyLevel
from cassandra.policies import DCAwareRoundRobinPolicy

from app.core.config import settings

logger = logging.getLogger(__name__)


class CassandraClient:
    def __init__(self):
        self.cluster = None
        self.session = None

    def connect(self):
        hosts = settings.CASSANDRA_HOSTS.split(",")
        self.cluster = Cluster(
            contact_points=hosts,
            port=settings.CASSANDRA_PORT,
            load_balancing_policy=DCAwareRoundRobinPolicy(local_dc="datacenter1"),
        )
        self.session = self.cluster.connect()
        self._init_keyspace()
        self._init_tables()
        logger.info("Cassandra connection established")

    def _init_keyspace(self):
        self.session.execute(f"""
            CREATE KEYSPACE IF NOT EXISTS {settings.CASSANDRA_KEYSPACE}
            WITH replication = {{
                'class': 'SimpleStrategy',
                'replication_factor': {settings.CASSANDRA_REPLICATION_FACTOR}
            }}
        """)
        self.session.set_keyspace(settings.CASSANDRA_KEYSPACE)

    def _init_tables(self):
        self.session.execute("""
            CREATE TABLE IF NOT EXISTS messages_by_conversation (
                conversation_id text,
                message_ts timestamp,
                message_id text,
                sender_id text,
                encrypted_payload blob,
                encrypted_key text,
                message_type text,
                metadata text,
                created_at timestamp,
                PRIMARY KEY (conversation_id, message_ts, message_id)
            ) WITH CLUSTERING ORDER BY (message_ts DESC, message_id ASC)
              AND gc_grace_seconds = 864000
              AND compaction = {'class': 'TimeWindowCompactionStrategy', 'compaction_window_size': 1, 'compaction_window_unit': 'DAYS'}
        """)

        self.session.execute("""
            CREATE TABLE IF NOT EXISTS message_by_id (
                message_id text PRIMARY KEY,
                conversation_id text,
                sender_id text,
                message_ts timestamp,
                encrypted_payload blob,
                encrypted_key text,
                message_type text,
                metadata text,
                created_at timestamp
            )
        """)

    def get_session(self):
        if not self.session:
            raise RuntimeError("Cassandra session not initialized")
        return self.session

    def close(self):
        if self.cluster:
            self.cluster.shutdown()
            logger.info("Cassandra connection closed")


cassandra_client = CassandraClient()
