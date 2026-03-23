# Local Image Runtime - 2026-03-15

This note records the verified local image-generation base runtime on the
Issac workstation.

## Verified Environment

- Python: `C:\Users\issda\Python312\python.exe`
- Torch: `2.6.0+cu124`
- Diffusers: `0.37.0`
- CUDA available: `True`
- GPU: `NVIDIA GeForce GTX 1660 Ti with Max-Q Design`

## What This Means

- local image generation is possible on this machine
- future image work should target the `Python312` environment first
- the limiting factor is mostly disk headroom and model size, not missing CUDA support

## Practical Constraints

- keep at least `15 GB` free before additional heavy installs
- prefer `25+ GB` free before downloading model weights or running another large ML stack
- avoid duplicating large Python/torch installs unless there is a clear need

## Current Recommendation

Use this runtime as the local-first base for:

- diffusion experiments
- storyboard/manhwa panel generation tests
- model benchmarking against the existing webtoon pipeline

Do not assume from this note alone that a specific model fits in VRAM or disk.
Validate each model family separately.
