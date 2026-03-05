#!/usr/bin/env python3
"""
Clear all chat / messaging data across every storage layer:
  - Cassandra : messages_by_conversation, message_by_id  (keyspace: messaging)
  - MongoDB   : conversations, user_encryption_keys, user_blocks
  - Redis     : presence, WebSocket sessions, typing indicators, rate limits,
                delivery buffers, pub/sub broadcast keys
  - Uploaded images (Docker volume mount or local path)

Usage:
    python clear_messaging_data.py            # dry-run (shows counts only)
    python clear_messaging_data.py --confirm  # actually deletes
"""

import argparse
import os

from pymongo import MongoClient
import redis

MONGODB_URL        = "mongodb://trustgraph:trustgraph_secure_2024@localhost:27017/trustgraph_db?authSource=admin"
REDIS_URL          = "redis://localhost:6379/0"
CASSANDRA_HOST     = "localhost"
CASSANDRA_PORT     = 9042
CASSANDRA_KEYSPACE = "messaging"

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "messaging-service", "uploads")


# --- Cassandra ----------------------------------------------------------------

def clear_cassandra(dry_run: bool):
    try:
        from cassandra.cluster import Cluster
        from cassandra.policies import DCAwareRoundRobinPolicy
    except (ImportError, Exception) as e:
        print(f"\n[Cassandra] Skipped ({type(e).__name__}: {str(e)[:60]}...)")
        return

    print("\n[Cassandra]")
    try:
        cluster = Cluster(
            contact_points=[CASSANDRA_HOST],
            port=CASSANDRA_PORT,
            load_balancing_policy=DCAwareRoundRobinPolicy(local_dc="datacenter1"),
        )
        session = cluster.connect(CASSANDRA_KEYSPACE)

        tables = ["messages_by_conversation", "message_by_id"]
        for table in tables:
            row = session.execute(f"SELECT COUNT(*) FROM {table}").one()
            count = row[0] if row else 0
            if dry_run:
                print(f"  Would TRUNCATE {table:<35}  ({count} rows)")
            else:
                session.execute(f"TRUNCATE {table}")
                print(f"  TRUNCATEd      {table:<35}  ({count} rows deleted)")

        cluster.shutdown()
    except Exception as exc:
        print(f"  Skipped ({type(exc).__name__}: {str(exc)[:60]}...)")


# --- MongoDB -----------------------------------------------------------------

def clear_mongo(dry_run: bool):
    print("\n[MongoDB]")
    try:
        client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
        db = client.get_default_database()

        collections = {
            "conversations":        "conversations",
            "user_encryption_keys": "encryption keys",
            "user_blocks":          "user blocks",
        }

        for coll, label in collections.items():
            count = db[coll].count_documents({})
            if dry_run:
                print(f"  Would delete {count:>6} {label}")
            else:
                result = db[coll].delete_many({})
                print(f"  Deleted     {result.deleted_count:>6} {label}")

        client.close()
    except Exception as exc:
        print(f"  ERROR: {exc}")


# --- Redis -------------------------------------------------------------------

_REDIS_PATTERNS = [
    "presence:*",
    "ws:sessions:*",
    "typing:*",
    "ratelimit:msg:*",
    "buffer:*",
    "ws:broadcast:*",
]

def clear_redis(dry_run: bool):
    print("\n[Redis]")
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)

        for pattern in _REDIS_PATTERNS:
            keys = list(r.scan_iter(match=pattern))
            if not keys:
                continue
            if dry_run:
                print(f"  Would delete {len(keys):>6} keys  ({pattern})")
            else:
                r.delete(*keys)
                print(f"  Deleted     {len(keys):>6} keys  ({pattern})")

        r.close()
    except Exception as exc:
        print(f"  ERROR: {exc}")


# --- Uploaded images ---------------------------------------------------------

def clear_images(dry_run: bool):
    print("\n[Image uploads]")
    images_dir = os.path.abspath(IMAGES_DIR)

    if not os.path.isdir(images_dir):
        print(f"  Directory not found, skipping: {images_dir}")
        return

    files = [
        os.path.join(root, f)
        for root, _, filenames in os.walk(images_dir)
        for f in filenames
    ]

    if dry_run:
        print(f"  Would delete {len(files)} file(s) in {images_dir}")
    else:
        deleted = 0
        for path in files:
            try:
                os.remove(path)
                deleted += 1
            except OSError as e:
                print(f"  WARNING: could not delete {path}: {e}")
        print(f"  Deleted {deleted} file(s) from {images_dir}")


# --- Main --------------------------------------------------------------------

def main(dry_run: bool):
    if dry_run:
        print("=" * 50)
        print("  DRY RUN - nothing will be deleted")
        print("  Re-run with --confirm to actually delete")
        print("=" * 50)
    else:
        print("=" * 50)
        print("  DELETING all messaging data ...")
        print("=" * 50)

    clear_cassandra(dry_run)
    clear_mongo(dry_run)
    clear_redis(dry_run)
    clear_images(dry_run)

    print("\n" + "=" * 50)
    if dry_run:
        print("  Dry run complete. Pass --confirm to delete.")
    else:
        print("  All messaging data cleared successfully.")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clear all chat / messaging data")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually delete data (omit for a dry-run)",
    )
    args = parser.parse_args()
    main(dry_run=not args.confirm)
