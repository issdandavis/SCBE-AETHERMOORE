# AetherBrowser Mobile — Integration Packet

**For**: Codex V1 spec integration
**From**: Claude session 2026-03-26/27
**Status**: Ready for wiring

---

## 1. Apollo Data Pipeline (Email + Content Triage)

### What Exists
- `scripts/apollo/email_reader.py` — reads ProtonMail + Gmail, classifies by tongue
- `scripts/apollo/apollo_core.py` — search, teach, collect, scrub secrets
- `scripts/apollo/youtube_transcript_collector.py` — pulls transcripts from 18 curated channels
- `scripts/apollo/video_review.py` — scores video quality (title, desc, transcript, tags)
- `scripts/apollo/tor_sweeper.py` — dark web research crawler
- `scripts/apollo/field_trip.py` — multi-hop clearnet/Tor routing
- `scripts/apollo/obsidian_vault_sync.py` — vault graph builder + SFT export

### Mobile Integration Hooks
```
Browse tab → Apollo can classify any page by tongue activation
Chat tab → Apollo search ("find emails about X") works via apollo_core.py search
Vault tab → Obsidian vault sync provides the knowledge graph
Ops tab → Email check, YouTube review, Tor sweep all callable as commands
```

### API Surface Needed
```python
# These functions are ready to call from a mobile backend:
apollo_core.search_emails(query, days, accounts)  # returns results
apollo_core.collect_training_context(days)         # scrub + SFT
email_reader.read_account(host, port, user, pass)  # returns classified digests
video_review.review_video(video_data, transcript)  # returns scores
```

### Credentials
All in `config/connector_oauth/.env.connector.oauth`:
- `PROTONMAIL_BRIDGE_PASSWORD` / `PROTONMAIL_USER`
- `GMAIL_APP_PASSWORD` / `GMAIL_USER`
- `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET`
- `HF_TOKEN`, `GEMINI_API_KEY`, `BLUESKY_HANDLE`

ProtonMail Bridge must be running locally (127.0.0.1:1143). For mobile, need a relay or direct IMAP from device.

---

## 2. Security Stack

### Code Governance Gate
- `scripts/security/code_governance_gate.py`
- 16 injection patterns, owner vs outsider trust
- Decisions: PASS / WARN / BLOCK

### Mobile Integration
```
Every action in the app passes through governance gate:
- Browse: URL checked against trusted_external_sites.json
- Chat: responses checked for injection patterns
- Rooms: red-team prompts scored by adversarial harness
- Ops: git operations checked by code_governance_gate
```

### Trusted Sites Registry
- `config/security/trusted_external_sites.json` — 150+ domains, 8 tiers
- `config/security/trusted_onion_sites.json` — 17 verified .onion sites
- Mobile browser should color-code URLs by trust tier:
  - CORE (green): .gov, .edu, our domains
  - TRUSTED (blue): GitHub, HuggingFace, Stripe
  - PROVISIONAL (yellow): social media, publishing
  - UNKNOWN (grey): not in registry
  - BLOCKED (red): known malicious

### Runtime Gate
- `src/governance/runtime_gate.py` — 46 tests passing
- Fibonacci BFT trust: session builds trust over time
- Null-space detection: catches adversarial patterns by absence
- Mobile app should show trust level badge: UNTRUSTED → PROVISIONAL → TRUSTED → CORE

---

## 3. Training Loop

### How the App Generates Training Data
Every user action can become an SFT pair:
```
Browse: page visit → tongue classification → SFT pair
Chat: question + response → quality-scored → SFT pair
Rooms: red-team prompt + result → adversarial SFT pair
Vault: note created → linked to graph → vault SFT pair
Ops: command + result → operational SFT pair
```

### Current Training Data (from today's session)
| Dataset | Pairs | Location |
|---------|-------|----------|
| Email triage | 100 | training-data/apollo/ |
| Obsidian vault | 161 | training-data/apollo/ |
| Copilot replacement | 25 | training-data/sft/ |
| Security deep | 20 | training-data/sft/ |
| Phi-poincare | 15 | training-data/sft/ |
| Null-space confidence | 12+6 DPO | training-data/sft/ |
| Tor sweep | 12 | training-data/apollo/tor_sweeps/ |
| YouTube transcripts | 13 | training-data/sft/ |
| Own channel | 9 | training-data/sft/ |
| Tax bot | 12 | training-data/sft/ |
| Field trip | 4 | training-data/apollo/field_trips/ |
| **Total new** | **389** | |

### HuggingFace Push
```python
from huggingface_hub import HfApi
api = HfApi(token=os.environ['HF_TOKEN'])
api.upload_file(path, path_in_repo, repo_id='issdandavis/scbe-aethermoore-training-data', repo_type='dataset')
```

### Training Plan (6 Specialist Models)
| Specialist | Tongue | Base Model |
|-----------|--------|------------|
| Intent/Control | KO | Qwen 0.5B |
| Context/Metadata | AV | Qwen 0.5B |
| Binding/Witness | RU | Qwen 0.5B |
| Compute/Crypto | CA | Qwen 0.5B |
| Security/Redaction | UM | Qwen 0.5B |
| Structure/Schema | DR | Qwen 0.5B |

Arena: 4/6 BFT consensus for chat responses.

---

## 4. Release Constraints

### Stable vs Canary
```
Stable channel:
- Tagged releases only
- All 172+ tests must pass
- Code governance gate: PASS required
- No experimental features

Canary channel:
- Branch builds (fix/eslint-unused-vars-bulk or feature branches)
- Tests should pass but experimental features allowed
- Governance gate: WARN acceptable
- New Apollo features, Tor sweeper, etc.
```

### Packaging Paths
| Platform | Method | Existing |
|----------|--------|----------|
| Android | Capacitor/Cordova from kindle-app | APK exists (debug) |
| Web | Vite build → Vercel/GitHub Pages | docs site exists |
| Desktop | Electron wrapper (future) | Not started |

### Signing & Distribution
- Android: debug APK at `kindle-app/android/app/build/outputs/apk/debug/`
- Android SDK: `C:\Users\issda\android-sdk` (platform-35, build-tools-35)
- JDK: `C:\Users\issda\jdk-21\jdk-21.0.10`
- Google Play: needs $25 developer account
- Amazon Appstore: pending submission

### Owner Identity
- Only issdandavis can push to stable
- Code governance gate enforces: owner = CORE trust, outsiders = BLOCK on critical
- All commits signed with `Co-Authored-By` for audit trail

---

## 5. Existing App Surfaces

### kindle-app/
- PWA: manifest.json, sw.js, BYOK settings panel
- Chat interface: `kindle-app/www/chat.html`
- Polly chat: `kindle-app/www/static/polly-hf-chat.js`
- Android build pipeline working

### conference-app/
- Vite + React + TypeScript
- SCBE governance gate integrated
- `conference-app/vercel.json` for deployment

### Omni-Heal- (separate repo)
- AI Studio React/Vite shell
- UI scaffolding for rooms/chat

---

## 6. Backend Connectors Available

| Connector | Status | Auth |
|-----------|--------|------|
| GitHub API | Working | PAT via gh auth |
| HuggingFace | Working | HF_TOKEN |
| YouTube Data API | Working | OAuth (token refreshed) |
| ProtonMail | Working | Bridge IMAP |
| Gmail | Working | App password |
| Stripe | Working | rk_live key |
| Bluesky | Working | App password |
| Shopify | Working | shpat token |
| Gemini | Working | API key |
| Tor SOCKS5 | Working | 127.0.0.1:9050 |

---

## 7. Skills Available for Mobile Commands

The `.claude/skills/` directory has 50+ skills that map to mobile commands:
- `scbe-email-checker` → "check email" command
- `scbe-copilot` → "review code" command
- `scbe-revenue-autopilot` → "revenue check" command
- `scbe-article-posting` → "post article" command
- `scbe-training-pipeline` → "train model" command
- `scbe-youtube-factory` → "make video" command

Each skill is a self-contained workflow that can be triggered from a mobile button.

---

## 8. Tests That Must Pass Before Release

| Suite | Tests | What It Covers |
|-------|-------|---------------|
| Runtime gate + Fibonacci | 46 | Governance decisions |
| Phi-poincare + edge cases | 35 | Math primitives |
| Biblical null-space | 9 | Probe validation |
| Adversarial benchmark | 12 | Attack detection |
| Flow router | 12 | Workflow routing |
| Hard-negative benign | 11 | False positive rate |
| Golden vectors | 48 | Cross-language parity |
| YouTube collector | 13 | Transcript pipeline |
| Scbe vs industry | 3 | Benchmark |
| **Total** | **189** | |

Run: `python -m pytest tests/ -v --tb=short -q`
