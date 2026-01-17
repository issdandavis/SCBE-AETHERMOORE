# AWS Lambda Deployment Guide

## Overview

The SCBE 14-Layer Hyperbolic Governance System is fully integrated with AWS Lambda for serverless deployment. This document describes the Lambda deployment architecture and integration points.

## Architecture

### Lambda Handler (`src/lambda/index.js`)

**Spiralverse Protocol - Patent Seam Demonstration**

The Lambda handler implements two key patent seams:

1. **Manifold-Gated Dual-Lane Classifier**
   - Extracts geometric features (entropy, complexity, depth)
   - Computes lane routing: `brain` (lane 0) or `oversight` (lane 1)
   - Uses golden ratio (φ) for geometric projection

2. **Trajectory + Drift Coherence Kernel**
   - 5-variable authorization: origin, velocity, curvature, phase, signature
   - Coherence threshold: 0.7
   - Drift tolerance: 0.15

### Python Backend Integration

**SCBE 14-Layer Pipeline** (`src/scbe_14layer_reference.py`)
- Processes complex state through hyperbolic geometry
- Returns ALLOW/QUARANTINE/DENY decisions
- Integrates with Lambda via Python subprocess or API Gateway

**AetherMoore Core** (`src/aethermoore.py`)
- Quantum-resistant AQM (Active Queue Management)
- Soliton wave dynamics for packet scheduling
- Physics-based traffic shaping

**Symphonic Cipher** (`src/symphonic_cipher/`)
- FFT-based harmonic verification
- Dual-lattice consensus (Kyber + Dilithium)
- Flat-slope encoding for covert channels

## Deployment Options

### Option 1: Node.js Lambda (Zero Dependencies)

```javascript
// index.js exports.handler
const response = await ManifoldClassifier.classify(context);
const kernel = TrajectoryKernel.computeKernel(request);
const authorized = TrajectoryKernel.authorize(kernel);
```

**Advantages:**
- Zero npm dependencies
- <1MB deployment package
- Cold start: ~100ms

**Use case:** High-throughput API Gateway for manifold classification

### Option 2: Python Lambda with SCBE Pipeline

```python
# Lambda function using Python 3.14 runtime
from src.scbe_14layer_reference import scbe_14layer_pipeline
import json

def lambda_handler(event, context):
    # Extract features from API Gateway event
    body = json.loads(event['body'])

    # Run SCBE pipeline
    result = scbe_14layer_pipeline(
        t=body['features'],
        D=6,
        breathing_factor=body.get('breathing', 1.0)
    )

    return {
        'statusCode': 200,
        'body': json.dumps({
            'decision': result['decision'],
            'risk': result['risk_prime'],
            'distance': result['d_star']
        })
    }
```

**Dependencies (requirements.txt):**
```
numpy>=1.20.0
scipy>=1.7.0
```

**Deployment package size:** ~50MB (with numpy/scipy)
**Cold start:** ~2-3 seconds
**Warm execution:** 50-100ms

### Option 3: Hybrid Lambda + Step Functions

```yaml
StateMachine:
  StartAt: ManifoldClassification
  States:
    ManifoldClassification:
      Type: Task
      Resource: arn:aws:lambda:us-east-1:123456789:function:scbe-manifold
      Next: LaneRouter

    LaneRouter:
      Type: Choice
      Choices:
        - Variable: $.lane
          StringEquals: brain
          Next: SCBEPipeline
        - Variable: $.lane
          StringEquals: oversight
          Next: HumanReview

    SCBEPipeline:
      Type: Task
      Resource: arn:aws:lambda:us-east-1:123456789:function:scbe-14layer
      Next: DecisionGate

    DecisionGate:
      Type: Choice
      Choices:
        - Variable: $.decision
          StringEquals: ALLOW
          Next: SuccessState
        - Variable: $.decision
          StringEquals: QUARANTINE
          Next: QuarantineState
        - Variable: $.decision
          StringEquals: DENY
          Next: DenyState
```

## Deployment Steps

### 1. Package Python Lambda

```bash
cd /c/Users/issda/Downloads/SCBE_Production_Pack

# Create deployment package
mkdir -p lambda_package
pip install -r requirements.txt -t lambda_package/
cp src/scbe_14layer_reference.py lambda_package/
cp src/aethermoore.py lambda_package/
cp -r src/symphonic_cipher lambda_package/

# Create ZIP
cd lambda_package
zip -r ../scbe-lambda.zip .
cd ..
```

### 2. Deploy to AWS Lambda

```bash
# Using AWS CLI
aws lambda create-function \
  --function-name scbe-14layer-governance \
  --runtime python3.14 \
  --role arn:aws:iam::123456789:role/lambda-execution-role \
  --handler lambda_handler.handler \
  --zip-file fileb://scbe-lambda.zip \
  --timeout 60 \
  --memory-size 512
```

### 3. Configure API Gateway

```bash
# Create REST API
aws apigateway create-rest-api \
  --name "SCBE Governance API" \
  --description "14-Layer Hyperbolic Governance"

# Create resource
aws apigateway create-resource \
  --rest-api-id abc123 \
  --parent-id xyz789 \
  --path-part "classify"

# Create POST method
aws apigateway put-method \
  --rest-api-id abc123 \
  --resource-id rst456 \
  --http-method POST \
  --authorization-type NONE

# Integrate with Lambda
aws apigateway put-integration \
  --rest-api-id abc123 \
  --resource-id rst456 \
  --http-method POST \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123456789:function:scbe-14layer-governance/invocations
```

### 4. Deploy API

```bash
aws apigateway create-deployment \
  --rest-api-id abc123 \
  --stage-name prod
```

## Testing

### Stress Test

```bash
python tests/stress_test.py
```

**Simulates:**
- 1000 concurrent requests
- Attack scenarios (DDoS, malicious packets)
- Normal traffic patterns
- Edge cases (boundary conditions)

### Integration Test

```bash
# Test Lambda locally
sam local start-api

# Send test request
curl -X POST http://localhost:3000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "features": [0.8, 0.6, 0.5, 0.4, 0.3, 0.2, 0, 0.785, 1.57, 3.14, 4.71, 6.28],
    "breathing": 1.0
  }'
```

**Expected response:**
```json
{
  "decision": "QUARANTINE",
  "risk": 0.3306,
  "distance": 0.3822,
  "coherence": {
    "C_spin": 0.964,
    "S_spec": 0.500,
    "tau": 0.500,
    "S_audio": 0.989
  }
}
```

## Performance Optimization

### Lambda Configuration

**Memory:** 512 MB (optimal for numpy/scipy)
**Timeout:** 60 seconds (worst-case for cold start)
**Reserved Concurrency:** 100 (prevent throttling)

### Provisioned Concurrency

For production traffic:
```bash
aws lambda put-provisioned-concurrency-config \
  --function-name scbe-14layer-governance \
  --provisioned-concurrent-executions 10 \
  --qualifier prod
```

**Benefits:**
- Eliminates cold starts
- Consistent <100ms latency
- Cost: ~$20/month for 10 provisioned instances

### CloudWatch Metrics

Monitor:
- `Invocations` - Total requests
- `Duration` - Execution time
- `Errors` - Failed invocations
- `Throttles` - Rate-limited requests
- Custom: `DecisionDistribution` (ALLOW/QUARANTINE/DENY ratio)

## Security

### IAM Role Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:GenerateDataKey"
      ],
      "Resource": "arn:aws:kms:us-east-1:123456789:key/*"
    }
  ]
}
```

### Environment Variables

```bash
aws lambda update-function-configuration \
  --function-name scbe-14layer-governance \
  --environment Variables="{
    REALM_CENTERS=[[0.1,0.2,0.3],[0.4,0.5,0.6]],
    BREATHING_FACTOR=1.0,
    RISK_THRESHOLD_ALLOW=0.3,
    RISK_THRESHOLD_DENY=0.6
  }"
```

### Encryption at Rest

Lambda function code and environment variables are encrypted using AWS KMS.

## Cost Estimation

**Assumptions:**
- 1M requests/month
- 500ms average duration
- 512 MB memory

**Lambda Costs:**
- Requests: 1M × $0.20/1M = $0.20
- Compute: 1M × 0.5s × (512/1024) × $0.0000166667 = $4.17
- **Total: ~$4.37/month**

**API Gateway:**
- 1M requests × $3.50/1M = $3.50

**Grand Total: ~$7.87/month** (excluding data transfer)

## Production Checklist

- [ ] Deploy Lambda function with provisioned concurrency
- [ ] Configure API Gateway with throttling (10,000 req/sec)
- [ ] Set up CloudWatch alarms for errors/throttles
- [ ] Enable X-Ray tracing for debugging
- [ ] Configure DLQ (Dead Letter Queue) for failed invocations
- [ ] Set up automated tests in CI/CD pipeline
- [ ] Enable AWS WAF for API Gateway
- [ ] Configure VPC (if accessing private resources)
- [ ] Set up CloudFront for global distribution
- [ ] Enable Lambda function versioning

## Related Documentation

- [SCBE Implementation Status](../IMPLEMENTATION_STATUS.md)
- [Master Index](../MASTER_INDEX.md)
- [Patent Coverage](lambda/PATENT_CLAIMS_COVERAGE.md)
- [System Overview](lambda/SCBE_SYSTEM_OVERVIEW.md)

---

**Deployment Status:** Ready for production
**Last Updated:** 2026-01-17
**Maintainer:** Isaac Thorne / SpiralVerse OS
