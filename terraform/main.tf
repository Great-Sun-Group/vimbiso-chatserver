# Networking Module
module "networking" {
  source = "./modules/networking"

  environment = var.environment
  vpc_cidr    = local.current_env.vpc_cidr
  az_count    = local.current_env.az_count
  public_subnet_cidrs = [
    for i in range(local.current_env.az_count) :
    cidrsubnet(local.current_env.vpc_cidr, 8, local.current_env.az_count + i)
  ]
  tags = local.common_tags
}

# Route53 Certificate Module
module "route53_cert" {
  source = "./modules/route53_cert"

  environment  = var.environment
  domain_name = "${local.current_env.subdomain}.${local.current_env.domain_base}"
  tags        = local.common_tags
}

# Load Balancer Module
module "loadbalancer" {
  source = "./modules/loadbalancer"

  environment            = var.environment
  vpc_id                = module.networking.vpc_id
  public_subnet_ids     = module.networking.public_subnet_ids
  alb_security_group_id = module.networking.alb_security_group_id
  certificate_arn       = module.route53_cert.certificate_arn
  health_check_path     = "/health/"
  health_check_port     = 8000
  deregistration_delay  = 60
  tags                  = local.common_tags

  depends_on = [module.networking, module.route53_cert]
}

# EFS Module
module "efs" {
  source = "./modules/efs"

  environment            = var.environment
  private_subnet_ids     = module.networking.private_subnet_ids
  efs_security_group_id  = module.networking.efs_security_group_id
  encrypted             = true
  performance_mode      = "generalPurpose"
  throughput_mode       = "bursting"
  transition_to_ia      = "AFTER_30_DAYS"
  enable_backup         = true
  backup_retention_days = 30
  tags                  = local.common_tags

  depends_on = [module.networking]
}

# IAM Module
module "iam" {
  source = "./modules/iam"

  environment              = var.environment
  efs_file_system_arn     = module.efs.file_system_arn
  app_access_point_arn    = module.efs.app_access_point_arn
  redis_state_access_point_arn = module.efs.redis_state_access_point_arn
  cloudwatch_log_group_arn = "arn:aws:logs:${local.current_env.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/vimbiso-pay-${var.environment}:*"
  region                  = local.current_env.aws_region
  account_id              = data.aws_caller_identity.current.account_id
  tags                    = local.common_tags

  depends_on = [module.efs]
}

# ECR Module
module "ecr" {
  source = "./modules/ecr"

  environment           = var.environment
  scan_on_push         = true
  image_retention_count = 20
  force_delete         = var.environment != "production"
  encryption_type      = "AES256"
  image_tag_mutability = "MUTABLE"
  tags                 = local.common_tags
}

# ECS Module
module "ecs" {
  source = "./modules/ecs"

  environment                = var.environment
  vpc_id                     = module.networking.vpc_id
  private_subnet_ids         = module.networking.private_subnet_ids
  ecs_tasks_security_group_id = module.networking.ecs_tasks_security_group_id
  target_group_arn           = module.loadbalancer.target_group_arn
  alb_arn                    = module.loadbalancer.alb_arn
  execution_role_arn         = module.iam.ecs_execution_role_arn
  task_role_arn             = module.iam.ecs_task_role_arn
  docker_image              = var.docker_image
  efs_file_system_id        = module.efs.file_system_id
  app_access_point_id       = module.efs.app_access_point_id
  redis_state_access_point_id = module.efs.redis_state_access_point_id
  efs_mount_targets         = module.efs.mount_target_ids
  task_cpu                  = local.current_env.ecs_task.cpu
  task_memory               = local.current_env.ecs_task.memory
  min_capacity              = local.current_env.autoscaling.min_capacity
  max_capacity              = local.current_env.autoscaling.max_capacity
  cpu_threshold             = local.current_env.autoscaling.cpu_threshold
  memory_threshold          = local.current_env.autoscaling.memory_threshold
  log_retention_days        = 30
  service_discovery_ttl     = 10
  aws_account_id           = data.aws_caller_identity.current.account_id
  aws_region               = local.current_env.aws_region

  django_env = {
    django_secret                         = var.django_secret
    debug                                = var.debug
    mycredex_app_url                     = var.mycredex_app_url
    client_api_key                       = var.client_api_key
    whatsapp_api_url                     = var.whatsapp_api_url
    whatsapp_access_token                = var.whatsapp_access_token
    whatsapp_phone_number_id             = var.whatsapp_phone_number_id
    whatsapp_business_id                 = var.whatsapp_business_id
  }

  tags = local.common_tags

  depends_on = [
    module.networking,
    module.loadbalancer,
    module.efs,
    module.iam
  ]
}

# Health Checks Module
module "health_checks" {
  source = "./modules/health_checks"

  alb_dns_name      = module.loadbalancer.alb_dns_name
  health_check_path = "/health/"

  depends_on = [module.loadbalancer]
}

# Route53 DNS Module - After health checks are ready
module "route53_dns" {
  source = "./modules/route53_dns"

  environment        = var.environment
  domain_name       = "${local.current_env.subdomain}.${local.current_env.domain_base}"
  create_dns_records = true
  alb_dns_name      = module.loadbalancer.alb_dns_name
  alb_zone_id       = module.loadbalancer.alb_zone_id
  health_check_id   = module.health_checks.health_check_id
  tags             = local.common_tags

  depends_on = [module.health_checks]
}
