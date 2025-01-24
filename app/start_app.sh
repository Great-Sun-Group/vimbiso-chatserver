#!/bin/bash
set -e

echo "Starting application..."
echo "Environment: $DJANGO_ENV"
echo "Port: $PORT"

# Debug Redis configuration
echo "REDIS_URL from environment: ${REDIS_URL:-not set}"
REDIS_HOST=$(echo "${REDIS_URL:-redis://localhost:6379/0}" | sed -E 's|redis://([^:/]+).*|\1|')
echo "Extracted Redis host: $REDIS_HOST"

# Test Redis connectivity with reasonable timeout
echo "Waiting for Redis to be ready..."
max_attempts=20  # 20 attempts * 3s = 60s total
attempt=1
wait_time=3

while true; do
    if [ $attempt -gt $max_attempts ]; then
        echo "Redis is still unavailable after $max_attempts attempts - giving up"
        echo "Last Redis connection attempt output:"
        redis-cli -h "$REDIS_HOST" ping || true
        echo "Network status:"
        netstat -an | grep 6379 || true
        exit 1
    fi

    echo "Attempting Redis connection (attempt $attempt/$max_attempts waiting ${wait_time}s)..."

    echo "Attempt $attempt: Testing Redis connection..."
    PING_RESULT=$(redis-cli -h "$REDIS_HOST" ping 2>&1)
    PING_EXIT=$?

    if [ $PING_EXIT -eq 0 ] && [ "$PING_RESULT" = "PONG" ]; then
        echo "Redis connection successful!"
        echo "Redis info:"
        redis-cli -h "$REDIS_HOST" info server
        redis-cli -h "$REDIS_HOST" info clients
        break
    else
        echo "Redis connection failed (exit code: $PING_EXIT)"
        echo "Redis response: $PING_RESULT"
        echo "Network status:"
        netstat -an | grep 6379 || true
        echo "DNS lookup:"
        nslookup "$REDIS_HOST" || true
        echo "Retrying in ${wait_time}s..."
        sleep $wait_time
        attempt=$((attempt + 1))
    fi
done

echo "Redis is ready!"

# Create and set up directories
echo "Setting up directories..."
mkdir -p /app/data/{static,media,logs}
chmod -R 755 /app/data
ls -la /app/data

# In production collect static files
if [ "${DJANGO_ENV:-development}" = "production" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Determine environment and set appropriate server command
if [ "${DJANGO_ENV:-development}" = "production" ]; then
    echo "Starting Gunicorn server in production mode..."
    echo "Workers: ${GUNICORN_WORKERS:-2}"

    # Using sync worker with preload for better memory efficiency
    echo "Starting Gunicorn with configuration:"
    echo "- Workers: ${GUNICORN_WORKERS:-2}"
    echo "- Timeout: ${GUNICORN_TIMEOUT:-120}"
    echo "- Log level: ${LOG_LEVEL:-info}"

    exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:${PORT:-8000} \
        --workers ${GUNICORN_WORKERS:-2} \
        --worker-class sync \
        --preload \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --log-level ${LOG_LEVEL:-info} \
        --access-logfile - \
        --error-logfile - \
        --timeout ${GUNICORN_TIMEOUT:-120} \
        --graceful-timeout 30 \
        --keep-alive 65
else
    echo "Starting Django development server..."
    # Start Django with stdout/stderr going to console
    exec python manage.py runserver 0.0.0.0:${PORT:-8000}
fi
