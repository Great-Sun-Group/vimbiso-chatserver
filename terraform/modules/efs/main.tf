# EFS File System
resource "aws_efs_file_system" "main" {
  creation_token = "vimbiso-pay-efs-${var.environment}"
  encrypted      = var.encrypted

  performance_mode = var.performance_mode
  throughput_mode = var.throughput_mode

  lifecycle_policy {
    transition_to_ia = var.transition_to_ia
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-efs-${var.environment}"
  })
}

# Backup Policy
resource "aws_efs_backup_policy" "main" {
  count = var.enable_backup ? 1 : 0

  file_system_id = aws_efs_file_system.main.id

  backup_policy {
    status = "ENABLED"
  }
}

# App Data Access Point
resource "aws_efs_access_point" "app_data" {
  file_system_id = aws_efs_file_system.main.id

  posix_user {
    gid = 10001  # Match container's appuser GID
    uid = 10001  # Match container's appuser UID
  }

  root_directory {
    path = "/app/data"
    creation_info {
      owner_gid   = 10001  # Match container's appuser GID
      owner_uid   = 10001  # Match container's appuser UID
      permissions = "755"
    }
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-app-ap-${var.environment}"
  })
}

# Redis State Access Point
resource "aws_efs_access_point" "redis_state" {
  file_system_id = aws_efs_file_system.main.id

  posix_user {
    gid = 999  # Alpine Redis group
    uid = 999  # Alpine Redis user
  }

  root_directory {
    path = "/redis/state"  # Dedicated state directory
    creation_info {
      owner_gid   = 999  # Alpine Redis group
      owner_uid   = 999  # Alpine Redis user
      permissions = "755"
    }
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-redis-state-ap-${var.environment}"
  })
}

# Get existing mount targets
data "aws_efs_mount_target" "existing" {
  count = length(var.private_subnet_ids)

  mount_target_id = tolist(data.aws_efs_mount_targets.all[0].mount_targets)[count.index].mount_target_id

  depends_on = [aws_efs_file_system.main]
}

data "aws_efs_mount_targets" "all" {
  count = 1
  file_system_id = aws_efs_file_system.main.id
}

locals {
  # Get list of subnets that don't have mount targets
  existing_subnet_ids = try(
    toset([for mt in data.aws_efs_mount_targets.all[0].mount_targets : mt.subnet_id]),
    toset([])
  )
  subnets_needing_mounts = toset(var.private_subnet_ids) - local.existing_subnet_ids
}

# Mount Targets (only for subnets without existing targets)
resource "aws_efs_mount_target" "main" {
  for_each = local.subnets_needing_mounts

  file_system_id  = aws_efs_file_system.main.id
  subnet_id       = each.value
  security_groups = [var.efs_security_group_id]
}

# EFS File System Policy
resource "aws_efs_file_system_policy" "main" {
  file_system_id = aws_efs_file_system.main.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RequireEncryptedTransport"
        Effect = "Deny"
        Principal = {
          AWS = "*"
        }
        Action = "*"
        Resource = aws_efs_file_system.main.arn
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid    = "AllowAccessViaAccessPoint"
        Effect = "Allow"
        Principal = {
          AWS = "*"
        }
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientRootAccess"
        ]
        Resource = aws_efs_file_system.main.arn
        Condition = {
          StringEquals = {
            "elasticfilesystem:AccessPointArn": [
              aws_efs_access_point.app_data.arn,
              aws_efs_access_point.redis_state.arn
            ]
          }
        }
      }
    ]
  })
}
