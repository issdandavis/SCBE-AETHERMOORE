#!/usr/bin/env python3
"""
Generate tutorial-style SFT training data from Codex skill vault + cross-talk packets.

Three complexity tiers (on top of existing K-12):
  - 10th grade: accessible, analogy-heavy, builds intuition
  - college: technical, references CS/math concepts, shows tradeoffs
  - cutting_edge: research-grade, cites formal methods, connects to open problems

Sources:
  - ~/.codex/skills/*/SKILL.md  (110 skills)
  - artifacts/agent_comm/**/*.json  (44 cross-talk packets)

Output: training-data/sft/codex_skill_tutorials_{tier}.jsonl
"""

import json
import os
import glob
from pathlib import Path
from datetime import datetime

CODEX_SKILLS_DIR = os.path.expanduser("~/.codex/skills")
CROSSTALK_DIR = "artifacts/agent_comm"
OUTPUT_DIR = "training-data/sft"

# ─── Skill Loader ───────────────────────────────────────────────────────────

def load_skills():
    """Load all Codex SKILL.md files, return list of dicts with name + content."""
    skills = []
    skill_dirs = sorted(glob.glob(os.path.join(CODEX_SKILLS_DIR, "*", "SKILL.md")))
    for path in skill_dirs:
        skill_name = os.path.basename(os.path.dirname(path))
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        # Parse frontmatter
        description = ""
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split("\n"):
                    if line.strip().startswith("description:"):
                        description = line.split(":", 1)[1].strip().strip('"').strip("'")
                content = parts[2].strip()
        skills.append({
            "name": skill_name,
            "description": description,
            "content": content,
        })
    return skills


def load_crosstalk_packets():
    """Load all cross-talk JSON packets."""
    packets = []
    for path in sorted(glob.glob(os.path.join(CROSSTALK_DIR, "**", "*.json"), recursive=True)):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            packets.append(data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    return packets


# ─── Categorization ─────────────────────────────────────────────────────────

CATEGORY_MAP = {
    "browser": ["aetherbrowser", "hydra-node-terminal", "playwright", "browser", "screenshot"],
    "ai_coordination": ["crosstalk", "ai-to-ai", "handoff", "multi-agent", "flock", "overwatch", "session"],
    "monetization": ["monetization", "shopify", "profit", "checkout", "gumroad", "offer", "cash", "revenue"],
    "training": ["training", "colab", "hugging-face", "hf-publish", "datasets", "model-trainer"],
    "publishing": ["publish", "npm", "github-pages", "article", "research-publishing", "website"],
    "governance": ["governance", "gate", "context-full-test", "experimental-research", "security"],
    "creative": ["story", "novel", "manhwa", "webtoon", "book", "lore", "speed-line", "animation"],
    "devops": ["docker", "gh-fix-ci", "github-systems", "gitlab", "sweep", "powershell", "system"],
    "knowledge": ["notion", "obsidian", "vault", "knowledge", "codebase-orienter", "world-anvil"],
    "infrastructure": ["mcp", "n8n", "connector", "meridian", "workflow", "phone", "kindle", "pocket"],
}

def categorize_skill(name):
    for cat, keywords in CATEGORY_MAP.items():
        for kw in keywords:
            if kw in name:
                return cat
    return "general"


# ─── Tutorial Templates per Tier ─────────────────────────────────────────────

def make_10th_grade_instructions(skill):
    """Generate 10th-grade-level tutorial questions."""
    name_clean = skill["name"].replace("-", " ").replace("scbe ", "").title()
    cat = categorize_skill(skill["name"])
    pairs = []

    # What is it?
    pairs.append({
        "instruction": f"What is {name_clean} and why would someone use it? Explain like I'm in 10th grade.",
        "tier": "10th_grade",
    })

    # How does it work step by step?
    pairs.append({
        "instruction": f"Walk me through how {name_clean} works, step by step, using a real-world analogy.",
        "tier": "10th_grade",
    })

    # When would you use it?
    pairs.append({
        "instruction": f"Give me three situations where I'd need {name_clean}. Keep it simple.",
        "tier": "10th_grade",
    })

    return pairs


def make_college_instructions(skill):
    """Generate college-level tutorial questions."""
    name_clean = skill["name"].replace("-", " ").replace("scbe ", "").title()
    cat = categorize_skill(skill["name"])
    pairs = []

    pairs.append({
        "instruction": f"Explain the architecture and design decisions behind {name_clean}. What tradeoffs were made?",
        "tier": "college",
    })

    pairs.append({
        "instruction": f"How does {name_clean} integrate with the SCBE 14-layer pipeline and governance system? Include technical details.",
        "tier": "college",
    })

    pairs.append({
        "instruction": f"Compare {name_clean} to how a similar problem is solved in traditional software engineering. What's different about the SCBE approach?",
        "tier": "college",
    })

    return pairs


def make_cutting_edge_instructions(skill):
    """Generate research-grade questions."""
    name_clean = skill["name"].replace("-", " ").replace("scbe ", "").title()
    cat = categorize_skill(skill["name"])
    pairs = []

    pairs.append({
        "instruction": f"Analyze {name_clean} through the lens of formal verification and safety guarantees. What invariants does it maintain? Where are the open problems?",
        "tier": "cutting_edge",
    })

    pairs.append({
        "instruction": f"How could {name_clean} be extended to operate in a federated multi-agent environment with Byzantine fault tolerance? Sketch the protocol.",
        "tier": "cutting_edge",
    })

    pairs.append({
        "instruction": f"What novel research contributions does {name_clean} make compared to existing literature in AI safety, multi-agent coordination, or geometric security? Cite relevant parallels.",
        "tier": "cutting_edge",
    })

    return pairs


# ─── Cross-talk Tutorial Templates ──────────────────────────────────────────

def make_crosstalk_tutorials(packets):
    """Generate tutorials from cross-talk packet corpus."""
    pairs = {
        "10th_grade": [],
        "college": [],
        "cutting_edge": [],
    }

    # Group by intent
    intents = set(p.get("intent", "unknown") for p in packets)
    senders = set(p.get("sender", "unknown") for p in packets)

    pairs["10th_grade"].append({
        "instruction": "What is AI cross-talk and why do AI agents need to send messages to each other? Explain like I'm in 10th grade.",
        "skill_source": "cross-talk-corpus",
        "category": "ai_coordination",
    })
    pairs["10th_grade"].append({
        "instruction": f"In the SCBE system, agents communicate using intents like {', '.join(list(intents)[:5])}. What does each intent mean in plain English?",
        "skill_source": "cross-talk-corpus",
        "category": "ai_coordination",
    })
    pairs["10th_grade"].append({
        "instruction": "Why would an AI agent need a 'lease' on a computing resource? Use an analogy to explain.",
        "skill_source": "cross-talk-corpus",
        "category": "ai_coordination",
    })

    pairs["college"].append({
        "instruction": "Describe the SCBE cross-talk packet schema. What fields are required, what are optional, and how does the governance layer validate packets?",
        "skill_source": "cross-talk-corpus",
        "category": "ai_coordination",
    })
    pairs["college"].append({
        "instruction": "How does the SCBE cross-talk system handle packet delivery failure, duplicate detection, and session continuity across agent restarts?",
        "skill_source": "cross-talk-corpus",
        "category": "ai_coordination",
    })
    pairs["college"].append({
        "instruction": f"Agents in SCBE use senders like {', '.join(list(senders)[:4])}. How does the system authenticate sender identity and prevent spoofed packets?",
        "skill_source": "cross-talk-corpus",
        "category": "ai_coordination",
    })

    pairs["cutting_edge"].append({
        "instruction": "Compare SCBE cross-talk to established multi-agent communication protocols (FIPA ACL, KQML, actor model). What does SCBE add with governance-stamped packets and hyperbolic distance-based trust?",
        "skill_source": "cross-talk-corpus",
        "category": "ai_coordination",
    })
    pairs["cutting_edge"].append({
        "instruction": "Design a formal verification framework for SCBE cross-talk that can prove liveness (packets eventually delivered) and safety (no unauthorized state mutation) properties. What model checking approaches apply?",
        "skill_source": "cross-talk-corpus",
        "category": "ai_coordination",
    })
    pairs["cutting_edge"].append({
        "instruction": "How could SCBE cross-talk scale to 1000+ concurrent agents without centralized coordination? Analyze the protocol's communication complexity and propose optimizations using gossip protocols or CRDTs.",
        "skill_source": "cross-talk-corpus",
        "category": "ai_coordination",
    })

    return pairs


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Loading Codex skills...")
    skills = load_skills()
    print(f"  Loaded {len(skills)} skills")

    print("Loading cross-talk packets...")
    packets = load_crosstalk_packets()
    print(f"  Loaded {len(packets)} packets")

    tiers = {
        "10th_grade": [],
        "college": [],
        "cutting_edge": [],
    }

    # Generate from skills
    for skill in skills:
        cat = categorize_skill(skill["name"])
        meta_base = {
            "skill_source": skill["name"],
            "skill_description": skill["description"][:200],
            "category": cat,
            "source_type": "codex_skill_tutorial",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

        for pair in make_10th_grade_instructions(skill):
            pair.update(meta_base)
            # Response placeholder — to be filled by subagents
            pair["response"] = ""
            pair["skill_content"] = skill["content"][:3000]
            tiers["10th_grade"].append(pair)

        for pair in make_college_instructions(skill):
            pair.update(meta_base)
            pair["response"] = ""
            pair["skill_content"] = skill["content"][:3000]
            tiers["college"].append(pair)

        for pair in make_cutting_edge_instructions(skill):
            pair.update(meta_base)
            pair["response"] = ""
            pair["skill_content"] = skill["content"][:3000]
            tiers["cutting_edge"].append(pair)

    # Generate from cross-talk
    ct_tutorials = make_crosstalk_tutorials(packets)
    for tier_name, pairs in ct_tutorials.items():
        for pair in pairs:
            pair["source_type"] = "crosstalk_tutorial"
            pair["generated_at"] = datetime.utcnow().isoformat() + "Z"
            pair["response"] = ""
            # Include sample packets as context
            pair["sample_packets"] = json.dumps(packets[:3], indent=2)[:2000]
            tiers[tier_name].append(pair)

    # Write instruction stubs (responses to be filled by LLM subagents)
    for tier_name, records in tiers.items():
        outpath = os.path.join(OUTPUT_DIR, f"codex_skill_tutorials_{tier_name}_stubs.jsonl")
        with open(outpath, "w", encoding="utf-8") as f:
            for rec in records:
                # Strip skill_content and sample_packets from final output
                # (only needed during response generation)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"  {tier_name}: {len(records)} instruction stubs -> {outpath}")

    # Summary
    total = sum(len(v) for v in tiers.values())
    print(f"\nTotal: {total} tutorial stubs across 3 tiers")
    print("Next: Run subagents to fill responses using skill_content as context")


if __name__ == "__main__":
    main()
