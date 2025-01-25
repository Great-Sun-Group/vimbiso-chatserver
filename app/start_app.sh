#!/bin/bash
set -e

echo "Starting application..."
echo "Environment: $DJANGO_ENV"
echo "Port: $PORT"

# Debug Redis configuration
echo "REDIS_URL from environment: ${REDIS_URL:-not set}"
REDIS_HOST=$(echo "${REDIS_URL:-redis://localhost:6379/0}" | sed -E 's|redis://([^:/]+).*|\1|')
echo "Extracted Redis host: $REDIS_HOST"

# Try to get Redis container's IP
echo "Attempting to get Redis container IP..."
if getent hosts redis-state >/dev/null 2>&1; then
    REDIS_IP=$(getent hosts redis-state | awk '{ print $1 }')
    echo "Found Redis IP: $REDIS_IP"
    export REDIS_URL="redis://$REDIS_IP:6379/0"
    echo "Updated REDIS_URL to: $REDIS_URL"
    REDIS_HOST="$REDIS_IP"
else
    echo "Could not resolve Redis IP, using original host: $REDIS_HOST"
fi

# Test Redis connectivity in background with enhanced logging
(
    echo "Starting Redis connection attempts in background..."
    max_attempts=30  # 30 attempts * 10s = 5 minutes total
    attempt=1
    wait_time=10

    while true; do
        if [ $attempt -gt $max_attempts ]; then
            echo "Redis is still unavailable after $max_attempts attempts - will continue running without Redis"
            break
        fi

        echo "=== Redis Connection Attempt $attempt/$max_attempts ==="
        echo "Current time: $(date -u)"
        echo "REDIS_URL: ${REDIS_URL}"
        echo "REDIS_HOST: ${REDIS_HOST}"

        echo "=== DNS Resolution ==="
        echo "DNS configuration:"
        cat /etc/resolv.conf

        echo "DNS lookup for redis-state:"
        getent hosts redis-state || echo "Failed to resolve redis-state"

        echo "=== Network Configuration ==="
        echo "Network interfaces:"
        ip addr show

        echo "Network routes:"
        ip route

        echo "=== Container Discovery ==="
        echo "Docker DNS check:"
        dig redis-state || echo "dig command failed"

        echo "=== Redis Connection Test ==="
        if timeout 10 redis-cli -h "$REDIS_HOST" ping; then
            echo "Redis connection SUCCESSFUL!"
            # Export success for health check
            echo "REDIS_HEALTHY=true" > /tmp/redis_health
            break
        else
            echo "Redis connection FAILED (attempt $attempt)"
            echo "Detailed connection test:"
            nc -zv "$REDIS_HOST" 6379 || echo "TCP connection to $REDIS_HOST:6379 failed"
            redis-cli -h "$REDIS_HOST" ping -v || echo "Redis ping failed with verbose output"
            # Mark Redis as unhealthy
            echo "REDIS_HEALTHY=false" > /tmp/redis_health
        fi

        echo "=== End of Attempt $attempt ==="
        echo "Waiting $wait_time seconds before next attempt..."
        sleep $wait_time
        attempt=$((attempt + 1))
    done
) &

# Continue with app startup while Redis connection attempts happen in background

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
