#!/usr/bin/env python3
"""AI Bridge: terminal access to external models (HF + Vertex)."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


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
    root = Path(vault_path)
    ts = datetime.now(timezone.utc)
    day = ts.strftime("%Y-%m-%d")
    stamp = ts.strftime("%H%M%S")
    folder = root / "SCBE-Hub" / "AI-Bridge" / day
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{stamp}-{provider}-{model.replace('/', '_')}.md"
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
