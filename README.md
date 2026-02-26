# TrustGraph - Startup Ecosystem Platform

A trust-weighted graph platform for warm introductions between Founders and Investors.

---

## ⚡ **Quick Start (For First-Time Setup)**

### **Prerequisites**
- **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop/)
- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Flutter SDK** - [Download](https://docs.flutter.dev/get-started/install)

### **Automated Setup (Recommended)**

**Windows PowerShell:**
```powershell
# Navigate to project
cd e:\Sem-6\NoSQL\startupConnect_draft

# Run quick start script
.\start.ps1
```

**Manual Setup:**
```powershell
# 1. Start backend services
docker-compose up -d

# 2. Wait 60 seconds, then seed data
python backend\scripts\seed_data.py

# 3. Run Flutter app
cd frontend\trustgraph_app
flutter pub get
flutter run -d chrome
```

📚 **Detailed Setup Guide:** See [SETUP_GUIDE.md](SETUP_GUIDE.md) for complete instructions

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend Layer                        │
│                     Flutter Mobile App                       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway (8000)                      │
│                 Authentication & Routing                     │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
│ Graph Service  │  │ Workflow Service│  │ Search Service  │
│    (8001)      │  │     (8002)      │  │     (8003)      │
│                │  │                 │  │                 │
│  JanusGraph    │  │    MongoDB      │  │ Elasticsearch   │
│  Cassandra     │  │    Redis        │  │    MongoDB      │
│  Redis Cache   │  │    Kafka        │  │    Redis        │
└────────────────┘  └─────────────────┘  └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Flutter 3.x (for mobile app)

### 1. Start Infrastructure

```bash
# Start all services
docker-compose up -d

# Wait for services to be healthy (2-3 minutes)
docker-compose ps

# View logs
docker-compose logs -f
```

### 2. Initialize Graph Schema

```bash
docker-compose exec graph-service python scripts/init_schema.py
```

### 3. Access Services

- **API Gateway**: http://localhost:8000/docs
- **Graph Service**: http://localhost:8001/docs
- **Workflow Service**: http://localhost:8002/docs
- **Search Service**: http://localhost:8003/docs
- **JanusGraph**: ws://localhost:8182/gremlin
- **MongoDB**: mongodb://localhost:27017
- **Elasticsearch**: http://localhost:9200
- **Redis**: localhost:6379

## 📁 Project Structure

```
startupConnect_draft/
├── backend/
│   ├── api-gateway/          # Main API Gateway (FastAPI)
│   ├── graph-service/        # Graph traversal & trust scoring
│   ├── workflow-service/     # Intro workflow state machine
│   ├── search-service/       # Search & discovery
│   ├── shared/               # Shared libraries
│   └── scripts/              # Database init scripts
├── frontend/
│   └── trustgraph_app/       # Flutter mobile app
├── docker-compose.yml
└── README.md
```

## 🎯 Core Features

### 1. Trust-Weighted Graph
- Multi-role nodes (Founder/Investor/Connector)
- Trust edges with scoring (trust, strength, recency)
- Mutual trust detection
- Dynamic weight updates

### 2. Intro Path Discovery
- Max 4-hop constraint
- Trust-weighted scoring
- Mutual trust prioritization
- Success probability prediction

### 3. Intro Workflow Engine
- Stepwise approval chain
- Intermediary accept/decline
- Auto graph updates
- Outcome tracking

### 4. Search & Discovery
- Graph-aware ranking
- Domain/tag filtering
- Investor thesis matching
- Connector discovery

## 🛠️ Development

### Backend Services

Each service follows the same structure:

```
service-name/
├── app/
│   ├── api/              # Route handlers
│   ├── core/             # Config & clients
│   ├── models/           # DB models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   └── main.py           # FastAPI app
├── tests/
├── Dockerfile
└── requirements.txt
```

### Running Tests

```bash
# Graph service tests
docker-compose exec graph-service pytest

# Workflow service tests
docker-compose exec workflow-service pytest

# Search service tests
docker-compose exec search-service pytest
```

### Local Development

```bash
# Install dependencies
cd backend/graph-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run locally (update .env with local URLs)
uvicorn app.main:app --reload --port 8001
```

## 📊 Graph Schema

### Vertex Types
- **User**: Founders, Investors, Connectors
- **Startup**: Companies in the ecosystem
- **Organization**: VCs, Accelerators, Incubators

### Edge Types
- **TRUSTS**: User → User (trust relationship)
- **FOUNDED**: User → Startup (founder relationship)
- **INVESTED_IN**: User → Startup (investment)
- **MEMBER_OF**: User → Organization (employment)
- **WORKED_WITH**: User → User (collaboration)

## 🔒 Environment Variables

Create `.env` files in each service directory:

```bash
# graph-service/.env
ENV=development
JANUSGRAPH_URL=ws://janusgraph:8182/gremlin
REDIS_URL=redis://redis:6379
KAFKA_BOOTSTRAP_SERVERS=redpanda:29092
MAX_INTRO_PATH_HOPS=4
MIN_TRUST_SCORE=0.3
```

## 📈 Monitoring

- **Health Checks**: Each service has `/health` endpoint
- **Metrics**: Prometheus metrics at `/metrics`
- **Logs**: Structured JSON logging

## 🐛 Troubleshooting

### JanusGraph connection issues
```bash
# Check JanusGraph health
docker-compose exec janusgraph bin/gremlin.sh
gremlin> :remote connect tinkerpop.server conf/remote.yaml
gremlin> :remote console
gremlin> g.V().count()
```

### Cassandra not ready
```bash
# Wait for Cassandra to stabilize
docker-compose logs cassandra
# Restart if needed
docker-compose restart janusgraph
```

## 📚 API Documentation

Visit `/docs` on any service for interactive API documentation (Swagger UI).

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Write tests
4. Submit PR

## 📄 License

MIT License - see LICENSE file
