#!/usr/bin/env python3
"""Smoke-test a Colab notebook through Playwright with a safe scratch cell."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.system import colab_workflow_catalog as catalog
from scripts.system import colab_worker_lease as worker


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "colab_smoke"
DEFAULT_PROFILE_DIR = Path.home() / ".scbe-playwright-colab"
DEFAULT_SMOKE_CODE = "print('SCBE_COLAB_SMOKE_OK')"
DEFAULT_CONNECT_ATTEMPTS = 3
DEFAULT_CONNECT_WAIT_MS = 6000


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


COLLECT_CELLS_JS = """
() => {
  const notebook = window.colab?.global?.notebook;
  const cells = Array.from(notebook?.cells || []);
  const sample = cells.slice(0, 8).map((cell, index) => {
    let text = '';
    try {
      if (typeof cell.getText === 'function') {
        text = cell.getText() || '';
      }
    } catch (error) {
      text = '';
    }
    const output = (Array.isArray(cell?.model?.outputs) ? cell.model.outputs : [])
      .map((entry) => {
        if (typeof entry?.text === 'string') return entry.text;
        if (Array.isArray(entry?.text)) return entry.text.join('');
        return '';
      })
      .filter(Boolean)
      .join('\\n')
      .slice(0, 400);
    return {
      index,
      type: cell?.model?.type || 'unknown',
      first_line: text.trim().split('\\n')[0].slice(0, 140),
      output_preview: output,
    };
  });
  const firstCodeIndex = cells.findIndex((cell) => cell?.model?.type === 'code');
  return {
    cell_count: cells.length,
    first_code_index: firstCodeIndex,
    code_cell_count: cells.filter((cell) => cell?.model?.type === 'code').length,
    markdown_cell_count: cells.filter((cell) => cell?.model?.type === 'text').length,
    sample,
  };
}
"""


RUNTIME_PROBE_JS = """
() => {
  const notebook = window.colab?.global?.notebook;
  const kernel = notebook?.kernel;
  const usage = document.querySelector('colab-usage-display');
  const machine = document.querySelector('colab-machine-type');
  const buttons = Array.from(document.querySelectorAll('button'))
    .map((btn) => (btn.innerText || btn.textContent || '').trim())
    .filter(Boolean);
  let runtimeMonitorRunning = false;
  let cachedUsagePreview = '';
  try {
    runtimeMonitorRunning = !!notebook?.runtimeResourceMonitor?.isRunning?.();
  } catch (error) {}
  try {
    const cachedUsage = notebook?.runtimeResourceMonitor?.getCachedUsage?.();
    if (cachedUsage && typeof cachedUsage === 'object') {
      cachedUsagePreview = JSON.stringify(cachedUsage).slice(0, 240);
    } else if (cachedUsage != null) {
      cachedUsagePreview = String(cachedUsage).slice(0, 240);
    }
  } catch (error) {}
  const connectVisible = buttons.some((text) => {
    const lowered = text.toLowerCase();
    return lowered === 'connect' || lowered === 'reconnect' || lowered.includes('connect');
  });
  return {
    notebook_loaded: Array.from(notebook?.cells || []).length > 0,
    usage_visible: !!usage,
    usage_text: usage ? (usage.innerText || usage.textContent || '').trim().slice(0, 240) : '',
    machine_type: machine ? (machine.innerText || machine.textContent || '').trim().slice(0, 120) : '',
    connect_button_visible: connectVisible,
    button_samples: buttons.slice(0, 20),
    kernel_state: typeof kernel?.state === 'string' ? kernel.state : '',
    kernel_last_connected_time_ms: typeof notebook?.kernelLastConnectedTimeMs === 'number' ? notebook.kernelLastConnectedTimeMs : null,
    runtime_monitor_running: runtimeMonitorRunning,
    cached_usage_preview: cachedUsagePreview,
  };
}
"""


AUTO_CONNECT_JS = """
() => {
  const notebook = window.colab?.global?.notebook;
  const kernel = notebook?.kernel;
  const attempts = [];
  const tryCall = (label, fn) => {
    try {
      const value = fn();
      attempts.push({
        label,
        ok: true,
        returned: value && typeof value.then === 'function' ? 'promise' : typeof value,
      });
    } catch (error) {
      attempts.push({ label, ok: false, error: String(error) });
    }
  };
  if (typeof kernel?.attemptAutoconnect === 'function') {
    tryCall('kernel.attemptAutoconnect', () => kernel.attemptAutoconnect());
  }
  if (typeof notebook?.attemptAutoconnect === 'function') {
    tryCall('notebook.attemptAutoconnect', () => notebook.attemptAutoconnect());
  }
  if (typeof kernel?.refreshConnectionDetails === 'function') {
    tryCall('kernel.refreshConnectionDetails', () => kernel.refreshConnectionDetails());
  }
  return {
    attempts,
    kernel_state: typeof kernel?.state === 'string' ? kernel.state : '',
  };
}
"""


ADD_CODE_CELL_JS = """
() => {
  const button = document.querySelector('#toolbar-add-code');
  if (!button) {
    return { ok: false, error: 'add_code_button_missing' };
  }
  button.click();
  return { ok: true };
}
"""


SET_LAST_CELL_CODE_JS = """
(code) => {
  try {
    const nb = window.colab?.global?.notebook;
    if (nb && nb.cells && nb.cells.length) {
      const idx = nb.cells.length - 1;
      const cell = nb.cells[idx];
      if (cell && typeof cell.setText === 'function') {
        cell.setText(code);
        return { ok: true, method: 'colab_api', index: idx };
      }
    }
  } catch (error) {
    // fall through to textarea path
  }
  const cells = document.querySelectorAll('.cell');
  const cell = cells[cells.length - 1];
  if (!cell) {
    return { ok: false, error: 'last_cell_missing' };
  }
  const textarea = cell.querySelector('textarea.inputarea, textarea');
  if (!textarea) {
    return { ok: false, error: 'textarea_missing' };
  }
  textarea.focus();
  textarea.value = code;
  textarea.dispatchEvent(new Event('input', { bubbles: true }));
  return { ok: true, method: 'textarea' };
}
"""


RUN_LAST_CELL_JS = """
() => {
  const notebook = window.colab?.global?.notebook;
  const cells = Array.from(notebook?.cells || []);
  const cell = cells[cells.length - 1];
  if (!cell) {
    return { ok: false, error: 'last_cell_missing' };
  }
  if (cell.runButton && typeof cell.runButton.click === 'function') {
    cell.runButton.click();
    return { ok: true, method: 'runButton.click' };
  }
  const renderedButton = cell.runButton?.renderRoot?.querySelector('button');
  if (renderedButton) {
    renderedButton.click();
    return { ok: true, method: 'runButton.renderRoot.button' };
  }
  const executeHandler = typeof cell.getExecuteHandler === 'function' ? cell.getExecuteHandler() : null;
  if (typeof executeHandler === 'function') {
    executeHandler();
    return { ok: true, method: 'getExecuteHandler' };
  }
  try {
    cell.resumeExecution();
    return { ok: true, method: 'resumeExecution' };
  } catch (error) {
    return { ok: false, error: String(error) };
  }
}
"""


READ_LAST_OUTPUT_JS = """
() => {
  const notebook = window.colab?.global?.notebook;
  const cells = Array.from(notebook?.cells || []);
  const cell = cells[cells.length - 1];
  if (!cell) {
    return { ok: false, error: 'last_cell_missing', joined_text: '' };
  }
  const outputs = (Array.isArray(cell?.model?.outputs) ? cell.model.outputs : [])
    .map((entry) => {
      if (typeof entry?.text === 'string') return entry.text;
      if (Array.isArray(entry?.text)) return entry.text.join('');
      return '';
    })
    .filter(Boolean);
  return {
    ok: true,
    output_count: outputs.length,
    joined_text: outputs.join('\\n').slice(0, 2000),
    busy: !!cell.busy,
    execution_count: typeof cell.getExecutionCount === 'function' ? cell.getExecutionCount() : null,
  };
}
"""


def _runtime_probe(page) -> dict[str, Any]:
    return dict(page.evaluate(RUNTIME_PROBE_JS))


def _collect_cells(page) -> dict[str, Any]:
    return dict(page.evaluate(COLLECT_CELLS_JS))


def _runtime_attached(runtime_probe: dict[str, Any]) -> bool:
    if runtime_probe.get("usage_visible"):
        return True
    state = str(runtime_probe.get("kernel_state") or "").strip().lower()
    if state in {"connected", "busy", "running", "idle", "ready"}:
        return True
    last_connected = runtime_probe.get("kernel_last_connected_time_ms")
    if isinstance(last_connected, (int, float)) and last_connected >= 0:
        return True
    return False


def _attempt_autoconnect(page) -> dict[str, Any]:
    return dict(page.evaluate(AUTO_CONNECT_JS))


def _maybe_click_connect(page) -> dict[str, Any]:
    connect_buttons = page.get_by_role("button", name=re.compile(r"connect|reconnect", re.IGNORECASE))
    count = connect_buttons.count()
    for index in range(count):
        try:
            button = connect_buttons.nth(index)
            text = button.inner_text(timeout=500).strip()
            if not text:
                text = (button.get_attribute("aria-label", timeout=500) or "").strip()
        except Exception:
            continue
        try:
            button.click(timeout=3000)
            return {"attempted": True, "clicked": True, "label": text or "connect"}
        except Exception as exc:
            return {"attempted": True, "clicked": False, "label": text or "connect", "error": str(exc)}
    return {"attempted": True, "clicked": False, "label": "", "error": "connect_button_not_found"}


def _connect_runtime_loop(page, *, connect_attempts: int, connect_wait_ms: int) -> dict[str, Any]:
    poll_trace: list[dict[str, Any]] = []
    click_attempts: list[dict[str, Any]] = []
    auto_attempts: list[dict[str, Any]] = []
    current_probe = _runtime_probe(page)
    poll_trace.append(current_probe)
    if _runtime_attached(current_probe):
        return {
            "click_attempts": click_attempts,
            "auto_attempts": auto_attempts,
            "poll_trace": poll_trace,
            "runtime_probe": current_probe,
        }

    for _ in range(max(1, int(connect_attempts))):
        click_result = _maybe_click_connect(page)
        click_attempts.append(click_result)
        auto_result = _attempt_autoconnect(page)
        auto_attempts.append(auto_result)
        page.wait_for_timeout(max(500, int(connect_wait_ms)))
        current_probe = _runtime_probe(page)
        poll_trace.append(current_probe)
        if _runtime_attached(current_probe):
            break

    return {
        "click_attempts": click_attempts,
        "auto_attempts": auto_attempts,
        "poll_trace": poll_trace,
        "runtime_probe": current_probe,
    }


def _run_scratch_cell(page, smoke_code: str, wait_ms: int) -> dict[str, Any]:
    add_result = dict(page.evaluate(ADD_CODE_CELL_JS))
    if not add_result.get("ok"):
        return {
            "attempted": True,
            "success": False,
            "stage": "add_code_cell",
            "details": add_result,
        }

    page.wait_for_timeout(1200)
    set_result = dict(page.evaluate(SET_LAST_CELL_CODE_JS, smoke_code))
    if not set_result.get("ok"):
        return {
            "attempted": True,
            "success": False,
            "stage": "set_cell_content",
            "details": set_result,
        }

    page.wait_for_timeout(400)
    run_result = dict(page.evaluate(RUN_LAST_CELL_JS))
    if not run_result.get("ok"):
        return {
            "attempted": True,
            "success": False,
            "stage": "run_cell",
            "details": run_result,
        }

    poll_count = max(1, wait_ms // 1000)
    output_result: dict[str, Any] = {"ok": False, "output_count": 0, "joined_text": ""}
    marker_found = False
    for _ in range(poll_count):
        page.wait_for_timeout(1000)
        output_result = dict(page.evaluate(READ_LAST_OUTPUT_JS))
        if "SCBE_COLAB_SMOKE_OK" in output_result.get("joined_text", ""):
            marker_found = True
            break

    return {
        "attempted": True,
        "success": marker_found,
        "stage": "output",
        "add_result": add_result,
        "set_result": set_result,
        "run_result": run_result,
        "output_result": output_result,
    }


def run_notebook_smoke(
    *,
    notebook_query: str,
    profile_dir: Path,
    artifact_root: Path,
    headless: bool,
    timeout_ms: int,
    connect_runtime: bool,
    connect_attempts: int,
    connect_wait_ms: int,
    run_smoke_cell: bool,
    smoke_code: str,
) -> dict[str, Any]:
    notebook = catalog.resolve_notebook_payload(notebook_query)
    artifact_dir = artifact_root / f"smoke-{_utc_stamp()}-{notebook['name']}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = artifact_dir / "page.png"
    artifact_path = artifact_dir / "result.json"

    sync_playwright = worker._load_sync_playwright()
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=headless,
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(str(notebook["colab_url"]), wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(5000)

            cells_before = _collect_cells(page)
            runtime_before = _runtime_probe(page)
            connect_result = {"attempted": False, "clicked": False, "label": ""}
            autoconnect_result = {"attempted": False, "attempts": []}
            connect_trace: list[dict[str, Any]] = [runtime_before]
            if connect_runtime:
                connect_details = _connect_runtime_loop(
                    page,
                    connect_attempts=connect_attempts,
                    connect_wait_ms=connect_wait_ms,
                )
                click_attempts = connect_details["click_attempts"]
                auto_attempts = connect_details["auto_attempts"]
                connect_trace = connect_details["poll_trace"]
                runtime_after_connect = connect_details["runtime_probe"]
                if click_attempts:
                    connect_result = dict(click_attempts[-1])
                autoconnect_result = {
                    "attempted": bool(auto_attempts),
                    "attempts": auto_attempts,
                }
            else:
                runtime_after_connect = runtime_before

            smoke_result = {"attempted": False, "success": False, "stage": "skipped"}
            if run_smoke_cell:
                smoke_result = _run_scratch_cell(page, smoke_code, wait_ms=max(5000, timeout_ms // 6))

            runtime_after_smoke = _runtime_probe(page)
            page.screenshot(path=str(screenshot_path), full_page=True)
            result = {
                "schema_version": "scbe_colab_smoke_v1",
                "notebook": notebook,
                "title": page.title(),
                "current_url": page.url,
                "headless": headless,
                "profile_dir": str(profile_dir),
                "cells_before": cells_before,
                "runtime_before": runtime_before,
                "connect_result": connect_result,
                "autoconnect_result": autoconnect_result,
                "connect_trace": connect_trace,
                "runtime_after_connect": runtime_after_connect,
                "smoke_result": smoke_result,
                "runtime_after_smoke": runtime_after_smoke,
                "screenshot_path": str(screenshot_path),
                "artifact_path": str(artifact_path),
            }
        finally:
            context.close()

    artifact_path.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke-test a Colab notebook with Playwright.")
    parser.add_argument("--notebook", required=True, help="Notebook name or alias from the Colab catalog.")
    parser.add_argument("--profile-dir", default=str(DEFAULT_PROFILE_DIR))
    parser.add_argument("--artifact-root", default=str(ARTIFACT_ROOT))
    parser.add_argument("--timeout-ms", type=int, default=90000)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    parser.add_argument("--connect-runtime", action="store_true", help="Try clicking Connect/Reconnect if visible.")
    parser.add_argument("--connect-attempts", type=int, default=DEFAULT_CONNECT_ATTEMPTS)
    parser.add_argument("--connect-wait-ms", type=int, default=DEFAULT_CONNECT_WAIT_MS)
    parser.add_argument("--run-smoke-cell", action="store_true", help="Add and run a safe scratch code cell.")
    parser.add_argument("--smoke-code", default=DEFAULT_SMOKE_CODE)
    parser.set_defaults(headless=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = run_notebook_smoke(
        notebook_query=args.notebook,
        profile_dir=Path(args.profile_dir),
        artifact_root=Path(args.artifact_root),
        headless=bool(args.headless),
        timeout_ms=args.timeout_ms,
        connect_runtime=bool(args.connect_runtime),
        connect_attempts=max(1, int(args.connect_attempts)),
        connect_wait_ms=max(500, int(args.connect_wait_ms)),
        run_smoke_cell=bool(args.run_smoke_cell),
        smoke_code=args.smoke_code,
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
