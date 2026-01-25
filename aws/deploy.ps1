# SCBE-AETHERMOORE AWS Lambda Deployment Script
# Run: .\aws\deploy.ps1

param(
    [string]$Environment = "production",
    [string]$Region = "us-west-2"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "SCBE-AETHERMOORE Lambda Deployment" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Configuration
$FunctionName = "scbe-aethermoore-api-$Environment"
$ZipFile = "scbe-lambda.zip"

# Check AWS CLI
try {
    aws --version | Out-Null
} catch {
    Write-Host "ERROR: AWS CLI not found. Please install it first." -ForegroundColor Red
    exit 1
}

# Get AWS Account ID
$AccountId = aws sts get-caller-identity --query Account --output text
Write-Host "AWS Account: $AccountId" -ForegroundColor Green
Write-Host "Region: $Region" -ForegroundColor Green

# Create deployment package
Write-Host "`nCreating deployment package..." -ForegroundColor Yellow

# Remove old zip if exists
if (Test-Path $ZipFile) {
    Remove-Item $ZipFile -Force
}

# Create zip with required files
$FilesToInclude = @(
    "api\main.py",
    "api\persistence.py",
    "api\__init__.py",
    "aws\lambda_handler.py",
    "src\"
)

# Use PowerShell Compress-Archive
$TempDir = "lambda_package_temp"
if (Test-Path $TempDir) {
    Remove-Item $TempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $TempDir | Out-Null

# Copy files
Copy-Item "api" -Destination "$TempDir\api" -Recurse -ErrorAction SilentlyContinue
Copy-Item "src" -Destination "$TempDir\src" -Recurse -ErrorAction SilentlyContinue
Copy-Item "aws\lambda_handler.py" -Destination "$TempDir\lambda_handler.py" -ErrorAction SilentlyContinue

# Create requirements for Lambda layer
$LambdaRequirements = @"
fastapi==0.109.0
pydantic==2.5.3
mangum==0.17.0
"@
$LambdaRequirements | Out-File -FilePath "$TempDir\requirements.txt" -Encoding UTF8

Compress-Archive -Path "$TempDir\*" -DestinationPath $ZipFile -Force
Remove-Item $TempDir -Recurse -Force

Write-Host "Package created: $ZipFile" -ForegroundColor Green

# Check if function exists
$FunctionExists = $false
try {
    aws lambda get-function --function-name $FunctionName --region $Region 2>$null | Out-Null
    $FunctionExists = $true
    Write-Host "Function exists, updating..." -ForegroundColor Yellow
} catch {
    Write-Host "Function does not exist, creating..." -ForegroundColor Yellow
}

# Create or get IAM role
$RoleName = "scbe-lambda-execution-role"
$RoleArn = "arn:aws:iam::${AccountId}:role/$RoleName"

try {
    aws iam get-role --role-name $RoleName --region $Region 2>$null | Out-Null
    Write-Host "Using existing IAM role: $RoleName" -ForegroundColor Green
} catch {
    Write-Host "Creating IAM role..." -ForegroundColor Yellow

    $TrustPolicy = @"
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "lambda.amazonaws.com"},
        "Action": "sts:AssumeRole"
    }]
}
"@
    $TrustPolicy | Out-File -FilePath "trust-policy.json" -Encoding UTF8

    aws iam create-role `
        --role-name $RoleName `
        --assume-role-policy-document file://trust-policy.json `
        --region $Region

    aws iam attach-role-policy `
        --role-name $RoleName `
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    Remove-Item "trust-policy.json" -Force

    # Wait for role to propagate
    Write-Host "Waiting for role to propagate..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
}

if ($FunctionExists) {
    # Update existing function
    aws lambda update-function-code `
        --function-name $FunctionName `
        --zip-file fileb://$ZipFile `
        --region $Region

    Write-Host "Function code updated!" -ForegroundColor Green
} else {
    # Create new function
    aws lambda create-function `
        --function-name $FunctionName `
        --runtime python3.11 `
        --handler lambda_handler.handler `
        --role $RoleArn `
        --zip-file fileb://$ZipFile `
        --timeout 30 `
        --memory-size 512 `
        --environment "Variables={SCBE_ENV=$Environment,SCBE_LOG_LEVEL=INFO}" `
        --region $Region

    Write-Host "Function created!" -ForegroundColor Green

    # Wait for function to be active
    Write-Host "Waiting for function to be active..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
}

# Create or get API Gateway
$ApiName = "scbe-aethermoore-api"
Write-Host "`nSetting up API Gateway..." -ForegroundColor Yellow

# Check for existing HTTP API
$ExistingApis = aws apigatewayv2 get-apis --region $Region | ConvertFrom-Json
$Api = $ExistingApis.Items | Where-Object { $_.Name -eq $ApiName }

if ($Api) {
    $ApiId = $Api.ApiId
    Write-Host "Using existing API: $ApiId" -ForegroundColor Green
} else {
    # Create HTTP API
    $CreateResult = aws apigatewayv2 create-api `
        --name $ApiName `
        --protocol-type HTTP `
        --cors-configuration "AllowOrigins=*,AllowMethods=*,AllowHeaders=*" `
        --region $Region | ConvertFrom-Json

    $ApiId = $CreateResult.ApiId
    Write-Host "Created API: $ApiId" -ForegroundColor Green

    # Create Lambda integration
    $FunctionArn = "arn:aws:lambda:${Region}:${AccountId}:function:$FunctionName"

    $IntegrationResult = aws apigatewayv2 create-integration `
        --api-id $ApiId `
        --integration-type AWS_PROXY `
        --integration-uri $FunctionArn `
        --payload-format-version "2.0" `
        --region $Region | ConvertFrom-Json

    $IntegrationId = $IntegrationResult.IntegrationId

    # Create route for all methods
    aws apigatewayv2 create-route `
        --api-id $ApiId `
        --route-key "`$default" `
        --target "integrations/$IntegrationId" `
        --region $Region | Out-Null

    # Create stage
    aws apigatewayv2 create-stage `
        --api-id $ApiId `
        --stage-name $Environment `
        --auto-deploy `
        --region $Region | Out-Null

    # Add Lambda permission
    aws lambda add-permission `
        --function-name $FunctionName `
        --statement-id "apigateway-invoke-$ApiId" `
        --action lambda:InvokeFunction `
        --principal apigateway.amazonaws.com `
        --source-arn "arn:aws:execute-api:${Region}:${AccountId}:${ApiId}/*" `
        --region $Region 2>$null

    Write-Host "API Gateway configured!" -ForegroundColor Green
}

# Get API URL
$ApiUrl = "https://$ApiId.execute-api.$Region.amazonaws.com/$Environment"

# Clean up
Remove-Item $ZipFile -Force -ErrorAction SilentlyContinue

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "SCBE API URL: $ApiUrl" -ForegroundColor White
Write-Host ""
Write-Host "Test endpoints:" -ForegroundColor Yellow
Write-Host "  Health:    $ApiUrl/v1/health"
Write-Host "  Authorize: $ApiUrl/v1/authorize"
Write-Host "  Docs:      $ApiUrl/docs"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Set SCBE_API_KEY environment variable in Lambda"
Write-Host "  2. Test with: curl $ApiUrl/v1/health"
Write-Host "============================================" -ForegroundColor Cyan
