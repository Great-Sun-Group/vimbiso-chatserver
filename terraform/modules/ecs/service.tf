# ECS Service
resource "aws_ecs_service" "app" {
  name                               = "vimbiso-pay-service-${var.environment}"
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.app.arn
  desired_count                     = var.min_capacity
  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent        = 200
  scheduling_strategy               = "REPLICA"
  force_new_deployment             = true
  health_check_grace_period_seconds = 120

  # Disable automatic rollback to prevent deployment loops
  deployment_circuit_breaker {
    enable   = true
    rollback = false
  }

  deployment_controller {
    type = "ECS"
  }

  network_configuration {
    security_groups  = [var.ecs_tasks_security_group_id]
    subnets         = var.private_subnet_ids
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "vimbiso-pay-${var.environment}"
    container_port   = var.app_port
  }

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight           = 100
    base             = 1
  }

  service_registries {
    registry_arn = aws_service_discovery_service.app.arn
  }

  # Ignore changes that are managed by the deployment workflow
  lifecycle {
    ignore_changes = [
      desired_count,
      task_definition,
      capacity_provider_strategy,
      health_check_grace_period_seconds
    ]
  }

  depends_on = [
    aws_service_discovery_service.app,
    aws_ecs_cluster.main
  ]

  tags = merge(var.tags, {
    Name = "vimbiso-pay-service-${var.environment}"
  })
}