# Integration Matrix

Use this file only when deciding which companion lane should take over part of the phone workflow.

| Surface | Companion | Use when | Entry point |
|---|---|---|---|
| Emulator boot, repair, density, route truth | `$aether-phone-lane-ops` | The phone must be started, recovered, tuned, or proven live | `phone_lane_status.py`, `start_polly_pad_emulator.ps1`, `stop_polly_pad_emulator.ps1` |
| Secret-backed web or app session | `$scbe-api-key-local-mirror` | A browser or app flow needs a token without plaintext storage | `key_mirror.py doctor/store/resolve/list` |
| Research browsing | `$aetherbrowser-arxiv-nav` | The phone session should move through arXiv pages or capture metadata | `browser_chain_dispatcher.py --domain arxiv.org` |
| Repo or PR browsing | `$aetherbrowser-github-nav` | The phone session should open GitHub surfaces with evidence capture | `browser_chain_dispatcher.py --domain github.com` |
| Workspace discovery | `$aetherbrowser-notion-nav` | The phone session should open or locate Notion pages before API work | `browser_chain_dispatcher.py --domain notion.so` |
| Multi-skill orchestration | `$scbe-universal-synthesis` | The phone is one lane inside a larger coordinated run | `refresh_universal_skill_synthesis.py` |
| Notes and capture | `$obsidian` | The phone session should leave behind a note, link dump, or checklist | `obsidian-cli` |
| Document handling | Adobe Acrobat app tools | A synced or host-accessible document needs PDF creation, export, OCR, or review | Use the Acrobat connector from the host lane |
| Image handling | Adobe Photoshop app tools | A synced or host-accessible image needs masking, effects, or adjustment work | Use the Photoshop connector from the host lane |

## Optional Additions

- Add messaging or storefront skills here only when they have a stable skill body and trigger description.
- Keep this file as a routing sheet, not a second SKILL body.
