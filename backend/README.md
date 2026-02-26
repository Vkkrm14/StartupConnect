# TrustGraph Backend Services

Production-grade microservices backend for the TrustGraph platform.

## Architecture

```
backend/
├── api-gateway/          # API Gateway (Port 8000)
├── graph-service/        # Graph traversal (Port 8001)
├── workflow-service/     # Intro workflow (Port 8002)
├── search-service/       # Search & discovery (Port 8003)
├── shared/               # Shared libraries
└── scripts/              # Database initialization
```

## Services

### 1. API Gateway (8000)
Main entry point for all client requests.

**Responsibilities**:
- Request routing to microservices
- Authentication & authorization
- Rate limiting
- CORS handling

**Tech Stack**: FastAPI, Redis, MongoDB

### 2. Graph Service (8001)
Core graph operations and path discovery.

**Responsibilities**:
- User/Startup/Organization vertex management
- TRUSTS edge creation and management
- **Path Discovery Engine** - Trust-weighted pathfinding (≤4 hops)
- Trust score calculation
- Reputation scoring

**Tech Stack**: FastAPI, JanusGraph, Cassandra, Gremlin, Redis

**Key Algorithms**:
- Trust-weighted path scoring
- Mutual trust detection
- Path ranking and filtering

### 3. Workflow Service (8002)
Intro request state management.

**Responsibilities**:
- Intro request creation
- Stepwise approval chain
- State machine engine
- Workflow status tracking

**Tech Stack**: FastAPI, MongoDB, Redis, Kafka

### 4. Search Service (8003)
Full-text search and discovery.

**Responsibilities**:
- User/Startup/Investor search
- Tag-based filtering
- Autocomplete
- Graph-aware ranking

**Tech Stack**: FastAPI, Elasticsearch, MongoDB, Redis

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- JanusGraph, Cassandra, MongoDB, Elasticsearch

### Quick Start

```bash
# 1. Start all infrastructure
docker-compose up -d

# 2. Wait for services to be healthy (check logs)
docker-compose logs -f

# 3. Initialize JanusGraph schema
docker-compose exec janusgraph bin/gremlin.sh
# Then paste the script from graph-service/scripts/init_schema.py

# 4. Access API documentation
open http://localhost:8000/docs      # API Gateway
open http://localhost:8001/docs      # Graph Service
open http://localhost:8002/docs      # Workflow Service
open http://localhost:8003/docs      # Search Service
```

### Local Development

Each service can be run locally for development:

```bash
cd backend/graph-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Run service
uvicorn app.main:app --reload --port 8001
```

## Environment Variables

Each service requires a `.env` file (see `.env.example` in each service directory).

**Common Variables**:
```bash
ENV=development
REDIS_URL=redis://localhost:6379
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

**Graph Service**:
```bash
JANUSGRAPH_URL=ws://localhost:8182/gremlin
MAX_INTRO_PATH_HOPS=4
MIN_TRUST_SCORE=0.3
```

**Workflow Service**:
```bash
MONGODB_URL=mongodb://trustgraph:password@localhost:27017/trustgraph_db
```

**Search Service**:
```bash
ELASTICSEARCH_URL=http://localhost:9200
```

## Testing

```bash
# Run all tests
docker-compose exec graph-service pytest
docker-compose exec workflow-service pytest
docker-compose exec search-service pytest

# Run specific test
docker-compose exec graph-service pytest tests/test_paths.py

# With coverage
docker-compose exec graph-service pytest --cov=app
```

## API Endpoints

### Graph Service

**Vertices**:
- `POST /api/v1/vertices/users` - Create user
- `GET /api/v1/vertices/users/{user_id}` - Get user
- `POST /api/v1/vertices/startups` - Create startup

**Edges**:
- `POST /api/v1/edges/trusts` - Create TRUSTS edge
- `PUT /api/v1/edges/trusts/score` - Update trust score
- `POST /api/v1/edges/trusts/increment-intros` - Increment successful intros

**Path Discovery** (Core Feature):
- `POST /api/v1/paths/discover` - Discover intro paths

Example request:
```json
{
  "founder_id": "user-123",
  "investor_id": "user-456",
  "max_paths": 5,
  "domain_filter": "fintech"
}
```

### Workflow Service

**Intro Workflows**:
- `POST /api/v1/intros` - Create intro request
- `GET /api/v1/intros/{intro_id}` - Get intro request
- `POST /api/v1/intros/approve` - Approve/decline intro

### Search Service

**Search**:
- `GET /api/v1/search/users?q={query}` - Search users
- `GET /api/v1/search/startups?q={query}` - Search startups

## Monitoring

### Health Checks
Each service exposes health endpoints:

```bash
curl http://localhost:8000/health  # API Gateway
curl http://localhost:8001/health  # Graph Service
curl http://localhost:8002/health  # Workflow Service
curl http://localhost:8003/health  # Search Service
```

### Logs
View logs for specific service:

```bash
docker-compose logs -f graph-service
docker-compose logs -f workflow-service
```

## Deployment

### Production Checklist

- [ ] Update all `.env` files with production values
- [ ] Change JWT secret keys
- [ ] Configure proper CORS origins
- [ ] Set up SSL/TLS certificates
- [ ] Enable Prometheus metrics
- [ ] Configure log aggregation
- [ ] Set up monitoring & alerting
- [ ] Configure backup strategy for databases

### Docker Build

```bash
# Build all services
docker-compose build

# Build specific service
docker-compose build graph-service

# Push to registry
docker tag trustgraph-graph-service:latest registry.example.com/trustgraph-graph-service:latest
docker push registry.example.com/trustgraph-graph-service:latest
```

## Contributing

1. Create feature branch from `main`
2. Follow code style (use `black` for Python formatting)
3. Write tests for new features
4. Update documentation
5. Submit pull request

## License

MIT License
