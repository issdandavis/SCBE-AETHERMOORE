# Multi-stage build for SCBE-AETHERMOORE
# With real Post-Quantum Cryptography (liboqs)

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

# Stage 2: Build liboqs C library
FROM python:3.11-slim AS liboqs-builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    ninja-build \
    gcc \
    g++ \
    libssl-dev \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Clone and build liboqs (NIST FIPS 203/204 compliant)
RUN git clone --depth 1 --branch 0.10.1 https://github.com/open-quantum-safe/liboqs.git && \
    cd liboqs && \
    mkdir build && cd build && \
    cmake -GNinja \
      -DCMAKE_INSTALL_PREFIX=/usr/local \
      -DBUILD_SHARED_LIBS=ON \
      -DOQS_BUILD_ONLY_LIB=ON \
      .. && \
    ninja && \
    ninja install

# Stage 3: Python environment with PQC
FROM python:3.11-slim AS py-builder

WORKDIR /app

# Copy liboqs from builder
COPY --from=liboqs-builder /usr/local/lib/liboqs* /usr/local/lib/
COPY --from=liboqs-builder /usr/local/include/oqs /usr/local/include/oqs

# Update library cache
RUN ldconfig

# Install Python dependencies including liboqs-python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir liboqs-python>=0.10.0

# Copy Python source
COPY src/ ./src/
COPY scbe-cli.py ./

# Stage 4: Final runtime image
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      curl \
      libssl3 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy liboqs shared library
COPY --from=liboqs-builder /usr/local/lib/liboqs* /usr/local/lib/
RUN ldconfig

# Copy Python dependencies (including liboqs-python)
COPY --from=py-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=py-builder /app/src ./src
COPY --from=py-builder /app/scbe-cli.py ./

# Copy TypeScript build
COPY --from=ts-builder /app/dist ./dist
COPY --from=ts-builder /app/node_modules ./node_modules
COPY --from=ts-builder /app/package.json ./

# Copy demo files
COPY demo/ ./demo/

# Copy documentation
COPY README.md LICENSE ./

# Environment variables
ENV SCBE_ENV=production
ENV SCBE_PQC_BACKEND=liboqs

# Expose ports
EXPOSE 3000 8000

# Health check - verify API is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Verify PQC on startup
RUN python -c "from src.crypto.pqc_liboqs import get_pqc_backend; print(f'PQC Backend: {get_pqc_backend()}')"

# Default command
CMD ["python", "scbe-cli.py"]
