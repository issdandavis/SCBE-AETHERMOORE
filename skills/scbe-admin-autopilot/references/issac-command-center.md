# Issac Command Center

Use this reference when `scbe-admin-autopilot` needs exact command names from the local PowerShell operator surface.

## Health And Core Control

- `issac-help`: print the command-center menu
- `hstatus`: HYDRA status as JSON
- `hinteractive`: interactive HYDRA session
- `hqueue`: switchboard queue stats
- `hdoctor`: local command-center smoke test

## Research And Swarm

- `hresearch <q>`: quick research
- `hdeep <q>`: deeper multi-provider research
- `hswarm <task>`: 6-agent Sacred Tongue swarm

## arXiv

- `harxiv <q>`: search `cs.AI`
- `harxiv-ml <q>`: search `cs.LG`
- `harxiv-get <id>`: fetch paper by ID
- `harxiv-outline <q>`: produce an outline from matching papers

## Canvas, Branch, Workflow, Lattice

- `hcanvas`: list recipes
- `hcanvas-run <recipe> [topic]`: run a canvas recipe
- `hpaint <topic>`: freeform article pipeline
- `hbranch`: list branch graphs
- `hbranch-run <graph> [topic]`: run a branch graph
- `hwf`: list workflows
- `hwf-run <name>`: run a workflow
- `hwf-show <name>`: show a workflow
- `hlattice [n]`: sample lattice nodes
- `hlattice-notes`: ingest docs or notes to the lattice

## Skill Vault And Cascades

- `hskills-refresh`: refresh repo-local skill synthesis artifacts
- `hskills`: show the current synthesis summary
- `hstack <task>`: compose a skill stack from a task prompt
- `hcascade <topic>`: skill refresh -> research -> arXiv -> branch -> canvas -> lattice -> cross-talk
- `harticle <topic>`: deep research -> arXiv -> article canvas
- `hmission <topic>`: skill stack -> deep research -> branch -> canvas
- `htunnel`: start the HYDRA terminal tunnel stack

## Memory

- `hremember <key> <value>`: store a fact
- `hrecall <key>`: retrieve a fact
- `hsearch <q>`: semantic search

## Services And Cross-Talk

- `scbe-bridge`: start the n8n browser bridge on `:8001`
- `scbe-api`: start the SCBE API on `:8000`
- `octo-serve`: start the OctoArmor gateway on `:8400`
- `xtalk-send <to> <msg>`: emit a cross-talk packet
- `xtalk-ack <id>`: acknowledge a packet
- `xtalk-pending [agent]`: show pending packets
- `xtalk-health`: show cross-talk health

## Navigation

- `go-scbe`
- `go-hydra`
- `go-agents`
- `go-train`
- `go-armor`
- `go-docs`
- `go-api`
- `go-workflows`
- `go-browser`
- `go-scripts`
