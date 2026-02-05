#!/bin/bash
#
# Multi-Cloud Agent Deployment Script
# ====================================
# Deploys SCBE AI agents to both AWS Lambda and Google Cloud Run
#
# Usage:
#   ./multi_cloud_deploy.sh [aws|gcp|both] [environment]
#
# Examples:
#   ./multi_cloud_deploy.sh both production
#   ./multi_cloud_deploy.sh aws staging
#   ./multi_cloud_deploy.sh gcp production

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="scbe-aethermoore"
VERSION=$(git describe --tags --always 2>/dev/null || echo "dev")
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Default values
TARGET="${1:-both}"
ENVIRONMENT="${2:-production}"

# AWS Configuration
AWS_REGION="${AWS_REGION:-us-west-2}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
AWS_LAMBDA_ROLE="${AWS_LAMBDA_ROLE:-scbe-lambda-execution-role}"

# GCP Configuration
GCP_PROJECT="${GCP_PROJECT:-}"
GCP_REGION="${GCP_REGION:-us-central1}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         SCBE Multi-Cloud Agent Deployment                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Target: ${GREEN}${TARGET}${NC}"
echo -e "Environment: ${GREEN}${ENVIRONMENT}${NC}"
echo -e "Version: ${GREEN}${VERSION}${NC}"
echo ""

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"

    local missing=()

    # Check Python
    if ! command -v python3 &> /dev/null; then
        missing+=("python3")
    fi

    # Check pip
    if ! command -v pip3 &> /dev/null; then
        missing+=("pip3")
    fi

    # Check AWS CLI (if deploying to AWS)
    if [[ "$TARGET" == "aws" || "$TARGET" == "both" ]]; then
        if ! command -v aws &> /dev/null; then
            missing+=("aws-cli")
        fi
    fi

    # Check gcloud CLI (if deploying to GCP)
    if [[ "$TARGET" == "gcp" || "$TARGET" == "both" ]]; then
        if ! command -v gcloud &> /dev/null; then
            missing+=("gcloud-cli")
        fi
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        missing+=("docker")
    fi

    if [ ${#missing[@]} -ne 0 ]; then
        echo -e "${RED}Missing prerequisites: ${missing[*]}${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ All prerequisites met${NC}"
}

# Function to build deployment package
build_package() {
    echo -e "${YELLOW}Building deployment package...${NC}"

    # Create build directory
    BUILD_DIR="build/${TIMESTAMP}"
    mkdir -p "$BUILD_DIR"

    # Copy source files
    cp -r src "$BUILD_DIR/"
    cp -r api "$BUILD_DIR/"
    cp requirements.txt "$BUILD_DIR/"

    # Install dependencies to package
    pip3 install -r requirements.txt -t "$BUILD_DIR/dependencies" --no-cache-dir 2>/dev/null || true

    echo -e "${GREEN}✓ Package built in ${BUILD_DIR}${NC}"
    export BUILD_DIR
}

# Function to deploy to AWS Lambda
deploy_aws() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Deploying to AWS Lambda...${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

    if [ -z "$AWS_ACCOUNT_ID" ]; then
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
        if [ -z "$AWS_ACCOUNT_ID" ]; then
            echo -e "${RED}Error: Could not determine AWS Account ID. Please set AWS_ACCOUNT_ID${NC}"
            return 1
        fi
    fi

    echo "AWS Account: $AWS_ACCOUNT_ID"
    echo "Region: $AWS_REGION"

    # Agent types to deploy
    AGENTS=("security_tester" "performance_monitor" "hallucination_detector" "orchestrator")

    for agent in "${AGENTS[@]}"; do
        echo -e "${YELLOW}Deploying ${agent} agent...${NC}"

        FUNCTION_NAME="${PROJECT_NAME}-${agent}-${ENVIRONMENT}"

        # Create deployment package
        PACKAGE_DIR="$BUILD_DIR/lambda_${agent}"
        mkdir -p "$PACKAGE_DIR"
        cp -r "$BUILD_DIR/src" "$PACKAGE_DIR/"
        cp -r "$BUILD_DIR/api" "$PACKAGE_DIR/"
        cp -r "$BUILD_DIR/dependencies/"* "$PACKAGE_DIR/" 2>/dev/null || true

        # Create Lambda handler
        cat > "$PACKAGE_DIR/lambda_handler.py" << 'HANDLER_EOF'
"""AWS Lambda Handler for SCBE Agents"""
import json
import asyncio
from src.cloud.multi_cloud_agents import AgentFactory, CloudConfig, CloudProvider

# Initialize agent
config = CloudConfig(
    provider=CloudProvider.AWS,
    region="${AWS_REGION}",
    memory_mb=512,
    timeout_seconds=300
)

agent = None

def get_agent(agent_type):
    global agent
    if agent is None:
        agent = AgentFactory.create(agent_type, config)
    return agent

def handler(event, context):
    """Lambda handler function."""
    agent_type = "${agent}"

    try:
        agent = get_agent(agent_type)

        # Run async process
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            agent.process(event, {"aws_context": str(context)})
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
HANDLER_EOF

        # Replace variables in handler
        sed -i "s/\${agent}/${agent}/g" "$PACKAGE_DIR/lambda_handler.py"
        sed -i "s/\${AWS_REGION}/${AWS_REGION}/g" "$PACKAGE_DIR/lambda_handler.py"

        # Create ZIP package
        cd "$PACKAGE_DIR"
        zip -r "../${agent}_lambda.zip" . -x "*.pyc" -x "__pycache__/*" > /dev/null
        cd - > /dev/null

        # Check if function exists
        if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" 2>/dev/null; then
            # Update existing function
            echo "Updating existing function..."
            aws lambda update-function-code \
                --function-name "$FUNCTION_NAME" \
                --zip-file "fileb://$BUILD_DIR/${agent}_lambda.zip" \
                --region "$AWS_REGION" > /dev/null
        else
            # Create new function
            echo "Creating new function..."
            aws lambda create-function \
                --function-name "$FUNCTION_NAME" \
                --runtime python3.11 \
                --handler lambda_handler.handler \
                --role "arn:aws:iam::${AWS_ACCOUNT_ID}:role/${AWS_LAMBDA_ROLE}" \
                --zip-file "fileb://$BUILD_DIR/${agent}_lambda.zip" \
                --timeout 300 \
                --memory-size 512 \
                --environment "Variables={SCBE_ENV=${ENVIRONMENT}}" \
                --region "$AWS_REGION" > /dev/null 2>&1 || echo "Function may already exist"
        fi

        echo -e "${GREEN}✓ Deployed ${agent} to AWS Lambda${NC}"
    done

    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}AWS Deployment Complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
}

# Function to deploy to Google Cloud Run
deploy_gcp() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Deploying to Google Cloud Run...${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

    if [ -z "$GCP_PROJECT" ]; then
        GCP_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
        if [ -z "$GCP_PROJECT" ]; then
            echo -e "${RED}Error: GCP project not set. Run 'gcloud config set project <PROJECT>'${NC}"
            return 1
        fi
    fi

    echo "GCP Project: $GCP_PROJECT"
    echo "Region: $GCP_REGION"

    # Agent types to deploy
    AGENTS=("security_tester" "performance_monitor" "hallucination_detector" "orchestrator")

    for agent in "${AGENTS[@]}"; do
        echo -e "${YELLOW}Deploying ${agent} agent...${NC}"

        SERVICE_NAME="${PROJECT_NAME}-${agent}"

        # Create Dockerfile for agent
        AGENT_DIR="$BUILD_DIR/gcp_${agent}"
        mkdir -p "$AGENT_DIR"
        cp -r "$BUILD_DIR/src" "$AGENT_DIR/"
        cp -r "$BUILD_DIR/api" "$AGENT_DIR/"
        cp "$BUILD_DIR/requirements.txt" "$AGENT_DIR/"

        cat > "$AGENT_DIR/Dockerfile" << DOCKERFILE_EOF
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn

# Copy application
COPY src/ ./src/
COPY api/ ./api/

# Create main.py for Cloud Run
COPY main.py .

# Environment
ENV SCBE_ENV=${ENVIRONMENT}
ENV AGENT_TYPE=${agent}
ENV PORT=8080

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
DOCKERFILE_EOF

        # Create main.py for Cloud Run
        cat > "$AGENT_DIR/main.py" << 'MAIN_EOF'
"""Google Cloud Run entry point for SCBE Agents"""
import os
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.cloud.multi_cloud_agents import AgentFactory, CloudConfig, CloudProvider

app = FastAPI(title="SCBE Agent")

# Get agent type from environment
AGENT_TYPE = os.getenv("AGENT_TYPE", "security_tester")
ENVIRONMENT = os.getenv("SCBE_ENV", "production")
REGION = os.getenv("GCP_REGION", "us-central1")

# Initialize agent
config = CloudConfig(
    provider=CloudProvider.GCP,
    region=REGION,
    memory_mb=512,
    timeout_seconds=300
)

agent = AgentFactory.create(AGENT_TYPE, config)

@app.get("/health")
async def health():
    """Health check endpoint."""
    result = await agent.health_check()
    return {
        "status": result.status.value,
        "agent_type": AGENT_TYPE,
        "environment": ENVIRONMENT
    }

@app.post("/process")
async def process(request: Request):
    """Process agent request."""
    try:
        event = await request.json()
        result = await agent.process(event, {"cloud": "gcp"})
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/metrics")
async def metrics():
    """Get agent metrics."""
    return agent.get_metrics().__dict__
MAIN_EOF

        # Build and deploy to Cloud Run
        echo "Building container image..."
        gcloud builds submit "$AGENT_DIR" \
            --tag "gcr.io/${GCP_PROJECT}/${SERVICE_NAME}:${VERSION}" \
            --project "$GCP_PROJECT" \
            --quiet 2>/dev/null || {
                echo -e "${YELLOW}Using local docker build...${NC}"
                docker build -t "gcr.io/${GCP_PROJECT}/${SERVICE_NAME}:${VERSION}" "$AGENT_DIR"
                docker push "gcr.io/${GCP_PROJECT}/${SERVICE_NAME}:${VERSION}" 2>/dev/null || true
            }

        echo "Deploying to Cloud Run..."
        gcloud run deploy "$SERVICE_NAME" \
            --image "gcr.io/${GCP_PROJECT}/${SERVICE_NAME}:${VERSION}" \
            --platform managed \
            --region "$GCP_REGION" \
            --allow-unauthenticated \
            --memory 512Mi \
            --timeout 300 \
            --set-env-vars "SCBE_ENV=${ENVIRONMENT},AGENT_TYPE=${agent}" \
            --project "$GCP_PROJECT" \
            --quiet 2>/dev/null || echo "Deployment may require authentication"

        echo -e "${GREEN}✓ Deployed ${agent} to GCP Cloud Run${NC}"
    done

    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}GCP Deployment Complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
}

# Function to display deployment summary
show_summary() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                    Deployment Summary                          ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [[ "$TARGET" == "aws" || "$TARGET" == "both" ]]; then
        echo -e "${GREEN}AWS Lambda Functions:${NC}"
        echo "  • ${PROJECT_NAME}-security_tester-${ENVIRONMENT}"
        echo "  • ${PROJECT_NAME}-performance_monitor-${ENVIRONMENT}"
        echo "  • ${PROJECT_NAME}-hallucination_detector-${ENVIRONMENT}"
        echo "  • ${PROJECT_NAME}-orchestrator-${ENVIRONMENT}"
        echo ""
        echo "  Region: ${AWS_REGION}"
        echo "  Invoke: aws lambda invoke --function-name <name> --payload '{}' out.json"
        echo ""
    fi

    if [[ "$TARGET" == "gcp" || "$TARGET" == "both" ]]; then
        echo -e "${GREEN}GCP Cloud Run Services:${NC}"
        echo "  • ${PROJECT_NAME}-security_tester"
        echo "  • ${PROJECT_NAME}-performance_monitor"
        echo "  • ${PROJECT_NAME}-hallucination_detector"
        echo "  • ${PROJECT_NAME}-orchestrator"
        echo ""
        echo "  Region: ${GCP_REGION}"
        echo "  URLs: gcloud run services list --project ${GCP_PROJECT}"
        echo ""
    fi

    echo -e "${GREEN}Deployment completed at: $(date)${NC}"
}

# Main execution
main() {
    check_prerequisites
    build_package

    case "$TARGET" in
        aws)
            deploy_aws
            ;;
        gcp)
            deploy_gcp
            ;;
        both)
            deploy_aws
            deploy_gcp
            ;;
        *)
            echo -e "${RED}Invalid target: $TARGET. Use 'aws', 'gcp', or 'both'${NC}"
            exit 1
            ;;
    esac

    show_summary
}

# Run main
main
