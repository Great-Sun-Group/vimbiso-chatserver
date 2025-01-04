# Docker Configuration

## Overview

VimbisoPay uses Docker for:
- Application (Django)
- Redis Cache (General caching)
- Redis State (State management)
- Mock WhatsApp server (Testing)

## Services

### Application
```yaml
app:
  build:
    context: ..
    target: development  # or production
  ports:
    - "8000:8000"
  environment:
    - DJANGO_ENV=development
    - REDIS_URL=redis://redis-cache:6379/0
    - REDIS_STATE_URL=redis://redis-state:6379/0
  volumes:
    - ./data:/app/data
    - .:/app
  depends_on:
    redis-cache:
      condition: service_healthy
    redis-state:
      condition: service_healthy
```

### Redis Services

#### Cache Redis
```yaml
redis-cache:
  image: redis:7.0-alpine
  command: >
    redis-server
    --maxmemory 256mb
    --maxmemory-policy allkeys-lru
    --appendonly no
    --save ""
  volumes:
    - ./data/redis/cache:/data
  ports:
    - "6379:6379"
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 5s
    timeout: 3s
    retries: 3
```

#### State Redis
```yaml
redis-state:
  image: redis:7.0-alpine
  command: >
    redis-server
    --maxmemory 256mb
    --maxmemory-policy allkeys-lru
    --appendonly yes
    --appendfsync everysec
    --save ""
  volumes:
    - ./data/redis/state:/data
  ports:
    - "6380:6379"
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 5s
    timeout: 3s
    retries: 3
```

### Mock Server
```yaml
mock:
  build:
    context: ..
    target: development
  volumes:
    - ../mock:/app/mock
  ports:
    - "8001:8001"
```

## Development

### Quick Start
```bash
# Start services
make dev-build
make dev-up

# Access services
Application: http://localhost:8000
Mock WhatsApp: http://localhost:8001
Redis Cache: localhost:6379
Redis State: localhost:6380
```

### Service Communication
Within Docker network:
- Application: http://app:8000
- Redis Cache: redis://redis-cache:6379
- Redis State: redis://redis-state:6379
- Mock Server: http://mock:8001

## Production

### Security Features
```dockerfile
# Use non-root user
RUN adduser \
    --disabled-password \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "10001" \
    appuser

# Minimal dependencies
RUN apt-mark manual redis-tools curl gosu && \
    apt-get purge -y build-essential && \
    apt-get autoremove -y
```

### Health Checks
```yaml
healthcheck:
  test: curl -f http://localhost:${PORT}/health/
  interval: 30s
  timeout: 10s
  retries: 3
```

## Troubleshooting

Common issues:
1. **Connection Refused**
   ```bash
   # Check services
   docker-compose ps

   # Check logs
   docker-compose logs [service]
   ```

2. **Redis Issues**
   - Check memory usage
   - Verify configuration
   - See [Redis Management](redis-memory-management.md)