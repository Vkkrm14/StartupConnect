# TrustGraph Project File Tree

```
startupConnect_draft/
│
├── docker-compose.yml                     # Orchestrates all infrastructure services
├── .gitignore
├── README.md                              # Project overview & setup guide
├── context.txt                            # Feature specs & architecture docs
├── FILE_TREE.md                           # This file
│
├── backend/
│   │
│   ├── shared/                            # Shared libraries across services
│   │   ├── __init__.py
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── jwt_handler.py           # JWT token management
│   │   │   └── dependencies.py          # FastAPI auth dependencies
│   │   ├── messaging/
│   │   │   ├── __init__.py
│   │   │   ├── kafka_producer.py        # Kafka event producer
│   │   │   └── kafka_consumer.py        # Kafka event consumer
│   │   ├── cache/
│   │   │   ├── __init__.py
│   │   │   └── redis_client.py          # Redis cache utilities
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── logging.py               # Structured logging setup
│   │       └── validators.py            # Common validators
│   │
│   ├── api-gateway/                       # Main API Gateway (Port 8000)
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                  # FastAPI app entry point
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── config.py            # Service configuration
│   │   │   │   └── security.py          # Auth middleware
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── routes.py            # Main router
│   │   │   │   ├── users.py             # User endpoints
│   │   │   │   ├── intros.py            # Intro endpoints
│   │   │   │   └── search.py            # Search endpoints
│   │   │   └── middleware/
│   │   │       ├── __init__.py
│   │   │       ├── rate_limiter.py      # Rate limiting
│   │   │       └── cors.py              # CORS configuration
│   │   ├── tests/
│   │   │   └── test_gateway.py
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── .env.example
│   │
│   ├── graph-service/                     # Graph Service (Port 8001)
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                  # FastAPI app
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── config.py            # Service config
│   │   │   │   └── graph_client.py      # JanusGraph client
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── vertices.py          # Vertex CRUD
│   │   │   │   ├── edges.py             # Edge CRUD
│   │   │   │   ├── paths.py             # Path discovery
│   │   │   │   └── health.py            # Health checks
│   │   │   ├── schemas/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── vertex_schemas.py    # User/Startup/Org schemas
│   │   │   │   ├── edge_schemas.py      # Edge schemas
│   │   │   │   └── path_schemas.py      # Path response schemas
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── vertex_service.py    # Vertex operations
│   │   │       ├── edge_service.py      # Edge operations
│   │   │       ├── path_discovery.py    # Core pathfinding engine
│   │   │       └── trust_scoring.py     # Trust score calculations
│   │   ├── config/
│   │   │   ├── janusgraph-server.yaml   # JanusGraph config
│   │   │   └── gremlin-server.yaml      # Gremlin server config
│   │   ├── scripts/
│   │   │   └── init_schema.py           # Graph schema initialization
│   │   ├── tests/
│   │   │   ├── test_vertices.py
│   │   │   ├── test_edges.py
│   │   │   └── test_paths.py
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── .env.example
│   │
│   ├── workflow-service/                  # Workflow Service (Port 8002)
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                  # FastAPI app
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── config.py
│   │   │   │   └── database.py          # MongoDB connection
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── intros.py            # Intro workflow endpoints
│   │   │   │   ├── approvals.py         # Approval chain endpoints
│   │   │   │   └── health.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── intro_request.py     # Intro request model
│   │   │   │   └── approval.py          # Approval model
│   │   │   ├── schemas/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── intro_schemas.py     # Intro request schemas
│   │   │   │   └── approval_schemas.py  # Approval schemas
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── intro_service.py     # Intro workflow logic
│   │   │       ├── state_machine.py     # State machine engine
│   │   │       └── notification_service.py # Notification triggers
│   │   ├── tests/
│   │   │   └── test_workflow.py
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── .env.example
│   │
│   ├── search-service/                    # Search Service (Port 8003)
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                  # FastAPI app
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── config.py
│   │   │   │   ├── elasticsearch_client.py
│   │   │   │   └── database.py          # MongoDB connection
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── search.py            # Search endpoints
│   │   │   │   ├── autocomplete.py      # Autocomplete endpoints
│   │   │   │   └── health.py
│   │   │   ├── schemas/
│   │   │   │   ├── __init__.py
│   │   │   │   └── search_schemas.py    # Search request/response
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── search_service.py    # Search logic
│   │   │       ├── indexer.py           # ES indexing
│   │   │       └── ranking.py           # Graph-aware ranking
│   │   ├── tests/
│   │   │   └── test_search.py
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── .env.example
│   │
│   └── scripts/
│       ├── mongo-init.js                  # MongoDB initialization
│       ├── seed_data.py                   # Sample data seeding
│       └── test_connections.py            # Test all connections
│
├── frontend/
│   └── trustgraph_app/                    # Flutter Mobile App
│       ├── lib/
│       │   ├── main.dart                  # App entry point
│       │   ├── app.dart                   # App configuration
│       │   ├── core/
│       │   │   ├── config/
│       │   │   │   └── api_config.dart    # API endpoints
│       │   │   ├── theme/
│       │   │   │   └── app_theme.dart     # Theme configuration
│       │   │   └── utils/
│       │   │       └── validators.dart
│       │   ├── data/
│       │   │   ├── models/
│       │   │   │   ├── user_model.dart
│       │   │   │   ├── intro_model.dart
│       │   │   │   └── path_model.dart
│       │   │   ├── repositories/
│       │   │   │   ├── auth_repository.dart
│       │   │   │   ├── user_repository.dart
│       │   │   │   └── intro_repository.dart
│       │   │   └── providers/
│       │   │       └── api_client.dart    # HTTP client
│       │   ├── features/
│       │   │   ├── auth/
│       │   │   │   ├── screens/
│       │   │   │   │   ├── login_screen.dart
│       │   │   │   │   └── register_screen.dart
│       │   │   │   └── widgets/
│       │   │   ├── home/
│       │   │   │   ├── screens/
│       │   │   │   │   └── home_screen.dart
│       │   │   │   └── widgets/
│       │   │   ├── search/
│       │   │   │   ├── screens/
│       │   │   │   │   └── search_screen.dart
│       │   │   │   └── widgets/
│       │   │   ├── intros/
│       │   │   │   ├── screens/
│       │   │   │   │   ├── intro_request_screen.dart
│       │   │   │   │   └── path_visualization_screen.dart
│       │   │   │   └── widgets/
│       │   │   │       └── path_graph_widget.dart
│       │   │   └── profile/
│       │   │       ├── screens/
│       │   │       │   └── profile_screen.dart
│       │   │       └── widgets/
│       │   └── shared/
│       │       └── widgets/
│       │           ├── custom_button.dart
│       │           └── loading_indicator.dart
│       ├── test/
│       ├── pubspec.yaml                   # Flutter dependencies
│       ├── analysis_options.yaml
│       └── README.md
│
└── docs/
    ├── api/
    │   ├── api-gateway.md
    │   ├── graph-service.md
    │   ├── workflow-service.md
    │   └── search-service.md
    ├── architecture.md
    ├── deployment.md
    └── graph-schema.md
```

## Key Components Overview

### Backend Services (Microservices)

1. **API Gateway (8000)** - Entry point, auth, routing
2. **Graph Service (8001)** - JanusGraph, path discovery, trust scoring
3. **Workflow Service (8002)** - Intro workflow, state machine, MongoDB
4. **Search Service (8003)** - Elasticsearch, autocomplete, discovery

### Infrastructure (Docker Compose)

- **JanusGraph** (8182) - Graph database
- **Cassandra** (9042) - JanusGraph storage backend
- **MongoDB** (27017) - Document storage
- **Elasticsearch** (9200) - Search engine
- **Redis** (6379) - Cache & queues
- **Redpanda** (9092) - Event streaming (Kafka-compatible)

### Frontend

- **Flutter Mobile App** - Cross-platform iOS/Android app

## File Count Summary

- **Backend Python files**: ~85 files
- **Frontend Dart files**: ~35 files
- **Config files**: ~20 files
- **Total**: ~140 files

## Next Steps After Generation

1. `docker-compose up -d` - Start infrastructure
2. `docker-compose exec graph-service python scripts/init_schema.py` - Init graph
3. Access API docs at http://localhost:8000/docs
4. Run `cd frontend/trustgraph_app && flutter run` for mobile app
