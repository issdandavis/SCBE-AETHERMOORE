import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "system" / "openclaw_swarm.py"


def load_module():
    spec = importlib.util.spec_from_file_location("_openclaw_swarm_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_mentioned_paths_normalizes_diff_prefixes():
    module = load_module()

    text = """
    diff --git a/scripts/system/openclaw_swarm.py b/scripts/system/openclaw_swarm.py
    --- a/scripts/system/openclaw_swarm.py
    +++ b/scripts/system/openclaw_swarm.py
    Files:
      - /docs/AETHERBROWSER_PACK.md
    Verification: ./scripts/system/openclaw_swarm.py
    """

    assert module.extract_mentioned_paths(text) == [
        "docs/AETHERBROWSER_PACK.md",
        "scripts/system/openclaw_swarm.py",
    ]


def test_quality_flags_reject_placeholder_and_git_mutating_verification():
    module = load_module()

    text = """
    1. Decision: build
    2. Files:
       - scripts/system/missing.sh
    3. Patch:
    ```diff
    diff --git a/scripts/system/missing.sh b/scripts/system/missing.sh
    index 1234567..89abcdef 100755
    ```
    4. Verification: git add scripts/system/missing.sh && git commit -m test
    """

    flags = module.quality_flags(text, ("scripts/system/",))

    assert "path_not_found:scripts/system/missing.sh" in flags
    assert "placeholder_diff_index" in flags
    assert "verification_mutates_git_state" in flags


def test_quality_flags_accept_existing_scoped_file_reference():
    module = load_module()

    text = """
    1. Decision: defer
    2. Files:
       - aetherdesk/server.js
    3. Patch: none
    4. Verification: npx vitest run tests/aetherdesk/server.test.ts
    5. Risk: proposal only.
    """

    assert module.quality_flags(text, ("aetherdesk/", "tests/")) == []


def test_resolve_agent_uses_catalog_and_fallback_candidates():
    module = load_module()

    resolved = module.resolve_agent("opencode", {"qwen2.5-coder:1.5b"})

    assert resolved.status == "active"
    assert resolved.model == "qwen2.5-coder:1.5b"
    assert resolved.profile.launch_command == "ollama launch opencode"
    assert resolved.profile.geometry_role == "open-source patch proposer"
    assert resolved.execution_surface == "ollama_local"
    assert resolved.cost_tier == "free_local"


def test_resolve_agent_skips_missing_catalog_agent_without_losing_launch_path():
    module = load_module()

    resolved = module.resolve_agent("claude", set())

    assert resolved.status == "skipped"
    assert resolved.model is None
    assert resolved.profile.launch_command == "ollama launch claude"
    assert resolved.execution_surface == "none"


def test_quality_flags_accept_markdown_bold_decision_label():
    module = load_module()

    text = """
    1. **Decision**: defer
    2. Files:
       - aetherdesk/server.js
    3. Patch: none
    4. Verification: npx vitest run tests/aetherdesk/server.test.ts
    5. Risk: proposal only.
    """

    assert "decision_missing_or_ambiguous" not in module.quality_flags(text, ("aetherdesk/", "tests/"))


def test_quality_flags_accept_markdown_bold_decision_value():
    module = load_module()

    text = """
    1. Decision: **build**
    2. Files:
       - aetherdesk/server.js
    3. Patch: none
    4. Verification: npx vitest run tests/aetherdesk/server.test.ts
    5. Risk: proposal only.
    """

    assert "decision_missing_or_ambiguous" not in module.quality_flags(text, ("aetherdesk/", "tests/"))


def test_quality_flags_accept_json_style_decision_value():
    module = load_module()

    text = """
    {
      "Decision": "evidence",
      "Files checked": ["scripts/system/openclaw_swarm.py"]
    }
    """

    assert "decision_missing_or_ambiguous" not in module.quality_flags(text, ("scripts/",))


def test_quality_flags_accept_answer_contract_without_paths():
    module = load_module()

    text = """
    1. Decision: answer
    2. Capability: You can run local role benchmarks.
    3. Limits: No repo mutation.
    4. Next action: Run the role test.
    5. Risk: Low.
    """

    assert module.quality_flags(text, ("docs/",), require_paths=False) == []


def test_quality_flags_answer_contract_ignores_limit_path_mentions():
    module = load_module()

    text = """
    1. Decision: answer
    2. Capability: You can read public docs.
    3. Limits: You cannot modify `.git` or `.env`.
    4. Next action: Read docs.
    5. Risk: Low.
    """

    assert module.quality_flags(text, ("docs/",), require_paths=False, check_paths=False) == []


def test_quality_flags_reject_unresolved_answer_decision_template():
    module = load_module()

    text = """
    1. Decision: answer | defer | needs-human
    2. Capability: You can read public docs.
    """

    assert "unresolved_decision_template" in module.quality_flags(
        text,
        ("docs/",),
        require_paths=False,
        check_paths=False,
    )


def test_quality_flags_reject_non_git_diff_and_invented_runner_flag():
    module = load_module()

    text = """
    1. **Decision**: build
    2. **Files**:
       - `tests/test_agent_router_bridge_tasks.py`
    3. **Patch**:
    ```diff
    --- tests/test_agent_router_bridge_tasks.py.orig 2023-10-05
    +++ tests/test_agent_router_bridge_tasks.py 2023-10-05
    @@ -1,2 +1,3 @@
    +from hermes.agent.router.result_quality import AgentRouterResultQuality
    ```
    4. **Verification**:
    ```bash
    pytest -v tests/test_agent_router_bridge_tasks.py --hermes-agent=hermes
    ```
    """

    flags = module.quality_flags(text, ("tests/", "scripts/"))

    assert "non_git_unified_diff_context" in flags
    assert "invented_test_runner_flag" in flags
    assert "probable_external_module_import" in flags


def test_quality_flags_reject_wrapper_symbol_hallucination():
    module = load_module()

    text = """
    1. Decision: build
    2. Files:
       - scripts/system/scbe_swarm_router.py
    3. Patch:
    ```diff
    --- a/scripts/system/scbe_swarm_router.py
    +++ b/scripts/system/scbe_swarm_router.py
    @@ -1,2 +1,3 @@
     class SCBESwarmRouter:
         pass
    ```
    4. Verification: python -m py_compile scripts/system/scbe_swarm_router.py
    """

    assert "probable_wrapper_symbol_hallucination" in module.quality_flags(text, ("scripts/",))


def test_quality_flags_reject_missing_context_symbol():
    module = load_module()

    text = """
    1. Decision: build
    2. Files:
       - scripts/system/scbe_swarm_router.py
    3. Patch:
    ```diff
    --- a/scripts/system/scbe_swarm_router.py
    +++ b/scripts/system/scbe_swarm_router.py
    @@ -42,6 +42,9 @@ class DefinitelyMissingRouter:
         pass
    ```
    4. Verification: python -m py_compile scripts/system/scbe_swarm_router.py
    """

    flags = module.quality_flags(text, ("scripts/",))

    assert "symbol_not_found:scripts/system/scbe_swarm_router.py#DefinitelyMissingRouter" in flags


def test_quality_flags_accept_symbol_imported_from_local_python_module():
    module = load_module()

    text = """
    1. Decision: build
    2. Files:
       - src/cddm/tongue_domains.py
    3. Patch:
    ```diff
    --- a/src/cddm/tongue_domains.py
    +++ b/src/cddm/tongue_domains.py
    @@ -31,6 +31,7 @@ TONGUE_DOMAINS: Dict[str, Domain] = {
         "KO": Domain("Energy", units=("Joule",), bounds=(0, 1e6)),
    ```
    4. Verification: python -m py_compile src/cddm/tongue_domains.py
    """

    flags = module.quality_flags(text, ("src/",), require_paths=True)

    assert "symbol_not_found:src/cddm/tongue_domains.py#Domain" not in flags


def test_file_contains_symbol_resolves_local_python_imports():
    module = load_module()

    assert module._file_contains_symbol("src/cddm/tongue_domains.py", "Domain") is True


def test_file_contains_symbol_resolves_src_layout_absolute_import(tmp_path):
    module = load_module()
    probe = Path("artifacts") / "tmp_symbol_probe.py"
    target = REPO_ROOT / probe
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("from cddm.domain import Domain\n\nvalue = Domain\n", encoding="utf-8")
    try:
        assert module._file_contains_symbol(probe.as_posix(), "Domain") is True
    finally:
        target.unlink(missing_ok=True)


def test_file_contains_symbol_still_rejects_missing_local_symbol():
    module = load_module()

    assert module._file_contains_symbol("src/cddm/tongue_domains.py", "NotDomain") is False


def test_file_contains_symbol_rejects_missing_relative_import(tmp_path):
    module = load_module()
    probe_dir = REPO_ROOT / "artifacts" / "tmp_symbol_pkg"
    probe_dir.mkdir(parents=True, exist_ok=True)
    probe = probe_dir / "module.py"
    probe.write_text("from .missing import MissingThing\n\nvalue = MissingThing\n", encoding="utf-8")
    try:
        assert module._file_contains_symbol("artifacts/tmp_symbol_pkg/module.py", "MissingThing") is False
    finally:
        probe.unlink(missing_ok=True)
        probe_dir.rmdir()


def test_quality_flags_reject_evidence_symbols_not_present_in_checked_files():
    module = load_module()

    text = """
    1. Decision: evidence
    2. Files checked:
       - scripts/system/openclaw_swarm.py
    3. Declarations:
       - `load_task_graph_prompt`
       - `WorkLane`
    4. Builder handoff: Patch only real declarations.
    5. Risk: invented declarations poison the builder lane.
    """

    flags = module.quality_flags(text, ("scripts/",), require_paths=True)

    assert "evidence_symbol_not_found:load_task_graph_prompt" in flags
    assert "evidence_symbol_not_found:WorkLane" not in flags


def test_quality_flags_do_not_treat_evidence_file_stems_as_symbols():
    module = load_module()

    text = """
    1. Decision: evidence
    2. Files checked:
       - `scripts/benchmark/openclaw_swarm_benchmark.py`
       - `docs/research/SCBE_SWARM_ROUTER_COMPARISON_2026-05-10.md`
    3. Declarations:
       - `BenchmarkCase` (from scripts/benchmark/openclaw_swarm_benchmark.py)
       - `openclaw_swarm_benchmark` evidence file
       - `SCBE_SWARM_ROUTER_COMPARISON_2026` evidence note
    """

    flags = module.quality_flags(text, ("scripts/", "docs/"), require_paths=True)

    assert "evidence_symbol_not_found:openclaw_swarm_benchmark" not in flags
    assert "evidence_symbol_not_found:SCBE_SWARM_ROUTER_COMPARISON_2026" not in flags


def test_applicability_score_penalizes_hard_blockers():
    module = load_module()

    score = module.applicability_score(
        [
            "path_not_found:scripts/missing.py",
            "symbol_not_found:scripts/system/scbe_swarm_router.py#Missing",
        ]
    )

    assert score == 30


def test_quality_flags_reject_blacklisted_and_graylisted_paths():
    module = load_module()

    text = """
    1. Decision: build
    2. Files:
       - .env
       - package.json
    3. Patch: none
    4. Verification: npm test
    """

    flags = module.quality_flags(text, ("scripts/", "package.json"))

    assert "blacklisted_path:.env" in flags
    assert "graylisted_path_requires_approval:package.json" in flags


def test_build_lanes_assigns_tiers_and_contracts():
    module = load_module()

    local = module.resolve_agent("openclaw", {"openclaw:latest"})
    cloud = module.resolve_agent(
        "opencode",
        {"qwen2.5-coder:1.5b"},
        allow_ollama_cloud=True,
        prefer_ollama_cloud=True,
    )

    lanes = module.build_lanes("test task", [local, cloud], ("scripts/", "tests/"))

    assert lanes[0].lane_tier == "builder"
    assert lanes[0].helper_contract
    assert lanes[1].lane_tier == "escalation"
    assert "grey_requires_human" in lanes[1].trust_policy


def test_routing_recommendation_includes_correction_guide():
    module = load_module()

    lane = module.WorkLane(
        lane_id="01-implementation",
        lane_tier="builder",
        agent_alias="openclaw",
        agent_name="OpenClaw",
        model="openclaw:latest",
        execution_surface="ollama_local",
        cost_tier="free_local",
        geometry_role="router",
        geometry_anchor=(1.0, 0.0, 0.0),
        goal="test",
        allowed_paths=("scripts/",),
        blocked_paths=(".git/",),
        done_criteria=("done",),
        verify_command="npm test",
        helper_contract="builder",
        cycle_policy="retry with correction",
        trust_policy="allow=scripts/",
        output_contract="patch-proposal",
    )
    agent = module.resolve_agent("openclaw", {"openclaw:latest"})
    results = [
        {
            "lane": module.asdict(lane),
            "ok": True,
            "error": "",
            "response": "1. Decision: build\n2. Files:\n- scripts/missing.py",
            "response_chars": 10,
            "quality_flags": ["path_not_found:scripts/missing.py"],
            "constraint_mode": "strict",
            "elapsed_seconds": 0.1,
        }
    ]

    routing = module.build_routing_recommendation(results, [agent])

    assert routing["policy"] == "tiered_free_first_guarded_builder_rotation"
    assert routing["quality_flag_counts"]["path_not_found"] == 1
    assert routing["correction_guide"][0]["flag"] == "path_not_found"
    assert routing["assurance_packet"]["schema"] == "scbe_darpa_style_assurance_packet_v1"
    assert "heterogeneous_evidence" in routing["assurance_packet"]["requirements"]
    assert routing["next_cycle"] == "helper_collect_file_evidence_then_guard_review"


def test_choose_next_action_is_output_contract_aware():
    module = load_module()

    answer_lane = {"lane": {"output_contract": "answer"}}
    evidence_lane = {"lane": {"output_contract": "evidence"}}
    patch_lane = {"lane": {"output_contract": "patch-proposal"}}

    assert module.choose_next_action([answer_lane], False) == "deliver_answer_to_user"
    assert module.choose_next_action([evidence_lane], False) == "handoff_evidence_to_builder"
    assert module.choose_next_action([patch_lane], False) == "extract_one_promotable_diff_then_safe_apply"
    assert module.choose_next_action([], True) == "run_helper_guard_cycle_before_escalation"


def test_task_graph_selects_public_answer_node(tmp_path):
    module = load_module()
    graph_path = tmp_path / "task_graph.json"
    graph_path.write_text(
        json.dumps(
            {
                "task_types": {
                    "public_answer": {
                        "operation_frame": "answer",
                        "description": "Answer public free-user capability questions.",
                        "aliases": ["public free user"],
                        "source_clues": ["public", "free user"],
                        "response_format": ["direct answer"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    module.KNOWLEDGE_GRAPH_PATH = graph_path

    graph = module.load_task_graph()
    name, node = module.select_task_graph_node("Public free user role: what can I do?", "answer", graph)

    assert name == "public_answer"
    assert node["operation_frame"] == "answer"


def test_prompt_includes_task_graph_hint(tmp_path):
    module = load_module()
    graph_path = tmp_path / "task_graph.json"
    graph_path.write_text(
        json.dumps(
            {
                "task_types": {
                    "public_answer": {
                        "operation_frame": "answer",
                        "description": "Answer public free-user capability questions.",
                        "aliases": ["public free user"],
                        "source_clues": ["public", "free user"],
                        "response_format": ["direct answer", "next step"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    module.KNOWLEDGE_GRAPH_PATH = graph_path

    agent = module.resolve_agent("openclaw", {"openclaw:latest"})
    lane = module.build_lanes("Public free user role: what can I do?", [agent], ("docs/",))[0]
    lane = module.WorkLane(**{**module.asdict(lane), "output_contract": "answer"})

    prompt = module.prompt_for_lane(lane, ["docs/research/SCBE_BUS_TASK_KNOWLEDGE_GRAPH_2026-05-10.json"], "relaxed")

    assert "Task graph node: public_answer" in prompt
    assert "Expected response shape:" in prompt


def test_prompt_includes_deterministic_declaration_hints():
    module = load_module()

    agent = module.resolve_agent("openclaw", {"openclaw:latest"})
    lane = module.build_lanes("Inspect router declarations", [agent], ("scripts/",))[0]

    prompt = module.prompt_for_lane(lane, ["scripts/system/openclaw_swarm.py"], "strict")

    assert "Known declaration hints:" in prompt
    assert "scripts/system/openclaw_swarm.py:" in prompt
    assert "WorkLane" in prompt


def test_inventory_focus_paths_prevent_broad_repo_spray():
    module = load_module()

    files = module.inventory_allowed_files(
        ("scripts/", "tests/", "docs/"),
        (
            "scripts/system/openclaw_swarm.py",
            "scripts/system/scbe_swarm_router.py",
        ),
    )

    assert files == [
        "scripts/system/openclaw_swarm.py",
        "scripts/system/scbe_swarm_router.py",
    ]


def test_make_run_dir_allocates_unique_directories(tmp_path):
    module = load_module()

    first = module.make_run_dir(tmp_path)
    second = module.make_run_dir(tmp_path)

    assert first.exists()
    assert second.exists()
    assert first != second


def test_select_coding_systems_prefers_stisa_for_atomic_tasks():
    module = load_module()

    registry = {
        "systems": [
            {
                "system_id": "swarm_router",
                "name": "Router",
                "purpose": "Route agents",
                "best_for": [],
                "benchmark_role": "swarm_surface",
            },
            {
                "system_id": "stisa_atomic_tokenizer",
                "name": "STISA Atomic Tokenizer Surface",
                "purpose": "Atomic tokenizer feature rows",
                "best_for": ["precision builds"],
                "benchmark_role": "atomic_surface",
            },
        ]
    }

    selected = module.select_coding_systems("Use STISA atomic tokenizer for precision builds", "evidence", registry)

    assert selected[0]["system_id"] == "stisa_atomic_tokenizer"


def test_prompt_includes_coding_system_registry_hints(tmp_path):
    module = load_module()
    registry_path = tmp_path / "coding_system_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "systems": [
                    {
                        "system_id": "stisa_atomic_tokenizer",
                        "purpose": "Atomic tokenizer feature rows",
                        "best_for": ["precision coding", "cross-language"],
                        "benchmark_role": "atomic_surface",
                        "commands": ["python scripts/system/scbe_swarm_router.py --dry-run"],
                        "expected_outputs": ["structured hints"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    module.CODING_SYSTEM_REGISTRY_PATH = registry_path

    agent = module.resolve_agent("openclaw", {"openclaw:latest"})
    lane = module.build_lanes("Use STISA and SS1 for cross-language precision coding", [agent], ("scripts/",))[0]

    prompt = module.prompt_for_lane(lane, ["scripts/system/openclaw_swarm.py"], "strict")

    assert "Coding system registry:" in prompt
    assert "stisa_atomic_tokenizer" in prompt


def test_prompt_includes_kaggle_winner_loop_hint():
    module = load_module()

    agent = module.resolve_agent("openclaw", {"openclaw:latest"})
    lane = module.build_lanes("Improve the coding harness without re-walking solved paths", [agent], ("scripts/",))[0]

    prompt = module.prompt_for_lane(lane, ["scripts/system/openclaw_swarm.py"], "strict")

    assert "Kaggle-style improvement loop:" in prompt
    assert "weakest dimension" in prompt
    assert "next cycle does not re-walk solved paths" in prompt


def test_inventory_allowed_files_prioritizes_existing_focus_paths():
    module = load_module()

    files = module.inventory_allowed_files(
        ("scripts/", "tests/"),
        ("scripts/system/openclaw_swarm.py", "not-real.py"),
        limit=8,
    )

    assert "scripts/system/openclaw_swarm.py" in files
    assert files[0] == "scripts/system/openclaw_swarm.py"
    assert "not-real.py" not in files


def test_implementation_lane_can_patch_tests_when_allowed():
    module = load_module()

    agent = module.resolve_agent("openclaw", {"openclaw:latest"})
    lanes = module.build_lanes("Patch router and tests", [agent], ("scripts/", "tests/"))

    assert "tests/" in lanes[0].allowed_paths


def test_resolve_agent_can_prefer_ollama_cloud_when_opted_in():
    module = load_module()

    resolved = module.resolve_agent(
        "opencode",
        {"qwen2.5-coder:1.5b"},
        allow_ollama_cloud=True,
        prefer_ollama_cloud=True,
    )

    assert resolved.status == "active_cloud"
    assert resolved.model.endswith("-cloud") or resolved.model.endswith(":cloud")
    assert resolved.execution_surface == "ollama_cloud"
    assert resolved.cost_tier == "ollama_cloud"


def test_pazaak_plan_marks_overlapping_builder_lanes_as_conflicts():
    module = load_module()

    openclaw = module.resolve_agent("openclaw", {"openclaw:latest"})
    opencode = module.resolve_agent("opencode", {"qwen2.5-coder:1.5b"})
    lanes = module.build_lanes("Patch the same router surface", [openclaw, opencode], ("scripts/", "tests/"))

    plan = module.build_pazaak_plan(lanes, limit=6)

    assert plan["schema"] == "scbe_swarm_pazaak_plan_v1"
    assert plan["bitboards"]["conflict"] != 0
    assert any(move["card_id"] == "claim_territory" for move in plan["moves"])


def test_integration_plan_includes_pazaak_board_recommendations():
    module = load_module()

    routing = {
        "policy": "tiered_free_first_guarded_builder_rotation",
        "free_signal_exhausted": False,
        "next_action": "review_promotable_lane",
        "next_cycle": "extract_one_promotable_diff_then_safe_apply",
        "guard_clean_lanes": 1,
        "builder_attempt_lanes": 1,
        "paid_escalation_note": "none",
        "correction_guide": [],
        "tier_contract": {"builder": "coding models produce narrow diffs"},
        "assurance_packet": {
            "schema": "scbe_darpa_style_assurance_packet_v1",
            "readiness": "prototype_evidence_packet",
            "acceptance_rule": "accept only verified lanes",
            "mean_applicability_score": 100,
            "requirements": {"traceability": "lane artifacts exist"},
        },
        "pazaak_plan": {
            "bitboards": {"conflict": 1},
            "moves": [
                {
                    "lane_id": "01-implementation",
                    "card_name": "Claim Territory",
                    "symbol": "+1",
                    "score": 12.5,
                    "reason": "matched file_conflict",
                }
            ],
        },
    }

    text = module.build_integration_plan("test", [], routing)

    assert "## Pazaak Board Recommendation" in text
    assert "Claim Territory" in text
