# Obsidian Trace Promotion Loop

Use this when outside-house work is still auxiliary and Obsidian is the local truth surface.

The loop is:

1. Throw raw ideas, chats, and external traces into the vault.
2. Extract them into low-trust trace records.
3. Review them inside Obsidian.
4. Mark only the good ones for promotion.
5. Build verified route-consistency records for training.

## What counts as intake

By default the promotion script pulls from the note surfaces you already use:

- `notes/_inbox.md`
- `notes/GROk*.md`
- `notes/RAW DUMPS*.md`
- `notes/Messges Dumps_trainging files/**/*.md`
- `notes/sessions/**/*.md`
- `notes/round-table/**/*.md`

You can also point it at a specific file or folder.

## Step 1: Discover what will be scanned

```powershell
python .\scripts\obsidian_local_promotion.py discover
```

If you only want one folder or file:

```powershell
python .\scripts\obsidian_local_promotion.py discover --input "notes\Messges Dumps_trainging files"
python .\scripts\obsidian_local_promotion.py discover --input "notes\GROk drop 2.103.md"
```

## Step 2: Extract low-trust traces and build the review queue

```powershell
python .\scripts\obsidian_local_promotion.py extract
```

This writes:

- low-trust trace records to `training-data/model_traces/obsidian/obsidian_model_trace_records.jsonl`
- a review note to `notes/agent-memory/obsidian-trace-review-queue.md`
- a machine-readable decisions template to `notes/agent-memory/obsidian-trace-decisions.jsonl`

If the decisions file already exists, the script leaves it alone unless you force a refresh:

```powershell
python .\scripts\obsidian_local_promotion.py extract --overwrite-decisions
```

## Step 3: Review inside Obsidian

Open:

- `notes/agent-memory/obsidian-trace-review-queue.md`
- `notes/agent-memory/obsidian-trace-decisions.jsonl`

Keep the queue note as the human reading surface.
Keep the JSONL file as the machine gate.

Each line in the decisions file looks like this:

```json
{"trace_id":"trace_1234abcd","decision":"hold","notes":"","language_override":"","tongue_override":"","layer_override":""}
```

Valid `decision` values:

- `promote`
- `hold`
- `skip`

Only `promote` moves forward into training outputs.

## Step 4: Promote verified traces

```powershell
python .\scripts\obsidian_local_promotion.py promote
```

This writes:

- verified traces to `training-data/model_traces/obsidian/obsidian_verified_model_trace_records.jsonl`
- a route-builder seed corpus to `training-data/model_traces/obsidian/obsidian_verified_route_seed.jsonl`
- verified route-consistency records to `training-data/route_consistency/obsidian_verified_route_records.jsonl`
- a manifest to `training-data/route_consistency/obsidian_verified_manifest.json`

## Operating rule

Treat vault notes as meaning in motion.
Treat extracted traces as low-trust structure.
Treat promoted records as locally verified training material.

That keeps the separation clean:

- Obsidian = evolving thought
- extracted traces = auxiliary route material
- promoted records = curated training substrate
