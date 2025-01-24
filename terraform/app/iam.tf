# ECS Task Execution Role
resource "aws_iam_role" "ecs_execution" {
  name = "vimbiso-execution-role-${var.environment}"

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
}

# Allow execution role to create log streams and put logs
resource "aws_iam_role_policy" "ecs_execution_logs" {
  name = "vimbiso-execution-logs-${var.environment}"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = [
          "${aws_cloudwatch_log_group.app.arn}",
          "${aws_cloudwatch_log_group.app.arn}:*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role
resource "aws_iam_role" "ecs_task" {
  name = "vimbiso-task-role-${var.environment}"

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
}

# Allow ECS tasks to write logs and get task info
resource "aws_iam_role_policy" "ecs_task_permissions" {
  name = "vimbiso-task-permissions-${var.environment}"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:CreateLogGroup",
          "logs:DescribeLogStreams",
          "logs:GetLogEvents"
        ]
        Resource = [
          "${aws_cloudwatch_log_group.app.arn}",
          "${aws_cloudwatch_log_group.app.arn}:*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeTasks",
          "ecs:ListTasks"
        ]
        Resource = "*"
      }
    ]
  })
}

# Allow execution role to pull images and manage logs
resource "aws_iam_role_policy" "ecs_execution_permissions" {
  name = "vimbiso-execution-permissions-${var.environment}"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:CreateLogGroup",
          "logs:DescribeLogStreams"
        ]
        Resource = [
          "${aws_cloudwatch_log_group.app.arn}",
          "${aws_cloudwatch_log_group.app.arn}:*"
        ]
      }
    ]
  })
}
