# Error Handling Quick Reference

## Exception Types

### ValidationException
For invalid input data:
```python
if not user_data.email:
    raise ValidationException("Email is required", {
        "field": "email",
        "reason": "required"
    })
```

### ResourceNotFoundException
For missing resources:
```python
user = await db.users.find_one({"_id": user_id})
if not user:
    raise ResourceNotFoundException("User", user_id)
```

### ServiceUnavailableException
For downstream service failures:
```python
try:
    response = await http_client.get(f"{service_url}/api/endpoint")
except httpx.ConnectError as e:
    raise ServiceUnavailableException("graph-service", str(e))
```

### AuthenticationException
For auth failures:
```python
if not token or not verify_token(token):
    raise AuthenticationException("Invalid or missing token")
```

### AuthorizationException
For permission issues:
```python
if user.role != "admin":
    raise AuthorizationException("Only admins can perform this action")
```

---

## Logging Patterns

### Basic Info Logging
```python
logger.info("User created successfully", extra={
    "user_id": user_id,
    "email": user.email
})
```

### Error Logging with Stack Trace
```python
try:
    result = await risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {str(e)}", exc_info=True)
    raise
```

### Warning for Recoverable Issues
```python
try:
    data = await fetch_from_service()
except httpx.TimeoutException:
    logger.warning(f"Service timeout, using cached data")
    data = await get_cached_data()
```

### Debug Logging for Development
```python
logger.debug(f"Processing payload", extra={
    "user_id": user_id,
    "payload_size": len(payload)
})
```

---

## API Endpoint Pattern

```python
@router.post("/api/v1/users")
async def create_user(request: Request, user_data: UserCreate):
    """Create a new user with error handling"""
    try:
        # Validate input
        if not user_data.email:
            raise ValidationException("Email is required", {"field": "email"})
        
        # Get database from request
        db = request.app.state.db
        
        # Check if exists
        existing = await db.users.find_one({"email": user_data.email})
        if existing:
            raise ValidationException("Email already exists", {"field": "email"})
        
        # Create user
        user_doc = {
            "_id": str(uuid.uuid4()),
            "email": user_data.email,
            "name": user_data.name,
            "created_at": datetime.utcnow()
        }
        
        await db.users.insert_one(user_doc)
        logger.info("User created", extra={"user_id": user_doc["_id"], "email": user_data.email})
        
        return {
            "user_id": user_doc["_id"],
            "email": user_data.email,
            "name": user_data.name
        }
    
    except (ValidationException, ResourceNotFoundException):
        raise  # Let global handler deal with it
    except Exception as e:
        logger.error(f"Failed to create user: {str(e)}", exc_info=True)
        raise
```

---

## Proxy Pattern (in API Gateway)

```python
@app.post("/api/v1/some/endpoint")
async def proxy_endpoint(request: Request):
    try:
        body = await request.json()
        
        result, status_code = await proxy_request(
            "POST",
            f"{settings.WORKFLOW_SERVICE_URL}/api/v1/some/endpoint",
            body,
            "proxy_endpoint"  # Context for logging
        )
        
        return result if status_code < 400 else {"error": result}
    except ServiceUnavailableException:
        raise
    except Exception as e:
        logger.error(f"Proxy error: {str(e)}", exc_info=True)
        raise
```

---

## Service Startup Pattern

```python
# In main.py

from shared.error_handling import (
    setup_logging,
    setup_exception_handlers,
    setup_request_logging_middleware
)

logger = setup_logging("service-name")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("🚀 Starting service...")
        logger.info(f"Environment: {settings.ENV}")
        
        # Connect to databases/services
        await connect_mongodb()
        await connect_elasticsearch()
        
        logger.info("✅ All connections established")
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}", exc_info=True)
        raise
    finally:
        logger.info("🛑 Shutting down service...")
        await cleanup()

app = FastAPI(...)
setup_exception_handlers(app, logger)
setup_request_logging_middleware(app, logger)
```

---

## Health Check Pattern

```python
@app.get("/health")
async def health_check():
    services_status = {}
    
    for service_name, service_url in services.items():
        try:
            response = await http_client.get(f"{service_url}/health", timeout=5.0)
            is_healthy = response.status_code == 200
            services_status[service_name] = {
                "status": "healthy" if is_healthy else "degraded",
                "status_code": response.status_code
            }
            logger.info(f"✅ {service_name} is healthy")
        except Exception as e:
            services_status[service_name] = {"status": "unavailable", "error": str(e)}
            logger.warning(f"⚠️ {service_name} is unavailable: {str(e)}")
    
    all_healthy = all(s.get("status") == "healthy" for s in services_status.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": services_status
    }
```

---

## Testing Error Handling

### Test with curl
```bash
# Test validation error
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"name": "John"}' # Missing email

# Test external service error
curl http://localhost:8000/health

# View error response with error ID
curl -X POST http://localhost:8000/api/v1/invalid \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Parse Error Response
```json
{
  "error": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "code": "VALIDATION_ERROR",
    "message": "Email is required",
    "details": { "field": "email" },
    "timestamp": "2026-02-28T10:30:45.123456"
  }
}
```

Use the error ID to find the corresponding error in logs:
```bash
grep "550e8400" logs/*.log
```

---

## Key Messages to Watch For

| Log Pattern | Meaning | Action |
|------------|---------|--------|
| `❌ Error during startup` | Service failed to start | Check connection config, database status |
| `⚠️ Service timeout` | Request took too long | Check service logs, network, load |
| `⚠️ Cannot connect to service` | Connection refused | Check if service is running |
| `❌ JSON parse error` | Invalid response format | Check upstream service response |
| `ERROR: ServiceUnavailable` | Downstream service down | Check health endpoint of that service |
| `WARNING: Kafka not available` | Message queue unavailable | Events may not be processed |

---

## Common Issues & Fixes

### "Service unavailable" errors
```bash
# Check if service is running
curl http://localhost:8001/health

# Check service logs for startup errors
docker logs <service-container>

# Verify configuration in config.py
```

### Timeout errors
```python
# Increase timeout in proxy calls
result, status = await proxy_request(
    "GET",
    url,
    logger_context="my_endpoint",
    timeout=15.0  # Increase from 10.0
)
```

### JSON parse errors
```python
# Check response before parsing
response = await http_client.get(url)
logger.debug(f"Response: {response.text[:500]}")  # Log first 500 chars
return response.json()
```

---

## Useful Debugging Commands

```bash
# View all errors
grep "ERROR" logs/*.log

# View errors for specific service
grep "graph-service" logs/*.log | grep "ERROR"

# View error IDs to track
grep "error_id" logs/*.log | head -20

# Count errors by type
grep "error_code" logs/*.log | cut -d: -f2 | sort | uniq -c

# Real-time log watching
tail -f logs/api-gateway.log | grep "ERROR"
```
