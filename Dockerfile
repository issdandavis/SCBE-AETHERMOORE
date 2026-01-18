# Multi-stage build for SCBE-AETHERMOORE

# Stage 1: Build TypeScript
FROM node:20-alpine AS ts-builder

WORKDIR /app

# Copy package files
COPY package*.json tsconfig*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY src/ ./src/

# Build TypeScript
RUN npm run build

# Stage 2: Python environment
FROM python:3.11-slim AS py-builder

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python source
COPY src/ ./src/
COPY scbe-cli.py ./

# Stage 3: Final runtime image
FROM python:3.11-slim

WORKDIR /app

# Install Node.js for hybrid runtime
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy Python dependencies
COPY --from=py-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=py-builder /app/src ./src
COPY --from=py-builder /app/scbe-cli.py ./

# Copy TypeScript build
COPY --from=ts-builder /app/dist ./dist
COPY --from=ts-builder /app/node_modules ./node_modules
COPY --from=ts-builder /app/package.json ./

# Copy demo files
COPY scbe-aethermoore/ ./demo/

# Copy documentation
COPY README.md LICENSE ./

# Expose ports
EXPOSE 3000 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["python", "scbe-cli.py"]
