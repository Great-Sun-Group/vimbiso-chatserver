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
      user         = "root"
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
          containerPath = "/data"
          readOnly     = false
        }
      ]
      environment = [
        {
          name  = "TZ",
          value = "UTC"
        }
      ]
      command = [
        "sh",
        "-c",
        <<-EOT
        # Install su-exec if not present
        apk add --no-cache su-exec

        # Ensure data directory exists with correct permissions
        mkdir -p /data
        chown -R redis:redis /data
        chmod 755 /data

        echo "[Redis] Starting Redis server..."
        exec su-exec redis redis-server --appendonly yes --protected-mode no --bind 0.0.0.0 --dir /data
        EOT
      ]
      healthCheck = {
        command     = ["CMD-SHELL", "redis-cli ping | grep -q PONG || exit 1"]
        interval    = 15
        timeout     = 5
        retries     = 3
        startPeriod = 20
      }
    },
    {
      name         = "vimbiso-pay-${var.environment}"
      image        = var.docker_image
      essential    = true
      memory       = floor(var.task_memory * 0.65)
      cpu          = floor(var.task_cpu * 0.65)
      user         = "root"  # Run as root initially for setup
      environment  = [
        { name = "DJANGO_ENV", value = var.environment },
        { name = "DJANGO_SECRET", value = var.django_env.django_secret },
        { name = "DEBUG", value = tostring(var.django_env.debug) },
        { name = "ALLOWED_HOSTS", value = "${var.allowed_hosts} localhost 127.0.0.1 0.0.0.0" },
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
        { name = "REDIS_URL", value = "redis://redis:${var.redis_port}/0" },
        { name = "LANG", value = "en_US.UTF-8" },
        { name = "LANGUAGE", value = "en_US:en" },
        { name = "LC_ALL", value = "en_US.UTF-8" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "TZ", value = "UTC" },
        { name = "PORT", value = tostring(var.app_port) }
      ]
      portMappings = [
        {
          containerPort = var.app_port
          hostPort      = var.app_port
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "app"
          awslogs-datetime-format = "%Y-%m-%d %H:%M:%S"
          awslogs-create-group  = "true"
          awslogs-multiline-pattern = "^\\[\\d{4}-\\d{2}-\\d{2}"
          mode                  = "non-blocking"
          max-buffer-size       = "4m"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f --max-time 10 http://localhost:${var.app_port}/health/ || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 120
      }
      mountPoints = [
        {
          sourceVolume  = "app-data"
          containerPath = "/efs-vols/app-data"
          readOnly     = false
        }
      ]
      command = [
        "sh",
        "-c",
        <<-EOT
        # Install required packages
        apt-get update && \
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
          curl \
          iproute2 \
          netcat-traditional && \
        rm -rf /var/lib/apt/lists/*

        # Set up directories with proper permissions
        mkdir -p /efs-vols/app-data/data/{db,static,media,logs}
        chown -R 10001:10001 /efs-vols/app-data
        chmod 755 /efs-vols/app-data
        chmod 777 /efs-vols/app-data/data/db  # Ensure SQLite has write access

        echo "[App] Waiting for Redis..."
        until (echo > /dev/tcp/redis/${var.redis_port}) >/dev/null 2>&1; do
          echo "[App] Redis is unavailable - sleeping 2s"
          sleep 2
        done

        # Additional Redis connectivity check
        max_attempts=30
        attempt=1
        until redis-cli -h redis ping > /dev/null 2>&1; do
          if [ $attempt -ge $max_attempts ]; then
            echo "[App] ERROR: Redis not responding after 60 seconds"
            exit 1
          fi
          echo "[App] Waiting for Redis to accept connections... attempt $attempt/$max_attempts"
          attempt=$((attempt + 1))
          sleep 2
        done
        echo "[App] Redis is ready"

        # Create SQLite database directory if it doesn't exist
        mkdir -p /app/data/db
        chown -R 10001:10001 /app/data
        chmod 777 /app/data/db

        # Switch to app user and start the application
        exec su-exec 10001:10001 ./start_app.sh
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
