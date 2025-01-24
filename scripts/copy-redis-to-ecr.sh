#!/bin/bash
set -e

# This script copies the official Redis image from Docker Hub to our ECR repository
# in af-south-1. This is needed because:
# 1. Cape Town region may have connectivity issues with Docker Hub
# 2. Having the image in ECR gives us more control and reliability
# 3. ECS tasks can pull from ECR more efficiently than from Docker Hub

# Configuration
REGION="af-south-1"
ENVIRONMENT=${1:-production}  # Use 'production' if no environment specified
REDIS_VERSION="7.0-alpine"    # Official Redis image tag from Docker Hub

# Get AWS account ID for ECR repository URL
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Step 1: Ensuring ECR repository exists..."
# Create ECR repository for Redis if it doesn't exist
aws ecr describe-repositories --repository-names redis-${ENVIRONMENT} --region ${REGION} || \
aws ecr create-repository \
    --repository-name redis-${ENVIRONMENT} \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256 \
    --region ${REGION}
echo "✓ ECR repository ready"

echo "Step 2: Authenticating with ECR..."
# Get ECR login token and authenticate Docker
aws ecr get-login-password --region ${REGION} | \
docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com
echo "✓ Authentication successful"

echo "Step 3: Pulling Redis image from Docker Hub..."
# Pull the official Redis image from Docker Hub's public registry
docker pull redis:${REDIS_VERSION}
echo "✓ Redis image pulled from Docker Hub"

echo "Step 4: Preparing image for ECR..."
# Tag the image for our ECR repository
docker tag redis:${REDIS_VERSION} ${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/redis-${ENVIRONMENT}:${REDIS_VERSION}
echo "✓ Image tagged for ECR"

echo "Step 5: Pushing to ECR in ${REGION}..."
# Push the image to our ECR repository
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/redis-${ENVIRONMENT}:${REDIS_VERSION}
echo "✓ Redis image successfully copied to ECR"

echo "Complete! Redis image is now available in ECR at:"
echo "${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/redis-${ENVIRONMENT}:${REDIS_VERSION}"
