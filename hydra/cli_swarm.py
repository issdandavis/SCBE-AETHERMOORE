from __future__ import annotations

import argparse
import json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HYDRA swarm compatibility CLI")
    parser.add_argument("task", nargs="*", help="Task text")
    parser.add_argument("--provider", default="local")
    parser.add_argument("--model", default="local-model")
    parser.add_argument("--backend", default="playwright")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not args.dry_run:
        raise SystemExit("hydra.cli_swarm compatibility mode only supports --dry-run")

    print(
        json.dumps(
            {
                "schema_version": "hydra_cli_swarm_compat_v1",
                "status": "dry-run",
                "provider": args.provider,
                "model": args.model,
                "backend": args.backend,
                "base_url": args.base_url,
                "task": " ".join(args.task).strip(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
