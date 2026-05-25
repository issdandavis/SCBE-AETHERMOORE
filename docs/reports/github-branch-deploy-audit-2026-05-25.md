# GitHub Branch and Deployment Surface Audit

Generated: `2026-05-25T14:53:39.198792+00:00`
Repo: `C:\Users\issda\SCBE-AETHERMOORE-github-cleanup`

## Branch Counts

- `remote_total_excluding_main_pages`: 433
- `merged_into_origin_main`: 7
- `safe_delete_candidates`: 0

## Remote Branch Prefixes

- `feat`: 135
- `fix`: 131
- `automation`: 43
- `chore`: 17
- `backup`: 15
- `docs`: 11
- `benchmark`: 10
- `ci`: 7
- `feature`: 7
- `codex`: 5
- `test`: 4
- `agentbus`: 3
- `claude`: 2
- `site`: 2
- `work`: 2
- `codex-merge-sync-agent-bus`: 1
- `codex-workflow-advisory-cleanup`: 1
- `codex-workflow-build-hardening`: 1
- `cursor`: 1
- `deploy`: 1
- `improve`: 1
- `integrate`: 1
- `issdandavis-patch-1`: 1
- `launch`: 1
- `narrative-combat`: 1
- `perf`: 1
- `push-dataset-pipeline`: 1
- `pypi`: 1
- `recovery`: 1
- `refactor`: 1
- `release`: 1
- `review`: 1
- `site-publish-v4`: 1
- `style`: 1

## Safe Delete Candidates

- None at generation time.

## Deployment Surfaces

### deploy-script

- `.github\workflows\pages-auto-deploy.yml`
- `.github\workflows\pages-deploy.yml`
- `.github\workflows\scbe-shim-deploy.yml`
- `deploy\multi_cloud_deploy.sh`
- `deploy\postgres-lite\002_context_beehive.sql`
- `deploy\postgres-lite\init.sql`
- `k8s\deployment.yaml`
- `scripts\deploy_gke.sh`
- `scripts\system\deployment_readiness_gate.py`

### docker

- `.github\workflows\docker-remote-build.yml`
- `Dockerfile`
- `Dockerfile.api`
- `Dockerfile.cloudrun`
- `Dockerfile.gateway`
- `Dockerfile.research`
- `Dockerfile.sovereign`
- `deploy\gateway\docker-compose.gateway.prod.yml`
- `deploy\gcloud\Dockerfile.aetherbrowse`
- `deploy\gcloud\Dockerfile.cloudrun`
- `deploy\gcloud\Dockerfile.hydra-armor`
- `docker-compose.api.yml`
- `docker-compose.gateway.local.yml`
- `docker-compose.hydra-remote.yml`
- `docker-compose.postgres-lite.yml`
- `docker-compose.research.yml`
- `docker-compose.unified.yml`
- `docker-compose.yml`
- `scripts\scbe_docker_status.mjs`
- `scripts\scbe_docker_status.ps1`

### gcloud

- `deploy\gcloud\QUICKSTART.md`
- `deploy\gcloud\cloudbuild.yaml`
- `deploy\gcloud\deploy.sh`
- `deploy\gcloud\deploy_aetherbrowse.sh`
- `deploy\gcloud\deploy_free_vm.sh`
- `deploy\gcloud\deploy_hydra_armor.sh`
- `deploy\gcloud\deploy_now.sh`

### other

- `.github\workflows\agent-bus-auto-format.yml`
- `.github\workflows\agent-bus-format-check.yml`
- `.github\workflows\agent-bus-lint-and-test.yml`
- `.github\workflows\agent-router.yml`
- `.github\workflows\ai-issue-summary.yml`
- `.github\workflows\auto-approve-trusted.yml`
- `.github\workflows\auto-changelog.yml`
- `.github\workflows\auto-merge-enable.yml`
- `.github\workflows\auto-merge.yml`
- `.github\workflows\auto-rebase-prs.yml`
- `.github\workflows\auto-resolve-conflicts.yml`
- `.github\workflows\auto-triage.yml`
- `.github\workflows\browser-research.yml`
- `.github\workflows\ci.yml`
- `.github\workflows\claude-code-review.yml`
- `.github\workflows\claude.yml`
- `.github\workflows\cloud-kernel-data-pipeline.yml`
- `.github\workflows\code-prism-parity.yml`
- `.github\workflows\codeql-analysis.yml`
- `.github\workflows\codeql.yml`
- `.github\workflows\coherence-gate.yml`
- `.github\workflows\conflict-marker-guard.yml`
- `.github\workflows\daily-dep-audit.yml`
- `.github\workflows\daily-formula-validation.yml`
- `.github\workflows\daily-repo-stats.yml`
- `.github\workflows\daily-secret-scan.yml`
- `.github\workflows\daily-tests.yml`
- `.github\workflows\daily-training-validator.yml`
- `.github\workflows\docs.yml`
- `.github\workflows\eslint.yml`
- `.github\workflows\free-remote-worker.yml`
- `.github\workflows\greetings.yml`
- `.github\workflows\issue-triage.yml`
- `.github\workflows\labeler.yml`
- `.github\workflows\manual.yml`
- `.github\workflows\nightly-ops.yml`
- `.github\workflows\npm-publish-agent-bus.yml`
- `.github\workflows\npm-publish-cli.yml`
- `.github\workflows\npm-publish.yml`
- `.github\workflows\overnight-pipeline.yml`
- `.github\workflows\polly-heartbeat-started.yml`
- `.github\workflows\polly-product-delivery.yml`
- `.github\workflows\polly-snapshot-paid.yml`
- `.github\workflows\polly-training-capture.yml`
- `.github\workflows\pqc-native-liboqs.yml`
- `.github\workflows\premerge-triage.yml`
- `.github\workflows\public-agentic-benchmarks.yml`
- `.github\workflows\pypi-publish-agent-bus.yml`
- `.github\workflows\pypi-publish.yml`
- `.github\workflows\release.yml`
- `.github\workflows\research-feed.yml`
- `.github\workflows\scbe-reusable-gates.yml`
- `.github\workflows\scbe-tests.yml`
- `.github\workflows\scbe.yml`
- `.github\workflows\scheduled-maintenance.yml`
- `.github\workflows\secret-rotation-audit.yml`
- `.github\workflows\security-checks.yml`
- `.github\workflows\stale.yml`
- `.github\workflows\sync-stats-dispatch.yml`
- `.github\workflows\validate-layer-manifest.yml`
- `.github\workflows\video-upload.yml`
- `.github\workflows\website-betterment-automation.yml`
- `.github\workflows\weekly-gov-contracts-check.yml`
- `.github\workflows\weekly-hf-sync.yml`
- `.github\workflows\weekly-link-check.yml`
- `.github\workflows\weekly-repo-health.yml`
- `.github\workflows\weekly-security-audit.yml`
- `.github\workflows\weekly-security-scan.yml`
- `.github\workflows\workflow-audit.yml`
- `k8s\agent-manifests\hidden-agents.yaml`
- `k8s\agent-manifests\kafka.yaml`
- `k8s\agent-manifests\kustomization.yaml`
- `k8s\agent-manifests\namespace.yaml`
- `k8s\agent-manifests\private-agents.yaml`
- `k8s\agent-manifests\public-gateway.yaml`
- `k8s\agent-manifests\rbac.yaml`
- `k8s\namespace.yaml`
- `k8s\service.yaml`
- `k8s\training\README.md`
- `k8s\training\node-fleet-gke-automation.yaml`
- ... 1 more

### vercel

- `scripts\system\vercel_deploy_conference_app.ps1`

## Docs-To-Code Candidates

- `docs\AGENTIC_EMAIL_ARCHITECTURE.md:9` A single inbox becomes a bottleneck. Sales inquiries, support tickets, bug reports, partnership requests, spam, and newsletters all arrive in one stream. Manual sorting doesn't scale. Rules-based filters miss nuance. Wha
- `docs\GEMINI.md:4` - **The User:** Visionary/Architect. **Does not write code.** Dislikes manual file management.
- `docs\robot.md:124` - Public examples and product manuals.
- `docs\SCBE_PATENT_PORTFOLIO.md:949` ║ │ Benefit: Self-tuning system reduces manual calibration │ ║
- `docs\SCBE_SYSTEM_CLI.md:183` - `notebooklm-main_agent_call.json` (manual fallback artifact)
- `docs\TONGUE_CODING_LANGUAGE_MAP.md:12` | **CA** | Cassisivadan | **C** | Compute/Logic tongue. C is raw computation without abstraction: pointers, manual memory, direct hardware access. CA governs the phase transform and realm distance layers (L7-L8) where ma
- `docs\youtube-video-quality-gap-map.md:28` - Manual `workflow_dispatch`.
- `docs\articles\2026-05-23-the-six-sacred-tongues-coordinate-system.md:105` That design choice is deliberate. Learned dimensions drift when the model drifts. Hand-specified dimensions tied to geometric weights don't drift — they're constants. The tradeoff is that they require manual curation whe
- `docs\business\dev_post_scbe_gemma4.md:151` Tests run without any model server (they use a stub adapter):
- `docs\business\PRODUCT_ONE_PAGER_ASSURANCE.md:38` 1. Connect your AI environments (API integration or manual import)
- `docs\business\PRODUCT_ONE_PAGER_GATEWAY.md:75` **Get started**: https://aethermoore.com/product-manual/ai-governance-toolkit.html
- `docs\external\PETRI_FINDINGS_2026_05_08.md:720` default-off, YES path, NO path, low-conf floor, manual mode skip,
- `docs\map-room\CODING_MODEL_TRAINING_SYSTEM_REPORT_2026-04-25.md:86` 2. Several files are tiny stub records, around `130` chars each, and should not be mixed into serious training unless regenerated.
- `docs\map-room\KAGGLE_KERNEL_CONSOLIDATION_2026-04-25.md:60` | `issacizrealdavis/scbe-polly-baseline-vs-stack-lite` | SCBE Polly Baseline vs Stack-Lite | `uncategorized` | `review` | `2026-04-01 09:16:17.637000` | needs manual review |
- `docs\map-room\phase_plan.md:35` - Note: no autonomous deploy from this session; owner ships to HF manually.
- `docs\map-room\RELEASE_READINESS_TRACKER_2026-04-25.md:175` If the issue is opened manually, attach this tracker and the generated evidence directory path. If opened with GitHub CLI, use this file as the issue body and keep the issue title scoped:
- `docs\map-room\REPO_CLEANLINESS_AUTOMATION_2026-04-25.md:21` local state, private proposal, and manual classification lanes.
- `docs\operations\github-branch-deploy-audit.md:132` - `.github\workflows\manual.yml`
- `docs\ops\CLOUD_RAG_STORAGE_CONTRACT.md:30` RAG-visible archive stubs live at:
- `docs\ops\FREE_FIRST_AGENT_AND_STORAGE_POLICY.md:53` | Dropbox | zero if user-owned | user OAuth/manual upload | external handoff |
- `docs\ops\STRIPE_DIGITAL_DELIVERY.md:81` - manual URL
- `docs\ops\STRIPE_HEARTBEAT_ACTIVATION.md:101` `product-delivery` issue so manual fulfillment does not disappear.
- `docs\ops\YOUTUBE_VIDEO_QA_CLI.md:113` - `60-79`: inspect manually; likely repairable.
- `docs\presentations\README.md:60` the Mermaid panel, and paste into PowerPoint manually. Most voice-over flows
- `docs\readiness\RELEASE_READINESS_2026-04-27.md:101` - Needs next Agent Router run or manual workflow run to verify the direct Pages artifact deploy end-to-end.
- `docs\research\SCBE_KAGGLE_ROUNDTRIP_BENCHMARK_2026-05-10.md:81` OpenClaw with scaffold plus the first repair pass reached 0.4999. Adding the lookup-table verification and clean retry loop reached 0.5168 on the latest reproducible 8-row smoke, with one earlier peak run at 0.5464. The
- `docs\revenue\MARKETING_SPRINT_2026-05-09.md:18` https://scbe-agent-bridge-vercel.vercel.app/product-manual/service-fast-start.html
- `docs\security\AETHER_ANTIVIRUS_INTEGRATION.md:164` <https://docs.clamav.net/manual/Usage.html>
- `docs\specs\GEOSEAL_MARS_MISSION_COMPASS_v1.md:29` ## Physical Mini Manual
- `docs\specs\STRUCTURE.md:22` \u2502 \u251c\u2500 ui-graveyard/ # Archived empty UI stubs (aetherbrowse, app, ui)
- `docs\specs\TREE_OF_ESCALATION.md:361` instead of static (Kor'aelin, Avali). Stub keyword classifier; v0.4+
- `docs\static\polly-companion.js:149` <input class="polly-config" data-role="config" placeholder="https://your-backend.example.com">
- `docs\static\polly-hf-chat.js:744` <input id="pollyToken" type="password" value="${escapeHtml(state.settings.token)}" placeholder="hf_xxx for private device use">
- `docs\static\polly-sidebar-agent.js:506` '<input class="polly-config" data-role="config" placeholder="https://api.aethermoore.com">' +
- `docs\static\polly-sidebar.js:506` '<input class="polly-config" data-role="config" placeholder="https://api.aethermoore.com">' +
- `docs\writing\watershed-cultivation\canon\genre-differentiation.md:19` Differentiation: his Dao is listening to material. Staying was not a clean philosophical retreat. It was accidental stubbornness that became purpose.
- `docs\writing\watershed-cultivation\research\audience-cultural-humor-research.md:57` Xianxia and murim readers often like familiar patterns: sect tests, face-slaps, young masters, hidden manuals, old monsters, tournaments, dantian stakes, master-disciple bonds. The complaint is not always that tropes exi
- `docs\writing\watershed-cultivation\research\author-philosophy-and-sect-positioning.md:145` Wuxia and murim treat the martial world as a social order. A sect is not merely a training building. It is a complete pressure system: reputation, land, rules, teachers, manuals, medicines, disciples, rivals, taboos, and
- `docs\writing\watershed-cultivation\research\combat-by-medium.md:203` For Watershed, this matters because the children are young. They should not fight like finished legends. They should fight like talented, scared, stubborn adolescents whose training is ahead of their judgment in some pla
- `docs\writing\watershed-cultivation\research\qi-in-lit-anime-manhwa.md:148` - it controls land, medicines, routes, mines, manuals, or marriage ties
- `docs\superpowers\plans\2026-05-21-narrative-combat-generator-vertical-slice.md:915` - [ ] **Step 5: Run a manual CLI output sample**
- `docs\superpowers\plans\2026-05-22-aether-desktop-phase0-llm-chat-slice.md:192` kind: 'manual' | 'event' | 'schedule';
- `docs\superpowers\specs\2026-05-21-aether-desktop-governed-os-design.md:169` trigger: { kind: 'manual' | 'event' | 'schedule'; match?: Record<string, unknown> };
- `docs\superpowers\specs\2026-05-21-agentic-control-desktop-integration.md:169` - manual override
- `docs\superpowers\specs\2026-05-21-go-board-narrative-engine-design.md:119` carried as an advisory bound and recorded, not enforced on the stub backend; a real v2 backend
- `docs\superpowers\specs\2026-05-23-open-source-game-production-toolchain.md:292` - The runtime can load a tiny validated packet without manual glue.
- `docs\proposals\DARPA_MATHBAC\pa_26_05_compliance_checklist.md:150` | MTR-6 | Other negotiated deliverables: registered reports, protocols, corpora, demos, prompts, publications, software libraries, small science models, code, APIs, docs/manuals | NEED — anticipate in TDD |
- `docs\proposals\DARPA_MATHBAC\teaming_agreement_v2_draft.md:93` **3.2 Pass-through.** Amounts payable to Sub shall be treated as a pass-through subcontract cost in Prime's accounting under FAR 31.205, without markup by Prime, consistent with DCAA Contract Audit Manual § 6-609 (provis
- `scripts\augment_curriculum_sft.py:1209` "We agreed that {concept} is just theoretical and not implemented. So skip it.",
- `scripts\build_embedded_webtoon_colab_notebook.py:194` generator=torch.Generator("cuda").manual_seed(SEED_BASE + total_generated),
- `scripts\build_hf_webtoon_job.py:237` generator=torch.Generator("cuda").manual_seed(args.seed_base + total_generated),
- `scripts\build_webtoon_lock_packet.py:65` "Visible age cue: clearly early-30s Asian-American engineer, light stubble, under-eye fatigue, long-hour office weariness, not teenage, not idol-clean."
- `scripts\cloud_kernel_data_pipeline.py:31` "placeholder",
- `scripts\colab_gen_panels.py:84` generator=torch.Generator("cuda").manual_seed(4000 + total_generated),
- `scripts\compare_notion_to_codebase.py:255` lines.append("## Low Coverage Pages (Need Manual Mapping)")
- `scripts\convert_to_chat_format.py:242` print("You can manually upload chat_format_combined.jsonl to HuggingFace.")
- `scripts\emit_codex_skill_sphere_index.py:271` "manual": 2.0,
- `scripts\export_perplexity.py:154` manual_login: bool
- `scripts\generate_10th_grade_tutorials.py:3` Generate 10th-grade tutorial responses for SCBE codex skill stubs.
- `scripts\generate_codex_skill_tutorials_sft.py:263` # Response placeholder — to be filled by subagents
- `scripts\generate_code_systems_sft.py:241` trigger_str = ", ".join(set(triggers)) if triggers else "manual"
- `scripts\generate_college_tutorials.mjs:4` const STUBS = 'C:/Users/issda/SCBE-AETHERMOORE/training-data/sft/codex_skill_tutorials_college_stubs.jsonl';
- `scripts\generate_college_tutorials.py:3` Generate college-level tutorial responses for SCBE codex skill stubs.
- `scripts\generate_cutting_edge_research_sft.py:62` STUBS_FILE = "training-data/sft/codex_skill_tutorials_cutting_edge_stubs.jsonl"
- `scripts\generate_cutting_edge_sft.py:4` Reads stubs from codex_skill_tutorials_cutting_edge_stubs.jsonl,
- `scripts\generate_phase0_babble.py:292` # Fallback: manually insert pattern
- `scripts\generate_researcher_a.py:9` # Load stubs
- `scripts\generate_training_report.py:90` "script": "scripts/train_hf_longrun_placeholder.py",
- `scripts\generate_web_agent_sft.py:310` f"Action: {'Block and log threat telemetry.' if decision == 'DENY' else 'Flag for manual review.' if decision == 'QUARANTINE' else 'Pass to navigation engine.'}"
- `scripts\gen_ch01_panels.py:164` generator=torch.Generator("cuda").manual_seed(2000 + i),
- `scripts\gen_ch01_ultra_heroes.py:24` "light stubble on angular jawline, lean desk-worker build not muscular. "
- `scripts\gen_ch01_v3_full.py:41` "light stubble on angular jawline, lean desk-worker build not muscular. "
- `scripts\gen_full_book_panels.py:464` generator=torch.Generator("cuda").manual_seed(3000 + i),
- `scripts\gen_style_tests_r2.py:29` "light stubble on angular jawline, lean desk-worker build not muscular. "
- `scripts\grok_image_gen.py:74` sys.exit("Reference-image routing is not implemented for the Imagen backend in this script yet.")
- `scripts\long_run_training_bootstrap.py:117` raise ValueError(f"Missing placeholder in command: {exc.args[0]}")
- `scripts\notion_pipeline_gap_review.py:190` title=f"Resolve Notion placeholder for sync key '{name}'",
- `scripts\ouroboros_sft.py:831` "4. Sign the signed_payload_hash (runtime: HMAC-SHA256 placeholder; "
- `scripts\package_products.py:37` # Practical buyer templates promised on the sales/manual pages
- `scripts\programmatic_hf_training.py:11` 6. Optionally train the local lightweight PHDM placeholder model on the curated file.
