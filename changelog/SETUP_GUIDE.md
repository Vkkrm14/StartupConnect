# TrustGraph - Complete Setup Guide (From Scratch)

This guide will walk you through setting up and running TrustGraph with **no prior environment setup**.

---

## 📋 **Prerequisites to Install**

### **1. Docker Desktop**
**Required for:** Running backend services (databases, APIs)

**Windows Installation:**
1. Download Docker Desktop: https://www.docker.com/products/docker-desktop/
2. Install and restart your computer
3. Open Docker Desktop and wait for it to start
4. Verify installation:
   ```powershell
   docker --version
   docker-compose --version
   ```

### **2. Python 3.11+**
**Required for:** Running Kafka consumers and seed scripts

**Windows Installation:**
1. Download Python 3.11: https://www.python.org/downloads/
2. During installation, **CHECK** "Add Python to PATH"
3. Verify installation:
   ```powershell
   python --version
   pip --version
   ```

### **3. Flutter SDK**
**Required for:** Running the mobile app

**Windows Installation:**
1. Download Flutter: https://docs.flutter.dev/get-started/install/windows
2. Extract to `C:\src\flutter`
3. Add `C:\src\flutter\bin` to your PATH:
   - Search "Environment Variables" in Windows
   - Edit PATH → Add `C:\src\flutter\bin`
4. Verify installation:
   ```powershell
   flutter doctor
   ```
5. Install VS Code + Flutter extension (recommended)

### **4. Git**
**Required for:** Cloning repository (if needed)

Download: https://git-scm.com/download/win

---

## 🚀 **Setup Steps**

### **Step 1: Navigate to Project**
```powershell
cd e:\Sem-6\NoSQL\startupConnect_draft
```

### **Step 2: Create Environment Configuration**

Create `.env` file in project root:

```powershell
# Create .env file
New-Item -Path .env -ItemType File -Force

# Add configuration (copy-paste this entire block)
@"
# JanusGraph
JANUSGRAPH_HOST=localhost
JANUSGRAPH_PORT=8182

# Cassandra
CASSANDRA_HOST=localhost
CASSANDRA_PORT=9042

# MongoDB
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_USER=trustgraph
MONGO_PASSWORD=trustgraph_secure_2024
MONGO_DB=trustgraph

# Elasticsearch
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Kafka/Redpanda
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Services
GRAPH_SERVICE_URL=http://localhost:8001
WORKFLOW_SERVICE_URL=http://localhost:8002
SEARCH_SERVICE_URL=http://localhost:8003

# JWT
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000,http://localhost:8001

# Email (Development - logs to console)
EMAIL_ENABLED=false
EMAIL_FROM=noreply@trustgraph.com
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# Push Notifications (Not implemented yet)
PUSH_ENABLED=false
"@ | Out-File -FilePath .env -Encoding utf8
```

### **Step 3: Start Backend Infrastructure**

```powershell
# Start all services
docker compose up -d

# This starts:
# - Cassandra (database for JanusGraph)
# - Elasticsearch (search engine)
# - MongoDB (document storage)
# - Redis (caching)
# - Redpanda (Kafka alternative - easier setup)
# - JanusGraph (graph database)
# - Graph Service (API)
# - API Gateway (main API)
# - Workflow Service (intro workflow)
# - Search Service (search API)
```

**Windows / Docker Desktop note (Elasticsearch):**

If you see an error like:

`sysctl "vm.max_map_count" is not in a separate kernel namespace`

Set the value in Docker Desktop’s WSL2 VM (this is where the Docker engine runs) and start again:

```powershell
wsl -d docker-desktop -u root sysctl -w vm.max_map_count=262144
docker compose up -d
```

**Wait 2-3 minutes** for all services to start and become healthy.

### **Step 4: Check Service Status**

```powershell
# Check if all containers are running
docker compose ps

# You should see:
# - cassandra (healthy)
# - elasticsearch (healthy)
# - mongodb (healthy)
# - redis (healthy)
# - redpanda (healthy)
# - janusgraph (healthy)
# - graph-service (healthy)
# - api-gateway (healthy)
# - workflow-service (healthy)
# - search-service (healthy)
```

**If any service is not healthy:**
```powershell
# View logs for specific service
docker compose logs -f <service-name>

# Example: Check JanusGraph logs
docker compose logs -f janusgraph
```

### **Step 5: Install Python Dependencies**

```powershell
# Install dependencies for running seed script and test scripts
pip install gremlinpython==3.7.1 requests
```

### **Step 6: Seed Sample Data**

The seed script creates a sample trust network with users, startups, and relationships.

```powershell
# Seed the database (auto-clears existing data)
python backend\scripts\seed_data.py --clear
```

**What gets created:**
- 10 Users (5 founders, 3 investors, 2 connectors)
- 4 Startups (FinFlow, HealthAI, EduTech Pro, BlockChain Solutions)
- 10 TRUSTS edges (trust relationships)
- 4 FOUNDED edges (founder-startup relationships)
- 3 INVESTED_IN edges (investor-startup relationships)

**Verify the seeded data:**
```powershell
python verify_seed_data.py
```

You should see:
```
===== VERTEX COUNTS =====
Total vertices: 14
  - Users: 10
  - Startups: 4

===== EDGE COUNTS =====
Total edges: 17
  - TRUSTS: 10
  - FOUNDED: 4
  - INVESTED_IN: 3

✅ All counts match expected values!
```

**Seed script options:**
- `--clear` - Automatically clear database before seeding (recommended)
- `--force` - Skip all confirmations

**Troubleshooting:**
If seeding fails, ensure JanusGraph is fully started (wait 60-90 seconds after `docker compose up`):
```powershell
# Check JanusGraph logs for "Channel started at port 8182"
docker compose logs janusgraph | Select-String "Channel started"
```

### **Step 7: Test Backend APIs**

```powershell
# Test API Gateway health
Invoke-WebRequest -Uri http://localhost:8000/health

# Test Graph Service
Invoke-WebRequest -Uri http://localhost:8001/health/

# Test Search
Invoke-WebRequest -Uri http://localhost:8003/health

# View API Documentation
# Open in browser: http://localhost:8000/docs
```

**Run comprehensive API endpoint tests:**
```powershell
# Tests all 11 Graph Service endpoints and auto-cleans test data
python test_graph_api.py
```

This will test:
- ✅ Health and readiness endpoints
- ✅ User creation and retrieval
- ✅ Startup creation
- ✅ TRUSTS, FOUNDED, and INVESTED_IN edge creation
- ✅ Trust score updates
- ✅ Path discovery

After testing, it automatically cleans up test data to keep your database clean.

---

## 🎧 **Step 8: Start Kafka Consumers** (Optional but Recommended)

Kafka consumers enable real-time features (auto-indexing, notifications, trust updates).

**Open 3 separate PowerShell windows:**

**Window 1: Search Indexer**
```powershell
cd e:\Sem-6\NoSQL\startupConnect_draft\backend\search-service
python -m app.consumers.user_indexer_consumer
```

**Window 2: Trust Updater**
```powershell
cd e:\Sem-6\NoSQL\startupConnect_draft\backend\graph-service
python -m app.consumers.trust_update_consumer
```

**Window 3: Intro Workflow**
```powershell
cd e:\Sem-6\NoSQL\startupConnect_draft\backend\workflow-service
python -m app.consumers.intro_event_consumer
```

**Keep these windows running** while using the app.

---

## 📱 **Step 9: Setup and Run Flutter App**

### **Install Dependencies**

```powershell
cd e:\Sem-6\NoSQL\startupConnect_draft\frontend\trustgraph_app

# Install Flutter packages
flutter pub get
```

### **Run on Android Emulator or Device**

```powershell
# List available devices
flutter devices

# Run app (automatically picks available device)
flutter run

# Or specify device
flutter run -d windows    # Windows desktop
flutter run -d chrome     # Web browser
flutter run -d <device-id> # Specific device
```

### **Run on Chrome (Easiest for Testing)**

```powershell
flutter run -d chrome
```

**App should open in Chrome at:** http://localhost:port

---

## ✅ **Verify Everything Works**

### **1. Test User Registration**

1. Open app → Click "Register"
2. Fill form:
   - Name: Test User
   - Email: test@example.com
   - Password: password123
   - Role: Founder
   - Domains: Select "fintech", "saas"
   - Location: San Francisco
3. Click "Register"
4. Should auto-login and navigate to Home screen

**Check Kafka Consumer Logs:**
- Window 1 (Search Indexer) should show: `✅ Indexed user <user_id> in Elasticsearch`

### **2. Test Search**

1. Bottom nav → Tap "Search"
2. Search for "Alice" (from seed data)
3. Should see: Alice Johnson (Founder)
4. Tap on profile → Should show full details
5. Tap "Request Introduction" → Should show intro path screen

### **3. Test Intro Request**

1. From Alice's profile → "Request Introduction"
2. App discovers paths to connect you
3. Select a path → Add optional message
4. Submit intro request

**Check Kafka Consumer Logs:**
- Window 3 (Intro Workflow) should show: `✅ Sent intro_created notification`

### **4. Test Profile**

1. Bottom nav → Tap "Profile"
2. Should see your profile with stats
3. Tap "Edit" → Update bio and domains
4. Save → Should update successfully

---

## 🐛 **Troubleshooting**

### **Problem: Docker services won't start**

```powershell
# Stop all containers
docker-compose down

# Remove volumes (WARNING: Deletes data)
docker-compose down -v

# Rebuild and restart
docker-compose up -d --build
```

### **Problem: JanusGraph connection fails**

JanusGraph takes 60-90 seconds to fully initialize.

```powershell
# Wait and check logs
docker-compose logs -f janusgraph

# Look for: "Channel started at port 8182"
```

### **Problem: Kafka consumers can't connect**

```powershell
# Check Redpanda is running
docker-compose ps redpanda

# Check logs
docker-compose logs -f redpanda
```

### **Problem: Flutter app can't connect to backend**

**On Chrome/Web:**
- Check CORS settings in `.env` file
- Add `http://localhost:<flutter-port>` to `CORS_ORIGINS`

**On Android Emulator:**
- Use `http://10.0.2.2:8000` instead of `localhost:8000`
- Update `lib/data/providers/api_client.dart`:
  ```dart
  final baseUrl = 'http://10.0.2.2:8000';
  ```

### **Problem: Seed script fails**

```powershell
# Make sure JanusGraph is fully started
docker compose logs janusgraph | Select-String "Channel started"

# Wait 60 seconds after seeing this message, then retry
python backend\scripts\seed_data.py --clear
```

**If seeding still fails:**
1. Check that all Docker containers are healthy: `docker compose ps`
2. Restart JanusGraph: `docker compose restart janusgraph`
3. Wait 90 seconds for initialization
4. Try seeding again: `python backend\scripts\seed_data.py --clear`

**Clear and reseed database:**
```powershell
# Option 1: Using seed script flag
python backend\scripts\seed_data.py --clear

# Option 2: Using separate cleanup script
python clear_graph_data.py
python backend\scripts\seed_data.py
```

### **Problem: Python packages not found**

```powershell
# Install all required packages
pip install gremlinpython==3.7.1 motor==3.3.2 kafka-python==2.0.2 httpx elasticsearch redis
```

---

## 🔍 **View Service UIs**

- **API Gateway Docs**: http://localhost:8000/docs
- **Graph Service Docs**: http://localhost:8001/docs
- **Workflow Service Docs**: http://localhost:8002/docs
- **Search Service Docs**: http://localhost:8003/docs
- **Elasticsearch**: http://localhost:9200
- **MongoDB**: Connect with MongoDB Compass to `mongodb://trustgraph:trustgraph_secure_2024@localhost:27017`

---

## 📊 **Service Architecture**

```
┌─────────────────────────────────────────┐
│        Flutter App (Port: Auto)         │
└────────────────┬────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────┐
│      API Gateway (Port: 8000)           │
└────┬─────────────┬───────────────┬──────┘
     │             │               │
     v             v               v
┌─────────┐  ┌──────────┐  ┌──────────┐
│ Graph   │  │ Workflow │  │  Search  │
│ Service │  │ Service  │  │  Service │
│  8001   │  │   8002   │  │   8003   │
└────┬────┘  └────┬─────┘  └────┬─────┘
     │            │              │
     v            v              v
┌─────────────────────────────────────────┐
│        Infrastructure Layer             │
│  • JanusGraph (8182)                    │
│  • Cassandra (9042)                     │
│  • MongoDB (27017)                      │
│  • Elasticsearch (9200)                 │
│  • Redis (6379)                         │
│  • Redpanda/Kafka (9092)                │
└─────────────────────────────────────────┘
```

---

## 🎯 **Quick Start Commands (Summary)**

```powershell
# 1. Start backend
docker-compose up -d

# 2. Wait 2-3 minutes, then seed data
python backend\scripts\seed_data.py

# 3. Start Flutter app
cd frontend\trustgraph_app
flutter run -d chrome

# 4. (Optional) Start Kafka consumers in separate windows
python backend\search-service\app\consumers\user_indexer_consumer.py
python backend\graph-service\app\consumers\trust_update_consumer.py
python backend\workflow-service\app\consumers\intro_event_consumer.py
```

---

## 🛑 **Stop Everything**

```powershell
# Stop Docker services
docker-compose down

# Stop Flutter app (Ctrl+C in terminal)

# Stop Kafka consumers (Ctrl+C in each window)
```

---

## 📚 **Next Steps**

1. ✅ **Register a user** and test login/logout
2. ✅ **Search for users** from seed data (Alice, Bob, Carol, etc.)
3. ✅ **Request an introduction** and observe the workflow
4. ✅ **View pending intros** and approve/decline
5. ✅ **Check Profile** and edit your information
6. ✅ **View Connections** to see trust network

---

## 💡 **Tips**

- Keep Docker Desktop running while using the app
- Backend APIs are hot-reloaded (changes reflected automatically)
- Flutter supports hot-reload (`r` in terminal) for UI changes
- Check Kafka consumer logs to see real-time event processing
- Use Swagger docs (`/docs`) to test API endpoints directly

---

**Need Help?**
- Check logs: `docker-compose logs -f <service-name>`
- Verify services: `docker-compose ps`
- Restart service: `docker-compose restart <service-name>`
- Full reset: `docker-compose down -v && docker-compose up -d`
