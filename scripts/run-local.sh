#!/bin/bash
# ===========================================
# SCBE-AETHERMOORE Local Development Runner
# ===========================================
# Runs the full system without Docker
#
# Usage: ./scripts/run-local.sh
#
# Requirements:
#   - Python 3.10+
#   - Node.js 18+
#   - Redis (optional, will use in-memory fallback)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}  SCBE-AETHERMOORE Local Runner${NC}"
echo -e "${BLUE}=========================================${NC}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Check Python
echo -e "\n${YELLOW}Checking Python...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}Python not found. Please install Python 3.10+${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
echo -e "${GREEN}Found Python $PYTHON_VERSION${NC}"

# Check Node.js
echo -e "\n${YELLOW}Checking Node.js...${NC}"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}Found Node.js $NODE_VERSION${NC}"
else
    echo -e "${YELLOW}Node.js not found. TypeScript gateway will be skipped.${NC}"
fi

# Install Python dependencies
echo -e "\n${YELLOW}Installing Python dependencies...${NC}"
$PYTHON_CMD -m pip install -q -r requirements.txt 2>/dev/null || {
    echo -e "${YELLOW}Some dependencies may have failed, continuing...${NC}"
}

# Install additional API dependencies
$PYTHON_CMD -m pip install -q fastapi uvicorn pydantic 2>/dev/null || true

# Create .env if not exists
if [ ! -f .env ]; then
    echo -e "\n${YELLOW}Creating .env from .env.example...${NC}"
    cp .env.example .env 2>/dev/null || {
        echo "SCBE_API_KEY=dev-key-local" > .env
        echo "SCBE_MODE=development" >> .env
        echo "LOG_LEVEL=INFO" >> .env
    }
fi

# Export environment variables
export $(grep -v '^#' .env | xargs) 2>/dev/null || true

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# Start Python API
echo -e "\n${GREEN}Starting SCBE Core API on http://localhost:8000${NC}"
cd "$PROJECT_ROOT/api"
$PYTHON_CMD -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

# Wait for API to start
echo -e "${YELLOW}Waiting for API to start...${NC}"
sleep 3

# Health check
if curl -s http://localhost:8000/v1/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is running!${NC}"
else
    echo -e "${YELLOW}API may still be starting...${NC}"
fi

# Print status
echo -e "\n${BLUE}=========================================${NC}"
echo -e "${GREEN}SCBE-AETHERMOORE is running!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo -e ""
echo -e "  ${GREEN}API:${NC}      http://localhost:8000"
echo -e "  ${GREEN}Docs:${NC}     http://localhost:8000/docs"
echo -e "  ${GREEN}Health:${NC}   http://localhost:8000/v1/health"
echo -e ""
echo -e "  ${YELLOW}Press Ctrl+C to stop${NC}"
echo -e ""

# Keep running
wait $API_PID
