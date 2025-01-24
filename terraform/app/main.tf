# ECR Repositories
resource "aws_ecr_repository" "redis" {
  name = "redis-${var.environment}"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  # Prevent accidental deletion and handle creation conflicts
  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      name,
      image_scanning_configuration,
      encryption_configuration
    ]
  }
}

resource "aws_ecr_repository" "app" {
  name = "vimbiso-${var.environment}"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  # Prevent accidental deletion and handle creation conflicts
  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      name,
      image_scanning_configuration,
      encryption_configuration
    ]
  }
}

# ECR Lifecycle Policy
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 30 untagged images"
        selection = {
          tagStatus   = "untagged"
          countType   = "imageCountMoreThan"
          countNumber = 30
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "vimbiso-cluster-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "app" {
  family                   = "vimbiso-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn           = aws_iam_role.ecs_task.arn

  ephemeral_storage {
    size_in_gib = 21  # Minimum size for Fargate
  }

  container_definitions = jsonencode([
    {
      name      = "redis-state"
      image     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/redis-${var.environment}:7.0-alpine"
      essential = true
      memory    = 384
      cpu       = 256
      portMappings = [
        {
          containerPort = 6379
          hostPort     = 6379
          protocol     = "tcp"
        }
      ]
      command = [
        "--protected-mode", "no",
        "--bind", "0.0.0.0",
        "--maxmemory", "356mb",
        "--maxmemory-policy", "allkeys-lru",
        "--save", "",
        "--appendonly", "no"
      ]
      ulimits = [
        {
          name = "nofile",
          softLimit = 65536,
          hardLimit = 65536
        }
      ]
      healthCheck = {
        command     = ["CMD-SHELL", "/usr/local/bin/redis-cli -h localhost ping"]
        interval    = 10
        timeout     = 5
        retries     = 3
        startPeriod = 15
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "redis",
          "awslogs-create-group"  = "true"
        }
      }
    },
    {
      name      = "app"
      image     = var.docker_image
      essential = true
      memory    = var.task_memory - 384  # Remaining memory after Redis (1664 MiB)
      cpu       = var.task_cpu - 256     # Remaining CPU after Redis
      command   = ["/app/start_app.sh"]
      user      = "appuser"  # Run as non-root user
      environment = [
        { name = "DJANGO_ENV", value = var.environment },
        { name = "DJANGO_SECRET", value = var.django_secret },
        { name = "MYCREDEX_APP_URL", value = var.mycredex_app_url },
        { name = "CLIENT_API_KEY", value = var.client_api_key },
        { name = "WHATSAPP_API_URL", value = var.whatsapp_api_url },
        { name = "WHATSAPP_ACCESS_TOKEN", value = var.whatsapp_access_token },
        { name = "WHATSAPP_PHONE_NUMBER_ID", value = var.whatsapp_phone_number_id },
        { name = "WHATSAPP_BUSINESS_ID", value = var.whatsapp_business_id },
        { name = "REDIS_URL", value = "redis://redis-state:6379/0" },
        { name = "ALLOWED_HOSTS", value = "*" },  # Allow all hosts since behind ALB
        { name = "DEBUG", value = "false" },
        { name = "APP_LOG_LEVEL", value = "INFO" },
        { name = "DJANGO_LOG_LEVEL", value = "INFO" }
      ]
      portMappings = [
        {
          containerPort = 8000
          hostPort     = 8000
          protocol     = "tcp"
        }
      ]
      dependsOn = [
        {
          containerName = "redis-state"
          condition     = "HEALTHY"
        }
      ]
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health/ || exit 1"]
        interval    = 10
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "app",
          "awslogs-create-group"  = "true"
        }
      }
    }
  ])

}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/vimbiso-${var.environment}"
  retention_in_days = 30
}

# ECS Service
resource "aws_ecs_service" "app" {
  name                               = "vimbiso-service-${var.environment}"
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.app.arn
  desired_count                     = var.min_capacity
  launch_type                       = "FARGATE"
  platform_version                  = "LATEST"
  health_check_grace_period_seconds = 120  # 2 minutes should be enough for initial startup
  enable_execute_command           = true  # Useful for debugging
  deployment_minimum_healthy_percent = 100  # Ensure no service interruption
  deployment_maximum_percent        = 200  # Allow double capacity for zero-downtime

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false  # Use NAT Gateway for internet access
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "app"
    container_port   = 8000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_controller {
    type = "ECS"
  }

  lifecycle {
    ignore_changes = [
      desired_count  # Allow autoscaling to manage count
    ]
  }
}

# Auto Scaling
resource "aws_appautoscaling_target" "app" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "vimbiso-cpu-autoscaling-${var.environment}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.app.resource_id
  scalable_dimension = aws_appautoscaling_target.app.scalable_dimension
  service_namespace  = aws_appautoscaling_target.app.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 80

    scale_in_cooldown  = 300  # 5 minutes to match grace period
    scale_out_cooldown = 60   # Quick scale out for responsiveness
  }
}

resource "aws_appautoscaling_policy" "memory" {
  name               = "vimbiso-memory-autoscaling-${var.environment}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.app.resource_id
  scalable_dimension = aws_appautoscaling_target.app.scalable_dimension
  service_namespace  = aws_appautoscaling_target.app.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value = 80

    scale_in_cooldown  = 300  # 5 minutes to match grace period
    scale_out_cooldown = 60   # Quick scale out for responsiveness
  }
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "vimbiso-cpu-high-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period             = "60"
  statistic          = "Average"
  threshold          = 80
  alarm_description  = "This metric monitors ECS CPU utilization"
  alarm_actions      = [aws_appautoscaling_policy.cpu.arn]

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.app.name
  }
}

resource "aws_cloudwatch_metric_alarm" "memory_high" {
  alarm_name          = "vimbiso-memory-high-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period             = "60"
  statistic          = "Average"
  threshold          = 80
  alarm_description  = "This metric monitors ECS memory utilization"
  alarm_actions      = [aws_appautoscaling_policy.memory.arn]

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.app.name
  }
}

# Get current region and account ID
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
