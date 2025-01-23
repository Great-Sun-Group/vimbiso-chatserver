# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/vimbiso-pay-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name = "vimbiso-pay-logbucket-${var.environment}"
  })
}

# ECS Cluster with Container Insights
resource "aws_ecs_cluster" "main" {
  name = "vimbiso-pay-cluster-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  configuration {
    execute_command_configuration {
      logging = "OVERRIDE"
      log_configuration {
        cloud_watch_log_group_name = aws_cloudwatch_log_group.app.name
      }
    }
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-cluster-${var.environment}"
  })
}

# Configure cluster capacity providers
resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight           = 1
    base             = 1
  }
}

# Service Discovery Namespace
resource "aws_service_discovery_private_dns_namespace" "main" {
  name        = "vimbiso-pay-${var.environment}.internal"
  description = "Internal service discovery namespace for VimbisoPay ${var.environment}"
  vpc         = var.vpc_id

  tags = merge(var.tags, {
    Name = "vimbiso-pay-discovery-${var.environment}"
  })
}

# Service Discovery Service
resource "aws_service_discovery_service" "app" {
  name = "app"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 3  # Allow more failures before marking unhealthy
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-app-discovery-${var.environment}"
  })
}

# Redis Service Discovery Service
resource "aws_service_discovery_service" "redis" {
  name = "redis"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 3  # Match app's failure threshold
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-redis-discovery-${var.environment}"
  })
}

# Add CloudWatch log metric filters for error monitoring
resource "aws_cloudwatch_log_metric_filter" "error_logs" {
  name           = "vimbiso-pay-errors-${var.environment}"
  pattern        = "[timestamp, level=ERROR, message]"
  log_group_name = aws_cloudwatch_log_group.app.name

  metric_transformation {
    name          = "ErrorCount"
    namespace     = "VimbisoPay/${var.environment}"
    value         = "1"
    default_value = "0"
  }
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "vimbiso-pay-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ClusterName", aws_ecs_cluster.main.name],
            [".", "MemoryUtilization", ".", "."]
          ]
          period = 300
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "ECS Cluster Utilization"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["VimbisoPay/${var.environment}", "ErrorCount"]
          ]
          period = 300
          stat   = "Sum"
          region = data.aws_region.current.name
          title  = "Application Errors"
        }
      }
    ]
  })
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "cluster_cpu_high" {
  alarm_name          = "vimbiso-pay-cluster-cpu-high-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ECS cluster CPU utilization"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-cluster-cpu-alarm-${var.environment}"
  })
}

resource "aws_cloudwatch_metric_alarm" "cluster_memory_high" {
  alarm_name          = "vimbiso-pay-cluster-memory-high-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ECS cluster memory utilization"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-cluster-memory-alarm-${var.environment}"
  })
}

# Add CloudWatch log metric filters for container insights
resource "aws_cloudwatch_log_metric_filter" "container_insights" {
  name           = "vimbiso-pay-container-insights-${var.environment}"
  pattern        = "[timestamp, type=ContainerInsights, ...]"
  log_group_name = aws_cloudwatch_log_group.app.name

  metric_transformation {
    name          = "ContainerInsightsEvents"
    namespace     = "VimbisoPay/${var.environment}"
    value         = "1"
    default_value = "0"
  }
}

# Get current region
data "aws_region" "current" {}
