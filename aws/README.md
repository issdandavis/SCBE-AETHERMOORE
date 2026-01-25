# AWS Lambda Deployment

This directory contains the AWS Lambda deployment configuration for SCBE-AETHERMOORE API.

## Files

- `lambda_handler.py` - Lambda entry point using Mangum adapter
- `requirements-lambda.txt` - Minimal dependencies for Lambda package

## Prerequisites

1. AWS Account with Lambda access
2. IAM role with Lambda execution permissions
3. API Gateway (HTTP API or REST API) configured

## Required GitHub Secrets

Configure these in your repository settings:

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS IAM access key |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret key |

## Lambda Configuration

| Setting | Value |
|---------|-------|
| Runtime | Python 3.11 |
| Handler | `lambda_handler.lambda_handler` |
| Memory | 512 MB (recommended) |
| Timeout | 30 seconds |

## Environment Variables

Set these in Lambda configuration:

| Variable | Description | Required |
|----------|-------------|----------|
| `SCBE_API_KEY` | API key for authentication | Yes |
| `LOG_LEVEL` | Logging level (INFO, DEBUG) | No |

## Manual Deployment

```bash
# Install dependencies
pip install -r aws/requirements-lambda.txt -t ./package

# Copy app code
cp -r api package/
cp aws/lambda_handler.py package/

# Create zip
cd package && zip -r ../lambda.zip .

# Deploy
aws lambda update-function-code \
  --function-name scbe-aethermoore-api-production \
  --zip-file fileb://lambda.zip
```

## API Gateway Integration

Configure API Gateway to proxy all requests to Lambda:

- **Route:** `ANY /{proxy+}`
- **Integration:** Lambda function
- **Payload format:** 2.0 (HTTP API) or 1.0 (REST API)
