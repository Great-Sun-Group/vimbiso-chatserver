output "file_system_id" {
  description = "ID of the EFS file system"
  value       = aws_efs_file_system.main.id
}

output "file_system_arn" {
  description = "ARN of the EFS file system"
  value       = aws_efs_file_system.main.arn
}

output "mount_target_ids" {
  description = "List of mount target IDs"
  value       = [for mt in aws_efs_mount_target.main : mt.id]
}

output "mount_target_info" {
  description = "Mount target information for debugging"
  value = {
    file_system_id = aws_efs_file_system.main.id
    mount_targets  = {
      for k, v in aws_efs_mount_target.main : k => {
        id        = v.id
        subnet_id = v.subnet_id
        status    = v.mount_target_dns_name
      }
    }
  }
}

output "app_access_point_id" {
  description = "ID of the app data access point"
  value       = aws_efs_access_point.app_data.id
}

output "app_access_point_arn" {
  description = "ARN of the app data access point"
  value       = aws_efs_access_point.app_data.arn
}
