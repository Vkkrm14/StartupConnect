# Cassandra - truncate both message tables
docker exec trustgraph-cassandra cqlsh -e "TRUNCATE messaging.messages_by_conversation; TRUNCATE messaging.message_by_id;"

# MongoDB - delete all conversation data
docker exec trustgraph-mongodb mongosh -u trustgraph -p trustgraph_secure_2024 --authenticationDatabase admin trustgraph_db --eval "db.conversations.deleteMany({}); db.user_encryption_keys.deleteMany({}); db.user_blocks.deleteMany({});"

# Redis - flush all keys (⚠️ warning: this clears everything)
docker exec trustgraph-redis redis-cli FLUSHALL