# JanusGraph Traversal Source Debugging Guide

## Problem: "The traversal source [g] for alias [g] is not configured on the server"

This error occurs when trying to use Python's `gremlinpython` to connect to JanusGraph 1.0.0.

---

## Root Cause Analysis

### What's Happening?
1. **JanusGraph Server starts successfully** and initializes the graph from `janusgraph.properties`
2. **The graph object exists** internally on the server
3. **BUT** the WebSocket server doesn't expose a traversal source alias `g` for remote clients
4. When your Python script tries to connect with `traversal().withRemote(remoteconn)`, it looks for  traversal source `g`
5. The server returns error 499: traversal source not configured

### Why Does This Happen?
- JanusGraph 1.0.0 uses `JanusGraphManager` which doesn't automatically create traversal source bindings like standard Gremlin Server
- The `graphs` section in YAML only defines graph instances, not traversal sources
- Groovy initialization scripts (`empty-sample.groovy`) run but don't properly expose globals to remote WebSocket clients

---

## Step-by-Step Debugging Process

### **Step 1: Verify JanusGraph Container is Healthy**
```powershell
docker compose ps janusgraph
```
**Expected:** `Up X minutes (healthy)`

If not healthy, check logs:
```powershell
docker compose logs janusgraph --tail 100
```

---

### **Step 2: Verify Graph is Accessible Locally**

Connect to Gremlin Console inside the container:
```powershell
docker exec -it trustgraph-janusgraph ./bin/gremlin.sh
```

Inside the Gremlin console:
```groovy
// Open the graph
graph = JanusGraphFactory.open('conf/janusgraph.properties')

// Create traversal source
g = graph.traversal()

// Test query
g.V().count()  // Should return 0 if database is empty

// Exit
:exit
```

**If this works**, the graph itself is fine - the issue is only with remote connections.

---

### **Step 3: Check Server Configuration Files**

#### A. Check gremlin-server.yaml
```powershell
docker exec trustgraph-janusgraph cat /etc/opt/janusgraph/gremlin-server.yaml
```

**Look for:**
- `graphManager: org.janusgraph.graphdb.management.JanusGraphManager`
- `graphs:` section defines your graph
- `scriptEngines:` section with ScriptFileGremlinPlugin loading `empty-sample.groovy`

#### B. Check janusgraph.properties
```powershell
docker exec trustgraph-janusgraph cat /opt/janusgraph/conf/janusgraph.properties
```

**Verify:**
- `storage.backend=cql` (for Cassandra)
- `storage.hostname=cassandra` (should match Docker service name)
- `index.search.backend=elasticsearch`

---

### **Step 4: Test WebSocket Connection**

Try a raw Gremlin query via WebSocket:
```powershell
cd backend\scripts
python -c "
from gremlin_python.driver import client
try:
    c = client.Client('ws://localhost:8182/gremlin', 'g')
    result = c.submit('1+1').all().result()
    print('✅ Connection works:', result)
except Exception as e:
    print('❌ Error:', e)
"
```

**Expected Error:** "traversal source [g] for alias [g] is not configured"

---

### **Step 5: Check Groovy Script Execution**

View server startup logs for script loading:
```powershell
docker logs trustgraph-janusgraph 2>&1 | Select-String -Pattern "ScriptFile|empty-sample|Evaluating"
```

**Problem:** Jan usGraph 1.0.0 loads the script but doesn't properly expose globals to remote clients.

---

## ✅ **SOLUTION OPTIONS**

### **Option 1: Use Graph Service API (Recommended)**

Instead of connecting directly to JanusGraph from Python, use the Graph Service API which handles graph operations.

**Advantages:**
- ✅ Works out of the box
- ✅ Provides REST API with proper authentication
- ✅ Includes business logic and validation
- ✅ Already configured and tested

**Usage:**
```powershell
# Test Graph Service health
Invoke-WebRequest http://localhost:8001/health

# Create a user vertex (example)
$body = @{
    user_id = "test-123"
    name = "Test User"
    email = "test@example.com"
    role_primary = "founder"
} | ConvertTo-Json

Invoke-WebRequest -Uri http://localhost:8001/api/vertices/users `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

**Skip seed_data.py** - The Graph Service API will create vertices/edges when users interact with the Flutter app.

---

### **Option 2: Use Session-Based Connection (Advanced)**

Modify your Python scripts to use session-based connections instead of traversal source bindings:

```python
from gremlin_python.driver import client as gremlin_client

# Create client with session
client = gremlin_client.Client(
    'ws://localhost:8182/gremlin',
    'g',  # Still uses 'g' but in session mode
    session=str(uuid.uuid4())  # Create unique session
)

# Submit raw Gremlin queries as strings
query = """
g.addV('User')
 .property('user_id', user_id)
 .property('name', name)
 .iterate()
"""

client.submit(query, {'user_id': 'abc123', 'name': 'John Doe'}).all().result()
client.close()
```

**Note:** This bypasses the traversal source issue by using string-based queries in a session.

---

### **Option 3: Use Official JanusGraph Docker Image with Pre-configured Server (Complex)**

Switch to a different JanusGraph setup that properly configures traversal sources. This requires:
1. Custom Dockerfile extending janusgraph/janusgraph
2. Custom server initialization scripts
3. Rebuilding the  Docker image

**Not recommended** for this project due to complexity.

---

## 🎯 **Recommended Approach for Your Project**

### **FOR DEVELOPMENT & TESTING:**

**Skip `seed_data.py` for now** and use one of these alternatives:

#### **Option A: Use Gremlin Console for Manual Seeding**
```powershell
# Enter Gremlin console
docker exec -it trustgraph-janusgraph ./bin/gremlin.sh
```

```groovy
// Inside Gremlin console
graph = JanusGraphFactory.open('conf/janusgraph.properties')
g = graph.traversal()

// Create a founder
g.addV('User')
 .property('user_id', UUID.randomUUID().toString())
 .property('name', 'Alice Johnson')
 .property('email', 'alice@startup.com')
 .property('role_primary', 'founder')
 .property('geography', 'San Francisco')
 .iterate()

// Verify
g.V().hasLabel('User').valueMap().toList()

// Commit and close
graph.tx().commit()
:exit
```

#### **Option B: Use Graph Service API**
The Graph Service is already running at `http://localhost:8001` and provides endpoints to create users, startups, and relationships. Use the Swagger docs at `http://localhost:8000/docs` to interact with it.

#### **Option C: Use the Flutter App**
Register users through the Flutter app - the Graph Service will automatically create vertices and edges in JanusGraph.

---

### **FOR PRODUCTION:**

Fix the traversal source configuration by:
1. Using a custom initialization script that properly registers traversal sources
2. OR switching to a different JanusGraph server configuration
3. OR using the Graph Service API as the primary interface (recommended)

---

## 📊 **Testing the Solution**

### **1. Verify Graph Service Works**
```powershell
# Health check
curl http://localhost:8001/health

# Create test vertex via REST API
curl -X POST http://localhost:8001/api/vertices/users `
  -H "Content-Type: application/json" `
  -d '{
    "user_id": "test-user-1",
    "name": "Test User",
    "email": "test@example.com",
    "role_primary": "founder"
  }'
```

### **2. Verify Data in JanusGraph**
```powershell
docker exec -it trustgraph-janusgraph ./bin/gremlin.sh
```

```groovy
graph = JanusGraphFactory.open('conf/janusgraph.properties')
g = graph.traversal()
g.V().hasLabel('User').count()  // Should be > 0
g.V().hasLabel('User').valueMap().toList()
```

---

## 🔍 **Common Issues & Fixes**

### **Issue: Container keeps restarting**
```powershell
docker logs trustgraph-janusgraph --tail 50
```
**Look for:** YAML syntax errors, missing configuration files

### **Issue: Cassandra connection fails**
Wait 2-3 minutes for Cassandra to fully start:
```powershell
docker compose logs cassandra | Select-String "Starting listening for CQL clients"
```

### **Issue: Elasticsearch connection fails**
```powershell
docker compose logs elasticsearch
```
If you see `vm.max_map_count` error:
```powershell
wsl -d docker-desktop -u root sysctl -w vm.max_map_count=262144
docker compose restart janusgraph
```

---

## 📚 **Additional Resources**

- **JanusGraph Docs:** https://docs.janusgraph.org/
- **Gremlin Python Docs:** https://tinkerpop.apache.org/docs/current/reference/#gremlin-python
- **TrustGraph API Docs:** http://localhost:8000/docs

---

## 📝 **Summary**

**The Problem:** JanusGraph 1.0.0 doesn't expose traversal source alias 'g' for remote connections by default

**The Solution:** 
1. **Short-term:** Use Graph Service API or Gremlin Console for data seeding
2. **Long-term:** Continue using Graph Service API as the primary interface (this is the designed architecture)

**Why Graph Service API is Better:**
- ✅ Handles authentication & authorization
- ✅ Validates input data
- ✅ Publishes events to Kafka
- ✅ Implements business logic
- ✅ Direct JanusGraph access bypasses all of this

**Bottom Line:** The `seed_data.py` approach was for quick development testing, but the Graph Service API is the proper way to interact with the graph database in this architecture.
