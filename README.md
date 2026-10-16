# TrustGraph - Startup Ecosystem Platform

A trust-weighted graph platform for warm introductions between founders and investors. Instead of matching on keywords alone, TrustGraph finds and ranks introduction paths by trust, relationship strength, recency, mutual trust and path length.

> A shorter path with stronger, recent and mutual trust is more likely to produce a successful introduction.

---

## Architecture

```
                    Flutter App (mobile / web)
                               |
                      API Gateway :8000
                               |
   +-----------+-----------+---+-------+-------------+
   |           |           |           |             |
 Graph      Workflow     Search     Messaging       Post
 :8001       :8002       :8003       :8004          :8005
   |           |           |           |             |
JanusGraph  MongoDB   Elasticsearch  Cassandra    MongoDB
Cassandra   Redis     MongoDB
Elasticsearch
Redis

Shared infrastructure: Redis (cache), Redpanda/Kafka (events)
```

| Layer | Technology |
|---|---|
| Frontend | Flutter |
| Services | FastAPI (Python 3.11+) |
| Graph | JanusGraph on Cassandra, Elasticsearch index backend |
| Documents | MongoDB (workflows, posts) |
| Search | Elasticsearch |
| Messaging | Cassandra |
| Cache / events | Redis, Redpanda (Kafka) |
| Auth | JWT |
| Orchestration | Docker Compose |

## Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Python 3.11+](https://www.python.org/downloads/)
- [Flutter SDK](https://docs.flutter.dev/get-started/install)

### 1. Start the backend

```bash
docker-compose up -d

# Wait for services to become healthy (2-3 minutes)
docker-compose ps
docker-compose logs -f
```

### 2. Seed data

```bash
python backend/scripts/seed_data.py
```

### 3. Run the Flutter app

```bash
cd frontend/trustgraph_app
flutter pub get
flutter run -d chrome
```

### Service endpoints

| Service | URL |
|---|---|
| API Gateway | http://localhost:8000/docs |
| Graph Service | http://localhost:8001/docs |
| Workflow Service | http://localhost:8002/docs |
| Search Service | http://localhost:8003/docs |
| Messaging Service | http://localhost:8004/docs |
| Post Service | http://localhost:8005/docs |
| JanusGraph | ws://localhost:8182/gremlin |
| MongoDB | mongodb://localhost:27017 |
| Elasticsearch | http://localhost:9200 |
| Redis | localhost:6379 |

## Project Structure

```
startupConnect_draft/
├── backend/
│   ├── api-gateway/          # Public entry point, auth, routing
│   ├── graph-service/        # Graph traversal and trust scoring
│   ├── workflow-service/     # Intro workflow state machine
│   ├── search-service/       # Search and discovery
│   ├── messaging-service/    # Conversations and messages
│   ├── post-service/         # Posts and feed
│   ├── shared/               # Shared libraries
│   └── scripts/              # Seeding, backfill and connection tests
├── frontend/
│   └── trustgraph_app/       # Flutter app
├── docker-compose.yml
├── Dockerfile.janusgraph
└── janusgraph-server.yaml
```

## Core Features

- **Trust-weighted graph**: multi-role nodes (founder, investor, connector), trust edges scored on trust, strength and recency, mutual-trust detection and dynamic weight updates.
- **Intro path discovery**: up to 4 hops, trust-weighted scoring, mutual-trust prioritisation and success-probability estimates.
- **Intro workflow engine**: stepwise approval chain, intermediary accept/decline, automatic graph updates and outcome tracking.
- **Search and discovery**: graph-aware ranking, domain/tag filters, investor thesis matching and connector discovery.
- **Messaging and posts**: conversations stored in Cassandra, posts and feed in MongoDB.
- **Authentication**: JWT-based, with role-aware behaviour.

## Graph Schema

**Vertices:** `User` (founder, investor, connector), `Startup`, `Organization` (VC, accelerator, incubator)

**Edges:**
- `TRUSTS`: User → User
- `FOUNDED`: User → Startup
- `INVESTED_IN`: User → Startup
- `MEMBER_OF`: User → Organization
- `WORKED_WITH`: User → User

## Development

Each backend service follows the same layout:

```
service-name/
├── app/
│   ├── api/        # Route handlers
│   ├── core/       # Config and clients
│   ├── models/     # DB models
│   ├── schemas/    # Pydantic schemas
│   ├── services/   # Business logic
│   └── main.py
├── tests/
├── Dockerfile
└── requirements.txt
```

Run a service locally:

```bash
cd backend/graph-service
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Run tests:

```bash
docker-compose exec graph-service pytest
docker-compose exec workflow-service pytest
docker-compose exec search-service pytest
```

### Environment variables

Create a `.env` per service, for example `graph-service/.env`:

```bash
ENV=development
JANUSGRAPH_URL=ws://janusgraph:8182/gremlin
REDIS_URL=redis://redis:6379
KAFKA_BOOTSTRAP_SERVERS=redpanda:29092
MAX_INTRO_PATH_HOPS=4
MIN_TRUST_SCORE=0.3
```

`.env` files are git-ignored; never commit secrets.

## Troubleshooting

**JanusGraph connection issues**
```bash
docker-compose exec janusgraph bin/gremlin.sh
gremlin> :remote connect tinkerpop.server conf/remote.yaml
gremlin> :remote console
gremlin> g.V().count()
```

**Cassandra not ready**
```bash
docker-compose logs cassandra
docker-compose restart janusgraph
```

**Verify connectivity to all stores**
```bash
python backend/scripts/test_connections.py
```

## Monitoring

Every service exposes `/health`. Interactive API docs (Swagger UI) are at `/docs` on each service.

## Contributing

1. Create a feature branch
2. Make changes and add tests
3. Open a PR

## License

MIT
