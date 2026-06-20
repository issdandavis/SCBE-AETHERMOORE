# Remote Container Deployment Boundary

SCBE should use Docker as a remote build and deployment boundary, not as local
storage. The local machine is space constrained, so container images, build
caches, and deployment artifacts should live in remote registries or managed
builders whenever possible.

## What Docker Is For Here

- Build a reproducible image from a specific commit.
- Store the built image in a registry such as Docker Hub or GHCR.
- Deploy that image to a remote runtime.
- Scan image dependencies before promotion.

Docker is not the right place for manuscripts, training corpora, raw archives,
or long-term project storage. Those belong in their own Git repositories,
private storage, or artifact buckets.

## Preferred No-Local-Space Flow

1. Keep source in GitHub.
2. Let GitHub Actions build the image on GitHub-hosted runners.
3. Push the image to a remote registry.
4. Deploy from the registry digest, not from a local image.
5. Keep only logs and small manifest records in this repository.

This avoids pulling large images or creating local Docker build cache on `C:`.

## Registry Choices

- Use GHCR when the image belongs tightly to a GitHub repo or should inherit
  GitHub permissions.
- Use Docker Hub when Docker subscription features, Docker Scout, or external
  pull access matter.
- Use a cloud provider registry only when the deployment runtime is already
  there.

## Local Guardrails

- Do not install or start Docker Desktop just to move files.
- Do not run `docker build` locally unless there is a specific local runtime
  issue to reproduce.
- Do not mount `C:\Users` or the repo root into long-running containers.
- Do not keep local images as backups.
- Prefer `docker buildx` remote builders or GitHub Actions.

## Minimal GitHub Actions Shape

The workflow should:

- check out source,
- log in to the registry using repository secrets,
- build with BuildKit/buildx,
- push by commit SHA and branch tag,
- write the resulting image digest to a deployment record.

For production promotion, deploy by immutable digest:

```text
ghcr.io/issdandavis/scbe-aethermoore@sha256:<digest>
```

## Paid Docker Subscription Use

Use paid Docker features only where they remove local load:

- Docker Build Cloud: remote builds and remote cache.
- Docker Hub private repositories: remote image storage.
- Docker Scout: vulnerability review of pushed images.

Do not treat the subscription as a reason to run heavy Docker workloads on the
local machine.

## Sources

- Docker Build Cloud: https://docs.docker.com/build-cloud/
- Docker Hub repositories: https://docs.docker.com/docker-hub/repos/
- Docker GitHub Actions guide: https://docs.docker.com/guides/gha/
