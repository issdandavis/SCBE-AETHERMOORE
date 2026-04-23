#!/usr/bin/env python3
"""
build_agentic_seed.py - Create a seed dataset of synthetic agentic coding trajectories.

Generates multi-turn ReAct-style trajectories for common developer tasks
using the SCBE-AETHERMOORE repo as context. These are synthetic but
realistic — they teach the model how to use tools, edit files, run tests,
and handle errors.

Usage:
    python scripts/training/build_agentic_seed.py
    python scripts/training/build_agentic_seed.py --count 200

Output: training-data/agentic_coding/seed_dataset.jsonl
"""

import argparse
import json
import random
from pathlib import Path
from typing import List, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "training-data" / "agentic_coding" / "seed_dataset.jsonl"

random.seed(42)

# ---------------------------------------------------------------------------
#  Atomic task definitions (real tasks from the SCBE repo)
# ---------------------------------------------------------------------------

ATOMIC_TASKS = [
    {
        "id": "ag-seed-00001",
        "task": "Add a new Polly endpoint for phone calls",
        "files": ["scripts/aetherbrowser/api_server.py"],
        "steps": [
            {"thought": "I need to add a Twilio call endpoint. First, let me check the existing Polly endpoints to follow the pattern.", 
             "tool": "read_file", "args": {"path": "scripts/aetherbrowser/api_server.py", "offset": 2130, "lines": 30}},
            {"thought": "I see the pattern: define a Pydantic payload class, then add an @app.post endpoint. I'll add a PollyCallPayload and a /v1/polly/call endpoint.",
             "tool": "apply_diff", "args": {"path": "scripts/aetherbrowser/api_server.py", 
              "diff": "+class PollyCallPayload(BaseModel):\n+    phone: str\n+    name: Optional[str] = ''\n+\n+@app.post('/v1/polly/call')\n+async def polly_call(payload: PollyCallPayload):\n+    ..."}},
            {"thought": "Let me verify the endpoint is syntactically correct by checking the file.",
             "tool": "read_file", "args": {"path": "scripts/aetherbrowser/api_server.py", "offset": 2160, "lines": 40}},
            {"thought": "Looks good. Let me run a quick syntax check.",
             "tool": "terminal", "args": {"command": "python -m py_compile scripts/aetherbrowser/api_server.py"}},
            {"thought": "Syntax check passed. The endpoint is ready.", "tool": "finish", "args": {"status": "success"}},
        ],
        "tongues": ["KO", "CA", "DR"],
        "layers": [1, 3, 7, 12, 14],
        "difficulty": "medium",
    },
    {
        "id": "ag-seed-00002",
        "task": "Fix the missing favicon on index.html",
        "files": ["index.html"],
        "steps": [
            {"thought": "The user says index.html is missing a favicon. Let me check the head section.",
             "tool": "read_file", "args": {"path": "index.html", "offset": 1, "lines": 20}},
            {"thought": "I see the head section but no favicon link. I need to add `<link rel=\"icon\" ...>` after the charset meta.",
             "tool": "apply_diff", "args": {"path": "index.html", 
              "diff": "+  <link rel=\"icon\" type=\"image/svg+xml\" href=\"/favicon.svg\">"}},
            {"thought": "Let me verify the favicon file exists.",
             "tool": "terminal", "args": {"command": "ls favicon.svg"}},
            {"thought": "Favicon exists and link is added. Task complete.", "tool": "finish", "args": {"status": "success"}},
        ],
        "tongues": ["KO", "AV"],
        "layers": [1, 3, 14],
        "difficulty": "easy",
    },
    {
        "id": "ag-seed-00003",
        "task": "Run tests after adding the Twilio endpoint",
        "files": ["scripts/aetherbrowser/api_server.py", "tests/"],
        "steps": [
            {"thought": "I need to verify the new Twilio endpoint doesn't break existing tests.",
             "tool": "terminal", "args": {"command": "python -m pytest tests/ -v --tb=short"}},
            {"thought": "Tests are failing with ImportError for 'twilio'. I need to check if twilio is in requirements.",
             "tool": "read_file", "args": {"path": "requirements.txt", "offset": 1, "lines": 50}},
            {"thought": "Twilio is not in requirements. I need to add it.",
             "tool": "apply_diff", "args": {"path": "requirements.txt", "diff": "+twilio>=9.0.0"}},
            {"thought": "Now let me install and re-run tests.",
             "tool": "terminal", "args": {"command": "pip install twilio && python -m pytest tests/ -v"}},
            {"thought": "All tests pass. The endpoint is properly integrated.", "tool": "finish", "args": {"status": "success"}},
        ],
        "tongues": ["RU", "CA", "KO"],
        "layers": [1, 5, 7, 10, 14],
        "difficulty": "medium",
    },
    {
        "id": "ag-seed-00004",
        "task": "Refactor the polly_service.py to add error handling",
        "files": ["scripts/system/polly_service.py"],
        "steps": [
            {"thought": "I need to add better error handling to polly_service.py. Let me first read the current implementation.",
             "tool": "read_file", "args": {"path": "scripts/system/polly_service.py", "offset": 1, "lines": 100}},
            {"thought": "I see the chat() function. It needs try/except around the LLM call and a fallback to deterministic responses.",
             "tool": "apply_diff", "args": {"path": "scripts/system/polly_service.py",
              "diff": " async def chat(message, context='site', thinking=False):\n+    try:\n         result = await _llm_call(message, context, thinking)\n+    except Exception as e:\n+        logger.warning('LLM failed: %s', e)\n+        result = deterministic_fallback(message)\n+    return result"}},
            {"thought": "Let me verify the syntax.",
             "tool": "terminal", "args": {"command": "python -m py_compile scripts/system/polly_service.py"}},
            {"thought": "Syntax is valid. The error handling is in place.", "tool": "finish", "args": {"status": "success"}},
        ],
        "tongues": ["RU", "UM", "CA"],
        "layers": [1, 3, 7, 12, 14],
        "difficulty": "hard",
    },
    {
        "id": "ag-seed-00005",
        "task": "Add a new page to the website and link it from the nav",
        "files": ["new-page.html", "index.html"],
        "steps": [
            {"thought": "I need to create a new status page and add it to the navigation. Let me check the current nav structure first.",
             "tool": "read_file", "args": {"path": "index.html", "offset": 40, "lines": 20}},
            {"thought": "I see the nav pattern. Let me create the new page first.",
             "tool": "write_file", "args": {"path": "status.html", 
              "content": "<!DOCTYPE html>...<a href='index.html'>Home</a>..."}},
            {"thought": "Now add the link to the nav in index.html.",
             "tool": "apply_diff", "args": {"path": "index.html", 
              "diff": "+        <a href='status.html'>Status</a>"}},
            {"thought": "Let me verify both files are valid HTML.",
             "tool": "terminal", "args": {"command": "python -c \"import html.parser; list(html.parser.HTMLParser().feed(open('status.html').read()))\""}},
            {"thought": "Both files are valid. The new page is linked.", "tool": "finish", "args": {"status": "success"}},
        ],
        "tongues": ["KO", "AV", "DR"],
        "layers": [1, 3, 5, 14],
        "difficulty": "easy",
    },
    {
        "id": "ag-seed-00006",
        "task": "Debug why the Arena Debate button doesn't work",
        "files": ["arena.html", "arena.js"],
        "steps": [
            {"thought": "The user says the Debate button doesn't work. Let me check if the button exists in the HTML.",
             "tool": "read_file", "args": {"path": "arena.html", "offset": 230, "lines": 20}},
            {"thought": "I don't see a debateBtn in the HTML. But arena.js references it. Let me check the JS.",
             "tool": "read_file", "args": {"path": "arena.js", "offset": 90, "lines": 20}},
            {"thought": "The JS references debateBtn but the HTML only has dealBtn, relayBtn, deliberateBtn, shareBtn. I need to add the missing button.",
             "tool": "apply_diff", "args": {"path": "arena.html",
              "diff": "+                <button class=\"btn-dm\" id=\"debateBtn\" onclick=\"debateDuel()\">Debate</button>"}},
            {"thought": "Let me verify the button is properly placed and the JS function exists.",
             "tool": "read_file", "args": {"path": "arena.html", "offset": 230, "lines": 20}},
            {"thought": "The button is added and the debateDuel function already exists in arena.js. The fix is complete.", "tool": "finish", "args": {"status": "success"}},
        ],
        "tongues": ["RU", "CA", "KO"],
        "layers": [1, 3, 7, 14],
        "difficulty": "medium",
    },
    {
        "id": "ag-seed-00007",
        "task": "Commit the agentic coding scaffolding to git",
        "files": ["scripts/training/", "training-data/agentic_coding/"],
        "steps": [
            {"thought": "I need to commit the new training scripts. Let me check what changed.",
             "tool": "terminal", "args": {"command": "git status --short"}},
            {"thought": "I see new files in scripts/training/ and training-data/agentic_coding/. Let me stage them.",
             "tool": "terminal", "args": {"command": "git add scripts/training/ training-data/agentic_coding/ config/model_training/"}},
            {"thought": "Now commit with a descriptive message.",
             "tool": "terminal", "args": {"command": "git commit -m 'feat(training): add agentic coding scaffolding\\n\\n- generate_agentic_sft.py: Convert SKILL.md to SFT pairs\\n- build_agentic_seed.py: Synthetic trajectory generator\\n- ingest_open_datasets.py: R2E-Gym + CodeActInstruct importer\\n- trajectory_logger.py: AetherBrowse session exporter\\n- agentic-coding-qlora.json: Training config'"}},
            {"thought": "Commit successful. Now push to the remote.",
             "tool": "terminal", "args": {"command": "git push origin feature/agentic-coding-scaffold"}},
            {"thought": "Push successful. PR created at #1145.", "tool": "finish", "args": {"status": "success"}},
        ],
        "tongues": ["KO"],
        "layers": [1, 14],
        "difficulty": "easy",
    },
    {
        "id": "ag-seed-00008",
        "task": "Add Open Graph tags to a page missing them",
        "files": ["profile.html"],
        "steps": [
            {"thought": "I need to add OG tags to profile.html. Let me check what it currently has.",
             "tool": "read_file", "args": {"path": "profile.html", "offset": 1, "lines": 15}},
            {"thought": "No OG tags present. I'll add them after the description meta.",
             "tool": "apply_diff", "args": {"path": "profile.html",
              "diff": "+  <meta property=\"og:title\" content=\"Issac's Profile | aethermoore.com\">\n+  <meta property=\"og:description\" content=\"Issac Davis — builder of SCBE-AETHERMOORE.\">\n+  <meta property=\"og:type\" content=\"profile\">\n+  <meta property=\"og:url\" content=\"https://aethermoore.com/profile.html\">\n+  <meta property=\"og:image\" content=\"https://aethermoore.com/hero.webp\">"}},
            {"thought": "OG tags added. Let me do a quick syntax check.",
             "tool": "terminal", "args": {"command": "grep -c 'og:' profile.html"}},
            {"thought": "5 OG tags found. Task complete.", "tool": "finish", "args": {"status": "success"}},
        ],
        "tongues": ["AV", "KO"],
        "layers": [1, 3, 14],
        "difficulty": "easy",
    },
    {
        "id": "ag-seed-00009",
        "task": "Update the sitemap.xml after adding new pages",
        "files": ["sitemap.xml"],
        "steps": [
            {"thought": "I need to add the new status.html and contact.html pages to the sitemap.",
             "tool": "read_file", "args": {"path": "sitemap.xml", "offset": 1, "lines": 30}},
            {"thought": "I see the sitemap structure. I'll add the new URLs before the closing </urlset>.",
             "tool": "apply_diff", "args": {"path": "sitemap.xml",
              "diff": "+  <url>\n+    <loc>https://aethermoore.com/status.html</loc>\n+    <lastmod>2026-04-23</lastmod>\n+  </url>\n+  <url>\n+    <loc>https://aethermoore.com/contact.html</loc>\n+    <lastmod>2026-04-23</lastmod>\n+  </url>"}},
            {"thought": "Let me validate the XML.",
             "tool": "terminal", "args": {"command": "python -c \"import xml.etree.ElementTree as ET; ET.parse('sitemap.xml')\" && echo 'Valid XML'"}},
            {"thought": "XML is valid. Sitemap updated.", "tool": "finish", "args": {"status": "success"}},
        ],
        "tongues": ["KO", "AV"],
        "layers": [1, 3, 14],
        "difficulty": "easy",
    },
    {
        "id": "ag-seed-00010",
        "task": "Add a cookie consent banner to all HTML pages",
        "files": ["*.html"],
        "steps": [
            {"thought": "I need to add a cookie banner to all pages. Let me first create the banner script.",
             "tool": "write_file", "args": {"path": "static/cookie-consent.js",
              "content": "(function(){...cookie banner code...})();"}},
            {"thought": "Now I need to add the script tag to all HTML files. Let me find them first.",
             "tool": "terminal", "args": {"command": "find . -name '*.html' -not -path '*/.git/*' | head -10"}},
            {"thought": "I'll use a Python script to batch-add the script tag before </body>.",
             "tool": "write_file", "args": {"path": "scripts/add_cookie_banner.py",
              "content": "#!/usr/bin/env python3\nimport os, re\nfor root, dirs, files in os.walk('.'):\n    for f in files:\n        if f.endswith('.html'):\n            path = os.path.join(root, f)\n            with open(path) as fh: content = fh.read()\n            if 'cookie-consent.js' not in content:\n                content = content.replace('</body>', '  <script src=\"/static/cookie-consent.js\" defer></script>\\n</body>')\n                with open(path, 'w') as fh: fh.write(content)\n                print(f'Updated: {path}')\n"}},
            {"thought": "Run the script.",
             "tool": "terminal", "args": {"command": "python3 scripts/add_cookie_banner.py"}},
            {"thought": "Let me verify one file.",
             "tool": "terminal", "args": {"command": "grep 'cookie-consent' index.html"}},
            {"thought": "Banner added to all pages. Task complete.", "tool": "finish", "args": {"status": "success"}},
        ],
        "tongues": ["KO", "AV", "UM"],
        "layers": [1, 3, 5, 14],
        "difficulty": "medium",
    },
]


# ---------------------------------------------------------------------------
#  Trajectory formatter
# ---------------------------------------------------------------------------

def format_trajectory(task: Dict) -> Dict:
    """Convert an atomic task into a chat-format SFT trajectory."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are SCBE-Coder, an agentic coding assistant. "
                "You use tools to read files, edit code, run commands, and verify results. "
                "Always think before acting. Always verify before finishing."
            )
        },
        {
            "role": "user",
            "content": task["task"]
        },
    ]
    
    for step in task["steps"]:
        thought = step.get("thought", "")
        tool = step.get("tool", "")
        args = step.get("args", {})
        
        if tool == "finish":
            messages.append({
                "role": "assistant",
                "content": f"<think>\n{thought}\n</think>\n\n<finish status=\"{args.get('status', 'success')}\" />"
            })
        else:
            args_str = json.dumps(args, ensure_ascii=False)
            messages.append({
                "role": "assistant",
                "content": f"<think>\n{thought}\n</think>\n\n<{tool}>\n{args_str}\n</{tool}>"
            })
            # Simulate tool result
            messages.append({
                "role": "tool",
                "content": f"[{tool}] Executed with args: {args_str[:200]}"
            })
    
    return {
        "id": task["id"],
        "category": "agentic-trajectory",
        "messages": messages,
        "metadata": {
            "source": "scbe_aethermoore",
            "version": "3.3.0",
            "generator": "build_agentic_seed.py",
            "task_type": "atomic",
            "files_involved": task.get("files", []),
            "tongues": task.get("tongues", ["KO"]),
            "layers": task.get("layers", [1, 14]),
            "difficulty": task.get("difficulty", "medium"),
            "turn_count": len(messages) - 2,
        }
    }


def augment_task(task: Dict, variation: int) -> Dict:
    """Create a variation of a task with different wording or files."""
    augmented = dict(task)
    augmented["id"] = f"ag-seed-{hash(task['id'] + str(variation)) % 100000:05d}"
    
    # Paraphrase the task
    paraphrases = {
        "Add": ["Implement", "Create", "Set up", "Build"],
        "Fix": ["Repair", "Resolve", "Correct", "Patch"],
        "Update": ["Refresh", "Modify", "Adjust", "Change"],
        "Debug": ["Troubleshoot", "Investigate", "Diagnose", "Fix"],
    }
    
    words = task["task"].split()
    if words and words[0] in paraphrases:
        words[0] = random.choice(paraphrases[words[0]])
        augmented["task"] = " ".join(words)
    
    # Slightly vary layers
    augmented["layers"] = sorted(list(set(
        [l + random.choice([-1, 0, 1]) for l in task["layers"]]
    )))
    augmented["layers"] = [max(1, min(14, l)) for l in augmented["layers"]]
    
    return augmented


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build agentic coding seed dataset")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--count", type=int, default=100,
                        help="Target number of trajectories (includes augmentations)")
    parser.add_argument("--augmentations", type=int, default=2,
                        help="Variations per base task")
    args = parser.parse_args()
    
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    trajectories = []
    
    # Base tasks
    for task in ATOMIC_TASKS:
        trajectories.append(format_trajectory(task))
        
        # Augmentations
        for v in range(1, args.augmentations + 1):
            aug = augment_task(task, v)
            trajectories.append(format_trajectory(aug))
    
    # If we need more, duplicate with random modifications from base tasks
    while len(trajectories) < args.count:
        base = random.choice(ATOMIC_TASKS)
        aug = augment_task(base, len(trajectories))
        trajectories.append(format_trajectory(aug))
    
    # Trim to exact count
    trajectories = trajectories[:args.count]
    
    with open(args.output, 'w', encoding='utf-8') as f:
        for t in trajectories:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')
    
    print(f"Wrote {len(trajectories)} agentic trajectories to {args.output}")
    
    # Stats
    difficulties = {}
    tongues = {}
    for t in trajectories:
        d = t["metadata"]["difficulty"]
        difficulties[d] = difficulties.get(d, 0) + 1
        for tongue in t["metadata"]["tongues"]:
            tongues[tongue] = tongues.get(tongue, 0) + 1
    
    print(f"\nDifficulty: {difficulties}")
    print(f"Tongues: {tongues}")
    print(f"Avg turns: {sum(t['metadata']['turn_count'] for t in trajectories) / len(trajectories):.1f}")


if __name__ == "__main__":
    main()
