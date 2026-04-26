"""Multi-adapter coding agent router.

Loads the Qwen coding base model once and attaches every coding-lane LoRA
adapter named in the adapter registry. Routes generation requests to the
right adapter via PEFT `set_adapter()` so we can defer merging until the
drift evidence supports it.

Usage:
    python scripts/agents/coding_agent_router.py --list
    python scripts/agents/coding_agent_router.py --lane cross_tongue_coder \
        --prompt "Write a python function that ..."
    python scripts/agents/coding_agent_router.py --serve --port 8020

The registry is the canonical source of which adapters belong to the coding
agent. A lane only loads if its `lane` field appears in the allowed coding
lanes set (configurable via --lanes).

Output for one-shot mode:
    {"lane": str, "prompt": str, "response": str, "latency_ms": float,
     "adapter_repo": str, "base_model": str}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = REPO_ROOT / "artifacts" / "adapter_registry" / "registry.json"
DEFAULT_BASE = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
DEFAULT_LANES = (
    "cross_tongue_coder",
    "binary_geoseal_coder",
    "command_recall_geoseal_coder",
    "atomic_workflow_resource_decay",
    "dsl_synthesis_v1",
)
DEFAULT_SYSTEM = "You are an SCBE-AETHERMOORE GeoSeal command-line coding agent."


class CodingAgentRouter:
    """Holds a base model + multiple LoRA adapters keyed by lane."""

    def __init__(
        self,
        base_model: str = DEFAULT_BASE,
        registry_path: Path = DEFAULT_REGISTRY,
        allowed_lanes: tuple[str, ...] = DEFAULT_LANES,
        cache_dir: Path | None = None,
        system_prompt: str = DEFAULT_SYSTEM,
    ) -> None:
        self.base_model = base_model
        self.registry_path = registry_path
        self.allowed_lanes = set(allowed_lanes)
        self.cache_dir = cache_dir
        self.system_prompt = system_prompt
        self.tokenizer = None
        self.model = None
        self.lane_to_repo: dict[str, str] = {}
        self.lane_to_local: dict[str, str] = {}
        self.loaded_lanes: set[str] = set()

    def discover(self) -> list[dict[str, Any]]:
        if not self.registry_path.exists():
            raise FileNotFoundError(f"missing registry: {self.registry_path}")
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        out: list[dict[str, Any]] = []
        for a in payload.get("adapters", []):
            lane = a.get("lane")
            if lane not in self.allowed_lanes:
                continue
            row = {
                "lane": lane,
                "profile_id": a.get("profile_id"),
                "adapter_repo": a.get("adapter_repo"),
                "status": a.get("status"),
                "local": None,
            }
            for la in a.get("local_adapters") or []:
                ldir = la.get("local_adapter_dir")
                if ldir:
                    row["local"] = str((REPO_ROOT / ldir).resolve())
                    break
            if row["adapter_repo"] or row["local"]:
                out.append(row)
        return out

    def _resolve_adapter_path(self, lane: str, repo: str | None, local: str | None) -> str:
        if local and (Path(local) / "adapter_config.json").exists():
            return local
        if repo:
            from huggingface_hub import snapshot_download

            kwargs: dict[str, Any] = {"repo_id": repo}
            if self.cache_dir:
                kwargs["cache_dir"] = str(self.cache_dir)
            return snapshot_download(**kwargs)
        raise RuntimeError(f"no resolvable adapter path for lane={lane}")

    def boot(self, lanes: list[dict[str, Any]] | None = None) -> None:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if lanes is None:
            lanes = self.discover()

        print(f"[router] base: {self.base_model}", flush=True)
        self.tokenizer = AutoTokenizer.from_pretrained(self.base_model, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        base = AutoModelForCausalLM.from_pretrained(
            self.base_model,
            torch_dtype=dtype,
            trust_remote_code=True,
        )
        if torch.cuda.is_available():
            base = base.to("cuda")

        first_lane = None
        peft_model = None
        for row in lanes:
            try:
                path = self._resolve_adapter_path(row["lane"], row.get("adapter_repo"), row.get("local"))
            except Exception as exc:  # noqa: BLE001
                print(f"[router] skip {row['lane']}: {exc}", flush=True)
                continue
            try:
                if peft_model is None:
                    peft_model = PeftModel.from_pretrained(base, path, adapter_name=row["lane"])
                    first_lane = row["lane"]
                else:
                    peft_model.load_adapter(path, adapter_name=row["lane"])
                self.lane_to_repo[row["lane"]] = row.get("adapter_repo") or ""
                self.lane_to_local[row["lane"]] = path
                self.loaded_lanes.add(row["lane"])
                print(f"[router] loaded {row['lane']} <- {path}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"[router] load failed for {row['lane']}: {exc}", flush=True)

        if peft_model is None:
            raise RuntimeError("no adapters loaded; check registry and HF auth")

        peft_model.eval()
        self.model = peft_model
        if first_lane:
            self.model.set_adapter(first_lane)

    def generate(self, lane: str, prompt: str, max_new_tokens: int = 320) -> dict[str, Any]:
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("router not booted")
        if lane not in self.loaded_lanes:
            raise ValueError(f"lane '{lane}' not loaded; loaded={sorted(self.loaded_lanes)}")
        import torch

        self.model.set_adapter(lane)
        msgs = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        text = self.tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)
        n_in = inputs["input_ids"].shape[1]
        t0 = time.time()
        with torch.no_grad():
            out = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                temperature=1.0,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        latency_ms = (time.time() - t0) * 1000.0
        response = self.tokenizer.decode(out[0][n_in:], skip_special_tokens=True)
        return {
            "lane": lane,
            "prompt": prompt,
            "response": response,
            "latency_ms": latency_ms,
            "adapter_repo": self.lane_to_repo.get(lane, ""),
            "adapter_path": self.lane_to_local.get(lane, ""),
            "base_model": self.base_model,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        }


def _serve(router: CodingAgentRouter, host: str, port: int) -> int:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    import uvicorn

    class GenReq(BaseModel):
        lane: str
        prompt: str
        max_new_tokens: int = 320

    app = FastAPI(title="SCBE Coding Agent Router")

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "loaded_lanes": sorted(router.loaded_lanes),
            "base_model": router.base_model,
        }

    @app.get("/lanes")
    def lanes() -> dict[str, Any]:
        return {"lanes": sorted(router.loaded_lanes), "lane_to_repo": router.lane_to_repo}

    @app.post("/generate")
    def generate(req: GenReq) -> dict[str, Any]:
        try:
            return router.generate(req.lane, req.prompt, req.max_new_tokens)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc))

    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    p.add_argument("--base", default=DEFAULT_BASE)
    p.add_argument("--lanes", default=",".join(DEFAULT_LANES), help="comma-separated lane allowlist")
    p.add_argument("--cache-dir", type=Path, default=None)
    p.add_argument("--system-prompt", default=DEFAULT_SYSTEM)
    p.add_argument("--list", action="store_true", help="list discoverable lanes and exit (no model load)")
    p.add_argument("--lane", help="single lane to invoke")
    p.add_argument("--prompt", help="prompt text for one-shot mode")
    p.add_argument("--max-new-tokens", type=int, default=320)
    p.add_argument("--serve", action="store_true", help="launch FastAPI server")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8020)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    lanes_tuple = tuple(s.strip() for s in args.lanes.split(",") if s.strip())
    router = CodingAgentRouter(
        base_model=args.base,
        registry_path=args.registry,
        allowed_lanes=lanes_tuple,
        cache_dir=args.cache_dir,
        system_prompt=args.system_prompt,
    )

    if args.list:
        rows = router.discover()
        print(json.dumps(rows, indent=2))
        return 0

    router.boot()

    if args.serve:
        return _serve(router, args.host, args.port)

    if args.lane and args.prompt is not None:
        result = router.generate(args.lane, args.prompt, args.max_new_tokens)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    print(
        "router booted; pass --lane and --prompt for one-shot, or --serve for HTTP",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
