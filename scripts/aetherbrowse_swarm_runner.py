"""Multi-agent AetherBrowse runner with verification + DecisionRecords."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pathlib
import re
import shutil
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

HIGH_RISK = {"click", "type"}
MAX_MISSION_BATCH = 50

try:
    from agents.antivirus_membrane import scan_text_for_threats as _scan_text_for_threats
    from agents.antivirus_membrane import turnstile_action as _turnstile_action
except Exception:  # noqa: BLE001
    class _FallbackScan:
        risk_score = 0.0
        verdict = "CLEAN"

        def to_dict(self) -> Dict[str, Any]:
            return {"risk_score": 0.0, "verdict": "CLEAN", "reasons": ["fallback"]}

    def _scan_text_for_threats(text: str) -> _FallbackScan:  # type: ignore[misc]
        return _FallbackScan()

    def _turnstile_action(domain: str, scan: Any) -> str:  # type: ignore[misc]
        return "ALLOW"


def _sid(v: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", v).strip("-") or "job"


def _j(data: Dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _sha(v: bytes) -> str:
    return hashlib.sha256(v).hexdigest()


def _sha_t(v: str) -> str:
    return _sha(v.encode("utf-8"))


def _api_key(cli: str | None) -> str:
    if cli and cli.strip():
        return cli.strip()
    for k in ("SCBE_API_KEY", "SCBE_BROWSER_API_KEY", "N8N_API_KEY", "BROWSER_AGENT_API_KEY"):
        val = os.getenv(k, "").strip()
        if val:
            return val
    raise RuntimeError("Missing API key (--api-key or SCBE_API_KEY/N8N_API_KEY)")


def _url(cli: str | None) -> str:
    if cli and cli.strip():
        return cli.strip()
    return os.getenv("SCBE_BROWSER_WEBHOOK_URL", "http://127.0.0.1:8001/v1/integrations/n8n/browse").strip()


def _post(url: str, token: str, payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": token},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def _na(a: Dict[str, Any], ji: int, ai: int) -> Dict[str, Any]:
    if "action" not in a and "type" in a:
        a["action"] = a["type"]
    if "target" not in a:
        if "url" in a:
            a["target"] = a["url"]
        elif "selector" in a:
            a["target"] = a["selector"]
        elif str(a.get("action", "")).strip().lower() == "screenshot":
            a["target"] = "full_page"
    if str(a.get("action", "")).strip().lower() == "type" and "value" not in a and "text" in a:
        a["value"] = a["text"]
    out = {"action": str(a.get("action", "")).strip().lower(), "target": str(a.get("target", "")).strip()}
    if "value" in a and a["value"] is not None:
        out["value"] = str(a["value"])
    if "timeout_ms" in a and a["timeout_ms"] is not None:
        out["timeout_ms"] = int(a["timeout_ms"])
    if not out["action"] or not out["target"]:
        raise ValueError(f"Job {ji} action {ai} missing action/target")
    return out


def _jobs(obj: Dict[str, Any]) -> List[Dict[str, Any]]:
    jobs = obj.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("jobs-file must have non-empty jobs[]")
    out: List[Dict[str, Any]] = []
    for ji, j in enumerate(jobs, start=1):
        if not isinstance(j, dict):
            raise ValueError(f"Job {ji} must be object")
        acts = j.get("actions")
        if not isinstance(acts, list) or not acts:
            raise ValueError(f"Job {ji} requires actions[]")
        jj = dict(j)
        jj["actions"] = [_na(dict(a), ji, ai) for ai, a in enumerate(acts, start=1)]
        out.append(jj)
    return out


def _tier(job: Dict[str, Any]) -> str:
    explicit = str(job.get("risk_tier", "")).strip().upper()
    if explicit in {"REFLEX", "DELIBERATION"}:
        return explicit
    return "DELIBERATION" if any(a["action"] in HIGH_RISK for a in job["actions"]) else "REFLEX"


def _cap(job: Dict[str, Any], tier: str) -> Dict[str, Any]:
    token = str(job.get("capability_token", "")).strip()
    required = tier == "DELIBERATION"
    ok = (not required) or bool(token)
    return {
        "required": required,
        "present": bool(token),
        "valid": ok,
        "token_id": _sha_t(token)[:16] if token else None,
        "reason": "ok" if ok else "missing capability token for DELIBERATION",
    }


def _pqc_audit(job: Dict[str, Any], payload: Dict[str, Any], tier: str) -> Dict[str, Any]:
    """Run optional PQC drift/rotation audit for DELIBERATION jobs.

    Triggered only if job contains a `pqc` metadata object.
    """
    """Optional PQC metadata gate used for long-horizon mission hygiene."""
    if tier != "DELIBERATION":
        return {"status": "SKIP", "reason": "tier is REFLEX"}
    pqc_meta = job.get("pqc")
    if not isinstance(pqc_meta, dict):
        return {"status": "SKIP", "reason": "missing job.pqc metadata"}

    try:
        from agents.pqc_key_auditor import audit_pqc_keyset
    except Exception as exc:  # noqa: BLE001
        return {"status": "ERROR", "reason": f"pqc auditor unavailable: {exc}"}

    threshold = float(pqc_meta.get("drift_threshold", 0.82))
    rotation_hours = int(pqc_meta.get("rotation_hours", 720))
    return audit_pqc_keyset(
        pqc_meta,
        context_payload=payload,
        drift_threshold=threshold,
        rotation_hours=rotation_hours,
    )
    kyber_id = str(pqc_meta.get("kyber_id", "")).strip()
    dilithium_id = str(pqc_meta.get("dilithium_id", "")).strip()
    if not kyber_id or not dilithium_id:
        return {"status": "QUARANTINE", "reason": "missing kyber_id or dilithium_id"}

    age_hours = float(pqc_meta.get("last_rotated_hours", 0) or 0)
    rotation_hours = int(pqc_meta.get("rotation_hours", 720) or 720)
    if age_hours >= rotation_hours:
        return {
            "status": "QUARANTINE",
            "reason": f"key age {age_hours:.1f}h exceeds rotation policy {rotation_hours}h",
        }

    fp = _sha_t(_j({"kyber_id": kyber_id, "dilithium_id": dilithium_id, "workflow_id": payload.get("workflow_id")}))[:20]
    return {"status": "ALLOW", "reason": "pqc metadata within policy", "key_fingerprint": fp}


def _chunk_actions(actions: List[Dict[str, Any]], batch_size: int) -> List[List[Dict[str, Any]]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")
    return [actions[i : i + batch_size] for i in range(0, len(actions), batch_size)]


def _page_lock_id(job: Dict[str, Any]) -> str | None:
    val = str(job.get("page_lock", "")).strip()
    return val if val else None


def _verify(job: Dict[str, Any], resp: Dict[str, Any]) -> Dict[str, Any]:
    rules = job.get("verify", {}) if isinstance(job.get("verify"), dict) else {}
    results = resp.get("results", []) if isinstance(resp.get("results", []), list) else []
    checks: List[Dict[str, Any]] = []
    txt: List[str] = []
    sel_ok: set[str] = set()
    risk: List[float] = []
    dstar: List[float] = []
    nav_req = [a["target"] for a in job["actions"] if a["action"] == "navigate"]
    nav_obs: List[str] = []
    for i, r in enumerate(results, start=1):
        ok = bool(r.get("success")) if isinstance(r, dict) else False
        checks.append({"check": f"action_success_{i}", "passed": ok})
        if isinstance(r, dict):
            c = r.get("containment", {})
            if isinstance(c, dict):
                if c.get("risk_score") is not None:
                    risk.append(float(c["risk_score"]))
                if c.get("radius") is not None:
                    dstar.append(float(c["radius"]))
            d = r.get("data", {})
            if isinstance(d, dict):
                if isinstance(d.get("text"), str):
                    txt.append(d["text"])
                if isinstance(d.get("url"), str):
                    nav_obs.append(d["url"])
            if r.get("action") == "extract" and bool(r.get("success")):
                sel_ok.add(str(r.get("target", "")).strip())
    blob = "\n".join(txt).casefold()
    for t in rules.get("must_contain", []):
        s = str(t).strip()
        if s:
            checks.append({"check": f"must_contain::{s}", "passed": s.casefold() in blob})
    for s in rules.get("selectors_present", []):
        x = str(s).strip()
        if x:
            checks.append({"check": f"selector::{x}", "passed": x in sel_ok})
    if rules.get("max_redirects") is not None:
        m = int(rules["max_redirects"])
        rd = sum(1 for a, b in zip(nav_req, nav_obs) if a.strip().rstrip("/").lower() != b.strip().rstrip("/").lower())
        checks.append({"check": "max_redirects", "passed": rd <= m, "observed": rd, "expected_max": m})
    if not checks:
        checks.append({"check": "response_status", "passed": resp.get("status") == "success"})
    passed = len([c for c in checks if c.get("passed")])
    total = len(checks)
    score = round((passed / total) if total else 0.0, 4)
    rmax = max(risk) if risk else 1.0
    dmax = max(dstar) if dstar else 1.0
    coh = max(0.0, min(1.0, round(1.0 - rmax, 4)))
    return {
        "verification_score": score,
        "checks": checks,
        "passed_checks": passed,
        "total_checks": total,
        "metrics": {"risk": round(rmax, 6), "d_star": round(dmax, 6), "coherence": coh},
        "text_blob": blob[:20000],
    }


def _chunks(actions: List[Dict[str, Any]], max_actions: int) -> List[List[Dict[str, Any]]]:
    if max_actions <= 0 or len(actions) <= max_actions:
        return [actions]
    return [actions[i : i + max_actions] for i in range(0, len(actions), max_actions)]


def _decide(score: float, cap: Dict[str, Any], noise_on_deny: bool) -> Tuple[str, str]:
    if not cap.get("valid", False):
        return ("NOISE" if noise_on_deny else "DENY", f"capability gate failed: {cap.get('reason')}")
    if score >= 0.90:
        return "ALLOW", "verification score >= 0.90"
    if score >= 0.60:
        return "QUARANTINE", "verification score in [0.60,0.90)"
    return ("NOISE" if noise_on_deny else "DENY", "verification score < 0.60")


def _scr_hashes(resp: Dict[str, Any], outdir: pathlib.Path | None, job_id: str, session_id: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    rr = resp.get("results", []) if isinstance(resp.get("results", []), list) else []
    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(rr, start=1):
        if not isinstance(r, dict):
            continue
        d = r.get("data", {})
        if not isinstance(d, dict) or not isinstance(d.get("screenshot"), str):
            continue
        s = d["screenshot"].strip()
        mode, path = "truncated-base64", None
        digest = _sha_t(s)
        if not s.endswith("..."):
            try:
                raw = base64.b64decode(s, validate=True)
                digest = _sha(raw)
                mode = "image-bytes"
                if outdir:
                    p = outdir / f"{_sid(job_id)}_{_sid(session_id)}_step{i}.png"
                    p.write_bytes(raw)
                    path = str(p)
            except Exception:  # noqa: BLE001
                pass
        rows.append({"step": i, "sha256": digest, "mode": mode, "path": path})
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description="Submit multiple browser jobs to AetherBrowse in parallel.")
    p.add_argument("--jobs-file", required=True)
    p.add_argument("--url", default=None)
    p.add_argument("--api-key", default=None)
    p.add_argument("--concurrency", type=int, default=3)
    p.add_argument("--timeout-sec", type=int, default=180)
    p.add_argument("--output-json", default=None)
    p.add_argument("--save-screenshots-dir", default=None)
    p.add_argument("--artifact-root", default="artifacts/aetherbrowse_runs")
    p.add_argument("--replica-roots", nargs="*", default=[])
    p.add_argument("--kernel-version", default=os.getenv("SCBE_KERNEL_VERSION", "scbe-kernel-v1"))
    p.add_argument("--profile-id", default=os.getenv("SCBE_PROFILE_ID", "default-safe"))
    p.add_argument("--noise-on-deny", dest="noise_on_deny", action="store_true")
    p.add_argument("--no-noise-on-deny", dest="noise_on_deny", action="store_false")
    p.add_argument("--max-actions-per-request", type=int, default=MAX_MISSION_BATCH)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--run-id", default=None)
    p.set_defaults(noise_on_deny=True)
    a = p.parse_args()

    token, url = _api_key(a.api_key), _url(a.url)
    jobs = _jobs(json.loads(pathlib.Path(a.jobs_file).read_text(encoding="utf-8")))
    if a.run_id:
        run_id = str(a.run_id)
    elif a.seed is not None:
        seed_material = f"seed:{a.seed}|jobs:{_sha_t(_j({'jobs': jobs}))[:16]}"
        run_id = f"swarm-seeded-{_sha_t(seed_material)[:12]}"
    else:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = pathlib.Path(a.artifact_root) / run_id
    ddir, tdir = root / "decision_records", root / "traces"
    ddir.mkdir(parents=True, exist_ok=True)
    tdir.mkdir(parents=True, exist_ok=True)
    shot_dir = pathlib.Path(a.save_screenshots_dir) if a.save_screenshots_dir else None

    req = ["schema_version", "decision_id", "timestamp_utc", "kernel_version", "profile_id", "job_id", "agent_id", "session_id", "decision", "metrics", "capability", "trace_hash", "verification"]
    schema_path = pathlib.Path("schemas/decision_record.schema.json")
    if schema_path.exists():
        try:
            schema_obj = json.loads(schema_path.read_text(encoding="utf-8"))
            req_from_schema = schema_obj.get("required")
            if isinstance(req_from_schema, list) and req_from_schema:
                req = [str(x) for x in req_from_schema]
        except Exception:  # noqa: BLE001
            pass
    results: List[Dict[str, Any]] = [None] * len(jobs)  # type: ignore[list-item]
    fails: List[Dict[str, Any]] = []
    active_page_locks: set[str] = set()

    for idx, job in enumerate(jobs):
        lock_id = _page_lock_id(job)
        if lock_id is None:
            continue
        if lock_id in active_page_locks:
            raise ValueError(f"Duplicate page_lock detected for jobs-file entry {idx + 1}: {lock_id}")
        active_page_locks.add(lock_id)

    def run_one(i: int, job: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        job_id = _sid(str(job.get("job_id", f"job-{i+1:03d}")))
        aid = str(job.get("agent_id", f"agent-{i+1}"))
        sid = str(job.get("session_id", f"{aid}-session"))
        tier = _tier(job)
        cap = _cap(job, tier)
        payload = {"actions": job["actions"], "session_id": sid, "source": job.get("source", "swarm"), "workflow_id": job.get("workflow_id", "swarm-run"), "run_id": job.get("run_id", f"run-{int(time.time())}-{i+1}"), "dry_run": bool(job.get("dry_run", False))}
        pqc_result = _pqc_audit(job, payload, tier)
        if pqc_result.get("status") in {"QUARANTINE", "DENY"}:
            cap = {**cap, "valid": False, "reason": f"pqc audit failed: {pqc_result.get('reason', 'quarantine')}"}
        payload_base = {
            "session_id": sid,
            "source": job.get("source", "swarm"),
            "workflow_id": job.get("workflow_id", "swarm-run"),
            "run_id": job.get("run_id", f"run-{run_id}-{i+1}"),
            "dry_run": bool(job.get("dry_run", False)),
        }
        pqc_result = _pqc_audit(job, payload_base, tier)
        if pqc_result.get("status") in {"QUARANTINE", "DENY"}:
            cap = {**cap, "valid": False, "reason": f"pqc audit failed: {pqc_result.get('reason', 'quarantine')}"}

        chunks = _chunk_actions(job["actions"], max(1, a.max_actions_per_request))
        payload = {**payload_base, "actions": job["actions"], "chunk_count": len(chunks)}
        t0 = time.time()
        err = None
        if cap["valid"]:
            try:
                all_results: List[Dict[str, Any]] = []
                blocked_actions = 0
                traces: List[str] = []
                for chunk_idx, chunk in enumerate(chunks, start=1):
                    chunk_payload = {
                        **payload_base,
                        "actions": chunk,
                        "chunk_index": chunk_idx,
                        "chunk_count": len(chunks),
                        "page_lock": job.get("page_lock"),
                    }
                    chunk_resp = _post(url, token, chunk_payload, a.timeout_sec)
                    if isinstance(chunk_resp.get("results"), list):
                        all_results.extend(chunk_resp["results"])
                    blocked_actions += int(chunk_resp.get("blocked_actions", 0) or 0)
                    if isinstance(chunk_resp.get("trace"), str):
                        traces.append(chunk_resp["trace"])
                    if str(chunk_resp.get("status", "")).strip().lower() not in {"success", "ok"}:
                        err = f"chunk {chunk_idx} status={chunk_resp.get('status')}"
                        break
                resp = {
                    "status": "request_error" if err else "success",
                    "session_id": sid,
                    "results": all_results,
                    "total_actions": len(job["actions"]),
                    "executed_actions": len(all_results),
                    "blocked_actions": blocked_actions,
                    "trace": "|".join(traces) if traces else ("request_error" if err else "chunked_success"),
                    "chunk_count": len(chunks),
                }
            except Exception as exc:  # noqa: BLE001
                err = str(exc)
                resp = {"status": "request_error", "session_id": sid, "results": [], "total_actions": len(job["actions"]), "executed_actions": 0, "blocked_actions": len(job["actions"]), "trace": "request_error"}
        else:
            err = cap["reason"]
            resp = {"status": "blocked_by_policy", "session_id": sid, "results": [], "total_actions": len(job["actions"]), "executed_actions": 0, "blocked_actions": len(job["actions"]), "trace": "policy_gate_blocked"}
        return i, {"job_id": job_id, "agent_id": aid, "session_id": sid, "risk_tier": tier, "payload": payload, "response": resp, "capability": cap, "verify": job.get("verify", {}), "elapsed_ms": round((time.time() - t0) * 1000.0, 2), "request_error": err, "pqc_audit": pqc_result}

    with ThreadPoolExecutor(max_workers=max(1, a.concurrency)) as pool:
        futs = {pool.submit(run_one, i, j): i for i, j in enumerate(jobs)}
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                idx, out = fut.result()
            except Exception as exc:  # noqa: BLE001
                fails.append({"job_index": i, "error": str(exc)})
                continue
            v = _verify(jobs[idx], out["response"])
            decision, why = _decide(v["verification_score"], out["capability"], a.noise_on_deny)
            antivirus_scan = _scan_text_for_threats(v.get("text_blob", ""))
            antivirus_action = _turnstile_action("browser", antivirus_scan)
            antivirus_report = antivirus_scan.to_dict()
            antivirus_report["turnstile_action"] = antivirus_action
            if antivirus_action == "HONEYPOT":
                decision = "NOISE" if a.noise_on_deny else "DENY"
                why = "antivirus membrane action=HONEYPOT"
            elif antivirus_action in {"HOLD", "ISOLATE"} and decision == "ALLOW":
                decision = "QUARANTINE"
                why = f"antivirus membrane action={antivirus_action}"
            trace = {"request": {"payload": out["payload"], "risk_tier": out["risk_tier"], "verify": out["verify"]}, "response": out["response"]}
            trace = {
                "request": {"payload": out["payload"], "risk_tier": out["risk_tier"], "verify": out["verify"]},
                "response": out["response"],
                "pqc_audit": out.get("pqc_audit", {}),
            }
            trace_hash = _sha_t(_j(trace))
            rec = {
                "schema_version": "1.0.0",
                "decision_id": f"{run_id}:{out['job_id']}",
                "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "kernel_version": a.kernel_version,
                "profile_id": a.profile_id,
                "job_id": out["job_id"],
                "agent_id": out["agent_id"],
                "session_id": out["session_id"],
                "workflow_id": str(out["payload"].get("workflow_id", "swarm-run")),
                "runner_run_id": run_id,
                "request_run_id": str(out["payload"].get("run_id", "")),
                "decision": decision,
                "decision_reason": why,
                "risk_tier": out["risk_tier"],
                "metrics": {"risk": v["metrics"]["risk"], "d_star": v["metrics"]["d_star"], "coherence": v["metrics"]["coherence"], "verification_score": v["verification_score"]},
                "capability": out["capability"],
                "pqc_audit": out.get("pqc_audit", {}),
                "antivirus": antivirus_report,
                "trace_hash": trace_hash,
                "verification": {"score": v["verification_score"], "passed_checks": v["passed_checks"], "total_checks": v["total_checks"], "checks": v["checks"]},
            }
            miss = [k for k in req if k not in rec]
            if miss:
                raise RuntimeError(f"DecisionRecord missing fields: {', '.join(miss)}")
            rp = ddir / f"{out['job_id']}.json"
            tp = tdir / f"{out['job_id']}.json"
            rp.write_text(json.dumps(rec, indent=2), encoding="utf-8")
            tp.write_text(json.dumps(trace, indent=2), encoding="utf-8")
            for replica_root in a.replica_roots:
                try:
                    replica_base = pathlib.Path(replica_root) / run_id
                    dr = replica_base / "decision_records" / rp.name
                    tr = replica_base / "traces" / tp.name
                    dr.parent.mkdir(parents=True, exist_ok=True)
                    tr.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(rp, dr)
                    shutil.copyfile(tp, tr)
                except Exception as exc:  # noqa: BLE001
                    fails.append({"job_id": out["job_id"], "replica_root": replica_root, "error": str(exc)})
            sh = _scr_hashes(out["response"], shot_dir, out["job_id"], out["session_id"])
            pub = {"status": "noise", "detail": "suppressed by governance policy"} if decision == "NOISE" else out["response"]
            results[idx] = {
                "job_id": out["job_id"], "agent_id": out["agent_id"], "session_id": out["session_id"], "risk_tier": out["risk_tier"],
                "decision": decision, "decision_reason": why, "verification_score": v["verification_score"], "decision_record_path": str(rp),
                "trace_path": str(tp), "trace_hash": trace_hash, "screenshot_hashes": sh, "elapsed_ms": out["elapsed_ms"],
                "request_error": out["request_error"], "response_status": out["response"].get("status"), "response": pub, "pqc_audit": out.get("pqc_audit", {}),
                "antivirus": antivirus_report,
            }
            print(f"[job {idx+1}] job_id={out['job_id']} decision={decision} score={v['verification_score']} elapsed_ms={out['elapsed_ms']}")

    summary = {"run_id": run_id, "kernel_version": a.kernel_version, "profile_id": a.profile_id, "total_jobs": len(jobs), "success_jobs": len([r for r in results if r is not None]), "failed_jobs": len(fails), "failures": fails, "results": results}
    op = pathlib.Path(a.output_json) if a.output_json else (root / "summary.json")
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[output] wrote {op}")
    print(json.dumps({k: summary[k] for k in ("run_id", "total_jobs", "success_jobs", "failed_jobs")}, indent=2))
    if fails:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
