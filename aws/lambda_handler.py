"""
AWS Lambda Handler for SCBE-AETHERMOORE API
============================================

This module provides the Lambda entry point using Mangum to adapt
the FastAPI application for AWS Lambda + API Gateway.

Deployment:
- Package with dependencies into a Lambda deployment package
- Configure API Gateway HTTP API or REST API
- Set environment variables: SCBE_API_KEY, FIREBASE_CONFIG (optional)

Usage:
- Lambda handler: aws.lambda_handler.handler
- Memory: 512MB recommended (1024MB for heavy load)
- Timeout: 30 seconds recommended
"""

import os
import logging

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

# Import FastAPI app
try:
    from api.main import app
except ImportError:
    # Fallback for local testing
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from api.main import app

# Import Mangum for Lambda/API Gateway adapter
try:
    from mangum import Mangum
except ImportError:
    logger.error("Mangum not installed. Install with: pip install mangum")
    raise

# Create the Lambda handler
handler = Mangum(app, lifespan="off")


def lambda_handler(event, context):
    """
    AWS Lambda entry point.

    Supports:
    - API Gateway REST API (v1)
    - API Gateway HTTP API (v2)
    - Lambda Function URLs
    - Application Load Balancer
    """
    logger.info(f"Request: {event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', 'UNKNOWN'))} {event.get('path', event.get('rawPath', '/'))}")

    try:
        response = handler(event, context)
        logger.info(f"Response status: {response.get('statusCode', 'N/A')}")
        return response
    except Exception as e:
        logger.exception(f"Lambda handler error: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": '{"error": "Internal server error"}'
        }
