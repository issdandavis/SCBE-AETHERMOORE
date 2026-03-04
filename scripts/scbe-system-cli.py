#!/usr/bin/env python3
"""SCBE System CLI (unified).

Commands:
- tongues    -> delegates to six-tongues-cli.py (encoding, xlate, blend, GeoSeal)
- gap        -> runs notion_pipeline_gap_review.py
- self-improve -> runs self_improvement_orchestrator.py
- web        -> delegates to agentic_web_tool.py
- antivirus  -> runs agentic_antivirus.py
- status     -> prints a quick system run summary
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import uuid
import subprocess
from datetime import datetime, timezone
import sys
import urllib.error
from urllib.request import Request, urlopen
from pathlib import Path


DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAD_ROOT = Path(".scbe") / "polly-pads"
DEFAULT_AGENT_REGISTRY = Path(".scbe") / "agent_squad.json"
DEFAULT_NOTEBOOKLM_PAD_ID = "notebooklm-main"
DEFAULT_NOTEBOOKLM_URL = "https://notebooklm.google.com/notebook/bf1e9a1b-b49c-4343-8f0e-8494546e4f24"


def _run_script(script: Path, args: list[str]) -> int:
    return subprocess.run([sys.executable, str(script), *args], cwd=str(script.parent), check=False).returncode


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _pad_root(repo_root: Path) -> Path:
    return repo_root / DEFAULT_PAD_ROOT


def _pad_dir(repo_root: Path, agent_id: str) -> Path:
    return _pad_root(repo_root) / agent_id


def _manifest_path(pad_dir: Path) -> Path:
    return pad_dir / "manifest.json"


def _ensure_agent_id(agent_id: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9._-]{2,64}$", agent_id))


def _load_manifest(manifest_path: Path) -> dict:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing pad manifest: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_manifest(manifest_path: Path, data: dict) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def _agent_registry_path(repo_root: Path) -> Path:
    return repo_root / DEFAULT_AGENT_REGISTRY


def _read_env_file(repo_root: Path) -> dict[str, str]:
    env_path = repo_root / ".env"
    env: dict[str, str] = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def _load_agent_registry(registry_path: Path) -> dict[str, dict]:
    if not registry_path.exists():
        return {
            "version": "1.0.0",
            "agents": {},
        }
    with registry_path.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return {
                "version": "1.0.0",
                "agents": {},
            }
    if "agents" not in data or not isinstance(data["agents"], dict):
        data["agents"] = {}
    if "version" not in data:
        data["version"] = "1.0.0"
    return data


def _save_agent_registry(registry_path: Path, data: dict) -> None:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with registry_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def _new_agent_entry(
    agent_id: str,
    provider: str,
    display_name: str,
    description: str,
    api_key_env: str | None = None,
    model: str | None = None,
    endpoint: str | None = None,
    notebook_url: str | None = None,
) -> dict:
    entry = {
        "agent_id": agent_id,
        "provider": provider,
        "display_name": display_name or agent_id,
        "description": description or "",
        "enabled": True,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "capabilities": [],
    }
    if api_key_env:
        entry["api_key_env"] = api_key_env
    if model:
        entry["model"] = model
    if endpoint:
        entry["endpoint"] = endpoint
    if notebook_url:
        entry["notebook_url"] = notebook_url
    return entry


def _resolve_agent_api_key(agent: dict, env_cache: dict[str, str]) -> tuple[str | None, str | None]:
    env_var = agent.get("api_key_env")
    if not env_var:
        provider = (agent.get("provider") or "").lower()
        env_var = (
            "ANTHROPIC_API_KEY" if provider == "anthropic" else
            "OPENAI_API_KEY" if provider == "openai" else
            "GOOGLE_API_KEY" if provider == "gemini" else
            None
        )
    if not env_var:
        return None, None
    return os.environ.get(env_var) or env_cache.get(env_var), env_var


def _call_openai_agent(agent: dict, prompt: str, output_dir: Path, env_cache: dict[str, str], max_tokens: int) -> dict:
    provider = (agent.get("provider") or "openai").lower()
    if provider != "openai":
        return {
            "ok": False,
            "agent_id": agent.get("agent_id"),
            "provider": provider,
            "error": f"OpenAI REST path is only for openai provider, got {provider}",
        }
    api_key, env_key = _resolve_agent_api_key(agent, env_cache)
    if not api_key:
        return {
            "ok": False,
            "agent_id": agent.get("agent_id"),
            "provider": provider,
            "error": f"Missing API key. Set {env_key or 'OPENAI_API_KEY'} and retry.",
        }
    model = agent.get("model") or "gpt-4o-mini"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an SCBE-AETHERMOORE coordination agent."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
    }
    req = Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
        response_obj = json.loads(raw)
        choices = response_obj.get("choices") or []
        content = ""
        if choices:
            msg = choices[0].get("message") or {}
            content = msg.get("content") or ""
        return {
            "ok": True,
            "agent_id": agent.get("agent_id"),
            "provider": provider,
            "model": model,
            "raw": response_obj,
            "content": content,
            "output_path": str((output_dir / f"{agent.get('agent_id')}_openai.json").resolve()) if output_dir else None,
        }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore") if getattr(exc, "read", None) else ""
        return {
            "ok": False,
            "agent_id": agent.get("agent_id"),
            "provider": provider,
            "error": f"HTTP {exc.code}: {body or str(exc)}",
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "ok": False,
            "agent_id": agent.get("agent_id"),
            "provider": provider,
            "error": str(exc),
        }


def _write_agent_call_result(output_dir: Path, agent_id: str, result: dict) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{agent_id}_agent_call.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return str(path)


def _route_agent_call(agent: dict, prompt: str, output_dir: Path, env_cache: dict[str, str], max_tokens: int) -> dict:
    provider = (agent.get("provider") or "").lower()
    if provider in {"openai", "openai-compatible", ""}:
        return _call_openai_agent(agent, prompt, output_dir, env_cache, max_tokens)
    if provider in {"notebooklm", "notebooklm-web", "notebooklm-ui"}:
        return _notebooklm_fallback(agent, prompt, output_dir)
    return {
        "ok": False,
        "agent_id": agent.get("agent_id"),
        "provider": provider or "unknown",
        "error": f"Unsupported provider '{provider}'. Supported providers: openai, notebooklm.",
    }


def _notebooklm_fallback(agent: dict, prompt: str, output_dir: Path) -> dict:
    notebook_url = agent.get("notebook_url") or DEFAULT_NOTEBOOKLM_URL
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{agent.get('agent_id')}_notebooklm.json"
    result = {
        "ok": False,
        "agent_id": agent.get("agent_id"),
        "provider": "notebooklm-web",
        "mode": "manual",
        "message": (
            "NotebookLM has no documented public REST API endpoint in this code path. "
            "Use the web UI with the notebook id and paste this prompt."
        ),
        "prompt": prompt,
        "notebook_url": notebook_url,
        "generated_at": _now_iso(),
    }
    path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    result["output_path"] = str(path)
    return result


def _new_manifest(agent_id: str, name: str, role: str, owner: str, max_mb: int) -> dict:
    return {
        "agent_id": agent_id,
        "name": name or agent_id,
        "role": role or "",
        "owner": owner or "",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "storage": {
            "max_bytes": max_mb * 1024 * 1024,
            "notes_count": 0,
            "books_count": 0,
            "apps_count": 0,
            "notes": [],
            "books": [],
            "apps": [],
        },
        "utilities": [],
        "flux_state_hint": "polly",
    }


def _touch_note_file(pad_dir: Path, title: str, content: str) -> Path:
    notes_dir = pad_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    note_id = uuid.uuid4().hex[:10]
    safe_title = re.sub(r"[^A-Za-z0-9._-]+", "-", title.strip().lower())[:35].strip("-") or "note"
    filename = f"{safe_title}-{note_id}.md"
    path = notes_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def cmd_pollypad_init(args: argparse.Namespace) -> int:
    if not _ensure_agent_id(args.agent_id):
        print("Invalid --agent-id. Use 2-64 chars: letters, numbers, . _ -")
        return 2
    pad_dir = _pad_dir(args.repo_root, args.agent_id)
    manifest_path = _manifest_path(pad_dir)
    if pad_dir.exists() and not args.force:
        print(f"Pad already exists: {pad_dir}")
        return 1

    manifest = _new_manifest(
        args.agent_id,
        args.name,
        args.role,
        args.owner,
        max_mb=args.max_storage_mb,
    )
    _save_manifest(manifest_path, manifest)
    for folder in ["notes", "books", "apps", "assets"]:
        (pad_dir / folder).mkdir(parents=True, exist_ok=True)
    print(f"Created Polly Pad for {args.agent_id}")
    print(f"Path: {pad_dir}")
    print(f"Manifest: {manifest_path}")
    return 0


def cmd_pollypad_list(args: argparse.Namespace) -> int:
    root = _pad_root(args.repo_root)
    if not root.exists():
        print("No polly pads configured yet.")
        return 0
    for path in sorted(root.iterdir()):
        if not path.is_dir():
            continue
        manifest_file = path / "manifest.json"
        if not manifest_file.exists():
            print(f"{path.name}: (missing manifest)")
            continue
        try:
            manifest = _load_manifest(manifest_file)
            print(
                f"{manifest.get('agent_id', path.name)} | "
                f"{manifest.get('name', '')} | role={manifest.get('role', 'unknown')} | "
                f"notes={manifest.get('storage', {}).get('notes_count', 0)} "
                f"books={manifest.get('storage', {}).get('books_count', 0)} "
                f"apps={manifest.get('storage', {}).get('apps_count', 0)}"
            )
        except Exception as exc:  # pragma: no cover - best-effort CLI readability
            print(f"{path.name}: manifest read error ({exc})")
    return 0


def cmd_pollypad_note_add(args: argparse.Namespace) -> int:
    pad_dir = _pad_dir(args.repo_root, args.agent_id)
    manifest_file = _manifest_path(pad_dir)
    if not manifest_file.exists():
        print("Pad not found. Run pollypad init first.")
        return 1
    if args.text is None and args.file is None:
        print("Use --text or --file to add note content.")
        return 2
    if args.text is not None and args.file is not None:
        print("Use only one of --text or --file.")
        return 2
    content = args.text if args.text is not None else Path(args.file).read_text(encoding="utf-8")
    path = _touch_note_file(pad_dir, args.title, content)
    manifest = _load_manifest(manifest_file)
    entry = {
        "id": uuid.uuid4().hex,
        "title": args.title,
        "path": f"notes/{path.name}",
        "updated_at": _now_iso(),
        "tags": args.tags or [],
    }
    manifest["storage"]["notes"].append(entry)
    manifest["storage"]["notes_count"] = len(manifest["storage"]["notes"])
    manifest["updated_at"] = _now_iso()
    _save_manifest(manifest_file, manifest)
    print(f"Saved note: {path}")
    return 0


def cmd_pollypad_note_list(args: argparse.Namespace) -> int:
    pad_dir = _pad_dir(args.repo_root, args.agent_id)
    manifest = _load_manifest(_manifest_path(pad_dir))
    for note in manifest.get("storage", {}).get("notes", []):
        print(f"{note['id']} | {note['title']} | {note['updated_at']} | {note['path']}")
    if not manifest.get("storage", {}).get("notes"):
        print("No notes yet.")
    return 0


def cmd_pollypad_book_add(args: argparse.Namespace) -> int:
    pad_dir = _pad_dir(args.repo_root, args.agent_id)
    manifest_file = _manifest_path(pad_dir)
    if not manifest_file.exists():
        print("Pad not found. Run pollypad init first.")
        return 1
    src = Path(args.path)
    if not src.exists():
        print(f"Missing source: {src}")
        return 2
    books_dir = pad_dir / "books"
    books_dir.mkdir(parents=True, exist_ok=True)
    target = books_dir / f"{uuid.uuid4().hex}_{src.name}"
    shutil.copy2(src, target)
    manifest = _load_manifest(manifest_file)
    manifest["storage"]["books"].append(
        {
            "id": uuid.uuid4().hex,
            "title": args.title or src.name,
            "source_path": str(src),
            "pad_path": str(target.relative_to(pad_dir)),
            "added_at": _now_iso(),
        }
    )
    manifest["storage"]["books_count"] = len(manifest["storage"]["books"])
    manifest["updated_at"] = _now_iso()
    _save_manifest(manifest_file, manifest)
    print(f"Added book: {target}")
    return 0


def cmd_pollypad_book_list(args: argparse.Namespace) -> int:
    manifest = _load_manifest(_manifest_path(_pad_dir(args.repo_root, args.agent_id)))
    for item in manifest.get("storage", {}).get("books", []):
        print(f"{item['id']} | {item['title']} | {item['pad_path']}")
    if not manifest.get("storage", {}).get("books"):
        print("No books yet.")
    return 0


def cmd_pollypad_app_install(args: argparse.Namespace) -> int:
    pad_dir = _pad_dir(args.repo_root, args.agent_id)
    manifest_file = _manifest_path(pad_dir)
    if not manifest_file.exists():
        print("Pad not found. Run pollypad init first.")
        return 1
    apps_dir = pad_dir / "apps"
    apps_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "id": uuid.uuid4().hex,
        "name": args.name,
        "description": args.description or "",
        "entrypoint": args.entrypoint,
        "installed_at": _now_iso(),
    }
    if args.script:
        src = Path(args.script)
        if not src.exists():
            print(f"Missing script: {src}")
            return 2
        target = apps_dir / src.name
        shutil.copy2(src, target)
        entry["local_script"] = str(target.relative_to(pad_dir))
    manifest = _load_manifest(manifest_file)
    manifest["storage"]["apps"].append(entry)
    manifest["storage"]["apps_count"] = len(manifest["storage"]["apps"])
    manifest["updated_at"] = _now_iso()
    _save_manifest(manifest_file, manifest)
    print(f"Installed app: {args.name}")
    return 0


def cmd_pollypad_app_list(args: argparse.Namespace) -> int:
    manifest = _load_manifest(_manifest_path(_pad_dir(args.repo_root, args.agent_id)))
    for item in manifest.get("storage", {}).get("apps", []):
        print(f"{item['id']} | {item['name']} | {item['description']} | {item['entrypoint']}")
    if not manifest.get("storage", {}).get("apps"):
        print("No apps yet.")
    return 0


def cmd_pollypad_snapshot(args: argparse.Namespace) -> int:
    pad_path = _pad_dir(args.repo_root, args.agent_id)
    manifest_path = _manifest_path(pad_path)
    if not manifest_path.exists():
        print("Pad not found. Run pollypad init first.")
        return 1
    manifest = _load_manifest(manifest_path)
    output = args.output or str(pad_path / "snapshot.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    print(f"Snapshot saved: {output}")
    return 0


def cmd_tongues(args: argparse.Namespace) -> int:
    script = args.repo_root / "six-tongues-cli.py"
    if not script.exists():
        print(f"Missing tongues CLI: {script}")
        return 1
    if args.tongue_args == ["selftest"]:
        return _run_script(script, [])
    if not args.tongue_args:
        print("No six-tongue subcommand provided. Try:")
        print("  tongues encode --tongue KO --in input.bin")
        print("  tongues xlate --src KO --dst AV")
        return 2
    return _run_script(script, args.tongue_args)


def cmd_gap_review(args: argparse.Namespace) -> int:
    script = args.repo_root / "scripts" / "notion_pipeline_gap_review.py"
    if not script.exists():
        print(f"Missing gap review script: {script}")
        return 1
    extra = [
        "--repo-root",
        str(args.repo_root),
        "--sync-config",
        str(args.sync_config),
        "--pipeline-config",
        str(args.pipeline_config),
        "--training-data",
        str(args.training_data),
        "--output",
        str(args.output),
        "--summary-path",
        str(args.summary_path),
    ]
    return _run_script(script, extra)


def cmd_self_improve(args: argparse.Namespace) -> int:
    gap_report = args.gap_report
    if args.run_gap:
        gap_script = args.repo_root / "scripts" / "notion_pipeline_gap_review.py"
        if not gap_script.exists():
            print(f"Missing gap review script: {gap_script}")
            return 1
        gap_report = args.output.parent / "self_improvement_notion_gap.json"
        gap_args = [
            "--repo-root",
            str(args.repo_root),
            "--sync-config",
            str(args.sync_config),
            "--pipeline-config",
            str(args.pipeline_config),
            "--training-data",
            str(args.training_data),
            "--output",
            str(gap_report),
            "--summary-path",
            str(gap_report.with_suffix(".md")),
        ]
        rc = _run_script(gap_script, gap_args)
        if rc != 0:
            return rc

    script = args.repo_root / "scripts" / "self_improvement_orchestrator.py"
    if not script.exists():
        print(f"Missing orchestrator script: {script}")
        return 1
    extra = [
        "--mode",
        args.mode,
        "--coherence-report",
        str(args.coherence_report),
        "--training-data",
        str(args.training_data),
        "--pipeline-config",
        str(args.pipeline_config),
        "--output",
        str(args.output),
        "--summary-path",
        str(args.summary),
    ]
    if gap_report:
        extra.extend(["--notion-gap-report", str(gap_report)])
    return _run_script(script, extra)


def cmd_web(args: argparse.Namespace) -> int:
    script = args.repo_root / "scripts" / "agentic_web_tool.py"
    if not script.exists():
        print(f"Missing web tool script: {script}")
        return 1
    base = [
        "--engine",
        args.engine,
        "--output-dir",
        str(args.output_dir),
    ]
    if args.web_cmd == "search":
        if not args.query:
            print("Missing --query")
            return 2
        base.extend(["search", "--query", args.query, "--max-results", str(args.max_results)])
    elif args.web_cmd == "capture":
        if not args.url:
            print("Missing --url")
            return 2
        base.extend(["capture", "--url", args.url])
    else:
        print("Unknown web command")
        return 2
    return _run_script(script, base)


def cmd_antivirus(args: argparse.Namespace) -> int:
    script = args.repo_root / "scripts" / "agentic_antivirus.py"
    if not script.exists():
        print(f"Missing antivirus script: {script}")
        return 1
    return _run_script(
        script,
        [
            "--repo-root",
            str(args.repo_root),
            "--output",
            str(args.output),
            "--summary",
            str(args.summary),
            "--ring-core",
            str(args.ring_core),
            "--ring-outer",
            str(args.ring_outer),
            *(["--geoseal"] if args.geoseal else []),
        ],
    )


def cmd_aetherauth(args: argparse.Namespace) -> int:
    script = args.repo_root / "scripts" / "agentic_aetherauth.py"
    if not script.exists():
        print(f"Missing aetherauth script: {script}")
        return 1

    command = [
        "--action",
        args.action,
        "--core-max",
        str(args.core_max),
        "--outer-max",
        str(args.outer_max),
        "--max-time-skew-ms",
        str(args.max_time_skew_ms),
        "--output",
        str(args.output),
        "--summary",
        str(args.summary),
    ]
    if args.context_json:
        command.extend(["--context-json", args.context_json])
    if args.context_vector:
        command.extend(["--context-vector", args.context_vector])
    if args.reference_vector:
        command.extend(["--reference-vector", args.reference_vector])
    if args.time_ms:
        command.extend(["--time-ms", str(args.time_ms)])
    if args.latitude is not None:
        command.extend(["--latitude", str(args.latitude)])
    if args.longitude is not None:
        command.extend(["--longitude", str(args.longitude)])
    if args.reference_latitude is not None:
        command.extend(["--reference-latitude", str(args.reference_latitude)])
    if args.reference_longitude is not None:
        command.extend(["--reference-longitude", str(args.reference_longitude)])
    if args.trusted_radius_km is not None:
        command.extend(["--trusted-radius-km", str(args.trusted_radius_km)])
    if args.location_core_radius_km is not None:
        command.extend(["--location-core-radius-km", str(args.location_core_radius_km)])
    if args.location_outer_radius_km is not None:
        command.extend(["--location-outer-radius-km", str(args.location_outer_radius_km)])
    if args.location_core_max is not None:
        command.extend(["--location-core-max", str(args.location_core_max)])
    if args.location_outer_max is not None:
        command.extend(["--location-outer-max", str(args.location_outer_max)])
    if args.enforce_location:
        command.extend(["--enforce-location"])
    if args.cpu is not None:
        command.extend(["--cpu", str(args.cpu)])
    if args.memory is not None:
        command.extend(["--memory", str(args.memory)])
    if args.intent is not None:
        command.extend(["--intent", str(args.intent)])
    if args.history is not None:
        command.extend(["--history", str(args.history)])
    if args.secret:
        command.extend(["--secret", args.secret])
    if args.signature:
        command.extend(["--signature", args.signature])
    return _run_script(script, command)


def cmd_agent_bootstrap(args: argparse.Namespace) -> int:
    registry_path = _agent_registry_path(args.repo_root)
    registry = _load_agent_registry(registry_path)
    current_agents = registry.get("agents", {})

    if current_agents and not args.append and not args.force:
        print(f"Agent registry already exists with {len(current_agents)} agent(s): {', '.join(sorted(current_agents))}")
        print("Use --append to add defaults or --force to replace.")
        return 2

    seed_agents: dict[str, dict] = {}
    seed_agents["codex"] = _new_agent_entry(
        agent_id="codex",
        provider="openai",
        display_name="Codex",
        description=(
            "General-purpose coding and architecture agent using OpenAI Chat Completions API."
        ),
        api_key_env="OPENAI_API_KEY",
        model=args.codex_model or "gpt-4o-mini",
    )
    if args.include_notebooklm:
        seed_agents["notebooklm-main"] = _new_agent_entry(
            agent_id="notebooklm-main",
            provider="notebooklm",
            display_name="NotebookLM",
            description="Research and reflection assistant through NotebookLM.",
            notebook_url=DEFAULT_NOTEBOOKLM_URL,
        )

    if args.force and not args.append:
        registry["agents"] = {}
        current_agents = {}

    for aid, entry in seed_agents.items():
        if not args.force and not args.append and not current_agents.get(aid):
            current_agents[aid] = entry
        elif args.force or args.append or aid not in current_agents:
            current_agents[aid] = entry
        else:
            print(f"Skipping existing agent '{aid}' (use --force to overwrite).")

    registry["agents"] = current_agents
    registry["version"] = "1.0.0"
    _save_agent_registry(registry_path, registry)
    print(f"Agent registry written: {registry_path}")
    for aid, entry in sorted(current_agents.items()):
        print(f" - {aid}: {entry.get('provider')} ({entry.get('display_name')})")
    return 0


def cmd_agent_list(args: argparse.Namespace) -> int:
    registry = _load_agent_registry(_agent_registry_path(args.repo_root))
    agents = registry.get("agents", {})
    if not agents:
        print("No agents registered. Run: scbe-system agent bootstrap")
        return 0
    print(f"Agent registry: {len(agents)} entries")
    for aid in sorted(agents):
        entry = agents[aid]
        status = "enabled" if entry.get("enabled", True) else "disabled"
        print(
            f"{aid:24} | {entry.get('provider', 'unknown'):<12} | "
            f"{entry.get('display_name', ''):<18} | {status}"
        )
    return 0


def cmd_agent_remove(args: argparse.Namespace) -> int:
    registry_path = _agent_registry_path(args.repo_root)
    registry = _load_agent_registry(registry_path)
    if args.agent_id not in registry.get("agents", {}):
        print(f"Agent '{args.agent_id}' not found")
        return 2
    registry["agents"].pop(args.agent_id, None)
    _save_agent_registry(registry_path, registry)
    print(f"Removed agent '{args.agent_id}' from {registry_path}")
    return 0


def cmd_agent_register(args: argparse.Namespace) -> int:
    if not _ensure_agent_id(args.agent_id):
        print("Invalid agent_id. Use 2-64 chars [A-Za-z0-9._-]")
        return 2

    registry_path = _agent_registry_path(args.repo_root)
    registry = _load_agent_registry(registry_path)
    providers = {"openai", "notebooklm"}
    if args.provider not in providers:
        print(f"Unsupported provider '{args.provider}'. Use {', '.join(sorted(providers))}")
        return 2

    capabilities = [c.strip() for c in args.capabilities.split(",")] if args.capabilities else []
    if args.provider == "openai" and not args.api_key_env:
        args.api_key_env = "OPENAI_API_KEY"

    entry = _new_agent_entry(
        agent_id=args.agent_id,
        provider=args.provider,
        display_name=args.display_name,
        description=args.description,
        api_key_env=args.api_key_env,
        model=args.model,
        endpoint=args.endpoint,
        notebook_url=args.notebook_url,
    )
    if capabilities:
        entry["capabilities"] = capabilities

    registry.setdefault("agents", {})[args.agent_id] = entry
    registry["version"] = "1.0.0"
    _save_agent_registry(registry_path, registry)
    print(f"Registered agent '{args.agent_id}' ({args.provider})")
    return 0


def cmd_agent_ping(args: argparse.Namespace) -> int:
    env_cache = _read_env_file(args.repo_root)
    registry = _load_agent_registry(_agent_registry_path(args.repo_root))
    agent_id = args.agent_id
    if agent_id == "__all__":
        candidates = [a for a, entry in registry.get("agents", {}).items() if entry.get("enabled", True)]
    else:
        entry = registry.get("agents", {}).get(agent_id)
        if not entry:
            print(f"Unknown agent '{agent_id}'")
            return 2
        candidates = [agent_id]

    if not candidates:
        print("No enabled agents available.")
        return 0

    print("Pinging agents...")
    out_dir = Path(args.output_dir)
    for aid in candidates:
        entry = registry["agents"][aid]
        result = _route_agent_call(
            entry,
            "Reply with one line: 'SCBE ping OK'.",
            out_dir,
            env_cache,
            args.max_tokens,
        )
        output_path = _write_agent_call_result(out_dir, f"{aid}_ping", result)
        result["output_path"] = output_path
        print(f"{aid:20} -> {'OK' if result.get('ok') else 'FAILED'}")
    return 0


def cmd_agent_call(args: argparse.Namespace) -> int:
    registry = _load_agent_registry(_agent_registry_path(args.repo_root))
    env_cache = _read_env_file(args.repo_root)
    out_dir = Path(args.output_dir)

    if args.all:
        agent_ids = [a for a, entry in registry.get("agents", {}).items() if entry.get("enabled", True)]
    else:
        agent_ids = [s.strip() for s in args.agent_id.split(",") if s.strip()]

    if not agent_ids:
        print("No agents specified. Use --all or --agent-id.")
        return 2

    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    else:
        prompt = args.prompt

    if not prompt:
        print("Missing prompt. Provide --prompt or --prompt-file.")
        return 2

    summary = {
        "called_at": _now_iso(),
        "prompt": prompt,
        "agents": {},
        "succeeded": 0,
        "failed": 0,
    }
    for aid in agent_ids:
        entry = registry.get("agents", {}).get(aid)
        if not entry:
            summary["agents"][aid] = {"ok": False, "error": "agent not found"}
            summary["failed"] += 1
            continue
        if not entry.get("enabled", True):
            summary["agents"][aid] = {"ok": False, "error": "agent disabled"}
            summary["failed"] += 1
            continue
        result = _route_agent_call(entry, prompt, out_dir, env_cache, args.max_tokens)
        result["agent_id"] = aid
        result_path = _write_agent_call_result(out_dir, aid, result)
        result["output_path"] = result_path
        summary["agents"][aid] = {"ok": result.get("ok", False), "output_path": result_path}
        if result.get("ok"):
            summary["succeeded"] += 1
            if args.show_output:
                print(f"\n[{aid}]")
                print(result.get("content", ""))
        else:
            summary["failed"] += 1
            if args.show_output:
                print(f"[{aid}] FAIL: {result.get('error')}")

    summary_path = out_dir / "agent_call_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Summary: {summary['succeeded']} ok, {summary['failed']} failed")
    print(f"Saved: {summary_path}")
    return 0 if summary["failed"] == 0 else 1


def cmd_status(args: argparse.Namespace) -> int:
    paths = [
        "artifacts/self_improvement_manifest.json",
        "artifacts/notion_pipeline_gap_review.json",
        "artifacts/aetherauth_decision.json",
        "artifacts/aetherauth_decision.md",
        "artifacts/agentic_antivirus_report.md",
        "artifacts/agentic_antivirus_report.json",
        "artifacts/self_improvement_summary.md",
    ]
    print("SCBE Runbook status check")
    print("-" * 28)
    for path in paths:
        file_path = args.repo_root / path
        status = "present" if file_path.exists() else "missing"
        print(f"{status:8} {path}")
    print("\nTip: run `status` after each cycle and open `artifacts/*.md` files for human review.")
    print("Notion/AI notes reference points:")
    print("- docs/SELF_IMPROVEMENT_AGENTS.md")
    print("- .scbe/next-coder-marker.md")
    print("- scripts/notion_pipeline_gap_review.py")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scbe-system",
        description="SCBE-AETHERMOORE unified CLI for system operations",
    )
    parser.add_argument(
        "--repo-root",
        default=str(DEFAULT_REPO_ROOT),
        help="Repository root (default: current checkout)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    tongues = sub.add_parser("tongues", help="Six-Tongues toolkit passthrough")
    tongues.add_argument("tongue_args", nargs=argparse.REMAINDER, help="Args for six-tongues-cli.py")
    tongues.set_defaults(func=cmd_tongues)

    gap = sub.add_parser("notion-gap", help="Run notion-to-pipeline gap review")
    gap.add_argument("--sync-config", default="scripts/sync-config.json")
    gap.add_argument("--pipeline-config", default="training/vertex_pipeline_config.yaml")
    gap.add_argument("--training-data", default="training-data")
    gap.add_argument("--output", default="artifacts/notion_pipeline_gap_review.json")
    gap.add_argument("--summary-path", default="artifacts/notion_pipeline_gap_review.md")
    gap.set_defaults(func=cmd_gap_review)

    improve = sub.add_parser("self-improve", help="Run self-improvement orchestrator")
    improve.add_argument("--mode", default="all", choices=("all", "code-assistant", "ai-nodal-dev-specialist", "fine-tune-funnel"))
    improve.add_argument("--coherence-report", default="coherence-report.json")
    improve.add_argument("--training-data", default="training-data")
    improve.add_argument("--pipeline-config", default="training/vertex_pipeline_config.yaml")
    improve.add_argument("--notion-gap-report", default="")
    improve.add_argument("--run-gap", action="store_true", help="Run notion gap review before orchestration")
    improve.add_argument("--sync-config", default="scripts/sync-config.json")
    improve.add_argument("--output", default="artifacts/self_improvement_manifest.json")
    improve.add_argument("--summary", default="artifacts/self_improvement_summary.md")
    improve.set_defaults(func=cmd_self_improve)

    web = sub.add_parser("web", help="Run web lookup/capture helpers")
    web.add_argument("--engine", choices=("auto", "playwright", "http"), default="auto")
    web.add_argument("--output-dir", default="artifacts/web_tool")
    web_sub = web.add_subparsers(dest="web_cmd", required=True)
    web_search = web_sub.add_parser("search", help="DuckDuckGo search capture")
    web_search.add_argument("--query", required=True)
    web_search.add_argument("--max-results", type=int, default=8)
    web_capture = web_sub.add_parser("capture", help="Capture URL using browser/http")
    web_capture.add_argument("--url", required=True)
    web.set_defaults(func=cmd_web)

    av = sub.add_parser("antivirus", help="Run lightweight static safety scan")
    av.add_argument("--output", default="artifacts/agentic_antivirus_report.json")
    av.add_argument("--summary", default="artifacts/agentic_antivirus_report.md")
    av.add_argument("--geoseal", action="store_true", help="Enable GeoSeal trust ring scoring")
    av.add_argument("--ring-core", type=float, default=0.70, help="Trust threshold for CORE ring")
    av.add_argument("--ring-outer", type=float, default=0.45, help="Trust threshold for OUTER ring")
    av.set_defaults(func=cmd_antivirus)

    auth = sub.add_parser("aetherauth", help="Run context-bound AetherAuth-style access decision")
    auth.add_argument("--action", default="read", help="Requested action")
    auth.add_argument("--core-max", type=float, default=0.30, help="Core ring cutoff")
    auth.add_argument("--outer-max", type=float, default=0.70, help="Outer ring cutoff")
    auth.add_argument("--max-time-skew-ms", type=int, default=15 * 60 * 1000, help="Maximum acceptable clock skew")
    auth.add_argument("--context-json", default="", help="Context JSON object/list")
    auth.add_argument("--context-vector", default="", help="CSV 6D context vector")
    auth.add_argument("--reference-vector", default="", help="CSV expected reference vector")
    auth.add_argument("--time-ms", type=int, default=None, help="Event time in unix milliseconds")
    auth.add_argument("--latitude", type=float, default=None, help="Geospatial latitude")
    auth.add_argument("--longitude", type=float, default=None, help="Geospatial longitude")
    auth.add_argument("--cpu", type=float, default=None, help="CPU utilization metric")
    auth.add_argument("--memory", type=float, default=None, help="Memory utilization metric")
    auth.add_argument("--intent", type=float, default=None, help="Intent score")
    auth.add_argument("--history", type=float, default=None, help="History score")
    auth.add_argument("--reference-latitude", type=float, default=None, help="Reference latitude for geospatial matching")
    auth.add_argument("--reference-longitude", type=float, default=None, help="Reference longitude for geospatial matching")
    auth.add_argument("--trusted-radius-km", type=float, default=50.0, help="GeoSeal trusted radius in km")
    auth.add_argument("--location-core-radius-km", type=float, default=5.0, help="GeoSeal location core radius in km")
    auth.add_argument("--location-outer-radius-km", type=float, default=80.0, help="GeoSeal location outer radius in km")
    auth.add_argument("--location-core-max", type=float, default=None, help="Location core ring max risk")
    auth.add_argument("--location-outer-max", type=float, default=None, help="Location outer ring max risk")
    auth.add_argument("--enforce-location", action="store_true", help="Reject when location is missing/unresolvable")
    auth.add_argument("--secret", default="", help="Optional shared secret for envelope signature")
    auth.add_argument("--signature", default="", help="Optional request signature")
    auth.add_argument("--output", default="artifacts/aetherauth_decision.json")
    auth.add_argument("--summary", default="artifacts/aetherauth_decision.md")
    auth.set_defaults(func=cmd_aetherauth)

    agent = sub.add_parser("agent", help="Manage and call Squad AI agents")
    agent_sub = agent.add_subparsers(dest="agent_cmd", required=True)
    a_boot = agent_sub.add_parser("bootstrap", help="Create or refresh default agent registry")
    a_boot.add_argument("--append", action="store_true", help="Add defaults while keeping existing agents")
    a_boot.add_argument("--force", action="store_true", help="Replace existing registry before bootstrapping")
    a_boot.add_argument("--include-notebooklm", action="store_true", default=True, help="Include NotebookLM default entry")
    a_boot.add_argument("--no-include-notebooklm", dest="include_notebooklm", action="store_false", help="Skip NotebookLM default entry")
    a_boot.add_argument("--codex-model", default="gpt-4o-mini")
    a_boot.set_defaults(func=cmd_agent_bootstrap)

    a_list = agent_sub.add_parser("list", help="List registered squad agents")
    a_list.set_defaults(func=cmd_agent_list)

    a_reg = agent_sub.add_parser("register", help="Register or update one squad agent")
    a_reg.add_argument("--agent-id", required=True)
    a_reg.add_argument("--provider", required=True, choices=("openai", "notebooklm"))
    a_reg.add_argument("--display-name")
    a_reg.add_argument("--description")
    a_reg.add_argument("--api-key-env", default="")
    a_reg.add_argument("--model", default="gpt-4o-mini")
    a_reg.add_argument("--endpoint", default="")
    a_reg.add_argument("--notebook-url", default=DEFAULT_NOTEBOOKLM_URL)
    a_reg.add_argument("--capabilities", default="")
    a_reg.set_defaults(func=cmd_agent_register)

    a_rm = agent_sub.add_parser("remove", help="Remove a squad agent")
    a_rm.add_argument("--agent-id", required=True)
    a_rm.set_defaults(func=cmd_agent_remove)

    a_ping = agent_sub.add_parser("ping", help="Send a simple ping prompt to one or all agents")
    a_ping.add_argument("--agent-id", default="__all__")
    a_ping.add_argument("--output-dir", default="artifacts/agent_calls")
    a_ping.add_argument("--max-tokens", type=int, default=64)
    a_ping.set_defaults(func=cmd_agent_ping)

    a_call = agent_sub.add_parser("call", help="Call one or more squad agents")
    a_call.add_argument("--agent-id", default="")
    a_call.add_argument("--all", action="store_true", help="Call every enabled agent")
    a_call.add_argument("--prompt", default="")
    a_call.add_argument("--prompt-file")
    a_call.add_argument("--output-dir", default="artifacts/agent_calls")
    a_call.add_argument("--max-tokens", type=int, default=420)
    a_call.add_argument("--show-output", action="store_true", help="Print successful model output")
    a_call.set_defaults(func=cmd_agent_call)

    sub.add_parser("status", help="Show artifact presence for last cycle").set_defaults(func=cmd_status)

    pollypad = sub.add_parser("pollypad", help="Agent personal storage capsule (Kindle-style)")
    pollypad.add_argument("--agent-root", default=str(DEFAULT_PAD_ROOT), help="Optional root path for polly pads")
    pollypad_sub = pollypad.add_subparsers(dest="pollypad_cmd", required=True)

    pp_init = pollypad_sub.add_parser("init", help="Create a new Polly Pad")
    pp_init.add_argument("--agent-id", required=True)
    pp_init.add_argument("--name", default="")
    pp_init.add_argument("--role", default="")
    pp_init.add_argument("--owner", default="")
    pp_init.add_argument("--max-storage-mb", type=int, default=256)
    pp_init.add_argument("--force", action="store_true", help="Overwrite existing pad")
    pp_init.set_defaults(func=cmd_pollypad_init)

    pollypad_sub.add_parser("list", help="List all Polly Pads").set_defaults(func=cmd_pollypad_list)

    pp_note = pollypad_sub.add_parser("note", help="Manage pad notes")
    pp_note_sub = pp_note.add_subparsers(dest="note_cmd", required=True)
    pp_note_add = pp_note_sub.add_parser("add", help="Add a note")
    pp_note_add.add_argument("--agent-id", required=True)
    pp_note_add.add_argument("--title", required=True)
    pp_note_add.add_argument("--text")
    pp_note_add.add_argument("--file")
    pp_note_add.add_argument("--tags", nargs="*")
    pp_note_add.set_defaults(func=cmd_pollypad_note_add)
    pp_note_list = pp_note_sub.add_parser("list", help="List notes")
    pp_note_list.add_argument("--agent-id", required=True)
    pp_note_list.set_defaults(func=cmd_pollypad_note_list)

    pp_book = pollypad_sub.add_parser("book", help="Manage pad books")
    pp_book_sub = pp_book.add_subparsers(dest="book_cmd", required=True)
    pp_book_add = pp_book_sub.add_parser("add", help="Add a book file")
    pp_book_add.add_argument("--agent-id", required=True)
    pp_book_add.add_argument("--title")
    pp_book_add.add_argument("--path", required=True)
    pp_book_add.set_defaults(func=cmd_pollypad_book_add)
    pp_book_list = pp_book_sub.add_parser("list", help="List books")
    pp_book_list.add_argument("--agent-id", required=True)
    pp_book_list.set_defaults(func=cmd_pollypad_book_list)

    pp_app = pollypad_sub.add_parser("app", help="Manage pad apps/utilities")
    pp_app_sub = pp_app.add_subparsers(dest="app_cmd", required=True)
    pp_app_install = pp_app_sub.add_parser("install", help="Install utility/app entry")
    pp_app_install.add_argument("--agent-id", required=True)
    pp_app_install.add_argument("--name", required=True)
    pp_app_install.add_argument("--entrypoint", required=True, help="Run command or path reference")
    pp_app_install.add_argument("--description")
    pp_app_install.add_argument("--script", help="Optional script to copy into this pad")
    pp_app_install.set_defaults(func=cmd_pollypad_app_install)
    pp_app_list = pp_app_sub.add_parser("list", help="List apps/utilities")
    pp_app_list.add_argument("--agent-id", required=True)
    pp_app_list.set_defaults(func=cmd_pollypad_app_list)

    pp_snapshot = pollypad_sub.add_parser("snapshot", help="Export current pad snapshot JSON")
    pp_snapshot.add_argument("--agent-id", required=True)
    pp_snapshot.add_argument("--output")
    pp_snapshot.set_defaults(func=cmd_pollypad_snapshot)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.repo_root = Path(args.repo_root).resolve()
    if args.command == "pollypad":
        pad_root = args.agent_root
        # Keep root consistent with any provided override.
        global DEFAULT_PAD_ROOT
        if isinstance(pad_root, str):
            DEFAULT_PAD_ROOT = Path(pad_root)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
