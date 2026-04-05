#!/usr/bin/env python3
"""
Translateral Code Training Pair Generator — 10K Matched A/B Dataset

This is NOT template slotting. Every record teaches four simultaneous views:

  L0 (Substrate):    Binary/AST structure, memory model, cyclomatic complexity
  L1 (Coordination): Dependency graph, inverse operation, alternative build orders
  L2 (Orientation):  The "sniper" — structural threats invisible at surface level
  L3 (Expression):   The actual human-readable code

The A/B comparison:
  - Baseline: L3 only (surface code — what mainstream LLMs see)
  - Multiview: L0+L1+L2+L3 (full structural vision — seeing the sniper)

Combinatorial expansion:
  25 domains × 4-6 operations each × 5 languages × 4 difficulty tiers
  × threat/build-order cross-products → 10,000 unique matched pairs

Output:
  training-data/sft/round5_code_baseline_l3.jsonl
  training-data/sft/round5_code_multiview_l0l3.jsonl
"""

import json
import random
import hashlib
import itertools
from pathlib import Path
from datetime import datetime, timezone

random.seed(42)  # Reproducible dataset

TIMESTAMP = datetime.now(timezone.utc).isoformat()
OUTPUT_DIR = Path("training-data/sft")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FILE_BASELINE = OUTPUT_DIR / "round5_code_baseline_l3.jsonl"
FILE_MULTIVIEW = OUTPUT_DIR / "round5_code_multiview_l0l3.jsonl"

TARGET_COUNT = 10000

# ═══════════════════════════════════════════════════════════════════
# SECTION 1: CODE ATOMS — real code, real structure, real threats
# ═══════════════════════════════════════════════════════════════════
# Each atom is a minimal but COMPLETE code pattern with all 4 views.
# The L0/L1/L2 views are what the model learns to extract FROM L3.

ATOMS = [
    # ── FUNDAMENTALS (Tier: Basic) ──
    {
        "id": "var_assign_safe", "domain": "fundamentals", "tier": "basic",
        "name": "Safe Variable Assignment with Default",
        "python": "value = data.get('key', default_val)\nif not isinstance(value, expected_type):\n    raise TypeError(f'Expected {expected_type}, got {type(value)}')",
        "typescript": "const value: T = data?.key ?? defaultVal;\nif (typeof value !== expectedType) throw new TypeError(`Expected ${expectedType}`);",
        "rust": "let value = data.get(\"key\").unwrap_or(&default_val);\nassert!(value.type_id() == TypeId::of::<T>());",
        "go": "value, ok := data[\"key\"]\nif !ok {\n    value = defaultVal\n}",
        "sql": "COALESCE(column_name, default_value) AS safe_column",
        "ast": {"depth": 3, "nodes": ["Assignment", "MemberAccess", "Default", "TypeGuard"], "memory": "stack", "complexity": 2},
        "inverse": "del value  # But first verify no downstream references exist\nassert 'value' not in [v for v in gc.get_referrers(value) if v is not locals()]",
        "inverse_desc": "Delete binding after verifying no dangling references remain in scope",
        "build_orders": {
            "sequential": "Assign → validate type → use",
            "defensive": "Pre-validate input dict exists → assign with default → type-check → use in try/except",
            "inverse": "Capture pre-assignment state → assign → on failure, restore previous state",
        },
        "sniper": "type_confusion",
        "sniper_detail": "If `data['key']` returns a dict where a string was expected, downstream string methods (.split, .strip) will silently fail or raise AttributeError far from the source. The sniper is the TYPE, not the VALUE.",
        "absence_risk": "Missing isinstance check means type error surfaces 50 lines later, not at assignment",
    },
    {
        "id": "loop_bounded", "domain": "fundamentals", "tier": "basic",
        "name": "Bounded Loop with Early Exit",
        "python": "MAX_ITER = 10000\nfor i, item in enumerate(iterable):\n    if i >= MAX_ITER:\n        raise RuntimeError(f'Loop exceeded {MAX_ITER} iterations')\n    if predicate(item):\n        break\n    process(item)",
        "typescript": "const MAX_ITER = 10000;\nfor (let i = 0; i < Math.min(iterable.length, MAX_ITER); i++) {\n  if (predicate(iterable[i])) break;\n  process(iterable[i]);\n}",
        "rust": "const MAX_ITER: usize = 10000;\nfor (i, item) in iterable.iter().enumerate().take(MAX_ITER) {\n    if predicate(item) { break; }\n    process(item);\n}",
        "go": "const maxIter = 10000\nfor i, item := range iterable {\n    if i >= maxIter { break }\n    if predicate(item) { break }\n    process(item)\n}",
        "sql": "SELECT * FROM table_name LIMIT 10000 WHERE predicate_column = true",
        "ast": {"depth": 4, "nodes": ["ForLoop", "BoundCheck", "Predicate", "Break", "FunctionCall"], "memory": "stack+heap_ref", "complexity": 3},
        "inverse": "# Reverse: undo all process() calls in reverse order\nfor item in reversed(processed_items):\n    unprocess(item)",
        "inverse_desc": "Undo processing in reverse order; requires process() to be idempotent or logged",
        "build_orders": {
            "sequential": "Init counter → iterate → check bound → check predicate → process",
            "functional": "iterable |> take(MAX_ITER) |> takeWhile(!predicate) |> map(process)",
            "parallel": "chunk(iterable, NUM_WORKERS) |> parallel_map(bounded_process) |> merge",
        },
        "sniper": "unbounded_iteration",
        "sniper_detail": "Without MAX_ITER, a generator that yields forever (network stream, infinite sequence) causes OOM or CPU hang. The sniper isn't the loop body — it's the ITERATOR SOURCE that never signals StopIteration.",
        "absence_risk": "Missing bound means adversarial input controls your CPU time",
    },
    {
        "id": "func_def_pure", "domain": "fundamentals", "tier": "basic",
        "name": "Pure Function with Contract",
        "python": "def transform(x: float, scale: float = 1.0) -> float:\n    \"\"\"Contract: output = x * scale, no side effects.\"\"\"\n    assert isinstance(x, (int, float)), f'x must be numeric, got {type(x)}'\n    assert scale != 0, 'scale must be non-zero'\n    return x * scale",
        "typescript": "function transform(x: number, scale: number = 1.0): number {\n  if (scale === 0) throw new RangeError('scale must be non-zero');\n  return x * scale;\n}",
        "rust": "fn transform(x: f64, scale: f64) -> f64 {\n    assert!(scale != 0.0, \"scale must be non-zero\");\n    x * scale\n}",
        "go": "func transform(x, scale float64) (float64, error) {\n    if scale == 0 {\n        return 0, errors.New(\"scale must be non-zero\")\n    }\n    return x * scale, nil\n}",
        "sql": "CREATE FUNCTION transform(x NUMERIC, scale NUMERIC DEFAULT 1.0) RETURNS NUMERIC AS $$ SELECT x * scale $$ LANGUAGE SQL IMMUTABLE;",
        "ast": {"depth": 3, "nodes": ["FunctionDef", "Parameter", "Assert", "Return", "BinaryOp"], "memory": "stack_only", "complexity": 2},
        "inverse": "def inverse_transform(result: float, scale: float) -> float:\n    assert scale != 0\n    return result / scale  # Exact inverse: inverse_transform(transform(x, s), s) == x",
        "inverse_desc": "Division is exact inverse of multiplication when scale != 0; floating-point precision may introduce ULP drift",
        "build_orders": {
            "sequential": "Validate inputs → compute → return",
            "defensive": "Validate → compute in try/except → log on failure → return or raise",
            "inverse": "Store input → compute → verify inverse(output) ≈ input → return",
        },
        "sniper": "float_precision",
        "sniper_detail": "transform(1e308, 2.0) = Infinity. transform(1e-308, 1e-308) = 0.0 (underflow). The function is 'pure' but IEEE 754 makes multiplication non-invertible at extremes. The sniper is the RANGE, not the logic.",
        "absence_risk": "Missing overflow/underflow guard means correct logic produces wrong results at scale boundaries",
    },
    {
        "id": "error_handle_layered", "domain": "fundamentals", "tier": "basic",
        "name": "Layered Error Handling with Context",
        "python": "try:\n    result = operation(data)\nexcept ValueError as e:\n    logger.warning(f'Validation failed: {e}')\n    result = fallback(data)\nexcept (ConnectionError, TimeoutError) as e:\n    logger.error(f'Network failure: {e}')\n    raise RetryableError(str(e)) from e\nexcept Exception as e:\n    logger.critical(f'Unexpected: {e}', exc_info=True)\n    raise",
        "typescript": "try {\n  result = await operation(data);\n} catch (e) {\n  if (e instanceof ValidationError) {\n    logger.warn(`Validation: ${e.message}`);\n    result = fallback(data);\n  } else if (e instanceof NetworkError) {\n    logger.error(`Network: ${e.message}`);\n    throw new RetryableError(e.message, { cause: e });\n  } else { throw e; }\n}",
        "rust": "match operation(&data) {\n    Ok(val) => val,\n    Err(AppError::Validation(msg)) => {\n        warn!(\"Validation failed: {}\", msg);\n        fallback(&data)\n    },\n    Err(AppError::Network(msg)) => return Err(RetryableError::new(msg)),\n    Err(e) => return Err(e.into()),\n}",
        "go": "result, err := operation(data)\nif err != nil {\n    var valErr *ValidationError\n    var netErr *NetworkError\n    switch {\n    case errors.As(err, &valErr):\n        log.Printf(\"Validation: %v\", err)\n        result = fallback(data)\n    case errors.As(err, &netErr):\n        return fmt.Errorf(\"retryable: %w\", err)\n    default:\n        return err\n    }\n}",
        "sql": "DO $$ BEGIN\n  PERFORM operation(data);\nEXCEPTION\n  WHEN check_violation THEN RAISE NOTICE 'Validation: %', SQLERRM;\n  WHEN connection_exception THEN RAISE;\nEND $$;",
        "ast": {"depth": 5, "nodes": ["Try", "ExceptClause", "ExceptClause", "ExceptClause", "Raise", "FunctionCall", "ChainedExc"], "memory": "stack+exception_table", "complexity": 5},
        "inverse": "# Reverse: if fallback was used, re-attempt original; if retried, mark as resolved\nif used_fallback:\n    retry_original(data)\nif was_retried:\n    mark_resolved(original_error)",
        "inverse_desc": "Error recovery is non-trivially reversible; must track WHICH path was taken to undo correctly",
        "build_orders": {
            "sequential": "Try → catch specific → catch general → log → return/raise",
            "defensive": "Pre-validate → try → catch → fallback → verify fallback succeeded → log",
            "redundant": "Try primary → on fail, try secondary → on fail, try tertiary → on all fail, raise aggregate",
        },
        "sniper": "exception_swallowing",
        "sniper_detail": "The bare `except Exception` at the bottom looks safe but if `operation()` raises SystemExit or KeyboardInterrupt (which DON'T inherit from Exception in Python), they pass through. In TS, `catch(e)` catches EVERYTHING including programmer errors. The sniper is the exception HIERARCHY, not the handler logic.",
        "absence_risk": "Missing `from e` in re-raise destroys the original traceback, making debugging impossible",
    },
    # ── DATA STRUCTURES (Tier: Basic-Intermediate) ──
    {
        "id": "hash_map_safe", "domain": "data_structures", "tier": "basic",
        "name": "Hash Map with Collision-Resistant Access",
        "python": "from collections import defaultdict\n\ncache: dict[str, list[T]] = defaultdict(list)\n\ndef safe_insert(key: str, value: T) -> None:\n    sanitized = key.strip()[:256]  # Bound key length\n    cache[sanitized].append(value)\n\ndef safe_lookup(key: str) -> list[T]:\n    sanitized = key.strip()[:256]\n    return cache.get(sanitized, [])",
        "typescript": "const cache = new Map<string, T[]>();\n\nfunction safeInsert(key: string, value: T): void {\n  const sanitized = key.trim().slice(0, 256);\n  const existing = cache.get(sanitized) ?? [];\n  existing.push(value);\n  cache.set(sanitized, existing);\n}\n\nfunction safeLookup(key: string): T[] {\n  return cache.get(key.trim().slice(0, 256)) ?? [];\n}",
        "rust": "use std::collections::HashMap;\n\nlet mut cache: HashMap<String, Vec<T>> = HashMap::new();\n\nfn safe_insert(cache: &mut HashMap<String, Vec<T>>, key: &str, value: T) {\n    let sanitized: String = key.trim().chars().take(256).collect();\n    cache.entry(sanitized).or_default().push(value);\n}",
        "go": "cache := make(map[string][]T)\n\nfunc safeInsert(key string, value T) {\n    sanitized := strings.TrimSpace(key)\n    if len(sanitized) > 256 { sanitized = sanitized[:256] }\n    cache[sanitized] = append(cache[sanitized], value)\n}",
        "sql": "CREATE TABLE cache_table (\n  key VARCHAR(256) PRIMARY KEY,\n  values JSONB DEFAULT '[]'::jsonb\n);\nINSERT INTO cache_table (key, values) VALUES ($1, jsonb_build_array($2))\nON CONFLICT (key) DO UPDATE SET values = cache_table.values || jsonb_build_array($2);",
        "ast": {"depth": 4, "nodes": ["FunctionDef", "StringOp", "DictAccess", "DefaultFactory", "BoundCheck"], "memory": "heap_allocated", "complexity": 3},
        "inverse": "def safe_remove(key: str, value: T) -> bool:\n    sanitized = key.strip()[:256]\n    if sanitized in cache and value in cache[sanitized]:\n        cache[sanitized].remove(value)\n        if not cache[sanitized]: del cache[sanitized]\n        return True\n    return False",
        "inverse_desc": "Remove specific value from key's list; clean up empty lists; return success/failure",
        "build_orders": {
            "sequential": "Sanitize key → check existence → insert/append → return",
            "defensive": "Sanitize → lock → check capacity → insert → unlock → verify",
            "inverse": "Snapshot state → insert → on failure, restore snapshot",
        },
        "sniper": "hash_dos",
        "sniper_detail": "An attacker who knows the hash function can craft keys that ALL collide into the same bucket, turning O(1) lookup into O(n). Python dicts use randomized SipHash to prevent this, but custom hash maps often don't. The sniper is the HASH FUNCTION, not the data structure.",
        "absence_risk": "Missing key length bound lets attacker allocate arbitrary memory via long keys",
    },
    {
        "id": "queue_bounded", "domain": "data_structures", "tier": "intermediate",
        "name": "Bounded Queue with Backpressure",
        "python": "import asyncio\n\nclass BoundedQueue:\n    def __init__(self, maxsize: int = 1000):\n        self._queue = asyncio.Queue(maxsize=maxsize)\n        self._dropped = 0\n\n    async def put(self, item, timeout: float = 5.0):\n        try:\n            await asyncio.wait_for(self._queue.put(item), timeout=timeout)\n        except asyncio.TimeoutError:\n            self._dropped += 1\n            raise BackpressureError(f'Queue full, dropped={self._dropped}')\n\n    async def get(self, timeout: float = 5.0):\n        return await asyncio.wait_for(self._queue.get(), timeout=timeout)",
        "typescript": "class BoundedQueue<T> {\n  private items: T[] = [];\n  private dropped = 0;\n  constructor(private maxSize = 1000) {}\n\n  push(item: T): boolean {\n    if (this.items.length >= this.maxSize) {\n      this.dropped++;\n      return false; // Backpressure signal\n    }\n    this.items.push(item);\n    return true;\n  }\n\n  pop(): T | undefined { return this.items.shift(); }\n  get dropCount() { return this.dropped; }\n}",
        "rust": "use std::sync::mpsc;\nuse std::time::Duration;\n\nlet (tx, rx) = mpsc::sync_channel::<T>(1000); // Bounded\n\n// Producer with backpressure\nmatch tx.send_timeout(item, Duration::from_secs(5)) {\n    Ok(()) => {},\n    Err(mpsc::SendTimeoutError::Timeout(_)) => {\n        dropped += 1;\n        return Err(BackpressureError);\n    }\n    Err(mpsc::SendTimeoutError::Disconnected(_)) => return Err(ChannelClosed),\n}",
        "go": "ch := make(chan T, 1000) // Bounded channel\n\nselect {\ncase ch <- item:\n    // Sent\ncase <-time.After(5 * time.Second):\n    dropped++\n    return fmt.Errorf(\"backpressure: queue full, dropped=%d\", dropped)\n}",
        "sql": "-- Bounded queue via table with row count trigger\nCREATE OR REPLACE FUNCTION enforce_queue_limit() RETURNS TRIGGER AS $$\nBEGIN\n  IF (SELECT count(*) FROM queue_table) >= 1000 THEN\n    RAISE EXCEPTION 'Queue full: backpressure';\n  END IF;\n  RETURN NEW;\nEND; $$ LANGUAGE plpgsql;",
        "ast": {"depth": 6, "nodes": ["ClassDef", "AsyncMethod", "Try", "WaitFor", "Timeout", "Counter", "Raise"], "memory": "heap+channel_buffer", "complexity": 5},
        "inverse": "async def drain(self) -> list:\n    items = []\n    while not self._queue.empty():\n        items.append(await self._queue.get())\n    return items  # Returns all items, restoring empty state",
        "inverse_desc": "Drain empties queue to list; inverse of all puts. Drop count is non-reversible (information loss).",
        "build_orders": {
            "sequential": "Create queue → producer puts → consumer gets → repeat",
            "parallel": "N producers → bounded queue → M consumers (fan-in/fan-out)",
            "redundant": "Primary queue → on backpressure, overflow to secondary queue → alert → drain secondary when primary has capacity",
        },
        "sniper": "unbounded_memory",
        "sniper_detail": "Without maxsize, a fast producer + slow consumer = OOM kill. The queue grows silently until the process is terminated by the OS. The sniper is the RATE MISMATCH, not the queue itself. Backpressure is the only defense.",
        "absence_risk": "Missing timeout on get() means consumer blocks forever if producer dies",
    },
    {
        "id": "tree_traversal_safe", "domain": "data_structures", "tier": "intermediate",
        "name": "Depth-Limited Tree Traversal",
        "python": "def traverse(node, visitor, depth=0, max_depth=100, visited=None):\n    if visited is None:\n        visited = set()\n    node_id = id(node)\n    if node_id in visited:\n        return  # Cycle detected\n    if depth > max_depth:\n        raise RecursionGuard(f'Max depth {max_depth} exceeded')\n    visited.add(node_id)\n    visitor(node, depth)\n    for child in getattr(node, 'children', []):\n        traverse(child, visitor, depth + 1, max_depth, visited)",
        "typescript": "function traverse<T extends {children?: T[]}>(node: T, visitor: (n: T, d: number) => void, depth = 0, maxDepth = 100, visited = new Set<T>()): void {\n  if (visited.has(node)) return; // Cycle\n  if (depth > maxDepth) throw new Error(`Max depth ${maxDepth}`);\n  visited.add(node);\n  visitor(node, depth);\n  for (const child of node.children ?? []) {\n    traverse(child, visitor, depth + 1, maxDepth, visited);\n  }\n}",
        "rust": "fn traverse<T: TreeNode>(node: &T, visitor: &mut dyn FnMut(&T, usize), depth: usize, max_depth: usize, visited: &mut HashSet<usize>) {\n    let id = node.id();\n    if !visited.insert(id) { return; } // Cycle\n    if depth > max_depth { panic!(\"Max depth exceeded\"); }\n    visitor(node, depth);\n    for child in node.children() {\n        traverse(child, visitor, depth + 1, max_depth, visited);\n    }\n}",
        "go": "func traverse(node *TreeNode, visitor func(*TreeNode, int), depth, maxDepth int, visited map[uintptr]bool) {\n    id := reflect.ValueOf(node).Pointer()\n    if visited[id] { return }\n    if depth > maxDepth { panic(\"max depth exceeded\") }\n    visited[id] = true\n    visitor(node, depth)\n    for _, child := range node.Children {\n        traverse(child, visitor, depth+1, maxDepth, visited)\n    }\n}",
        "sql": "WITH RECURSIVE tree AS (\n  SELECT id, parent_id, name, 0 AS depth FROM nodes WHERE id = $1\n  UNION ALL\n  SELECT n.id, n.parent_id, n.name, t.depth + 1\n  FROM nodes n JOIN tree t ON n.parent_id = t.id\n  WHERE t.depth < 100  -- Depth guard\n) SELECT * FROM tree;",
        "ast": {"depth": 6, "nodes": ["FunctionDef", "RecursiveCall", "SetLookup", "DepthGuard", "ForLoop", "AttributeAccess"], "memory": "stack_frames(O(depth))+heap(visited_set)", "complexity": 4},
        "inverse": "def collect_path(node, target_id, path=None):\n    # Inverse: given a node found during traversal, reconstruct the path FROM root TO it\n    if path is None: path = []\n    path.append(node)\n    if id(node) == target_id: return path\n    for child in getattr(node, 'children', []):\n        result = collect_path(child, target_id, path[:])\n        if result: return result\n    return None",
        "inverse_desc": "Forward traversal visits all nodes; inverse reconstructs the specific path to any discovered node",
        "build_orders": {
            "sequential": "DFS: push root → visit → push children → repeat (stack-based)",
            "parallel": "BFS: level-by-level, process each level's nodes concurrently",
            "defensive": "Check cycle → check depth → check node validity → visit → recurse with timeout",
        },
        "sniper": "stack_overflow_via_depth",
        "sniper_detail": "Python's default recursion limit is 1000. A tree with depth 1001 crashes the interpreter. But the REAL sniper is a CYCLIC graph disguised as a tree — without the visited set, a cycle causes infinite recursion that eats the entire stack before any depth check fires.",
        "absence_risk": "Missing visited set means cycles cause silent infinite recursion; missing depth limit means deep trees crash the runtime",
    },
    # ── I/O AND SERIALIZATION (Tier: Intermediate) ──
    {
        "id": "json_parse_safe", "domain": "io_serialization", "tier": "intermediate",
        "name": "Safe JSON Deserialization with Schema Validation",
        "python": "import json\nfrom typing import Any\n\ndef safe_parse(raw: str | bytes, max_size: int = 10_000_000) -> dict[str, Any]:\n    if len(raw) > max_size:\n        raise ValueError(f'Payload too large: {len(raw)} > {max_size}')\n    try:\n        data = json.loads(raw)\n    except json.JSONDecodeError as e:\n        raise ValueError(f'Invalid JSON at position {e.pos}') from e\n    if not isinstance(data, dict):\n        raise TypeError(f'Expected object, got {type(data).__name__}')\n    return data",
        "typescript": "function safeParse(raw: string, maxSize = 10_000_000): Record<string, unknown> {\n  if (raw.length > maxSize) throw new Error(`Payload too large: ${raw.length}`);\n  const data = JSON.parse(raw); // Throws SyntaxError on invalid\n  if (typeof data !== 'object' || data === null || Array.isArray(data))\n    throw new TypeError(`Expected object, got ${typeof data}`);\n  return data;\n}",
        "rust": "use serde_json::Value;\n\nfn safe_parse(raw: &str, max_size: usize) -> Result<serde_json::Map<String, Value>, String> {\n    if raw.len() > max_size { return Err(format!(\"Too large: {}\", raw.len())); }\n    let data: Value = serde_json::from_str(raw).map_err(|e| format!(\"Invalid JSON: {e}\"))?;\n    match data {\n        Value::Object(map) => Ok(map),\n        _ => Err(\"Expected JSON object\".into()),\n    }\n}",
        "go": "func safeParse(raw []byte, maxSize int) (map[string]interface{}, error) {\n    if len(raw) > maxSize {\n        return nil, fmt.Errorf(\"too large: %d > %d\", len(raw), maxSize)\n    }\n    var data map[string]interface{}\n    if err := json.Unmarshal(raw, &data); err != nil {\n        return nil, fmt.Errorf(\"invalid JSON: %w\", err)\n    }\n    return data, nil\n}",
        "sql": "SELECT jsonb_typeof(payload::jsonb) AS jtype,\n       octet_length(payload) AS size\nFROM incoming\nWHERE octet_length(payload) <= 10000000\n  AND jsonb_typeof(payload::jsonb) = 'object';",
        "ast": {"depth": 4, "nodes": ["FunctionDef", "SizeCheck", "JsonParse", "TypeError", "TypeGuard"], "memory": "heap(parsed_object)+stack", "complexity": 3},
        "inverse": "def safe_serialize(data: dict, max_size: int = 10_000_000) -> str:\n    raw = json.dumps(data, ensure_ascii=False, default=str)\n    if len(raw) > max_size:\n        raise ValueError(f'Serialized too large: {len(raw)}')\n    return raw",
        "inverse_desc": "Serialization is the exact inverse of parsing; safe_serialize(safe_parse(x)) == x for valid JSON objects (key ordering may differ)",
        "build_orders": {
            "sequential": "Check size → parse → validate type → return",
            "defensive": "Check size → parse in sandbox → validate schema → sanitize strings → return",
            "redundant": "Parse with primary lib → on failure, try fallback lib → on failure, reject",
        },
        "sniper": "billion_laughs",
        "sniper_detail": "JSON doesn't have entity expansion like XML, but deeply nested arrays/objects ({{{...}}}) can cause stack overflow in recursive parsers. A 1MB payload with 10,000 nesting levels crashes json.loads(). The sniper is the NESTING DEPTH, not the payload size.",
        "absence_risk": "Missing size check allows memory exhaustion; missing type check allows array-where-object-expected bugs downstream",
    },
    {
        "id": "file_io_atomic", "domain": "io_serialization", "tier": "intermediate",
        "name": "Atomic File Write with Rollback",
        "python": "import os, tempfile\nfrom pathlib import Path\n\ndef atomic_write(path: Path, content: bytes) -> None:\n    path = Path(path).resolve()\n    # Prevent path traversal\n    if '..' in path.parts:\n        raise ValueError('Path traversal detected')\n    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix='.tmp')\n    try:\n        os.write(fd, content)\n        os.fsync(fd)\n        os.close(fd)\n        os.replace(tmp, str(path))  # Atomic on POSIX\n    except:\n        os.close(fd) if not os.get_inheritable(fd) else None\n        os.unlink(tmp)  # Clean up temp file\n        raise",
        "typescript": "import { writeFileSync, renameSync, unlinkSync, mkdtempSync } from 'fs';\nimport { join, resolve, relative } from 'path';\n\nfunction atomicWrite(filePath: string, content: Buffer): void {\n  const resolved = resolve(filePath);\n  if (relative(process.cwd(), resolved).startsWith('..')) throw new Error('Path traversal');\n  const tmp = join(resolve(filePath, '..'), `.tmp-${Date.now()}`);\n  try {\n    writeFileSync(tmp, content, { flag: 'wx' });\n    renameSync(tmp, resolved);\n  } catch (e) {\n    try { unlinkSync(tmp); } catch {}\n    throw e;\n  }\n}",
        "rust": "use std::fs;\nuse std::io::Write;\nuse tempfile::NamedTempFile;\n\nfn atomic_write(path: &Path, content: &[u8]) -> io::Result<()> {\n    let canonical = path.canonicalize().unwrap_or_else(|_| path.to_path_buf());\n    let mut tmp = NamedTempFile::new_in(canonical.parent().unwrap())?;\n    tmp.write_all(content)?;\n    tmp.persist(canonical)?;\n    Ok(())\n}",
        "go": "func atomicWrite(path string, content []byte) error {\n    dir := filepath.Dir(path)\n    tmp, err := os.CreateTemp(dir, \".tmp-*\")\n    if err != nil { return err }\n    defer func() {\n        if err != nil { os.Remove(tmp.Name()) }\n    }()\n    if _, err = tmp.Write(content); err != nil { return err }\n    if err = tmp.Sync(); err != nil { return err }\n    if err = tmp.Close(); err != nil { return err }\n    return os.Rename(tmp.Name(), path)\n}",
        "sql": "BEGIN;\nCOPY target_table FROM '/tmp/staging.csv' WITH (FORMAT csv);\n-- If any error, entire COPY is rolled back\nCOMMIT;",
        "ast": {"depth": 5, "nodes": ["FunctionDef", "PathResolve", "TempFile", "Write", "Fsync", "AtomicReplace", "ExceptCleanup"], "memory": "stack+fd(2)+disk_io", "complexity": 5},
        "inverse": "def atomic_delete(path: Path, backup_dir: Path) -> Path:\n    backup = backup_dir / f'{path.name}.{int(time.time())}.bak'\n    os.replace(str(path), str(backup))  # Atomic move to backup\n    return backup  # Return backup path for undo-undo",
        "inverse_desc": "Inverse of write is delete, but safe delete means atomic MOVE to backup, not unlink. The backup enables undo-of-undo.",
        "build_orders": {
            "sequential": "Resolve path → create temp → write → fsync → atomic replace",
            "defensive": "Check permissions → check disk space → resolve path → create temp → write → fsync → replace → verify",
            "inverse": "Backup existing → write new → on failure, restore backup → on success, delete backup after TTL",
        },
        "sniper": "toctou_race",
        "sniper_detail": "Time-of-check-to-time-of-use: between checking if the path is safe and writing to it, an attacker can replace the directory with a symlink pointing to /etc/passwd. The RESOLVED path at check time may differ from write time. The sniper is the TIME GAP between check and use.",
        "absence_risk": "Missing fsync means data loss on power failure; missing temp file cleanup means disk leak on crash",
    },
    # ── NETWORKING (Tier: Intermediate-Advanced) ──
    {
        "id": "http_request_safe", "domain": "networking", "tier": "intermediate",
        "name": "HTTP Request with Timeout and SSRF Protection",
        "python": "import urllib.parse, ipaddress, socket\nimport httpx\n\nBLOCKED_NETS = [ipaddress.ip_network(n) for n in ['127.0.0.0/8', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '169.254.0.0/16']]\n\ndef safe_fetch(url: str, timeout: float = 10.0) -> bytes:\n    parsed = urllib.parse.urlparse(url)\n    if parsed.scheme not in ('http', 'https'):\n        raise ValueError(f'Blocked scheme: {parsed.scheme}')\n    # Resolve hostname BEFORE connecting to prevent DNS rebinding\n    ip = socket.getaddrinfo(parsed.hostname, None)[0][4][0]\n    addr = ipaddress.ip_address(ip)\n    if any(addr in net for net in BLOCKED_NETS):\n        raise ValueError(f'SSRF blocked: {ip} is internal')\n    resp = httpx.get(url, timeout=timeout, follow_redirects=False)\n    resp.raise_for_status()\n    return resp.content",
        "typescript": "import { URL } from 'url';\nimport dns from 'dns/promises';\nimport { isPrivate } from 'ip';\n\nasync function safeFetch(url: string, timeoutMs = 10000): Promise<Buffer> {\n  const parsed = new URL(url);\n  if (!['http:', 'https:'].includes(parsed.protocol))\n    throw new Error(`Blocked scheme: ${parsed.protocol}`);\n  const { address } = await dns.lookup(parsed.hostname);\n  if (isPrivate(address)) throw new Error(`SSRF blocked: ${address}`);\n  const controller = new AbortController();\n  const timer = setTimeout(() => controller.abort(), timeoutMs);\n  try {\n    const resp = await fetch(url, { signal: controller.signal, redirect: 'error' });\n    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);\n    return Buffer.from(await resp.arrayBuffer());\n  } finally { clearTimeout(timer); }\n}",
        "rust": "// Using reqwest with trust-dns\nasync fn safe_fetch(url: &str, timeout: Duration) -> Result<Vec<u8>, FetchError> {\n    let parsed = Url::parse(url)?;\n    if !matches!(parsed.scheme(), \"http\" | \"https\") {\n        return Err(FetchError::BlockedScheme);\n    }\n    let ip: IpAddr = tokio::net::lookup_host(parsed.host_str().unwrap())\n        .await?.next().unwrap().ip();\n    if ip.is_loopback() || ip.is_private() {\n        return Err(FetchError::Ssrf(ip));\n    }\n    let client = reqwest::Client::builder().timeout(timeout).redirect(Policy::none()).build()?;\n    Ok(client.get(url).send().await?.bytes().await?.to_vec())\n}",
        "go": "func safeFetch(rawURL string, timeout time.Duration) ([]byte, error) {\n    u, err := url.Parse(rawURL)\n    if err != nil { return nil, err }\n    if u.Scheme != \"http\" && u.Scheme != \"https\" {\n        return nil, fmt.Errorf(\"blocked scheme: %s\", u.Scheme)\n    }\n    ips, err := net.LookupIP(u.Hostname())\n    if err != nil { return nil, err }\n    for _, ip := range ips {\n        if ip.IsLoopback() || ip.IsPrivate() {\n            return nil, fmt.Errorf(\"SSRF blocked: %s\", ip)\n        }\n    }\n    client := &http.Client{Timeout: timeout, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}\n    resp, err := client.Get(rawURL)\n    if err != nil { return nil, err }\n    defer resp.Body.Close()\n    return io.ReadAll(io.LimitReader(resp.Body, 10<<20)) // 10MB max\n}",
        "sql": "-- SQL doesn't do HTTP natively; this shows the pg_net extension pattern\nSELECT net.http_get(\n  url := $1,\n  params := '{}'::jsonb,\n  timeout_milliseconds := 10000\n) WHERE $1 ~ '^https?://[^/]*[^0-9.]';  -- Basic scheme + non-IP check",
        "ast": {"depth": 6, "nodes": ["FunctionDef", "URLParse", "DNSResolve", "IPCheck", "NetworkCall", "StatusCheck", "Timeout"], "memory": "stack+heap(response_buffer)+socket_fd", "complexity": 6},
        "inverse": "# There is no true inverse of an HTTP GET — it's a read operation.\n# The closest inverse is cache invalidation:\ndef invalidate(url: str, cache: dict) -> bool:\n    return cache.pop(url, None) is not None",
        "inverse_desc": "HTTP GET is inherently non-invertible (you can't un-read). Inverse is cache eviction or undo of any state change triggered by the response.",
        "build_orders": {
            "sequential": "Parse URL → resolve DNS → check IP → connect → read → return",
            "defensive": "Parse → resolve → check IP → connect with timeout → read with size limit → validate content-type → return",
            "redundant": "Try primary URL → on timeout, try mirror → on failure, return cached version → log staleness",
        },
        "sniper": "dns_rebinding",
        "sniper_detail": "Attacker's DNS returns a safe IP on first lookup (passes SSRF check), then switches to 127.0.0.1 on the actual connection. The time gap between DNS resolution and TCP connect is the attack window. The sniper is the DNS TTL — it can change between your check and your use.",
        "absence_risk": "Missing redirect=False allows attacker to redirect from safe URL to internal IP after SSRF check passes",
    },
    {
        "id": "websocket_managed", "domain": "networking", "tier": "advanced",
        "name": "Managed WebSocket with Heartbeat and Reconnect",
        "python": "import asyncio, json\n\nclass ManagedSocket:\n    def __init__(self, url, heartbeat_s=30, max_reconnect=5):\n        self.url = url\n        self.heartbeat_s = heartbeat_s\n        self.max_reconnect = max_reconnect\n        self._ws = None\n        self._reconnect_count = 0\n\n    async def connect(self):\n        import websockets\n        self._ws = await websockets.connect(self.url)\n        self._reconnect_count = 0\n        asyncio.create_task(self._heartbeat_loop())\n\n    async def _heartbeat_loop(self):\n        while self._ws and self._ws.open:\n            try:\n                await self._ws.ping()\n                await asyncio.sleep(self.heartbeat_s)\n            except Exception:\n                await self._try_reconnect()\n\n    async def _try_reconnect(self):\n        if self._reconnect_count >= self.max_reconnect:\n            raise ConnectionError(f'Max reconnects ({self.max_reconnect}) exhausted')\n        self._reconnect_count += 1\n        await asyncio.sleep(min(2 ** self._reconnect_count, 60))  # Exponential backoff\n        await self.connect()\n\n    async def send(self, data: dict): await self._ws.send(json.dumps(data))\n    async def recv(self) -> dict: return json.loads(await self._ws.recv())\n    async def close(self): await self._ws.close()",
        "typescript": "class ManagedSocket {\n  private ws: WebSocket | null = null;\n  private reconnectCount = 0;\n  constructor(private url: string, private heartbeatMs = 30000, private maxReconnect = 5) {}\n\n  connect(): Promise<void> {\n    return new Promise((resolve, reject) => {\n      this.ws = new WebSocket(this.url);\n      this.ws.onopen = () => { this.reconnectCount = 0; this.startHeartbeat(); resolve(); };\n      this.ws.onerror = (e) => reject(e);\n      this.ws.onclose = () => this.tryReconnect();\n    });\n  }\n  private startHeartbeat() {\n    setInterval(() => { if (this.ws?.readyState === WebSocket.OPEN) this.ws.send('ping'); }, this.heartbeatMs);\n  }\n  private async tryReconnect() {\n    if (this.reconnectCount >= this.maxReconnect) throw new Error('Max reconnects');\n    this.reconnectCount++;\n    await new Promise(r => setTimeout(r, Math.min(2 ** this.reconnectCount * 1000, 60000)));\n    await this.connect();\n  }\n}",
        "rust": "// Using tokio-tungstenite\nasync fn managed_connect(url: &str, heartbeat: Duration, max_reconnect: u32) -> Result<WebSocketStream, Error> {\n    let mut attempts = 0;\n    loop {\n        match connect_async(url).await {\n            Ok((ws, _)) => return Ok(ws),\n            Err(e) if attempts < max_reconnect => {\n                attempts += 1;\n                sleep(Duration::from_secs(2u64.pow(attempts).min(60))).await;\n            }\n            Err(e) => return Err(e),\n        }\n    }\n}",
        "go": "type ManagedConn struct {\n    URL          string\n    HeartbeatSec int\n    MaxReconnect int\n    conn         *websocket.Conn\n    reconnects   int\n}\n\nfunc (m *ManagedConn) Connect() error {\n    var err error\n    m.conn, _, err = websocket.DefaultDialer.Dial(m.URL, nil)\n    if err != nil { return err }\n    m.reconnects = 0\n    go m.heartbeatLoop()\n    return nil\n}\n\nfunc (m *ManagedConn) heartbeatLoop() {\n    ticker := time.NewTicker(time.Duration(m.HeartbeatSec) * time.Second)\n    for range ticker.C {\n        if err := m.conn.WriteMessage(websocket.PingMessage, nil); err != nil {\n            m.tryReconnect()\n            return\n        }\n    }\n}",
        "sql": "-- WebSockets don't exist in SQL; closest pattern is LISTEN/NOTIFY\nLISTEN channel_name;\n-- In application: reconnect on disconnect, re-subscribe on reconnect",
        "ast": {"depth": 7, "nodes": ["ClassDef", "AsyncMethod", "TaskCreate", "While", "Try", "ExponentialBackoff", "PingPong"], "memory": "heap(ws_buffer)+stack(task_frames)+timer", "complexity": 7},
        "inverse": "async def graceful_close(self):\n    # Inverse of connect: drain pending messages, send close frame, await confirmation\n    if self._ws and self._ws.open:\n        pending = []\n        while not self._ws.messages.empty():\n            pending.append(await self._ws.recv())\n        await self._ws.close(code=1000, reason='graceful shutdown')\n    return pending  # Return unprocessed messages for recovery",
        "inverse_desc": "Inverse of connect is graceful close: drain pending, send close frame, return unprocessed messages for potential replay",
        "build_orders": {
            "sequential": "Connect → start heartbeat → send/recv loop → close",
            "defensive": "Connect with timeout → verify TLS → start heartbeat → send/recv with per-message timeout → reconnect on failure",
            "redundant": "Primary connection → shadow secondary connection → if primary drops, promote secondary → reconnect primary in background",
        },
        "sniper": "slowloris",
        "sniper_detail": "Attacker opens a WebSocket, sends one byte every 29 seconds (just under heartbeat timeout). Connection appears alive, holds resources indefinitely. The sniper is the ACTIVITY THRESHOLD — ping/pong checks liveness but not usefulness. A connection can be 'alive' but adversarially idle.",
        "absence_risk": "Missing max_reconnect means a down server causes infinite reconnect loop with exponential memory growth in pending messages",
    },
    # ── CRYPTOGRAPHY (Tier: Advanced) ──
    {
        "id": "hash_password_safe", "domain": "cryptography", "tier": "advanced",
        "name": "Password Hashing with Argon2id",
        "python": "import argon2\nimport secrets\n\nhasher = argon2.PasswordHasher(\n    time_cost=3,        # Iterations\n    memory_cost=65536,  # 64 MB\n    parallelism=4,\n    hash_len=32,\n    type=argon2.Type.ID  # Argon2id: hybrid of data-dependent and independent\n)\n\ndef hash_password(password: str) -> str:\n    return hasher.hash(password)  # Salt auto-generated\n\ndef verify_password(stored_hash: str, password: str) -> bool:\n    try:\n        return hasher.verify(stored_hash, password)\n    except argon2.exceptions.VerifyMismatchError:\n        return False\n    except argon2.exceptions.InvalidHashError:\n        return False  # Corrupted hash",
        "typescript": "import argon2 from 'argon2';\n\nasync function hashPassword(password: string): Promise<string> {\n  return argon2.hash(password, {\n    type: argon2.argon2id,\n    memoryCost: 65536,\n    timeCost: 3,\n    parallelism: 4,\n  });\n}\n\nasync function verifyPassword(hash: string, password: string): Promise<boolean> {\n  try { return await argon2.verify(hash, password); }\n  catch { return false; }\n}",
        "rust": "use argon2::{Argon2, PasswordHasher, PasswordVerifier};\nuse argon2::password_hash::{SaltString, rand_core::OsRng};\n\nfn hash_password(password: &[u8]) -> String {\n    let salt = SaltString::generate(&mut OsRng);\n    let argon2 = Argon2::default();\n    argon2.hash_password(password, &salt).unwrap().to_string()\n}\n\nfn verify_password(hash: &str, password: &[u8]) -> bool {\n    let parsed = PasswordHash::new(hash).unwrap();\n    Argon2::default().verify_password(password, &parsed).is_ok()\n}",
        "go": "import \"golang.org/x/crypto/argon2\"\n\nfunc hashPassword(password string) (string, error) {\n    salt := make([]byte, 16)\n    if _, err := rand.Read(salt); err != nil { return \"\", err }\n    hash := argon2.IDKey([]byte(password), salt, 3, 65536, 4, 32)\n    return base64.StdEncoding.EncodeToString(append(salt, hash...)), nil\n}",
        "sql": "-- PostgreSQL with pgcrypto (NOT recommended for passwords — use application layer)\n-- Shown for completeness: gen_salt + crypt use bcrypt, not Argon2\nSELECT crypt($1, gen_salt('bf', 12)) AS hashed;",
        "ast": {"depth": 4, "nodes": ["FunctionDef", "CryptoCall", "SaltGeneration", "Try", "ConstantTimeCompare"], "memory": "heap(64MB_argon2_arena)+stack", "complexity": 3},
        "inverse": "# Passwords are ONE-WAY. There is no inverse.\n# The closest operation is password RESET, not password RECOVERY:\ndef reset_password(user_id: str, new_password: str) -> str:\n    new_hash = hash_password(new_password)\n    store.update(user_id, password_hash=new_hash)\n    invalidate_all_sessions(user_id)  # CRITICAL: old sessions must die\n    return new_hash",
        "inverse_desc": "Hashing is intentionally non-invertible. The 'inverse' is reset (generate new hash), NOT recovery. Any system that can 'recover' passwords is broken by design.",
        "build_orders": {
            "sequential": "Generate salt → hash with Argon2id → store hash",
            "defensive": "Generate salt → hash → verify hash immediately (round-trip check) → store → log event",
            "redundant": "Hash with Argon2id → also compute bcrypt fallback → store both → verify against Argon2id first, bcrypt if format mismatch (migration)",
        },
        "sniper": "timing_oracle",
        "sniper_detail": "If verify returns False faster for 'wrong format' than 'wrong password', the attacker knows whether a hash exists. Argon2 libraries use constant-time comparison internally, but the EXCEPTION PATHS (InvalidHashError vs VerifyMismatchError) may take different times. The sniper is the BRANCH TIMING, not the comparison itself.",
        "absence_risk": "Using SHA-256 instead of Argon2 means passwords are crackable at billions/second on GPU; missing session invalidation on reset means old sessions survive password change",
    },
    {
        "id": "encrypt_envelope", "domain": "cryptography", "tier": "advanced",
        "name": "Authenticated Encryption with Envelope Pattern",
        "python": "from cryptography.hazmat.primitives.ciphers.aead import AESGCM\nimport os, json, base64\n\ndef envelope_encrypt(plaintext: bytes, dek: bytes = None) -> dict:\n    if dek is None:\n        dek = AESGCM.generate_key(bit_length=256)  # Data Encryption Key\n    nonce = os.urandom(12)  # 96-bit nonce, NEVER reuse\n    aad = json.dumps({'ts': int(time.time()), 'ver': 1}).encode()\n    ciphertext = AESGCM(dek).encrypt(nonce, plaintext, aad)\n    return {\n        'v': 1,\n        'nonce': base64.b64encode(nonce).decode(),\n        'aad': base64.b64encode(aad).decode(),\n        'ct': base64.b64encode(ciphertext).decode(),\n        # DEK is encrypted separately by KEK (Key Encryption Key) — not shown here\n    }\n\ndef envelope_decrypt(envelope: dict, dek: bytes) -> bytes:\n    nonce = base64.b64decode(envelope['nonce'])\n    aad = base64.b64decode(envelope['aad'])\n    ct = base64.b64decode(envelope['ct'])\n    return AESGCM(dek).decrypt(nonce, ct, aad)  # Raises InvalidTag if tampered",
        "typescript": "import { createCipheriv, createDecipheriv, randomBytes } from 'crypto';\n\nfunction envelopeEncrypt(plaintext: Buffer, dek?: Buffer): EnvelopeResult {\n  dek ??= randomBytes(32); // AES-256\n  const nonce = randomBytes(12);\n  const aad = Buffer.from(JSON.stringify({ ts: Date.now(), ver: 1 }));\n  const cipher = createCipheriv('aes-256-gcm', dek, nonce);\n  cipher.setAAD(aad);\n  const ct = Buffer.concat([cipher.update(plaintext), cipher.final()]);\n  const tag = cipher.getAuthTag();\n  return { v: 1, nonce: nonce.toString('base64'), aad: aad.toString('base64'),\n           ct: Buffer.concat([ct, tag]).toString('base64') };\n}",
        "rust": "use aes_gcm::{Aes256Gcm, KeyInit, Nonce};\nuse aes_gcm::aead::Aead;\nuse rand::RngCore;\n\nfn envelope_encrypt(plaintext: &[u8], dek: &[u8; 32]) -> Vec<u8> {\n    let cipher = Aes256Gcm::new_from_slice(dek).unwrap();\n    let mut nonce_bytes = [0u8; 12];\n    rand::thread_rng().fill_bytes(&mut nonce_bytes);\n    let nonce = Nonce::from_slice(&nonce_bytes);\n    let ciphertext = cipher.encrypt(nonce, plaintext).unwrap();\n    [nonce_bytes.to_vec(), ciphertext].concat()\n}",
        "go": "func envelopeEncrypt(plaintext, dek []byte) ([]byte, error) {\n    block, err := aes.NewCipher(dek)\n    if err != nil { return nil, err }\n    gcm, err := cipher.NewGCM(block)\n    if err != nil { return nil, err }\n    nonce := make([]byte, gcm.NonceSize())\n    if _, err = io.ReadFull(rand.Reader, nonce); err != nil { return nil, err }\n    return gcm.Seal(nonce, nonce, plaintext, nil), nil\n}",
        "sql": "-- PostgreSQL pgcrypto\nSELECT encode(encrypt_iv(plaintext::bytea, dek::bytea, gen_random_bytes(16), 'aes-cbc'), 'base64');",
        "ast": {"depth": 5, "nodes": ["FunctionDef", "KeyGeneration", "NonceGeneration", "AEADEncrypt", "Base64Encode", "DictReturn"], "memory": "heap(plaintext+ciphertext)+stack+secure_wipe", "complexity": 4},
        "inverse": "# Decryption IS the inverse — but it's authenticated.\n# If ANY bit of ciphertext, nonce, or AAD was modified, decrypt FAILS.\n# This is the critical property: forgery is computationally infeasible.",
        "inverse_desc": "Decryption is the exact inverse; AES-GCM authentication tag guarantees integrity — any tampering causes InvalidTag exception, not silent corruption",
        "build_orders": {
            "sequential": "Generate DEK → generate nonce → encrypt → package envelope",
            "defensive": "Generate DEK → verify entropy source → generate nonce → encrypt → verify by decrypting → package",
            "inverse": "Decrypt → verify AAD timestamp (reject if too old) → verify AAD version → return plaintext",
        },
        "sniper": "nonce_reuse",
        "sniper_detail": "If the same nonce is used twice with the same key, AES-GCM becomes completely broken — an attacker can XOR two ciphertexts to recover both plaintexts AND forge new valid ciphertexts. One nonce reuse = total key compromise. The sniper is a 12-byte value that looks random and harmless.",
        "absence_risk": "Missing AAD means ciphertext can be moved between contexts (replay); missing nonce uniqueness check means catastrophic key compromise on collision",
    },
    # ── AUTHENTICATION & AUTHORIZATION (Tier: Advanced) ──
    {
        "id": "jwt_validate", "domain": "auth", "tier": "advanced",
        "name": "JWT Validation with Algorithm Pinning",
        "python": "import jwt\nfrom datetime import datetime, timezone\n\nALLOWED_ALGORITHMS = ['ES256']  # ONLY allow ECDSA — pin the algorithm\n\ndef validate_token(token: str, public_key: str, issuer: str, audience: str) -> dict:\n    try:\n        payload = jwt.decode(\n            token,\n            public_key,\n            algorithms=ALLOWED_ALGORITHMS,  # CRITICAL: never accept 'none' or 'HS256'\n            issuer=issuer,\n            audience=audience,\n            options={'require': ['exp', 'iat', 'iss', 'aud', 'sub']}\n        )\n    except jwt.ExpiredSignatureError:\n        raise AuthError('Token expired')\n    except jwt.InvalidTokenError as e:\n        raise AuthError(f'Invalid token: {e}')\n    # Additional checks the library doesn't enforce\n    if payload['iat'] > datetime.now(timezone.utc).timestamp():\n        raise AuthError('Token issued in the future')\n    return payload",
        "typescript": "import jwt from 'jsonwebtoken';\n\nconst ALLOWED_ALGORITHMS = ['ES256'] as const;\n\nfunction validateToken(token: string, publicKey: string, issuer: string, audience: string): JwtPayload {\n  try {\n    const payload = jwt.verify(token, publicKey, {\n      algorithms: [...ALLOWED_ALGORITHMS],\n      issuer,\n      audience,\n      complete: false,\n    }) as JwtPayload;\n    if (!payload.exp || !payload.iat || !payload.sub) throw new Error('Missing required claims');\n    return payload;\n  } catch (e) {\n    throw new AuthError(`Token validation failed: ${(e as Error).message}`);\n  }\n}",
        "rust": "use jsonwebtoken::{decode, DecodingKey, Validation, Algorithm};\n\nfn validate_token(token: &str, public_key: &[u8], issuer: &str, audience: &str) -> Result<Claims, AuthError> {\n    let mut validation = Validation::new(Algorithm::ES256);\n    validation.set_issuer(&[issuer]);\n    validation.set_audience(&[audience]);\n    validation.set_required_spec_claims(&[\"exp\", \"iat\", \"iss\", \"aud\", \"sub\"]);\n    let data = decode::<Claims>(token, &DecodingKey::from_ec_pem(public_key)?, &validation)?;\n    Ok(data.claims)\n}",
        "go": "func validateToken(tokenStr, publicKeyPEM, issuer, audience string) (*Claims, error) {\n    key, err := jwt.ParseECPublicKeyFromPEM([]byte(publicKeyPEM))\n    if err != nil { return nil, err }\n    token, err := jwt.ParseWithClaims(tokenStr, &Claims{}, func(t *jwt.Token) (interface{}, error) {\n        if _, ok := t.Method.(*jwt.SigningMethodECDSA); !ok {\n            return nil, fmt.Errorf(\"unexpected signing method: %v\", t.Header[\"alg\"])\n        }\n        return key, nil\n    })\n    if err != nil { return nil, err }\n    claims := token.Claims.(*Claims)\n    if claims.Issuer != issuer { return nil, fmt.Errorf(\"wrong issuer\") }\n    return claims, nil\n}",
        "sql": "-- JWT validation belongs in application layer, not SQL\n-- But: verify at query time that session hasn't been revoked\nSELECT * FROM sessions WHERE token_jti = $1 AND revoked_at IS NULL AND expires_at > NOW();",
        "ast": {"depth": 5, "nodes": ["FunctionDef", "LibraryCall", "AlgorithmPin", "ClaimValidation", "TimestampCheck", "ExceptionHandler"], "memory": "stack+heap(decoded_payload)", "complexity": 5},
        "inverse": "def create_token(payload: dict, private_key: str, ttl_seconds: int = 3600) -> str:\n    now = datetime.now(timezone.utc).timestamp()\n    payload.update({'iat': now, 'exp': now + ttl_seconds})\n    return jwt.encode(payload, private_key, algorithm='ES256')",
        "inverse_desc": "Token creation is the inverse of validation; private key signs what public key verifies. But validation is STRICTER than creation — you can create invalid tokens.",
        "build_orders": {
            "sequential": "Decode → verify signature → check expiry → check claims → return",
            "defensive": "Check token format → decode → verify algorithm → verify signature → check all claims → check revocation list → return",
            "redundant": "Validate JWT → also check session store → if JWT valid but session revoked, reject (belt and suspenders)",
        },
        "sniper": "algorithm_confusion",
        "sniper_detail": "If the server accepts both HS256 and RS256, attacker takes the PUBLIC key (which is public!), signs a token with HS256 using the public key as the HMAC secret. The server verifies with the same public key and accepts it. The sniper is the `algorithms` parameter accepting 'any' — one misconfigured list = full auth bypass.",
        "absence_risk": "Missing algorithm pinning = complete authentication bypass; missing exp/iat checks = eternal tokens",
    },
    {
        "id": "rbac_enforce", "domain": "auth", "tier": "advanced",
        "name": "Role-Based Access Control with Least Privilege",
        "python": "from enum import Flag, auto\nfrom functools import wraps\n\nclass Permission(Flag):\n    NONE = 0\n    READ = auto()\n    WRITE = auto()\n    DELETE = auto()\n    ADMIN = READ | WRITE | DELETE\n\nROLE_PERMISSIONS = {\n    'viewer': Permission.READ,\n    'editor': Permission.READ | Permission.WRITE,\n    'admin': Permission.ADMIN,\n}\n\ndef require_permission(required: Permission):\n    def decorator(fn):\n        @wraps(fn)\n        def wrapper(user, *args, **kwargs):\n            user_perms = ROLE_PERMISSIONS.get(user.role, Permission.NONE)\n            if not (user_perms & required) == required:\n                raise PermissionError(f'{user.role} lacks {required!r}')\n            return fn(user, *args, **kwargs)\n        return wrapper\n    return decorator\n\n@require_permission(Permission.WRITE)\ndef update_record(user, record_id, data): ...",
        "typescript": "enum Permission {\n  NONE = 0,\n  READ = 1 << 0,\n  WRITE = 1 << 1,\n  DELETE = 1 << 2,\n  ADMIN = READ | WRITE | DELETE,\n}\n\nconst ROLE_PERMS: Record<string, Permission> = {\n  viewer: Permission.READ,\n  editor: Permission.READ | Permission.WRITE,\n  admin: Permission.ADMIN,\n};\n\nfunction requirePermission(required: Permission) {\n  return (_target: any, _key: string, desc: PropertyDescriptor) => {\n    const orig = desc.value;\n    desc.value = function(user: User, ...args: any[]) {\n      if ((ROLE_PERMS[user.role] & required) !== required)\n        throw new Error(`${user.role} lacks ${Permission[required]}`);\n      return orig.call(this, user, ...args);\n    };\n  };\n}",
        "rust": "use bitflags::bitflags;\n\nbitflags! {\n    struct Permission: u32 {\n        const NONE   = 0;\n        const READ   = 1 << 0;\n        const WRITE  = 1 << 1;\n        const DELETE = 1 << 2;\n        const ADMIN  = Self::READ.bits() | Self::WRITE.bits() | Self::DELETE.bits();\n    }\n}\n\nfn check_permission(user_role: &str, required: Permission) -> Result<(), AuthError> {\n    let user_perms = match user_role {\n        \"viewer\" => Permission::READ,\n        \"editor\" => Permission::READ | Permission::WRITE,\n        \"admin\" => Permission::ADMIN,\n        _ => Permission::NONE,\n    };\n    if user_perms.contains(required) { Ok(()) } else { Err(AuthError::Forbidden) }\n}",
        "go": "type Permission uint32\n\nconst (\n    PermNone   Permission = 0\n    PermRead   Permission = 1 << iota\n    PermWrite\n    PermDelete\n    PermAdmin = PermRead | PermWrite | PermDelete\n)\n\nvar rolePerms = map[string]Permission{\n    \"viewer\": PermRead,\n    \"editor\": PermRead | PermWrite,\n    \"admin\":  PermAdmin,\n}\n\nfunc checkPermission(role string, required Permission) error {\n    if rolePerms[role]&required != required {\n        return fmt.Errorf(\"%s lacks permission %d\", role, required)\n    }\n    return nil\n}",
        "sql": "-- Row-Level Security in PostgreSQL\nALTER TABLE records ENABLE ROW LEVEL SECURITY;\nCREATE POLICY viewer_read ON records FOR SELECT\n  USING (current_setting('app.role') IN ('viewer', 'editor', 'admin'));\nCREATE POLICY editor_write ON records FOR INSERT\n  USING (current_setting('app.role') IN ('editor', 'admin'));",
        "ast": {"depth": 5, "nodes": ["EnumDef", "BitFlag", "DictLookup", "BitwiseAnd", "Decorator", "Closure", "PermissionCheck"], "memory": "stack+enum_table(static)", "complexity": 4},
        "inverse": "def revoke_permission(user_id: str, permission: Permission) -> None:\n    current = get_user_permissions(user_id)\n    new_perms = current & ~permission  # Bitwise clear\n    store.update(user_id, permissions=new_perms)\n    invalidate_cached_permissions(user_id)",
        "inverse_desc": "Grant is additive (|=), revoke is subtractive (&= ~perm). Inverse of granting WRITE is revoking WRITE via bitwise clear.",
        "build_orders": {
            "sequential": "Get user role → lookup permissions → bitwise check → allow/deny",
            "defensive": "Verify user exists → get role → lookup permissions → check → audit log → allow/deny",
            "redundant": "Check RBAC → also check resource-level ACL → also check time-based restrictions → all must pass",
        },
        "sniper": "privilege_escalation",
        "sniper_detail": "If the permission check uses `user_perms | required` instead of `user_perms & required`, ANY permission satisfies ANY check (bitwise OR vs AND confusion). This is a one-character bug that grants admin to everyone. The sniper is the OPERATOR, not the logic.",
        "absence_risk": "Missing default-deny (NONE instead of ADMIN) means unknown roles get full access; missing cache invalidation means revoked permissions persist until restart",
    },
    # ── CONCURRENCY (Tier: Advanced) ──
    {
        "id": "mutex_resource", "domain": "concurrency", "tier": "advanced",
        "name": "Mutex-Protected Shared Resource",
        "python": "import asyncio\nfrom contextlib import asynccontextmanager\n\nclass SharedCounter:\n    def __init__(self):\n        self._value = 0\n        self._lock = asyncio.Lock()\n        self._history: list[tuple[str, int, int]] = []  # (op, old, new)\n\n    @asynccontextmanager\n    async def modify(self, op_name: str):\n        async with self._lock:\n            old = self._value\n            yield self  # Caller modifies self._value\n            self._history.append((op_name, old, self._value))\n\n    async def increment(self, by: int = 1):\n        async with self.modify('increment'):\n            self._value += by\n\n    async def get(self) -> int:\n        async with self._lock:\n            return self._value",
        "typescript": "class SharedCounter {\n  private value = 0;\n  private lock = new Mutex(); // From async-mutex package\n  private history: [string, number, number][] = [];\n\n  async increment(by = 1): Promise<void> {\n    const release = await this.lock.acquire();\n    try {\n      const old = this.value;\n      this.value += by;\n      this.history.push(['increment', old, this.value]);\n    } finally { release(); }\n  }\n\n  async get(): Promise<number> {\n    const release = await this.lock.acquire();\n    try { return this.value; }\n    finally { release(); }\n  }\n}",
        "rust": "use std::sync::{Arc, Mutex};\n\nstruct SharedCounter {\n    value: Mutex<i64>,\n}\n\nimpl SharedCounter {\n    fn new() -> Self { Self { value: Mutex::new(0) } }\n\n    fn increment(&self, by: i64) {\n        let mut val = self.value.lock().unwrap();\n        *val += by;\n    }\n\n    fn get(&self) -> i64 {\n        *self.value.lock().unwrap()\n    }\n}",
        "go": "type SharedCounter struct {\n    mu    sync.Mutex\n    value int64\n}\n\nfunc (c *SharedCounter) Increment(by int64) {\n    c.mu.Lock()\n    defer c.mu.Unlock()\n    c.value += by\n}\n\nfunc (c *SharedCounter) Get() int64 {\n    c.mu.Lock()\n    defer c.mu.Unlock()\n    return c.value\n}",
        "sql": "-- Database-level locking\nBEGIN;\nSELECT value FROM counters WHERE id = $1 FOR UPDATE; -- Row lock\nUPDATE counters SET value = value + $2 WHERE id = $1;\nCOMMIT;",
        "ast": {"depth": 5, "nodes": ["ClassDef", "Lock", "ContextManager", "AtomicModify", "History", "Yield"], "memory": "heap(lock+history)+stack", "complexity": 5},
        "inverse": "async def rollback_last(self) -> bool:\n    async with self._lock:\n        if not self._history:\n            return False\n        op, old, new = self._history.pop()\n        self._value = old  # Restore previous value\n        return True",
        "inverse_desc": "History enables exact rollback: pop last operation, restore old value. Without history, mutation is non-invertible.",
        "build_orders": {
            "sequential": "Acquire lock → read → modify → release",
            "defensive": "Acquire lock with timeout → read → modify → verify invariant → release → if invariant broken, rollback",
            "redundant": "Lock → modify → write to WAL (write-ahead log) → release → if crash, replay WAL",
        },
        "sniper": "deadlock",
        "sniper_detail": "If two coroutines each hold lock A and wait for lock B (and vice versa), both block forever. The sniper is LOCK ORDERING — acquiring locks in different orders across different code paths creates circular wait. This is invisible in single-threaded testing.",
        "absence_risk": "Missing lock on get() means reads see partial writes; missing history means mutations are irreversible",
    },
    # ── DATABASE (Tier: Intermediate-Advanced) ──
    {
        "id": "sql_parameterized", "domain": "database", "tier": "intermediate",
        "name": "Parameterized Query with Connection Pooling",
        "python": "import asyncpg\n\nclass DB:\n    def __init__(self, dsn: str, min_pool: int = 2, max_pool: int = 10):\n        self._dsn = dsn\n        self._pool = None\n        self._min = min_pool\n        self._max = max_pool\n\n    async def connect(self):\n        self._pool = await asyncpg.create_pool(self._dsn, min_size=self._min, max_size=self._max)\n\n    async def fetch_one(self, query: str, *params) -> dict | None:\n        async with self._pool.acquire() as conn:\n            row = await conn.fetchrow(query, *params)  # Parameterized — no SQL injection\n            return dict(row) if row else None\n\n    async def execute(self, query: str, *params) -> str:\n        async with self._pool.acquire() as conn:\n            return await conn.execute(query, *params)\n\n    async def close(self):\n        await self._pool.close()\n\n# Usage: await db.fetch_one('SELECT * FROM users WHERE id = $1', user_id)",
        "typescript": "import { Pool, PoolClient } from 'pg';\n\nconst pool = new Pool({ max: 10, min: 2, connectionString: process.env.DATABASE_URL });\n\nasync function fetchOne<T>(query: string, params: unknown[]): Promise<T | null> {\n  const client = await pool.connect();\n  try {\n    const { rows } = await client.query(query, params); // Parameterized\n    return rows[0] ?? null;\n  } finally { client.release(); }\n}\n\n// Usage: await fetchOne('SELECT * FROM users WHERE id = $1', [userId]);",
        "rust": "use sqlx::PgPool;\n\nasync fn fetch_one(pool: &PgPool, user_id: i64) -> Result<Option<User>, sqlx::Error> {\n    sqlx::query_as!(User, \"SELECT * FROM users WHERE id = $1\", user_id)\n        .fetch_optional(pool)\n        .await\n}",
        "go": "func fetchOne(pool *pgxpool.Pool, userID int64) (*User, error) {\n    var user User\n    err := pool.QueryRow(context.Background(),\n        \"SELECT id, name, email FROM users WHERE id = $1\", userID).Scan(&user.ID, &user.Name, &user.Email)\n    if err == pgx.ErrNoRows { return nil, nil }\n    return &user, err\n}",
        "sql": "-- The query itself — parameterized at call site\nPREPARE user_by_id (bigint) AS SELECT * FROM users WHERE id = $1;\nEXECUTE user_by_id(42);",
        "ast": {"depth": 5, "nodes": ["ClassDef", "AsyncMethod", "PoolAcquire", "ContextManager", "ParameterizedQuery", "RowMapping"], "memory": "heap(pool_connections)+stack", "complexity": 4},
        "inverse": "async def undo_insert(self, table: str, row_id: int) -> bool:\n    result = await self.execute(f'DELETE FROM {table} WHERE id = $1 RETURNING id', row_id)\n    return 'DELETE 1' in result",
        "inverse_desc": "INSERT inverse is DELETE by primary key; UPDATE inverse requires storing previous values (audit trail); SELECT has no inverse (read-only)",
        "build_orders": {
            "sequential": "Acquire connection → prepare query → bind params → execute → release",
            "defensive": "Acquire with timeout → prepare → bind → execute in transaction → commit → release → on failure, rollback",
            "redundant": "Try primary pool → on exhaustion, try read replica pool → on failure, queue for retry",
        },
        "sniper": "sql_injection_via_identifier",
        "sniper_detail": "Parameters protect VALUES ($1, $2) but NOT identifiers (table names, column names). `f'SELECT * FROM {table}'` is injectable even with parameterized values. The sniper is the TABLE NAME — developers parameterize values religiously but interpolate identifiers carelessly.",
        "absence_risk": "Missing connection pool means each query opens a new TCP connection (100x slower); missing pool.close() means connection leak until OS kills the process",
    },
    {
        "id": "transaction_saga", "domain": "database", "tier": "advanced",
        "name": "Saga Pattern for Distributed Transactions",
        "python": "class Saga:\n    def __init__(self):\n        self._steps: list[tuple[callable, callable]] = []  # (execute, compensate)\n        self._completed: list[int] = []\n\n    def add_step(self, execute, compensate):\n        self._steps.append((execute, compensate))\n\n    async def run(self) -> bool:\n        for i, (execute, _) in enumerate(self._steps):\n            try:\n                await execute()\n                self._completed.append(i)\n            except Exception as e:\n                await self._compensate()\n                raise SagaFailed(f'Step {i} failed: {e}', completed=self._completed) from e\n        return True\n\n    async def _compensate(self):\n        # Compensate in REVERSE order\n        for i in reversed(self._completed):\n            _, compensate = self._steps[i]\n            try:\n                await compensate()\n            except Exception as e:\n                # Compensation failure is CRITICAL — log for manual intervention\n                logger.critical(f'Compensation step {i} failed: {e}')\n\n# Usage:\n# saga.add_step(charge_payment, refund_payment)\n# saga.add_step(reserve_inventory, release_inventory)\n# saga.add_step(send_notification, noop)  # Notifications can't be un-sent",
        "typescript": "type SagaStep = { execute: () => Promise<void>; compensate: () => Promise<void>; };\n\nclass Saga {\n  private steps: SagaStep[] = [];\n  private completed: number[] = [];\n\n  addStep(execute: () => Promise<void>, compensate: () => Promise<void>): void {\n    this.steps.push({ execute, compensate });\n  }\n\n  async run(): Promise<boolean> {\n    for (let i = 0; i < this.steps.length; i++) {\n      try {\n        await this.steps[i].execute();\n        this.completed.push(i);\n      } catch (e) {\n        await this.compensate();\n        throw new SagaFailed(`Step ${i} failed`, { cause: e });\n      }\n    }\n    return true;\n  }\n\n  private async compensate(): Promise<void> {\n    for (const i of [...this.completed].reverse()) {\n      try { await this.steps[i].compensate(); }\n      catch (e) { console.error(`Compensation ${i} failed:`, e); }\n    }\n  }\n}",
        "rust": "struct Saga {\n    steps: Vec<(Box<dyn AsyncFn>, Box<dyn AsyncFn>)>,\n    completed: Vec<usize>,\n}\n\nimpl Saga {\n    async fn run(&mut self) -> Result<(), SagaError> {\n        for (i, (execute, _)) in self.steps.iter().enumerate() {\n            match execute().await {\n                Ok(()) => self.completed.push(i),\n                Err(e) => {\n                    self.compensate().await;\n                    return Err(SagaError::StepFailed(i, e));\n                }\n            }\n        }\n        Ok(())\n    }\n    async fn compensate(&self) {\n        for &i in self.completed.iter().rev() {\n            let _ = self.steps[i].1().await; // Best-effort\n        }\n    }\n}",
        "go": "type SagaStep struct {\n    Execute    func(ctx context.Context) error\n    Compensate func(ctx context.Context) error\n}\n\ntype Saga struct {\n    steps     []SagaStep\n    completed []int\n}\n\nfunc (s *Saga) Run(ctx context.Context) error {\n    for i, step := range s.steps {\n        if err := step.Execute(ctx); err != nil {\n            s.compensate(ctx)\n            return fmt.Errorf(\"saga step %d failed: %w\", i, err)\n        }\n        s.completed = append(s.completed, i)\n    }\n    return nil\n}\n\nfunc (s *Saga) compensate(ctx context.Context) {\n    for i := len(s.completed) - 1; i >= 0; i-- {\n        _ = s.steps[s.completed[i]].Compensate(ctx)\n    }\n}",
        "sql": "-- Saga-like in SQL using savepoints\nBEGIN;\nSAVEPOINT step_1;\n-- Execute step 1\nSAVEPOINT step_2;\n-- Execute step 2\n-- On step 3 failure:\nROLLBACK TO SAVEPOINT step_2;\nROLLBACK TO SAVEPOINT step_1;\nCOMMIT;",
        "ast": {"depth": 6, "nodes": ["ClassDef", "StepList", "AsyncExecute", "CompensationLoop", "ReverseIteration", "CriticalLog"], "memory": "heap(step_closures+completed_indices)+stack", "complexity": 6},
        "inverse": "# The Saga IS its own inverse — compensation IS the inverse operation.\n# But: some operations have no true inverse (sent email, published event).\n# Those get 'semantic compensation' (send correction email, publish retraction).",
        "inverse_desc": "Each step has an explicit compensating action; the saga framework automatically applies them in reverse on failure. Non-invertible steps require semantic compensation.",
        "build_orders": {
            "sequential": "Step 1 → Step 2 → Step 3 → done (or compensate in reverse)",
            "parallel": "Independent steps run concurrently; dependent steps run sequentially; compensation always sequential reverse",
            "redundant": "Primary saga → on compensation failure, escalate to dead letter queue → manual intervention",
        },
        "sniper": "compensation_failure",
        "sniper_detail": "What if the COMPENSATION itself fails? You charged the customer, inventory update failed, but the refund also fails. Now you have an inconsistent state with no automatic recovery. The sniper is the assumption that compensation always succeeds — in distributed systems, it doesn't.",
        "absence_risk": "Missing compensation for a step means partial failure leaves permanent inconsistency; missing reverse-order execution means later compensations run before earlier ones, violating causal ordering",
    },
    # ── SECRET MANAGEMENT (Tier: Advanced) ──
    {
        "id": "secret_rotation", "domain": "secrets", "tier": "advanced",
        "name": "Secret Rotation with Zero-Downtime Overlap",
        "python": "import os, time\nfrom typing import Optional\n\nclass SecretManager:\n    def __init__(self):\n        self._current: Optional[str] = None\n        self._previous: Optional[str] = None\n        self._rotated_at: float = 0\n        self._overlap_seconds: float = 300  # 5 min overlap window\n\n    def rotate(self, new_secret: str) -> None:\n        self._previous = self._current\n        self._current = new_secret\n        self._rotated_at = time.time()\n\n    def validate(self, candidate: str) -> bool:\n        # Accept BOTH current and previous during overlap window\n        if candidate == self._current:\n            return True\n        if (self._previous and\n            candidate == self._previous and\n            time.time() - self._rotated_at < self._overlap_seconds):\n            return True\n        return False\n\n    def get_current(self) -> str:\n        if self._current is None:\n            raise RuntimeError('No secret configured')\n        return self._current",
        "typescript": "class SecretManager {\n  private current: string | null = null;\n  private previous: string | null = null;\n  private rotatedAt = 0;\n  private overlapMs = 300_000; // 5 min\n\n  rotate(newSecret: string): void {\n    this.previous = this.current;\n    this.current = newSecret;\n    this.rotatedAt = Date.now();\n  }\n\n  validate(candidate: string): boolean {\n    if (candidate === this.current) return true;\n    if (this.previous && candidate === this.previous && Date.now() - this.rotatedAt < this.overlapMs)\n      return true;\n    return false;\n  }\n}",
        "rust": "struct SecretManager {\n    current: Option<String>,\n    previous: Option<String>,\n    rotated_at: Instant,\n    overlap: Duration,\n}\n\nimpl SecretManager {\n    fn rotate(&mut self, new: String) {\n        self.previous = self.current.take();\n        self.current = Some(new);\n        self.rotated_at = Instant::now();\n    }\n    fn validate(&self, candidate: &str) -> bool {\n        if self.current.as_deref() == Some(candidate) { return true; }\n        if let Some(prev) = &self.previous {\n            if prev == candidate && self.rotated_at.elapsed() < self.overlap { return true; }\n        }\n        false\n    }\n}",
        "go": "type SecretManager struct {\n    mu        sync.RWMutex\n    current   string\n    previous  string\n    rotatedAt time.Time\n    overlap   time.Duration\n}\n\nfunc (sm *SecretManager) Rotate(newSecret string) {\n    sm.mu.Lock()\n    defer sm.mu.Unlock()\n    sm.previous = sm.current\n    sm.current = newSecret\n    sm.rotatedAt = time.Now()\n}\n\nfunc (sm *SecretManager) Validate(candidate string) bool {\n    sm.mu.RLock()\n    defer sm.mu.RUnlock()\n    if candidate == sm.current { return true }\n    if sm.previous != \"\" && candidate == sm.previous && time.Since(sm.rotatedAt) < sm.overlap { return true }\n    return false\n}",
        "sql": "-- Secrets table with rotation tracking\nCREATE TABLE secrets (\n  name TEXT PRIMARY KEY,\n  current_value TEXT NOT NULL,\n  previous_value TEXT,\n  rotated_at TIMESTAMPTZ DEFAULT NOW(),\n  overlap_seconds INT DEFAULT 300\n);\n-- Validation query\nSELECT 1 FROM secrets WHERE name = $1 AND (\n  current_value = $2 OR\n  (previous_value = $2 AND rotated_at + (overlap_seconds || ' seconds')::interval > NOW())\n);",
        "ast": {"depth": 4, "nodes": ["ClassDef", "StateRotation", "OverlapWindow", "ConstantTimeCompare", "TimestampCheck"], "memory": "heap(2_secrets)+timer", "complexity": 4},
        "inverse": "def emergency_revoke_all(self) -> None:\n    # Nuclear option: invalidate BOTH current and previous immediately\n    self._current = None\n    self._previous = None\n    self._rotated_at = 0\n    logger.critical('All secrets revoked — service will reject all requests until new secret is configured')",
        "inverse_desc": "Inverse of rotation is revocation; but revoking BOTH means total denial of service until re-provisioned. This is intentional — security incident response prioritizes safety over availability.",
        "build_orders": {
            "sequential": "Generate new → set as current (old becomes previous) → wait for overlap → clear previous",
            "defensive": "Generate new → verify entropy → rotate → verify both work → notify consumers → clear previous after TTL",
            "redundant": "Primary secret manager → replicated to standby → on rotation, update both → verify consistency",
        },
        "sniper": "timing_side_channel",
        "sniper_detail": "String comparison `candidate == self._current` is NOT constant-time in most languages. Python and JS compare byte-by-byte and return False on first mismatch. An attacker can measure response time to determine how many leading characters match, brute-forcing the secret one character at a time. The sniper is the == operator.",
        "absence_risk": "Missing overlap window means rotation causes instant outage for in-flight requests using old secret; missing constant-time comparison means secret is recoverable via timing",
    },
    {
        "id": "env_var_safe", "domain": "secrets", "tier": "intermediate",
        "name": "Environment Variable Loading with Validation",
        "python": "import os\nfrom dataclasses import dataclass\nfrom typing import Optional\n\n@dataclass(frozen=True)\nclass Config:\n    db_url: str\n    api_key: str\n    debug: bool\n    max_workers: int\n\ndef load_config() -> Config:\n    def require(name: str) -> str:\n        val = os.environ.get(name)\n        if val is None:\n            raise EnvironmentError(f'Required env var {name} is not set')\n        if len(val) > 10000:  # Sanity bound\n            raise ValueError(f'{name} value suspiciously large: {len(val)} chars')\n        return val\n\n    return Config(\n        db_url=require('DATABASE_URL'),\n        api_key=require('API_KEY'),\n        debug=os.environ.get('DEBUG', 'false').lower() in ('true', '1', 'yes'),\n        max_workers=int(os.environ.get('MAX_WORKERS', '4')),\n    )\n\n# NEVER log config values — redact in __repr__\ndef safe_repr(config: Config) -> str:\n    return f'Config(db_url=***, api_key=***[{len(config.api_key)}chars], debug={config.debug})'",
        "typescript": "interface Config {\n  dbUrl: string;\n  apiKey: string;\n  debug: boolean;\n  maxWorkers: number;\n}\n\nfunction loadConfig(): Config {\n  function require(name: string): string {\n    const val = process.env[name];\n    if (!val) throw new Error(`Required env var ${name} not set`);\n    if (val.length > 10000) throw new Error(`${name} suspiciously large`);\n    return val;\n  }\n  return {\n    dbUrl: require('DATABASE_URL'),\n    apiKey: require('API_KEY'),\n    debug: ['true', '1', 'yes'].includes((process.env.DEBUG ?? 'false').toLowerCase()),\n    maxWorkers: parseInt(process.env.MAX_WORKERS ?? '4', 10),\n  };\n}",
        "rust": "use std::env;\n\nstruct Config {\n    db_url: String,\n    api_key: String,\n    debug: bool,\n    max_workers: usize,\n}\n\nimpl Config {\n    fn from_env() -> Result<Self, String> {\n        Ok(Self {\n            db_url: env::var(\"DATABASE_URL\").map_err(|_| \"DATABASE_URL not set\")?,\n            api_key: env::var(\"API_KEY\").map_err(|_| \"API_KEY not set\")?,\n            debug: env::var(\"DEBUG\").unwrap_or_default().eq_ignore_ascii_case(\"true\"),\n            max_workers: env::var(\"MAX_WORKERS\").unwrap_or(\"4\".into()).parse().map_err(|e| format!(\"MAX_WORKERS: {e}\"))?,\n        })\n    }\n}\n\nimpl fmt::Debug for Config {\n    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {\n        f.debug_struct(\"Config\").field(\"debug\", &self.debug).field(\"max_workers\", &self.max_workers).finish_non_exhaustive()\n    }\n}",
        "go": "type Config struct {\n    DBUrl      string\n    APIKey     string\n    Debug      bool\n    MaxWorkers int\n}\n\nfunc LoadConfig() (*Config, error) {\n    require := func(name string) (string, error) {\n        val := os.Getenv(name)\n        if val == \"\" { return \"\", fmt.Errorf(\"%s not set\", name) }\n        return val, nil\n    }\n    dbURL, err := require(\"DATABASE_URL\")\n    if err != nil { return nil, err }\n    apiKey, err := require(\"API_KEY\")\n    if err != nil { return nil, err }\n    workers, _ := strconv.Atoi(os.Getenv(\"MAX_WORKERS\"))\n    if workers == 0 { workers = 4 }\n    return &Config{DBUrl: dbURL, APIKey: apiKey, Debug: os.Getenv(\"DEBUG\") == \"true\", MaxWorkers: workers}, nil\n}",
        "sql": "-- PostgreSQL runtime config (not env vars, but analogous pattern)\nSHOW app.api_key;  -- DON'T DO THIS — exposes secrets in query logs\n-- Instead: use connection-level settings that aren't logged\nSELECT current_setting('app.api_key', true);  -- true = return NULL if not set",
        "ast": {"depth": 4, "nodes": ["FunctionDef", "EnvLookup", "Validation", "DefaultValue", "FrozenDataclass"], "memory": "stack+heap(config_struct)", "complexity": 3},
        "inverse": "# There is no safe inverse — you can't 'unload' a secret from memory.\n# Best effort: overwrite with zeros, then delete reference\nimport ctypes\ndef scrub_string(s: str) -> None:\n    # WARNING: CPython-specific, may not work with interning\n    buf = ctypes.create_string_buffer(len(s))\n    ctypes.memmove(id(s) + 48, buf, len(s))  # Overwrite string buffer with zeros",
        "inverse_desc": "Secrets in memory cannot be reliably scrubbed in GC languages (Python, JS, Go). Rust's zeroize crate is the only reliable option. The inverse of 'loading a secret' is 'secure memory wipe' — which most languages can't guarantee.",
        "build_orders": {
            "sequential": "Load all required → load optional with defaults → validate types → freeze → return",
            "defensive": "Load → validate → freeze → verify no secrets in string representation → register shutdown hook to scrub",
            "redundant": "Load from env → if missing, try secrets manager (AWS/GCP/Vault) → if missing, try config file (warn) → if missing, fail",
        },
        "sniper": "secret_in_logs",
        "sniper_detail": "Default __repr__ or console.log(config) will print the API key in plaintext to stdout/log files. One debug statement in production = credentials in CloudWatch/Datadog forever. The sniper is the LOGGING FRAMEWORK, not the code itself.",
        "absence_risk": "Missing frozen=True means config can be mutated after load (injection); missing safe_repr means any log/error/traceback leaks secrets",
    },
    # ── INPUT VALIDATION (Tier: Intermediate) ──
    {
        "id": "input_sanitize", "domain": "validation", "tier": "intermediate",
        "name": "Input Sanitization Pipeline",
        "python": "import re\nimport html\nfrom typing import Any\n\nMAX_STRING_LEN = 10000\n\ndef sanitize_string(raw: Any) -> str:\n    if not isinstance(raw, str):\n        raise TypeError(f'Expected string, got {type(raw).__name__}')\n    # Step 1: Length bound\n    if len(raw) > MAX_STRING_LEN:\n        raise ValueError(f'Input too long: {len(raw)} > {MAX_STRING_LEN}')\n    # Step 2: Strip null bytes (C string terminator injection)\n    cleaned = raw.replace('\\x00', '')\n    # Step 3: Normalize Unicode (prevent homoglyph attacks)\n    import unicodedata\n    cleaned = unicodedata.normalize('NFC', cleaned)\n    # Step 4: HTML-encode for output context\n    cleaned = html.escape(cleaned)\n    return cleaned\n\ndef sanitize_int(raw: Any, min_val: int = 0, max_val: int = 2**31 - 1) -> int:\n    if isinstance(raw, bool):  # bool is subclass of int in Python!\n        raise TypeError('Boolean is not an integer')\n    val = int(raw)\n    if not min_val <= val <= max_val:\n        raise ValueError(f'{val} not in [{min_val}, {max_val}]')\n    return val",
        "typescript": "function sanitizeString(raw: unknown): string {\n  if (typeof raw !== 'string') throw new TypeError(`Expected string, got ${typeof raw}`);\n  if (raw.length > 10000) throw new Error(`Too long: ${raw.length}`);\n  let cleaned = raw.replace(/\\0/g, ''); // Null bytes\n  cleaned = cleaned.normalize('NFC'); // Unicode normalization\n  cleaned = cleaned.replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]!));\n  return cleaned;\n}\n\nfunction sanitizeInt(raw: unknown, min = 0, max = 2**31 - 1): number {\n  if (typeof raw === 'boolean') throw new TypeError('Boolean is not integer');\n  const val = Number(raw);\n  if (!Number.isInteger(val)) throw new TypeError(`Not integer: ${raw}`);\n  if (val < min || val > max) throw new RangeError(`${val} not in [${min}, ${max}]`);\n  return val;\n}",
        "rust": "fn sanitize_string(raw: &str, max_len: usize) -> Result<String, ValidationError> {\n    if raw.len() > max_len { return Err(ValidationError::TooLong(raw.len())); }\n    let cleaned: String = raw.chars()\n        .filter(|c| *c != '\\0')\n        .collect();\n    // NFC normalization via unicode-normalization crate\n    Ok(cleaned.nfc().collect())\n}",
        "go": "func sanitizeString(raw string, maxLen int) (string, error) {\n    if len(raw) > maxLen {\n        return \"\", fmt.Errorf(\"too long: %d > %d\", len(raw), maxLen)\n    }\n    cleaned := strings.ReplaceAll(raw, \"\\x00\", \"\")\n    cleaned = norm.NFC.String(cleaned)\n    cleaned = html.EscapeString(cleaned)\n    return cleaned, nil\n}",
        "sql": "-- Validate at insertion time\nALTER TABLE inputs ADD CONSTRAINT input_length CHECK (length(raw_input) <= 10000);\nALTER TABLE inputs ADD CONSTRAINT no_nullbytes CHECK (raw_input !~ '\\x00');",
        "ast": {"depth": 4, "nodes": ["FunctionDef", "TypeCheck", "LengthCheck", "StringReplace", "UnicodeNormalize", "HtmlEscape"], "memory": "heap(2_string_copies)+stack", "complexity": 4},
        "inverse": "def unescape_html(sanitized: str) -> str:\n    return html.unescape(sanitized)  # &amp; → &, &lt; → <\n# NOTE: null byte removal and NFC normalization are NOT reversible\n# Information was intentionally destroyed during sanitization",
        "inverse_desc": "HTML escaping is reversible (unescape). Null byte removal and Unicode normalization are intentionally destructive — information is discarded for safety.",
        "build_orders": {
            "sequential": "Type check → length check → null strip → normalize → escape → return",
            "defensive": "Type check → length check → null strip → normalize → escape → verify no forbidden chars remain → return",
            "redundant": "Application-layer sanitize → also enforce DB constraints → also escape at output layer (defense in depth)",
        },
        "sniper": "unicode_homoglyph",
        "sniper_detail": "Cyrillic 'а' (U+0430) looks identical to Latin 'a' (U+0061). An attacker registers 'аdmin' (Cyrillic a) which passes all ASCII checks but doesn't match 'admin'. NFC normalization doesn't fix cross-script homoglyphs. The sniper is the FONT RENDERER — it shows identical glyphs for different codepoints.",
        "absence_risk": "Missing null byte strip allows C-level string truncation attacks; missing Unicode normalization allows duplicate accounts via normalization-variant usernames; bool-is-int in Python means True passes int validation as 1",
    },
    # ── CACHING (Tier: Intermediate) ──
    {
        "id": "cache_lru_ttl", "domain": "caching", "tier": "intermediate",
        "name": "LRU Cache with TTL Expiration",
        "python": "import time\nfrom collections import OrderedDict\nfrom threading import Lock\n\nclass LRUCache:\n    def __init__(self, capacity: int = 1000, ttl_seconds: float = 300):\n        self._data: OrderedDict[str, tuple[float, any]] = OrderedDict()\n        self._capacity = capacity\n        self._ttl = ttl_seconds\n        self._lock = Lock()\n        self._hits = 0\n        self._misses = 0\n\n    def get(self, key: str):\n        with self._lock:\n            if key not in self._data:\n                self._misses += 1\n                return None\n            ts, value = self._data[key]\n            if time.time() - ts > self._ttl:\n                del self._data[key]  # Expired\n                self._misses += 1\n                return None\n            self._data.move_to_end(key)  # Mark as recently used\n            self._hits += 1\n            return value\n\n    def put(self, key: str, value) -> None:\n        with self._lock:\n            if key in self._data:\n                del self._data[key]\n            elif len(self._data) >= self._capacity:\n                self._data.popitem(last=False)  # Evict LRU\n            self._data[key] = (time.time(), value)\n\n    @property\n    def hit_rate(self) -> float:\n        total = self._hits + self._misses\n        return self._hits / total if total > 0 else 0.0",
        "typescript": "class LRUCache<T> {\n  private data = new Map<string, { ts: number; value: T }>();\n  private hits = 0;\n  private misses = 0;\n  constructor(private capacity = 1000, private ttlMs = 300_000) {}\n\n  get(key: string): T | undefined {\n    const entry = this.data.get(key);\n    if (!entry) { this.misses++; return undefined; }\n    if (Date.now() - entry.ts > this.ttlMs) {\n      this.data.delete(key); this.misses++; return undefined;\n    }\n    // Move to end (Map preserves insertion order)\n    this.data.delete(key);\n    this.data.set(key, entry);\n    this.hits++;\n    return entry.value;\n  }\n\n  put(key: string, value: T): void {\n    this.data.delete(key);\n    if (this.data.size >= this.capacity) {\n      const firstKey = this.data.keys().next().value!;\n      this.data.delete(firstKey);\n    }\n    this.data.set(key, { ts: Date.now(), value });\n  }\n}",
        "rust": "use lru::LruCache;\nuse std::time::{Duration, Instant};\nuse std::num::NonZeroUsize;\n\nstruct TtlLruCache<V> {\n    inner: LruCache<String, (Instant, V)>,\n    ttl: Duration,\n}\n\nimpl<V> TtlLruCache<V> {\n    fn new(cap: usize, ttl: Duration) -> Self {\n        Self { inner: LruCache::new(NonZeroUsize::new(cap).unwrap()), ttl }\n    }\n    fn get(&mut self, key: &str) -> Option<&V> {\n        if let Some((ts, val)) = self.inner.get(key) {\n            if ts.elapsed() < self.ttl { return Some(val); }\n            self.inner.pop(key);\n        }\n        None\n    }\n}",
        "go": "// Using golang-lru with TTL wrapper\ntype entry struct {\n    value interface{}\n    ts    time.Time\n}\n\ntype TTLCache struct {\n    lru *lru.Cache\n    ttl time.Duration\n}\n\nfunc (c *TTLCache) Get(key string) (interface{}, bool) {\n    val, ok := c.lru.Get(key)\n    if !ok { return nil, false }\n    e := val.(*entry)\n    if time.Since(e.ts) > c.ttl {\n        c.lru.Remove(key)\n        return nil, false\n    }\n    return e.value, true\n}",
        "sql": "-- Materialized view as cache with refresh\nCREATE MATERIALIZED VIEW cached_results AS SELECT * FROM expensive_query;\n-- TTL via scheduled refresh\nREFRESH MATERIALIZED VIEW CONCURRENTLY cached_results;  -- Non-blocking",
        "ast": {"depth": 5, "nodes": ["ClassDef", "OrderedDict", "Lock", "TTLCheck", "LRUEviction", "Metrics"], "memory": "heap(ordered_dict_entries)+lock", "complexity": 5},
        "inverse": "def invalidate(self, key: str) -> bool:\n    with self._lock:\n        if key in self._data:\n            del self._data[key]\n            return True\n        return False\n\ndef flush(self) -> int:\n    with self._lock:\n        count = len(self._data)\n        self._data.clear()\n        return count",
        "inverse_desc": "Invalidate removes one entry; flush removes all. Both are lossy — the cached computation must be re-done. Cache is an optimization, so its inverse is 're-compute from source'.",
        "build_orders": {
            "sequential": "Check cache → miss → compute → store → return",
            "defensive": "Check cache → if hit, verify staleness → if stale, recompute → store → return",
            "redundant": "L1 cache (in-process LRU) → L2 cache (Redis) → L3 (database) → compute (defense in depth)",
        },
        "sniper": "cache_poisoning",
        "sniper_detail": "If an attacker can make the application cache a bad response (e.g., by triggering an error during computation that gets cached), ALL subsequent requests for that key return the poisoned value until TTL expires. The sniper is the ERROR PATH — caching failures is as dangerous as caching successes.",
        "absence_risk": "Missing TTL means stale data lives forever; missing capacity bound means unbounded memory growth; missing lock means concurrent access corrupts the OrderedDict",
    },
    # ── LOGGING AND OBSERVABILITY (Tier: Basic-Intermediate) ──
    {
        "id": "structured_logging", "domain": "observability", "tier": "basic",
        "name": "Structured Logging with Secret Redaction",
        "python": "import json, logging, re, time\n\nSECRET_PATTERNS = [\n    re.compile(r'(?i)(api[_-]?key|token|secret|password|bearer)\\s*[:=]\\s*\\S+'),\n    re.compile(r'sk-[a-zA-Z0-9]{20,}'),  # OpenAI/Anthropic key format\n    re.compile(r'ghp_[a-zA-Z0-9]{36}'),   # GitHub PAT\n    re.compile(r'hf_[a-zA-Z0-9]{34}'),     # HuggingFace token\n]\n\ndef redact(msg: str) -> str:\n    for pattern in SECRET_PATTERNS:\n        msg = pattern.sub('[REDACTED]', msg)\n    return msg\n\nclass SafeJsonFormatter(logging.Formatter):\n    def format(self, record):\n        log_entry = {\n            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(record.created)),\n            'level': record.levelname,\n            'logger': record.name,\n            'message': redact(record.getMessage()),\n            'module': record.module,\n            'line': record.lineno,\n        }\n        if record.exc_info:\n            log_entry['exception'] = redact(self.formatException(record.exc_info))\n        return json.dumps(log_entry)",
        "typescript": "const SECRET_PATTERNS = [\n  /(?:api[_-]?key|token|secret|password|bearer)\\s*[:=]\\s*\\S+/gi,\n  /sk-[a-zA-Z0-9]{20,}/g,\n  /ghp_[a-zA-Z0-9]{36}/g,\n  /hf_[a-zA-Z0-9]{34}/g,\n];\n\nfunction redact(msg: string): string {\n  for (const pat of SECRET_PATTERNS) msg = msg.replace(pat, '[REDACTED]');\n  return msg;\n}\n\nfunction log(level: string, message: string, meta?: Record<string, unknown>): void {\n  const entry = {\n    timestamp: new Date().toISOString(),\n    level,\n    message: redact(message),\n    ...Object.fromEntries(Object.entries(meta ?? {}).map(([k, v]) => [k, typeof v === 'string' ? redact(v) : v])),\n  };\n  process.stdout.write(JSON.stringify(entry) + '\\n');\n}",
        "rust": "use regex::Regex;\nuse serde_json::json;\n\nfn redact(msg: &str) -> String {\n    let patterns = [\n        Regex::new(r\"(?i)(api[_-]?key|token|secret|password)\\s*[:=]\\s*\\S+\").unwrap(),\n        Regex::new(r\"sk-[a-zA-Z0-9]{20,}\").unwrap(),\n    ];\n    let mut result = msg.to_string();\n    for re in &patterns {\n        result = re.replace_all(&result, \"[REDACTED]\").into_owned();\n    }\n    result\n}",
        "go": "var secretPatterns = []*regexp.Regexp{\n    regexp.MustCompile(`(?i)(api[_-]?key|token|secret|password)\\s*[:=]\\s*\\S+`),\n    regexp.MustCompile(`sk-[a-zA-Z0-9]{20,}`),\n    regexp.MustCompile(`ghp_[a-zA-Z0-9]{36}`),\n}\n\nfunc redact(msg string) string {\n    for _, re := range secretPatterns {\n        msg = re.ReplaceAllString(msg, \"[REDACTED]\")\n    }\n    return msg\n}\n\nfunc logJSON(level, message string) {\n    entry := map[string]interface{}{\n        \"timestamp\": time.Now().UTC().Format(time.RFC3339),\n        \"level\": level, \"message\": redact(message),\n    }\n    json.NewEncoder(os.Stdout).Encode(entry)\n}",
        "sql": "-- Audit logging table with no secret columns\nCREATE TABLE audit_log (\n  id BIGSERIAL PRIMARY KEY,\n  ts TIMESTAMPTZ DEFAULT NOW(),\n  actor TEXT NOT NULL,\n  action TEXT NOT NULL,\n  resource TEXT NOT NULL,\n  -- NEVER store request bodies or headers that may contain tokens\n  status TEXT NOT NULL\n);",
        "ast": {"depth": 4, "nodes": ["ClassDef", "RegexCompile", "RegexSub", "JsonSerialize", "TimestampFormat"], "memory": "heap(compiled_regex+log_string)+stack", "complexity": 3},
        "inverse": "# Redaction is intentionally NON-REVERSIBLE.\n# You CANNOT recover 'sk-abc123...' from '[REDACTED]'.\n# This is a feature, not a limitation.",
        "inverse_desc": "Redaction is a one-way hash of information. The inverse would be 'de-redaction' which requires the original value — if you had it, you wouldn't need to de-redact.",
        "build_orders": {
            "sequential": "Format message → redact → serialize to JSON → write to stdout",
            "defensive": "Format → redact → validate no secrets remain (double-check) → serialize → write → flush",
            "redundant": "Log to stdout (structured) → also log to file (for persistence) → also send to aggregator (for alerting)",
        },
        "sniper": "log_injection",
        "sniper_detail": "If user input contains newlines, an attacker can inject fake log entries: `username\\n{\"level\":\"INFO\",\"message\":\"Admin login successful\"}`. Log parsers treat each line as a separate entry. The sniper is the NEWLINE CHARACTER in unescaped user input.",
        "absence_risk": "Missing redaction means secrets appear in CloudWatch/Splunk/Datadog forever (you can't delete cloud logs); missing JSON structure means log parsing breaks on messages containing quotes or newlines",
    },
]

# ═══════════════════════════════════════════════════════════════════
# SECTION 2: THREAT CATALOG — the snipers in the hills
# ═══════════════════════════════════════════════════════════════════

THREATS = {
    "type_confusion": {
        "name": "Type Confusion",
        "category": "logic",
        "detection": "Check isinstance/typeof at boundary, not deep in logic",
        "mitigation": "Type guards at every deserialization boundary; frozen dataclasses/interfaces",
    },
    "unbounded_iteration": {
        "name": "Unbounded Iteration / Resource Exhaustion",
        "category": "availability",
        "detection": "Any loop without explicit termination bound",
        "mitigation": "MAX_ITER constant; timeout wrapper; generator with .take(n)",
    },
    "float_precision": {
        "name": "IEEE 754 Float Precision Loss",
        "category": "correctness",
        "detection": "Multiplication/division near float boundaries (1e308, 1e-308, 0.1+0.2)",
        "mitigation": "Decimal types for money; explicit overflow checks; epsilon comparisons",
    },
    "exception_swallowing": {
        "name": "Exception Hierarchy Mismatch",
        "category": "reliability",
        "detection": "Bare except/catch that doesn't re-raise system exceptions",
        "mitigation": "Catch specific types; always `from e` for chain; never catch BaseException",
    },
    "hash_dos": {
        "name": "Hash Collision Denial of Service",
        "category": "availability",
        "detection": "Custom hash maps with deterministic hash functions",
        "mitigation": "Randomized hashing (SipHash); key length bounds; rate limiting",
    },
    "unbounded_memory": {
        "name": "Unbounded Memory Growth",
        "category": "availability",
        "detection": "Any collection without capacity limit; any buffer without max size",
        "mitigation": "Bounded queues; LRU eviction; streaming instead of buffering",
    },
    "stack_overflow_via_depth": {
        "name": "Stack Overflow via Deep Recursion",
        "category": "availability",
        "detection": "Recursive function without depth limit AND without cycle detection",
        "mitigation": "Explicit depth counter; visited set for graphs; iterative rewrite for deep trees",
    },
    "billion_laughs": {
        "name": "Nested Structure Bomb",
        "category": "availability",
        "detection": "Parser accepts arbitrary nesting depth",
        "mitigation": "Max nesting depth limit; streaming parser; payload size limit",
    },
    "toctou_race": {
        "name": "Time-of-Check-to-Time-of-Use Race",
        "category": "integrity",
        "detection": "Any check-then-act pattern with filesystem or shared state",
        "mitigation": "Atomic operations (rename, open with O_EXCL); lock files; database transactions",
    },
    "dns_rebinding": {
        "name": "DNS Rebinding / SSRF",
        "category": "confidentiality",
        "detection": "URL validation before DNS resolution, followed by separate connection",
        "mitigation": "Resolve DNS first, validate IP, connect to IP directly; block redirects",
    },
    "slowloris": {
        "name": "Slow Connection Resource Exhaustion",
        "category": "availability",
        "detection": "Connections without activity timeout or minimum throughput requirement",
        "mitigation": "Per-connection timeout; minimum data rate threshold; connection limits per IP",
    },
    "timing_oracle": {
        "name": "Timing Side Channel",
        "category": "confidentiality",
        "detection": "String comparison (==) for secrets; early-return on mismatch",
        "mitigation": "hmac.compare_digest; constant-time comparison; fixed-time response",
    },
    "nonce_reuse": {
        "name": "Cryptographic Nonce Reuse",
        "category": "confidentiality",
        "detection": "Counter-based nonce without persistence; random nonce without sufficient entropy",
        "mitigation": "CSPRNG for nonce generation; nonce-misuse-resistant schemes (AES-GCM-SIV); key rotation",
    },
    "algorithm_confusion": {
        "name": "Algorithm Confusion / Downgrade",
        "category": "authentication",
        "detection": "JWT/crypto libraries accepting multiple algorithms without explicit pinning",
        "mitigation": "Whitelist exactly one algorithm; reject 'none'; verify alg matches expected",
    },
    "privilege_escalation": {
        "name": "Privilege Escalation via Logic Bug",
        "category": "authorization",
        "detection": "Permission checks using OR instead of AND; missing default-deny",
        "mitigation": "Bitwise AND for permission checks; default to Permission.NONE; audit all role mappings",
    },
    "deadlock": {
        "name": "Deadlock via Lock Ordering",
        "category": "availability",
        "detection": "Multiple locks acquired in different orders across code paths",
        "mitigation": "Global lock ordering convention; lock timeout with retry; deadlock detection (cycle in wait graph)",
    },
    "sql_injection_via_identifier": {
        "name": "SQL Injection via Table/Column Name",
        "category": "confidentiality",
        "detection": "f-strings or concatenation for table/column names in queries",
        "mitigation": "Whitelist valid identifiers; use ORM; quote identifiers with pg_quote_ident()",
    },
    "compensation_failure": {
        "name": "Saga Compensation Failure",
        "category": "consistency",
        "detection": "Distributed transactions without compensation logging",
        "mitigation": "Persist compensation log; dead letter queue for failed compensations; manual intervention alerts",
    },
    "timing_side_channel": {
        "name": "Secret Comparison Timing Leak",
        "category": "confidentiality",
        "detection": "Direct string equality for secret validation",
        "mitigation": "hmac.compare_digest or equivalent constant-time compare; fixed response timing",
    },
    "secret_in_logs": {
        "name": "Credential Exposure in Logs/Errors",
        "category": "confidentiality",
        "detection": "Default __repr__/toString on config objects containing secrets; error messages interpolating secret values",
        "mitigation": "Custom __repr__ that redacts; structured logging with auto-redaction; never log config objects directly",
    },
    "unicode_homoglyph": {
        "name": "Unicode Homoglyph Identity Bypass",
        "category": "authentication",
        "detection": "Username/identifier comparison without script normalization",
        "mitigation": "Restrict to ASCII for identifiers; or apply Unicode confusable detection (ICU); NFC + script consistency check",
    },
    "log_injection": {
        "name": "Log Injection via Newlines",
        "category": "integrity",
        "detection": "User input written to logs without newline escaping",
        "mitigation": "JSON-structured logging (newlines escaped by serializer); strip control chars from user input",
    },
    "cache_poisoning": {
        "name": "Cache Poisoning via Error Caching",
        "category": "integrity",
        "detection": "Cache stores error responses alongside valid ones",
        "mitigation": "Only cache successful results; use separate error cache with shorter TTL; validate before caching",
    },
}

# ═══════════════════════════════════════════════════════════════════
# SECTION 3: COMPLEXITY MODIFIERS — make the same atom teach more
# ═══════════════════════════════════════════════════════════════════

COMPLEXITY_MODIFIERS = [
    {
        "id": "base", "tier": "basic",
        "instruction_prefix": "Implement",
        "l0_extra": "",
        "l1_extra": "",
        "l2_extra": "",
    },
    {
        "id": "with_tests", "tier": "intermediate",
        "instruction_prefix": "Implement and write unit tests for",
        "l0_extra": " | Test_Coverage: branch+edge+error_path",
        "l1_extra": " | Testability: inject dependencies, mock external calls",
        "l2_extra": " | Test_Blind_Spots: what edge cases are the tests NOT covering?",
    },
    {
        "id": "with_monitoring", "tier": "intermediate",
        "instruction_prefix": "Implement with observability hooks for",
        "l0_extra": " | Metrics: latency_histogram, error_counter, throughput_gauge",
        "l1_extra": " | Trace_Points: entry, exit, error, retry",
        "l2_extra": " | Alert_Conditions: when should this trigger a page?",
    },
    {
        "id": "production_hardened", "tier": "advanced",
        "instruction_prefix": "Implement a production-hardened version of",
        "l0_extra": " | Resource_Budget: max_memory=256MB, max_cpu=2s, max_fds=100",
        "l1_extra": " | Graceful_Degradation: what happens under partial failure?",
        "l2_extra": " | Blast_Radius: if this component fails, what else breaks?",
    },
    {
        "id": "adversarial_review", "tier": "advanced",
        "instruction_prefix": "Review this code for adversarial exploitation vectors:",
        "l0_extra": " | Attack_Surface: memory_layout, timing_channels, resource_limits",
        "l1_extra": " | Kill_Chain: how does an attacker chain this with other vulnerabilities?",
        "l2_extra": " | APT_Persistence: could an attacker maintain access through this component?",
    },
]

# ═══════════════════════════════════════════════════════════════════
# SECTION 4: LANGUAGES
# ═══════════════════════════════════════════════════════════════════

LANGUAGES = ["python", "typescript", "rust", "go", "sql"]

# ═══════════════════════════════════════════════════════════════════
# SECTION 5: INSTRUCTION TEMPLATES — varying how we ask
# ═══════════════════════════════════════════════════════════════════

INSTRUCTION_TEMPLATES = [
    "{modifier_prefix} a {tier} {name} in {lang}. {threat_context}",
    "Write {lang} code for: {name}. Difficulty: {tier}. {threat_context}",
    "Given this requirement — {name} — write a {tier}-level {lang} implementation. {threat_context}",
    "How would you implement {name} in {lang} at {tier} level? {threat_context}",
    "Show me a secure {lang} implementation of {name}. Consider: {threat_context}",
    "Implement {name} in {lang}. This is {tier}-level code. Key concern: {threat_context}",
    "Build a {name} module in {lang}. Requirements: {tier} tier, must handle {threat_name}.",
    "Code review task: verify this {name} implementation in {lang} handles {threat_name} correctly.",
]

THREAT_CONTEXT_TEMPLATES = [
    "Protect against {threat_name}: {threat_detail}",
    "The primary threat is {threat_name}. {threat_detail}",
    "Must be resilient to {threat_name}. Explain your defense.",
    "Consider the {threat_name} attack vector: {threat_detail}",
    "Security requirement: mitigate {threat_name}.",
]


# ═══════════════════════════════════════════════════════════════════
# SECTION 6: GENERATOR ENGINE
# ═══════════════════════════════════════════════════════════════════

def build_l0_view(atom: dict, lang: str, modifier: dict) -> str:
    ast = atom["ast"]
    lines = [
        f"[L0:SUBSTRATE] Domain: {atom['domain']} | Tier: {atom['tier']}",
        f"  AST: depth={ast['depth']}, nodes={ast['nodes']}",
        f"  Memory_Model: {ast['memory']}",
        f"  Cyclomatic_Complexity: {ast['complexity']}",
        f"  Language: {lang.upper()}",
        f"  Binary_Properties: All code lives in bytes 0x09-0x7E (95/256 usable)",
    ]
    if modifier["l0_extra"]:
        lines.append(f"  Extended{modifier['l0_extra']}")
    return "\n".join(lines)


def build_l1_view(atom: dict, modifier: dict) -> str:
    bo = atom["build_orders"]
    lines = [
        f"[L1:COORDINATION] Operation: {atom['name']}",
        f"  Inverse_Operation: {atom['inverse_desc']}",
        f"  Build_Orders:",
    ]
    for order_name, order_desc in bo.items():
        lines.append(f"    {order_name}: {order_desc}")
    if modifier["l1_extra"]:
        lines.append(f"  Extended{modifier['l1_extra']}")
    return "\n".join(lines)


def build_l2_view(atom: dict, threat: dict, modifier: dict) -> str:
    lines = [
        f"[L2:ORIENTATION — THE SNIPER]",
        f"  Primary_Threat: {threat['name']} ({threat['category']})",
        f"  How_It_Hides: {atom['sniper_detail']}",
        f"  Detection: {threat['detection']}",
        f"  Mitigation: {threat['mitigation']}",
        f"  Absence_Risk: {atom['absence_risk']}",
    ]
    if modifier["l2_extra"]:
        lines.append(f"  Extended{modifier['l2_extra']}")
    return "\n".join(lines)


def build_l3_view(atom: dict, lang: str) -> str:
    code = atom.get(lang, atom.get("python", "# No implementation for this language"))
    lines = [
        f"[L3:EXPRESSION] {atom['name']}",
        f"```{lang}",
        code,
        "```",
    ]
    # Include inverse code
    if atom.get("inverse"):
        lines.extend([
            f"\n// Inverse operation:",
            f"```{lang if lang == 'python' else 'python'}",
            atom["inverse"],
            "```",
        ])
    return "\n".join(lines)


def generate_instruction(atom: dict, lang: str, modifier: dict, threat: dict) -> str:
    template = random.choice(INSTRUCTION_TEMPLATES)
    threat_ctx_template = random.choice(THREAT_CONTEXT_TEMPLATES)

    threat_context = threat_ctx_template.format(
        threat_name=threat["name"],
        threat_detail=atom["sniper_detail"][:120] + "..." if len(atom["sniper_detail"]) > 120 else atom["sniper_detail"],
    )

    instruction = template.format(
        modifier_prefix=modifier["instruction_prefix"],
        tier=atom["tier"],
        name=atom["name"],
        lang=lang.capitalize(),
        threat_context=threat_context,
        threat_name=threat["name"],
        threat_detail=atom["sniper_detail"][:100],
    )
    return instruction


def generate_record_id(atom_id: str, lang: str, modifier_id: str, threat_id: str) -> str:
    key = f"{atom_id}:{lang}:{modifier_id}:{threat_id}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def generate_all_pairs():
    baseline_records = []
    multiview_records = []

    # Generate all valid combinations
    combos = []
    for atom in ATOMS:
        atom_threat_id = atom["sniper"]
        atom_threat = THREATS[atom_threat_id]

        for lang in LANGUAGES:
            if lang not in atom:
                continue  # Skip languages without implementation

            for modifier in COMPLEXITY_MODIFIERS:
                # Primary: atom's own threat
                combos.append((atom, lang, modifier, atom_threat, atom_threat_id))

                # Cross-pollinate: pair atom with ALL other threats for translateral density
                # 23 atoms x 5 langs x 5 modifiers x 23 threats = 13,225 unique combos
                for cross_threat_id, cross_threat in THREATS.items():
                    if cross_threat_id != atom_threat_id:
                        combos.append((atom, lang, modifier, cross_threat, cross_threat_id))

    random.shuffle(combos)

    # Generate records up to target
    seen_ids = set()
    for atom, lang, modifier, threat, threat_id in combos:
        if len(baseline_records) >= TARGET_COUNT:
            break

        rec_id = generate_record_id(atom["id"], lang, modifier["id"], threat_id)
        if rec_id in seen_ids:
            continue
        seen_ids.add(rec_id)

        instruction = generate_instruction(atom, lang, modifier, threat)

        # L3 only (baseline)
        l3 = build_l3_view(atom, lang)
        baseline_records.append({
            "text": f"<|im_start|>user\n{instruction}<|im_end|>\n<|im_start|>assistant\n{l3}<|im_end|>"
        })

        # Full multiview
        l0 = build_l0_view(atom, lang, modifier)
        l1 = build_l1_view(atom, modifier)
        l2 = build_l2_view(atom, threat, modifier)
        multiview_output = f"{l0}\n\n{l1}\n\n{l2}\n\n{l3}"

        # Add tongue tags for SCBE integration
        tongue_tag = f"[Tongue:CA|Null:KO,AV,UM|Layer:L0-L3|Gov:ALLOW]"
        multiview_records.append({
            "text": f"<|im_start|>user\n{instruction} {tongue_tag}<|im_end|>\n<|im_start|>assistant\n{multiview_output}<|im_end|>"
        })

    # Trim to exact target
    baseline_records = baseline_records[:TARGET_COUNT]
    multiview_records = multiview_records[:TARGET_COUNT]

    return baseline_records, multiview_records


def main():
    print(f"=== Translateral Code Training Pair Generator ===")
    print(f"Target: {TARGET_COUNT} matched A/B pairs")
    print(f"Atoms: {len(ATOMS)}")
    print(f"Threats: {len(THREATS)}")
    print(f"Languages: {LANGUAGES}")
    print(f"Complexity modifiers: {len(COMPLEXITY_MODIFIERS)}")
    print(f"Instruction templates: {len(INSTRUCTION_TEMPLATES)}")
    print()

    # Calculate theoretical space
    total_combos = 0
    for atom in ATOMS:
        langs_available = sum(1 for l in LANGUAGES if l in atom)
        total_combos += langs_available * len(COMPLEXITY_MODIFIERS) * len(THREATS)  # every atom x every threat
    print(f"Theoretical combination space: {total_combos}")
    print()

    baseline, multiview = generate_all_pairs()

    with open(FILE_BASELINE, "w", encoding="utf-8") as f:
        for r in baseline:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(FILE_MULTIVIEW, "w", encoding="utf-8") as f:
        for r in multiview:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Stats
    print(f"Generated:")
    print(f"  Baseline (L3 only): {len(baseline)} records -> {FILE_BASELINE}")
    print(f"  Multiview (L0-L3):  {len(multiview)} records -> {FILE_MULTIVIEW}")

    # Domain coverage
    domains = {}
    tiers = {}
    langs_used = {}
    for atom in ATOMS:
        domains[atom["domain"]] = domains.get(atom["domain"], 0) + 1
        tiers[atom["tier"]] = tiers.get(atom["tier"], 0) + 1
        for l in LANGUAGES:
            if l in atom:
                langs_used[l] = langs_used.get(l, 0) + 1

    print(f"\nAtom coverage:")
    print(f"  Domains: {dict(sorted(domains.items()))}")
    print(f"  Tiers: {dict(sorted(tiers.items()))}")
    print(f"  Languages: {dict(sorted(langs_used.items()))}")

    # Sample a record for verification
    print(f"\n--- Sample Multiview Record ---")
    sample = json.loads(open(FILE_MULTIVIEW).readline())
    print(sample["text"][:800])
    print("...")


if __name__ == "__main__":
    main()
