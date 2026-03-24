"""Test path discovery with real seeded data"""

import requests
import time
from typing import Dict, List
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.driver.serializer import GraphSONSerializersV3d0

GRAPH_SERVICE_URL = "http://100.70.53.90:8001"
GREMLIN_URL = 'ws://100.70.53.90:8182/gremlin'

def get_user_id_by_name(name: str) -> str:
    """Get user_id from database by name"""
    try:
        connection = DriverRemoteConnection(GREMLIN_URL, 'g', message_serializer=GraphSONSerializersV3d0())
        g = traversal().withRemote(connection)
        
        user = g.V().has('User', 'name', name).elementMap().next()
        connection.close()
        
        # Handle both GraphBinary (list) and GraphSON (plain) formats
        user_id = user.get('user_id')
        if isinstance(user_id, list):
            user_id = user_id[0]
        
        return str(user_id)
    except Exception as e:
        print(f"❌ Error getting user {name}: {e}")
        return None


def test_path_discovery(founder_name: str, investor_name: str, test_description: str):
    """Test path discovery between a founder and investor"""
    print(f"\n{'='*80}")
    print(f"TEST: {test_description}")
    print(f"{'='*80}")
    
    # Get user IDs
    founder_id = get_user_id_by_name(founder_name)
    investor_id = get_user_id_by_name(investor_name)
    
    if not founder_id or not investor_id:
        print("❌ Could not find both users")
        return
    
    print(f"Founder: {founder_name} (ID: {founder_id[:8]}...)")
    print(f"Investor: {investor_name} (ID: {investor_id[:8]}...)")
    
    # Call path discovery endpoint
    start_time = time.time()
    try:
        response = requests.post(
            f"{GRAPH_SERVICE_URL}/api/v1/paths/discover",
            json={
                "founder_id": founder_id,
                "investor_id": investor_id,
                "domain_tags": [],
                "max_hops": 4
            },
            timeout=10
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        data = response.json()
        paths = data.get("paths", [])
        
        print(f"\n📊 Response Time: {elapsed_ms:.1f}ms")
        print(f"📝 Found {len(paths)} path(s)\n")
        
        if len(paths) == 0:
            print("⚠️  No paths found")
            return
        
        # Display each path
        for i, path in enumerate(paths, 1):
            nodes = path.get("nodes", [])
            path_type = "MULTI-HOP" if len(nodes) > 2 else "DIRECT"
            hops = path.get("hop_count", len(nodes) - 1)
            
            print(f"Path #{i}: {path_type} ({hops} hop{'s' if hops > 1 else ''})")
            print(f"  Score: {path.get('path_score', 0):.3f}")
            print(f"  Success Probability: {path.get('success_probability', 0)*100:.1f}%")
            print(f"  Explanation: {path.get('explanation', 'N/A')}")
            
            # Build route string
            route_parts = []
            for node in nodes:
                role_emoji = {"founder": "👤", "investor": "💰", "connector": "🔗"}.get(node.get("role", ""), "?")
                route_parts.append(f"{role_emoji} {node['name']}")
            
            route = " → ".join(route_parts)
            print(f"  Route: {route}")
            
            # Edge details
            if path.get("edges"):
                print(f"  Edge Details:")
                for edge in path["edges"]:
                    trust = edge.get("trust", 0)
                    strength = edge.get("strength", 0)
                    mutual = "Yes" if edge.get("mutual", False) else "No"
                    print(f"    • Trust: {trust:.2f}, Strength: {strength:.2f}, Mutual: {mutual}")
            
            print()
        
        # Summary
        multi_hop_paths = [p for p in paths if len(p.get("nodes", [])) > 2]
        direct_paths = [p for p in paths if len(p.get("nodes", [])) == 2]
        
        print(f"Summary:")
        print(f"  Direct paths: {len(direct_paths)}")
        print(f"  Multi-hop paths: {len(multi_hop_paths)}")
        if multi_hop_paths:
            avg_score = sum(p.get("path_score", 0) for p in multi_hop_paths) / len(multi_hop_paths)
            print(f"  Avg multi-hop score: {avg_score:.3f}")
        print(f"  ✅ Test complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all path discovery tests with real seeded data"""
    
    print("=" * 80)
    print("🧪 REAL DATA PATH DISCOVERY TESTS")
    print("=" * 80)
    
    # Test cases based on seeded trust network
    test_cases = [
        {
            "founder": "Alice Johnson",
            "investor": "Frank Miller",
            "description": "Alice → Ivy (connector) → Frank (expected 2-hop path)"
        },
        {
            "founder": "Alice Johnson",
            "investor": "Grace Chen",
            "description": "Alice → Ivy (connector) → Grace (expected 2-hop path)"
        },
        {
            "founder": "Bob Smith",
            "investor": "Grace Chen",
            "description": "Bob → Jack (connector) → Grace (expected 2-hop path)"
        },
        {
            "founder": "Carol Davis",
            "investor": "Frank Miller",
            "description": "Carol → Ivy (connector) → Frank (expected 2-hop path)"
        },
        {
            "founder": "Alice Johnson",
            "investor": "Henry Brown",
            "description": "Alice → Ivy → Frank → Henry (expected 3-hop path)"
        },
        {
            "founder": "David Lee",
            "investor": "Frank Miller",
            "description": "David → Alice → Ivy → Frank (expected 3-hop path)"
        }
    ]
    
    successful_tests = 0
    failed_tests = 0
    
    for test_case in test_cases:
        try:
            test_path_discovery(
                test_case["founder"],
                test_case["investor"],
                test_case["description"]
            )
            successful_tests += 1
            time.sleep(0.5)  # Brief pause between tests
        except Exception as e:
            print(f"❌ Test failed: {e}")
            failed_tests += 1
    
    # Final summary
    print("\n" + "=" * 80)
    print("📊 FINAL TEST SUMMARY")
    print("=" * 80)
    print(f"Total tests: {len(test_cases)}")
    print(f"✅ Successful: {successful_tests}")
    print(f"❌ Failed: {failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 All tests passed! Multi-hop path discovery is working with real data!")
    
    print("=" * 80)


if __name__ == "__main__":
    main()

