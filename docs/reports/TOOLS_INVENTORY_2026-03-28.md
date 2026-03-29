# SCBE-AETHERMOORE Tools Inventory
## Complete System Surface Map
### Date: 2026-03-28

---

## Section 1: Built and Working

### Scripts (scripts/) -- 149+ files

#### Core System (scripts/system/)
| Script | Description |
|--------|-------------|
| `dual_sync.py` | GitHub-GitLab bidirectional mirror sync |
| `crosstalk_relay.py` | Cross-agent communication (Claude/Codex/Gemini handoffs) |
| `sitrep.py` | Generate situation report from cross-talk + git log |
| `ops_control.py` | Multi-agent operations controller |
| `ai_bridge.py` | AI model bridge (local/remote routing) |
| `ai_bridge_streamlit.py` | Streamlit UI for AI bridge |
| `terminal_ai_router.py` | Terminal-based AI model router |
| `sell_from_terminal.py` | Terminal-based sales automation |
| `daily_revenue_check.py` | Daily Stripe/Shopify revenue check |
| `daily_patent_check.py` | USPTO patent status monitor |
| `proton_mail_ops.py` | ProtonMail operations (check/send) |
| `onion_site.py` | .onion hidden service manager |
| `goal_race_loop.py` | Goal tracking and progress racing |
| `helix_merge.py` | Helix merge strategy tool |
| `storage_benchmark.py` | Storage system benchmarking |
| `storage_bridge_lab.py` | Storage bridge experiments |
| `storage_compaction_lab.py` | Storage compaction testing |
| `system_card_deck.py` | System status card generator |
| `system_hub_sync.py` | AI Evolution Hub sync |
| `pr_merge_triage.py` | PR merge triage automation |
| `repo_ordering.py` | Repository ordering/organization |
| `run_core_python_checks.py` | Python health checks |
| `github_workflow_audit.py` | Audit GitHub Actions workflows |
| `inventory_notes_for_github.py` | Generate inventory notes |
| `nightly_research_pipeline.py` | Nightly research automation |
| `research_training_bridge.py` | Research-to-training pipeline |
| `colab_bridge.py` | Google Colab bridge |
| `colab_notebook_smoke.py` | Colab notebook smoke tests |
| `colab_worker_lease.py` | Colab worker lease manager |
| `colab_workflow_catalog.py` | Colab workflow catalog |
| `momentum_train.py` | Momentum training pipeline |
| `chessboard_dev_stack.py` | Dev task chessboard manager |
| `website_sales_train.py` | Website sales funnel training |
| `secret_lane.ps1` | Secret management lane |

#### Publishing (scripts/publish/)
| Script | Description |
|--------|-------------|
| `post_to_x.py` | Post to X/Twitter (OAuth 2.0 PKCE) |
| `post_to_youtube.py` | Upload videos to YouTube (OAuth 2.0) |
| `post_to_devto.py` | Publish to Dev.to |
| `post_to_medium.py` | Publish to Medium |
| `post_to_bluesky.py` | Post to Bluesky |
| `post_to_buffer.py` | Schedule via Buffer |
| `post_to_huggingface_discussion.py` | Post HuggingFace discussions |
| `post_all.py` | Publish to all platforms at once |
| `publish_discussions.py` | GitHub Discussions publisher |
| `article_to_video.py` | Article to TTS video pipeline |
| `rebuild_and_stage_kdp.py` | KDP manuscript rebuild |
| `kdp_auto_upload.py` | Automated KDP upload |
| `build_research_campaign.py` | Research campaign builder |
| `generate_daily_system_update.py` | Daily system update generator |
| `roundtable_review.py` | Content roundtable review |

#### Training & ML (scripts/)
| Script | Description |
|--------|-------------|
| `codebase_to_sft.py` | Convert codebase modules to SFT pairs |
| `hf_training_loop.py` | HuggingFace training loop runner |
| `convert_to_sft.py` | Generic SFT converter |
| `merge_training_data.py` | Merge multiple training datasets |
| `push_to_hf.py` | Push datasets to HuggingFace |
| `push_jsonl_dataset.py` | Push JSONL to HuggingFace |
| `validate_training_data.py` | Validate training data quality |
| `training_auditor.py` | Audit training data integrity |
| `generate_sft_from_modules.py` | Generate SFT from source modules |
| `daily_training_wave.py` | Daily training data generation wave |
| `symphonic_training.py` | Symphonic cipher training pipeline |
| `spiralverse_to_sft.py` | Spiralverse lore to SFT |
| `mega_ingest.py` | Mega-scale data ingestion |
| `train_projector.py` | Train semantic projector weights |
| `web_research_training_pipeline.py` | Web research to training pipeline |
| `build_training_ingestion_pool.py` | Training ingestion pool builder |
| `tetris_training_pipeline.py` | Tetris-style stacked training |

#### Benchmarks & Evaluation (scripts/benchmark/, scripts/eval/)
| Script | Description |
|--------|-------------|
| `scbe_vs_industry.py` | Benchmark SCBE vs industry tools |
| `scbe_vs_baseline.py` | Benchmark SCBE vs baselines |
| `context_embedding_benchmark.py` | Context embedding benchmarks |
| `spectral_sweep_benchmark.py` | Spectral analysis benchmarks |
| `null_space_ablation.py` | Null-space ablation study |
| `tongue_weight_field_tuner.py` | Sacred Tongue weight tuning |
| `hyperbolic_helix_test.py` | Hyperbolic helix testing |
| `unified_triangulation.py` | Unified triangulation benchmark |

#### AetherBrowser (scripts/aetherbrowser/)
| Script | Description |
|--------|-------------|
| `aetherbrowse_swarm_runner.py` | Browser swarm coordinator |
| `launch_aetherbrowser.py` | Launch AetherBrowser service |
| `headless_browser.py` | Headless browser operations |
| `n8n_aetherbrowse_bridge.py` | n8n-AetherBrowse bridge |

#### Security (scripts/security/)
| Script | Description |
|--------|-------------|
| `code_governance_gate.py` | Code governance gate checker |
| (sacred_vault.py in separate location) | Sacred Vault v3 secrets management |

#### Social (scripts/social/)
| Script | Description |
|--------|-------------|
| `run_x_monetize_pack.ps1` | X/Twitter monetization pack runner |

#### Revenue (scripts/revenue/)
| Script | Description |
|--------|-------------|
| `daily_autopilot.py` | Daily revenue autopilot |

#### Outreach (scripts/outreach/)
| Script | Description |
|--------|-------------|
| `cold_outreach_pipeline.py` | Cold outreach email pipeline |

#### GitLab (scripts/gitlab/)
| Script | Description |
|--------|-------------|
| `mirror_push.ps1` | Mirror push to GitLab |
| `pond_flush.ps1` | GitLab pond flush |
| `smoke_test.ps1` | GitLab smoke test |

#### Git Hooks (scripts/git-hooks/)
| Script | Description |
|--------|-------------|
| `post-push-gitlab.sh` | Auto-mirror pushes to GitLab after GitHub push |

---

### Claude Code Skills (.claude/skills/) -- 29 skills

| Skill | Purpose |
|-------|---------|
| `latticegate-orchestrator` | AI safety governance with 21D hyperbolic embeddings |
| `scbe-9d-state-engine` | 9-dimensional governance state vector |
| `scbe-art-generator` | Character/scene art generation (Imagen 4.0 + HF) |
| `scbe-article-posting` | Multi-platform article publishing (12+ platforms) |
| `scbe-audio-intent` | Phase-modulated audio intent encoding |
| `scbe-browser-swarm-ops` | Multi-agent browser coordination |
| `scbe-copilot` | Code review, CI fix, research-backed repairs |
| `scbe-crosstalk-workflow` | Claude-Codex cross-talk protocol |
| `scbe-disk-management` | Disk audit and cleanup |
| `scbe-doc-maker` | Document builder with citations |
| `scbe-email-checker` | ProtonMail/Gmail checker |
| `scbe-entropy-dynamics` | Entropy/time/quantum dynamics |
| `scbe-fleet-deploy` | Model fleet deployment |
| `scbe-flock-shepherd` | Multi-agent flock orchestration |
| `scbe-gate-swap` | 2-gate/3-gate encoding analysis |
| `scbe-governance-gate` | Grand Unified Governance function |
| `scbe-ide` | IDE integration |
| `scbe-longform-work` | Checkpointed long-running tasks |
| `scbe-manifold-validate` | 9D manifold geometric validation |
| `scbe-mobile-connector-orchestrator` | Mobile goal control plane |
| `scbe-ops-control` | Multi-agent operations |
| `scbe-personal-rag` | Fast-recall knowledge base |
| `scbe-product-docs-autolog` | Auto-log product documentation |
| `scbe-revenue-autopilot` | Revenue automation |
| `scbe-shopify-cli-windows` | Shopify CLI operations |
| `scbe-sitrep` | Situation report generator |
| `scbe-story-canon-writer` | Canon-aligned story writer |
| `scbe-training-pipeline` | SFT training data pipeline |
| `scbe-web-research-verified` | Verified web research with confidence scoring |

---

### Standalone Skills (skills/) -- 17 entries

| Skill | Purpose |
|-------|---------|
| `scbe-admin-autopilot` | Admin task automation |
| `scbe-autonomous-worker-productizer` | Autonomous worker productization |
| `scbe-browser-sidepanel-ops` | Browser side panel operations |
| `scbe-claim-to-code-evidence` | Claim-to-code evidence building |
| `scbe-codebase-orienter` | Codebase orientation/navigation |
| `scbe-colab-bridge` | Google Colab bridge |
| `scbe-colab-training-ops` | Colab training operations |
| `scbe-government-contract-intelligence` | Government contract intelligence |
| `scbe-kernel-external-toolcall-specialist` | Kernel external tool calls |
| `scbe-playwright-ops-extension` | Playwright operations extension |
| `scbe-research-training-bridge` | Research-to-training bridge |
| `scbe-spin-conversation-engine` | Conversation spin engine |
| `scbe-spiralverse-intent-auth` | Spiralverse intent auth |
| `long-form-work-orchestrator` | Long-form work orchestration |
| `multi-agent-cloud-offload` | Multi-agent cloud offload |
| `codex-mirror` | Codex skill mirroring |

---

### GitHub Actions Workflows (.github/workflows/) -- 67 files

#### Core CI/CD
| Workflow | Purpose |
|----------|---------|
| `ci.yml` | Main CI pipeline (build, test, lint) |
| `scbe.yml` | SCBE-specific test suite |
| `scbe-gates.yml` | SCBE gate checks |
| `scbe-tests.yml` | SCBE test runner |
| `scbe-reusable-gates.yml` | Reusable gate workflows |

#### Publishing & Release
| Workflow | Purpose |
|----------|---------|
| `npm-publish.yml` | npm publishing |
| `auto-publish.yml` | Auto-publish on merge |
| `release-and-deploy.yml` | Release + deploy |
| `release.yml` | Release management |
| `docker-publish.yml` | Docker image publishing |

#### Security
| Workflow | Purpose |
|----------|---------|
| `security-checks.yml` | Security scanning |
| `weekly-security-audit.yml` | Weekly security audit |
| `codeql-analysis.yml` | CodeQL analysis |
| `codeql.yml` | CodeQL scanning |
| `frogbot-scan-and-fix.yml` | JFrog Frogbot scanning |
| `conflict-marker-guard.yml` | Merge conflict detection |

#### Deployment
| Workflow | Purpose |
|----------|---------|
| `deploy-aws.yml` | AWS deployment |
| `deploy-cloudrun.yml` | Cloud Run deployment |
| `deploy-eks.yml` | EKS deployment |
| `deploy-gke.yml` | GKE deployment |
| `pages-deploy.yml` | GitHub Pages |

#### Automation
| Workflow | Purpose |
|----------|---------|
| `auto-merge.yml` | Auto-merge PRs |
| `auto-merge-enable.yml` | Enable auto-merge |
| `auto-changelog.yml` | Changelog generation |
| `auto-triage.yml` | Issue triage |
| `auto-resolve-conflicts.yml` | Conflict resolution |
| `auto-approve-trusted.yml` | Approve trusted PRs |
| `auto-rebase-prs.yml` | Auto-rebase PRs |
| `ci-auto-fix.yml` | CI auto-fix |

#### Daily/Nightly
| Workflow | Purpose |
|----------|---------|
| `daily-review.yml` | Daily code review |
| `daily_ops.yml` | Daily operations |
| `daily-social-updates.yml` | Daily social media updates |
| `nightly-connector-health.yml` | Nightly connector health check |
| `nightly-multicloud-training.yml` | Nightly multi-cloud training |
| `nightly-ops.yml` | Nightly operations |
| `overnight-pipeline.yml` | Overnight pipeline |
| `overnight-runner.yml` | Overnight runner |
| `scheduled-maintenance.yml` | Scheduled maintenance |
| `cli-nightly-ops.yml` | CLI nightly ops |

#### Integration
| Workflow | Purpose |
|----------|---------|
| `huggingface-sync.yml` | HuggingFace model sync |
| `notion-sync.yml` | Notion sync |
| `notion-to-dataset.yml` | Notion to dataset |
| `cloud-kernel-data-pipeline.yml` | Cloud data pipeline |
| `vertex-training.yml` | Vertex AI training |
| `programmatic-hf-training.yml` | Programmatic HF training |
| `cross-repo-sync.yml` | Cross-repo sync |
| `publish-content.yml` | Content publishing |
| `kindle-build.yml` | Kindle book build |

---

### API Endpoints

#### FastAPI Python Server (src/api/main.py)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/v1/governance/scan` | POST | Governance scanning |
| `/v1/tongue/encode` | POST | Sacred Tongue encoding |
| `/v1/agent/task` | POST | Agent task dispatch |
| `/v1/training/ingest` | POST | Training data ingestion |
| `/v1/vertex/push-to-hf` | POST | Vertex to HuggingFace |

#### Express Gateway (src/gateway/)
| Route | Purpose |
|-------|---------|
| Unified SCBE API Gateway | Routes to all sub-services |

#### AetherBrowser API (src/aetherbrowser/)
| Endpoint | Purpose |
|----------|---------|
| 13 endpoints | Browser service, navigation, search, governance |

#### SaaS Routes (src/api/saas_routes.py)
| Route | Purpose |
|-------|---------|
| Billing routes | Stripe integration |

---

### Demos (demos/)
| Demo | Purpose |
|------|---------|
| `demo-cli.py` | CLI demo |
| `demo.py` | Basic demo |
| `demo_complete_system.py` | Complete system demo |
| `demo_full_system.py` | Full system demo |
| `demo_memory_shard.py` | Memory shard demo |
| `demo_product_showcase.py` | Product showcase |
| `demo_spiralverse_complete.py` | Spiralverse complete demo |
| `demo_spiralverse_story.py` | Spiralverse story demo |
| `run_demo.py` | Demo runner |
| `run_dual_lattice_demo.py` | Dual lattice demo |
| `run_spiralverse_demos.py` | Spiralverse demo runner |
| `scbe_demo.py` | SCBE demo |

---

### MCP Servers (Live)
| Server | Purpose |
|--------|---------|
| `scbe-orchestrator` | Sacred Tongues, GeoSeal, Eggs, Cubes, HYDRA, Training |
| `youtube-studio` | YouTube Data API + Analytics |
| `notion-sweep` | Notion workspace search/analysis |
| `claude-in-chrome` | Browser automation |
| `fs` | File system operations |
| `github` | GitHub API operations |
| `playwright` | Browser testing/automation |

---

### Training Data (training-data/) -- 61 entries
- 26 subdirectories (sft/, hf/, art-style-lora/, browser/, dm_sessions/, etc.)
- 15+ JSONL datasets (mega_ingest, tetris_enriched, sft_codebase, sft_governance, etc.)
- Schemas, metadata, datasheets

---

## Section 2: Built but Needs Testing/Polish

### Needs End-to-End Validation
| Item | Status | Issue |
|------|--------|-------|
| Gumroad product upload pipeline | Script exists (`remote_gumroad_upload.py`) | Untested with real products |
| DARPA CLARA proposal | Drafted | Needs review, formatting, submission |
| KDP book v2 manuscript | Edited | Needs reformatting for KDP specs |
| Android APK | Built (`app-debug.apk`) | Not submitted to any app store |
| Firebase hosting | `public/` dir ready | Needs `firebase deploy --only hosting` |
| Cold outreach pipeline | Script exists | Untested with real recipients |
| arXiv paper submission | Script exists (`arxiv_submit_playwright.py`) | Needs endorsement |
| Medium/Reddit/LessWrong publishers | Scripts built | Need account tokens / API access |

### Works Locally, Not in CI
| Item | Status | Issue |
|------|--------|-------|
| Sacred Vault v3 | Works locally | No CI test coverage |
| Colab training pipeline | Works via browser | No automated CI path |
| YouTube upload pipeline | Works with tokens | OAuth tokens expire every 7 days |
| Shopify store operations | Works via API | No CI smoke tests |
| Browser swarm (HYDRA) | Works locally | Requires browser, can't run in CI |

### Works in CI, Not for Users
| Item | Status | Issue |
|------|--------|-------|
| npm package install | CI passes | Onboarding docs are thin |
| PyPI package install | CI passes | No quickstart guide |
| API server | CI health check passes | No hosted instance for users to try |
| Demo scripts | Run locally | No hosted/web version |

---

## Section 3: Needed but Not Built

### What Successful Startups Have That We Don't

| Tool/Feature | Why It Matters | Priority |
|--------------|----------------|----------|
| **Interactive web demo** ("try it now") | Lakera's Gandalf drove viral growth. SCBE has no equivalent. | CRITICAL |
| **Hosted API playground** | Socket, Snyk let users try the product in-browser. SCBE requires local install. | HIGH |
| **Product Hunt page** | Major discovery channel for developer tools. Not launched. | HIGH |
| **Onboarding quickstart** | npm/PyPI packages exist but no "5-minute quickstart" guide. | HIGH |
| **Pricing page** | No public pricing. Enterprise buyers need to see tiers. | HIGH |
| **Customer testimonials** | Zero social proof. Need at least 3 testimonials. | HIGH |
| **SOC 2 Type 1** | Enterprise gate. At minimum, start the process. | MEDIUM |
| **Landing page with clear CTA** | aethermoorgames.com exists but doesn't clearly sell a product. | HIGH |
| **Email capture / waitlist** | No way to collect interested leads. | HIGH |
| **Changelog / release notes** | Users need to see activity and progress. | MEDIUM |
| **Status page** | Enterprise customers expect uptime monitoring. | LOW |
| **Bug bounty program** | Security companies should eat their own dog food. | MEDIUM |

### Automation That Would Save the Most Time

| Automation | Time Saved | Effort to Build |
|------------|-----------|-----------------|
| **Auto-post to all platforms on git tag** | 2h/release | 4h (extend existing publishers) |
| **Auto-generate release notes from commits** | 1h/release | 2h (auto-changelog exists, needs polish) |
| **Nightly training data quality report** | 30min/day | 3h |
| **Automated Stripe revenue dashboard** | 15min/day | 2h |
| **Auto-respond to GitHub issues with RAG** | 30min/issue | 6h |

### What Would Make the First Sale Happen Faster

| Action | Impact | Effort |
|--------|--------|--------|
| **Gumroad product page for Training Vault** | Direct revenue path | 2h |
| **"Buy" button on website homepage** | Convert visitors to customers | 30min |
| **Free tier with email capture** | Lead generation | 4h |
| **LinkedIn post about the patent** | Credibility signal | 30min |
| **Product Hunt launch** | Discovery spike | 4h |

### What Would Make Enterprise Buyers Trust Us

| Action | Impact | Effort |
|--------|--------|--------|
| **SOC 2 Type 1 assessment** | Opens enterprise sales | $5K-$15K + 3 months |
| **Third-party penetration test** | Proves security claims | $2K-$10K |
| **Published benchmark whitepaper** | Technical credibility | 2 weeks |
| **Customer reference** (even free pilot) | Social proof | Need to find first customer |
| **SLA documentation** | Shows operational maturity | 4h to write |
| **Data processing agreement template** | Legal readiness | 2h with template |

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Scripts (all types) | 149+ |
| Claude Code Skills | 29 |
| Standalone Skills | 17 |
| GitHub Actions Workflows | 67 |
| API Endpoints | 20+ |
| Demos | 12 |
| MCP Servers | 7 |
| Training Data Files/Dirs | 61 |
| Source Modules (src/) | 62+ |
| Tests | 6,134+ passing |
| Published Platforms | npm, PyPI, HuggingFace, GitHub, Dev.to, YouTube, Shopify |
