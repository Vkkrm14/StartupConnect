"""Data seeding script for TrustGraph development - Uses Graph Service API"""

import requests
import uuid
from datetime import datetime, timezone
import random
import time
import sys
import hashlib
import os
from typing import Dict, List
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.driver.serializer import GraphSONSerializersV3d0

# Configuration
GRAPH_SERVICE_URL = os.getenv("GRAPH_SERVICE_URL", "http://localhost:8001")
SEARCH_SERVICE_URL = os.getenv("SEARCH_SERVICE_URL", "http://localhost:8003")
JANUSGRAPH_URL = os.getenv("JANUSGRAPH_URL", "ws://localhost:8182/gremlin")
API_TIMEOUT = 10
DEFAULT_PASSWORD = "password123"  # Default password for all seeded users
EXTRA_TRUST_CONNECTION_TARGET = int(os.getenv("EXTRA_TRUST_CONNECTION_TARGET", "18"))
EXTRA_DISTRUST_EDGES_TARGET = int(os.getenv("EXTRA_DISTRUST_EDGES_TARGET", "8"))

# Sample data0
FOUNDERS = [
    {"name": "Alice Johnson", "email": "alice@startup.com", "domain": ["fintech", "saas"], "geography": "San Francisco"},
    {"name": "Bob Smith", "email": "bob@techco.com", "domain": ["healthtech", "ai-ml"], "geography": "New York"},
    {"name": "Carol Davis", "email": "carol@innovate.io", "domain": ["e-commerce", "saas"], "geography": "Austin"},
    {"name": "David Lee", "email": "david@venture.io", "domain": ["fintech", "blockchain"], "geography": "San Francisco"},
    {"name": "Emma Wilson", "email": "emma@startup.ai", "domain": ["ai-ml", "edtech"], "geography": "Boston"},
    {"name": "Fiona Park", "email": "fiona@climategrid.io", "domain": ["climate", "saas"], "geography": "Seattle"},
    {"name": "George Kim", "email": "george@agrotech.co", "domain": ["agritech", "ai-ml"], "geography": "Chicago"},
    {"name": "Hannah Reed", "email": "hannah@mobipay.app", "domain": ["fintech", "mobile"], "geography": "Miami"},
]

INVESTORS = [
    {"name": "Frank Miller", "email": "frank@vc-firm.com", "domain": ["fintech", "saas"], "geography": "Palo Alto"},
    {"name": "Grace Chen", "email": "grace@capital.vc", "domain": ["healthtech", "ai-ml"], "geography": "San Francisco"},
    {"name": "Henry Brown", "email": "henry@invest.com", "domain": ["e-commerce", "blockchain"], "geography": "New York"},
    {"name": "Isabella Moore", "email": "isabella@northstar.vc", "domain": ["climate", "agritech"], "geography": "Denver"},
    {"name": "James Patel", "email": "james@earlystage.fund", "domain": ["edtech", "mobile"], "geography": "Los Angeles"},
    {"name": "Karen Liu", "email": "karen@alphaangels.com", "domain": ["healthtech", "fintech"], "geography": "San Diego"},
]

CONNECTORS = [
    {"name": "Ivy Martinez", "email": "ivy@network.com", "domain": ["fintech", "saas"], "geography": "San Francisco"},
    {"name": "Jack Taylor", "email": "jack@connect.io", "domain": ["healthtech", "ai-ml"], "geography": "Boston"},
    {"name": "Liam Scott", "email": "liam@bridgehub.net", "domain": ["climate", "fintech"], "geography": "Seattle"},
    {"name": "Nora Evans", "email": "nora@warmintro.co", "domain": ["edtech", "mobile"], "geography": "Chicago"},
    {"name": "Omar Rahman", "email": "omar@venturemesh.io", "domain": ["agritech", "healthtech"], "geography": "Austin"},
]

STARTUPS = [
    {"name": "FinFlow", "domain": "fintech", "stage": "seed", "geography": "San Francisco"},
    {"name": "HealthAI", "domain": "healthtech", "stage": "seriesA", "geography": "Boston"},
    {"name": "EduTech Pro", "domain": "edtech", "stage": "seed", "geography": "Austin"},
    {"name": "BlockChain Solutions", "domain": "blockchain", "stage": "seriesB", "geography": "New York"},
    {"name": "AgroSense", "domain": "agritech", "stage": "seed", "geography": "Chicago"},
    {"name": "ClimateLedger", "domain": "climate", "stage": "seriesA", "geography": "Seattle"},
    {"name": "PocketCare", "domain": "mobile", "stage": "seed", "geography": "Los Angeles"},
]


# ── Trust score formula (mirrors trust_scoring.py compute_score) ─────────────
def compute_score(
    interaction_count: int,
    successful_intros: int,
    last_interaction_at: float = None,
    interaction_decay_factor: float = 1.0
) -> float:
    """Compute trust score from edge counters. Base = 0.0, must be earned."""
    effective_interactions = interaction_count * max(0.0, min(interaction_decay_factor, 1.0))
    interaction_bonus = min(effective_interactions / 20.0, 1.0) * 0.40
    success_bonus     = min(successful_intros  / 10.0, 1.0) * 0.40
    recency_bonus = 0.0
    if last_interaction_at:
        days_since = (datetime.now(timezone.utc).timestamp() - last_interaction_at) / 86400
        if days_since <= 90:
            recency_bonus = (1 - days_since / 90) * 0.20
    return round(min(interaction_bonus + success_bonus + recency_bonus, 1.0), 4)


def compute_recency_score(last_interaction_at: float | None) -> float:
    """Mirror trust_scoring.py recency behaviour for seeded edges."""
    if not last_interaction_at:
        return 1.0

    days_since = (datetime.now(timezone.utc).timestamp() - last_interaction_at) / 86400
    return round(max(0.0, 1.0 - (days_since / 90.0)), 4)


def get_gremlin_traversal():
    """Open a direct gremlin connection to JanusGraph."""
    conn = DriverRemoteConnection(
        JANUSGRAPH_URL, 'g',
        message_serializer=GraphSONSerializersV3d0()
    )
    return traversal().withRemote(conn), conn


def get_distrust_counts() -> Dict[str, int]:
    """Return distrust edge counts for verification after seeding."""
    try:
        g, conn = get_gremlin_traversal()
        try:
            total = int(g.E().hasLabel('DISTRUSTS').count().next())
            active = int(
                g.E().hasLabel('DISTRUSTS')
                .has('is_active', True)
                .not_(__.has('is_disputed', True))
                .count()
                .next()
            )
            disputed = int(
                g.E().hasLabel('DISTRUSTS')
                .has('is_disputed', True)
                .count()
                .next()
            )
            return {"total": total, "active_effective": active, "disputed": disputed}
        finally:
            conn.close()
    except Exception:
        return {"total": 0, "active_effective": 0, "disputed": 0}


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
            message_serializer=GraphSONSerializersV3d0()
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
            message_serializer=GraphSONSerializersV3d0()
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


def get_user_by_email(email: str) -> Dict:
    """Fetch an existing user by email via Graph Service API."""
    try:
        response = requests.get(
            f"{GRAPH_SERVICE_URL}/api/v1/vertices/users/by-email/{email}",
            timeout=API_TIMEOUT,
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


def get_startup_by_name(name: str) -> Dict:
    """Check if a startup already exists by name"""
    try:
        g, conn = get_gremlin_traversal()
        try:
            startup = (
                g.V()
                .has('Startup', 'name', name)
                .valueMap('startup_id', 'name', 'domain', 'stage', 'geography', 'created_at')
                .limit(1)
                .toList()
            )
            if not startup:
                return None

            row = startup[0]
            return {
                'startup_id': row.get('startup_id', [None])[0],
                'name': row.get('name', [''])[0],
                'domain': row.get('domain', [''])[0],
                'stage': row.get('stage', [''])[0],
                'geography': row.get('geography', [''])[0],
                'created_at': row.get('created_at', [None])[0],
            }
        finally:
            conn.close()
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
        if response.status_code in (200, 201):
            return response.json()

        # Common on reruns: backend may throw 500 for duplicate email constraints.
        existing = get_user_by_email(user_data["email"])
        if existing:
            print(f"  ℹ️ Reusing existing user by email: {user_data['email']}")
            return existing

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        existing = get_user_by_email(user_data["email"])
        if existing:
            print(f"  ℹ️ Reusing existing user by email: {user_data['email']}")
            return existing
        err_detail = ""
        if hasattr(e, "response") and e.response is not None:
            err_detail = f" | response={e.response.text}"
        print(f"❌ Failed to create user {user_data['name']}: {e}{err_detail}")
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
        if response.status_code in (200, 201):
            return response.json()

        # Reruns may fail if startup already exists; fall back to graph lookup by name.
        existing = get_startup_by_name(startup_data["name"])
        if existing and existing.get("startup_id"):
            print(f"  ℹ️ Reusing existing startup by name: {startup_data['name']}")
            return existing

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        existing = get_startup_by_name(startup_data["name"])
        if existing and existing.get("startup_id"):
            print(f"  ℹ️ Reusing existing startup by name: {startup_data['name']}")
            return existing
        err_detail = ""
        if hasattr(e, "response") and e.response is not None:
            err_detail = f" | response={e.response.text}"
        print(f"❌ Failed to create startup {startup_data['name']}: {e}{err_detail}")
        raise


def _create_directed_trust_edge(
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
    last_interaction_at = datetime.now(timezone.utc).timestamp() - random.randint(1, 30) * 86400
    recency_score = compute_recency_score(last_interaction_at)

    # Compute the score using the same formula as trust_scoring.py
    computed_score = compute_score(
        interaction_count=interaction_count,
        successful_intros=successful_intros,
        last_interaction_at=last_interaction_at
    )

    edge_id = str(uuid.uuid4())
    created_at = int(datetime.now(timezone.utc).timestamp())

    try:
        g, conn = get_gremlin_traversal()
        try:
            g.V().has('User', 'user_id', from_user_id) \
                .addE('TRUSTS') \
                .to(__.V().has('User', 'user_id', to_user_id)) \
                .property('edge_id', edge_id) \
                .property('trust_score', computed_score) \
                .property('strength_score', round(random.uniform(0.5, 0.9), 2)) \
                .property('recency_score', recency_score) \
                .property('interaction_count', interaction_count) \
                .property('successful_intros', successful_intros) \
                .property('interaction_decay_factor', 1.0) \
                .property('endorsement_count', random.randint(0, 5)) \
                .property('last_interaction_at', last_interaction_at) \
                .property('is_mutual', True) \
                .property('status', 'accepted') \
                .property('created_at', created_at) \
                .property('accepted_at', created_at) \
                .property('updated_at', created_at) \
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
            "recency_score": recency_score,
            "interaction_count": interaction_count,
            "successful_intros": successful_intros,
        }
    except Exception as e:
        print(f"❌ Failed to create TRUSTS edge directly: {e}")
        raise


def create_mutual_trust_connection(
    user_a_id: str,
    user_b_id: str,
    trust_score_hint: float,
    domain_tags: List[str] = None,
) -> tuple[dict, dict]:
    """Create both accepted TRUSTS edges so the seeded pair is a real connection."""
    forward = _create_directed_trust_edge(
        user_a_id,
        user_b_id,
        trust_score_hint,
        domain_tags,
    )
    reverse = _create_directed_trust_edge(
        user_b_id,
        user_a_id,
        trust_score_hint,
        domain_tags,
    )
    return forward, reverse


def refresh_user_reputation(user_id: str) -> float:
    """Force-refresh reputation so seeded connections appear immediately in the UI."""
    response = requests.get(
        f"{GRAPH_SERVICE_URL}/api/v1/edges/trusts/reputation/{user_id}",
        timeout=API_TIMEOUT,
    )
    response.raise_for_status()
    return float(response.json().get("reputation_score", 0.0))


def fetch_user(user_id: str) -> Dict:
    """Fetch the latest user payload from graph-service."""
    response = requests.get(
        f"{GRAPH_SERVICE_URL}/api/v1/vertices/users/{user_id}",
        timeout=API_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


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


def create_distrusts_edge(from_user_id: str, to_user_id: str, reason_category: str, severity: float) -> Dict:
    """
    Create a DISTRUSTS edge via Graph Service API.
    
    Args:
        from_user_id: User filing the distrust report
        to_user_id: User being reported
        reason_category: fraud, unreliable_collaborator, harassment, dispute
        severity: 0.0-1.0 severity level
    
    Returns:
        Response from Graph Service
    """
    payload = {
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
        "reason_category": reason_category,
        "severity": severity,
        "evidence_notes": f"Seeded distrust edge for testing"
    }
    
    try:
        response = requests.post(
            f"{GRAPH_SERVICE_URL}/api/v1/edges/distrusts",
            json=payload,
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        err_detail = ""
        if hasattr(e, "response") and e.response is not None:
            err_detail = f" | response={e.response.text}"
        print(f"❌ Failed to create DISTRUSTS edge: {e}{err_detail}")
        raise


def activate_distrusts_edge(from_user_id: str, to_user_id: str) -> bool:
    """Activate a DISTRUSTS report so it takes effect in path filtering."""
    try:
        response = requests.put(
            f"{GRAPH_SERVICE_URL}/api/v1/edges/distrusts/activate",
            params={"from_user_id": from_user_id, "to_user_id": to_user_id},
            timeout=API_TIMEOUT,
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        err_detail = ""
        if hasattr(e, "response") and e.response is not None:
            err_detail = f" | response={e.response.text}"
        print(f"❌ Failed to activate DISTRUSTS edge: {e}{err_detail}")
        return False


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
    
    # Create mutual accepted TRUSTS edges (connection network)
    print("\n🤝 Creating mutual trust connections...")
    trust_relationships = [
        # Founder ↔ Connector (primary warm-intro channels)
        ("Alice Johnson", "Ivy Martinez", 0.85, ["fintech"]),
        ("Bob Smith", "Jack Taylor", 0.80, ["healthtech", "ai-ml"]),
        ("Carol Davis", "Ivy Martinez", 0.75, ["e-commerce"]),
        ("David Lee", "Liam Scott", 0.82, ["fintech", "climate"]),
        ("Emma Wilson", "Nora Evans", 0.84, ["edtech", "mobile"]),
        ("Fiona Park", "Liam Scott", 0.90, ["climate"]),
        ("George Kim", "Omar Rahman", 0.86, ["agritech", "ai-ml"]),
        ("Hannah Reed", "Nora Evans", 0.81, ["mobile", "fintech"]),

        # Connector ↔ Investor (distribution routes)
        ("Ivy Martinez", "Frank Miller", 0.90, ["fintech"]),
        ("Ivy Martinez", "Grace Chen", 0.85, ["saas"]),
        ("Jack Taylor", "Grace Chen", 0.88, ["healthtech"]),
        ("Liam Scott", "Isabella Moore", 0.89, ["climate", "agritech"]),
        ("Nora Evans", "James Patel", 0.87, ["edtech", "mobile"]),
        ("Omar Rahman", "Karen Liu", 0.83, ["healthtech"]),

        # Founder ↔ Founder (peer network)
        ("Alice Johnson", "David Lee", 0.70, ["fintech"]),
        ("Bob Smith", "Emma Wilson", 0.75, ["ai-ml"]),
        ("Fiona Park", "George Kim", 0.78, ["climate", "agritech"]),
        ("Hannah Reed", "Alice Johnson", 0.74, ["fintech", "mobile"]),

        # Investor ↔ Investor (syndicate network)
        ("Frank Miller", "Henry Brown", 0.80, []),
        ("Grace Chen", "Frank Miller", 0.85, []),
        ("Isabella Moore", "Karen Liu", 0.79, ["healthtech"]),
        ("James Patel", "Grace Chen", 0.76, ["edtech"]),

        # Select founder ↔ investor direct trust (post-deal relationships)
        ("David Lee", "Frank Miller", 0.72, ["fintech"]),
        ("Fiona Park", "Isabella Moore", 0.77, ["climate"]),
        ("Emma Wilson", "James Patel", 0.73, ["edtech"]),
    ]

    # Build a richer graph by adding extra generated bridge links across clusters.
    profile_lookup = {
        **{u["name"]: u for u in FOUNDERS},
        **{u["name"]: u for u in INVESTORS},
        **{u["name"]: u for u in CONNECTORS},
    }
    all_names = list(profile_lookup.keys())
    pair_key_set = {
        tuple(sorted((a, b))) for a, b, _, _ in trust_relationships
    }
    extra_trust_relationships = []
    attempts = 0
    max_attempts = EXTRA_TRUST_CONNECTION_TARGET * 12
    while len(extra_trust_relationships) < EXTRA_TRUST_CONNECTION_TARGET and attempts < max_attempts:
        attempts += 1
        from_name, to_name = random.sample(all_names, 2)
        pair_key = tuple(sorted((from_name, to_name)))
        if pair_key in pair_key_set:
            continue

        from_domains = profile_lookup[from_name].get("domain", [])
        to_domains = profile_lookup[to_name].get("domain", [])
        shared_domains = sorted(set(from_domains).intersection(to_domains))
        if shared_domains:
            chosen_domains = shared_domains[:2]
        else:
            merged = sorted(set(from_domains + to_domains))
            chosen_domains = merged[:2] if merged else []

        trust_score_hint = round(random.uniform(0.62, 0.92), 2)
        extra_trust_relationships.append(
            (from_name, to_name, trust_score_hint, chosen_domains)
        )
        pair_key_set.add(pair_key)

    trust_relationships.extend(extra_trust_relationships)
    print(
        f"  ℹ️ Added {len(extra_trust_relationships)} generated bridge trust links "
        f"(target={EXTRA_TRUST_CONNECTION_TARGET})"
    )

    for from_name, to_name, trust_score_hint, domain_tags in trust_relationships:
        forward, reverse = create_mutual_trust_connection(
            user_ids[from_name],
            user_ids[to_name],
            trust_score_hint,
            domain_tags
        )
        print(
            f"  ✅ {from_name} ↔ {to_name}  "
            f"forward={forward['trust_score']:.4f}  reverse={reverse['trust_score']:.4f}"
        )

    print("\n📈 Refreshing reputation scores...")
    refreshed_users = []
    for user_name, user_id in user_ids.items():
        reputation = refresh_user_reputation(user_id)
        refreshed_users.append((user_name, user_id, reputation))
        print(f"  ✅ {user_name}: reputation={reputation:.3f}")

    print("\n🔄 Re-indexing users with refreshed reputation...")
    reindexed = 0
    role_lookup = {
        **{u["name"]: ("founder", u) for u in FOUNDERS},
        **{u["name"]: ("investor", u) for u in INVESTORS},
        **{u["name"]: ("connector", u) for u in CONNECTORS},
    }
    for user_name, user_id, _ in refreshed_users:
        role, info = role_lookup[user_name]
        latest_user = fetch_user(user_id)
        if index_user_in_search(latest_user, role, info):
            reindexed += 1
    print(f"  ✅ Re-indexed {reindexed}/{len(refreshed_users)} users")
    
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
    
    # Create DISTRUSTS edges (conflict scenarios)
    print("\n⚠️  Creating DISTRUSTS edges (conflict test scenarios)...")
    distrust_relationships = [
        # Mutual dispute from an existing trusted pair
        ("Bob Smith", "Emma Wilson", "unreliable_collaborator", 0.7),
        ("Emma Wilson", "Bob Smith", "dispute", 0.6),

        # One-way distrust on existing trusted pairs
        ("David Lee", "Alice Johnson", "fraud", 0.8),
        ("George Kim", "Omar Rahman", "unreliable_collaborator", 0.65),
        ("Nora Evans", "James Patel", "dispute", 0.45),

        # Lower severity distrust (for resolution testing)
        ("Hannah Reed", "Nora Evans", "dispute", 0.35),
        ("Fiona Park", "Isabella Moore", "dispute", 0.3),
    ]

    # Generate additional distrusts from existing trusted pairs to satisfy edge guardrails.
    distrust_reasons = ["dispute", "unreliable_collaborator", "fraud", "harassment"]
    distrust_pair_set = {(a, b) for a, b, _, _ in distrust_relationships}
    trust_pair_directions = []
    for a, b, _, _ in trust_relationships:
        trust_pair_directions.append((a, b))
        trust_pair_directions.append((b, a))

    from_user_distrust_counts = {}
    for from_name, _, _, _ in distrust_relationships:
        from_user_distrust_counts[from_name] = from_user_distrust_counts.get(from_name, 0) + 1

    random.shuffle(trust_pair_directions)
    for from_name, to_name in trust_pair_directions:
        if len(distrust_relationships) >= (7 + EXTRA_DISTRUST_EDGES_TARGET):
            break
        if (from_name, to_name) in distrust_pair_set:
            continue
        if from_user_distrust_counts.get(from_name, 0) >= 3:
            continue
        reason = random.choice(distrust_reasons)
        severity = round(random.uniform(0.28, 0.82), 2)
        distrust_relationships.append((from_name, to_name, reason, severity))
        distrust_pair_set.add((from_name, to_name))
        from_user_distrust_counts[from_name] = from_user_distrust_counts.get(from_name, 0) + 1

    print(
        f"  ℹ️ Prepared {len(distrust_relationships)} distrust scenarios "
        f"(base=7, generated={max(len(distrust_relationships) - 7, 0)})"
    )
    
    distrust_count = 0
    distrust_active_count = 0
    distrust_disputed_count = 0
    for from_name, to_name, reason, severity in distrust_relationships:
        try:
            created = create_distrusts_edge(
                user_ids[from_name],
                user_ids[to_name],
                reason,
                severity
            )
            distrust_count += 1

            # For seed/demo behavior, auto-activate non-disputed reports so they impact traversal.
            # Disputed reports remain non-effective by policy.
            is_disputed = bool(created.get("is_disputed", False))
            if is_disputed:
                distrust_disputed_count += 1
                print(
                    f"  ✅ {from_name} → {to_name} ({reason}, severity={severity}) "
                    f"[disputed, left inactive]"
                )
            else:
                activated = activate_distrusts_edge(user_ids[from_name], user_ids[to_name])
                if activated:
                    distrust_active_count += 1
                    print(
                        f"  ✅ {from_name} → {to_name} ({reason}, severity={severity}) "
                        f"[activated]"
                    )
                else:
                    print(
                        f"  ⚠️  {from_name} → {to_name} created but activation failed"
                    )
        except Exception as e:
            print(f"  ⚠️  Failed to create DISTRUSTS: {from_name} → {to_name}: {e}")
    
    # Stats
    print("\n📊 Database Statistics:")
    print(f"  Users created: {len(user_ids)}")
    print(f"    - Founders: {len(FOUNDERS)}")
    print(f"    - Investors: {len(INVESTORS)}")
    print(f"    - Connectors: {len(CONNECTORS)}")
    print(f"  Startups created: {len(startup_ids)}")
    print(f"  Trust edges created: {len(trust_relationships) * 2}")
    print(f"  Founded edges created: {len(founded_relationships)}")
    print(f"  Investment edges created: {len(investment_relationships)}")
    print(f"  Distrust edges created: {distrust_count}")
    print(f"    - Active distrust edges: {distrust_active_count}")
    print(f"    - Disputed/inactive distrust edges: {distrust_disputed_count}")

    distrust_graph_counts = get_distrust_counts()
    print("  Distrust edges in graph (post-seed verification):")
    print(f"    - Total DISTRUSTS edges: {distrust_graph_counts['total']}")
    print(f"    - Active/effective edges: {distrust_graph_counts['active_effective']}")
    print(f"    - Disputed edges: {distrust_graph_counts['disputed']}")
    
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
            message_serializer=GraphSONSerializersV3d0()
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
