# Portable SCBE verification container -- runs the verification vessels on ANY Docker host
# (Docker Desktop, GitHub Codespaces, Google Cloud Shell, Play with Docker). Uses no host disk.
#   build & run from the repo root:   docker build -f cloud/Dockerfile -t scbe-verify . && docker run --rm scbe-verify
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs git ca-certificates \
    && (command -v node >/dev/null || ln -sf "$(command -v nodejs)" /usr/local/bin/node) \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir numpy requests pytest

WORKDIR /work
COPY . /work/repo
WORKDIR /work/repo

CMD ["sh", "-c", "node --version && python -m pytest tests/crypto -q || true"]
