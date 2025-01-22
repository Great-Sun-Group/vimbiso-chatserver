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
      name         = "redis-state"
      image        = "public.ecr.aws/docker/library/redis:7.0-alpine"
      essential    = false
      memory       = floor(var.task_memory * 0.3)
      cpu          = floor(var.task_cpu * 0.3)
      portMappings = [
        {
          containerPort = var.redis_state_port
          hostPort     = var.redis_state_port
          protocol     = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "redis-state"
          "awslogs-create-group"  = "true"
        }
      }
      command = [
        "redis-server",
        "--protected-mode", "no",
        "--bind", "0.0.0.0",
        "--port", tostring(var.redis_state_port),
        "--maxmemory-policy", "allkeys-lru",
        "--maxmemory", "${tostring(floor(var.task_memory * 0.3 * 0.90))}mb",
        "--save", "",           # Disable RDB persistence
        "--appendonly", "no"    # Disable AOF persistence
      ]
      healthCheck = {
        command     = ["CMD-SHELL", "redis-cli ping"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 10
      }
    },
    {
      name         = "vimbiso-pay-${var.environment}"
      image        = var.docker_image
      essential    = true
      memory       = floor(var.task_memory * 0.6)
      cpu          = floor(var.task_cpu * 0.6)
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
        { name = "GUNICORN_WORKERS", value = "2" },
        { name = "GUNICORN_TIMEOUT", value = "120" },
        { name = "DJANGO_LOG_LEVEL", value = "DEBUG" },
        { name = "APP_LOG_LEVEL", value = "DEBUG" },
        { name = "REDIS_URL", value = "redis://localhost:${var.redis_state_port}/0" },
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
          hostPort     = 8000
          protocol     = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "vimbiso-pay-${var.environment}"
          "awslogs-create-group"  = "true"
        }
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
        set -e
        mkdir -p /efs-vols/app-data/data/{static,media,logs}
        chmod 755 /efs-vols/app-data/data  # Ensure directory is writable for SQLite
        ln -sfn /efs-vols/app-data/data /app/data
        cd /app
        python manage.py collectstatic --noinput
        exec gunicorn config.wsgi:application \
          --bind "0.0.0.0:8000" \
          --workers "$${GUNICORN_WORKERS:-2}" \
          --timeout "$${GUNICORN_TIMEOUT:-120}" \
          --access-logfile - \
          --error-logfile -
        EOT
      ]
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health/ || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
      dependsOn = [
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
      file_system_id = var.efs_file_system_id
      root_directory = "/"
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = var.app_access_point_id
        iam = "ENABLED"
      }
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}
