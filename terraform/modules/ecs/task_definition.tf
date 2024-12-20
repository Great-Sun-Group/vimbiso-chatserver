resource "aws_ecs_task_definition" "app" {
  family                   = "vimbiso-pay-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn           = var.task_role_arn

  container_definitions = jsonencode([
    {
      name         = "redis-cache"
      image        = "public.ecr.aws/docker/library/redis:7.0-alpine"
      essential    = true
      memory       = floor(var.task_memory * 0.2)
      cpu          = floor(var.task_cpu * 0.2)
      user         = "root"  # Need root for initial setup
      portMappings = [
        {
          containerPort = var.redis_cache_port
          hostPort     = var.redis_cache_port
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "redis-cache"
          awslogs-datetime-format = "%Y-%m-%d %H:%M:%S"
          awslogs-create-group  = "true"
          mode                  = "non-blocking"
          max-buffer-size       = "4m"
        }
      }
      mountPoints = [
        {
          sourceVolume  = "redis-cache-data"
          containerPath = "/redis/cache"
          readOnly     = false
        }
      ]
      environment = [
        {
          name  = "TZ"
          value = "UTC"
        }
      ]
      command = [
        "sh",
        "-c",
        <<-EOT
        # Install gosu for proper user switching
        apk add --no-cache gosu

        # Initialize Redis data directory
        mkdir -p /redis/cache/appendonlydir
        chown -R redis:redis /redis/cache

        # Check and repair AOF files if needed
        if [ -f /redis/cache/appendonlydir/appendonly.aof.1.incr.aof ]; then
          echo "Checking AOF file integrity..."
          if ! redis-check-aof --fix /redis/cache/appendonlydir/appendonly.aof.1.incr.aof; then
            echo "AOF file corrupted, removing and starting fresh..."
            rm -f /redis/cache/appendonlydir/appendonly.aof.1.incr.aof
            rm -f /redis/cache/appendonlydir/appendonly.aof.manifest
          fi
        fi

        # Start Redis with proper user and fixed memory limit
        exec gosu redis redis-server \
          --appendonly yes \
          --appendfsync no \
          --auto-aof-rewrite-percentage 100 \
          --auto-aof-rewrite-min-size 64mb \
          --aof-load-truncated yes \
          --aof-use-rdb-preamble yes \
          --protected-mode no \
          --bind 0.0.0.0 \
          --port ${var.redis_cache_port} \
          --dir /redis/cache \
          --timeout 30 \
          --tcp-keepalive 60 \
          --maxmemory-policy allkeys-lru \
          --maxmemory ${floor(var.task_memory * 0.2 * 0.95)}mb \
          --save "" \
          --stop-writes-on-bgsave-error no \
          --no-appendfsync-on-rewrite yes \
          --aof-rewrite-incremental-fsync yes \
          --dynamic-hz yes \
          --lazyfree-lazy-eviction yes \
          --lazyfree-lazy-expire yes \
          --lazyfree-lazy-server-del yes \
          --replica-lazy-flush yes \
          --activedefrag yes \
          --active-defrag-ignore-bytes 100mb \
          --active-defrag-threshold-lower 10 \
          --active-defrag-threshold-upper 100 \
          --active-defrag-cycle-min 25 \
          --active-defrag-cycle-max 75 \
          --active-defrag-max-scan-fields 1000 \
          --jemalloc-bg-thread yes \
          --maxclients 100 \
          --timeout 5 \
          --tcp-keepalive 60 \
          --appendfsync no \
          --shutdown-timeout 5 \
          --io-threads 2 \
          --io-threads-do-reads yes \
          --close-on-replica-write no
        EOT
      ]
      healthCheck = {
        command     = ["CMD-SHELL", "redis-cli -p ${var.redis_cache_port} ping"]
        interval    = 30
        timeout     = 15
        retries     = 3
        startPeriod = 300
      }
    },
    {
      name         = "redis-state"
      image        = "public.ecr.aws/docker/library/redis:7.0-alpine"
      essential    = true
      memory       = floor(var.task_memory * 0.2)
      cpu          = floor(var.task_cpu * 0.2)
      user         = "root"  # Need root for initial setup
      portMappings = [
        {
          containerPort = var.redis_state_port
          hostPort     = var.redis_state_port
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "redis-state"
          awslogs-datetime-format = "%Y-%m-%d %H:%M:%S"
          awslogs-create-group  = "true"
          mode                  = "non-blocking"
          max-buffer-size       = "4m"
        }
      }
      mountPoints = [
        {
          sourceVolume  = "redis-state-data"
          containerPath = "/redis/state"
          readOnly     = false
        }
      ]
      environment = [
        {
          name  = "TZ"
          value = "UTC"
        }
      ]
      command = [
        "sh",
        "-c",
        <<-EOT
        # Install gosu for proper user switching
        apk add --no-cache gosu

        # Initialize Redis data directory
        mkdir -p /redis/state/appendonlydir
        chown -R redis:redis /redis/state

        # Check and repair AOF files if needed
        if [ -f /redis/state/appendonlydir/appendonly.aof.1.incr.aof ]; then
          echo "Checking AOF file integrity..."
          if ! redis-check-aof --fix /redis/state/appendonlydir/appendonly.aof.1.incr.aof; then
            echo "AOF file corrupted, removing and starting fresh..."
            rm -f /redis/state/appendonlydir/appendonly.aof.1.incr.aof
            rm -f /redis/state/appendonlydir/appendonly.aof.manifest
          fi
        fi

        # Start Redis with proper user and fixed memory limit
        exec gosu redis redis-server \
          --appendonly yes \
          --appendfsync no \
          --auto-aof-rewrite-percentage 100 \
          --auto-aof-rewrite-min-size 64mb \
          --aof-load-truncated yes \
          --aof-use-rdb-preamble yes \
          --protected-mode no \
          --bind 0.0.0.0 \
          --port ${var.redis_state_port} \
          --dir /redis/state \
          --timeout 30 \
          --tcp-keepalive 60 \
          --maxmemory-policy allkeys-lru \
          --maxmemory ${floor(var.task_memory * 0.2 * 0.95)}mb \
          --save "" \
          --stop-writes-on-bgsave-error no \
          --no-appendfsync-on-rewrite yes \
          --aof-rewrite-incremental-fsync yes \
          --dynamic-hz yes \
          --lazyfree-lazy-eviction yes \
          --lazyfree-lazy-expire yes \
          --lazyfree-lazy-server-del yes \
          --replica-lazy-flush yes \
          --activedefrag yes \
          --active-defrag-ignore-bytes 100mb \
          --active-defrag-threshold-lower 10 \
          --active-defrag-threshold-upper 100 \
          --active-defrag-cycle-min 25 \
          --active-defrag-cycle-max 75 \
          --active-defrag-max-scan-fields 1000 \
          --jemalloc-bg-thread yes
        EOT
      ]
      healthCheck = {
        command     = ["CMD-SHELL", "redis-cli -p ${var.redis_state_port} ping"]
        interval    = 30
        timeout     = 15
        retries     = 3
        startPeriod = 300
      }
    },
    {
      name         = "vimbiso-pay-${var.environment}"
      image        = var.docker_image
      essential    = true
      memory       = floor(var.task_memory * 0.6)
      cpu          = floor(var.task_cpu * 0.6)
      user         = "root"  # Need root for initial setup
      environment  = [
        { name = "DJANGO_ENV", value = var.environment },
        { name = "DJANGO_SECRET", value = var.django_env.django_secret },
        { name = "DEBUG", value = tostring(var.django_env.debug) },
        { name = "ALLOWED_HOSTS", value = "*" },
        { name = "MYCREDEX_APP_URL", value = var.django_env.mycredex_app_url },
        { name = "CLIENT_API_KEY", value = var.django_env.client_api_key },
        { name = "WHATSAPP_API_URL", value = var.django_env.whatsapp_api_url },
        { name = "WHATSAPP_ACCESS_TOKEN", value = var.django_env.whatsapp_access_token },
        { name = "WHATSAPP_PHONE_NUMBER_ID", value = var.django_env.whatsapp_phone_number_id },
        { name = "WHATSAPP_BUSINESS_ID", value = var.django_env.whatsapp_business_id },
        { name = "WHATSAPP_REGISTRATION_FLOW_ID", value = var.django_env.whatsapp_registration_flow_id },
        { name = "WHATSAPP_COMPANY_REGISTRATION_FLOW_ID", value = var.django_env.whatsapp_company_registration_flow_id },
        { name = "GUNICORN_WORKERS", value = "2" },
        { name = "GUNICORN_TIMEOUT", value = "120" },
        { name = "DJANGO_LOG_LEVEL", value = "DEBUG" },
        { name = "APP_LOG_LEVEL", value = "DEBUG" },
        { name = "REDIS_URL", value = "redis://localhost:${var.redis_cache_port}/0" },
        { name = "REDIS_STATE_URL", value = "redis://localhost:${var.redis_state_port}/0" },
        { name = "LANG", value = "en_US.UTF-8" },
        { name = "LANGUAGE", value = "en_US:en" },
        { name = "LC_ALL", value = "en_US.UTF-8" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "TZ", value = "UTC" },
        { name = "PORT", value = "8000" }
      ]
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "vimbiso-pay-${var.environment}"
          awslogs-datetime-format = "%Y-%m-%d %H:%M:%S"
          awslogs-create-group  = "true"
          mode                  = "non-blocking"
          max-buffer-size       = "4m"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f --max-time 15 --retry 5 --retry-delay 10 --retry-max-time 90 http://127.0.0.1:8000/health/ || exit 1"]
        interval    = 30
        timeout     = 15
        retries     = 3
        startPeriod = 300
      }
      mountPoints = [
        {
          sourceVolume  = "app-data"
          containerPath = "/efs-vols/app-data"
          readOnly     = false
        }
      ]
      command = [
        "bash",
        "-c",
        <<-EOT
        set -ex

        echo "[App] Starting initialization..."

        # Install required packages
        apt-get update
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
          curl \
          iproute2 \
          netcat-traditional \
          dnsutils \
          gosu \
          redis-tools
        rm -rf /var/lib/apt/lists/*

        # Wait for network readiness
        echo "[App] Waiting for network readiness..."
        until getent hosts localhost >/dev/null 2>&1; do
          echo "[App] Network not ready - sleeping 2s"
          sleep 2
        done

        # Set up directories with proper permissions
        echo "[App] Setting up directories..."
        mkdir -p /efs-vols/app-data/data/{db,static,media,logs}
        chown -R 10001:10001 /efs-vols/app-data
        chmod 777 /efs-vols/app-data/data/db

        echo "[App] Waiting for Redis Cache..."
        until nc -z localhost ${var.redis_cache_port}; do
          echo "[App] Redis Cache port not available - sleeping 5s"
          sleep 5
        done

        echo "[App] Waiting for Redis State..."
        until nc -z localhost ${var.redis_state_port}; do
          echo "[App] Redis State port not available - sleeping 5s"
          sleep 5
        done

        # Test Redis connectivity with detailed output
        echo "[App] Testing Redis connectivity..."
        max_attempts=30
        attempt=1
        while [ $attempt -le $max_attempts ]; do
          echo "[App] Redis connection attempt $attempt/$max_attempts"

          if redis-cli -p ${var.redis_cache_port} ping && redis-cli -p ${var.redis_state_port} ping; then
            echo "[App] Redis PING successful for both instances"
            echo "[App] Redis Cache INFO:"
            redis-cli -p ${var.redis_cache_port} info | grep -E "^(# Server|redis_version|connected_clients|used_memory|used_memory_human|used_memory_peak|used_memory_peak_human|role)"
            echo "[App] Redis State INFO:"
            redis-cli -p ${var.redis_state_port} info | grep -E "^(# Server|redis_version|connected_clients|used_memory|used_memory_human|used_memory_peak|used_memory_peak_human|role)"
            break
          else
            echo "[App] Redis PING failed"
            if [ $attempt -eq $max_attempts ]; then
              echo "[App] Redis connection attempts exhausted"
              exit 1
            fi
          fi

          attempt=$((attempt + 1))
          sleep 5
        done

        # Test Django Redis connections
        echo "[App] Testing Django Redis connections..."
        cd /app
        python << EOF
import redis
from django.conf import settings
import sys

print("[App] Attempting to connect to Redis Cache using settings.REDIS_CACHE_URL:", settings.REDIS_CACHE_URL)
print("[App] Attempting to connect to Redis State using settings.REDIS_STATE_URL:", settings.REDIS_STATE_URL)
try:
    rc = redis.from_url(settings.REDIS_CACHE_URL)
    rs = redis.from_url(settings.REDIS_STATE_URL)
    rc.ping()
    rs.ping()
    print("[App] Django Redis connections successful")
except Exception as e:
    print("[App] Django Redis connections failed:", str(e))
    sys.exit(1)
EOF

        echo "[App] Creating data symlink..."
        ln -sfn /efs-vols/app-data/data /app/data

        echo "[App] Running migrations..."
        python manage.py migrate --noinput

        echo "[App] Collecting static files..."
        python manage.py collectstatic --noinput

        echo "[App] Starting Gunicorn..."
        exec gunicorn config.wsgi:application \
          --bind "0.0.0.0:8000" \
          --workers "$${GUNICORN_WORKERS:-2}" \
          --worker-class sync \
          --preload \
          --max-requests 1000 \
          --max-requests-jitter 50 \
          --log-level debug \
          --error-logfile - \
          --access-logfile - \
          --capture-output \
          --enable-stdio-inheritance \
          --timeout "$${GUNICORN_TIMEOUT:-120}" \
          --graceful-timeout 30 \
          --keep-alive 65 \
          --forwarded-allow-ips "*" \
          --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" "%({X-Forwarded-For}i)s" "%({X-Forwarded-Proto}i)s"'
        EOT
      ]
      dependsOn = [
        {
          containerName = "redis-cache"
          condition     = "HEALTHY"
        },
        {
          containerName = "redis-state"
          condition     = "HEALTHY"
        }
      ]
    }
  ])

  volume {
    name = "app-data"
    efs_volume_configuration {
      file_system_id          = var.efs_file_system_id
      root_directory          = "/"
      transit_encryption      = "ENABLED"
      authorization_config {
        access_point_id = var.app_access_point_id
        iam            = "ENABLED"
      }
    }
  }

  volume {
    name = "redis-cache-data"
    efs_volume_configuration {
      file_system_id          = var.efs_file_system_id
      root_directory          = "/"
      transit_encryption      = "ENABLED"
      authorization_config {
        access_point_id = var.redis_cache_access_point_id
        iam            = "ENABLED"
      }
    }
  }

  volume {
    name = "redis-state-data"
    efs_volume_configuration {
      file_system_id          = var.efs_file_system_id
      root_directory          = "/"
      transit_encryption      = "ENABLED"
      authorization_config {
        access_point_id = var.redis_state_access_point_id
        iam            = "ENABLED"
      }
    }
  }

  tags = {
    Name        = "vimbiso-pay-task-${var.environment}"
    Environment = var.environment
  }
}
