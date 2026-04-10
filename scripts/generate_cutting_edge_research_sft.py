#!/usr/bin/env python3
"""
Cutting-Edge Research Provenance SFT Generator

For each PhD research domain mapped from Codex skills:
  - 2 independent researcher agents pull arXiv thesis + supporting papers
  - Each agent explains WHY they picked what they picked (retrieval rationale)
  - Source verification chain traces institutional lineage
  - Geo-education mapping locates knowledge geographically + historically
  - Output carries full provenance metadata for HF training evaluation

Output schema per record:
{
  "id": "ce-{domain}-{seq}",
  "instruction": "...",
  "response": "...",
  "tier": "cutting_edge",
  "domain": "multi_agent_coordination",
  "arxiv_thesis": {
    "id": "2401.12345",
    "title": "...",
    "authors": ["..."],
    "abstract": "...",
    "categories": ["cs.MA"]
  },
  "supporting_papers": [
    {"id": "...", "title": "...", "relevance": "...", "retrieval_rationale": "..."}
  ],
  "retrieval_evaluation": {
    "agent_id": "researcher_A|researcher_B",
    "search_strategy": "how they searched",
    "selection_rationale": "WHY this thesis over alternatives",
    "confidence": 0.0-1.0,
    "alternatives_considered": ["..."]
  },
  "source_verification": {
    "cross_references": ["paper X cites Y which validates Z"],
    "citation_chain_depth": 3,
    "verification_status": "verified|partial|unverified"
  },
  "geo_education_map": {
    "institution": "MIT CSAIL",
    "country": "USA",
    "region": "New England",
    "coordinates": [42.3601, -71.0942],
    "research_tradition": "AI Lab lineage from Minsky/McCarthy -> Brooks -> modern multi-agent",
    "regional_history": "Brief history of the institution's research contributions in this domain",
    "knowledge_strata": "foundational|intermediate|frontier"
  },
  "skill_sources": ["skill1", "skill2"],
  "category": "...",
  "source_type": "cutting_edge_research_provenance",
  "generated_at": "..."
}
"""

import json
import os
from datetime import datetime, timezone

DOMAINS_FILE = "scripts/cutting_edge_research_domains.json"
STUBS_FILE = "training-data/sft/codex_skill_tutorials_cutting_edge_stubs.jsonl"
OUTPUT_DIR = "training-data/sft"

# Instruction templates per domain — each domain gets multiple angles
INSTRUCTION_TEMPLATES = {
    "thesis_analysis": [
        "Find and analyze a key arXiv paper on {topic}. Explain its thesis, methodology, and how it connects to {scbe_concept}. Trace the paper's institutional origin and the research tradition it belongs to.",
        "What is the current state-of-the-art in {topic}? Identify a foundational paper, its supporting evidence from at least 2 other papers, and map the geographic distribution of this research community.",
    ],
    "retrieval_challenge": [
        "You are given the task of finding the most relevant arXiv paper for implementing {scbe_concept} in a production AI safety system. Describe your search strategy, what you found, WHY you selected it over alternatives, and how confident you are in the selection.",
        "Two researchers independently searched for papers on {topic}. Researcher A picked [PAPER_A] and Researcher B picked [PAPER_B]. Compare their choices: which better supports {scbe_concept} and why? What does the disagreement reveal about the problem space?",
    ],
    "geo_provenance": [
        "Trace the intellectual lineage of research on {topic} from its geographic origin to current frontier labs. Map at least 3 institutions across different countries, noting how the research evolved as it moved between regions.",
        "How does the geographic distribution of {topic} research reflect different AI safety philosophies? Compare approaches from US labs, European institutions, and Asian research centers.",
    ],
    "cross_verification": [
        "Given a claim that '{scbe_concept}' is novel, find the closest prior art on arXiv. Build a citation chain showing: (1) what existed before, (2) what SCBE adds, (3) verification through independent reproduction or formal proof.",
        "Design a source verification protocol for validating research claims about {topic}. Include: primary source check, citation chain audit, institutional credibility assessment, and geographic bias detection.",
    ],
}

# Map domains to SCBE concepts and search topics
DOMAIN_TOPICS = {
    "multi_agent_coordination": {
        "topic": "multi-agent communication protocols with safety guarantees",
        "scbe_concept": "SCBE cross-talk governance packets with hyperbolic trust distance",
    },
    "autonomous_web_agents": {
        "topic": "autonomous web navigation agents with safety constraints",
        "scbe_concept": "AetherBrowser semantic antivirus membrane and HYDRA swarm browsing",
    },
    "ai_safety_governance": {
        "topic": "formal AI safety governance and adversarial robustness",
        "scbe_concept": "14-layer harmonic wall pipeline with Poincare ball containment",
    },
    "federated_model_training": {
        "topic": "federated fine-tuning with governance and quality gates",
        "scbe_concept": "SCBE Ouroboros training loop with 3-specialty heads and Sacred Tongue tokenization",
    },
    "knowledge_graph_rag": {
        "topic": "knowledge graph construction and retrieval-augmented generation",
        "scbe_concept": "SCBE 21D canonical state embedding with polyhedral classification for knowledge retrieval",
    },
    "geometric_security": {
        "topic": "hyperbolic geometry for adversarial defense and trust modeling",
        "scbe_concept": "Poincare ball trust rings, harmonic wall H(d,pd), and polyhedral confinement",
    },
    "workflow_orchestration": {
        "topic": "self-healing CI/CD pipelines with autonomous agent orchestration",
        "scbe_concept": "SCBE n8n bridge workflows with governance-stamped deployment gates",
    },
    "content_generation_publishing": {
        "topic": "multi-platform AI content generation with quality assurance",
        "scbe_concept": "SCBE content buffer with governance scanning and multi-platform publishing",
    },
    "creative_ai_narrative": {
        "topic": "computational narrative generation and interactive fiction",
        "scbe_concept": "Spiralverse canon engine with Sacred Tongue encoding and developmental psychology model",
    },
    "ai_commerce_monetization": {
        "topic": "AI-driven autonomous commerce and business automation",
        "scbe_concept": "SCBE monetization pipeline with Stripe/Shopify governance integration",
    },
    "mobile_edge_computing": {
        "topic": "edge AI agents on mobile devices with resource constraints",
        "scbe_concept": "SCBE phone lane operations with emulator-based governance testing",
    },
    "self_improving_systems": {
        "topic": "self-improving AI systems and autonomous skill acquisition",
        "scbe_concept": "SCBE skill vault self-management with meridian flush and session corkscrew",
    },
    "frontend_design_systems": {
        "topic": "AI-assisted UI generation and design system automation",
        "scbe_concept": "Living codex browser builder with Figma-to-code governance pipeline",
    },
    "game_ai_simulation": {
        "topic": "game-theoretic multi-agent simulation and training environments",
        "scbe_concept": "Tuxemon-SCBE bridge with battle telemetry and AI NPC governance",
    },
    "secure_credential_systems": {
        "topic": "decentralized identity and post-quantum credential management",
        "scbe_concept": "Sacred Eggs as living credentials with Mother Avion flock governor and phoenix rotation",
    },
}


def generate_stubs():
    """Generate instruction stubs for all domains x all template types."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(DOMAINS_FILE, "r") as f:
        domains = json.load(f)["domains"]

    records = []
    seq = 0

    for domain in domains:
        did = domain["id"]
        topics = DOMAIN_TOPICS.get(did)
        if not topics:
            continue

        skills = domain["skills"]
        arxiv_cats = domain["arxiv_categories"]
        search_terms = domain["search_terms"]

        for template_type, templates in INSTRUCTION_TEMPLATES.items():
            for template in templates:
                seq += 1
                instruction = template.format(
                    topic=topics["topic"],
                    scbe_concept=topics["scbe_concept"],
                )

                record = {
                    "id": f"ce-{did}-{seq:04d}",
                    "instruction": instruction,
                    "response": "",  # filled by researcher agents
                    "tier": "cutting_edge",
                    "domain": did,
                    "template_type": template_type,
                    "arxiv_categories": arxiv_cats,
                    "search_terms": search_terms,
                    "arxiv_thesis": {},
                    "supporting_papers": [],
                    "retrieval_evaluation": {
                        "agent_id": "",
                        "search_strategy": "",
                        "selection_rationale": "",
                        "confidence": 0.0,
                        "alternatives_considered": [],
                    },
                    "source_verification": {
                        "cross_references": [],
                        "citation_chain_depth": 0,
                        "verification_status": "unverified",
                    },
                    "geo_education_map": {
                        "institution": "",
                        "country": "",
                        "region": "",
                        "coordinates": [],
                        "research_tradition": "",
                        "regional_history": "",
                        "knowledge_strata": "",
                    },
                    "skill_sources": skills,
                    "category": did,
                    "source_type": "cutting_edge_research_provenance",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }
                records.append(record)

    # Write stubs
    outpath = os.path.join(OUTPUT_DIR, "cutting_edge_research_provenance_stubs.jsonl")
    with open(outpath, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Generated {len(records)} cutting-edge research provenance stubs")
    print(f"  Across {len(domains)} PhD domains")
    print(f"  {len(INSTRUCTION_TEMPLATES)} template types x 2 variants each")
    print(f"  Output: {outpath}")

    # Summary by domain
    from collections import Counter
    domain_counts = Counter(r["domain"] for r in records)
    for d, c in sorted(domain_counts.items()):
        print(f"    {d}: {c} stubs")

    return records


if __name__ == "__main__":
    generate_stubs()
