"""
AWS Lambda Handler for SCBE-AETHERMOORE API

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
SCBE-AETHERMOORE Lambda Handler

AWS Lambda entry point for the SCBE FastAPI application.
Uses Mangum to wrap FastAPI for Lambda compatibility.
"""

import json
import logging
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scbe-lambda")

# Try to import Mangum (FastAPI -> Lambda adapter)
try:
    from mangum import Mangum
    MANGUM_AVAILABLE = True
except ImportError:
    MANGUM_AVAILABLE = False
    logger.warning("Mangum not available, using fallback handler")

# Import FastAPI app
try:
    from api.main import app as fastapi_app
    FASTAPI_AVAILABLE = True
except ImportError as e:
    FASTAPI_AVAILABLE = False
    logger.error(f"Failed to import FastAPI app: {e}")

# Create Mangum handler if available
if MANGUM_AVAILABLE and FASTAPI_AVAILABLE:
    handler = Mangum(fastapi_app, lifespan="off")
else:
    # Fallback handler for basic functionality
    def handler(event, context):
        """
        Fallback Lambda handler when Mangum is not available.
        Implements core SCBE functionality directly.
        """
        import hashlib
        import math
        import time
        import uuid
        from datetime import datetime, timedelta

        # Parse request
        http_method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method', 'GET')
        raw_path = event.get('path') or event.get('rawPath') or event.get('requestContext', {}).get('http', {}).get('path', '/')

        # Strip stage prefix (e.g., /production/, /staging/, /dev/)
        path = raw_path
        stage_prefixes = ['/production', '/staging', '/dev', '/prod']
        for prefix in stage_prefixes:
            if path.startswith(prefix):
                path = path[len(prefix):]
                if not path:
                    path = '/'
                break

        # Parse body
        body = event.get('body', '{}')
        if isinstance(body, str):
            try:
                body = json.loads(body) if body else {}
            except json.JSONDecodeError:
                body = {}

        # Get API key from headers
        headers = event.get('headers', {})
        api_key = headers.get('x-api-key') or headers.get('X-API-Key')

        # Validate API key
        valid_keys = os.getenv('SCBE_API_KEY', '').split(',')
        valid_keys = [k.strip() for k in valid_keys if k.strip()]

        def response(status_code, body_dict):
            return {
                'statusCode': status_code,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': '*',
                    'Access-Control-Allow-Methods': '*'
                },
                'body': json.dumps(body_dict)
            }

        # Handle CORS preflight
        if http_method == 'OPTIONS':
            return response(200, {'status': 'ok'})

        # Health check (no auth required)
        if path == '/v1/health' or path == '/health':
            return response(200, {
                'status': 'healthy',
                'version': '1.0.0',
                'framework': 'SCBE-AETHERMOORE',
                'layers': 14,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'runtime': 'AWS Lambda',
                'checks': {
                    'api': 'ok',
                    'pipeline': 'ok'
                }
            })

        # Root endpoint
        if path == '/' and http_method == 'GET':
            return response(200, {
                'name': 'SCBE-AETHERMOORE API',
                'version': '1.0.0',
                'description': 'Quantum-Resistant AI Agent Governance',
                'docs': '/docs',
                'health': '/v1/health',
                'endpoints': {
                    'authorize': 'POST /v1/authorize',
                    'agents': 'POST /v1/agents',
                    'consensus': 'POST /v1/consensus',
                    'audit': 'GET /v1/audit/{id}'
                },
                'constants': {
                    'PHI_AETHER': 1.3782407725,
                    'LAMBDA_ISAAC': 3.9270509831,
                    'OMEGA_SPIRAL': 1.4832588477,
                    'ALPHA_ABH': 3.1180339887
                }
            })

        # API key required for other endpoints
        if not api_key or api_key not in valid_keys:
            return response(401, {'error': 'Invalid or missing API key'})

        # SCBE Core functions
        def hyperbolic_distance(p1, p2):
            norm1_sq = sum(x**2 for x in p1)
            norm2_sq = sum(x**2 for x in p2)
            diff_sq = sum((a - b)**2 for a, b in zip(p1, p2))
            norm1_sq = min(norm1_sq, 0.9999)
            norm2_sq = min(norm2_sq, 0.9999)
            numerator = 2 * diff_sq
            denominator = (1 - norm1_sq) * (1 - norm2_sq)
            if denominator <= 0:
                return float('inf')
            delta = numerator / denominator
            return math.acosh(1 + delta) if delta >= 0 else 0.0

        def agent_to_6d(agent_id, action, target, trust):
            seed = hashlib.sha256(f"{agent_id}:{action}:{target}".encode()).digest()
            coords = []
            for i in range(6):
                val = seed[i] / 255.0
                radius = (1 - trust) * 0.8 + 0.1
                coords.append(val * radius - radius/2)
            return tuple(coords)

        def scbe_pipeline(agent_id, action, target, trust_score, sensitivity=0.5):
            explanation = {"layers": {}}

            # Layers 1-4: Context Embedding
            position = agent_to_6d(agent_id, action, target, trust_score)
            explanation["layers"]["L1-4"] = "6D position computed"

            # Layers 5-7: Hyperbolic Geometry
            safe_center = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            distance = hyperbolic_distance(position, safe_center)
            explanation["layers"]["L5-7"] = f"Distance: {distance:.3f}"

            # Layer 8: Realm Trust
            realm_trust = trust_score * (1 - sensitivity * 0.5)
            explanation["layers"]["L8"] = f"Realm trust: {realm_trust:.2f}"

            # Layers 9-10: Spectral/Spin Coherence
            coherence = 1.0 - abs(math.sin(distance * math.pi))
            explanation["layers"]["L9-10"] = f"Coherence: {coherence:.2f}"

            # Layer 11: Temporal Pattern
            temporal_score = trust_score * 0.9 + 0.1
            explanation["layers"]["L11"] = f"Temporal: {temporal_score:.2f}"

            # Layer 12: Harmonic Scaling H(d,R) = R^(d²)
            R = 1.5  # Perfect Fifth
            d = int(sensitivity * 3) + 1
            H = R ** (d * d)  # H(d,R) = R^(d²)
            risk_factor = (1 - realm_trust) * sensitivity * 0.5
            explanation["layers"]["L12"] = f"H(d={d},R={R})={H:.2f}, risk: {risk_factor:.2f}"

            # Layer 13: Final Decision
            final_score = (realm_trust * 0.6 + coherence * 0.2 + temporal_score * 0.2) - risk_factor
            explanation["layers"]["L13"] = f"Score: {final_score:.3f}"

            # Layer 14: Telemetry
            explanation["layers"]["L14"] = f"Logged at {time.time():.0f}"

            # Decision
            if final_score > 0.6:
                decision = "ALLOW"
            elif final_score > 0.3:
                decision = "QUARANTINE"
            else:
                decision = "DENY"

            explanation["trust_score"] = trust_score
            explanation["distance"] = round(distance, 3)
            explanation["harmonic_amplification"] = round(H, 2)

            return decision, final_score, explanation

        # POST /v1/authorize
        if path == '/v1/authorize' and http_method == 'POST':
            agent_id = body.get('agent_id', 'unknown')
            action = body.get('action', 'READ')
            target = body.get('target', 'default')
            context = body.get('context', {})
            sensitivity = context.get('sensitivity', 0.5)
            trust_score = context.get('trust_score', 0.5)

            decision, score, explanation = scbe_pipeline(
                agent_id, action, target, trust_score, sensitivity
            )

            decision_id = f"dec_{uuid.uuid4().hex[:12]}"

            token = None
            expires_at = None
            if decision == "ALLOW":
                token = f"scbe_{hashlib.sha256(decision_id.encode()).hexdigest()[:16]}_{decision_id[:8]}"
                expires_at = (datetime.utcnow() + timedelta(minutes=5)).isoformat() + "Z"

            return response(200, {
                'decision': decision,
                'decision_id': decision_id,
                'score': round(score, 3),
                'explanation': explanation,
                'token': token,
                'expires_at': expires_at
            })

        # GET /v1/agents (list)
        if path == '/v1/agents' and http_method == 'GET':
            return response(200, {
                'agents': [],
                'message': 'Use DynamoDB persistence for production'
            })

        # POST /v1/consensus
        if path == '/v1/consensus' and http_method == 'POST':
            action = body.get('action', 'EXECUTE')
            target = body.get('target', 'resource')
            validators = body.get('validator_ids', ['v1', 'v2', 'v3'])
            required = body.get('required_approvals', 2)

            votes = []
            approvals = 0
            for vid in validators:
                decision, score, _ = scbe_pipeline(vid, action, target, 0.6, 0.5)
                is_approve = decision in ("ALLOW", "QUARANTINE")
                if is_approve:
                    approvals += 1
                votes.append({
                    'validator_id': vid,
                    'decision': decision,
                    'score': round(score, 3),
                    'approved': is_approve
                })

            status = "APPROVED" if approvals >= required else "REJECTED"

            return response(200, {
                'consensus_id': f"con_{uuid.uuid4().hex[:12]}",
                'status': status,
                'approvals': approvals,
                'rejections': len(validators) - approvals,
                'required': required,
                'votes': votes
            })

        # Fallback
        return response(404, {'error': 'Endpoint not found', 'path': path})


# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        'httpMethod': 'POST',
        'path': '/v1/authorize',
        'headers': {'X-API-Key': 'test-key'},
        'body': json.dumps({
            'agent_id': 'test-agent',
            'action': 'READ',
            'target': 'test-resource',
            'context': {'sensitivity': 0.3, 'trust_score': 0.7}
        })
    }

    # Set test API key
    os.environ['SCBE_API_KEY'] = 'test-key'

    result = handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))
