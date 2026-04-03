#!/usr/bin/env python3
"""Terminal-first Kaggle kernel staging and remote run helpers.

This keeps Kaggle as a normal shell lane for SCBE work instead of depending on
remote MCP resources that may not expose tools/resources consistently.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / "config" / "connector_oauth" / ".env.connector.oauth"
STAGE_ROOT = REPO_ROOT / "artifacts" / "kaggle_kernels"
OUTPUT_ROOT = REPO_ROOT / "artifacts" / "kaggle_outputs"
METADATA_FILE = "kernel-metadata.json"
STAGE_MANIFEST = "scbe-kaggle-stage.json"


@dataclass(frozen=True)
class KernelPreset:
    name: str
    slug: str
    title: str
    source: Path
    enable_gpu: bool = True
    enable_internet: bool = True
    language: str = "python"
    kernel_type: str = "script"
    is_private: bool = True
    wrapper_args: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    dataset_sources: tuple[str, ...] = ()
    kernel_sources: tuple[str, ...] = ()
    competition_sources: tuple[str, ...] = ()
    model_sources: tuple[str, ...] = ()
    notes: str = ""


PRESETS: dict[str, KernelPreset] = {
    "smoke-governance": KernelPreset(
        name="smoke-governance",
        slug="scbe-governance-kaggle-smoke",
        title="SCBE Governance Kaggle Smoke",
        source=REPO_ROOT / "scripts" / "system" / "kaggle_notebook_smoke.py",
        wrapper_args=("--require-kaggle", "--micro-train"),
        keywords=("scbe", "governance", "smoke", "kaggle"),
        notes="Runs the hard-fail Kaggle preflight remotely before a long training job.",
    ),
    "polly-comparison": KernelPreset(
        name="polly-comparison",
        slug="scbe-polly-kaggle-comparison",
        title="SCBE Polly Kaggle Comparison",
        source=REPO_ROOT / "scripts" / "train_polly_kaggle_comparison.py",
        keywords=("scbe", "polly", "comparison", "qlora"),
        notes="Baseline vs stack-lite Polly comparison on Kaggle GPU.",
    ),
    "polly-train": KernelPreset(
        name="polly-train",
        slug="scbe-polly-kaggle-train",
        title="SCBE Polly Kaggle Train",
        source=REPO_ROOT / "scripts" / "train_polly_kaggle.py",
        keywords=("scbe", "polly", "training", "qlora"),
        notes="Main Polly QLoRA training lane for Kaggle GPU.",
    ),
    "code-ab": KernelPreset(
        name="code-ab",
        slug="scbe-code-ab-matched-budget",
        title="SCBE Code A/B Matched Budget",
        source=REPO_ROOT / "scripts" / "research" / "train_code_ab_kaggle_safe.py",
        keywords=("scbe", "code", "benchmark", "matched-budget"),
        notes="Matched-budget code benchmark that fails fast on CPU-only Kaggle runtimes.",
    ),
    "scbe-coder": KernelPreset(
        name="scbe-coder",
        slug="scbe-coder-kaggle-train",
        title="SCBE Coder Kaggle Train",
        source=REPO_ROOT / "scripts" / "train_scbe_coder_kaggle.py",
        keywords=("scbe", "coder", "training", "kaggle"),
        notes="SCBE coder fine-tune lane for Kaggle-compatible training.",
    ),
}


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name and not os.environ.get(name):
            os.environ[name] = value


def normalize_kaggle_env() -> None:
    load_env_file(ENV_FILE)
    if not os.environ.get("KAGGLE_API_TOKEN") and os.environ.get("KAGGLE_KEY"):
        os.environ["KAGGLE_API_TOKEN"] = os.environ["KAGGLE_KEY"]
    if not os.environ.get("KAGGLE_KEY") and os.environ.get("KAGGLE_API_TOKEN"):
        os.environ["KAGGLE_KEY"] = os.environ["KAGGLE_API_TOKEN"]


def require_username() -> str:
    username = os.environ.get("KAGGLE_USERNAME", "").strip()
    if not username:
        raise SystemExit("KAGGLE_USERNAME is required. Load config/connector_oauth/.env.connector.oauth first.")
    return username


def require_kaggle_cli() -> str:
    exe = shutil.which("kaggle")
    if not exe:
        raise SystemExit("Kaggle CLI is not installed or not on PATH.")
    return exe


def ensure_source_exists(source: Path) -> Path:
    if not source.exists():
        raise SystemExit(f"Source file not found: {source}")
    return source


def sanitize_slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def kernel_ref_from_metadata(stage_dir: Path) -> str:
    metadata_path = stage_dir / METADATA_FILE
    if not metadata_path.exists():
        raise SystemExit(f"Missing {METADATA_FILE} in {stage_dir}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    kernel_ref = str(metadata.get("id", "")).strip()
    if not kernel_ref:
        raise SystemExit(f"Metadata in {metadata_path} does not include an id")
    return kernel_ref


def build_wrapper_script(target_script_name: str, args: tuple[str, ...]) -> str:
    rendered_args = ", ".join(repr(part) for part in args)
    return (
        "import subprocess\n"
        "import sys\n\n"
        f"cmd = [sys.executable, {target_script_name!r}"
        + (f", {rendered_args}" if rendered_args else "")
        + "]\n"
        "raise SystemExit(subprocess.run(cmd, check=False).returncode)\n"
    )


def stage_preset(
    preset: KernelPreset,
    *,
    slug: str | None = None,
    title: str | None = None,
    public: bool = False,
    enable_gpu: bool | None = None,
    enable_internet: bool | None = None,
    target_dir: Path | None = None,
) -> dict[str, Any]:
    username = require_username()
    source = ensure_source_exists(preset.source)
    final_slug = sanitize_slug(slug or preset.slug)
    final_title = title or preset.title
    stage_dir = (target_dir or (STAGE_ROOT / final_slug)).resolve()
    stage_dir.mkdir(parents=True, exist_ok=True)

    copied_source_name = source.name
    copied_source_path = stage_dir / copied_source_name
    shutil.copy2(source, copied_source_path)

    code_file = copied_source_name
    if preset.wrapper_args:
        code_file = "runner.py"
        (stage_dir / code_file).write_text(
            build_wrapper_script(copied_source_name, preset.wrapper_args),
            encoding="utf-8",
        )

    metadata = {
        "id": f"{username}/{final_slug}",
        "title": final_title,
        "code_file": code_file,
        "language": preset.language,
        "kernel_type": preset.kernel_type,
        "is_private": not public if public else preset.is_private,
        "enable_gpu": preset.enable_gpu if enable_gpu is None else enable_gpu,
        "enable_tpu": False,
        "enable_internet": preset.enable_internet if enable_internet is None else enable_internet,
        "dataset_sources": list(preset.dataset_sources),
        "competition_sources": list(preset.competition_sources),
        "kernel_sources": list(preset.kernel_sources),
        "model_sources": list(preset.model_sources),
        "keywords": list(preset.keywords),
    }
    metadata_path = stage_dir / METADATA_FILE
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "preset": preset.name,
        "kernel_ref": metadata["id"],
        "stage_dir": str(stage_dir),
        "source": str(source),
        "code_file": code_file,
        "notes": preset.notes,
    }
    (stage_dir / STAGE_MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def run_kaggle(args: list[str]) -> int:
    require_kaggle_cli()
    result = subprocess.run(["kaggle", *args], cwd=str(REPO_ROOT), check=False)
    return int(result.returncode)


def print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2))


def cmd_presets(_: argparse.Namespace) -> int:
    payload = {
        name: {
            "slug": preset.slug,
            "title": preset.title,
            "source": str(preset.source),
            "enable_gpu": preset.enable_gpu,
            "enable_internet": preset.enable_internet,
            "notes": preset.notes,
            "wrapper_args": list(preset.wrapper_args),
        }
        for name, preset in PRESETS.items()
    }
    print_json(payload)
    return 0


def cmd_stage(args: argparse.Namespace) -> int:
    preset = PRESETS[args.preset]
    manifest = stage_preset(
        preset,
        slug=args.slug,
        title=args.title,
        public=args.public,
        enable_gpu=args.enable_gpu,
        enable_internet=args.enable_internet,
        target_dir=Path(args.path).resolve() if args.path else None,
    )
    print_json(manifest)
    return 0


def _resolve_stage_dir(args: argparse.Namespace) -> Path:
    if args.path:
        return Path(args.path).resolve()
    if args.preset:
        preset = PRESETS[args.preset]
        manifest = stage_preset(
            preset,
            slug=args.slug,
            title=args.title,
            public=args.public,
            enable_gpu=args.enable_gpu,
            enable_internet=args.enable_internet,
        )
        return Path(manifest["stage_dir"])
    raise SystemExit("Provide either --path or --preset.")


def _resolve_kernel_ref(args: argparse.Namespace) -> str:
    if getattr(args, "kernel", ""):
        return str(args.kernel).strip()
    if args.path:
        return kernel_ref_from_metadata(Path(args.path).resolve())
    if args.preset:
        preset = PRESETS[args.preset]
        slug = sanitize_slug(args.slug or preset.slug)
        return f"{require_username()}/{slug}"
    raise SystemExit("Provide --kernel, --path, or --preset.")


def cmd_push(args: argparse.Namespace) -> int:
    stage_dir = _resolve_stage_dir(args)
    cmd = ["kernels", "push", "-p", str(stage_dir)]
    if args.timeout is not None:
        cmd.extend(["-t", str(args.timeout)])
    if args.accelerator:
        cmd.extend(["--accelerator", args.accelerator])
    return run_kaggle(cmd)


def cmd_status(args: argparse.Namespace) -> int:
    kernel_ref = _resolve_kernel_ref(args)
    return run_kaggle(["kernels", "status", kernel_ref])


def cmd_output(args: argparse.Namespace) -> int:
    kernel_ref = _resolve_kernel_ref(args)
    output_dir = Path(args.output or (OUTPUT_ROOT / sanitize_slug(kernel_ref.replace("/", "-")))).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["kernels", "output", kernel_ref, "-p", str(output_dir)]
    if args.force:
        cmd.append("-o")
    if args.quiet:
        cmd.append("-q")
    if args.file_pattern:
        cmd.extend(["--file-pattern", args.file_pattern])
    return run_kaggle(cmd)


def cmd_pull(args: argparse.Namespace) -> int:
    kernel_ref = _resolve_kernel_ref(args)
    pull_dir = Path(args.output or (STAGE_ROOT / sanitize_slug(kernel_ref.replace("/", "-")) / "pulled")).resolve()
    pull_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["kernels", "pull", kernel_ref, "-p", str(pull_dir), "-m"]
    return run_kaggle(cmd)


def cmd_url(args: argparse.Namespace) -> int:
    kernel_ref = _resolve_kernel_ref(args)
    print(f"https://www.kaggle.com/code/{kernel_ref}")
    return 0


def cmd_inventory(_: argparse.Namespace) -> int:
    result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_ROOT / "scripts" / "system" / "model_host_quickcall.ps1"),
            "-Action",
            "inventory-kaggle",
        ],
        cwd=str(REPO_ROOT),
        check=False,
    )
    return int(result.returncode)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stage and operate SCBE Kaggle kernels from the terminal.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("presets", help="List built-in SCBE Kaggle presets.").set_defaults(func=cmd_presets)

    parser_stage = subparsers.add_parser("stage", help="Stage a preset into a Kaggle kernel folder.")
    parser_stage.add_argument("--preset", choices=sorted(PRESETS), required=True)
    parser_stage.add_argument("--slug", default="")
    parser_stage.add_argument("--title", default="")
    parser_stage.add_argument("--path", default="")
    parser_stage.add_argument("--public", action="store_true")
    parser_stage.add_argument("--enable-gpu", dest="enable_gpu", action="store_true")
    parser_stage.add_argument("--disable-gpu", dest="enable_gpu", action="store_false")
    parser_stage.add_argument("--enable-internet", dest="enable_internet", action="store_true")
    parser_stage.add_argument("--disable-internet", dest="enable_internet", action="store_false")
    parser_stage.set_defaults(func=cmd_stage, enable_gpu=None, enable_internet=None)

    for name, help_text, handler in (
        ("push", "Push a staged or preset kernel and trigger a Kaggle run.", cmd_push),
        ("status", "Show the latest Kaggle run status for a kernel.", cmd_status),
        ("output", "Download the latest Kaggle run output for a kernel.", cmd_output),
        ("pull", "Pull the source and metadata for a Kaggle kernel.", cmd_pull),
        ("url", "Print the Kaggle code URL for a kernel.", cmd_url),
    ):
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("--kernel", default="")
        sub.add_argument("--preset", choices=sorted(PRESETS), default="")
        sub.add_argument("--slug", default="")
        sub.add_argument("--title", default="")
        sub.add_argument("--path", default="")
        sub.add_argument("--public", action="store_true")
        sub.add_argument("--enable-gpu", dest="enable_gpu", action="store_true")
        sub.add_argument("--disable-gpu", dest="enable_gpu", action="store_false")
        sub.add_argument("--enable-internet", dest="enable_internet", action="store_true")
        sub.add_argument("--disable-internet", dest="enable_internet", action="store_false")
        sub.set_defaults(func=handler, enable_gpu=None, enable_internet=None)
        if name == "push":
            sub.add_argument("--timeout", type=int, default=None)
            sub.add_argument("--accelerator", default="")
        if name in {"output", "pull"}:
            sub.add_argument("--output", default="")
        if name == "output":
            sub.add_argument("--file-pattern", default="")
            sub.add_argument("--force", action="store_true")
            sub.add_argument("--quiet", action="store_true")

    subparsers.add_parser("inventory", help="Run the repo's Kaggle inventory helper.").set_defaults(func=cmd_inventory)
    return parser


def main(argv: list[str] | None = None) -> int:
    normalize_kaggle_env()
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
