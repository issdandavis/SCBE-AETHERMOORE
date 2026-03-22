# AetherBrowser Search Mesh Spec

## Purpose

The browser-first search mesh is a lightweight composition of existing SCBE browser scripts. It should be treated as an execution pattern, not as a separate service.

Primary implementation surfaces:

- `scripts/system/browser_chain_dispatcher.py`
- `scripts/system/aetherbrowser_arxiv_nav.py`
- `scripts/system/aetherbrowser_github_nav.py`
- `scripts/system/aetherbrowser_notion_nav.py`
- `scripts/system/playwriter_lane_runner.py`
- `scripts/system/crosstalk_relay.py`

## Composition

### 1. Dispatcher selects the lane

`browser_chain_dispatcher.py` is the front door. It maps `--domain`, `--task`, and optional payload into a tentacle assignment.

Current built-in domain routing:

- `arxiv.org` -> `tentacle-arxiv-um`
- `github.com` -> `tentacle-github-ko`
- `notion.so` / `www.notion.so` -> `tentacle-notion-av`

The dispatcher returns metadata only:

- `tentacle_id`
- `execution_engine`
- `task_type`
- `payload`

It does not execute the browser task itself. The mesh should treat the dispatcher as a routing decision layer.

### 2. Site-specific nav script executes the search

After routing, the orchestrator should invoke the matching site adapter:

- `aetherbrowser_arxiv_nav.py` for arXiv search
- `aetherbrowser_github_nav.py` for GitHub search
- `aetherbrowser_notion_nav.py` for Notion search

Each script is domain-aware and returns structured search results. Current behavior is implementation-specific:

- arXiv prefers Playwright, then falls back to the arXiv API
- GitHub prefers Playwright, then falls back to the GitHub REST API
- Notion prefers the Notion API, with Playwright only as an optional visual fallback

This means the search mesh is browser-first, not browser-only. The nav layer should prefer live page navigation when available, but it may degrade to API search without breaking the mesh.

### 3. Playwriter captures page evidence

`playwriter_lane_runner.py` is the evidence spine for the mesh.

Supported tasks:

- `navigate`
- `title`
- `snapshot`

The lane runner stores:

- session state in `artifacts/page_evidence/playwriter-session-<session>.json`
- evidence artifacts in `artifacts/page_evidence/playwriter-<host>-<task>-session<session>.json`

Operational rule:

- use the site-specific nav script to get candidate results or route-specific extraction
- use `playwriter_lane_runner.py` to capture proof for the selected URL or current page state

The search mesh should treat Playwriter evidence as the canonical proof artifact for a browser run, especially when a later agent must verify what page was actually reached.

### 4. Crosstalk moves proof between agents

`crosstalk_relay.py` is the transport layer for mesh handoff.

Once a search step has produced usable results and evidence, emit a packet with:

- the search task id
- a short summary of what was found
- proof paths pointing to the relevant `artifacts/page_evidence/*` file and any derived notes
- the next browser or synthesis action

The relay writes to:

- dated JSON packets under `artifacts/agent_comm/<YYYYMMDD>/`
- the append-only JSONL bus at `artifacts/agent_comm/github_lanes/cross_talk.jsonl`
- the Obsidian mirror when available

Use `verify`, `ack`, and `pending` when the search mesh needs explicit delivery confirmation across agents.

## Recommended Flow

1. Route the domain and task with `browser_chain_dispatcher.py`.
2. Run the matching `aetherbrowser_*_nav.py` script to collect search results.
3. Pick the best target URL from the result set.
4. Run `playwriter_lane_runner.py --task navigate`, then `title` or `snapshot`, to create reproducible page evidence.
5. Emit a cross-talk packet with summary, proof, and next action.

## Current Boundaries

This composition is grounded in the scripts as they exist now:

- the dispatcher does not automatically launch the nav scripts
- the nav scripts do not automatically call Playwriter evidence capture
- Playwriter does not automatically emit cross-talk packets
- crosstalk does not update a browser scoreboard by itself

So the search mesh is a coordinated chain of scripts with stable artifact handoff points, not a single integrated runtime.

## Minimal Contract

For a browser-first search run to count as mesh-complete, it should produce:

- one dispatcher assignment
- one domain-specific search result set
- one Playwriter evidence artifact
- one crosstalk packet carrying proof and next action

That is the concrete AetherBrowser search mesh available in the repository today.
