"""Data seeding script for TrustGraph development - Uses Graph Service API"""

import requests
import uuid
from datetime import datetime, timezone
import random
import time
import sys
import hashlib
from typing import Dict, List
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.driver.serializer import GraphBinarySerializersV1

# Configuration
GRAPH_SERVICE_URL = "http://100.70.53.90:8001"
SEARCH_SERVICE_URL = "http://100.70.53.90:8003"
JANUSGRAPH_URL    = "ws://100.70.53.90:8182/gremlin"
API_TIMEOUT = 10
DEFAULT_PASSWORD = "password123"  # Default password for all seeded users

# Sample data
FOUNDERS = [
    {"name": "Alice Johnson", "email": "alice@startup.com", "domain": ["fintech", "saas"], "geography": "San Francisco"},
    {"name": "Bob Smith", "email": "bob@techco.com", "domain": ["healthtech", "ai-ml"], "geography": "New York"},
    {"name": "Carol Davis", "email": "carol@innovate.io", "domain": ["e-commerce", "saas"], "geography": "Austin"},
    {"name": "David Lee", "email": "david@venture.io", "domain": ["fintech", "blockchain"], "geography": "San Francisco"},
    {"name": "Emma Wilson", "email": "emma@startup.ai", "domain": ["ai-ml", "edtech"], "geography": "Boston"},
]

INVESTORS = [
    {"name": "Frank Miller", "email": "frank@vc-firm.com", "domain": ["fintech", "saas"], "geography": "Palo Alto"},
    {"name": "Grace Chen", "email": "grace@capital.vc", "domain": ["healthtech", "ai-ml"], "geography": "San Francisco"},
    {"name": "Henry Brown", "email": "henry@invest.com", "domain": ["e-commerce", "blockchain"], "geography": "New York"},
]

CONNECTORS = [
    {"name": "Ivy Martinez", "email": "ivy@network.com", "domain": ["fintech", "saas"], "geography": "San Francisco"},
    {"name": "Jack Taylor", "email": "jack@connect.io", "domain": ["healthtech", "ai-ml"], "geography": "Boston"},
]

STARTUPS = [
    {"name": "FinFlow", "domain": "fintech", "stage": "seed", "geography": "San Francisco"},
    {"name": "HealthAI", "domain": "healthtech", "stage": "seriesA", "geography": "Boston"},
    {"name": "EduTech Pro", "domain": "edtech", "stage": "seed", "geography": "Austin"},
    {"name": "BlockChain Solutions", "domain": "blockchain", "stage": "seriesB", "geography": "New York"},
]


# ── Trust score formula (mirrors trust_scoring.py compute_score) ─────────────
def compute_score(
    interaction_count: int,
    successful_intros: int,
    last_interaction_at: float = None
) -> float:
    """Compute trust score from edge counters. Base = 0.0, must be earned."""
    interaction_bonus = min(interaction_count / 20.0, 1.0) * 0.40
    success_bonus     = min(successful_intros  / 10.0, 1.0) * 0.40
    recency_bonus = 0.0
    if last_interaction_at:
        days_since = (datetime.utcnow().timestamp() - last_interaction_at) / 86400
        if days_since <= 90:
            recency_bonus = (1 - days_since / 90) * 0.20
    return round(min(interaction_bonus + success_bonus + recency_bonus, 1.0), 4)


def get_gremlin_traversal():
    """Open a direct gremlin connection to JanusGraph."""
    conn = DriverRemoteConnection(
        JANUSGRAPH_URL, 'g',
        message_serializer=GraphBinarySerializersV1()
    )
    return traversal().withRemote(conn), conn


def check_service_health() -> bool:
    """Check if Graph Service is accessible"""
    try:
        response = requests.get(f"{GRAPH_SERVICE_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Cannot reach Graph Service: {e}")
        return False


def check_database_empty() -> bool:
    """Check if JanusGraph database is empty"""
    try:
        connection = DriverRemoteConnection(
            JANUSGRAPH_URL,
            'g',
            message_serializer=GraphBinarySerializersV1()
        )
        g = traversal().withRemote(connection)
        
        vertex_count = g.V().count().next()
        connection.close()
        
        return vertex_count == 0
    except Exception as e:
        print(f"⚠️ Could not check database status: {e}")
        return None


def clear_database() -> bool:
    """Clear all data from JanusGraph database"""
    try:
        print("🗑️ Clearing existing data from database...")
        connection = DriverRemoteConnection(
            JANUSGRAPH_URL,
            'g',
            message_serializer=GraphBinarySerializersV1()
        )
        g = traversal().withRemote(connection)
        
        # Get counts before deletion
        vertex_count = g.V().count().next()
        edge_count = g.E().count().next()
        
        if vertex_count > 0 or edge_count > 0:
            print(f"  Found {vertex_count} vertices and {edge_count} edges")
            g.V().drop().iterate()
            print("  ✅ Database cleared")
        else:
            print("  ℹ️ Database was already empty")
        
        connection.close()
        return True
    except Exception as e:
        print(f"❌ Failed to clear database: {e}")
        return False


def get_user_by_name(name: str) -> Dict:
    """Check if a user already exists by name"""
    try:
        # Note: This would require a GET endpoint that accepts name query
        # For now, we'll use a workaround with direct gremlin query via a hypothetical endpoint
        # In a real scenario, you'd add a query endpoint to the Graph Service
        return None
    except Exception:
        return None


def get_startup_by_name(name: str) -> Dict:
    """Check if a startup already exists by name"""
    try:
        return None
    except Exception:
        return None


def create_user(user_data: dict, role: str) -> Dict:
    """Create a user via Graph Service API"""
    # Hash the default password using SHA256 (same as auth.py)
    password_hash = hashlib.sha256(DEFAULT_PASSWORD.encode()).hexdigest()
    
    payload = {
        "name": user_data["name"],
        "email": user_data["email"],
        "password_hash": password_hash,
        "role_primary": role,
        "domain_tags": user_data["domain"],
        "geography": user_data.get("geography"),
        "experience_years": random.randint(2, 15),
        "verification_status": "verified"
    }
    
    try:
        response = requests.post(
            f"{GRAPH_SERVICE_URL}/api/v1/vertices/users",
            json=payload,
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create user {user_data['name']}: {e}")
        raise


def index_user_in_search(user: Dict, role: str, user_info: dict) -> bool:
    """Index a user into Elasticsearch via Search Service"""
    try:
        payload = {
            "user_id": user["user_id"],
            "name": user["name"],
            "role_primary": role,
            "roles_secondary": user.get("roles_secondary", []),
            "domain_tags": user.get("domain_tags", user_info.get("domain", [])),
            "geography": user.get("geography", user_info.get("geography", "")),
            "experience_years": user.get("experience_years", 0),
            "reputation_score": user.get("reputation_score", 0.0),
            "verification_status": user.get("verification_status", "verified"),
            "bio": user.get("bio", ""),
            "created_at": user.get("created_at", "")
        }
        response = requests.post(
            f"{SEARCH_SERVICE_URL}/api/v1/search/index/user",
            json=payload,
            timeout=API_TIMEOUT
        )
        return response.status_code == 200
    except Exception as e:
        print(f"  ⚠️  Could not index {user['name']} in Elasticsearch: {e}")
        return False


def create_startup(startup_data: dict) -> Dict:
    """Create a startup via Graph Service API"""
    payload = {
        "name": startup_data["name"],
        "domain": startup_data["domain"],
        "stage": startup_data["stage"],
        "geography": startup_data.get("geography"),
        "visibility_level": "public"
    }
    
    try:
        response = requests.post(
            f"{GRAPH_SERVICE_URL}/api/v1/vertices/startups",
            json=payload,
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create startup {startup_data['name']}: {e}")
        raise


def create_trusts_edge(
    from_user_id: str,
    to_user_id: str,
    trust_score_hint: float,
    domain_tags: List[str] = None
) -> dict:
    """
    Create a TRUSTS edge directly in JanusGraph (no REST dependency).
    trust_score_hint drives the simulated interaction/intro history so the
    formula produces a realistic score for the seeded relationship.
    """
    # Map the desired trust level to realistic interaction history
    if trust_score_hint >= 0.85:
        interaction_count = random.randint(15, 20)
        successful_intros = random.randint(7, 10)
    elif trust_score_hint >= 0.70:
        interaction_count = random.randint(8, 14)
        successful_intros = random.randint(3, 6)
    else:
        interaction_count = random.randint(3, 7)
        successful_intros = random.randint(1, 3)

    # Simulate a recent interaction (within last 30 days)
    last_interaction_at = datetime.utcnow().timestamp() - random.randint(1, 30) * 86400

    # Compute the score using the same formula as trust_scoring.py
    computed_score = compute_score(
        interaction_count=interaction_count,
        successful_intros=successful_intros,
        last_interaction_at=last_interaction_at
    )

    edge_id    = str(uuid.uuid4())
    created_at = int(datetime.utcnow().timestamp())

    try:
        g, conn = get_gremlin_traversal()
        try:
            g.V().has('User', 'user_id', from_user_id) \
                .addE('TRUSTS') \
                .to(__.V().has('User', 'user_id', to_user_id)) \
                .property('edge_id',           edge_id) \
                .property('trust_score',        computed_score) \
                .property('strength_score',     round(random.uniform(0.5, 0.9), 2)) \
                .property('recency_score',      round(random.uniform(0.6, 1.0), 2)) \
                .property('interaction_count',  interaction_count) \
                .property('successful_intros',  successful_intros) \
                .property('endorsement_count',  random.randint(0, 5)) \
                .property('last_interaction_at', last_interaction_at) \
                .property('created_at',         created_at) \
                .iterate()
            if domain_tags:
                for tag in domain_tags:
                    g.E().has('edge_id', edge_id).property('domain_tags', tag).iterate()
        finally:
            conn.close()

        return {
            "edge_id": edge_id,
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "trust_score": computed_score,
            "interaction_count": interaction_count,
            "successful_intros": successful_intros,
        }
    except Exception as e:
        print(f"❌ Failed to create TRUSTS edge directly: {e}")
        raise


def create_founded_edge(user_id: str, startup_id: str) -> Dict:
    """Create a FOUNDED edge via Graph Service API"""
    payload = {
        "user_id": user_id,
        "startup_id": startup_id,
        "role": "founder",
        "active": True
    }
    
    try:
        response = requests.post(
            f"{GRAPH_SERVICE_URL}/api/v1/edges/founded",
            json=payload,
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create FOUNDED edge: {e}")
        raise


def create_invested_in_edge(investor_id: str, startup_id: str, round_type: str, year: int) -> Dict:
    """Create an INVESTED_IN edge via Graph Service API"""
    amount_ranges = {
        "seed": "100K-500K",
        "seriesA": "1M-5M",
        "seriesB": "5M-20M"
    }
    
    payload = {
        "investor_id": investor_id,
        "startup_id": startup_id,
        "round": round_type,
        "amount_range": amount_ranges.get(round_type),
        "year": year,
        "visibility": "trusted_only"
    }
    
    try:
        response = requests.post(
            f"{GRAPH_SERVICE_URL}/api/v1/edges/invested",
            json=payload,
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create INVESTED_IN edge: {e}")
        raise


def seed_data():
    """Seed the database with sample data using Graph Service API"""
    
    print("🌱 Starting data seeding via Graph Service API...")
    print(f"📍 Graph Service URL: {GRAPH_SERVICE_URL}")
    
    # Check service health (non-blocking: warn only, edges are seeded directly)
    print("Checking Graph Service availability...")
    if not check_service_health():
        print("Graph Service is not available — users/startups will NOT be created.")
        print("   Start graph-service first:  docker compose up -d graph-service")
        print("   Or run with --skip-service to create users directly via gremlin.")
        return
    print("✅ Graph Service is healthy and ready")
    
    # Check if database is empty
    print("\n🔍 Checking database status...")
    is_empty = check_database_empty()
    
    if is_empty is False:  # Database has data
        print("⚠️  Database contains existing data")
        response = input("Do you want to clear it before seeding? (yes/no): ")
        if response.lower() == 'yes':
            if not clear_database():
                print("❌ Failed to clear database. Aborting.")
                return
        else:
            print("⚠️  Seeding into non-empty database. This may create duplicates!")
            time.sleep(2)  # Give user time to read the warning
    
    user_ids = {}
    startup_ids = {}
    created_users = []  # Track all created users for ES indexing

    # Create Founders
    print("\n👤 Creating founders...")
    for founder in FOUNDERS:
        user = create_user(founder, "founder")
        user_ids[founder["name"]] = user["user_id"]
        created_users.append((user, "founder", founder))
        print(f"  ✅ {founder['name']} (ID: {user['user_id'][:8]}...)")
    
    # Create Investors
    print("\n💰 Creating investors...")
    for investor in INVESTORS:
        user = create_user(investor, "investor")
        user_ids[investor["name"]] = user["user_id"]
        created_users.append((user, "investor", investor))
        print(f"  ✅ {investor['name']} (ID: {user['user_id'][:8]}...)")
    
    # Create Connectors
    print("\n🔗 Creating connectors...")
    for connector in CONNECTORS:
        user = create_user(connector, "connector")
        user_ids[connector["name"]] = user["user_id"]
        created_users.append((user, "connector", connector))
        print(f"  ✅ {connector['name']} (ID: {user['user_id'][:8]}...)")

    # Index all users into Elasticsearch
    print("\n🔍 Indexing users into Elasticsearch...")
    es_ok = 0
    for user, role, info in created_users:
        success = index_user_in_search(user, role, info)
        if success:
            es_ok += 1
    print(f"  ✅ Indexed {es_ok}/{len(created_users)} users into Elasticsearch")

    # Create Startups
    print("\n🚀 Creating startups...")
    for startup in STARTUPS:
        startup_obj = create_startup(startup)
        startup_ids[startup["name"]] = startup_obj["startup_id"]
        print(f"  ✅ {startup['name']} (ID: {startup_obj['startup_id'][:8]}...)")
    
    # Create TRUSTS edges (trust network)
    print("\n🤝 Creating trust edges...")
    trust_relationships = [
        # Founder → Connector
        ("Alice Johnson", "Ivy Martinez", 0.85, ["fintech"]),
        ("Bob Smith", "Jack Taylor", 0.80, ["healthtech", "ai-ml"]),
        ("Carol Davis", "Ivy Martinez", 0.75, ["e-commerce"]),
        
        # Connector → Investor
        ("Ivy Martinez", "Frank Miller", 0.90, ["fintech"]),
        ("Ivy Martinez", "Grace Chen", 0.85, ["saas"]),
        ("Jack Taylor", "Grace Chen", 0.88, ["healthtech"]),
        
        # Founder → Founder
        ("Alice Johnson", "David Lee", 0.70, ["fintech"]),
        ("Bob Smith", "Emma Wilson", 0.75, ["ai-ml"]),
        
        # Investor → Investor
        ("Frank Miller", "Henry Brown", 0.80, []),
        ("Grace Chen", "Frank Miller", 0.85, []),
    ]
    
    for from_name, to_name, trust_score_hint, domain_tags in trust_relationships:
        edge = create_trusts_edge(
            user_ids[from_name],
            user_ids[to_name],
            trust_score_hint,
            domain_tags
        )
        print(f"  ✅ {from_name} → {to_name}  computed={edge['trust_score']:.4f}  (interactions={edge['interaction_count']}, intros={edge['successful_intros']})")
    
    # Create FOUNDED edges
    print("\n🎯 Creating FOUNDED edges...")
    founded_relationships = [
        ("Alice Johnson", "FinFlow"),
        ("Bob Smith", "HealthAI"),
        ("Emma Wilson", "EduTech Pro"),
        ("David Lee", "BlockChain Solutions"),
    ]
    
    for founder_name, startup_name in founded_relationships:
        create_founded_edge(
            user_ids[founder_name],
            startup_ids[startup_name]
        )
        print(f"  ✅ {founder_name} founded {startup_name}")
    
    # Create INVESTED_IN edges
    print("\n💸 Creating INVESTED_IN edges...")
    investment_relationships = [
        ("Frank Miller", "FinFlow", "seed", 2024),
        ("Grace Chen", "HealthAI", "seriesA", 2023),
        ("Henry Brown", "BlockChain Solutions", "seriesB", 2022),
    ]
    
    for investor_name, startup_name, round_type, year in investment_relationships:
        create_invested_in_edge(
            user_ids[investor_name],
            startup_ids[startup_name],
            round_type,
            year
        )
        print(f"  ✅ {investor_name} invested in {startup_name} ({round_type})")
    
    # Stats
    print("\n📊 Database Statistics:")
    print(f"  Users created: {len(user_ids)}")
    print(f"    - Founders: {len(FOUNDERS)}")
    print(f"    - Investors: {len(INVESTORS)}")
    print(f"    - Connectors: {len(CONNECTORS)}")
    print(f"  Startups created: {len(startup_ids)}")
    print(f"  Trust edges created: {len(trust_relationships)}")
    print(f"  Founded edges created: {len(founded_relationships)}")
    print(f"  Investment edges created: {len(investment_relationships)}")
    
    print("\n✅ Data seeding completed successfully!")
    print("\n💡 Next steps:")
    print("   - View API docs: http://100.70.53.90:8000/docs")
    print("   - Test Graph Service: http://100.70.53.90:8001/health")
    print("   - Query users: GET http://100.70.53.90:8001/api/v1/vertices/users")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed TrustGraph database with sample data')
    parser.add_argument('--clear', action='store_true', 
                       help='Clear database before seeding (no prompt)')
    parser.add_argument('--force', action='store_true',
                       help='Skip all confirmations')
    
    args = parser.parse_args()
    
    # Auto-clear if flag provided
    if args.clear:
        print("🗑️ --clear flag detected, clearing database...")
        connection = DriverRemoteConnection(
            JANUSGRAPH_URL,
            'g',
            message_serializer=GraphBinarySerializersV1()
        )
        g = traversal().withRemote(connection)
        vertex_count = g.V().count().next()
        if vertex_count > 0:
            print(f"  Deleting {vertex_count} vertices...")
            g.V().drop().iterate()
            print("  ✅ Database cleared")
        else:
            print("  ℹ️ Database was already empty")
        connection.close()
    
    try:
        # Set force mode for automated runs
        if args.force:
            # Monkey patch input to auto-answer 'yes'
            import builtins
            builtins.input = lambda _: 'yes'
        
        seed_data()
    except KeyboardInterrupt:
        print("\n\n⚠️  Seeding interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Seeding failed: {e}")
        import traceback
        traceback.print_exc()


