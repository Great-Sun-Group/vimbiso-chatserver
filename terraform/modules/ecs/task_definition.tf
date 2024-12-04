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
      name         = "redis"
      image        = "public.ecr.aws/docker/library/redis:7.0-alpine"
      essential    = true
      memory       = floor(var.task_memory * 0.35)
      cpu          = floor(var.task_cpu * 0.35)
      user         = "redis"
      portMappings = [
        {
          containerPort = var.redis_port
          hostPort     = var.redis_port
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "redis"
          awslogs-datetime-format = "%Y-%m-%d %H:%M:%S"
          awslogs-create-group  = "true"
          mode                  = "non-blocking"
          max-buffer-size       = "4m"
        }
      }
      mountPoints = [
        {
          sourceVolume  = "redis-data"
          containerPath = "/redis/data"  # Updated to match EFS access point path
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
        # Initialize Redis data directory
        mkdir -p /redis/data/appendonlydir

        # Check and repair AOF files if needed
        if [ -f /redis/data/appendonlydir/appendonly.aof.1.incr.aof ]; then
          echo "Checking AOF file integrity..."
          if ! redis-check-aof --fix /redis/data/appendonlydir/appendonly.aof.1.incr.aof; then
            echo "AOF file corrupted, removing and starting fresh..."
            rm -f /redis/data/appendonlydir/appendonly.aof.1.incr.aof
            rm -f /redis/data/appendonlydir/appendonly.aof.manifest
          fi
        fi

        # Ensure proper permissions
        chown -R redis:redis /redis/data

        # Start Redis with fixed memory limit and updated directory
        exec redis-server \
          --appendonly yes \
          --appendfsync everysec \
          --auto-aof-rewrite-percentage 100 \
          --auto-aof-rewrite-min-size 64mb \
          --aof-load-truncated yes \
          --aof-use-rdb-preamble yes \
          --protected-mode no \
          --bind 0.0.0.0 \
          --dir /redis/data \
          --timeout 30 \
          --tcp-keepalive 60 \
          --maxmemory-policy allkeys-lru \
          --maxmemory ${floor(var.task_memory * 0.35 * 0.95)}mb \
          --save "" \
          --stop-writes-on-bgsave-error no
        EOT
      ]
      healthCheck = {
        command     = ["CMD", "redis-cli", "ping"]
        interval    = 30
        timeout     = 15
        retries     = 3
        startPeriod = 300  # Increased to 5 minutes to match app startup time
      }
    },
    {
      name         = "vimbiso-pay-${var.environment}"
      image        = var.docker_image
      essential    = true
      memory       = floor(var.task_memory * 0.65)
      cpu          = floor(var.task_cpu * 0.65)
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
        { name = "REDIS_URL", value = "redis://localhost:${var.redis_port}/0" },
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

        echo "[App] Waiting for Redis..."
        until nc -z localhost ${var.redis_port}; do
          echo "[App] Redis port not available - sleeping 5s"
          sleep 5
        done

        # Test Redis connectivity with detailed output
        echo "[App] Testing Redis connectivity..."
        max_attempts=30
        attempt=1
        while [ $attempt -le $max_attempts ]; do
          echo "[App] Redis connection attempt $attempt/$max_attempts"

          if redis-cli -h localhost ping; then
            echo "[App] Redis PING successful"
            echo "[App] Redis INFO:"
            redis-cli -h localhost info | grep -E "^(# Server|redis_version|connected_clients|used_memory|used_memory_human|used_memory_peak|used_memory_peak_human|role)"
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

        # Test Django Redis connection
        echo "[App] Testing Django Redis connection..."
        cd /app
        python << EOF
import redis
from django.conf import settings
import sys

print("[App] Attempting to connect to Redis using settings.REDIS_URL:", settings.REDIS_URL)
try:
    r = redis.from_url(settings.REDIS_URL)
    r.ping()
    print("[App] Django Redis connection successful")
except Exception as e:
    print("[App] Django Redis connection failed:", str(e))
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
          --forwarded-allow-ips "*"
        EOT
      ]
      dependsOn = [
        {
          containerName = "redis"
          condition     = "HEALTHY"
        }
      ]
    }
  ])

  volume {
    name = "app-data"
    efs_volume_configuration {
      file_system_id = var.efs_file_system_id
      root_directory = "/"
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = var.app_access_point_id
        iam = "ENABLED"
      }
    }
  }

  volume {
    name = "redis-data"
    efs_volume_configuration {
      file_system_id = var.efs_file_system_id
      root_directory = "/"
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = var.redis_access_point_id
        iam = "ENABLED"
      }
    }
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-task-${var.environment}"
  })
}
