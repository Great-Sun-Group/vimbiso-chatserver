# Deployment

## Manual Account Setup
1. Register a domain and create an AWS account (currently one domain per deployment).
2. Copy paste the contents of [vimbisochatserver-permissions.json](terraform/vimbisochatserver-permissions.json]) into an IAM policy, and create a group and deployment user attached.
3. Create an Access Key and Secret Access Key for the deployment user and save to applicable Github Environment.

## Infrastructure Deployment

1. Run the Deploy Infrastructure workflow with the Initial Deployment checkbox ticked to disable HTTPS and domain certification.
2. The workflow will output 4 nameserver records to be added to the domain.
3. Once nameserver records are added and propogated, run Deploy Infrastructure workflow with the Initial Deployment checkbox empty to enable HTTPS and domain certification.
4. Only run the Deploy Infrastructure workflow again when the terraform infrastructure requires updates.

## Infrastructure Deployment
The deployed environment is now ready for the Redis and App images and the new task definition to be pushed with the Deploy Application workflow, which is intended to be run regularly with each app update and deploy.
