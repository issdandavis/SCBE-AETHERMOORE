#!/usr/bin/env python3
"""Demo runner for multi-cloud failover router."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.browser.multi_cloud_failover import CloudEndpoint, MultiCloudRouter


def main() -> int:
    parser = argparse.ArgumentParser(description="Run multi-cloud routing demo for browser governance payloads.")
    parser.add_argument("--lambda-url", default="http://127.0.0.1:9000/validate")
    parser.add_argument("--cloud-run-url", default="http://127.0.0.1:8001/v1/integrations/n8n/browse")
    parser.add_argument("--kind", choices=["stateless", "stateful"], default="stateless")
    parser.add_argument("--position", default="0.1,0.2,0.3", help="3D point as x,y,z")
    args = parser.parse_args()

    xyz = [float(x.strip()) for x in args.position.split(",")[:3]]

    router = MultiCloudRouter(
        lambda_endpoint=CloudEndpoint(name="aws_lambda", url=args.lambda_url, kind="stateless"),
        cloud_run_endpoint=CloudEndpoint(name="gcp_cloud_run", url=args.cloud_run_url, kind="stateful"),
    )

    payload = {
        "position": xyz,
        "action": "click",
        "target": "button.submit",
    }

    result = router.route(action_kind=args.kind, payload=payload)
    print(
        json.dumps(
            {
                "selected": result.selected,
                "fallback_used": result.fallback_used,
                "latency_ms": round(result.latency_ms, 3),
                "response": result.response,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
