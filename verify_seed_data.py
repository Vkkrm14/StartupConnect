#!/usr/bin/env python3
"""Verify seeded data in JanusGraph"""

from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.driver.serializer import GraphBinarySerializersV1

def verify_data():
    """Connect to JanusGraph and verify data counts"""
    print("🔍 Connecting to JanusGraph...")
    
    connection = DriverRemoteConnection(
        'ws://localhost:8182/gremlin',
        'g',
        message_serializer=GraphBinarySerializersV1()
    )
    g = traversal().withRemote(connection)
    
    try:
        print("\n===== VERTEX COUNTS =====")
        total_vertices = g.V().count().next()
        user_count = g.V().hasLabel('User').count().next()
        startup_count = g.V().hasLabel('Startup').count().next()
        
        print(f"Total vertices: {total_vertices}")
        print(f"  - Users: {user_count}")
        print(f"  - Startups: {startup_count}")
        
        print("\n===== EDGE COUNTS =====")
        total_edges = g.E().count().next()
        trusts_count = g.E().hasLabel('TRUSTS').count().next()
        founded_count = g.E().hasLabel('FOUNDED').count().next()
        invested_count = g.E().hasLabel('INVESTED_IN').count().next()
        
        print(f"Total edges: {total_edges}")
        print(f"  - TRUSTS: {trusts_count}")
        print(f"  - FOUNDED: {founded_count}")
        print(f"  - INVESTED_IN: {invested_count}")
        
        print("\n===== SAMPLE DATA =====")
        users = g.V().hasLabel('User').limit(3).valueMap('name', 'role').toList()
        print("Sample users:")
        for user in users:
            name = user.get('name', ['Unknown'])[0]
            role = user.get('role', ['Unknown'])[0]
            print(f"  - {name} ({role})")
        
        startups = g.V().hasLabel('Startup').limit(2).valueMap('name', 'industry').toList()
        print("\nSample startups:")
        for startup in startups:
            name = startup.get('name', ['Unknown'])[0]
            industry = startup.get('industry', ['Unknown'])[0]
            print(f"  - {name} ({industry})")
        
        print("\n✅ Data verification complete!")
        
        # Validation
        expected = {
            'vertices': 14,
            'users': 10,
            'startups': 4,
            'edges': 17,
            'trusts': 10,
            'founded': 4,
            'invested': 3
        }
        
        actual = {
            'vertices': total_vertices,
            'users': user_count,
            'startups': startup_count,
            'edges': total_edges,
            'trusts': trusts_count,
            'founded': founded_count,
            'invested': invested_count
        }
        
        if all(actual[k] == expected[k] for k in expected):
            print("✅ All counts match expected values!")
        else:
            print("\n⚠️ Count mismatch:")
            for k in expected:
                if actual[k] != expected[k]:
                    print(f"  {k}: expected {expected[k]}, got {actual[k]}")
                    
    finally:
        connection.close()
        print("\n🔌 Connection closed")

if __name__ == "__main__":
    verify_data()
