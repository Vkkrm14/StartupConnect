#!/usr/bin/env python3
"""
Test Graph Service API endpoints
Tests all major endpoints for vertices, edges, and paths
"""

import requests
import json
from typing import Dict, List
import time
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.driver.serializer import GraphBinarySerializersV1

# Configuration
BASE_URL = "http://100.70.53.90:8001"
API_BASE = f"{BASE_URL}/api/v1"

# Test data from seeding
TEST_USER_NAME = "Alice Johnson"
TEST_STARTUP_NAME = "FinFlow"

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_success(message: str):
    print(f"{GREEN}✅ {message}{RESET}")


def print_error(message: str):
    print(f"{RED}❌ {message}{RESET}")


def print_info(message: str):
    print(f"{BLUE}ℹ️  {message}{RESET}")


def print_warning(message: str):
    print(f"{YELLOW}⚠️  {message}{RESET}")


def test_health_endpoint():
    """Test health check endpoint"""
    print("\n" + "="*60)
    print("🏥 Testing Health Endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/health/", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Health endpoint returned: {data}")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Health check error: {e}")
        return False


def test_ready_endpoint():
    """Test readiness check endpoint"""
    print("\n" + "="*60)
    print("🔍 Testing Ready Endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/health/ready", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Ready endpoint returned: {data}")
            return True
        else:
            print_error(f"Ready check failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Ready check error: {e}")
        return False


def test_create_user():
    """Test creating a new user"""
    print("\n" + "="*60)
    print("👤 Testing Create User Endpoint")
    print("="*60)
    
    payload = {
        "name": "Test User",
        "role_primary": "founder",
        "domain_tags": ["test", "api"],
        "geography": "Test City",
        "experience_years": 5,
        "verification_status": "verified"
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/vertices/users",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            print_success(f"User created: {data['name']} (ID: {data['user_id'][:8]}...)")
            print_info(f"Full response: {json.dumps(data, indent=2)}")
            return data
        else:
            print_error(f"Failed to create user: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
    except Exception as e:
        print_error(f"Create user error: {e}")
        return None


def test_get_user(user_id: str):
    """Test getting a user by ID"""
    print("\n" + "="*60)
    print("🔎 Testing Get User Endpoint")
    print("="*60)
    
    try:
        response = requests.get(
            f"{API_BASE}/vertices/users/{user_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"User retrieved: {data['name']}")
            print_info(f"Full response: {json.dumps(data, indent=2)}")
            return data
        else:
            print_error(f"Failed to get user: {response.status_code}")
            return None
    except Exception as e:
        print_error(f"Get user error: {e}")
        return None


def test_create_startup():
    """Test creating a new startup"""
    print("\n" + "="*60)
    print("🚀 Testing Create Startup Endpoint")
    print("="*60)
    
    payload = {
        "name": "Test Startup",
        "domain": "test",
        "stage": "seed",
        "geography": "Test City",
        "visibility_level": "public"
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/vertices/startups",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            print_success(f"Startup created: {data['name']} (ID: {data['startup_id'][:8]}...)")
            print_info(f"Full response: {json.dumps(data, indent=2)}")
            return data
        else:
            print_error(f"Failed to create startup: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
    except Exception as e:
        print_error(f"Create startup error: {e}")
        return None


def test_create_trust_edge(from_user_id: str, to_user_id: str):
    """Test creating a TRUSTS edge"""
    print("\n" + "="*60)
    print("🤝 Testing Create TRUSTS Edge Endpoint")
    print("="*60)
    
    payload = {
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
        "trust_score": 0.75,
        "strength_score": 0.8,
        "recency_score": 0.9,
        "interaction_count": 10,
        "endorsement_count": 2,
        "domain_tags": ["test"]
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/edges/trusts",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            print_success(f"TRUSTS edge created: {from_user_id[:8]}... → {to_user_id[:8]}...")
            print_info(f"Trust score: {data['trust_score']}")
            return data
        else:
            print_error(f"Failed to create TRUSTS edge: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
    except Exception as e:
        print_error(f"Create TRUSTS edge error: {e}")
        return None


def test_create_founded_edge(user_id: str, startup_id: str):
    """Test creating a FOUNDED edge"""
    print("\n" + "="*60)
    print("🎯 Testing Create FOUNDED Edge Endpoint")
    print("="*60)
    
    payload = {
        "user_id": user_id,
        "startup_id": startup_id,
        "role": "founder",
        "active": True
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/edges/founded",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            print_success(f"FOUNDED edge created: {user_id[:8]}... → {startup_id[:8]}...")
            print_info(f"Role: {data['role']}")
            return data
        else:
            print_error(f"Failed to create FOUNDED edge: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
    except Exception as e:
        print_error(f"Create FOUNDED edge error: {e}")
        return None


def test_create_invested_edge(investor_id: str, startup_id: str):
    """Test creating an INVESTED_IN edge"""
    print("\n" + "="*60)
    print("💰 Testing Create INVESTED_IN Edge Endpoint")
    print("="*60)
    
    payload = {
        "investor_id": investor_id,
        "startup_id": startup_id,
        "round": "seed",
        "amount_range": "100K-500K",
        "year": 2024,
        "visibility": "trusted_only"
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/edges/invested",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            print_success(f"INVESTED_IN edge created: {investor_id[:8]}... → {startup_id[:8]}...")
            print_info(f"Round: {data['round']}, Amount: {data['amount_range']}")
            return data
        else:
            print_error(f"Failed to create INVESTED_IN edge: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
    except Exception as e:
        print_error(f"Create INVESTED_IN edge error: {e}")
        return None


def test_update_trust_score(from_user_id: str, to_user_id: str):
    """Test updating trust score"""
    print("\n" + "="*60)
    print("📊 Testing Update Trust Score Endpoint")
    print("="*60)
    
    params = {
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
        "new_score": 0.95
    }
    
    try:
        response = requests.put(
            f"{API_BASE}/edges/trusts/score",
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Trust score updated: {data}")
            return data
        else:
            print_error(f"Failed to update trust score: {response.status_code}")
            return None
    except Exception as e:
        print_error(f"Update trust score error: {e}")
        return None


def test_path_discovery(source_user_id: str, target_user_id: str):
    """Test path discovery endpoint"""
    print("\n" + "="*60)
    print("🗺️  Testing Path Discovery Endpoint")
    print("="*60)
    
    payload = {
        "founder_id": source_user_id,
        "investor_id": target_user_id,
        "max_paths": 5
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/paths/discover",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Path discovery complete")
            print_info(f"Paths found: {len(data.get('paths', []))}")
            if data.get('paths'):
                print_info(f"First path length: {len(data['paths'][0])}")
            return data
        else:
            print_error(f"Failed path discovery: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
    except Exception as e:
        print_error(f"Path discovery error: {e}")
        return None


def cleanup_test_data():
    """Clean up test data created during testing"""
    print("\n" + "="*60)
    print("🧹 CLEANING UP TEST DATA")
    print("="*60)
    
    try:
        connection = DriverRemoteConnection(
            'ws://100.70.53.90:8182/gremlin',
            'g',
            message_serializer=GraphBinarySerializersV1()
        )
        g = traversal().withRemote(connection)
        
        # Count test vertices before deletion
        test_user_count = g.V().hasLabel('User').has('name', 'Test User').count().next()
        test_user2_count = g.V().hasLabel('User').has('name', 'Test User 2').count().next()
        test_startup_count = g.V().hasLabel('Startup').has('name', 'Test Startup').count().next()
        
        total_test_vertices = int(test_user_count + test_user2_count + test_startup_count)
        
        if total_test_vertices == 0:
            print_info("No test data found to clean up")
            connection.close()
            return True
        
        print_info(f"Found {total_test_vertices} test vertices to delete")
        
        # Delete test users and startups (edges will be automatically deleted)
        g.V().hasLabel('User').has('name', 'Test User').drop().iterate()
        g.V().hasLabel('User').has('name', 'Test User 2').drop().iterate()
        g.V().hasLabel('Startup').has('name', 'Test Startup').drop().iterate()
        
        # Verify deletion
        remaining = g.V().or_(
            __.has('name', 'Test User'),
            __.has('name', 'Test User 2'),
            __.has('name', 'Test Startup')
        ).count().next()
        
        connection.close()
        
        if remaining == 0:
            print_success(f"Successfully deleted {total_test_vertices} test vertices")
            return True
        else:
            print_warning(f"Some test data may remain ({remaining} vertices)")
            return False
            
    except Exception as e:
        print_error(f"Cleanup error: {e}")
        return False


def run_all_tests():
    """Run all endpoint tests"""
    print("\n" + "="*60)
    print("🧪 GRAPH SERVICE API ENDPOINT TESTS")
    print("="*60)
    print(f"Testing API at: {BASE_URL}")
    
    results = {
        "passed": 0,
        "failed": 0,
        "total": 0
    }
    
    # Test 1: Health endpoint
    results["total"] += 1
    if test_health_endpoint():
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 2: Ready endpoint
    results["total"] += 1
    if test_ready_endpoint():
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 3: Create user
    results["total"] += 1
    user1 = test_create_user()
    if user1:
        results["passed"] += 1
    else:
        results["failed"] += 1
        print_error("Stopping tests - cannot create user")
        return results
    
    # Test 4: Get user by ID
    results["total"] += 1
    if test_get_user(user1["user_id"]):
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 5: Create another user for relationships
    results["total"] += 1
    user2_payload = {
        "name": "Test User 2",
        "role_primary": "investor",
        "domain_tags": ["test"],
        "geography": "Test City",
        "experience_years": 8,
        "verification_status": "verified"
    }
    response = requests.post(f"{API_BASE}/vertices/users", json=user2_payload, timeout=10)
    if response.status_code == 201:
        user2 = response.json()
        results["passed"] += 1
        print_success(f"Second user created: {user2['name']}")
    else:
        results["failed"] += 1
        user2 = None
    
    # Test 6: Create startup
    results["total"] += 1
    startup = test_create_startup()
    if startup:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 7: Create TRUSTS edge
    if user1 and user2:
        results["total"] += 1
        if test_create_trust_edge(user1["user_id"], user2["user_id"]):
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Test 8: Create FOUNDED edge
    if user1 and startup:
        results["total"] += 1
        if test_create_founded_edge(user1["user_id"], startup["startup_id"]):
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Test 9: Create INVESTED_IN edge
    if user2 and startup:
        results["total"] += 1
        if test_create_invested_edge(user2["user_id"], startup["startup_id"]):
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Test 10: Update trust score
    if user1 and user2:
        results["total"] += 1
        if test_update_trust_score(user1["user_id"], user2["user_id"]):
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Test 11: Path discovery
    if user1 and user2:
        results["total"] += 1
        if test_path_discovery(user1["user_id"], user2["user_id"]):
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Print summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Total tests: {results['total']}")
    print_success(f"Passed: {results['passed']}")
    if results['failed'] > 0:
        print_error(f"Failed: {results['failed']}")
    else:
        print_success("Failed: 0")
    
    success_rate = (results['passed'] / results['total'] * 100) if results['total'] > 0 else 0
    print(f"\nSuccess rate: {success_rate:.1f}%")
    
    if results['failed'] == 0:
        print_success("\n🎉 All tests passed!")
    else:
        print_warning(f"\n⚠️  {results['failed']} test(s) failed")
    
    # Clean up test data
    cleanup_test_data()
    
    return results


if __name__ == "__main__":
    run_all_tests()

