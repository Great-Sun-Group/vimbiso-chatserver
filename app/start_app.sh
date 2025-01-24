#!/bin/bash
set -e

echo "Starting application..."
echo "Environment: $DJANGO_ENV"
echo "Port: $PORT"

# Debug Redis configuration
echo "REDIS_URL from environment: ${REDIS_URL:-not set}"
REDIS_HOST=$(echo "${REDIS_URL:-redis://localhost:6379/0}" | sed -E 's|redis://([^:/]+).*|\1|')
echo "Extracted Redis host: $REDIS_HOST"

# Test Redis connectivity with increased timeout
echo "Waiting for Redis to be ready..."
max_attempts=12  # 12 attempts * 5s = 60s total
attempt=1
wait_time=5  # Keep 5s to allow Redis to initialize

while true; do
    if [ $attempt -gt $max_attempts ]; then
        echo "Redis is still unavailable after $max_attempts attempts - giving up"
        echo "Last Redis connection attempt:"
        redis-cli -h "$REDIS_HOST" ping || true
        exit 1
    fi

    echo "Attempting Redis connection (attempt $attempt/$max_attempts waiting ${wait_time}s)..."

    # Try Redis connection with explicit timeout
    if timeout 5 redis-cli -h "$REDIS_HOST" ping > /dev/null 2>&1; then
        echo "Redis connection successful!"
        break
    else
        echo "Redis connection failed (attempt $attempt). Error code: $?"
        echo "Retrying in ${wait_time}s..."
        sleep $wait_time
        attempt=$((attempt + 1))
    fi
done

echo "Redis is ready!"

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
    exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:${PORT:-8000} \
        --workers ${GUNICORN_WORKERS:-2} \
        --worker-class sync \
        --timeout ${GUNICORN_TIMEOUT:-30} \
        --graceful-timeout 10 \
        --keep-alive 5 \
        --log-level debug \
        --access-logfile - \
        --error-logfile - \
        --capture-output \
        --enable-stdio-inheritance
else
    echo "Starting Django development server..."
    # Start Django with stdout/stderr going to console
    exec python manage.py runserver 0.0.0.0:${PORT:-8000}
fi
