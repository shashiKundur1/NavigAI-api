#!/bin/bash

# AWS ECR Deployment Script for NavigAI API
# Make sure you have AWS CLI installed and configured

# Configuration
AWS_REGION="us-east-1"
ECR_REPOSITORY_NAME="navigai-api"
IMAGE_TAG="latest"

echo "🚀 Deploying NavigAI API to AWS ECR..."

# Step 1: Create ECR repository (if it doesn't exist)
echo "📦 Creating ECR repository..."
aws ecr create-repository --repository-name $ECR_REPOSITORY_NAME --region $AWS_REGION 2>/dev/null || echo "Repository already exists"

# Step 2: Get the login token and login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $(aws ecr describe-repositories --repository-names $ECR_REPOSITORY_NAME --region $AWS_REGION --query 'repositories[0].repositoryUri' --output text | cut -d'/' -f1)

# Step 3: Get the ECR repository URI
ECR_URI=$(aws ecr describe-repositories --repository-names $ECR_REPOSITORY_NAME --region $AWS_REGION --query 'repositories[0].repositoryUri' --output text)
echo "📍 ECR Repository URI: $ECR_URI"

# Step 4: Build the Docker image
echo "🔨 Building Docker image..."
docker build -t $ECR_REPOSITORY_NAME:$IMAGE_TAG .

# Step 5: Tag the image for ECR
echo "🏷️ Tagging image for ECR..."
docker tag $ECR_REPOSITORY_NAME:$IMAGE_TAG $ECR_URI:$IMAGE_TAG

# Step 6: Push the image to ECR
echo "⬆️ Pushing image to ECR..."
docker push $ECR_URI:$IMAGE_TAG

echo "✅ Successfully pushed to ECR!"
echo "📍 Image URI: $ECR_URI:$IMAGE_TAG"
echo ""
echo "🎯 Next steps:"
echo "1. Use this image URI in ECS, App Runner, or EKS"
echo "2. Or run locally: docker run -p 8080:8080 $ECR_URI:$IMAGE_TAG"