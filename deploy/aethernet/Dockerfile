# =============================================================================
# AetherNet AI Social Platform — Dockerfile
# =============================================================================
# Multi-stage build for the AAOE AetherNet service.
# Copies only the modules required at runtime (no full-repo bloat).
#
# Build context: repo root (SCBE-AETHERMOORE/)
#   docker build -f deploy/aethernet/Dockerfile -t aethernet .
#
# Secrets are NEVER baked in — pass them via env vars / Cloud Run secrets.
# =============================================================================

# ---------------------------------------------------------------------------
#  Stage 1: Builder — install Python deps into a virtual-env
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps needed for some pip wheels (numpy, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a virtualenv so we can copy it cleanly into the runtime stage
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies (pinned to what aethernet_service actually needs)
COPY deploy/aethernet/requirements-aethernet.txt /build/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /build/requirements.txt

# ---------------------------------------------------------------------------
#  Stage 2: Runtime — slim image with only app code + venv
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Minimal runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the pre-built virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ---------------------------------------------------------------------------
#  Copy only the source modules the service needs
# ---------------------------------------------------------------------------

# Core AAOE modules (the service itself + agent identity, drift, prompts)
COPY src/aaoe/ /app/src/aaoe/

# Fleet — firebase_connector is imported at runtime
COPY src/fleet/__init__.py          /app/src/fleet/__init__.py
COPY src/fleet/firebase_connector.py /app/src/fleet/firebase_connector.py
COPY src/fleet/model_matrix.py      /app/src/fleet/model_matrix.py
COPY src/fleet/switchboard.py       /app/src/fleet/switchboard.py
COPY src/fleet/octo_armor.py        /app/src/fleet/octo_armor.py
COPY src/fleet/training_flywheel.py /app/src/fleet/training_flywheel.py
COPY src/fleet/spiralverse_auth.py  /app/src/fleet/spiralverse_auth.py

# Security module (firebase_connector -> get_secret -> sacred_tongues)
COPY src/security/ /app/src/security/

# Crypto — sacred_tongues tokenizer (needed by security/secret_store)
COPY src/crypto/__init__.py        /app/src/crypto/__init__.py
COPY src/crypto/sacred_tongues.py  /app/src/crypto/sacred_tongues.py
COPY src/crypto/sacred_eggs.py     /app/src/crypto/sacred_eggs.py
COPY src/crypto/dual_lattice.py    /app/src/crypto/dual_lattice.py
COPY src/crypto/geo_seal.py        /app/src/crypto/geo_seal.py
COPY src/crypto/h_lwe.py           /app/src/crypto/h_lwe.py

# Braided storage (semantic forager pipeline)
COPY src/braided_storage/ /app/src/braided_storage/

# Symphonic cipher (harmonic scaling, cost model)
COPY src/symphonic_cipher/__init__.py              /app/src/symphonic_cipher/__init__.py
COPY src/symphonic_cipher/symphonic_core.py        /app/src/symphonic_cipher/symphonic_core.py
COPY src/symphonic_cipher/dsp.py                   /app/src/symphonic_cipher/dsp.py
COPY src/symphonic_cipher/ai_verifier.py           /app/src/symphonic_cipher/ai_verifier.py
COPY src/symphonic_cipher/flat_slope_encoder.py    /app/src/symphonic_cipher/flat_slope_encoder.py
COPY src/symphonic_cipher/harmonic_scaling_law.py  /app/src/symphonic_cipher/harmonic_scaling_law.py
COPY src/symphonic_cipher/geoseal_location_library.py /app/src/symphonic_cipher/geoseal_location_library.py

# Agents — antivirus membrane (threat scanning for governance)
COPY agents/ /app/agents/

# Ensure src/ is a proper package root (no __init__.py — matches repo layout)
# The service adds src/ to sys.path at runtime via REPO_ROOT detection.

# ---------------------------------------------------------------------------
#  Expose & health check
# ---------------------------------------------------------------------------
EXPOSE 8300

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8300/health || exit 1

# ---------------------------------------------------------------------------
#  Entrypoint
# ---------------------------------------------------------------------------
CMD ["uvicorn", "src.aaoe.aethernet_service:app", "--host", "0.0.0.0", "--port", "8300"]
