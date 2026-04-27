#!/usr/bin/env python3
"""Kaggle Zero-Touch Training Automation.

One command → creates kernel → pushes to Kaggle → runs on free T4 GPU →
polls until done → pulls output adapter → optionally pushes to HuggingFace.

No browser. No clicking. No copying tokens.

Usage:
    python scripts/kaggle_auto/launch.py --round covenantal
    python scripts/kaggle_auto/launch.py --round deep-knowledge --gpu t4x2
    python scripts/kaggle_auto/launch.py --round adversarial --poll
    python scripts/kaggle_auto/launch.py --status          # check running kernels
    python scripts/kaggle_auto/launch.py --pull             # download latest output
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from textwrap import dedent

try:
    from huggingface_hub import HfApi
except Exception:  # pragma: no cover - optional preflight dependency
    HfApi = None

REPO_ROOT = Path(__file__).resolve().parents[2]
KAGGLE_USER = "issacizrealdavis"
KAGGLE_DATASET = "issacizrealdavis/scbe-polly-training-data"
HF_DATASET = "issdandavis/scbe-aethermoore-training-data"

# ============================================================
# ROUND CONFIGS
# ============================================================
ROUNDS = {
    "covenantal": {
        "desc": "Covenantal null-space probes",
        "files": [
            "null_space_confidence_triggers.jsonl",
            "biblical_null_space_probes.jsonl",
            "sacred_eggs_triplets_sft.jsonl",
            "sacred_tongues_sft.jsonl",
            "governance_deep_v2.jsonl",
            "security_structure_deep_v1.jsonl",
            "null_space_dpo_pairs.jsonl",
            "genesis_seed.jsonl",
            "calibration_corpus_sft.jsonl",
        ],
        "hf_repo": "issdandavis/polly-covenantal-qwen-0.5b",
        "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
        "epochs": 2,
    },
    "deep-knowledge": {
        "desc": "Deep lore, personality, curriculum, frequency bundles",
        "files": [
            "polly_personality_deep_sft.jsonl",
            "polly_chat_seed.jsonl",
            "everweave_lore_sft.jsonl",
            "collegiate_curriculum_sft.jsonl",
            "quantum_frequency_bundles_sft.jsonl",
            "sacred_tongues_sft.jsonl",
            "trichromatic_spectrum_sft.jsonl",
            "phi_poincare_sft.jsonl",
            "polly_refusals_sft.jsonl",
        ],
        "hf_repo": "issdandavis/polly-deep-knowledge-qwen-0.5b",
        "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
        "epochs": 2,
    },
    "code-systems": {
        "desc": "Code patterns, architecture, typescript/python",
        "files": [
            "code_brushes_sft.jsonl",
            "code_substrate_l0_sft.jsonl",
            "architecture_explainer_v1.jsonl",
            "infrastructure_sft.jsonl",
            "typescript_docs_sft.jsonl",
            "python_docstrings_sft.jsonl",
            "copilot_replacement_v1.jsonl",
            "universal_code_primitives_sft.jsonl",
            "api_usage_pairs.jsonl",
        ],
        "hf_repo": "issdandavis/polly-code-systems-qwen-0.5b",
        "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
        "epochs": 2,
    },
    "adversarial": {
        "desc": "Adversarial defense, attack patterns, calibration",
        "files": [
            "advanced_adversarial_sft.jsonl",
            "adversarial_candy_sft.jsonl",
            "adversarial_storms_sft.jsonl",
            "entropic_defense_engine_sft.jsonl",
            "calibration_corpus_sft.jsonl",
            "test_behaviors_sft.jsonl",
            "autocorrection_behavior_sft.jsonl",
        ],
        "hf_repo": "issdandavis/polly-adversarial-qwen-0.5b",
        "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
        "epochs": 2,
    },
    "prime-r7": {
        "desc": "Multi-lang forge r7 — 14K instruction+relational+glucose pairs, 1.5B",
        "files": [
            "r7_instruction.jsonl",
            "r8_relational.jsonl",
            "r7_glucose_quiz.jsonl",
        ],
        "hf_repo": "issdandavis/polly-prime-r7-qwen-1.5b",
        "base_model": "Qwen/Qwen2.5-1.5B-Instruct",
        "epochs": 2,
    },
    "r8": {
        "desc": "r8 — 137K coding + tokenizer + spiral seal, 1.5B Coder",
        "files": [
            "code_master_sft.jsonl",
            "code_triangulated_sft.jsonl",
            "code_multiview_sft.jsonl",
            "lore_code_pairs_sft.jsonl",
            "tokenizer_master_class_sft.jsonl",
            "rosetta_code_primitives_sft.jsonl",
            "grok_code_sft.jsonl",
            "tongue_curriculum_v2.jsonl",
            "conlang_first_sft.jsonl",
            "tongue_primer_sft.jsonl",
            "universal_code_primitives_sft.jsonl",
            "code_brushes_sft.jsonl",
            "code_flow_sft.jsonl",
            "stage7_tongue_bundles.jsonl",
        ],
        "hf_repo": "issdandavis/polly-r8-qwen-0.5b",
        "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "epochs": 2,
    },
    "geoseal-stage6-repair-v7": {
        "desc": "GeoSeal coding-agent Stage 6 repair v7 - byte/hex, lane separation, fallback, re-advance",
        "files": [
            "bijective_codeflow_v1_train.sft.jsonl",
            "cross_tongue_dialogue_bijective_v1_train.sft.jsonl",
            "drill_langues_full_train.sft.jsonl",
            "command_lattice_seed_train.sft.jsonl",
            "binary_interpretation_matrix_v1.sft.jsonl",
            "geoseal_command_recall_v1.sft.jsonl",
            "geoseal_command_harmony_v1.sft.jsonl",
            "atomic_workflow_stage6_train.sft.jsonl",
            "atomic_workflow_stage6_repair_train.sft.jsonl",
        ],
        "hf_repo": "issdandavis/scbe-coding-agent-qwen-stage6-repair-v7-kaggle",
        "hf_dataset_repo": "issdandavis/scbe-coding-agent-sft-stage6-repair-v7",
        "kaggle_dataset": "issacizrealdavis/scbe-coding-agent-stage6-repair-v7",
        "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "epochs": 1,
        "batch_size": 1,
        "grad_accum": 16,
        "max_length": 768,
        "max_steps": 360,
        "learning_rate": 8e-5,
        "max_records": 3950,
        "lora_r": 32,
        "lora_alpha": 64,
        "lora_dropout": 0.05,
    },
    "coding-agent-smoke-v8": {
        "desc": "Coding-agent smoke v8 - bounded Kaggle run for adapter viability before full training",
        "files": [
            "bijective_codeflow_v1_train.sft.jsonl",
            "binary_interpretation_matrix_v1.sft.jsonl",
            "geoseal_command_recall_v1.sft.jsonl",
            "geoseal_command_harmony_v1.sft.jsonl",
            "atomic_workflow_stage6_train.sft.jsonl",
            "atomic_workflow_stage6_repair_train.sft.jsonl",
        ],
        "hf_repo": "issdandavis/scbe-coding-agent-qwen-smoke-v8-kaggle",
        "hf_dataset_repo": "issdandavis/scbe-coding-agent-sft-stage6-repair-v7",
        "kaggle_dataset": "issacizrealdavis/scbe-coding-agent-stage6-repair-v7",
        "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "epochs": 1,
        "batch_size": 1,
        "grad_accum": 16,
        "max_length": 768,
        "max_steps": 120,
        "learning_rate": 8e-5,
        "max_records": 1600,
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
    },
    "bijective-tongue-coder-v1": {
        "desc": "Pure bijective-tongue coder - code transport, cross-tongue dialogue, and tongue identity",
        "files": [
            "bijective_codeflow_v1_train.sft.jsonl",
            "cross_tongue_dialogue_bijective_v1_train.sft.jsonl",
            "drill_langues_full_train.sft.jsonl",
            "tongue_name_pairing_sft.jsonl",
            "coding_system_full_v1_train.sft.jsonl",
        ],
        "hf_repo": "issdandavis/scbe-bijective-tongue-coder-qwen-kaggle-v1",
        "hf_dataset_repo": "issdandavis/scbe-coding-agent-sft-stage6-repair-v7",
        "kaggle_dataset": "issacizrealdavis/scbe-coding-agent-stage6-repair-v7",
        "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "epochs": 1,
        "batch_size": 1,
        "grad_accum": 16,
        "max_length": 768,
        "max_steps": 260,
        "learning_rate": 8e-5,
        "max_records": 3200,
        "lora_r": 32,
        "lora_alpha": 64,
        "lora_dropout": 0.05,
    },
    "bijective-tongue-coder-v2": {
        "desc": (
            "Regularized bijective-tongue coder retrain. v1 was promotion-negative "
            "(overfit on drill_langues_full + catastrophic OOD forgetting). v2 drops "
            "drill_langues, adds 14.4% targeted anchor mix from v1's worst-regression "
            "OOD distributions, lowers LoRA capacity (r=8/alpha=16), raises dropout "
            "(0.1), and caps effective epochs at ~1.5. See artifacts/training_reports/"
            "bijective_tongue_coder_v2_PLAN.md for design rationale and promotion gate."
        ),
        "files": [
            # In-distribution (bijective lane) - 1336 rows / 85.6% of pool
            "bijective_codeflow_v1_train.sft.jsonl",
            "coding_system_full_v1_train.sft.jsonl",
            "cross_tongue_arithmetic_basics.sft.jsonl",
            "cross_tongue_string_basics.sft.jsonl",
            "cross_tongue_dialogue_bijective_v1_train.sft.jsonl",
            "tongue_name_pairing_sft.jsonl",
            # Anchor pool (counters worst-regression OOD) - 225 rows / 14.4% of pool
            "aligned_foundations_train.sft.jsonl",
            "atomic_workflow_stage6_train.sft.jsonl",
            "l13_governance_operation_sft.jsonl",
            "atomic_workflow_stage6_repair_train.sft.jsonl",
            "command_lattice_seed_train.sft.jsonl",
            "governance_deep_v2.jsonl",
            # NB: drill_langues_full deliberately excluded - dominated v1 (67.9% of pool)
            # NB: governance_security_boundary_eval_v1 deliberately excluded - eval-only
        ],
        # OOD-weighted in-training eval set. Tracks v1's worst-regression vectors so
        # EarlyStoppingCallback halts when OOD eval_loss stops improving (the failure
        # mode that produced v1's +803%/+559%/+299% holdout regressions). 154 rows.
        # governance_security_boundary_eval_v1 is held out of this set so the post-
        # promotion frozen-eval gate remains a clean unseen check.
        "eval_files": [
            "bijective_codeflow_v1_holdout.sft.jsonl",            # 104 rows  in-dist sanity
            "aligned_foundations_holdout.sft.jsonl",              #  15 rows  v1 +803%
            "atomic_workflow_stage6_repair_holdout.sft.jsonl",    #  10 rows  v1 +299%
            "atomic_workflow_stage6_holdout.sft.jsonl",           #  13 rows  v1 +136%
            "command_lattice_seed_holdout.sft.jsonl",             #   2 rows  v1 +559%
            "coding_system_full_v1_holdout.sft.jsonl",            #   8 rows  in-dist
            "cross_tongue_dialogue_bijective_v1_holdout.sft.jsonl", # 2 rows  in-dist
        ],
        "hf_repo": "issdandavis/scbe-bijective-tongue-coder-qwen-kaggle-v2",
        "hf_dataset_repo": "issdandavis/scbe-coding-agent-sft-stage6-repair-v7",
        "kaggle_dataset": "issacizrealdavis/scbe-coding-agent-stage6-repair-v7",
        "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "epochs": 1,
        "batch_size": 1,
        "grad_accum": 16,
        "max_length": 768,
        "max_steps": 150,
        "learning_rate": 5e-5,
        "max_records": 1700,
        "lora_r": 8,
        "lora_alpha": 16,
        "lora_dropout": 0.1,
        "early_stopping_patience": 3,
        "early_stopping_threshold": 0.0,
    },
    "bijective-tongue-coder-v2-format-repair": {
        "desc": (
            "Format-repair round for v51 contract collapse (0/106 unparseable_output, "
            "all 106 holdout rows emitted ```language code blocks instead of "
            "well_select(...) / tongue_shift(...) contract grammar). Root cause: v51's "
            "files list excluded bijective_dsl_v1_train.sft.jsonl - the file that "
            "carries the contract grammar. This round re-introduces it as PRIMARY "
            "contract source (939 rows) and oversamples contract_repair_v2_train via "
            "the kernel v5 repair-lane sampler (4x weight). From-base, not warm-start "
            "(kernel has no LoRA-load path). Eval against bijective_dsl_v4_holdout "
            "(boundary-clean: 0 idx overlap with contract_repair_v2 corpus). "
            "See artifacts/training_reports/bijective_tongue_coder_v2_format_repair_PLAN.md."
        ),
        "files": [
            # PRIMARY contract source - has well_select/tongue_shift grammar baked in
            "bijective_dsl_v1_train.sft.jsonl",        # 939 rows
            # Repair lane (oversampled via repair_lane_files / repair_lane_weight)
            "contract_repair_v2_train.sft.jsonl",      #  35 rows  -> 4x = 140 effective
            # Generalization slice - in-distribution code transport
            "bijective_codeflow_v1_train.sft.jsonl",   # subsampled via max_records
        ],
        "eval_files": [
            "bijective_dsl_v4_holdout.sft.jsonl",      #  69 rows  boundary-clean evaluator
            "contract_repair_v2_holdout.sft.jsonl",    #  11 rows  repair-specific sanity
        ],
        # v5 contract-aware levers
        "repair_lane_files": ["contract_repair_v2_train.sft.jsonl"],
        "repair_lane_weight": 4.0,
        "contract_eval_enabled": True,
        "contract_eval_steps": 30,
        "hf_repo": "issdandavis/scbe-bijective-tongue-coder-format-repair-qwen-kaggle",
        "hf_dataset_repo": "issdandavis/scbe-coding-agent-sft-stage6-repair-v7",
        "kaggle_dataset": "issacizrealdavis/scbe-coding-agent-stage6-repair-v7",
        "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "epochs": 1,
        "batch_size": 1,
        "grad_accum": 16,
        "max_length": 768,
        "max_steps": 120,
        "learning_rate": 5e-5,
        "max_records": 1100,
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.1,
        "early_stopping_patience": 3,
        "early_stopping_threshold": 0.0,
        "slug_override": "polly-auto-bijective-coder-v2-fmt-repair",
        "title_override": "Polly Auto bijective-coder-v2-fmt-repair",
    },
    "bijective-tongue-coder-v3": {
        "desc": (
            "v3 retry of the format-repair round after v2-format-repair was undermined "
            "by a Kaggle GPU lottery (P100 sm_60 instead of T4 sm_75) that tripped the "
            "kernel's silent CPU-fallback path (200 records / 30 steps / 0/25 contract "
            "parseable). v3 fixes that with require_gpu=True (hard-fail RuntimeError on "
            "sub-sm_70 so Kaggle re-queues), raises contract_eval_steps from 30 to 60 so "
            "the readout fires post-warmup, and consumes contract_repair_v3_train mined "
            "from v2-format-repair's failure log on bijective_dsl_v4_holdout. "
            "BOUNDARY NOTE: v3 train rows now include 18 idx from v4_holdout (24 mined, "
            "stratified split). v3 frozen-eval CANNOT use bijective_dsl_v4_holdout as a "
            "clean anchor; build a NEW holdout (bijective_dsl_v5_holdout) before "
            "promoting v3 adapter. From-base, not warm-start (kernel has no LoRA-load). "
            "See artifacts/training_reports/bijective_tongue_coder_v3_PLAN.md."
        ),
        "files": [
            # PRIMARY contract source - has well_select/tongue_shift grammar baked in
            "bijective_dsl_v1_train.sft.jsonl",        # 939 rows
            # Repair lane v3 - mined from v2-format-repair sample_diagnostics
            "contract_repair_v3_train.sft.jsonl",      #  18 rows  -> 4x = 72 effective
            # Generalization slice - in-distribution code transport
            "bijective_codeflow_v1_train.sft.jsonl",   # subsampled via max_records
        ],
        "eval_files": [
            # NOTE: v4_holdout is BURNED for v3 promotion eval (18 of its rows are now
            # in v3 train). Used here only as inline contract-eval slice for live signal.
            "bijective_dsl_v4_holdout.sft.jsonl",      #  69 rows
            "contract_repair_v3_holdout.sft.jsonl",    #   6 rows  repair-specific sanity
        ],
        # v5 contract-aware levers
        "repair_lane_files": ["contract_repair_v3_train.sft.jsonl"],
        "repair_lane_weight": 4.0,
        "contract_eval_enabled": True,
        "contract_eval_steps": 60,
        # v3-only: hard-fail on sub-sm_70 instead of silent CPU fallback
        "require_gpu": True,
        "hf_repo": "issdandavis/scbe-bijective-tongue-coder-v3-qwen-kaggle",
        "hf_dataset_repo": "issdandavis/scbe-coding-agent-sft-stage6-repair-v7",
        "kaggle_dataset": "issacizrealdavis/scbe-coding-agent-stage6-repair-v7",
        "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "epochs": 1,
        "batch_size": 1,
        "grad_accum": 16,
        "max_length": 768,
        "max_steps": 120,
        "learning_rate": 5e-5,
        "max_records": 1100,
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.1,
        "early_stopping_patience": 3,
        "early_stopping_threshold": 0.0,
        "slug_override": "polly-auto-bijective-coder-v3",
        "title_override": "Polly Auto bijective-coder-v3",
    },
    "binary-hex-lane-v1": {
        "desc": "Binary/hex lane - low-level substrate, bytes, ASCII, IEEE 754, and pillars",
        "files": [
            "binary_matrix_v2_full.sft.jsonl",
            "binary_pillars_v1.sft.jsonl",
            "binary_interpretation_matrix_v1.sft.jsonl",
            "blc_time_placement_v1.sft.jsonl",
        ],
        "hf_repo": "issdandavis/scbe-binary-hex-lane-qwen-kaggle-v1",
        "hf_dataset_repo": "issdandavis/scbe-coding-agent-sft-stage6-repair-v7",
        "kaggle_dataset": "issacizrealdavis/scbe-coding-agent-stage6-repair-v7",
        "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "epochs": 1,
        "batch_size": 1,
        "grad_accum": 16,
        "max_length": 768,
        "max_steps": 180,
        "learning_rate": 8e-5,
        "max_records": 1800,
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
    },
    "coding-approval-metrics-v1": {
        "desc": "Agentic coding approval metrics - overlooked preflight, safety, and merge-gate decisions",
        "files": [
            "coding_approval_metrics_v1.sft.jsonl",
            "honeycomb_choice_achievement_v1.sft.jsonl",
            "typescript_debug_harness_v1.sft.jsonl",
            "governance_security_boundary_eval_v1.sft.jsonl",
            "operator_agent_bus_extracted_v1_train.sft.jsonl",
            "colab_run_evidence_v1.sft.jsonl",
            "atomic_workflow_stage6_repair_train.sft.jsonl",
        ],
        "hf_repo": "issdandavis/scbe-coding-approval-metrics-qwen-kaggle-v1",
        "hf_dataset_repo": "issdandavis/scbe-coding-agent-sft-stage6-repair-v7",
        "kaggle_dataset": "issacizrealdavis/scbe-coding-agent-stage6-repair-v7",
        "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "epochs": 1,
        "batch_size": 1,
        "grad_accum": 16,
        "max_length": 768,
        "max_steps": 80,
        "learning_rate": 6e-5,
        "max_records": 900,
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
    },
    "coding-approval-metrics-v2": {
        "desc": "Agentic coding approval metrics v2 - executable repair records from benchmark failures",
        "files": [
            "coding_approval_metrics_v1.sft.jsonl",
            "honeycomb_choice_achievement_v1.sft.jsonl",
            "college_coding_choice_matrix_v1.sft.jsonl",
            "functional_coding_benchmark_repairs_v1.sft.jsonl",
            "typescript_debug_harness_v1.sft.jsonl",
            "operator_agent_bus_extracted_v1_train.sft.jsonl",
            "colab_run_evidence_v1.sft.jsonl",
            "atomic_workflow_stage6_repair_train.sft.jsonl",
        ],
        "eval_files": [
            "functional_coding_benchmark_repairs_v1_eval.sft.jsonl",
            "governance_security_boundary_eval_v1.sft.jsonl",
            "operator_agent_bus_extracted_v1_eval.sft.jsonl",
        ],
        "hf_repo": "issdandavis/scbe-coding-approval-metrics-qwen-kaggle-v2",
        "hf_dataset_repo": "issdandavis/scbe-coding-agent-sft-stage6-repair-v7",
        "kaggle_dataset": "issacizrealdavis/scbe-coding-agent-stage6-repair-v7",
        "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "epochs": 1,
        "batch_size": 1,
        "grad_accum": 16,
        "max_length": 768,
        "max_steps": 100,
        "learning_rate": 6e-5,
        "max_records": 950,
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        # Kaggle CLI currently rejects creating this fresh slug with
        # "Notebook not found". Reuse the existing v1 notebook shell while
        # keeping the injected round config and HF output repo as v2.
        "slug_override": "polly-auto-coding-approval-metrics-v1",
        "title_override": "Polly Auto: coding-approval-metrics-v1",
    },
    "full-3b": {
        "desc": "Full 3B model - all data, big GPU",
        "files": "__ALL__",
        "hf_repo": "issdandavis/scbe-polly-chat-v1",
        "base_model": "Qwen/Qwen2.5-3B-Instruct",
        "epochs": 2,
    },
    "dsl-synthesis-v1": {
        "desc": "L_dsl_synthesis Step 3 - 8-primitive DSL emission lane on top of v7 mix",
        "files": [
            "bijective_codeflow_v1_train.sft.jsonl",
            "cross_tongue_dialogue_bijective_v1_train.sft.jsonl",
            "drill_langues_full_train.sft.jsonl",
            "command_lattice_seed_train.sft.jsonl",
            "binary_interpretation_matrix_v1.sft.jsonl",
            "geoseal_command_recall_v1.sft.jsonl",
            "geoseal_command_harmony_v1.sft.jsonl",
            "atomic_workflow_stage6_train.sft.jsonl",
            "atomic_workflow_stage6_repair_train.sft.jsonl",
            "bijective_dsl_v1_train.sft.jsonl",
        ],
        "hf_repo": "issdandavis/scbe-coding-agent-qwen-dsl-synthesis-v1-kaggle",
        "hf_dataset_repo": "issdandavis/scbe-coding-agent-sft-dsl-synthesis-v1",
        "kaggle_dataset": "issacizrealdavis/scbe-coding-agent-stage6-repair-v7",
        "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "epochs": 1,
        "batch_size": 1,
        "grad_accum": 16,
        "max_length": 1024,
        "max_steps": 460,
        "learning_rate": 5e-5,
        "max_records": 4900,
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        "slug_override": "polly-auto-dsl-syn-v2",
    },
    "dsl-synthesis-v3-fast": {
        "desc": "L_dsl_synthesis fast bounded repair - finishes inside Kaggle wall clock with eval gate",
        "files": [
            "bijective_dsl_v1_train.sft.jsonl",
            "bijective_codeflow_v1_train.sft.jsonl",
            "cross_tongue_dialogue_bijective_v1_train.sft.jsonl",
            "atomic_workflow_stage6_repair_train.sft.jsonl",
            "command_lattice_seed_train.sft.jsonl",
            "binary_interpretation_matrix_v1.sft.jsonl",
        ],
        "eval_files": [
            "bijective_dsl_v1_holdout.sft.jsonl",
            "functional_coding_benchmark_repairs_v1_eval.sft.jsonl",
            "operator_agent_bus_extracted_v1_eval.sft.jsonl",
        ],
        "hf_repo": "issdandavis/scbe-coding-agent-qwen-dsl-synthesis-v3-fast-kaggle",
        "hf_dataset_repo": "issdandavis/scbe-coding-agent-sft-dsl-synthesis-v1",
        "kaggle_dataset": "issacizrealdavis/scbe-coding-agent-stage6-repair-v7",
        "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "epochs": 1,
        "batch_size": 1,
        "grad_accum": 16,
        "max_length": 512,
        "max_steps": 90,
        "learning_rate": 5e-5,
        "max_records": 1500,
        "lora_r": 8,
        "lora_alpha": 16,
        "lora_dropout": 0.1,
        "early_stopping_patience": 2,
        "early_stopping_threshold": 0.0,
        "eval_steps": 10,
        "save_steps": 10,
        "slug_override": "polly-auto-dsl-syn-v3-fast",
    },
    "regularized-coding-v8": {
        "desc": "Regularized coding model v8 - focused coding bucket with frozen eval",
        "files": [
            "regularized/coding_model/coding_model_train.regularized.jsonl",
        ],
        "eval_files": [
            "regularized/coding_model/coding_model_eval.regularized.jsonl",
        ],
        "hf_repo": "issdandavis/scbe-coding-agent-qwen-regularized-coding-v8-kaggle",
        "hf_dataset_repo": "issdandavis/scbe-training-regularized-20260426",
        "kaggle_dataset": "issacizrealdavis/scbe-coding-agent-stage6-repair-v7",
        "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "epochs": 1,
        "batch_size": 1,
        "grad_accum": 16,
        "max_length": 768,
        "max_steps": 120,
        "learning_rate": 5e-5,
        "max_records": 2755,
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
    },
    "aligned-foundations-helper-v1": {
        "desc": "Aligned foundations helper v1 - cross-stack instructor body with foundation bundle gate",
        "files": [
            "regularized/aligned_foundations/aligned_foundations_train.regularized.jsonl",
        ],
        "eval_files": [
            "regularized/aligned_foundations/aligned_foundations_eval.regularized.jsonl",
        ],
        "hf_repo": "issdandavis/scbe-aligned-foundations-helper-qwen-kaggle-v1",
        "hf_dataset_repo": "issdandavis/scbe-training-regularized-20260426",
        "kaggle_dataset": "issacizrealdavis/scbe-coding-agent-stage6-repair-v7",
        "base_model": "Qwen/Qwen2.5-7B-Instruct",
        "epochs": 1,
        "batch_size": 1,
        "grad_accum": 16,
        "max_length": 1024,
        "max_steps": 160,
        "learning_rate": 8e-5,
        "max_records": 1175,
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
    },
}


def resolve_slug(round_name: str) -> str:
    """Round-name-to-Kaggle-slug. Honors per-round slug_override (used to
    route around server-side stale state on a previously-created slug)."""
    cfg = ROUNDS.get(round_name) or {}
    return cfg.get("slug_override") or f"polly-auto-{round_name}"


GPU_CONFIGS = {
    "t4": {"accelerator": "gpu", "isGpuEnabled": True},
    "t4x2": {"accelerator": "gpu", "isGpuEnabled": True},  # Kaggle auto-assigns T4x2 for GPU
    "none": {"accelerator": "none", "isGpuEnabled": False},
}

# ARC submission kernel slug
ARC_KERNEL_SLUG = "arc-neurogolf-submit"
ARC_SUBMISSION_TEMPLATE = Path(__file__).parent / "arc_submission_kernel.py"
ARC_NEUROGOLF_DATASET = f"{KAGGLE_USER}/scbe-neurogolf-solver"
ARC_COMPETITION = "arc-prize-2026"


# ============================================================
# KERNEL SCRIPT GENERATOR
# ============================================================

TEMPLATE_PATH = Path(__file__).parent / "kernel_template.py"

def generate_kernel_script(round_name: str, config: dict) -> str:
    """Generate kernel script by injecting config into template."""

    # Determine batch size based on model size
    if "batch_size" in config and "grad_accum" in config and "max_length" in config:
        batch_size = int(config["batch_size"])
        grad_accum = int(config["grad_accum"])
        max_len = int(config["max_length"])
    elif "3B" in config["base_model"]:
        batch_size, grad_accum, max_len = 4, 4, 1024
    else:
        batch_size, grad_accum, max_len = 4, 8, 256

    kernel_cfg_dict = {
        "round": round_name,
        "base_model": config["base_model"],
        "hf_repo": config["hf_repo"],
        "files": config["files"],
        "eval_files": config.get("eval_files", []),
        "epochs": config["epochs"],
        "batch_size": batch_size,
        "grad_accum": grad_accum,
        "max_length": max_len,
        "hf_dataset_repo": config.get("hf_dataset_repo", HF_DATASET),
        "kaggle_dataset": config.get("kaggle_dataset", KAGGLE_DATASET),
        "max_steps": config.get("max_steps", -1),
        "learning_rate": config.get("learning_rate", 2e-4),
        "max_records": config.get("max_records", 10000),
        "lora_r": config.get("lora_r", 16),
        "lora_alpha": config.get("lora_alpha", 32),
        "lora_dropout": config.get("lora_dropout", 0.05),
        "early_stopping_patience": config.get("early_stopping_patience", 3),
        "early_stopping_threshold": config.get("early_stopping_threshold", 0.0),
        "eval_steps": config.get("eval_steps", 30),
        "save_steps": config.get("save_steps", 30),
    }

    # v5 contract-aware levers (kernel reads via CFG.get with safe defaults)
    for lever in (
        "repair_lane_files",
        "repair_lane_weight",
        "selector_token_weight",
        "weighted_ce_token_ids",
        "contract_eval_enabled",
        "contract_eval_steps",
        "require_gpu",
    ):
        if lever in config:
            kernel_cfg_dict[lever] = config[lever]

    kernel_config = json.dumps(kernel_cfg_dict)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.replace('"__INJECT_CONFIG_HERE__"', f"'{kernel_config}'")


# ============================================================
# KERNEL PUSH / POLL / PULL
# ============================================================

def create_kernel_dir(round_name: str, config: dict, gpu: str) -> Path:
    """Create a Kaggle kernel directory with metadata and script."""
    kernel_slug = resolve_slug(round_name)
    kernel_dir = REPO_ROOT / "artifacts" / "kaggle_kernels" / kernel_slug
    kernel_dir.mkdir(parents=True, exist_ok=True)

    # Write the training script
    script = generate_kernel_script(round_name, config)
    (kernel_dir / "script.py").write_text(script, encoding="utf-8")

    dataset_sources = [config.get("kaggle_dataset", KAGGLE_DATASET)]

    # Write kernel-metadata.json
    meta = {
        "id": f"{KAGGLE_USER}/{kernel_slug}",
        "title": config.get("title_override") or f"Polly Auto: {round_name}",
        "code_file": "script.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": gpu != "none",
        "enable_internet": True,
        "dataset_sources": dataset_sources,
        "competition_sources": [],
        "kernel_sources": [],
    }
    (kernel_dir / "kernel-metadata.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    return kernel_dir


def create_arc_kernel_dir(gpu: str) -> Path:
    """Create a Kaggle kernel directory for ARC Prize submission."""
    kernel_dir = REPO_ROOT / "artifacts" / "kaggle_kernels" / ARC_KERNEL_SLUG
    kernel_dir.mkdir(parents=True, exist_ok=True)

    # Copy the ARC submission script
    script = ARC_SUBMISSION_TEMPLATE.read_text(encoding="utf-8")
    (kernel_dir / "script.py").write_text(script, encoding="utf-8")

    # Write kernel-metadata.json
    gpu_conf = GPU_CONFIGS.get(gpu, GPU_CONFIGS["none"])
    meta = {
        "id": f"{KAGGLE_USER}/{ARC_KERNEL_SLUG}",
        "title": "ARC NeuroGolf Solver — SCBE",
        "code_file": "script.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": gpu_conf.get("isGpuEnabled", False),
        "enable_internet": False,
        "dataset_sources": [ARC_NEUROGOLF_DATASET],
        "competition_sources": [ARC_COMPETITION],
        "kernel_sources": [],
    }
    (kernel_dir / "kernel-metadata.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    return kernel_dir


def push_kernel(kernel_dir: Path, gpu: str = "none", accelerator_override: str | None = None) -> bool:
    """Push kernel to Kaggle."""
    print(f"Pushing kernel from {kernel_dir}...")
    cmd = ["kaggle", "kernels", "push", "-p", str(kernel_dir)]
    accelerator = accelerator_override or GPU_CONFIGS.get(gpu, GPU_CONFIGS["none"]).get("accelerator")
    if accelerator and accelerator != "none":
        cmd.extend(["--accelerator", accelerator])
    result = subprocess.run(
        cmd,
        capture_output=True, text=True,
    )
    print(result.stdout)
    combined = f"{result.stdout}\n{result.stderr}".lower()
    if result.returncode != 0 or "kernel push error" in combined or "maximum batch gpu session count" in combined:
        print(f"ERROR: {result.stderr or result.stdout}")
        return False
    return True


def check_status(kernel_slug: str) -> str:
    """Check kernel execution status."""
    ref = f"{KAGGLE_USER}/{kernel_slug}"
    result = subprocess.run(
        ["kaggle", "kernels", "status", ref],
        capture_output=True, text=True,
    )
    output = result.stdout.strip()
    # Parse status from output
    if "complete" in output.lower():
        return "complete"
    elif "running" in output.lower():
        return "running"
    elif "error" in output.lower() or "failed" in output.lower():
        return "error"
    elif "queued" in output.lower():
        return "queued"
    else:
        return output


def poll_until_done(kernel_slug: str, interval: int = 60, timeout: int = 43200) -> str:
    """Poll kernel status until complete or timeout (default 12h)."""
    ref = f"{KAGGLE_USER}/{kernel_slug}"
    elapsed = 0
    print(f"Polling {ref} every {interval}s (timeout {timeout//3600}h)...")

    while elapsed < timeout:
        status = check_status(kernel_slug)
        mins = elapsed // 60
        print(f"  [{mins:>4d}m] {status}")

        if status == "complete":
            print("Training complete!")
            return "complete"
        elif status == "error":
            print("Training FAILED.")
            return "error"

        time.sleep(interval)
        elapsed += interval

    print("TIMEOUT — kernel still running")
    return "timeout"


def pull_output(kernel_slug: str, dest: Path | None = None) -> Path:
    """Download kernel output files."""
    ref = f"{KAGGLE_USER}/{kernel_slug}"
    dest = dest or REPO_ROOT / "artifacts" / "kaggle_output" / kernel_slug
    dest.mkdir(parents=True, exist_ok=True)

    print(f"Pulling output from {ref} -> {dest}")
    result = subprocess.run(
        ["kaggle", "kernels", "output", ref, "-p", str(dest)],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"WARNING: {result.stderr}")

    return dest


def _run_kaggle(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["kaggle", *args], capture_output=True, text=True)


def list_mine_rows() -> list[dict[str, str]]:
    """Return parsed `kaggle kernels list --mine --csv` rows."""
    result = _run_kaggle(["kernels", "list", "--mine", "--csv"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return list(csv.DictReader(result.stdout.splitlines()))


def running_gpu_kernels() -> list[str]:
    """Return currently-running polly-auto kernel refs.

    Kaggle exposes the actual GPU-session limit only at push time. This helper
    gives a conservative preflight by checking our active polly-auto kernels.
    """
    refs: list[str] = []
    for row in list_mine_rows():
        ref = row.get("ref", "")
        if "polly-auto" not in ref:
            continue
        slug = ref.split("/", 1)[-1]
        status = check_status(slug)
        if status in {"running", "queued"}:
            refs.append(ref)
    return refs


def required_dataset_files(config: dict) -> list[str]:
    files = config.get("files", [])
    if files == "__ALL__":
        return []
    required = list(files)
    for name in config.get("eval_files", []):
        if name not in required:
            required.append(name)
    return required


def local_dataset_dir(config: dict) -> Path | None:
    dataset = str(config.get("kaggle_dataset") or "")
    if not dataset or "/" not in dataset:
        return None
    return REPO_ROOT / "artifacts" / "kaggle_datasets" / dataset.split("/", 1)[1]


def missing_local_dataset_files(config: dict) -> list[str]:
    root = local_dataset_dir(config)
    if root is None:
        return []
    return [name for name in required_dataset_files(config) if not (root / name).exists()]


def _hf_dataset_file_set(repo_id: str | None) -> set[str]:
    if not repo_id or HfApi is None:
        return set()
    try:
        return set(HfApi().list_repo_files(repo_id=repo_id, repo_type="dataset"))
    except Exception as exc:
        print(f"WARNING: HF dataset preflight failed for {repo_id}: {exc}")
        return set()


def missing_dataset_files(config: dict) -> list[str]:
    """Return files unavailable from either the local Kaggle mirror or HF dataset repo."""
    local_missing = set(missing_local_dataset_files(config))
    if not local_missing:
        return []

    hf_files = _hf_dataset_file_set(config.get("hf_dataset_repo"))
    if not hf_files:
        return sorted(local_missing)

    missing: list[str] = []
    for name in sorted(local_missing):
        candidates = (name, f"sft/{name}", f"training-data/sft/{name}")
        if not any(candidate in hf_files for candidate in candidates):
            missing.append(name)
    return missing


def default_gpu_session_limit() -> int:
    raw = os.environ.get("KAGGLE_GPU_SESSION_LIMIT", "2")
    try:
        limit = int(raw)
    except ValueError:
        return 2
    return max(0, limit)


def readiness_report(round_name: str, gpu: str, gpu_session_limit: int | None = None) -> dict:
    config = ROUNDS[round_name]
    active = running_gpu_kernels() if gpu != "none" else []
    session_limit = default_gpu_session_limit() if gpu_session_limit is None else max(0, gpu_session_limit)
    missing_local = missing_local_dataset_files(config)
    missing = missing_dataset_files(config)
    slug = resolve_slug(round_name)
    kernel_dir = create_kernel_dir(round_name, config, gpu)
    ready = not missing and (gpu == "none" or len(active) < session_limit)
    return {
        "round": round_name,
        "slug": slug,
        "gpu": gpu,
        "gpu_session_limit": session_limit if gpu != "none" else None,
        "ready": ready,
        "active_gpu_sessions": active,
        "gpu_slots_available": max(0, session_limit - len(active)) if gpu != "none" else None,
        "missing_dataset_files": missing,
        "missing_local_dataset_files": missing_local,
        "kernel_dir": str(kernel_dir),
        "hf_repo": config.get("hf_repo"),
        "hf_dataset_repo": config.get("hf_dataset_repo"),
        "files": required_dataset_files(config),
    }


def wait_until_ready(round_name: str, gpu: str, interval: int, timeout: int, gpu_session_limit: int) -> dict:
    """Poll readiness until the round can launch or timeout expires."""
    elapsed = 0
    while elapsed <= timeout:
        report = readiness_report(round_name, gpu, gpu_session_limit)
        print(
                f"[ready {elapsed//60:>4d}m] ready={report['ready']} "
                f"slots={report['gpu_slots_available']} missing={len(report['missing_dataset_files'])}"
        )
        if report["ready"]:
            return report
        time.sleep(interval)
        elapsed += interval
    raise TimeoutError(f"Timed out waiting for {round_name} readiness after {timeout}s")


def list_running():
    """Show status of all polly-auto kernels."""
    result = _run_kaggle(["kernels", "list", "--mine", "--csv"])
    print("\nYour Kaggle kernels:")
    print("-" * 80)
    for line in result.stdout.strip().split("\n"):
        if "polly-auto" in line.lower() or line.startswith("ref"):
            print(line)
    print("-" * 80)


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Kaggle zero-touch training automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent("""\
        Examples:
          # Launch covenantal training on Kaggle T4
          python scripts/kaggle_auto/launch.py --round covenantal

          # Launch and wait for completion
          python scripts/kaggle_auto/launch.py --round adversarial --poll

          # Launch full 3B run on T4x2
          python scripts/kaggle_auto/launch.py --round full-3b --gpu t4x2

          # Check status of running kernels
          python scripts/kaggle_auto/launch.py --status

          # Pull output from a completed kernel
          python scripts/kaggle_auto/launch.py --pull --round covenantal

          # Launch ALL rounds sequentially (each gets its own kernel)
          python scripts/kaggle_auto/launch.py --round all --poll
        """),
    )
    parser.add_argument("--round", choices=list(ROUNDS.keys()) + ["all"], metavar="ROUND")
    parser.add_argument("--gpu", choices=list(GPU_CONFIGS.keys()), default="t4")
    parser.add_argument(
        "--gpu-session-limit",
        type=int,
        default=default_gpu_session_limit(),
        help="Maximum active Kaggle GPU kernels allowed before launch preflight blocks "
        "(default: KAGGLE_GPU_SESSION_LIMIT env var or 2)",
    )
    parser.add_argument(
        "--accelerator",
        default=None,
        help="Raw Kaggle --accelerator override for paid-tier/CLI experiments; defaults to the --gpu profile",
    )
    parser.add_argument("--poll", action="store_true", help="Wait for completion")
    parser.add_argument("--poll-interval", type=int, default=120, help="Seconds between polls")
    parser.add_argument("--wait-ready", action="store_true", help="Wait for GPU slot/file readiness before launch")
    parser.add_argument("--wait-ready-timeout", type=int, default=21600, help="Seconds to wait for readiness")
    parser.add_argument("--status", action="store_true", help="Show running kernel status")
    parser.add_argument("--ready", action="store_true", help="Preflight a round: slots, local files, and kernel dir")
    parser.add_argument("--pull", action="store_true", help="Download output from completed kernel")
    parser.add_argument("--arc-submit", action="store_true", help="Push ARC Prize submission kernel")
    args = parser.parse_args()

    if args.status:
        list_running()
        return

    # ---- ARC submission mode ----
    if args.arc_submit:
        print(f"\n{'='*60}")
        print("ARC PRIZE SUBMISSION — NeuroGolf Solver")
        print(f"{'='*60}\n")

        kernel_dir = create_arc_kernel_dir(args.gpu)
        print(f"Kernel dir: {kernel_dir}")

        if not push_kernel(kernel_dir, args.gpu, args.accelerator):
            print("FAILED to push ARC kernel")
            sys.exit(1)

        print(f"Kernel pushed: kaggle.com/code/{KAGGLE_USER}/{ARC_KERNEL_SLUG}")

        if args.poll:
            status = poll_until_done(ARC_KERNEL_SLUG, interval=args.poll_interval)
            if status == "complete":
                dest = pull_output(ARC_KERNEL_SLUG)
                print(f"Output at: {dest}")
                # Check for submission.json
                sub = dest / "submission.json"
                if sub.exists():
                    data = json.loads(sub.read_text(encoding="utf-8"))
                    print(f"submission.json: {len(data)} tasks")
                else:
                    print("WARNING: submission.json not found in output")
        else:
            print(f"\nKernel running. Check status with:")
            print(f"  python scripts/kaggle_auto/launch.py --status")
            print(f"  kaggle kernels status {KAGGLE_USER}/{ARC_KERNEL_SLUG}")
        return

    if not args.round:
        parser.error("--round is required (unless using --status or --arc-submit)")

    if args.ready:
        if args.round == "all":
            parser.error("--ready requires one concrete --round")
        report = readiness_report(args.round, args.gpu, args.gpu_session_limit)
        print(json.dumps(report, indent=2))
        return

    if args.pull:
        slug = resolve_slug(args.round)
        pull_output(slug)
        return

    # Handle --round all
    rounds_to_run = list(ROUNDS.keys()) if args.round == "all" else [args.round]

    for round_name in rounds_to_run:
        config = ROUNDS[round_name]
        slug = resolve_slug(round_name)

        print(f"\n{'='*60}")
        print(f"LAUNCHING: {round_name} — {config['desc']}")
        print(f"  Model: {config['base_model']}")
        print(f"  GPU:   {args.gpu}")
        print(f"  GPU session limit: {args.gpu_session_limit}")
        print(f"  HF:    {config['hf_repo']}")
        print(f"{'='*60}\n")

        # Create kernel directory
        kernel_dir = create_kernel_dir(round_name, config, args.gpu)
        print(f"Kernel dir: {kernel_dir}")

        if args.wait_ready:
            try:
                wait_until_ready(
                    round_name,
                    args.gpu,
                    args.poll_interval,
                    args.wait_ready_timeout,
                    args.gpu_session_limit,
                )
            except TimeoutError as exc:
                print(f"FAILED preflight: {exc}")
                continue

        missing = missing_dataset_files(config)
        if missing:
            print(f"FAILED preflight: missing dataset files locally and on HF: {', '.join(missing)}")
            continue

        if args.gpu != "none":
            active = running_gpu_kernels()
            if len(active) >= args.gpu_session_limit:
                print(
                    "FAILED preflight: configured Kaggle GPU session limit is already full "
                    f"({len(active)}/{args.gpu_session_limit})."
                )
                for ref in active:
                    print(f"  active: {ref}")
                continue

        # Push to Kaggle
        if not push_kernel(kernel_dir, args.gpu, args.accelerator):
            print(f"FAILED to push {round_name} — skipping")
            continue

        print(f"Kernel pushed: kaggle.com/code/{KAGGLE_USER}/{slug}")

        if args.poll:
            status = poll_until_done(slug, interval=args.poll_interval)
            if status == "complete":
                dest = pull_output(slug)
                print(f"Output at: {dest}")
            elif status == "error":
                print(f"Check logs: kaggle kernels output {KAGGLE_USER}/{slug}")

            # If running all rounds, wait between them (Kaggle limits concurrent GPU kernels)
            if len(rounds_to_run) > 1:
                print("Waiting 30s before next round...")
                time.sleep(30)
        else:
            print(f"\nKernel running. Check status with:")
            print(f"  python scripts/kaggle_auto/launch.py --status")
            print(f"  kaggle kernels status {KAGGLE_USER}/{slug}")
            print(f"\nPull output when done:")
            print(f"  python scripts/kaggle_auto/launch.py --pull --round {round_name}")


if __name__ == "__main__":
    main()
