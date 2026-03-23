from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from huggingface_hub import HfApi

try:
    from scripts.build_hf_webtoon_job import DEFAULT_OUTPUT_PATH, write_uv_job_script
except ModuleNotFoundError:
    from build_hf_webtoon_job import DEFAULT_OUTPUT_PATH, write_uv_job_script


DEFAULT_FLAVOR = "a10g-small"
DEFAULT_TIMEOUT = "8h"
DEFAULT_SCRIPT_REPO = "issdandavis/scbe-webtoon-job-scripts"
DEFAULT_SCRIPT_PATH_IN_REPO = "jobs/webtoon_hf_embedded_job.py"


def build_submit_command(
    script_path: str | Path,
    *,
    flavor: str,
    timeout: str,
    output_repo: str,
    model_id: str | None = None,
    max_panels: int | None = None,
    only_chapters: str | None = None,
    run_name: str | None = None,
    detach: bool = True,
) -> list[str]:
    command = [
        "hf",
        "jobs",
        "uv",
        "run",
        "--flavor",
        flavor,
        "--timeout",
        timeout,
        "--secrets",
        "HF_TOKEN",
    ]
    if detach:
        command.append("--detach")

    command.append(str(script_path))
    command.extend(["--output-repo", output_repo])

    if model_id:
        command.extend(["--model-id", model_id])
    if max_panels is not None:
        command.extend(["--max-panels", str(max_panels)])
    if only_chapters:
        command.extend(["--only-chapters", only_chapters])
    if run_name:
        command.extend(["--run-name", run_name])

    return command


def stage_job_script(
    script_path: Path,
    *,
    repo_id: str,
    path_in_repo: str = DEFAULT_SCRIPT_PATH_IN_REPO,
) -> str:
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HF_TOKEN must be set before staging the Hugging Face Jobs script.")

    api = HfApi(token=token)
    api.create_repo(repo_id, repo_type="dataset", exist_ok=True)
    api.upload_file(
        path_or_fileobj=str(script_path),
        path_in_repo=path_in_repo,
        repo_id=repo_id,
        repo_type="dataset",
    )
    return f"https://huggingface.co/datasets/{repo_id}/resolve/main/{path_in_repo}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit the remote webtoon panel job to Hugging Face Jobs")
    parser.add_argument("--script-output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--flavor", default=DEFAULT_FLAVOR)
    parser.add_argument("--timeout", default=DEFAULT_TIMEOUT)
    parser.add_argument("--output-repo", default="issdandavis/six-tongues-webtoon-panels")
    parser.add_argument("--script-repo", default=DEFAULT_SCRIPT_REPO)
    parser.add_argument("--script-path-in-repo", default=DEFAULT_SCRIPT_PATH_IN_REPO)
    parser.add_argument("--model-id", default=None)
    parser.add_argument("--max-panels", type=int, default=None)
    parser.add_argument("--only-chapters", default=None)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--foreground", action="store_true", help="Run attached instead of detach")
    args = parser.parse_args()

    if not os.environ.get("HF_TOKEN", "").strip():
        raise RuntimeError("HF_TOKEN must be set before submitting a Hugging Face Job.")

    script_path = write_uv_job_script(args.script_output)
    staged_script_url = f"https://huggingface.co/datasets/{args.script_repo}/resolve/main/{args.script_path_in_repo}"
    if not args.dry_run:
        staged_script_url = stage_job_script(
            script_path,
            repo_id=args.script_repo,
            path_in_repo=args.script_path_in_repo,
        )
    command = build_submit_command(
        staged_script_url,
        flavor=args.flavor,
        timeout=args.timeout,
        output_repo=args.output_repo,
        model_id=args.model_id,
        max_panels=args.max_panels,
        only_chapters=args.only_chapters,
        run_name=args.run_name,
        detach=not args.foreground,
    )

    print(json.dumps({"script_path": str(script_path), "staged_script_url": staged_script_url, "command": command}, indent=2))
    if args.dry_run:
        return

    completed = subprocess.run(command, check=False, text=True, capture_output=True)
    print(completed.stdout)
    if completed.returncode != 0:
        if completed.stderr:
            print(completed.stderr)
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
