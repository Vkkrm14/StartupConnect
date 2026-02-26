"""Data seeding script for TrustGraph development - Uses Graph Service API"""

import requests
import uuid
from datetime import datetime, timezone
import random
import time
from typing import Dict, List

# Configuration
GRAPH_SERVICE_URL = "http://localhost:8001"
API_TIMEOUT = 10

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


def check_service_health() -> bool:
    """Check if Graph Service is accessible"""
    try:
        response = requests.get(f"{GRAPH_SERVICE_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Cannot reach Graph Service: {e}")
        return False


def create_user(user_data: dict, role: str) -> Dict:
    """Create a user via Graph Service API"""
    payload = {
        "name": user_data["name"],
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


def create_trusts_edge(from_user_id: str, to_user_id: str, trust_score: float, domain_tags: List[str] = None) -> Dict:
    """Create a TRUSTS edge via Graph Service API"""
    payload = {
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
        "trust_score": trust_score,
        "strength_score": round(random.uniform(0.5, 0.9), 2),
        "recency_score": round(random.uniform(0.6, 1.0), 2),
        "interaction_count": random.randint(5, 20),
        "endorsement_count": random.randint(0, 5),
        "domain_tags": domain_tags or []
    }
    
    try:
        response = requests.post(
            f"{GRAPH_SERVICE_URL}/api/v1/edges/trusts",
            json=payload,
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create TRUSTS edge: {e}")
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
    
    # Check service health
    print("\n🔍 Checking Graph Service availability...")
    if not check_service_health():
        print("❌ Graph Service is not available. Make sure it's running:")
        print("   docker compose ps graph-service")
        return
    
    print("✅ Graph Service is healthy and ready")
    
    user_ids = {}
    startup_ids = {}
    
    # Create Founders
    print("\n👤 Creating founders...")
    for founder in FOUNDERS:
        user = create_user(founder, "founder")
        user_ids[founder["name"]] = user["user_id"]
        print(f"  ✅ {founder['name']} (ID: {user['user_id'][:8]}...)")
    
    # Create Investors
    print("\n💰 Creating investors...")
    for investor in INVESTORS:
        user = create_user(investor, "investor")
        user_ids[investor["name"]] = user["user_id"]
        print(f"  ✅ {investor['name']} (ID: {user['user_id'][:8]}...)")
    
    # Create Connectors
    print("\n🔗 Creating connectors...")
    for connector in CONNECTORS:
        user = create_user(connector, "connector")
        user_ids[connector["name"]] = user["user_id"]
        print(f"  ✅ {connector['name']} (ID: {user['user_id'][:8]}...)")
    
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
    
    for from_name, to_name, trust_score, domain_tags in trust_relationships:
        create_trusts_edge(
            user_ids[from_name],
            user_ids[to_name],
            trust_score,
            domain_tags
        )
        print(f"  ✅ {from_name} → {to_name} ({trust_score})")
    
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
    print("   - View API docs: http://localhost:8000/docs")
    print("   - Test Graph Service: http://localhost:8001/health")
    print("   - Query users: GET http://localhost:8001/api/v1/vertices/users")


if __name__ == "__main__":
    try:
        seed_data()
    except KeyboardInterrupt:
        print("\n\n⚠️  Seeding interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Seeding failed: {e}")
        import traceback
        traceback.print_exc()

