# Agent Bus Workspace Formation

The agent bus should feel like a small operating system, not a loose download
button. Customer work gets a temporary local workspace, a visible folder shape,
and a clean offload path to the storage stop the user designates.

This is the product-facing companion to `FOLDER.md` hexa cards. `FOLDER.md`
organizes the repo for builders. The bus workspace formation organizes user
work for operators and customers.

## Shape

```text
.aethermoor-bus/workspaces/<workspace-id>/
  00_inbox/     raw drops, uploads, imports, unclassified files
  10_work/      active editable working files
  20_receipts/  governance verdicts, hashes, signatures, run receipts
  30_exports/   customer-ready packets and handoff bundles
  40_refs/      non-secret reference files and source notes
  90_tmp/       scratch files, deleted after offload verification
```

## Lifecycle

1. Create a workspace ID from timestamp, user hint, and random suffix.
2. Put raw inputs in `00_inbox`.
3. Move active files into `10_work`.
4. Write every governance/result receipt into `20_receipts`.
5. Build user-facing outputs in `30_exports`.
6. Keep safe public references in `40_refs`.
7. Use `90_tmp` for scratch only.
8. Offload `20_receipts`, `30_exports`, and selected `40_refs` to the user's
   transport stop.
9. Verify the offload manifest.
10. Delete or retain the temporary workspace according to the user's request.

## Transport Stops

The zero-server-storage endpoint exposes these stops:

- `local_download` - browser-generated JSON packet download.
- `browser_local` - small local browser records.
- `github` - user-designated repository handoff.
- `dropbox` - user-designated Dropbox handoff.
- `onedrive` - user-designated OneDrive handoff.
- `gdrive` - user-designated Google Drive handoff.

The bus does not need to own customer storage to be useful. It needs to produce
clean packets that the customer can move to storage they already trust.

## Rules

- Classify before offload.
- Never export secrets by default.
- Receipts and manifests travel with customer work.
- Temporary local workspaces are disposable after offload verification.
- External storage is user-designated; the bus does not retain export content.
- If a file is not in `20_receipts`, `30_exports`, or selected `40_refs`, it does
  not ship by default.

## API Surface

`GET /api/agent/storage` returns the current `workspace_formation`.

`POST /api/agent/storage` embeds the same `workspace_formation` in the export
packet so mobile clients, browser clients, and CLI clients all see the same
folder shape.

The schema string is:

```text
aethermoor.bus.workspace_formation.v1
```

## Customer Meaning

For the user, this becomes a one-click organizer:

```text
New bus workspace -> work happens -> receipts generated -> export packet -> chosen storage stop
```

For SCBE, it gives every agent a shared map. No more guessing whether a file is
scratch, evidence, customer output, or reference material.
