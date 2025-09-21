# AWS ECR Deployment Script for NavigAI API (PowerShell)
# Make sure you have AWS CLI installed and configured

# Configuration
$AWS_REGION = "us-east-1"
$ECR_REPOSITORY_NAME = "navigai-api"
$IMAGE_TAG = "latest"

Write-Host "🚀 Deploying NavigAI API to AWS ECR..." -ForegroundColor Green

# Step 1: Create ECR repository (if it doesn't exist)
Write-Host "📦 Creating ECR repository..." -ForegroundColor Yellow
try {
    aws ecr create-repository --repository-name $ECR_REPOSITORY_NAME --region $AWS_REGION | Out-Null
    Write-Host "✅ Repository created successfully" -ForegroundColor Green
} catch {
    Write-Host "ℹ️ Repository already exists" -ForegroundColor Blue
}

# Step 2: Get the login token and login to ECR
Write-Host "🔐 Logging in to ECR..." -ForegroundColor Yellow
$ECR_LOGIN = aws ecr get-login-password --region $AWS_REGION
$ECR_ENDPOINT = (aws ecr describe-repositories --repository-names $ECR_REPOSITORY_NAME --region $AWS_REGION --query 'repositories[0].repositoryUri' --output text).Split('/')[0]
$ECR_LOGIN | docker login --username AWS --password-stdin $ECR_ENDPOINT

# Step 3: Get the ECR repository URI
$ECR_URI = aws ecr describe-repositories --repository-names $ECR_REPOSITORY_NAME --region $AWS_REGION --query 'repositories[0].repositoryUri' --output text
Write-Host "📍 ECR Repository URI: $ECR_URI" -ForegroundColor Cyan

# Step 4: Build the Docker image
Write-Host "🔨 Building Docker image..." -ForegroundColor Yellow
docker build -t ${ECR_REPOSITORY_NAME}:${IMAGE_TAG} .

# Step 5: Tag the image for ECR
Write-Host "🏷️ Tagging image for ECR..." -ForegroundColor Yellow
docker tag ${ECR_REPOSITORY_NAME}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}

# Step 6: Push the image to ECR
Write-Host "⬆️ Pushing image to ECR..." -ForegroundColor Yellow
docker push ${ECR_URI}:${IMAGE_TAG}

Write-Host "✅ Successfully pushed to ECR!" -ForegroundColor Green
Write-Host "📍 Image URI: ${ECR_URI}:${IMAGE_TAG}" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎯 Next steps:" -ForegroundColor Yellow
Write-Host "1. Use this image URI in ECS, App Runner, or EKS"
Write-Host "2. Or run locally: docker run -p 8080:8080 ${ECR_URI}:${IMAGE_TAG}"