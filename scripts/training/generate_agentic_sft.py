#!/usr/bin/env python3
"""
generate_agentic_sft.py - Convert SKILL.md files and agent definitions into
agentic coding SFT training pairs.

Scans skills/, .agents/, and training-data/clawhub-skills/ for agent
capability definitions, then synthesizes instruction/response pairs that
teach tool use, file editing, git workflows, and multi-turn reasoning.

Usage:
    python scripts/training/generate_agentic_sft.py
    python scripts/training/generate_agentic_sft.py --output training-data/agentic_coding/from_skills.jsonl

Author: Issac Davis
Date: 2026-04-23
"""

import argparse
import json
import random
import re
from pathlib import Path
from typing import List, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "training-data" / "agentic_coding" / "from_skills.jsonl"

# ---------------------------------------------------------------------------
#  SKILL.md → SFT templates
# ---------------------------------------------------------------------------

TOOL_USE_TEMPLATES = [
    {
        "instruction": "Use the {tool_name} tool to {task_description}.",
        "response_template": "<tool_call>\n{{\"name\": \"{tool_name}\", \"args\": {tool_args}}}</tool_call>\n<tool_result>\n{tool_result}\n</tool_result>\n{follow_up}"
    },
    {
        "instruction": "I need to {task_description}. Which tool should I use and how?",
        "response_template": "For this task, use the {tool_name} tool.\n\n<tool_call>\n{{\"name\": \"{tool_name}\", \"args\": {tool_args}}}</tool_call>\n<tool_result>\n{tool_result}\n</tool_result>\n\n{follow_up}"
    },
]

FILE_EDIT_TEMPLATES = [
    {
        "instruction": "Edit {file_path} to {change_description}.",
        "response_template": "<read_file>\n{file_path}\n</read_file>\n\nThe file contains:\n```\n{file_content_snippet}\n```\n\n<apply_diff>\n{diff}\n</apply_diff>\n\n<verify>\n{verification_result}\n</verify>"
    },
]

GIT_WORKFLOW_TEMPLATES = [
    {
        "instruction": "Create a feature branch for '{feature_name}', commit the changes, and open a PR.",
        "response_template": "<terminal>\ngit checkout -b {branch_name}\ngit add {files_changed}\ngit commit -m \"{commit_message}\"\ngit push origin {branch_name}\n</terminal>\n\n<browser>\nOpen PR: {pr_title}\nBody: {pr_body}\n</browser>\n\n<verify>\nCI status: {ci_status}\n</verify>"
    },
]

DEBUG_TEMPLATES = [
    {
        "instruction": "The tests are failing with: {error_message}. Fix the issue.",
        "response_template": "<read_file>\n{file_path}\n</read_file>\n\n<think>\nThe error indicates {error_analysis}. I need to {proposed_fix}.\n</think>\n\n<apply_diff>\n{diff}\n</apply_diff>\n\n<terminal>\n{test_command}\n</terminal>\n\n<verify>\nTests: {test_result}\n</verify>"
    },
]

# ---------------------------------------------------------------------------
#  Skill parsers
# ---------------------------------------------------------------------------

def parse_skill_md(path: Path) -> Dict:
    """Extract structured data from a SKILL.md file."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    
    # Extract frontmatter
    frontmatter = {}
    fm_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).strip().split('\n'):
            if ':' in line:
                k, v = line.split(':', 1)
                frontmatter[k.strip()] = v.strip()
    
    # Extract sections
    sections = {}
    current_section = None
    current_content = []
    for line in text.split('\n'):
        if line.startswith('# '):
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = line[2:].strip().lower().replace(' ', '_')
            current_content = []
        elif current_section is not None:
            current_content.append(line)
    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "name": frontmatter.get("name", path.parent.name),
        "description": frontmatter.get("description", ""),
        "sections": sections,
    }


def find_all_skills() -> List[Path]:
    """Find all SKILL.md files in the repo."""
    paths = []
    for pattern in [
        "skills/**/SKILL.md",
        ".agents/**/SKILL.md",
        "training-data/clawhub-skills/**/SKILL.md",
    ]:
        paths.extend(PROJECT_ROOT.glob(pattern))
    return sorted(set(paths))


# ---------------------------------------------------------------------------
#  SFT pair generators
# ---------------------------------------------------------------------------

def generate_tool_use_pairs(skill: Dict, count: int = 3) -> List[Dict]:
    """Generate tool-use SFT pairs from a skill definition."""
    pairs = []
    desc = skill.get("description", "")
    name = skill.get("name", "")
    
    # Extract tool names from description (heuristic)
    tools_mentioned = re.findall(r'\b(\w+(?:\.\w+)?)\b', desc)
    tools_mentioned = [t for t in tools_mentioned if len(t) > 2][:3]
    if not tools_mentioned:
        tools_mentioned = [name.replace('-', '_')]
    
    for i in range(count):
        tool = random.choice(tools_mentioned) if tools_mentioned else "api_call"
        template = random.choice(TOOL_USE_TEMPLATES)
        
        task = desc if desc else f"execute {tool}"
        pairs.append({
            "id": f"ag-tool-{hash(skill['path'] + str(i)) % 100000:05d}",
            "category": "agentic-tool-use",
            "instruction": template["instruction"].format(
                tool_name=tool,
                task_description=task[:120]
            ),
            "response": template["response_template"].format(
                tool_name=tool,
                tool_args=json.dumps({"param": "value"}),
                tool_result="Success: operation completed.",
                follow_up=f"The {tool} operation completed successfully. Next step depends on the result.",
            ),
            "metadata": {
                "source": "scbe_aethermoore",
                "version": "3.3.0",
                "skill": name,
                "skill_path": skill["path"],
                "generator": "generate_agentic_sft.py",
                "tongue": random.choice(["KO", "AV", "CA"]),
                "difficulty": random.choice(["easy", "medium"]),
            }
        })
    return pairs


def generate_file_edit_pairs(skill: Dict, count: int = 2) -> List[Dict]:
    """Generate file-editing SFT pairs."""
    pairs = []
    name = skill.get("name", "")
    
    for i in range(count):
        template = random.choice(FILE_EDIT_TEMPLATES)
        pairs.append({
            "id": f"ag-edit-{hash(skill['path'] + str(i)) % 100000:05d}",
            "category": "agentic-file-edit",
            "instruction": template["instruction"].format(
                file_path=f"src/{name.replace('-', '_')}.py",
                change_description=f"implement {name} functionality"
            ),
            "response": template["response_template"].format(
                file_path=f"src/{name.replace('-', '_')}.py",
                file_content_snippet="# Existing code...",
                diff="+ def new_function():\n+     pass",
                verification_result="File updated successfully.",
            ),
            "metadata": {
                "source": "scbe_aethermoore",
                "version": "3.3.0",
                "skill": name,
                "skill_path": skill["path"],
                "generator": "generate_agentic_sft.py",
                "tongue": random.choice(["CA", "DR"]),
                "difficulty": random.choice(["medium", "hard"]),
            }
        })
    return pairs


def generate_git_workflow_pairs(count: int = 5) -> List[Dict]:
    """Generate git workflow SFT pairs."""
    pairs = []
    features = [
        "add Twilio click-to-call",
        "fix broken nav links",
        "implement 14-layer reward model",
        "add Pollinations AI to Arena",
        "update hero.webp across all pages",
    ]
    
    for i, feature in enumerate(features[:count]):
        template = random.choice(GIT_WORKFLOW_TEMPLATES)
        branch = feature.replace(' ', '-').replace('/', '-')[:30]
        pairs.append({
            "id": f"ag-git-{i:05d}",
            "category": "agentic-git-workflow",
            "instruction": template["instruction"].format(feature_name=feature),
            "response": template["response_template"].format(
                branch_name=f"feature/{branch}",
                files_changed="*.py *.html",
                commit_message=f"feat: {feature}",
                pr_title=f"feat: {feature}",
                pr_body=f"Implements {feature}.\n\n## Changes\n- ...\n\n## Testing\n- ...",
                ci_status="passing",
            ),
            "metadata": {
                "source": "scbe_aethermoore",
                "version": "3.3.0",
                "generator": "generate_agentic_sft.py",
                "tongue": "KO",
                "difficulty": "medium",
            }
        })
    return pairs


def generate_debug_pairs(count: int = 5) -> List[Dict]:
    """Generate debug SFT pairs."""
    pairs = []
    errors = [
        ("ModuleNotFoundError: No module named 'twilio'", "scripts/aetherbrowser/api_server.py", "Import twilio at top of file"),
        ("SyntaxError: unexpected EOF while parsing", "arena.js", "Close the unclosed brace"),
        ("AssertionError: expected 200 but got 404", "tests/test_api.py", "Update the endpoint path"),
        ("TypeError: Cannot read property 'trim' of undefined", "polly-sidebar.js", "Add null check before trim"),
        ("KeyError: 'TWILIO_ACCOUNT_SID'", "scripts/system/polly_service.py", "Add env var fallback"),
    ]
    
    for i, (error, filepath, fix) in enumerate(errors[:count]):
        template = random.choice(DEBUG_TEMPLATES)
        pairs.append({
            "id": f"ag-debug-{i:05d}",
            "category": "agentic-debug",
            "instruction": template["instruction"].format(error_message=error),
            "response": template["response_template"].format(
                file_path=filepath,
                error_analysis=error.split(':')[0],
                proposed_fix=fix,
                diff="+ # fix applied",
                test_command="pytest tests/ -v",
                test_result="5 passed, 0 failed",
            ),
            "metadata": {
                "source": "scbe_aethermoore",
                "version": "3.3.0",
                "generator": "generate_agentic_sft.py",
                "tongue": random.choice(["RU", "CA"]),
                "difficulty": random.choice(["medium", "hard"]),
            }
        })
    return pairs


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate agentic coding SFT from skills")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Output JSONL file path")
    parser.add_argument("--pairs-per-skill", type=int, default=3,
                        help="Number of SFT pairs to generate per skill")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    args = parser.parse_args()
    
    random.seed(args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    skill_paths = find_all_skills()
    print(f"Found {len(skill_paths)} SKILL.md files")
    
    all_pairs = []
    
    # Generate from skills
    for path in skill_paths:
        skill = parse_skill_md(path)
        all_pairs.extend(generate_tool_use_pairs(skill, args.pairs_per_skill))
        all_pairs.extend(generate_file_edit_pairs(skill, args.pairs_per_skill // 2))
    
    # Generate generic agentic pairs
    all_pairs.extend(generate_git_workflow_pairs(10))
    all_pairs.extend(generate_debug_pairs(10))
    
    # Deduplicate by ID
    seen_ids = set()
    unique_pairs = []
    for p in all_pairs:
        if p["id"] not in seen_ids:
            seen_ids.add(p["id"])
            unique_pairs.append(p)
    
    # Write
    with open(args.output, 'w', encoding='utf-8') as f:
        for p in unique_pairs:
            f.write(json.dumps(p, ensure_ascii=False) + '\n')
    
    print(f"Wrote {len(unique_pairs)} agentic SFT pairs to {args.output}")
    
    # Category breakdown
    from collections import Counter
    cats = Counter(p["category"] for p in unique_pairs)
    print("\nBreakdown:")
    for cat, cnt in cats.most_common():
        print(f"  {cat}: {cnt}")


if __name__ == "__main__":
    main()
