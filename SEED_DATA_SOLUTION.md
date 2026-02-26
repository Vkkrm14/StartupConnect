# Seed Data Solution - Using Gremlin Console

## Problem Summary

After extensive debugging, we discovered that **JanusGraph 1.0.0 with JanusGraphManager doesn't properly expose the traversal source `g` for remote WebSocket connections** (used by Python's gremlinpython and the Graph Service).

This affects:
- ❌ Direct Python scripts using `gremlinpython`  
- ❌ Graph Service API (which uses `gremlinpython` internally)
- ✅ **Gremlin Console works fine** (local JVM connection)

---

## ✅ WORKING SOLUTION: Use Gremlin Console

### Step 1: Enter Gremlin Console
```powershell
docker exec -it trustgraph-janusgraph ./bin/gremlin.sh
```

### Step 2: Connect to Graph Server
```groovy
// Connect to the running JanusGraph server
:remote connect tinkerpop.server conf/remote.yaml

// Set console to send all commands to the server
:remote console

// Now 'g' is automatically available from the server
// Test the connection
g.V().count()
```

**Note:** The `graph` and `g` variables are already configured on the server, so you don't need to create them.

### Step 3: Create Sample Data

```groovy
// Create Founders
alice_id = UUID.randomUUID().toString()
g.addV('User')
 .property('user_id', alice_id)
 .property('name', 'Alice Johnson')
 .property('role_primary', 'founder')
 .property('geography', 'San Francisco')
 .property('reputation_score', 0.85)
 .property('verification_status', 'verified')
 .property('experience_years', 10)
 .property('domain_tags', 'fintech')
 .property('domain_tags', 'saas')
 .property('created_at', System.currentTimeMillis() / 1000 as long)
 .iterate()

bob_id = UUID.randomUUID().toString()
g.addV('User')
 .property('user_id', bob_id)
 .property('name', 'Bob Smith')
 .property('role_primary', 'founder')
 .property('geography', 'New York')
 .property('reputation_score', 0.80)
 .property('verification_status', 'verified')
 .property('experience_years', 8)
 .property('domain_tags', 'healthtech')
 .property('domain_tags', 'ai-ml')
 .property('created_at', System.currentTimeMillis() / 1000 as long)
 .iterate()

// Create Investor
frank_id = UUID.randomUUID().toString()
g.addV('User')
 .property('user_id', frank_id)
 .property('name', 'Frank Miller')
 .property('role_primary', 'investor')
 .property('geography', 'Palo Alto')
 .property('reputation_score', 0.90)
 .property('verification_status', 'verified')
 .property('experience_years', 15)
 .property('domain_tags', 'fintech')
 .property('domain_tags', 'saas')
 .property('created_at', System.currentTimeMillis() / 1000 as long)
 .iterate()

// Create Connector
ivy_id = UUID.randomUUID().toString()
g.addV('User')
 .property('user_id', ivy_id)
 .property('name', 'Ivy Martinez')
 .property('role_primary', 'connector')
 .property('geography', 'San Francisco')
 .property('reputation_score', 0.95)
 .property('verification_status', 'verified')
 .property('experience_years', 12)
 .property('domain_tags', 'fintech')
 .property('domain_tags', 'saas')
 .property('created_at', System.currentTimeMillis() / 1000 as long)
 .iterate()

// Create Startups
finflow_id = UUID.randomUUID().toString()
g.addV('Startup')
 .property('startup_id', finflow_id)
 .property('name', 'FinFlow')
 .property('domain', 'fintech')
 .property('stage', 'seed')
 .property('geography', 'San Francisco')
 .property('visibility_level', 'public')
 .property('created_at', System.currentTimeMillis() / 1000 as long)
 .iterate()

healthai_id = UUID.randomUUID().toString()
g.addV('Startup')
 .property('startup_id', healthai_id)
 .property('name', 'HealthAI')
 .property('domain', 'healthtech')
 .property('stage', 'seriesA')
 .property('geography', 'Boston')
 .property('visibility_level', 'public')
 .property('created_at', System.currentTimeMillis() / 1000 as long)
 .iterate()

// Create TRUSTS edges
g.V().has('User', 'user_id', alice_id).next()
alice_v = g.V().has('User', 'user_id', alice_id).next()
ivy_v = g.V().has('User', 'user_id', ivy_id).next()

g.V(alice_v).addE('TRUSTS').to(ivy_v)
 .property('edge_id', UUID.randomUUID().toString())
 .property('trust_score', 0.85)
 .property('strength_score', 0.80)
 .property('recency_score', 1.0)
 .property('interaction_count', 15)
 .property('endorsement_count', 3)
 .property('successful_intros', 0)
 .property('domain_tags', 'fintech')
 .property('created_at', System.currentTimeMillis() / 1000 as long)
 .iterate()

// Create more TRUSTS edges
ivy_v = g.V().has('User', 'user_id', ivy_id).next()
frank_v = g.V().has('User', 'user_id', frank_id).next()

g.V(ivy_v).addE('TRUSTS').to(frank_v)
 .property('edge_id', UUID.randomUUID().toString())
 .property('trust_score', 0.90)
 .property('strength_score', 0.85)
 .property('recency_score', 1.0)
 .property('interaction_count', 20)
 .property('endorsement_count', 5)
 .property('successful_intros', 2)
 .property('domain_tags', 'fintech')
 .property('created_at', System.currentTimeMillis() / 1000 as long)
 .iterate()

// Create FOUNDED edge
alice_v = g.V().has('User', 'user_id', alice_id).next()
finflow_v = g.V().has('Startup', 'startup_id', finflow_id).next()

g.V(alice_v).addE('FOUNDED').to(finflow_v)
 .property('edge_id', UUID.randomUUID().toString())
 .property('role', 'founder')
 .property('active', true)
 .property('created_at', System.currentTimeMillis() / 1000 as long)
 .iterate()

bob_v = g.V().has('User', 'user_id', bob_id).next()
healthai_v = g.V().has('Startup', 'startup_id', healthai_id).next()

g.V(bob_v).addE('FOUNDED').to(healthai_v)
 .property('edge_id', UUID.randomUUID().toString())
 .property('role', 'founder')
 .property('active', true)
 .property('created_at', System.currentTimeMillis() / 1000 as long)
 .iterate()

// Create INVESTED_IN edge
frank_v = g.V().has('User', 'user_id', frank_id).next()
finflow_v = g.V().has('Startup', 'startup_id', finflow_id).next()

g.V(frank_v).addE('INVESTED_IN').to(finflow_v)
 .property('edge_id', UUID.randomUUID().toString())
 .property('round', 'seed')
 .property('amount_range', '100K-500K')
 .property('year', 2024)
 .property('visibility', 'trusted_only')
 .property('created_at', System.currentTimeMillis() / 1000 as long)
 .iterate()

// Verify data
println "Users: " + g.V().hasLabel('User').count().next()
println "Startups: " + g.V().hasLabel('Startup').count().next()
println "TRUSTS edges: " + g.E().hasLabel('TRUSTS').count().next()
println "FOUNDED edges: " + g.E().hasLabel('FOUNDED').count().next()
println "INVESTED_IN edges: " + g.E().hasLabel('INVESTED_IN').count().next()

// List all users
g.V().hasLabel('User').valueMap('name', 'role_primary').toList()
```

### Step 4: Exit Console
```groovy
:exit
```

---

## 📋 Quick Copy-Paste Script

```groovy
// Connect to JanusGraph server
:remote connect tinkerpop.server conf/remote.yaml
:remote console

// Verify connection
g.V().count()

// Create sample data
alice_id = UUID.randomUUID().toString()
g.addV('User').property('user_id', alice_id).property('name', 'Alice Johnson').property('role_primary', 'founder').property('geography', 'San Francisco').property('reputation_score', 0.85).property('verification_status', 'verified').property('experience_years', 10).property('domain_tags', 'fintech').property('domain_tags', 'saas').property('created_at', System.currentTimeMillis() / 1000 as long).iterate()

bob_id = UUID.randomUUID().toString()
g.addV('User').property('user_id', bob_id).property('name', 'Bob Smith').property('role_primary', 'founder').property('geography', 'New York').property('reputation_score', 0.80).property('verification_status', 'verified').property('experience_years', 8).property('domain_tags', 'healthtech').property('domain_tags', 'ai-ml').property('created_at', System.currentTimeMillis() / 1000 as long).iterate()

frank_id = UUID.randomUUID().toString()
g.addV('User').property('user_id', frank_id).property('name', 'Frank Miller').property('role_primary', 'investor').property('geography', 'Palo Alto').property('reputation_score', 0.90).property('verification_status', 'verified').property('experience_years', 15).property('domain_tags', 'fintech').property('created_at', System.currentTimeMillis() / 1000 as long).iterate()

ivy_id = UUID.randomUUID().toString()
g.addV('User').property('user_id', ivy_id).property('name', 'Ivy Martinez').property('role_primary', 'connector').property('geography', 'San Francisco').property('reputation_score', 0.95).property('verification_status', 'verified').property('experience_years', 12).property('domain_tags', 'fintech').property('created_at', System.currentTimeMillis() / 1000 as long).iterate()

finflow_id = UUID.randomUUID().toString()
g.addV('Startup').property('startup_id', finflow_id).property('name', 'FinFlow').property('domain', 'fintech').property('stage', 'seed').property('geography', 'San Francisco').property('visibility_level', 'public').property('created_at', System.currentTimeMillis() / 1000 as long).iterate()

healthai_id = UUID.randomUUID().toString()
g.addV('Startup').property('startup_id', healthai_id).property('name', 'HealthAI').property('domain', 'healthtech').property('stage', 'seriesA').property('geography', 'Boston').property('visibility_level', 'public').property('created_at', System.currentTimeMillis() / 1000 as long).iterate()

alice_v = g.V().has('User', 'user_id', alice_id).next()
ivy_v = g.V().has('User', 'user_id', ivy_id).next()
g.V(alice_v).addE('TRUSTS').to(ivy_v).property('edge_id', UUID.randomUUID().toString()).property('trust_score', 0.85).property('strength_score', 0.80).property('recency_score', 1.0).property('interaction_count', 15).property('created_at', System.currentTimeMillis() / 1000 as long).iterate()

ivy_v = g.V().has('User', 'user_id', ivy_id).next()
frank_v = g.V().has('User', 'user_id', frank_id).next()
g.V(ivy_v).addE('TRUSTS').to(frank_v).property('edge_id', UUID.randomUUID().toString()).property('trust_score', 0.90).property('strength_score', 0.85).property('recency_score', 1.0).property('interaction_count', 20).property('created_at', System.currentTimeMillis() / 1000 as long).iterate()

alice_v = g.V().has('User', 'user_id', alice_id).next()
finflow_v = g.V().has('Startup', 'startup_id', finflow_id).next()
g.V(alice_v).addE('FOUNDED').to(finflow_v).property('edge_id', UUID.randomUUID().toString()).property('role', 'founder').property('active', true).property('created_at', System.currentTimeMillis() / 1000 as long).iterate()

bob_v = g.V().has('User', 'user_id', bob_id).next()
healthai_v = g.V().has('Startup', 'startup_id', healthai_id).next()
g.V(bob_v).addE('FOUNDED').to(healthai_v).property('edge_id', UUID.randomUUID().toString()).property('role', 'founder').property('active', true).property('created_at', System.currentTimeMillis() / 1000 as long).iterate()

frank_v = g.V().has('User', 'user_id', frank_id).next()
finflow_v = g.V().has('Startup', 'startup_id', finflow_id).next()
g.V(frank_v).addE('INVESTED_IN').to(finflow_v).property('edge_id', UUID.randomUUID().toString()).property('round', 'seed').property('amount_range', '100K-500K').property('year', 2024).property('visibility', 'trusted_only').property('created_at', System.currentTimeMillis() / 1000 as long).iterate()

// Verify seeded data
println "✅ Data seeded successfully!"
println "Users: " + g.V().hasLabel('User').count().next()
println "Startups: " + g.V().hasLabel('Startup').count().next()
println "TRUSTS edges: " + g.E().hasLabel('TRUSTS').count().next()
println "FOUNDED edges: " + g.E().hasLabel('FOUNDED').count().next()
```

---

## 🔍 Verify Seeded Data

```groovy
// Count vertices
g.V().hasLabel('User').count()
g.V().hasLabel('Startup').count()

// Count edges
g.E().hasLabel('TRUSTS').count()
g.E().hasLabel('FOUNDED').count()
g.E().hasLabel('INVESTED_IN').count()

// List all users
g.V().hasLabel('User').valueMap('name', 'role_primary', 'geography').toList()

// List all startups
g.V().hasLabel('Startup').valueMap('name', 'domain', 'stage').toList()

// View trust network
g.E().hasLabel('TRUSTS').valueMap('trust_score').toList()
```

---

## 💡 Why This Works

- ✅ **Remote Console Connection** - Connects to the running JanusGraph server via `:remote connect`
- ✅ Uses the server's pre-configured `g` traversal source 
- ✅ No WebSocket client issues - uses native Gremlin Server protocol
- ✅ Automatic transaction management by the server
- ✅ Full Groovy scripting capabilities

---

## 🎯 Alternative: Use Flutter App

Once the Graph Service WebSocket issue is resolved (or after a JanusGraph update), you can:
1. Register users through the Flutter app
2. The API Gateway will forward requests to Graph Service
3. Graph Service will create vertices/edges in JanusGraph

This will work once we upgrade to a newer JanusGraph version or implement a different connection strategy.

---

## 📚 Technical Notes

**Root Cause:**
- JanusGraph 1.0.0 with `JanusGraphManager` doesn't properly expose Groovy script globals to WebSocket remote connections
- The traversal source `g` defined in `empty-sample.groovy` isn't accessible via `DriverRemoteConnection`
- This is a known limitation/configuration issue with this specific JanusGraph version

**Why seed_data.py doesn't work:**
- Uses `gremlinpython` → `DriverRemoteConnection` → WebSocket → Requires traversal source binding
- Graph Service has the same issue - it also uses `gremlinpython`

**Future Solutions:**
1. Upgrade to JanusGraph 1.1.0+ (when available)
2. Use a different JanusGraph server configuration
3. Implement a custom Gremlin Server setup
4. Use native JanusGraph Java API instead of Gremlin bindings

---

## 🔧 Troubleshooting

### Error: "Gremlin Server must be configured to use the JanusGraphManager"

This error occurs when you try to open the graph directly with `JanusGraphFactory.open()` in the console.

**Solution:** Use the `:remote connect` approach instead (documented above). The server manages the graph instance, so you connect to it rather than creating a new one.

### Error: "Could not connect to server"

**Check if JanusGraph is running:**
```powershell
docker compose ps janusgraph
```

**Check JanusGraph logs:**
```powershell
docker compose logs janusgraph --tail 20
```

Look for: `Channel started at port 8182`

### Verify Connection in Console

After connecting with `:remote console`, test with:
```groovy
g.V().count()  // Should return a number (0 if empty)
```

If you get a response, you're connected successfully!

---

## ✅ Summary

**For now, use Gremlin Console for seeding data.** 

It works perfectly and is actually more flexible for testing and development!
