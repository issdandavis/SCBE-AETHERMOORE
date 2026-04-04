#!/usr/bin/env python3
"""
Render a single-image lock packet through the live image router.

This closes the loop for the "lock one thing before scaling" workflow:
lock_packet.json -> render -> manifest
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from scripts.grok_image_gen import BACKENDS, check_backends, generate
from scripts.render_grok_storyboard_packet import nearest_supported_aspect, resolve_backend, should_retry_with_fallback


ROOT = Path(__file__).resolve().parent.parent


def load_lock_packet(path: str | Path) -> dict[str, Any]:
    packet_path = Path(path)
    return json.loads(packet_path.read_text(encoding="utf-8"))


def default_output_path(lock_packet_path: Path, lock_packet: dict[str, Any]) -> Path:
    panel_id = str(lock_packet.get("panel_id") or "lock-panel")
    return lock_packet_path.parent / f"{panel_id}.png"


def run_lock_packet(
    lock_packet_path: str | Path,
    *,
    output_path: str | None = None,
    backend_override: str | None = None,
    dry_run: bool = False,
) -> Path:
    lock_packet_path = Path(lock_packet_path)
    lock_packet = load_lock_packet(lock_packet_path)

    preferred_backend = str(lock_packet.get("preferred_backend") or "imagen-ultra")
    fallback_backend = str(lock_packet.get("fallback_backend") or "hf")
    width = int(lock_packet.get("width") or 720)
    height = int(lock_packet.get("height") or 1280)
    aspect = str(lock_packet.get("aspect") or nearest_supported_aspect(width, height))
    available_backends = check_backends()
    backend, backend_available = resolve_backend(
        preferred_backend,
        fallback=fallback_backend,
        backend_override=backend_override,
        available_backends=available_backends,
        dry_run=dry_run,
    )

    output_file = Path(output_path) if output_path else default_output_path(lock_packet_path, lock_packet)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "lock_packet": str(lock_packet_path),
        "lock_name": lock_packet.get("lock_name"),
        "panel_id": lock_packet.get("panel_id"),
        "shot_label": lock_packet.get("shot_label"),
        "dry_run": dry_run,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "preferred_backend": preferred_backend,
        "backend": backend,
        "backend_available": backend_available,
        "fallback_backend": fallback_backend,
        "aspect": aspect,
        "width": width,
        "height": height,
        "output": str(output_file),
        "prompt": lock_packet.get("prompt"),
        "negative_prompt": lock_packet.get("negative_prompt"),
        "acceptance_criteria": list(lock_packet.get("acceptance_criteria") or []),
    }

    if dry_run:
        result["ok"] = True
    else:
        try:
            generate(
                backend=backend,
                prompt=str(lock_packet.get("prompt") or ""),
                output=str(output_file),
                aspect=aspect,
                reference=None,
                negative_prompt=lock_packet.get("negative_prompt"),
                width=width,
                height=height,
            )
            result["ok"] = True
        except Exception as exc:  # pragma: no cover - runtime network path
            if (
                backend != fallback_backend
                and available_backends.get(fallback_backend, False)
                and should_retry_with_fallback(exc)
            ):
                try:
                    generate(
                        backend=fallback_backend,
                        prompt=str(lock_packet.get("prompt") or ""),
                        output=str(output_file),
                        aspect=aspect,
                        reference=None,
                        negative_prompt=lock_packet.get("negative_prompt"),
                        width=width,
                        height=height,
                    )
                    result["ok"] = True
                    result["fallback_from"] = backend
                    result["backend"] = fallback_backend
                except Exception as retry_exc:
                    result["ok"] = False
                    result["error"] = str(retry_exc)
                    result["fallback_from"] = backend
                    result["fallback_error"] = str(exc)
            else:
                result["ok"] = False
                result["error"] = str(exc)

    manifest_path = lock_packet_path.parent / "lock_render_manifest.json"
    manifest_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Manifest: {manifest_path}")
    print(f"Output: {output_file}")
    return manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a single-image webtoon lock packet")
    parser.add_argument("--lock-packet", required=True, help="Path to lock_packet.json")
    parser.add_argument("--output", default=None, help="Optional output file override")
    parser.add_argument("--backend", choices=list(BACKENDS.keys()), default=None, help="Force one backend")
    parser.add_argument("--dry-run", action="store_true", help="Compile manifest without rendering")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_lock_packet(
        args.lock_packet,
        output_path=args.output,
        backend_override=args.backend,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
