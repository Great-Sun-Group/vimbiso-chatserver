# First Deployment Guide

This guide outlines the complete process for deploying the VimbisoPay infrastructure from scratch.

## Initial Infrastructure Deployment

### Stage 1: Infrastructure Bootstrap

The initial deployment needs to use dummy values and a disabled container deployment to set up the core infrastructure:

1. The workflow automatically:
   - Creates S3 bucket for Terraform state
   - Creates DynamoDB table for state locking
   - Sets up ECR repositories
   - Uses dummy values for sensitive variables

2. In `terraform/main.tf`, both Route53 modules need to have DNS record creation disabled:
```hcl
module "route53_cert" {
  # ...
  create_dns_records = false  # Will be changed to true after NS records are configured
}

module "route53_dns" {
  # ...
  create_dns_records = false  # Will be changed to true after NS records are configured
}
```

3. The ful Docker build and deployment steps have to be commented out in the workflow:
```yaml
# Temporarily commented out for initial infrastructure deployment
# - name: Build and Push Docker Image
# - name: Wait for Deployment
```

### Stage 2: DNS Configuration

1. After initial deployment, get the NS records from the workflow output:
```bash
NS Records:
- ns-1234.awsdns-12.org
- ns-567.awsdns-34.com
...
```

2. In your domain registrar's DNS settings for the root domain (vimbisopay.africa):
   - Create NS records for the subdomain (e.g., dev.vimbiso-chatserver)
   - Point these NS records to the nameservers from Step 1
   - Wait for DNS propagation (typically 15-30 minutes)

### Stage 3: Enable DNS Validation

1. Update `terraform/main.tf`:
```hcl
module "route53_cert" {
  # ...
  create_dns_records = true  # Enable DNS validation
}

module "route53_dns" {
  # ...
  create_dns_records = true  # Enable DNS records
}
```

2. Run deployment to enable DNS validation
   - Certificate validation may take up to 30 minutes

## Full Application Deployment

### Stage 4: Configure Secrets

### Stage 5: Enable Application Deployment

1. In `.github/workflows/deploy.yml`, uncomment and enable:
   - Docker build and push step
   - Deployment wait step
   - Update TF_VAR_docker_image to use actual ECR image

2. Push changes to trigger full deployment with:
   - Real secrets and configuration
   - Application container deployment
   - Health check monitoring

The workflow will now:
1. Build and push Docker image to ECR
2. Deploy updated task definition with real image
3. Monitor deployment health:
   - Container health checks
   - Service stability
   - Task status
   - CloudWatch logs
