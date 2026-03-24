#!/usr/bin/env python3
"""NotebookLM connector (browser-first) for SCBE terminal workflows.

Actions:
- profile: runtime readiness + registry summary
- resolve-notebook: resolve notebook by url/id/title from registry
- create-notebook: create notebook (or reuse by title from registry)
- add-source-url: add URL source to notebook (url or title target)
- seed-notebooks: create/reuse N notebooks and attach shared URLs
- ingest-report: read local report files, extract URLs, and attach as sources
- agent-dual: visual lane (read preview) + writer lane (sources/prompt submit)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKSPACE_URL = "https://notebooklm.google.com/"
DEFAULT_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "notebooklm"
DEFAULT_REGISTRY_PATH = DEFAULT_ARTIFACT_DIR / "notebook_registry.json"
URL_PATTERN = re.compile(r"https?://[^\s\]\)>'\"`]+", flags=re.IGNORECASE)
NOTEBOOK_ID_PATTERN = re.compile(r"/notebook/([a-zA-Z0-9-]+)")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_playwriter_bin() -> str:
    for candidate in ("playwriter", "playwriter.cmd"):
        found = shutil.which(candidate)
        if found:
            return found
    return "playwriter"


def _extract_json_blob(text: str) -> dict[str, Any]:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith("{") and line.endswith("}"):
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue
    return {}


def run_playwriter(session_id: str, expr: str, timeout_ms: int) -> dict[str, Any]:
    cmd = [_resolve_playwriter_bin(), "-s", str(session_id), "-e", expr, "--timeout", str(timeout_ms)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    payload = {
        "ok": proc.returncode == 0,
        "return_code": int(proc.returncode),
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
    }
    parsed = _extract_json_blob(payload["stdout"])
    if parsed:
        payload["parsed"] = parsed
    return payload


def _normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def _extract_notebook_id(url: str) -> str:
    match = NOTEBOOK_ID_PATTERN.search(url or "")
    return match.group(1) if match else ""


def _empty_registry() -> dict[str, Any]:
    return {"version": "1.0", "updated_at": utc_now(), "notebooks": []}


def _load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _empty_registry()
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(parsed, dict):
            return _empty_registry()
        notebooks = parsed.get("notebooks", [])
        if not isinstance(notebooks, list):
            parsed["notebooks"] = []
        parsed.setdefault("version", "1.0")
        parsed.setdefault("updated_at", utc_now())
        return parsed
    except Exception:
        return _empty_registry()


def _save_registry(path: Path, registry: dict[str, Any]) -> str:
    registry["updated_at"] = utc_now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    return str(path.resolve())


def _find_notebook_record(
    registry: dict[str, Any],
    *,
    title: str = "",
    notebook_url: str = "",
    notebook_id: str = "",
) -> dict[str, Any] | None:
    title_norm = _normalize_title(title)
    target_id = notebook_id or _extract_notebook_id(notebook_url)
    for row in registry.get("notebooks", []):
        if notebook_url and str(row.get("notebook_url", "")).strip() == notebook_url.strip():
            return row
        if target_id and str(row.get("notebook_id", "")).strip() == target_id.strip():
            return row
        if title_norm and str(row.get("title_norm", "")).strip() == title_norm:
            return row
    return None


def _upsert_notebook_record(
    registry: dict[str, Any],
    *,
    title: str,
    notebook_url: str,
    session_id: str,
    source_urls: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = _find_notebook_record(registry, title=title, notebook_url=notebook_url)
    now = utc_now()
    if row is None:
        row = {
            "notebook_id": _extract_notebook_id(notebook_url),
            "title": title.strip(),
            "title_norm": _normalize_title(title),
            "notebook_url": notebook_url.strip(),
            "created_at": now,
            "updated_at": now,
            "last_session_id": str(session_id),
            "sources": [],
            "metadata": {},
        }
        registry.setdefault("notebooks", []).append(row)
    else:
        row["updated_at"] = now
        if title.strip():
            row["title"] = title.strip()
            row["title_norm"] = _normalize_title(title)
        if notebook_url.strip():
            row["notebook_url"] = notebook_url.strip()
            row["notebook_id"] = _extract_notebook_id(notebook_url)
        row["last_session_id"] = str(session_id)

    if source_urls:
        existing = [str(x).strip() for x in row.get("sources", []) if str(x).strip()]
        for src in source_urls:
            if src not in existing:
                existing.append(src)
        row["sources"] = existing

    if metadata:
        merged = dict(row.get("metadata", {}))
        merged.update(metadata)
        row["metadata"] = merged

    return row


def _validate_notebook_url(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return ""
    if not re.match(r"^https?://", value, flags=re.IGNORECASE):
        raise ValueError("notebook_url must be an http(s) URL")
    return value


def _save_output(path: str, payload: dict[str, Any]) -> str:
    out_path = (
        Path(path)
        if path
        else (
            DEFAULT_ARTIFACT_DIR / f"notebooklm_connector_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        )
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(out_path.resolve())


def _load_source_urls(args: argparse.Namespace) -> list[str]:
    urls = [u.strip() for u in (args.source_url or []) if str(u).strip()]
    if args.source_url_file:
        lines = Path(args.source_url_file).read_text(encoding="utf-8").splitlines()
        urls.extend([line.strip() for line in lines if line.strip() and not line.strip().startswith("#")])
    deduped: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def _extract_urls_from_report_files(paths: list[str]) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for raw_path in paths:
        path = Path(raw_path).expanduser().resolve()
        if not path.exists() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in URL_PATTERN.findall(text):
            url = match.strip().rstrip(".,;")
            if url and url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def _resolve_notebook_target(args: argparse.Namespace, registry: dict[str, Any]) -> tuple[str, str, str, bool]:
    notebook_url = _validate_notebook_url(args.notebook_url)
    notebook_id = (args.notebook_id or "").strip()
    title = (args.title or "").strip()
    if notebook_url:
        record = _find_notebook_record(registry, notebook_url=notebook_url)
        if record is not None and not title:
            title = str(record.get("title", "")).strip()
        return notebook_url, notebook_id or _extract_notebook_id(notebook_url), title, bool(record is not None)

    record = _find_notebook_record(registry, title=title, notebook_id=notebook_id)
    if record is None:
        raise ValueError("Notebook target not found. Provide --notebook-url or a known --title/--notebook-id.")
    return (
        str(record.get("notebook_url", "")).strip(),
        str(record.get("notebook_id", "")).strip(),
        str(record.get("title", "")).strip(),
        True,
    )


def _js_create_notebook(workspace_url: str, title: str) -> str:
    workspace_lit = json.dumps(workspace_url)
    title_lit = json.dumps(title)
    return (
        f"const wait=(ms)=>new Promise(r=>setTimeout(r,ms));"
        f"await page.goto({workspace_lit},{{waitUntil:'domcontentloaded'}});"
        "await wait(1000);"
        "const buttons=["
        "page.getByRole('button',{name:/new notebook/i}),"
        "page.getByText(/new notebook/i),"
        "page.locator('button:has-text(\"New notebook\")')"
        "];"
        "let clicked=false;"
        "for(const b of buttons){if(await b.count()){await b.first().click();clicked=true;break;}}"
        "if(!clicked){throw new Error('New notebook button not found.');}"
        "await wait(1700);"
        f"const desiredTitle={title_lit};"
        "if(desiredTitle){"
        "const titleFields=["
        "page.locator('input[aria-label*=\"title\" i]'),"
        "page.getByRole('textbox',{name:/title/i}),"
        "page.locator('[contenteditable=\"true\"]')"
        "];"
        "for(const t of titleFields){if(await t.count()){try{await t.first().click();await t.first().fill(desiredTitle);break;}catch(_err){}}}"
        "}"
        "console.log(JSON.stringify({ok:true, notebook_url:page.url(), page_title:await page.title()}));"
    )


def _js_add_source_url(notebook_url: str, source_url: str) -> str:
    notebook_lit = json.dumps(notebook_url)
    source_lit = json.dumps(source_url)
    return (
        f"const wait=(ms)=>new Promise(r=>setTimeout(r,ms));"
        f"await page.goto({notebook_lit},{{waitUntil:'domcontentloaded'}});"
        "await wait(1200);"
        "const addButtons=["
        "page.getByRole('button',{name:/add( a)? source/i}),"
        "page.getByText(/add source/i),"
        "page.locator('button:has-text(\"Add\")')"
        "];"
        "let addClicked=false;"
        "for(const b of addButtons){if(await b.count()){await b.first().click();addClicked=true;break;}}"
        "if(!addClicked){throw new Error('Add source button not found.');}"
        "await wait(700);"
        "const tabs=[page.getByRole('button',{name:/website|link|url/i}),page.getByText(/website|link|url/i)];"
        "for(const t of tabs){if(await t.count()){try{await t.first().click();break;}catch(_err){}}}"
        f"const src={source_lit};"
        "const inputs=[page.locator('input[type=\"url\"]'),page.locator('input[placeholder*=\"http\" i]'),page.getByRole('textbox')];"
        "let typed=false;"
        "for(const i of inputs){if(await i.count()){try{await i.first().click();await i.first().fill(src);await i.first().press('Enter');typed=true;break;}catch(_err){}}}"
        "if(!typed){throw new Error('Source URL input not found.');}"
        "await wait(1400);"
        "console.log(JSON.stringify({ok:true, notebook_url:page.url(), source_url:src}));"
    )


def _js_view_notebook(notebook_url: str, preview_chars: int) -> str:
    notebook_lit = json.dumps(notebook_url)
    return (
        f"const wait=(ms)=>new Promise(r=>setTimeout(r,ms));"
        f"await page.goto({notebook_lit},{{waitUntil:'domcontentloaded'}});"
        "await wait(1200);"
        f"const maxChars={int(max(100, preview_chars))};"
        "const body=(document.body && document.body.innerText) ? document.body.innerText : '';"
        "console.log(JSON.stringify({ok:true, notebook_url:page.url(), page_title:await page.title(), preview:body.slice(0,maxChars)}));"
    )


def _js_submit_prompt(notebook_url: str, prompt: str) -> str:
    notebook_lit = json.dumps(notebook_url)
    prompt_lit = json.dumps(prompt)
    return (
        f"const wait=(ms)=>new Promise(r=>setTimeout(r,ms));"
        f"await page.goto({notebook_lit},{{waitUntil:'domcontentloaded'}});"
        "await wait(1200);"
        f"const p={prompt_lit};"
        "const inputs=["
        "page.getByRole('textbox'),"
        "page.locator('textarea'),"
        "page.locator('[contenteditable=\"true\"]')"
        "];"
        "let sent=false;"
        "for(const i of inputs){if(await i.count()){try{await i.first().click();await i.first().fill(p);await i.first().press('Enter');sent=true;break;}catch(_err){}}}"
        "if(!sent){throw new Error('Notebook prompt input not found.');}"
        "await wait(2600);"
        "const body=(document.body && document.body.innerText) ? document.body.innerText : '';"
        "console.log(JSON.stringify({ok:true, notebook_url:page.url(), prompt_submitted:true, preview:body.slice(0,1200)}));"
    )


def _add_source_once(args: argparse.Namespace, notebook_url: str, source_url: str) -> dict[str, Any]:
    expr = _js_add_source_url(notebook_url, source_url)
    if args.dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "action": "add-source-url",
            "notebook_url": notebook_url,
            "source_url": source_url,
            "expr": expr,
            "timestamp": utc_now(),
        }
    play = run_playwriter(args.session, expr, args.timeout_ms)
    return {
        "ok": bool(play.get("ok")),
        "action": "add-source-url",
        "notebook_url": notebook_url,
        "source_url": source_url,
        "playwriter": play,
        "timestamp": utc_now(),
    }


def action_profile(args: argparse.Namespace) -> dict[str, Any]:
    reg_path = Path(args.registry_path).expanduser().resolve()
    registry = _load_registry(reg_path)
    return {
        "ok": True,
        "action": "profile",
        "mode": "browser",
        "timestamp": utc_now(),
        "workspace_url": args.workspace_url,
        "playwriter_bin": _resolve_playwriter_bin(),
        "playwriter_resolved": bool(shutil.which("playwriter") or shutil.which("playwriter.cmd")),
        "session_id": str(args.session),
        "registry_path": str(reg_path),
        "registry_notebooks": len(registry.get("notebooks", [])),
    }


def action_resolve_notebook(args: argparse.Namespace) -> dict[str, Any]:
    reg_path = Path(args.registry_path).expanduser().resolve()
    registry = _load_registry(reg_path)
    try:
        notebook_url, notebook_id, title, resolved = _resolve_notebook_target(args, registry)
        record = _find_notebook_record(registry, notebook_url=notebook_url, title=title, notebook_id=notebook_id)
        return {
            "ok": True,
            "action": "resolve-notebook",
            "resolved": resolved,
            "notebook_url": notebook_url,
            "notebook_id": notebook_id,
            "title": title,
            "record": record or {},
            "registry_path": str(reg_path),
            "timestamp": utc_now(),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "action": "resolve-notebook",
            "error": str(exc),
            "registry_path": str(reg_path),
            "timestamp": utc_now(),
        }


def action_create_notebook(args: argparse.Namespace) -> dict[str, Any]:
    reg_path = Path(args.registry_path).expanduser().resolve()
    registry = _load_registry(reg_path)
    title = (args.title or "").strip()

    if args.reuse_existing and title:
        existing = _find_notebook_record(registry, title=title)
        if existing is not None:
            return {
                "ok": True,
                "action": "create-notebook",
                "reused": True,
                "title": str(existing.get("title", title)),
                "notebook_url": str(existing.get("notebook_url", "")),
                "notebook_id": str(existing.get("notebook_id", "")),
                "registry_path": str(reg_path),
                "timestamp": utc_now(),
            }

    expr = _js_create_notebook(args.workspace_url, title)
    if args.dry_run:
        return {
            "ok": True,
            "action": "create-notebook",
            "dry_run": True,
            "title": title,
            "expr": expr,
            "workspace_url": args.workspace_url,
            "session_id": str(args.session),
            "registry_path": str(reg_path),
            "timestamp": utc_now(),
        }

    play = run_playwriter(args.session, expr, args.timeout_ms)
    parsed = play.get("parsed", {})
    notebook_url = str(parsed.get("notebook_url", "")).strip()
    notebook_id = _extract_notebook_id(notebook_url)

    payload = {
        "ok": bool(play.get("ok")),
        "action": "create-notebook",
        "reused": False,
        "title": title,
        "workspace_url": args.workspace_url,
        "session_id": str(args.session),
        "notebook_url": notebook_url,
        "notebook_id": notebook_id,
        "playwriter": play,
        "registry_path": str(reg_path),
        "timestamp": utc_now(),
    }
    if payload["ok"] and notebook_url:
        _upsert_notebook_record(
            registry,
            title=title or notebook_id,
            notebook_url=notebook_url,
            session_id=str(args.session),
            metadata={"page_title": str(parsed.get("page_title", ""))},
        )
        _save_registry(reg_path, registry)
    return payload


def action_add_source_url(args: argparse.Namespace) -> dict[str, Any]:
    reg_path = Path(args.registry_path).expanduser().resolve()
    registry = _load_registry(reg_path)
    notebook_url, notebook_id, title, resolved = _resolve_notebook_target(args, registry)
    source_url = (args.source_url[0] if args.source_url else "").strip()
    if not source_url:
        raise ValueError("--source-url is required for add-source-url")

    existing = _find_notebook_record(registry, notebook_url=notebook_url, title=title, notebook_id=notebook_id)
    if args.dedupe_sources and existing and source_url in [str(x) for x in existing.get("sources", [])]:
        return {
            "ok": True,
            "action": "add-source-url",
            "skipped_duplicate": True,
            "resolved_from_registry": resolved,
            "notebook_url": notebook_url,
            "notebook_id": notebook_id,
            "title": title,
            "source_url": source_url,
            "registry_path": str(reg_path),
            "timestamp": utc_now(),
        }

    payload = _add_source_once(args, notebook_url, source_url)
    payload.update(
        {
            "resolved_from_registry": resolved,
            "notebook_id": notebook_id,
            "title": title,
            "registry_path": str(reg_path),
        }
    )
    if payload.get("ok"):
        _upsert_notebook_record(
            registry,
            title=title or notebook_id,
            notebook_url=notebook_url,
            session_id=str(args.session),
            source_urls=[source_url],
        )
        _save_registry(reg_path, registry)
    return payload


def action_seed_notebooks(args: argparse.Namespace) -> dict[str, Any]:
    if args.count < 1:
        raise ValueError("--count must be >= 1")

    source_urls = _load_source_urls(args)
    created: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    reused_count = 0

    for idx in range(1, args.count + 1):
        title = f"{args.name_prefix} {idx:02d}"
        create_args = argparse.Namespace(
            session=args.session,
            workspace_url=args.workspace_url,
            title=title,
            timeout_ms=args.timeout_ms,
            dry_run=args.dry_run,
            reuse_existing=args.reuse_existing,
            registry_path=args.registry_path,
        )
        create_result = action_create_notebook(create_args)
        if not create_result.get("ok"):
            failures.append({"step": "create-notebook", "index": idx, "title": title, "result": create_result})
            continue
        if create_result.get("reused"):
            reused_count += 1

        notebook_url = str(create_result.get("notebook_url", "")).strip()
        source_results: list[dict[str, Any]] = []
        for src in source_urls:
            add_args = argparse.Namespace(
                session=args.session,
                notebook_url=notebook_url,
                notebook_id="",
                title=title,
                source_url=[src],
                timeout_ms=args.timeout_ms,
                dry_run=args.dry_run,
                dedupe_sources=args.dedupe_sources,
                registry_path=args.registry_path,
            )
            add_result = action_add_source_url(add_args)
            source_results.append(add_result)
            if not add_result.get("ok"):
                failures.append(
                    {
                        "step": "add-source-url",
                        "index": idx,
                        "title": title,
                        "notebook_url": notebook_url,
                        "source_url": src,
                        "result": add_result,
                    }
                )

        created.append(
            {
                "index": idx,
                "title": title,
                "notebook_url": notebook_url,
                "reused": bool(create_result.get("reused")),
                "sources_attempted": len(source_urls),
                "source_results": source_results,
            }
        )

    return {
        "ok": len(failures) == 0,
        "action": "seed-notebooks",
        "session_id": str(args.session),
        "count": args.count,
        "name_prefix": args.name_prefix,
        "source_urls": source_urls,
        "reused_count": reused_count,
        "created": created,
        "failures": failures,
        "registry_path": str(Path(args.registry_path).expanduser().resolve()),
        "timestamp": utc_now(),
    }


def action_ingest_report(args: argparse.Namespace) -> dict[str, Any]:
    reg_path = Path(args.registry_path).expanduser().resolve()
    registry = _load_registry(reg_path)
    notebook_url, notebook_id, title, resolved = _resolve_notebook_target(args, registry)

    report_urls = _extract_urls_from_report_files(args.report_file or [])
    explicit_urls = _load_source_urls(args)
    urls = []
    seen: set[str] = set()
    for url in report_urls + explicit_urls:
        if url not in seen:
            seen.add(url)
            urls.append(url)

    added: list[dict[str, Any]] = []
    skipped: list[str] = []
    failures: list[dict[str, Any]] = []

    existing = _find_notebook_record(registry, notebook_url=notebook_url, title=title, notebook_id=notebook_id)
    known_sources = [str(x) for x in (existing or {}).get("sources", [])]

    for url in urls:
        if args.dedupe_sources and url in known_sources:
            skipped.append(url)
            continue
        add_result = _add_source_once(args, notebook_url, url)
        if add_result.get("ok"):
            added.append(add_result)
            known_sources.append(url)
        else:
            failures.append({"source_url": url, "result": add_result})

    if added:
        _upsert_notebook_record(
            registry,
            title=title or notebook_id,
            notebook_url=notebook_url,
            session_id=str(args.session),
            source_urls=[a.get("source_url", "") for a in added if a.get("source_url")],
            metadata={"last_ingest_report_at": utc_now()},
        )
        _save_registry(reg_path, registry)

    return {
        "ok": len(failures) == 0,
        "action": "ingest-report",
        "resolved_from_registry": resolved,
        "notebook_url": notebook_url,
        "notebook_id": notebook_id,
        "title": title,
        "report_files": args.report_file or [],
        "report_urls_extracted": len(report_urls),
        "source_urls_total": len(urls),
        "added_count": len(added),
        "skipped_duplicates": skipped,
        "failures": failures,
        "registry_path": str(reg_path),
        "timestamp": utc_now(),
    }


def action_agent_dual(args: argparse.Namespace) -> dict[str, Any]:
    reg_path = Path(args.registry_path).expanduser().resolve()
    registry = _load_registry(reg_path)
    notebook_url, notebook_id, title, resolved = _resolve_notebook_target(args, registry)

    visual_expr = _js_view_notebook(notebook_url, args.visual_preview_chars)
    if args.dry_run:
        visual = {
            "ok": True,
            "dry_run": True,
            "lane": "visual",
            "expr": visual_expr,
        }
    else:
        visual_play = run_playwriter(args.session, visual_expr, args.timeout_ms)
        visual = {
            "ok": bool(visual_play.get("ok")),
            "lane": "visual",
            "playwriter": visual_play,
            "preview": str((visual_play.get("parsed") or {}).get("preview", "")),
        }

    writer_sources = _load_source_urls(args)
    writer_results: list[dict[str, Any]] = []
    for source_url in writer_sources:
        add_result = _add_source_once(args, notebook_url, source_url)
        writer_results.append(add_result)

    prompt_result: dict[str, Any] = {}
    prompt = (args.prompt or "").strip()
    if prompt:
        prompt_expr = _js_submit_prompt(notebook_url, prompt)
        if args.dry_run:
            prompt_result = {"ok": True, "dry_run": True, "lane": "writer_prompt", "expr": prompt_expr}
        else:
            prompt_play = run_playwriter(args.session, prompt_expr, args.timeout_ms)
            prompt_result = {"ok": bool(prompt_play.get("ok")), "lane": "writer_prompt", "playwriter": prompt_play}

    successful_sources = [r.get("source_url", "") for r in writer_results if r.get("ok") and r.get("source_url")]
    if successful_sources:
        _upsert_notebook_record(
            registry,
            title=title or notebook_id,
            notebook_url=notebook_url,
            session_id=str(args.session),
            source_urls=successful_sources,
            metadata={"last_dual_lane_at": utc_now()},
        )
        _save_registry(reg_path, registry)

    ok = (
        bool(visual.get("ok"))
        and all(bool(r.get("ok")) for r in writer_results)
        and (not prompt or bool(prompt_result.get("ok")))
    )
    return {
        "ok": ok,
        "action": "agent-dual",
        "resolved_from_registry": resolved,
        "notebook_url": notebook_url,
        "notebook_id": notebook_id,
        "title": title,
        "visual_lane": visual,
        "writer_lane": {
            "sources_requested": writer_sources,
            "source_results": writer_results,
            "prompt_result": prompt_result,
        },
        "registry_path": str(reg_path),
        "timestamp": utc_now(),
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="NotebookLM connector for terminal orchestration.")
    p.add_argument(
        "--action",
        required=True,
        choices=(
            "profile",
            "resolve-notebook",
            "create-notebook",
            "add-source-url",
            "seed-notebooks",
            "ingest-report",
            "agent-dual",
        ),
    )
    p.add_argument("--session", default="1", help="Playwriter session id")
    p.add_argument("--workspace-url", default=DEFAULT_WORKSPACE_URL)
    p.add_argument("--notebook-url", default="")
    p.add_argument("--notebook-id", default="")
    p.add_argument("--title", default="")
    p.add_argument("--prompt", default="")
    p.add_argument("--source-url", action="append", default=[])
    p.add_argument("--source-url-file", default="")
    p.add_argument("--report-file", action="append", default=[])
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--name-prefix", default="SCBE Research Notebook")
    p.add_argument("--timeout-ms", type=int, default=30000)
    p.add_argument("--visual-preview-chars", type=int, default=1800)
    p.add_argument("--registry-path", default=str(DEFAULT_REGISTRY_PATH))
    p.add_argument("--output", default="", help="Optional JSON output path")
    p.add_argument("--dry-run", action="store_true")

    p.add_argument("--reuse-existing", dest="reuse_existing", action="store_true")
    p.add_argument("--no-reuse-existing", dest="reuse_existing", action="store_false")
    p.set_defaults(reuse_existing=True)

    p.add_argument("--dedupe-sources", dest="dedupe_sources", action="store_true")
    p.add_argument("--no-dedupe-sources", dest="dedupe_sources", action="store_false")
    p.set_defaults(dedupe_sources=True)
    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.action == "profile":
            payload = action_profile(args)
        elif args.action == "resolve-notebook":
            payload = action_resolve_notebook(args)
        elif args.action == "create-notebook":
            payload = action_create_notebook(args)
        elif args.action == "add-source-url":
            payload = action_add_source_url(args)
        elif args.action == "seed-notebooks":
            payload = action_seed_notebooks(args)
        elif args.action == "ingest-report":
            payload = action_ingest_report(args)
        elif args.action == "agent-dual":
            payload = action_agent_dual(args)
        else:
            raise ValueError(f"Unsupported action: {args.action}")
    except Exception as exc:  # noqa: BLE001
        payload = {
            "ok": False,
            "action": args.action,
            "error": str(exc),
            "timestamp": utc_now(),
        }

    payload["output_path"] = _save_output(args.output, payload)
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
