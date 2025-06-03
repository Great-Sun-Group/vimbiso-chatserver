# Deployment

## Environment Setup
The deployment infrastructure is designed to support separate production and development environments, each with its own:
- AWS account
- Domain name (e.g., vimbisopay.africa for production, dailycredcoin.com for development)
- Route 53 hosted zone
- Infrastructure resources

This separation ensures that changes to one environment do not affect the other. For example, updating nameservers for the production domain has no impact on the development environment.

## Manual Account Setup
1. Register a domain and create an AWS account for each environment (production and development).
2. Copy paste the contents of [vimbisochatserver-permissions.json](terraform/vimbisochatserver-permissions.json]) into an IAM policy, and create a group and deployment user attached in each AWS account.
3. Create an Access Key and Secret Access Key for each deployment user and save to the applicable Github Environment.
4. In the AWS console for each account, create a Route 53 hosted zone for the respective domain (e.g., vimbisopay.africa for production, dailycredcoin.com for development). These will be referenced by the terraform configuration during deployment.

## Infrastructure Deployment

After creating the Route 53 hosted zone in the AWS console, once the nameserver records are added and propagated (this may take up to 48 hours), run the Deploy Infrastructure workflow.

## Application Deployment
The deployed environment is now ready for the Redis and App images and the new task definition to be pushed with the Deploy Application workflow, which is intended to be run regularly with each app update and deploy.
