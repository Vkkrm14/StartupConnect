"""Test connections to all TrustGraph services"""

import asyncio
import httpx
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from pymongo import MongoClient
from elasticsearch import Elasticsearch
import redis

# Service URLs
JANUSGRAPH_URL = "ws://localhost:8182/gremlin"
MONGODB_URL = "mongodb://trustgraph:trustgraph_secure_2024@localhost:27017"
ELASTICSEARCH_URL = "http://localhost:9200"
REDIS_URL = "redis://localhost:6379"
API_GATEWAY_URL = "http://localhost:8000"
GRAPH_SERVICE_URL = "http://localhost:8001"
WORKFLOW_SERVICE_URL = "http://localhost:8002"
SEARCH_SERVICE_URL = "http://localhost:8003"

async def test_janusgraph():
    """Test JanusGraph connection"""
    try:
        remoteconn = DriverRemoteConnection(JANUSGRAPH_URL, 'g')
        g = traversal().withRemote(remoteconn)
        
        # Test query
        count = g.V().count().next()
        
        remoteconn.close()
        print(f"✅ JanusGraph: Connected ({count} vertices)")
        return True
    except Exception as e:
        print(f"❌ JanusGraph: {str(e)}")
        return False

async def test_mongodb():
    """Test MongoDB connection"""
    try:
        client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        
        # List databases
        databases = client.list_database_names()
        
        client.close()
        print(f"✅ MongoDB: Connected ({len(databases)} databases)")
        return True
    except Exception as e:
        print(f"❌ MongoDB: {str(e)}")
        return False

async def test_elasticsearch():
    """Test Elasticsearch connection"""
    try:
        es = Elasticsearch([ELASTICSEARCH_URL])
        
        # Test connection
        info = es.info()
        version = info['version']['number']
        
        es.close()
        print(f"✅ Elasticsearch: Connected (v{version})")
        return True
    except Exception as e:
        print(f"❌ Elasticsearch: {str(e)}")
        return False

async def test_redis():
    """Test Redis connection"""
    try:
        r = redis.from_url(REDIS_URL, socket_connect_timeout=5)
        
        # Test connection
        r.ping()
        
        r.close()
        print(f"✅ Redis: Connected")
        return True
    except Exception as e:
        print(f"❌ Redis: {str(e)}")
        return False

async def test_http_service(name: str, url: str):
    """Test HTTP service health endpoint"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{url}/health")
            
            if response.status_code == 200:
                print(f"✅ {name}: Healthy")
                return True
            else:
                print(f"⚠️  {name}: Unhealthy (HTTP {response.status_code})")
                return False
    except Exception as e:
        print(f"❌ {name}: {str(e)}")
        return False

async def main():
    """Run all connection tests"""
    print("🔍 Testing TrustGraph Services...\n")
    
    tasks = [
        ("Infrastructure", [
            ("JanusGraph", test_janusgraph()),
            ("MongoDB", test_mongodb()),
            ("Elasticsearch", test_elasticsearch()),
            ("Redis", test_redis()),
        ]),
        ("Backend Services", [
            ("API Gateway", test_http_service("API Gateway", API_GATEWAY_URL)),
            ("Graph Service", test_http_service("Graph Service", GRAPH_SERVICE_URL)),
            ("Workflow Service", test_http_service("Workflow Service", WORKFLOW_SERVICE_URL)),
            ("Search Service", test_http_service("Search Service", SEARCH_SERVICE_URL)),
        ]),
    ]
    
    all_healthy = True
    
    for category, tests in tasks:
        print(f"\n--- {category} ---")
        for name, test in tests:
            result = await test
            if not result:
                all_healthy = False
        print()
    
    print("\n" + "="*50)
    if all_healthy:
        print("✅ All services are healthy!")
    else:
        print("⚠️  Some services are not responding. Check Docker containers:")
        print("   docker-compose ps")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
