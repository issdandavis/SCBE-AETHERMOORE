"""reference_bank -- the NOTEBOOK of known-good solutions for "verified-solvable, not by the runtime".

The answer to "how do you solve a task you've verified is solvable but the local model can't":
get the solution from a source that CAN (here: authored canonical fixes for the failure CLASS),
VERIFY it against the full test_list, and bank it. At runtime the loop injects the banked
reference and the verifier referees -- the weak model never has to crack its own blind spot.

Discipline: a reference is banked ONLY if it passes the full test_list in a fresh subprocess.
Never inject an unverified reference. This is `inject_or_fallback` with a persisted lookup table.

  build()  -> verify every authored solution against the pool, write reference_bank.jsonl (passers only)
  load()   -> {task_id: code} from the banked jsonl
  get(tid) -> banked code for a task, or None
"""

from __future__ import annotations
import json, os, sys, subprocess
from typing import Any, Dict, List, Optional

try:
    from .abstaining_verifier import differential
except ImportError:  # run as a script
    from abstaining_verifier import differential

HERE = os.path.dirname(os.path.abspath(__file__))
POOL = os.path.join(HERE, "pitfall_headroom_pool.jsonl")
BANK = os.path.join(HERE, "reference_bank.jsonl")

# Authored canonical fixes -- one per failure CLASS the local model systematically misses.
SOLUTIONS = {
    "pf_collect_leaves": '''
def collect_leaves(tree, path=None, out=None):
    if path is None: path = []
    if out is None: out = []
    label, children = tree[0], tree[1]
    newpath = path + [label]
    if not children:
        out.append("/".join(newpath))
    else:
        for ch in children:
            collect_leaves(ch, newpath, out)
    return out
''',
    "pf_binary_search_midpoints": '''
def binary_search_midpoints(n):
    lo, hi, out = 0, n - 1, []
    while lo <= hi:
        mid = (lo + hi) // 2
        out.append(mid)
        hi = mid - 1
    return out
''',
    "pf_change_due": '''
def change_due(paid, price, denominations):
    rem = round((paid - price) * 100)
    out = {}
    for d in denominations:
        dc = round(d * 100)
        cnt = rem // dc
        if cnt > 0:
            out[d] = cnt
            rem -= cnt * dc
        if rem == 0:
            break
    return out
''',
    "pf_frange_count": '''
def frange_count(start, stop, step):
    cnt, i = 0, 0
    while start + i * step <= stop + 1e-9:
        cnt += 1
        i += 1
    return cnt
''',
    "pf_make_multipliers": '''
def make_multipliers(factors):
    return [(lambda f: (lambda x: x * f))(fac) for fac in factors]
''',
    "pf_build_validators": '''
def build_validators(thresholds):
    return {name: (lambda t: (lambda v: v >= t))(thr) for name, thr in thresholds.items()}
''',
    "pf_column_getters": '''
def column_getters(headers):
    return [(lambda idx: (lambda row: row[idx]))(i) for i in range(len(headers))]
''',
    "pf_schedule_steps": '''
def schedule_steps(steps):
    cbs, total = [], 0
    for label, delta in steps:
        total += delta
        cbs.append((lambda l, t: (lambda: "%s:%d" % (l, t)))(label, total))
    return cbs
''',
    "pf_expand_template": '''
def expand_template(template, n):
    grid = [list(template) for _ in range(n)]
    for j in range(len(grid[-1])):
        grid[-1][j] += 1
    return grid
''',
    "pf_duplicate_board": '''
def duplicate_board(board, n):
    return [[list(row) for row in board] for _ in range(n)]
''',
    "pf_apply_defaults": '''
import copy
def apply_defaults(base_config, overrides_list):
    res = []
    for ov in overrides_list:
        d = copy.deepcopy(base_config)
        for k, v in ov.items():
            d[k] = v
        res.append(d)
    return res
''',
    "pf_record_history": '''
import copy
def record_history(state, events):
    history = []
    for item, delta in events:
        inv = state["inventory"]
        inv[item] = inv.get(item, 0) + delta
        history.append(copy.deepcopy(state))
    return history
''',
    "pf_apply_renames": '''
def apply_renames(record, rename_map):
    out = {}
    for k, v in record.items():
        out[rename_map.get(k, k)] = v
    return out
''',
    "pf_merge_sorted_unique": '''
def merge_sorted_unique(a, b):
    return sorted(set(a) | set(b))
''',
    "pf_sort_words_by_length": '''
def sort_words_by_length(words):
    return sorted(words, key=lambda w: (len(w), w))
''',
    "pf_median": '''
def median(nums):
    if not nums:
        raise ValueError("empty")
    s = sorted(nums)
    n = len(s)
    if n % 2:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2
''',
    "pf_remove_expired": '''
def remove_expired(sessions, now):
    return [s for s in sessions if s["expiry"] > now]
''',
    "pf_collapse_runs": '''
def collapse_runs(nums):
    i = 1
    while i < len(nums):
        if nums[i] == nums[i - 1]:
            del nums[i]
        else:
            i += 1
    return nums
''',
    "pf_running_max_resets": '''
def running_max_resets(nums, reset_on_zero=False):
    out, cur = [], None
    for x in nums:
        if reset_on_zero and x == 0:
            out.append(None)
            cur = None
            continue
        cur = x if cur is None else max(cur, x)
        out.append(cur)
    return out
''',
    "pf_chunk_diffs_from_start": '''
def chunk_diffs_from_start(data, chunk_size):
    if chunk_size < 1:
        raise ValueError("chunk_size must be >= 1")
    if not data:
        return []
    first = data[0]
    out = []
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        out.append(chunk[-1] - first)
    return out
''',
    "pf_longest_run_value": '''
def longest_run_value(seq):
    if not seq:
        return None
    best_val, best_len = seq[0], 1
    cur_val, cur_len = seq[0], 1
    for x in seq[1:]:
        if x == cur_val:
            cur_len += 1
        else:
            cur_val, cur_len = x, 1
        if cur_len > best_len:
            best_len, best_val = cur_len, cur_val
    return best_val
''',
    "pf_trim_and_summarize": '''
def trim_and_summarize(lines):
    cleaned = [s.strip() for s in lines if s.strip()]
    if not cleaned:
        return {"first": None, "last": None, "count": 0}
    return {"first": cleaned[0], "last": cleaned[-1], "count": len(cleaned)}
''',
}


def _passes(code, tests):
    try:
        return subprocess.run([sys.executable, "-c", code + "\n" + "\n".join(tests) + "\n"],
                              capture_output=True, text=True, timeout=15).returncode == 0
    except Exception:
        return False


def build():
    pool = {json.loads(l)["task_id"]: json.loads(l)
            for l in open(POOL, encoding="utf-8") if l.strip()}
    banked, rejected = [], []
    for tid, code in SOLUTIONS.items():
        if tid not in pool:
            rejected.append((tid, "not in pool"))
            continue
        if _passes(code, pool[tid]["test_list"]):
            banked.append({"task_id": tid, "code": code.strip(),
                           "category": pool[tid]["category"]})
        else:
            rejected.append((tid, "FAILED full tests -- NOT banked"))
    with open(BANK, "w", encoding="utf-8") as f:
        for row in banked:
            f.write(json.dumps(row) + "\n")
    print("reference_bank: banked %d/%d verified references -> %s"
          % (len(banked), len(SOLUTIONS), os.path.basename(BANK)))
    for tid, why in rejected:
        print("  REJECTED %s: %s" % (tid, why))
    return len(banked), len(rejected)


def load():
    if not os.path.exists(BANK):
        return {}
    return {json.loads(l)["task_id"]: json.loads(l)["code"]
            for l in open(BANK, encoding="utf-8") if l.strip()}


def get(task_id):
    return load().get(task_id)


def load_rows(path: Optional[str] = None) -> List[Dict[str, Any]]:
    target = path or BANK
    if not os.path.exists(target):
        return []
    rows = []
    with open(target, encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows


def put_verified(
    task_id: str,
    code: str,
    tests: List[str],
    *,
    category: str = "auto",
    source: str = "auto",
    reference: Optional[str] = None,
    require_fuzz: bool = True,
    bank_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Append a verified reference to the bank, never from visible-test success alone.

    The admission rule is:
      1. candidate passes the supplied held-out/full tests in a subprocess;
      2. if `require_fuzz` is true, a trusted reference must be supplied and the
         abstaining verifier must return `trust`.

    If fuzz cannot be run, the function returns a refusal receipt instead of
    weakening the bank silently.
    """

    tid = str(task_id or "").strip()
    if not tid:
        return {"banked": False, "reason": "missing task_id", "hidden_passed": False, "fuzz_verdict": "not_run"}
    candidate = str(code or "").strip()
    if not candidate:
        return {"banked": False, "reason": "missing code", "hidden_passed": False, "fuzz_verdict": "not_run"}
    if not _passes(candidate, tests):
        return {"banked": False, "reason": "candidate failed verification tests", "hidden_passed": False, "fuzz_verdict": "not_run"}

    fuzz_report: Dict[str, Any] = {"verdict": "not_required", "reason": "require_fuzz is false"}
    if require_fuzz:
        if not reference:
            return {
                "banked": False,
                "reason": "fuzz required but no trusted reference supplied",
                "hidden_passed": True,
                "fuzz_verdict": "unavailable",
            }
        fuzz_report = differential(candidate, reference, list(tests), n_fuzz=40)
        if fuzz_report.get("verdict") != "trust":
            return {
                "banked": False,
                "reason": "fuzz verifier did not trust candidate",
                "hidden_passed": True,
                "fuzz_verdict": fuzz_report.get("verdict"),
                "fuzz_report": fuzz_report,
            }

    target = bank_path or BANK
    rows = load_rows(target)
    for row in rows:
        if row.get("task_id") == tid and str(row.get("code") or "").strip() == candidate:
            return {
                "banked": True,
                "already_present": True,
                "task_id": tid,
                "path": target,
                "hidden_passed": True,
                "fuzz_verdict": fuzz_report.get("verdict"),
                "fuzz_report": fuzz_report,
            }

    record = {
        "task_id": tid,
        "code": candidate,
        "category": category,
        "source": source,
        "verified_by": "hidden+fuzz" if require_fuzz else "hidden",
        "fuzz_verdict": fuzz_report.get("verdict"),
    }
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    return {
        "banked": True,
        "already_present": False,
        "task_id": tid,
        "path": target,
        "hidden_passed": True,
        "fuzz_verdict": fuzz_report.get("verdict"),
        "fuzz_report": fuzz_report,
    }


if __name__ == "__main__":
    build()
