# Advanced Error Handling & Logging Guide

## Overview

A comprehensive error handling and logging system has been implemented across all TrustGraph services. This system provides:

- **Structured exception hierarchy** for different error types
- **Detailed request/response logging** with request tracing
- **Consistent error responses** across all services
- **Service health monitoring**
- **Proper exception handling middleware**

## Architecture

### Core Components

#### 1. **Custom Exception Classes** (`shared/error_handling.py`)

```python
# Base exception class
AppException
├── ValidationException      # 400 - Input validation failures
├── ResourceNotFoundException # 404 - Resource not found
├── ServiceUnavailableException # 503 - Service unavailable
├── AuthenticationException  # 401 - Auth failures
└── AuthorizationException   # 403 - Permission failures
```

#### 2. **Logging Configuration**

Each service uses a standardized logger configured with:
- Consistent timestamp format
- Service name in all log entries
- Function name and line number
- Detailed formatting for debugging

**Initialization:**
```python
from shared.error_handling import setup_logging
logger = setup_logging("service-name")
```

#### 3. **Exception Handlers**

Global exception handlers automatically:
- Catch application exceptions and return structured error responses
- Handle validation errors with 400 status
- Handle unexpected errors with 500 status
- Generate unique error IDs for tracking
- Include timestamps in all errors

**Error Response Format:**
```json
{
  "error": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "code": "VALIDATION_ERROR",
    "message": "Invalid input provided",
    "details": { "field": "user_id", "reason": "required" },
    "timestamp": "2026-02-28T10:30:45.123456"
  }
}
```

#### 4. **Request/Response Middleware**

Automatically logs:
- Incoming requests with method, path, query params, and client IP
- Outgoing responses with status codes
- Exceptions that occur during request handling
- Request IDs for tracing across services

**Log Entry Format:**
```
2026-02-28 10:30:45 | INFO     | service-name | handler:42 | → GET /api/v1/users
2026-02-28 10:30:46 | INFO     | service-name | handler:42 | ← GET /api/v1/users - 200
```

## Usage Guide

### For Each Service

**1. Update main.py:**
```python
from shared.error_handling import (
    setup_logging,
    setup_exception_handlers,
    setup_request_logging_middleware
)

# Setup logging
logger = setup_logging("service-name")

# After creating FastAPI app
setup_exception_handlers(app, logger)
setup_request_logging_middleware(app, logger)
```

**2. Use custom exceptions in endpoints:**
```python
@router.get("/api/v1/users/{user_id}")
async def get_user(user_id: str):
    try:
        user = await db.users.find_one({"_id": user_id})
        if not user:
            raise ResourceNotFoundException("User", user_id)
        return user
    except ResourceNotFoundException:
        raise  # Let the global handler deal with it
    except Exception as e:
        logger.error(f"Error fetching user: {str(e)}", exc_info=True)
        raise
```

### For API Gateway Proxying

The API Gateway includes a `proxy_request()` helper that automatically:
- Logs the proxy request
- Handles timeouts and connection errors
- Parses responses with error handling
- Returns structured error responses

**Usage:**
```python
@app.post("/api/v1/intros")
async def create_intro(request: Request):
    body = await request.json()
    result, status_code = await proxy_request(
        "POST",
        f"{settings.WORKFLOW_SERVICE_URL}/api/v1/intros",
        body,
        "create_intro"  # Context for logging
    )
    return result if status_code < 400 else {"error": result}
```

## Log Levels

- **DEBUG**: Detailed information for debugging, data transformations
- **INFO**: General operational information (service startup, successful operations)
- **WARNING**: Warning messages (service unavailable, retries, fallback actions)
- **ERROR**: Error conditions (failed operations, exceptions)

## Best Practices

### 1. Always Log Context

```python
# Good
logger.error(f"Failed to fetch user {user_id}", extra={
    "user_id": user_id,
    "service": "graph-service",
    "traceback": traceback.format_exc()
})

# Avoid
logger.error("Failed to fetch user")  # Too vague
```

### 2. Use Appropriate Exception Types

```python
# For validation errors
if not email_valid:
    raise ValidationException("Invalid email format", {
        "field": "email",
        "value": email
    })

# For missing resources
if not user:
    raise ResourceNotFoundException("User", user_id)

# For service failures
if connection_failed:
    raise ServiceUnavailableException("MongoDB", "Connection timeout")
```

### 3. Include Stack Traces in Error Logs

```python
try:
    result = await some_operation()
except Exception as e:
    logger.error(f"Operation failed: {str(e)}", exc_info=True)
    raise
```

### 4. Request IDs for Tracing

All responses include an `X-Request-ID` header. Use this in logs:
```python
request_id = request.headers.get("X-Request-ID", "unknown")
logger.info(f"Processing request", extra={"request_id": request_id})
```

### 5. Failed External Service Calls

```python
try:
    response = await http_client.get(f"{service_url}/endpoint", timeout=5.0)
    response.raise_for_status()
except httpx.TimeoutException:
    logger.error(f"Service timeout: {service_url}")
    raise ServiceUnavailableException("external-service")
except httpx.ConnectError as e:
    logger.error(f"Cannot connect to service: {str(e)}")
    raise ServiceUnavailableException("external-service", str(e))
```

## Monitoring

### Health Endpoints

All services expose `/health`:
```bash
# API Gateway aggregates all services
curl http://localhost:8000/health

# Individual service health
curl http://localhost:8001/health  # Graph Service
curl http://localhost:8002/health  # Workflow Service
curl http://localhost:8003/health  # Search Service
```

**Response:**
```json
{
  "status": "healthy|degraded",
  "services": {
    "graph-service": { "status": "healthy", "status_code": 200 },
    "workflow-service": { "status": "healthy", "status_code": 200 },
    "search-service": { "status": "unavailable", "error": "..." }
  }
}
```

### Log Monitoring

Set up log aggregation to monitor:
1. **Error rates** - Count of errors by service and type
2. **Response times** - Latency of requests
3. **Service health** - Connectivity to downstream services
4. **Exception patterns** - Recurring errors that need investigation

Example log queries:
```bash
# All errors in the system
grep "ERROR" logs/*.log

# All timeout-related errors
grep -i "timeout" logs/*.log

# All service unavailability errors
grep "ServiceUnavailable" logs/*.log

# Errors for a specific service
grep "graph-service" logs/*.log | grep "ERROR"
```

## Error Recovery Strategies

### Timeout Handling
```python
try:
    response = await http_client.get(url, timeout=5.0)
except httpx.TimeoutException:
    logger.warning(f"Timeout fetching {url}, retrying...")
    # Implement exponential backoff or circuit breaker
    retry_count = 0
    while retry_count < 3:
        try:
            response = await http_client.get(url, timeout=5.0)
            break
        except httpx.TimeoutException:
            retry_count += 1
            if retry_count >= 3:
                raise ServiceUnavailableException("service", "timeout after 3 retries")
```

### Graceful Degradation
```python
try:
    async with httpx.AsyncClient(timeout=2.0) as client:
        response = await client.get(f"{service_url}/critical_data")
        return response.json()
except:
    logger.warning(f"Could not fetch from {service_url}, using cached data")
    return await get_cached_data()
```

### Connection Pooling
```python
# Initialize once at startup
http_client = httpx.AsyncClient(
    timeout=30.0,
    follow_redirects=True,
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
)

# Use throughout the application
```

## Troubleshooting

### "Service unavailable" errors

1. Check service is running: `curl http://localhost:PORT/health`
2. Check logs for startup errors
3. Verify MongoDB/Redis/Elasticsearch connections
4. Check network connectivity between services

### High latency in responses

1. Check log for service timeouts
2. Monitor CPU/memory usage of services
3. Check database query performance
4. Review request/response sizes

### Repeated errors from same endpoint

1. Check error ID in logs for patterns
2. Review detailed error messages and context
3. Check for upstream service issues
4. Review recent code changes that modified the endpoint

## Summary

The error handling system provides:
✅ Structured exceptions for consistent error responses
✅ Detailed logging for debugging and monitoring  
✅ Request tracing with unique IDs
✅ Health checks for service monitoring
✅ Automatic middleware for request/response logging
✅ Graceful error responses instead of crashes

All services now use this unified system for reliable error handling and comprehensive logging.
