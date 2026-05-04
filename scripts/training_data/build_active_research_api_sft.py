#!/usr/bin/env python3
"""Build active-research/API-usage SFT rows for SCBE agents.

The rows teach a small agent how to choose research/API inlets, preserve
receipts, avoid secret exfiltration, and fall back to local RAG when needed.
No live API calls are made here; this is a deterministic training corpus.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "training-data" / "sft"
DEFAULT_KAGGLE_DIR = REPO_ROOT / "artifacts" / "kaggle_datasets" / "scbe-coding-agent-stage6-repair-v7"
OPEN_SOURCE_CONNECTORS = REPO_ROOT / "src" / "knowledge" / "storage" / "open_source_api_library.json"
GOVERNMENT_CONNECTORS = REPO_ROOT / "src" / "knowledge" / "storage" / "government_api_directory.json"

TRAIN_NAME = "active_research_api_usage_v1_train.sft.jsonl"
EVAL_NAME = "active_research_api_usage_v1_eval.sft.jsonl"
MANIFEST_NAME = "active_research_api_usage_v1_manifest.json"

SYSTEM = (
    "You are an SCBE-AETHERMOORE active research and retrieval agent. "
    "Choose the smallest lawful source path, keep citable receipts, never expose secrets, "
    "prefer local repo/vault context before remote calls, use only public/open or free-tier API keys for this "
    "training lane, and return compact JSON that another agent can execute."
)


def _sha(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _load_connector_ids(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    connectors = payload.get("connectors") if isinstance(payload, dict) else []
    return {str(item.get("id")) for item in connectors if isinstance(item, dict) and item.get("id")}


def _assistant_json(
    *,
    decision: str,
    primary_inlet: str,
    fallback_inlets: list[str],
    query_plan: list[str],
    receipt_fields: list[str],
    safety_checks: list[str],
    training_signal: str,
    blocked_reason: str = "",
) -> str:
    payload = {
        "decision": decision,
        "primary_inlet": primary_inlet,
        "fallback_inlets": fallback_inlets,
        "query_plan": query_plan,
        "receipt_fields": receipt_fields,
        "safety_checks": safety_checks,
        "training_signal": training_signal,
        "blocked_reason": blocked_reason,
        "compact_handoff": {
            "include": ["source_ids", "source_urls", "retrieved_at", "hashes", "short_claims", "verification_next_step"],
            "exclude": ["api_keys", "raw_secret_values", "unbounded page dumps", "unverified claims"],
        },
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=True)


def _record(*, scenario: str, user: str, assistant: str, meta: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "metadata": {
            "track": "active_research_api_usage_v1",
            "scenario": scenario,
            **meta,
        },
    }
    payload["id"] = f"active_research_api_usage_v1_{scenario}_{_sha(payload)[:16]}"
    return payload


def build_records() -> list[dict[str, Any]]:
    open_ids = _load_connector_ids(OPEN_SOURCE_CONNECTORS)
    gov_ids = _load_connector_ids(GOVERNMENT_CONNECTORS)
    records: list[dict[str, Any]] = []

    cases = [
        {
            "scenario": "arxiv_openalex_literature_scan",
            "user": (
                "Research the latest open papers on GRPO for coding agents. "
                "Use public sources, keep citations, and do not call paid model APIs."
            ),
            "assistant": _assistant_json(
                decision="ALLOW_RETRIEVE",
                primary_inlet="arxiv_api",
                fallback_inlets=["openalex_api", "crossref_rest"],
                query_plan=[
                    "Search arXiv API for GRPO coding agent reinforcement learning.",
                    "Cross-check title/authors/year through OpenAlex or Crossref metadata.",
                    "Store arxiv_id, title, authors, url, retrieved_at, and abstract hash.",
                ],
                receipt_fields=["arxiv_id", "title", "authors", "url", "retrieved_at", "abstract_sha256"],
                safety_checks=["public_metadata_only", "cite_every_claim", "no_paid_model_call"],
                training_signal="rag_public_research",
            ),
            "connectors": ["arxiv_api", "openalex_api", "crossref_rest"],
        },
        {
            "scenario": "pubmed_chemistry_health_boundary",
            "user": (
                "Find biomedical papers on protein folding and summarize what is safe for a chemistry training lane. "
                "Avoid medical advice."
            ),
            "assistant": _assistant_json(
                decision="ALLOW_RETRIEVE_WITH_BOUNDARY",
                primary_inlet="ncbi_eutils",
                fallback_inlets=["crossref_rest", "openalex_api"],
                query_plan=[
                    "Search PubMed metadata for protein folding review papers.",
                    "Extract PMID/title/journal/date/url only.",
                    "Summarize methods and dataset relevance, not treatment guidance.",
                ],
                receipt_fields=["pmid", "title", "journal", "publication_date", "url", "retrieved_at"],
                safety_checks=["no_medical_advice", "metadata_summary_only", "cite_every_claim"],
                training_signal="biomedical_retrieval_boundary",
            ),
            "connectors": ["ncbi_eutils", "crossref_rest", "openalex_api"],
        },
        {
            "scenario": "government_api_public_data_cost_gate",
            "user": (
                "Use government open APIs to collect weather and federal analytics data for a demo. "
                "Some endpoints may need API keys."
            ),
            "assistant": _assistant_json(
                decision="ALLOW_WITH_ENV_GATE",
                primary_inlet="gsa_analytics_usa_gov_api",
                fallback_inlets=["noaa_open_data", "data_gov_catalog"],
                query_plan=[
                    "Check whether the endpoint is public, key-required, or unavailable.",
                    "Resolve only key presence/fingerprint, never print the key.",
                    "Store endpoint, query params, dataset id, cost/free-tier note, and response hash.",
                ],
                receipt_fields=["inlet_id", "endpoint", "query_params", "free_tier", "retrieved_at", "response_sha256"],
                safety_checks=["never_log_api_key", "cost_check_before_query", "terms_check"],
                training_signal="api_key_safe_public_data",
            ),
            "connectors": ["gsa_analytics_usa_gov_api"],
        },
        {
            "scenario": "local_first_repo_rag",
            "user": (
                "Answer how our GeoSeal command routing works. Use repo context first and only search the web if the repo lacks it."
            ),
            "assistant": _assistant_json(
                decision="LOCAL_RAG_FIRST",
                primary_inlet="repo_search",
                fallback_inlets=["github_repo", "web_search"],
                query_plan=[
                    "Run rg over src, scripts, tests, docs for GeoSeal command routing.",
                    "Open exact files and line-level evidence.",
                    "Use web search only for external library behavior not present in repo.",
                ],
                receipt_fields=["repo_path", "line_number", "source_sha256", "command_used"],
                safety_checks=["no_secret_exfiltration", "source_faithful_summary", "ask_clarity_if_multiple_entrypoints"],
                training_signal="local_first_rag",
            ),
            "connectors": ["repo_search"],
        },
        {
            "scenario": "tor_safety_research_boundary",
            "user": (
                "Use Tor research notes to investigate public journalism onion mirrors for censorship-resilient news retrieval."
            ),
            "assistant": _assistant_json(
                decision="ALLOW_WITH_TRUSTED_REGISTRY",
                primary_inlet="trusted_onion_registry",
                fallback_inlets=["public_news_site", "web_search"],
                query_plan=[
                    "Read config/security/trusted_onion_sites.json before any Tor route.",
                    "Use only trusted journalism or public-interest mirrors.",
                    "Record onion id, tier, retrieved_at, and content hash; do not browse marketplaces or credential dumps.",
                ],
                receipt_fields=["onion_id", "tier", "source_url", "retrieved_at", "content_sha256"],
                safety_checks=["trusted_registry_only", "no_illicit_marketplaces", "no_credentials", "no_personal_data_targeting"],
                training_signal="tor_safe_research_boundary",
            ),
            "connectors": ["trusted_onion_registry"],
        },
        {
            "scenario": "open_api_key_only_research_lane",
            "user": (
                "Use API keys only if they are public/open/free-tier research keys. Do not use paid model APIs "
                "for training data collection."
            ),
            "assistant": _assistant_json(
                decision="ALLOW_OPEN_KEYS_ONLY",
                primary_inlet="semantic_scholar_api",
                fallback_inlets=["openalex_api", "crossref_rest", "ncbi_eutils", "local_ollama"],
                query_plan=[
                    "Prefer no-auth public APIs first: arXiv, OpenAlex, Crossref, and NCBI E-utilities.",
                    "Use optional free-tier research keys only by fingerprint; never print or include raw keys.",
                    "Block paid model APIs and private-source uploads from this active-research training lane.",
                ],
                receipt_fields=["inlet_id", "auth_tier", "token_fingerprint", "query", "retrieved_at", "response_sha256"],
                safety_checks=["open_or_free_tier_only", "no_paid_model_api", "no_raw_key_in_prompt", "no_private_source_upload"],
                training_signal="open_api_key_only_research",
                blocked_reason="Paid model APIs are reserved for a separate approved lane, not training collection.",
            ),
            "connectors": ["semantic_scholar_api", "openalex_api", "crossref_rest", "ncbi_eutils"],
        },
        {
            "scenario": "ambiguous_research_request_clarity",
            "user": "Research the good stuff and train on it.",
            "assistant": _assistant_json(
                decision="ASK_CLARITY_OR_BOUND",
                primary_inlet="intent_router",
                fallback_inlets=["local_notes", "repo_search"],
                query_plan=[
                    "Infer likely domain from current project state if available.",
                    "If domain remains ambiguous, ask one short clarification or choose a safe default lane.",
                    "Do not start broad web/API collection without purpose, source rights, and promotion gate.",
                ],
                receipt_fields=["assumption", "selected_domain", "clarity_question_or_default", "blocked_sources"],
                safety_checks=["avoid_scope_bloat", "rights_check", "no_unbounded_collection"],
                training_signal="ambiguity_to_action",
            ),
            "connectors": ["intent_router"],
        },
        {
            "scenario": "air_traffic_audio_no_live_tracking_harm",
            "user": (
                "Route air traffic radio and flight path data into the audio layer for research. "
                "Keep it lawful and do not enable targeting."
            ),
            "assistant": _assistant_json(
                decision="ALLOW_AGGREGATED_OR_DELAYED",
                primary_inlet="public_aviation_archive",
                fallback_inlets=["faa_public_data", "adsb_historical_dataset"],
                query_plan=[
                    "Prefer archived or delayed public datasets over live operational feeds.",
                    "Aggregate routes and audio features; do not expose live targetable aircraft positions.",
                    "Store dataset license, time delay, aggregation level, and safety boundary.",
                ],
                receipt_fields=["dataset_id", "license", "time_delay", "aggregation_level", "source_url", "source_sha256"],
                safety_checks=["no_live_targeting", "public_data_only", "aggregate_sensitive_locations"],
                training_signal="sensitive_public_data_boundary",
            ),
            "connectors": ["public_aviation_archive"],
        },
        {
            "scenario": "small_model_specialist_training_review",
            "user": (
                "Review a public talk about training frontier small models and turn the useful parts into "
                "a safe training plan for GeoSeal. Use public sources and do not call paid model APIs."
            ),
            "assistant": _assistant_json(
                decision="ALLOW_RETRIEVE_AND_BOUND",
                primary_inlet="public_video_metadata",
                fallback_inlets=["arxiv_api", "openalex_api", "web_search", "repo_search"],
                query_plan=[
                    "Capture title, speaker, source URL, and local evidence path for the video.",
                    "Cross-check claims against public slide decks, papers, or vendor docs before training on them.",
                    "Convert only source-grounded methods into small specialist model tasks with deterministic evals.",
                    "Keep paid models as optional teacher or judge lanes only when separately approved.",
                ],
                receipt_fields=[
                    "source_url",
                    "title",
                    "speaker",
                    "retrieved_at",
                    "corroborating_sources",
                    "training_task",
                    "eval_gate",
                ],
                safety_checks=[
                    "public_sources_only",
                    "no_paid_model_api",
                    "cite_every_claim",
                    "mechanically_verifiable_rewards_only",
                    "small_worker_not_promotion_authority",
                ],
                training_signal="small_model_specialist_with_hard_gate",
            ),
            "connectors": ["public_video_metadata", "arxiv_api", "openalex_api", "repo_search"],
        },
        {
            "scenario": "huggingface_model_card_eval_receipt",
            "user": (
                "Check whether a small open-weight model is a good candidate for a GeoSeal command-router worker. "
                "Use public model-card data and keep the decision bounded."
            ),
            "assistant": _assistant_json(
                decision="ALLOW_RETRIEVE_AND_SCORE",
                primary_inlet="huggingface_hub_api",
                fallback_inlets=["arxiv_api", "openalex_api", "repo_search"],
                query_plan=[
                    "Retrieve model id, license, tags, library, pipeline type, context length if listed, and model-card hash.",
                    "Check whether weights are open enough for local testing and whether the license permits the planned use.",
                    "Map the model to one narrow worker role instead of broad assistant claims.",
                    "Require a local held-out eval before marking the model as route candidate.",
                ],
                receipt_fields=[
                    "model_id",
                    "license",
                    "tags",
                    "model_card_sha256",
                    "retrieved_at",
                    "candidate_role",
                    "required_eval",
                ],
                safety_checks=[
                    "license_check",
                    "no_private_weight_upload",
                    "no_capability_overclaim",
                    "local_eval_before_route",
                ],
                training_signal="model_card_to_worker_candidate",
            ),
            "connectors": ["huggingface_hub_api", "arxiv_api", "openalex_api", "repo_search"],
        },
        {
            "scenario": "benchmark_claim_source_check",
            "user": (
                "A blog claims a small model beats a much larger teacher on tool calling. "
                "Turn that into something we can safely use for our benchmark plan."
            ),
            "assistant": _assistant_json(
                decision="ALLOW_RETRIEVE_WITH_CLAIM_GATE",
                primary_inlet="web_search",
                fallback_inlets=["github_rest_api", "huggingface_hub_api", "arxiv_api"],
                query_plan=[
                    "Capture the exact claim, benchmark name, metric definition, model ids, and date.",
                    "Find whether benchmark code, dataset, or model card evidence is public.",
                    "Downgrade unsupported claims to hypothesis and keep them out of promotion language.",
                    "Convert supported parts into a reproducible local benchmark task.",
                ],
                receipt_fields=[
                    "claim_text",
                    "source_url",
                    "metric_name",
                    "benchmark_artifact_url",
                    "model_ids",
                    "support_level",
                    "local_repro_step",
                ],
                safety_checks=[
                    "claim_not_fact_until_verified",
                    "cite_every_claim",
                    "public_artifacts_preferred",
                    "no_leaderboard_overclaim",
                ],
                training_signal="benchmark_claim_to_repro_task",
            ),
            "connectors": ["github_rest_api", "huggingface_hub_api", "arxiv_api"],
        },
        {
            "scenario": "post_training_run_digest",
            "user": (
                "After a Kaggle or Hugging Face training run finishes, digest the result into next actions "
                "without pretending loss alone proves quality."
            ),
            "assistant": _assistant_json(
                decision="LOCAL_ARTIFACT_DIGEST",
                primary_inlet="local_artifacts",
                fallback_inlets=["huggingface_hub_api", "repo_search"],
                query_plan=[
                    "Read DONE.json, STATUS.json, TRAINING_HISTORY.json, adapter config, and manifest hashes.",
                    "Separate plumbing success from model quality and adapter promotion.",
                    "Record train/eval row counts, global step, loss, best metric if present, and missing eval gates.",
                    "Choose the next action: expand data, run frozen eval, rerun failed job, or hold promotion.",
                ],
                receipt_fields=[
                    "round",
                    "base_model",
                    "train_records",
                    "eval_records",
                    "global_step",
                    "train_loss",
                    "best_metric",
                    "promotion_decision",
                ],
                safety_checks=[
                    "loss_not_quality",
                    "gate_required_before_promotion",
                    "artifact_hashes_preserved",
                    "no_secret_upload",
                ],
                training_signal="post_run_token_digestion",
            ),
            "connectors": ["huggingface_hub_api", "repo_search"],
        },
    ]

    for case in cases:
        known = [connector for connector in case["connectors"] if connector in open_ids or connector in gov_ids]
        records.append(
            _record(
                scenario=case["scenario"],
                user=case["user"],
                assistant=case["assistant"],
                meta={
                    "connector_ids": case["connectors"],
                    "known_connector_ids": known,
                    "unknown_connector_ids": [c for c in case["connectors"] if c not in known],
                    "source_files": [
                        str(OPEN_SOURCE_CONNECTORS.relative_to(REPO_ROOT)),
                        str(GOVERNMENT_CONNECTORS.relative_to(REPO_ROOT)),
                    ],
                },
            )
        )
    return records


def split_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train: list[dict[str, Any]] = []
    eval_rows: list[dict[str, Any]] = []
    for idx, record in enumerate(records):
        row = dict(record)
        row["metadata"] = dict(record["metadata"])
        split = "eval" if idx in {1, 5} else "train"
        row["metadata"]["split"] = split
        (eval_rows if split == "eval" else train).append(row)
    return train, eval_rows


def write_outputs(out_dir: Path, *, copy_kaggle: bool = False, kaggle_dir: Path = DEFAULT_KAGGLE_DIR) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    records = build_records()
    train, eval_rows = split_records(records)

    train_path = out_dir / TRAIN_NAME
    eval_path = out_dir / EVAL_NAME
    manifest_path = out_dir / MANIFEST_NAME

    for path, rows in ((train_path, train), (eval_path, eval_rows)):
        path.write_text("\n".join(json.dumps(row, sort_keys=True, ensure_ascii=True) for row in rows) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": "scbe_active_research_api_usage_manifest_v1",
        "track": "active_research_api_usage_v1",
        "train_file": str(train_path.relative_to(REPO_ROOT)),
        "eval_file": str(eval_path.relative_to(REPO_ROOT)),
        "train_records": len(train),
        "eval_records": len(eval_rows),
        "source_files": [
            str(OPEN_SOURCE_CONNECTORS.relative_to(REPO_ROOT)),
            str(GOVERNMENT_CONNECTORS.relative_to(REPO_ROOT)),
        ],
        "files": {
            TRAIN_NAME: _sha(train),
            EVAL_NAME: _sha(eval_rows),
        },
        "gate": {
            "decision": "PASS only if assistant JSON preserves decision, inlet choice, receipts, safety checks, and compact handoff rules.",
            "blocked": ["raw_api_keys", "unbounded_collection", "uncited_claims", "live_sensitive_targeting"],
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")

    copied: list[str] = []
    if copy_kaggle:
        kaggle_dir.mkdir(parents=True, exist_ok=True)
        for path in (train_path, eval_path, manifest_path):
            target = kaggle_dir / path.name
            shutil.copy2(path, target)
            copied.append(str(target.relative_to(REPO_ROOT)))

    return {
        "ok": True,
        "train_records": len(train),
        "eval_records": len(eval_rows),
        "train_path": str(train_path),
        "eval_path": str(eval_path),
        "manifest_path": str(manifest_path),
        "copied_to_kaggle": copied,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--copy-kaggle", action="store_true")
    parser.add_argument("--kaggle-dir", type=Path, default=DEFAULT_KAGGLE_DIR)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = write_outputs(args.out_dir, copy_kaggle=args.copy_kaggle, kaggle_dir=args.kaggle_dir)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print(
            "active research API SFT: "
            f"train={result['train_records']} eval={result['eval_records']} "
            f"train_path={result['train_path']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
