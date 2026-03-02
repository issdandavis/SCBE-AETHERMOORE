"""
AetherBrowse — Planner Module
================================
Takes a user command + PagePerception and produces an ActionPlan:
a sequence of browser actions (navigate, click, fill, upload, etc.)
that the Executor (Kael) will carry out.

Routes through OctoArmor for LLM reasoning.
Falls back to rule-based planning when no LLM is available.

The Planner is Zara's domain — tongue KO (leader).

Agent loop position: PERCEIVE → **PLAN** → GOVERN → EXECUTE
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("aetherbrowse-planner")

ROOT = Path(__file__).resolve().parent.parent.parent

# Try importing OctoArmor
try:
    import sys
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "src"))
    from fleet.octo_armor import OctoArmor
    HAS_OCTOARMOR = True
except ImportError:
    HAS_OCTOARMOR = False


# ---------------------------------------------------------------------------
#  Action Plan data structures
# ---------------------------------------------------------------------------

@dataclass
class BrowserAction:
    """A single browser action for the executor to carry out."""
    action: str                    # navigate, click, fill, upload, huggingface_upload, evaluate, wait_for, screenshot
                                  # telegram_send, telegram_get_updates, github_issue_list, github_issue_create, github_issue_comment,
                                  # github_issue_close, github_pr_list, github_pr_create, github_pr_merge,
                                  # github_codespace_list, github_codespace_create, github_codespace_stop
    selector: str = ""             # CSS selector target
    value: str = ""                # For fill/navigate: the value to enter
    file_path: str = ""            # For upload: local file path
    repo_id: str = ""              # For huggingface_upload
    repo: str = ""                 # For github actions
    chat_id: str = ""              # For telegram actions
    message: str = ""              # For telegram and text payload fields
    parse_mode: str = "Markdown"    # Telegram parse mode
    body: str = ""                 # For github issue/pr body
    repo_type: str = "model"       # For huggingface_upload
    path_in_repo: str = ""         # For huggingface_upload
    commit_message: str = ""        # For huggingface_upload
    metadata: dict[str, Any] = field(default_factory=dict)  # Extensible action metadata
    github_action: str = ""        # Action name when sending a github verb
    offset: int = 0
    limit: int = 100
    description: str = ""          # Human-readable explanation
    governance_required: bool = False  # Whether this needs extra governance check
    wait_after_ms: int = 500       # How long to wait after this action

    def to_dict(self) -> dict:
        d = {"action": self.action, "description": self.description}
        if self.selector:
            d["selector"] = self.selector
        if self.value:
            d["value"] = self.value
        if self.file_path:
            d["file_path"] = self.file_path
        if self.repo_id:
            d["repo_id"] = self.repo_id
        if self.repo_type != "model":
            d["repo_type"] = self.repo_type
        if self.path_in_repo:
            d["path_in_repo"] = self.path_in_repo
        if self.repo:
            d["repo"] = self.repo
        if self.chat_id:
            d["chat_id"] = self.chat_id
        if self.message:
            d["message"] = self.message
        if self.parse_mode:
            d["parse_mode"] = self.parse_mode
        if self.body:
            d["body"] = self.body
        if self.commit_message:
            d["commit_message"] = self.commit_message
        if self.offset:
            d["offset"] = self.offset
        if self.limit != 100:
            d["limit"] = self.limit
        if self.metadata:
            d["metadata"] = self.metadata
        if self.github_action:
            d["github_action"] = self.github_action
        if self.governance_required:
            d["governance_required"] = True
        if self.wait_after_ms != 500:
            d["wait_after_ms"] = self.wait_after_ms
        return d

    def to_worker_command(self) -> dict:
        """Convert to the format the browser worker expects."""
        cmd = {"type": "browser-command", "action": self.action}
        if self.action == "navigate":
            cmd["url"] = self.value
        elif self.action == "click":
            cmd["selector"] = self.selector
        elif self.action == "fill":
            cmd["selector"] = self.selector
            cmd["value"] = self.value
        elif self.action == "huggingface_upload":
            cmd["file_path"] = self.file_path
            cmd["repo_id"] = self.repo_id
            cmd["repo_type"] = self.repo_type
            if self.path_in_repo:
                cmd["path_in_repo"] = self.path_in_repo
            if self.commit_message:
                cmd["commit_message"] = self.commit_message
        elif self.action == "upload":
            cmd["selector"] = self.selector
            cmd["file_path"] = self.file_path
        elif self.action == "evaluate":
            cmd["script"] = self.value
        elif self.action == "wait_for":
            cmd["selector"] = self.selector
            cmd["timeout"] = self.wait_after_ms
        elif self.action == "screenshot":
            cmd["name"] = self.value or "step"
        elif self.action == "snapshot":
            pass  # No extra params needed
        elif self.action == "telegram_send":
            cmd["message"] = self.message
            cmd["chat_id"] = self.chat_id
            if self.parse_mode:
                cmd["parse_mode"] = self.parse_mode
        elif self.action == "telegram_get_updates":
            cmd["offset"] = self.offset
            cmd["limit"] = self.limit
        elif self.action.startswith("github_"):
            cmd["repo"] = self.repo
            cmd["action_name"] = self.github_action or self.action
            if self.value:
                cmd["title"] = self.value
            if self.body:
                cmd["body"] = self.body
            if self.message:
                cmd["message"] = self.message
            if self.metadata:
                cmd["metadata"] = self.metadata
            if self.commit_message:
                cmd["commit_message"] = self.commit_message
        return cmd


@dataclass
class ActionPlan:
    """A sequence of browser actions to accomplish a user goal."""
    goal: str                          # What the user asked for
    steps: list[BrowserAction] = field(default_factory=list)
    reasoning: str = ""                # LLM's reasoning about the plan
    confidence: float = 0.0            # How confident the planner is (0-1)
    method: str = "unknown"            # "llm", "rule_based", "hybrid"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "step_count": len(self.steps),
            "steps": [s.to_dict() for s in self.steps],
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "method": self.method,
        }

    def summary(self) -> str:
        lines = [f"Plan: {self.goal} ({len(self.steps)} steps, {self.confidence:.0%} confidence)"]
        for i, step in enumerate(self.steps):
            lines.append(f"  {i+1}. [{step.action}] {step.description}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
#  LLM-based planning
# ---------------------------------------------------------------------------

PLANNER_SYSTEM_PROMPT = """You are Zara, the planning agent for AetherBrowse — a governed AI browser.
You receive a user's goal and a description of the current page, and you produce a step-by-step action plan.

Available actions:
- navigate: Go to a URL. Requires "value" (the URL).
- click: Click an element. Requires "selector" (CSS selector from the page perception).
- fill: Type text into a field. Requires "selector" and "value".
- upload: Upload a file. Requires "selector" (file input) and "file_path" (local path).
- huggingface_upload: Upload a file directly to a Hugging Face repository.
-  Requires "file_path" and "repo_id". Optional "repo_type", "path_in_repo", "commit_message".
- telegram_send: Send a Telegram message. Requires "chat_id" and "message".
- telegram_get_updates: Fetch Telegram updates. Optional "offset" and "limit".
- github_issue_list: List GitHub issues for a repo. Requires "repo".
- github_issue_create: Create a GitHub issue. Requires "repo" and "title", optional "body".
- github_issue_comment: Add a GitHub comment. Requires "repo" and "number", plus "message".
- github_issue_close: Close a GitHub issue. Requires "repo" and "number".
- github_pr_list: List pull requests for a repo. Requires "repo".
- github_pr_create: Create a pull request. Requires "repo" and "title". Optional "body", "head", "base".
- github_pr_merge: Merge a pull request. Requires "repo" and "number".
- github_codespace_list: List GitHub codespaces. Optional "repo".
- github_codespace_create: Create a GitHub codespace. Requires "repo". Optional "branch", "machine", "name".
- github_codespace_stop: Stop a GitHub codespace. Requires "name".
- wait_for: Wait for an element to appear. Requires "selector".
- screenshot: Take a screenshot. Optional "value" for name.
- snapshot: Get a fresh accessibility tree of the current page.

Rules:
1. Use the selectors from the page perception — they are stable aria-label selectors.
2. If the user's goal requires navigating to a different page first, start with a navigate step.
3. After filling a form, include a click step for the submit button.
4. After navigation or form submission, include a snapshot step to perceive the new page.
5. For file uploads, use the local file paths from C:\\Users\\issda\\SCBE-AETHERMOORE\\
6. Mark destructive actions (delete, remove, cancel) with "governance_required": true.
7. Keep plans short — under 10 steps for simple tasks.

Respond with valid JSON only. Format:
{
  "reasoning": "Brief explanation of your approach",
  "confidence": 0.85,
  "steps": [
    {"action": "navigate", "value": "https://example.com", "description": "Go to the target page"},
    {"action": "fill", "selector": "input[aria-label=\\"Email\\"]", "value": "user@example.com", "description": "Enter email"},
    {"action": "click", "selector": "button:has-text(\\"Submit\\")", "description": "Submit the form"},
    {"action": "snapshot", "description": "Perceive the result page"}
  ]
}"""


async def plan_with_llm(goal: str, page_context: str) -> Optional[ActionPlan]:
    """Generate an action plan using OctoArmor LLM routing."""
    if not HAS_OCTOARMOR:
        logger.warning("OctoArmor not available, cannot use LLM planner")
        return None

    prompt = f"""User goal: {goal}

{page_context}

Produce an action plan as JSON."""

    try:
        armor = OctoArmor()
        result = await armor.reach(
            prompt,
            task_type="planning",
            temperature=0.3,
            max_tokens=2048,
            context=PLANNER_SYSTEM_PROMPT,
        )

        if result.get("status") != "ok" or not result.get("response"):
            logger.warning(f"LLM planner failed: {result.get('error', 'no response')}")
            return None

        raw = result["response"]
        plan = _parse_llm_plan(goal, raw)
        if plan:
            plan.method = f"llm:{result.get('tentacle', 'unknown')}"
        return plan

    except Exception as e:
        logger.error(f"LLM planner error: {e}")
        return None


def _parse_llm_plan(goal: str, raw_response: str) -> Optional[ActionPlan]:
    """Parse the LLM's JSON response into an ActionPlan."""
    # Try to extract JSON from the response (might have markdown fences)
    json_match = re.search(r'\{[\s\S]*\}', raw_response)
    if not json_match:
        logger.warning("No JSON found in LLM response")
        return None

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON from LLM: {e}")
        return None

    steps = []
    for step_data in data.get("steps", []):
        action = step_data.get("action", "")
        if action not in (
            "navigate",
            "click",
            "fill",
            "upload",
            "huggingface_upload",
            "telegram_send",
            "telegram_get_updates",
            "github_issue_list",
            "github_issue_create",
            "github_issue_comment",
            "github_issue_close",
            "github_pr_list",
            "github_pr_create",
            "github_pr_merge",
            "github_codespace_list",
            "github_codespace_create",
            "github_codespace_stop",
            "wait_for",
            "screenshot",
            "snapshot",
            "evaluate",
        ):
            continue

        step = BrowserAction(
            action=action,
            selector=step_data.get("selector", ""),
            value=step_data.get("value", ""),
            file_path=step_data.get("file_path", ""),
            repo_id=step_data.get("repo_id", ""),
            repo_type=step_data.get("repo_type", "model"),
            path_in_repo=step_data.get("path_in_repo", ""),
            commit_message=step_data.get("commit_message", ""),
            repo=step_data.get("repo", ""),
            chat_id=step_data.get("chat_id", ""),
            message=step_data.get("message", ""),
            parse_mode=step_data.get("parse_mode", "Markdown"),
            body=step_data.get("body", ""),
            metadata=step_data.get("metadata", {}),
            github_action=step_data.get("github_action", ""),
            offset=step_data.get("offset", 0),
            limit=step_data.get("limit", 100),
            description=step_data.get("description", ""),
            governance_required=step_data.get("governance_required", False),
            wait_after_ms=step_data.get("wait_after_ms", 500),
        )
        steps.append(step)

    if not steps:
        logger.warning("LLM produced no valid steps")
        return None

    return ActionPlan(
        goal=goal,
        steps=steps,
        reasoning=data.get("reasoning", ""),
        confidence=float(data.get("confidence", 0.7)),
    )


# ---------------------------------------------------------------------------
#  Rule-based planning (fallback when no LLM available)
# ---------------------------------------------------------------------------

# URL patterns for common platforms
PLATFORM_PATTERNS = {
    "shopify": {
        "url": "admin.shopify.com",
        "product_upload": "/products/new",
        "title_selector": 'input[name="title"]',
        "desc_selector": '[aria-label="Description"]',
        "price_selector": 'input[name="price"]',
    },
    "gumroad": {
        "url": "app.gumroad.com",
        "product_upload": "/products/new",
        "title_selector": 'input[name="name"]',
        "price_selector": 'input[name="price"]',
    },
    "github": {
        "url": "github.com",
    },
    "huggingface": {
        "url": "huggingface.co",
    },
}


def plan_rule_based(goal: str, page_context: str, perception=None) -> ActionPlan:
    """Generate a plan using pattern-matching rules. No LLM needed."""
    connector_plan = _parse_connector_goal(goal)
    if connector_plan is not None:
        return connector_plan

    goal_lower = goal.lower().strip()
    steps = []
    reasoning = ""
    confidence = 0.6

    # --- Pattern: direct Hugging Face upload ---
    if "huggingface" in goal_lower:
        hf_plan = _parse_huggingface_upload(goal)
        if hf_plan:
            return hf_plan

    # --- Pattern: Navigation ---
    url_match = re.search(r'(?:go to|open|visit|navigate to)\s+(\S+)', goal_lower)
    if url_match:
        url = url_match.group(1)
        if not url.startswith("http"):
            url = "https://" + url
        steps.append(BrowserAction(
            action="navigate",
            value=url,
            description=f"Navigate to {url}",
        ))
        steps.append(BrowserAction(
            action="snapshot",
            description="Perceive the new page",
        ))
        reasoning = f"Direct navigation to {url}"
        confidence = 0.95
        return ActionPlan(goal=goal, steps=steps, reasoning=reasoning, confidence=confidence, method="rule_based")

    # --- Pattern: Fill a field (checked BEFORE search to avoid "type X in Y" matching search) ---
    fill_match = re.search(r'(?:type|enter|fill|set|put|write)\s+["\'](.+?)["\']\s+(?:in|into)\s+(?:the\s+)?["\']?(.+?)["\']?\s*$', goal_lower)
    if not fill_match:
        fill_match = re.search(r'(?:type|enter|fill|put|write)\s+(.+?)\s+(?:in|into)\s+(?:the\s+)?(.+)', goal_lower)
    if fill_match and perception and perception.interactive_elements:
        value = fill_match.group(1).strip().strip("'\"")
        field_name = fill_match.group(2).strip().strip("'\"")
        best_el = _find_matching_element(field_name, perception.interactive_elements,
                                         roles={"textbox", "searchbox", "combobox"})
        if best_el:
            steps.append(BrowserAction(
                action="fill",
                selector=best_el["selector"],
                value=value,
                description=f"Fill '{best_el['name']}' with: {value}",
            ))
            reasoning = f"Fill field '{best_el['name']}' with '{value}'"
            confidence = 0.85
            return ActionPlan(goal=goal, steps=steps, reasoning=reasoning, confidence=confidence, method="rule_based")

    # --- Pattern: Search ---
    search_match = re.search(r'(?:search|google|look up|find)\s+(?:for\s+)?(.+)', goal_lower)
    if search_match:
        query = search_match.group(1).strip()
        steps.append(BrowserAction(
            action="navigate",
            value=f"https://www.google.com/search?q={query.replace(' ', '+')}",
            description=f"Search Google for: {query}",
        ))
        steps.append(BrowserAction(
            action="snapshot",
            description="Perceive search results",
        ))
        reasoning = f"Google search for '{query}'"
        confidence = 0.9
        return ActionPlan(goal=goal, steps=steps, reasoning=reasoning, confidence=confidence, method="rule_based")

    # --- Pattern: Screenshot ---
    if "screenshot" in goal_lower or "capture" in goal_lower:
        name = "user_request"
        name_match = re.search(r'(?:screenshot|capture)\s+(?:of\s+)?(\w+)', goal_lower)
        if name_match:
            name = name_match.group(1)
        steps.append(BrowserAction(
            action="screenshot",
            value=name,
            description=f"Take screenshot: {name}",
        ))
        reasoning = "User requested a screenshot"
        confidence = 0.95
        return ActionPlan(goal=goal, steps=steps, reasoning=reasoning, confidence=confidence, method="rule_based")

    # --- Pattern: Click something on the current page ---
    click_match = re.search(r'(?:click|press|tap|hit)\s+(?:on\s+)?(?:the\s+)?["\']?(.+?)["\']?\s*$', goal_lower)
    if click_match and perception and perception.interactive_elements:
        target_name = click_match.group(1).strip()
        # Find best matching element
        best_el = _find_matching_element(target_name, perception.interactive_elements)
        if best_el:
            # Check if the element or target name is destructive
            combined = (target_name + " " + best_el.get("name", "")).lower()
            is_destructive = any(d in combined for d in (
                "delete", "remove", "destroy", "reset", "cancel", "unsubscribe",
                "terminate", "revoke", "disable", "drop", "purge", "wipe",
            ))
            steps.append(BrowserAction(
                action="click",
                selector=best_el["selector"],
                description=f"Click: {best_el['name']}",
                governance_required=is_destructive,
            ))
            steps.append(BrowserAction(
                action="snapshot",
                description="Perceive page after click",
                wait_after_ms=1000,
            ))
            reasoning = f"Click element '{best_el['name']}' matching '{target_name}'"
            confidence = 0.8
            return ActionPlan(goal=goal, steps=steps, reasoning=reasoning, confidence=confidence, method="rule_based")

    # --- Pattern: Upload a file ---
    upload_match = re.search(r'(?:upload|attach)\s+(.+?)(?:\s+to\s+(.+))?$', goal_lower)
    if upload_match:
        file_ref = upload_match.group(1).strip()
        # Resolve to actual file path
        file_path = _resolve_file_path(file_ref)
        if file_path:
            steps.append(BrowserAction(
                action="upload",
                selector='input[type="file"]',
                file_path=file_path,
                description=f"Upload file: {file_path}",
                governance_required=True,
            ))
            steps.append(BrowserAction(
                action="snapshot",
                description="Perceive page after upload",
                wait_after_ms=2000,
            ))
            reasoning = f"Upload file '{file_path}'"
            confidence = 0.7
            return ActionPlan(goal=goal, steps=steps, reasoning=reasoning, confidence=confidence, method="rule_based")

    # --- Pattern: Submit a form (fill all visible fields then click submit) ---
    if ("submit" in goal_lower or "send" in goal_lower) and perception and perception.forms:
        form = perception.forms[0]
        if form.get("submit_selector"):
            steps.append(BrowserAction(
                action="click",
                selector=form["submit_selector"],
                description=f"Submit form: {form.get('submit_label', 'Submit')}",
                governance_required=True,
            ))
            steps.append(BrowserAction(
                action="snapshot",
                description="Perceive page after submission",
                wait_after_ms=2000,
            ))
            reasoning = "Submit the first form on the page"
            confidence = 0.6
            return ActionPlan(goal=goal, steps=steps, reasoning=reasoning, confidence=confidence, method="rule_based")

    # --- Fallback: Can't determine plan ---
    steps.append(BrowserAction(
        action="snapshot",
        description="Take a fresh perception snapshot to understand the page",
    ))
    reasoning = f"Could not determine specific actions for: '{goal}'. Taking a snapshot for the LLM planner."
    confidence = 0.2
    return ActionPlan(goal=goal, steps=steps, reasoning=reasoning, confidence=confidence, method="rule_based_fallback")


def _parse_huggingface_upload(goal: str) -> Optional[ActionPlan]:
    """Parse a direct Hugging Face upload intent."""
    goal_lower = goal.lower()
    hf_match = re.search(
        r"(?:upload|push|publish)\s+(.+?)\s+to\s+(?:hugging(?:face)?(?:\.co)?|\bhf)\s*:?\s*([a-z0-9._-]+/[a-z0-9._-]+)?(.*)$",
        goal_lower,
    )
    if not hf_match:
        return None

    file_ref = hf_match.group(1).strip().strip("\"'")
    repo_id = (hf_match.group(2) or "").strip()
    extra = hf_match.group(3) or ""

    if not repo_id:
        repo_match = re.search(r"(?:repo(?:_id)?|repository)\s*=\s*([a-z0-9._-]+/[a-z0-9._-]+)", extra)
        if repo_match:
            repo_id = repo_match.group(1).strip()

    repo_type_match = re.search(r"repo_type\s*=\s*(model|dataset|space)", extra)
    repo_type = repo_type_match.group(1) if repo_type_match else "model"

    path_match = re.search(r"(?:path|path_in_repo|as)\s*=\s*(\"[^\"]+\"|'[^']+'|\S+)", extra)
    path_in_repo = path_match.group(1).strip("\"'") if path_match else ""

    commit_match = re.search(r"(?:commit[-_]?message|message)\s*=\s*\"([^\"]+)\"", extra)
    if not commit_match:
        commit_match = re.search(r"(?:commit[-_]?message|message)\s*=\s*'([^']+)'", extra)
    commit_message = commit_match.group(1) if commit_match else ""

    file_path = _resolve_file_path(file_ref)
    if not file_path:
        return None

    if not path_in_repo:
        path_in_repo = Path(file_path).name

    step = BrowserAction(
        action="huggingface_upload",
        file_path=file_path,
        repo_id=repo_id,
        repo_type=repo_type,
        path_in_repo=path_in_repo,
        commit_message=commit_message,
        description=f"Upload '{file_path}' to Hugging Face repo '{repo_id or 'default'}'",
        governance_required=True,
        wait_after_ms=2000,
    )
    return ActionPlan(goal=goal, steps=[step], reasoning=f"Direct Hugging Face upload of '{file_path}'", confidence=0.75, method="rule_based")


def _find_matching_element(target: str, elements: list[dict],
                           roles: Optional[set] = None) -> Optional[dict]:
    """Find the interactive element whose name best matches the target string."""
    target_lower = target.lower()
    best = None
    best_score = 0

    for el in elements:
        if roles and el.get("role") not in roles:
            continue
        if el.get("disabled"):
            continue

        name = el.get("name", "").lower()
        if not name:
            continue

        # Exact match
        if name == target_lower:
            return el

        # Contains match
        score = 0
        if target_lower in name:
            score = len(target_lower) / len(name)
        elif name in target_lower:
            score = len(name) / len(target_lower) * 0.8

        # Word overlap
        target_words = set(target_lower.split())
        name_words = set(name.split())
        overlap = target_words & name_words
        if overlap:
            score = max(score, len(overlap) / max(len(target_words), len(name_words)))

        if score > best_score:
            best_score = score
            best = el

    return best if best_score > 0.3 else None


def _resolve_file_path(file_ref: str) -> Optional[str]:
    """Resolve a file reference to an actual path on disk."""
    # If it's already an absolute path
    if Path(file_ref).is_absolute() and Path(file_ref).exists():
        return str(Path(file_ref))

    # Try common locations relative to project root
    candidates = [
        ROOT / file_ref,
        ROOT / "artifacts" / file_ref,
        ROOT / "artifacts" / "products" / file_ref,
        ROOT / "training-data" / file_ref,
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    # Try glob matching
    for pattern_dir in [ROOT / "artifacts", ROOT]:
        matches = list(pattern_dir.glob(f"**/{file_ref}*"))
        if matches:
            return str(matches[0])

    return None


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
#  Connector command parsing (Telegram / GitHub)
# ---------------------------------------------------------------------------

def _parse_telegram_goal(goal: str) -> Optional[ActionPlan]:
    """Parse direct Telegram commands into a connector action plan."""
    goal_lower = goal.lower()

    parse_mode = "Markdown"
    parse_mode_match = re.search(r"\bparse\s*mode\b(?:\s*[:=]?)\s*(markdown|html)\b", goal_lower)
    if parse_mode_match:
        parse_mode = parse_mode_match.group(1).strip().capitalize()

    if "telegram" not in goal_lower and " tg " not in f" {goal_lower} ":
        return None

    if re.search(r"\bget\b.*\bupdates\b", goal_lower):
        offset = 0
        limit = 100
        off_match = re.search(r"\boffset\s*[:=]?\s*(\d+)", goal_lower)
        lim_match = re.search(r"\blimit\s*[:=]?\s*(\d+)", goal_lower)
        if off_match:
            offset = int(off_match.group(1))
        if lim_match:
            limit = int(lim_match.group(1))

        return ActionPlan(
            goal=goal,
            steps=[BrowserAction(
                action="telegram_get_updates",
                offset=offset,
                limit=limit,
                description="Fetch Telegram updates.",
                wait_after_ms=800,
            )],
            reasoning="Parsed direct Telegram get_updates request.",
            confidence=0.95,
            method="rule_based",
        )

    if re.search(r"\b(send|message|notify|dm|ping)\b", goal_lower):
        chat_match = re.search(r"(?:chat[_-]?id|chat|to)\s*[:=]?\s*([^-\d]\d+|[-]\d+)", goal, re.IGNORECASE)
        if not chat_match:
            chat_match = re.search(r"(?:chat[_-]?id|chat|to)\s*[:=]?\s*([-\d]+)", goal, re.IGNORECASE)
        quoted = re.search(r'"([^"]+)"', goal)
        if not quoted:
            quoted = re.search(r"'([^']+)'", goal)
        message = quoted.group(1).strip() if quoted else ""

        if not message:
            message_match = re.search(
                r"(?:message|text|say|send|notify|ping)\s+(?:to\s+[-\d]+\s+)?(?P<msg>.+)",
                goal,
                re.IGNORECASE,
            )
            if message_match:
                message = message_match.group("msg").strip()

        if not message:
            return None

        return ActionPlan(
            goal=goal,
            steps=[BrowserAction(
                action="telegram_send",
                chat_id=chat_match.group(1) if chat_match else "",
                parse_mode=parse_mode,
                message=message,
                description=f"Send Telegram message to {chat_match.group(1) if chat_match else 'default chat'}",
                wait_after_ms=500,
            )],
            reasoning="Parsed Telegram send command.",
            confidence=0.94,
            method="rule_based",
        )

    return None


def _parse_github_goal(goal: str) -> Optional[ActionPlan]:
    """Parse direct GitHub commands into a connector action plan."""
    goal_lower = goal.lower()
    codespace_intent = bool(
        re.search(
            r"\b(codespace|code\s+space|notebook|lm\s*notebook|lm-notebook|lmnotebook|notebooklm)\b",
            goal_lower,
        )
    )
    if "github" not in goal_lower and " gh " not in f" {goal_lower} " and not codespace_intent:
        return None

    repo_match = re.search(
        r"(?:repo|repository|in)\s+([a-z0-9_.-]+/[a-z0-9_.-]+)",
        goal,
        re.IGNORECASE,
    )
    if not repo_match:
        repo_match = re.search(
            r"\b([a-z0-9_.-]+/[a-z0-9_.-]+)\b",
            goal,
            re.IGNORECASE,
        )
    if not repo_match:
        return None
    repo = repo_match.group(1)

    if re.search(r"\blist\b.*\b(codespace|code\s+space|notebook|lm\s*notebook|lm-notebook|lmnotebook|notebooklm)\b", goal_lower):
        return ActionPlan(
            goal=goal,
            steps=[BrowserAction(
                action="github_codespace_list",
                repo=repo,
                github_action="list_codespaces",
                metadata={"repo": repo},
                description=f"List GitHub codespaces for {repo}",
                wait_after_ms=700,
            )],
            reasoning="Parsed GitHub Codespaces list request.",
            confidence=0.93,
            method="rule_based",
        )

    if re.search(
        r"\b(open|start|create|spin|launch)\b.*\b(codespace|code\s+space|notebook|lm\s*notebook|lm-notebook|lmnotebook|notebooklm)\b",
        goal_lower,
    ):
        metadata: dict[str, Any] = {}
        branch_match = re.search(r"branch\s*[:=]?\s*([^\s,;]+)", goal_lower)
        machine_match = re.search(r"machine\s*[:=]?\s*([^\s,;]+)", goal_lower)
        name_match = re.search(r"(?:name|label|notebook)\s*[:=]?\s*([a-z0-9-]+)", goal_lower, re.IGNORECASE)
        if branch_match:
            metadata["branch"] = branch_match.group(1).strip()
        if machine_match:
            metadata["machine"] = machine_match.group(1).strip()
        if name_match:
            metadata["name"] = name_match.group(1).strip()
        return ActionPlan(
            goal=goal,
            steps=[BrowserAction(
                action="github_codespace_create",
                repo=repo,
                github_action="create_codespace",
                metadata=metadata,
                description=f"Create GitHub codespace in {repo}",
                governance_required=True,
                wait_after_ms=1200,
            )],
            reasoning="Parsed GitHub Codespace create request.",
            confidence=0.92,
            method="rule_based",
        )

    if re.search(
        r"\b(stop|shutdown|delete|close|kill|end)\b.*\b(codespace|code\s+space|notebook|lm\s*notebook|lm-notebook|lmnotebook|notebooklm)\b",
        goal_lower,
    ):
        stop_name = None
        stop_match = re.search(r"\b(?:name|label|notebook)\s*[:=]?\s*([a-z0-9-]+)", goal, re.IGNORECASE)
        if not stop_match:
            stop_match = re.search(r"\b(?:codespace|notebook)[:= ]+([a-z0-9-]+)", goal, re.IGNORECASE)
        if stop_match:
            stop_name = stop_match.group(1).strip()
        metadata = {"name": stop_name} if stop_name else {}
        return ActionPlan(
            goal=goal,
            steps=[BrowserAction(
                action="github_codespace_stop",
                repo=repo,
                github_action="stop_codespace",
                metadata=metadata,
                description=f"Stop codespace in {repo}",
                governance_required=True,
                wait_after_ms=1200,
            )],
            reasoning="Parsed GitHub Codespace stop request.",
            confidence=0.91,
            method="rule_based",
        )

    if re.search(r"\blist\b.*\bissues?\b", goal_lower):
        return ActionPlan(
            goal=goal,
            steps=[BrowserAction(
                action="github_issue_list",
                repo=repo,
                github_action="list_issues",
                description=f"List GitHub issues for {repo}",
                wait_after_ms=700,
            )],
            reasoning="Parsed GitHub issue listing request.",
            confidence=0.9,
            method="rule_based",
        )

    if re.search(r"\blist\b.*\b(pr|pull)\b", goal_lower):
        return ActionPlan(
            goal=goal,
            steps=[BrowserAction(
                action="github_pr_list",
                repo=repo,
                github_action="list_prs",
                description=f"List GitHub pull requests for {repo}",
                wait_after_ms=700,
            )],
            reasoning="Parsed GitHub PR listing request.",
            confidence=0.9,
            method="rule_based",
        )

    title_match = re.search(
        r"(?:title|called|name)\s*[:=]\s*(\"[^\"]+\"|'[^']+')",
        goal,
    )
    title = title_match.group(1) if title_match else ""
    if title.startswith(("\"", "'")) and title.endswith(("\"", "'")):
        title = title[1:-1]

    body_match = re.search(
        r"(?:body|details|description)\s*[:=]\s*(\"[^\"]+\"|'[^']+')",
        goal,
    )
    body = body_match.group(1) if body_match else ""
    if body.startswith(("\"", "'")) and body.endswith(("\"", "'")):
        body = body[1:-1]

    if re.search(r"\bcreate\b.*\bissue\b", goal_lower):
        if not title:
            return None
        return ActionPlan(
            goal=goal,
            steps=[BrowserAction(
                action="github_issue_create",
                repo=repo,
                github_action="create_issue",
                value=title[:200],
                body=body,
                description=f"Create issue in {repo}",
                governance_required=True,
                wait_after_ms=1200,
            )],
            reasoning="Parsed GitHub issue create command.",
            confidence=0.93,
            method="rule_based",
        )

    if re.search(r"\bcreate\b.*\b(pr|pull request)\b", goal_lower):
        base_match = re.search(r"base\s*[:=]\s*([\w.-]+)", goal_lower)
        head_match = re.search(r"head\s*[:=]\s*([\w.-]+)", goal_lower)
        if not title:
            return None
        return ActionPlan(
            goal=goal,
            steps=[BrowserAction(
                action="github_pr_create",
                repo=repo,
                github_action="create_pr",
                value=title[:200],
                body=body,
                metadata={
                    "base": base_match.group(1) if base_match else "main",
                    "head": head_match.group(1) if head_match else "",
                },
                description=f"Create PR in {repo}",
                governance_required=True,
                wait_after_ms=1200,
            )],
            reasoning="Parsed GitHub PR create command.",
            confidence=0.92,
            method="rule_based",
        )

    number_match = re.search(r"(?:#|issue\s*|pr\s*|pull request\s*)(\d+)", goal_lower)
    number = int(number_match.group(1)) if number_match else None
    if number is None:
        return None

    if re.search(r"\bclose\b.*\bissue\b", goal_lower):
        return ActionPlan(
            goal=goal,
            steps=[BrowserAction(
                action="github_issue_close",
                repo=repo,
                github_action="close_issue",
                metadata={"number": number},
                description=f"Close issue #{number} in {repo}",
                governance_required=True,
                wait_after_ms=1000,
            )],
            reasoning="Parsed GitHub close issue command.",
            confidence=0.92,
            method="rule_based",
        )

    if re.search(r"\bcomment\b", goal_lower):
        comment = body if body else title
        if not comment:
            comment_match = re.search(
                r"\bcomment\b\s+(?:(?:on\s+(?:issue|pr|pull request)\s*#?\d+\s+)?(?P<msg>.+))",
                goal,
                re.IGNORECASE,
            )
            if comment_match:
                comment = comment_match.group("msg").strip()
        if not comment:
            return None
        return ActionPlan(
            goal=goal,
            steps=[BrowserAction(
                action="github_issue_comment",
                repo=repo,
                github_action="comment",
                metadata={"number": number},
                message=comment,
                description=f"Comment on item #{number} in {repo}",
                governance_required=True,
                wait_after_ms=1000,
            )],
            reasoning="Parsed GitHub comment command.",
            confidence=0.91,
            method="rule_based",
        )

    if re.search(r"\bmerge\b", goal_lower):
        return ActionPlan(
            goal=goal,
            steps=[BrowserAction(
                action="github_pr_merge",
                repo=repo,
                github_action="merge_pr",
                metadata={"number": number},
                description=f"Merge PR #{number} in {repo}",
                governance_required=True,
                wait_after_ms=1200,
            )],
            reasoning="Parsed GitHub PR merge command.",
            confidence=0.9,
            method="rule_based",
        )

    return None


def _parse_connector_goal(goal: str) -> Optional[ActionPlan]:
    """Apply connector parsers before normal browser rule patterns."""
    return _parse_telegram_goal(goal) or _parse_github_goal(goal)
# ---------------------------------------------------------------------------
#  Main planner interface
# ---------------------------------------------------------------------------

async def create_plan(goal: str, perception=None, use_llm: bool = True) -> ActionPlan:
    """
    Create an ActionPlan for a user goal.

    Strategy:
    1. Try rule-based planning first (fast, free, deterministic)
    2. If rule-based confidence is low (<0.5), escalate to LLM planner
    3. If LLM fails, return the rule-based plan anyway
    """
    # Build page context string
    if perception:
        page_context = perception.to_planner_prompt()
    else:
        page_context = "No page perception available. The browser may not be on any page yet."

    # Step 1: Try rule-based planning
    rule_plan = plan_rule_based(goal, page_context, perception)

    # If rule-based is confident enough, use it directly
    if rule_plan.confidence >= 0.7:
        logger.info(f"Rule-based plan: {rule_plan.confidence:.0%} confidence, {len(rule_plan.steps)} steps")
        return rule_plan

    # Step 2: If low confidence, try LLM
    if use_llm and rule_plan.confidence < 0.7:
        logger.info(f"Rule-based confidence low ({rule_plan.confidence:.0%}), escalating to LLM planner")
        llm_plan = await plan_with_llm(goal, page_context)
        if llm_plan and llm_plan.steps:
            logger.info(f"LLM plan: {llm_plan.confidence:.0%} confidence, {len(llm_plan.steps)} steps via {llm_plan.method}")
            return llm_plan
        logger.info("LLM planner unavailable, using rule-based fallback")

    # Step 3: Return whatever we have
    return rule_plan


# ---------------------------------------------------------------------------
#  Training data generation
# ---------------------------------------------------------------------------

def log_plan_result(plan: ActionPlan, success: bool, error: str = ""):
    """Log a completed plan as training data for the flywheel."""
    log_path = ROOT / "training-data" / "aetherbrowse" / "planning_pairs.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    pair = {
        "timestamp": time.time(),
        "input": {
            "goal": plan.goal,
            "step_count": len(plan.steps),
            "method": plan.method,
        },
        "output": {
            "success": success,
            "confidence": plan.confidence,
            "steps": [s.to_dict() for s in plan.steps],
            "error": error,
        },
        "source": "aetherbrowse_planner",
    }

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(pair) + "\n")
