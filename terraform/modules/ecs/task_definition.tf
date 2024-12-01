# ECS Task Definition
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
      image        = "redis:7-alpine"
      essential    = true
      memory       = floor(var.task_memory * 0.25)
      cpu          = floor(var.task_cpu * 0.25)
      portMappings = [
        {
          containerPort = var.redis_port
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "redis"
          awslogs-datetime-format = "%Y-%m-%d %H:%M:%S"
          awslogs-create-group  = "true"
        }
      }
      healthCheck = {
        command     = ["CMD", "redis-cli", "ping"]
        interval    = 30
        timeout     = 5
        retries     = 5
        startPeriod = 60
      }
      mountPoints = [
        {
          sourceVolume  = "redis-data"
          containerPath = "/data"
          readOnly     = false
        }
      ]
    },
    {
      name         = "vimbiso-pay-${var.environment}"
      image        = var.docker_image
      essential    = true
      memory       = floor(var.task_memory * 0.75)
      cpu          = floor(var.task_cpu * 0.75)
      environment  = [
        { name = "DJANGO_ENV", value = var.environment },
        { name = "DJANGO_SECRET", value = var.django_env.django_secret },
        { name = "DEBUG", value = tostring(var.django_env.debug) },
        { name = "ALLOWED_HOSTS", value = var.allowed_hosts },
        { name = "MYCREDEX_APP_URL", value = var.django_env.mycredex_app_url },
        { name = "CLIENT_API_KEY", value = var.django_env.client_api_key },
        { name = "WHATSAPP_API_URL", value = var.django_env.whatsapp_api_url },
        { name = "WHATSAPP_ACCESS_TOKEN", value = var.django_env.whatsapp_access_token },
        { name = "WHATSAPP_PHONE_NUMBER_ID", value = var.django_env.whatsapp_phone_number_id },
        { name = "WHATSAPP_BUSINESS_ID", value = var.django_env.whatsapp_business_id },
        { name = "WHATSAPP_REGISTRATION_FLOW_ID", value = var.django_env.whatsapp_registration_flow_id },
        { name = "WHATSAPP_COMPANY_REGISTRATION_FLOW_ID", value = var.django_env.whatsapp_company_registration_flow_id },
        { name = "REDIS_URL", value = "redis://localhost:${var.redis_port}/0" }
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
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "app"
          awslogs-datetime-format = "%Y-%m-%d %H:%M:%S"
          awslogs-create-group  = "true"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:${var.app_port}/health/ || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 5
        startPeriod = 180
      }
      mountPoints = [
        {
          sourceVolume  = "app-data"
          containerPath = "/app/data"
          readOnly     = false
        }
      ]
      dependsOn = [
        {
          containerName = "redis"
          condition     = "HEALTHY"
        }
      ]
      user = "root"  # Temporarily run as root to fix permissions
    }
  ])

  volume {
    name = "app-data"
    efs_volume_configuration {
      file_system_id = var.efs_file_system_id
      root_directory = "/app"
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
      root_directory = "/redis"
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