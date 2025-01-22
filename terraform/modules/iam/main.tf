# Permission boundary policy
resource "aws_iam_policy" "permission_boundary" {
  name = "vimbiso-pay-permission-boundary-${var.environment}"
  path = "/"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:CreateLogGroup",
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientRootAccess",
          "elasticfilesystem:DescribeFileSystems",
          "elasticfilesystem:DescribeMountTargets",
          "elasticfilesystem:DescribeAccessPoints"
        ]
        Resource = "*"
      },
      {
        Effect = "Deny"
        Action = [
          "ssm:DeleteParameter",
          "ssm:DeleteParameters",
          "ssm:PutParameter"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "vimbiso-pay-permission-boundary-${var.environment}"
  })
}

# ECS task execution role
resource "aws_iam_role" "ecs_execution_role" {
  name                 = "vimbiso-pay-ecs-execution-${var.environment}"
  permissions_boundary = aws_iam_policy.permission_boundary.arn

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "vimbiso-pay-ecs-execution-${var.environment}"
  })
}

# Attach the AWS managed policy for ECS task execution
resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Additional permissions for ECS execution role
resource "aws_iam_role_policy" "ecs_execution_extra" {
  name = "vimbiso-pay-ecs-execution-extra-${var.environment}"
  role = aws_iam_role.ecs_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:CreateLogGroup",
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientRootAccess",
          "elasticfilesystem:DescribeFileSystems",
          "elasticfilesystem:DescribeMountTargets",
          "elasticfilesystem:DescribeAccessPoints"
        ]
        Resource = "*"
      }
    ]
  })
}

# ECS task role
resource "aws_iam_role" "ecs_task_role" {
  name                 = "vimbiso-pay-ecs-task-${var.environment}"
  permissions_boundary = aws_iam_policy.permission_boundary.arn

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "vimbiso-pay-ecs-task-${var.environment}"
  })
}

# CloudWatch permissions for task role
resource "aws_iam_role_policy" "ecs_task_cloudwatch" {
  name = "vimbiso-pay-ecs-task-cloudwatch-${var.environment}"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:CreateLogGroup"
        ]
        Resource = "${var.cloudwatch_log_group_arn}:*"
      }
    ]
  })
}

# EFS permissions for task role
resource "aws_iam_role_policy" "ecs_task_efs" {
  name = "vimbiso-pay-ecs-task-efs-${var.environment}"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientRootAccess",
          "elasticfilesystem:DescribeFileSystems",
          "elasticfilesystem:DescribeMountTargets",
          "elasticfilesystem:DescribeAccessPoints"
        ]
        Resource = [
          var.efs_file_system_arn,
          "${var.efs_file_system_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite"
        ]
        Resource = [
          var.app_access_point_arn
        ]
      }
    ]
  })
}

# KMS permissions
resource "aws_iam_role_policy" "kms" {
  name = "vimbiso-pay-kms-${var.environment}"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = [
              "ecs.${var.region}.amazonaws.com",
              "ssm.${var.region}.amazonaws.com"
            ]
          }
        }
      }
    ]
  })
}

# ECS service linked role
resource "aws_iam_service_linked_role" "ecs" {
  aws_service_name = "ecs.amazonaws.com"
  description      = "Service-linked role for ECS"

  tags = merge(var.tags, {
    Name = "vimbiso-pay-ecs-service-linked-${var.environment}"
  })
}
