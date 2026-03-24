#!/usr/bin/env python3
"""Clear all data from JanusGraph"""

from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.driver.serializer import GraphBinarySerializersV1

def clear_all_data():
    """Connect to JanusGraph and delete all vertices and edges"""
    print("🔍 Connecting to JanusGraph...")
    
    connection = DriverRemoteConnection(
        'ws://100.70.53.90:8182/gremlin',
        'g',
        message_serializer=GraphBinarySerializersV1()
    )
    g = traversal().withRemote(connection)
    
    try:
        # Get counts before deletion
        vertex_count = g.V().count().next()
        edge_count = g.E().count().next()
        
        print(f"\n📊 Current data:")
        print(f"  - Vertices: {vertex_count}")
        print(f"  - Edges: {edge_count}")
        
        if vertex_count == 0 and edge_count == 0:
            print("\n✅ Database is already empty!")
            return
        
        print("\n🗑️ Deleting all data...")
        
        # Delete all vertices (this also deletes connected edges)
        g.V().drop().iterate()
        
        # Verify deletion
        remaining_vertices = g.V().count().next()
        remaining_edges = g.E().count().next()
        
        print(f"\n✅ Data cleared!")
        print(f"  - Remaining vertices: {remaining_vertices}")
        print(f"  - Remaining edges: {remaining_edges}")
        
        if remaining_vertices == 0 and remaining_edges == 0:
            print("\n🎉 Database is now completely empty and ready for fresh seeding!")
        else:
            print("\n⚠️ Warning: Some data may still remain")
                    
    except Exception as e:
        print(f"\n❌ Error clearing data: {e}")
        raise
    finally:
        connection.close()
        print("\n🔌 Connection closed")

if __name__ == "__main__":
    import sys
    
    print("⚠️  WARNING: This will delete ALL data from JanusGraph!")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() == 'yes':
        clear_all_data()
    else:
        print("❌ Operation cancelled")
        sys.exit(0)

