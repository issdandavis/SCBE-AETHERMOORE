#!/usr/bin/env python3
"""AI Bridge: terminal access to external models (HF + Vertex)."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _allowed_vault_roots() -> list[Path]:
    roots = [PROJECT_ROOT]

    joined_roots = os.getenv("SCBE_ALLOWED_VAULT_ROOTS", "")
    if joined_roots:
        for raw in joined_roots.split(os.pathsep):
            raw = raw.strip()
            if raw:
                roots.append(Path(raw).expanduser())

    for env_name in ("SCBE_VAULTS_ROOT", "OBSIDIAN_VAULT_PATH"):
        raw = os.getenv(env_name, "").strip()
        if raw:
            roots.append(Path(raw).expanduser())

    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        resolved = root.resolve(strict=False)
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(resolved)
    return deduped


def _resolve_vault_root(vault_path: str) -> Path:
    raw = str(vault_path or "").strip()
    if not raw:
        raise ValueError("vault_path is required")

    resolved = Path(raw).expanduser().resolve(strict=False)
    if not resolved.exists() or not resolved.is_dir():
        raise ValueError(f"Vault path must be an existing directory: {resolved}")

    for allowed_root in _allowed_vault_roots():
        if _is_relative_to(resolved, allowed_root):
            return resolved

    roots = ", ".join(str(root) for root in _allowed_vault_roots())
    raise ValueError(f"Vault path must stay within an allowed root: {roots}")


def _safe_model_slug(model: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", str(model or ""))
    slug = re.sub(r"_+", "_", slug).strip("._-")
    return slug or "model"


def call_hf(model: str, prompt: str) -> str:
    try:
        from huggingface_hub import InferenceClient
    except Exception as exc:
        raise RuntimeError("huggingface_hub not installed") from exc

    token = os.getenv("HF_TOKEN") or None
    client = InferenceClient(model=model, token=token)

    try:
        resp = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.3,
        )
        choice = resp.choices[0]
        return choice.message.content if hasattr(choice, "message") else str(resp)
    except Exception:
        try:
            out = client.text_generation(prompt=prompt, max_new_tokens=400, temperature=0.3)
            return out if isinstance(out, str) else str(out)
        except Exception as exc:
            raise RuntimeError(
                "HF bridge failed. Set HF_TOKEN with Inference Provider permissions or use --provider vertex."
            ) from exc


def call_vertex(model: str, prompt: str) -> str:
    try:
        from google import genai
        from google.genai.types import HttpOptions
    except Exception as exc:
        raise RuntimeError("google-genai not installed") from exc

    client = genai.Client(http_options=HttpOptions(api_version="v1"))
    resp = client.models.generate_content(model=model, contents=prompt)
    return (resp.text or "").strip()


def write_log(vault_path: str, provider: str, model: str, prompt: str, response: str) -> Path:
    root = _resolve_vault_root(vault_path)
    ts = datetime.now(timezone.utc)
    day = ts.strftime("%Y-%m-%d")
    stamp = ts.strftime("%H%M%S")
    folder = root / "SCBE-Hub" / "AI-Bridge" / day
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{stamp}-{provider}-{_safe_model_slug(model)}.md"
    lines = [
        f"# AI Bridge Log - {provider}",
        "",
        f"- timestamp_utc: {ts.isoformat()}",
        f"- model: {model}",
        "",
        "## Prompt",
        prompt,
        "",
        "## Response",
        response,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_once(provider: str, model: str, prompt: str) -> str:
    if provider == "hf":
        return call_hf(model, prompt)
    if provider == "vertex":
        return call_vertex(model, prompt)
    raise ValueError(f"Unsupported provider: {provider}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--provider", choices=["hf", "vertex"], required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--prompt", default="")
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--vault-path", default="")
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.interactive:
        print(f"AI Bridge interactive mode: provider={args.provider}, model={args.model}")
        while True:
            try:
                prompt = input("you> ").strip()
            except EOFError:
                break
            if not prompt or prompt.lower() in {"exit", "quit"}:
                break
            try:
                response = run_once(args.provider, args.model, prompt)
            except Exception as exc:
                print(f"ai-error> {exc}\n")
                continue
            print(f"ai> {response}\n")
            if args.vault_path:
                write_log(args.vault_path, args.provider, args.model, prompt, response)
        return 0

    if not args.prompt:
        raise SystemExit("--prompt is required when not using --interactive")

    try:
        response = run_once(args.provider, args.model, args.prompt)
    except Exception as exc:
        raise SystemExit(f"AI bridge error: {exc}")

    log = write_log(args.vault_path, args.provider, args.model, args.prompt, response) if args.vault_path else None

    if args.json:
        payload = {
            "provider": args.provider,
            "model": args.model,
            "prompt": args.prompt,
            "response": response,
            "log": str(log) if log else None,
        }
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    else:
        print(response)
        if log:
            print(f"\n[logged] {log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
