#!/usr/bin/env python3
"""Clear messaging service data (conversations, messages, etc.)"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URL = "mongodb://trustgraph:trustgraph_secure_2024@localhost:27017/trustgraph_db?authSource=admin"


async def clear_messaging_data():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client.get_default_database()
    
    print("Clearing messaging data...")
    
    # Clear conversations
    result = await db.conversations.delete_many({})
    print(f"  Deleted {result.deleted_count} conversations")
    
    # Clear messages (if using MongoDB for messages)
    result = await db.messages.delete_many({})
    print(f"  Deleted {result.deleted_count} messages")
    
    # Clear user blocks
    result = await db.user_blocks.delete_many({})
    print(f"  Deleted {result.deleted_count} user blocks")
    
    # Clear encryption keys
    result = await db.user_encryption_keys.delete_many({})
    print(f"  Deleted {result.deleted_count} encryption keys")
    
    print("\nMessaging data cleared successfully!")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(clear_messaging_data())
