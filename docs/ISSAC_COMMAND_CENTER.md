# Issac Command Center

`ISSAC'S COMMAND CENTER` is the richer PowerShell layer on top of the local HYDRA CLI, browser service scripts, cross-talk relay, and skill-vault synthesis helpers.

For copy-paste beginner instructions, read [ISSAC_QUICKSTART.md](/C:/Users/issda/SCBE-AETHERMOORE/docs/ISSAC_QUICKSTART.md).

For the current multi-system local guide index, read [FAST_ACCESS_GUIDE.md](/C:/Users/issda/SCBE-AETHERMOORE/docs/FAST_ACCESS_GUIDE.md).

## Install

From repo root:

```powershell
.\scripts\install_hydra_quick_aliases.ps1
```

This now installs a profile block that dot-sources [`scripts/hydra_command_center.ps1`](/C:/Users/issda/SCBE-AETHERMOORE/scripts/hydra_command_center.ps1).

## Core Commands

```powershell
issac-help
hstatus
hresearch "topic"
hdeep "topic"
hqueue
harxiv "topic"
harxiv-ml "topic"
harxiv-get 2501.00001v1
harxiv-outline "topic"
hcanvas
hcanvas-run article "topic"
hpaint "topic"
hbranch
hbranch-run research_pipeline "topic"
hswarm "task"
hremember key value
hrecall key
hsearch "query"
hwf
hwf-run name
hwf-show name
hlattice 12
hlattice-notes
```

## Skill Vault Commands

These commands are wired to the installed Codex skill vault, but keep outputs repo-local.

```powershell
hskills-refresh
hskills
hstack "browser research pipeline"
```

- `hskills-refresh` runs [`scripts/system/refresh_universal_skill_synthesis.py`](/C:/Users/issda/SCBE-AETHERMOORE/scripts/system/refresh_universal_skill_synthesis.py) and writes artifacts under `artifacts/skill_synthesis/`.
- `hstack` runs the external skill-stack composer from `C:\Users\issda\.codex\skills\skill-synthesis\scripts\compose_skill_stack.py`.

## Cascade Commands

These are the “lightning reaction” helpers where one command fans out into multiple subsystems.

```powershell
hcascade "topic"
harticle "topic"
hmission "topic"
hcascade -DryRun "topic"
```

- `hcascade`: skill refresh -> HYDRA deep research -> arXiv outline -> branch pipeline -> canvas recipe -> lattice checkpoint -> cross-talk packet
- `harticle`: deep research -> arXiv scan -> article canvas
- `hmission`: skill stack -> deep research -> training branch -> content canvas

## Services And Cross-Talk

```powershell
scbe-bridge
scbe-api
octo-serve
xtalk-send claude "message"
xtalk-ack <packet_id>
xtalk-pending
xtalk-health
htunnel
```

## Navigation

```powershell
go-scbe
go-hydra
go-agents
go-train
go-armor
go-docs
go-api
go-workflows
go-browser
go-scripts
```
