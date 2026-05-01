#!/usr/bin/env python3
"""
trajectory_logger.py - Log AetherBrowse agent sessions as training trajectories.

Hooks into the AetherBrowse runtime to capture the full PERCEIVE→PLAN→GOVERN→EXECUTE
loop as structured training data. Each session is exported as a JSONL entry
compatible with SCBE training schema v3.0.0.

Usage:
    from trajectory_logger import TrajectoryLogger
    logger = TrajectoryLogger(output_dir="training-data/agentic_coding/sessions")
    logger.start_session(task="Fix broken nav link")
    logger.log_perception(page_state={...})
    logger.log_plan(actions=[...])
    logger.log_governance(decision="ALLOW", layers=[3,7,12])
    logger.log_execution(result="success", diff="...")
    logger.finish_session(outcome="success")

Author: Issac Davis
Date: 2026-04-23
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class TrajectoryLogger:
    """Logger for agent sessions that exports training trajectories."""
    
    def __init__(self, output_dir: str = "training-data/agentic_coding/sessions"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = None
        self.turns = []
    
    def start_session(self, task: str, user_id: Optional[str] = None,
                      repo: Optional[str] = None, branch: Optional[str] = None):
        """Begin logging a new agent session."""
        self.session = {
            "session_id": str(uuid.uuid4())[:8],
            "task": task,
            "user_id": user_id or "anonymous",
            "repo": repo or "unknown",
            "branch": branch or "main",
            "started_at": datetime.utcnow().isoformat(),
            "tongues": [],
            "layers": [],
        }
        self.turns = []
    
    def log_perception(self, page_state: Dict[str, Any], agent: str = "Polly"):
        """Log the PERCEIVE phase."""
        self.turns.append({
            "phase": "PERCEIVE",
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat(),
            "observation": page_state,
        })
    
    def log_plan(self, actions: List[Dict[str, Any]], agent: str = "Zara",
                 reasoning: Optional[str] = None):
        """Log the PLAN phase."""
        self.turns.append({
            "phase": "PLAN",
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat(),
            "actions": actions,
            "reasoning": reasoning or "",
        })
    
    def log_governance(self, decision: str, layers: List[int],
                       scores: Optional[Dict[str, float]] = None,
                       agent: str = "Aria"):
        """Log the GOVERN phase."""
        self.turns.append({
            "phase": "GOVERN",
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat(),
            "decision": decision,
            "layers": layers,
            "scores": scores or {},
        })
        # Track which layers were activated
        self.session["layers"] = sorted(list(set(self.session.get("layers", []) + layers)))
    
    def log_execution(self, result: str, action_type: str,
                      output: Optional[str] = None,
                      diff: Optional[str] = None,
                      agent: str = "Kael"):
        """Log the EXECUTE phase."""
        self.turns.append({
            "phase": "EXECUTE",
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat(),
            "action_type": action_type,
            "result": result,
            "output": output or "",
            "diff": diff or "",
        })
    
    def log_error(self, error: str, recovery_action: Optional[str] = None):
        """Log an error and recovery attempt."""
        self.turns.append({
            "phase": "ERROR",
            "timestamp": datetime.utcnow().isoformat(),
            "error": error,
            "recovery_action": recovery_action or "",
        })
    
    def finish_session(self, outcome: str, tests_passed: Optional[bool] = None,
                       notes: Optional[str] = None):
        """Finalize the session and export to JSONL."""
        if not self.session:
            return
        
        self.session.update({
            "finished_at": datetime.utcnow().isoformat(),
            "outcome": outcome,
            "tests_passed": tests_passed,
            "notes": notes or "",
            "turns": self.turns,
            "turn_count": len(self.turns),
        })
        
        # Convert to SFT format
        sft_record = self._to_sft_format()
        
        # Write to file
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        output_file = self.output_dir / f"session_{date_str}.jsonl"
        
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(sft_record, ensure_ascii=False) + '\n')
        
        # Reset
        session_id = self.session["session_id"]
        self.session = None
        self.turns = []
        
        return session_id
    
    def _to_sft_format(self) -> Dict:
        """Convert the session to SCBE SFT schema."""
        # Build messages from turns
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": self.session["task"]},
        ]
        
        for turn in self.turns:
            phase = turn["phase"]
            
            if phase == "PERCEIVE":
                obs = json.dumps(turn["observation"], ensure_ascii=False)[:500]
                messages.append({
                    "role": "assistant",
                    "content": f"<think>Perceiving current state...</think>\n<observe>\n{obs}\n</observe>"
                })
            
            elif phase == "PLAN":
                actions = json.dumps(turn["actions"], ensure_ascii=False)[:500]
                reasoning = turn.get("reasoning", "")
                messages.append({
                    "role": "assistant",
                    "content": f"<think>\n{reasoning}\n</think>\n<plan>\n{actions}\n</plan>"
                })
            
            elif phase == "GOVERN":
                decision = turn["decision"]
                layers = turn["layers"]
                messages.append({
                    "role": "assistant",
                    "content": f"<governance decision=\"{decision}\" layers=\"{','.join(map(str, layers))}\" />"
                })
            
            elif phase == "EXECUTE":
                result = turn["result"]
                action_type = turn["action_type"]
                messages.append({
                    "role": "assistant",
                    "content": f"<execute type=\"{action_type}\">\n{result}\n</execute>"
                })
                # Tool result
                messages.append({
                    "role": "tool",
                    "content": f"[{action_type}] {result}"
                })
            
            elif phase == "ERROR":
                error = turn["error"]
                recovery = turn.get("recovery_action", "")
                messages.append({
                    "role": "assistant",
                    "content": f"<error>\n{error}\n</error>\n<recover>\n{recovery}\n</recover>"
                })
        
        # Final finish
        messages.append({
            "role": "assistant",
            "content": f"<finish outcome=\"{self.session['outcome']}\" />"
        })
        
        return {
            "id": f"session-{self.session['session_id']}",
            "category": "agentic-trajectory",
            "messages": messages,
            "metadata": {
                "source": "scbe_aethermoore",
                "version": "3.3.0",
                "generator": "trajectory_logger.py",
                "session_id": self.session["session_id"],
                "repo": self.session["repo"],
                "branch": self.session["branch"],
                "tongues": self.session.get("tongues", ["KO"]),
                "layers": self.session.get("layers", [1, 14]),
                "difficulty": "medium",
                "turn_count": len(self.turns),
                "outcome": self.session["outcome"],
                "tests_passed": self.session.get("tests_passed"),
            }
        }
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for this session."""
        return (
            "You are an SCBE agent operating within the AetherBrowse runtime. "
            "You follow the PERCEIVE→PLAN→GOVERN→EXECUTE loop. "
            "Always verify before executing. Always log your actions."
        )


# ---------------------------------------------------------------------------
#  Standalone utility: Convert existing session logs
# ---------------------------------------------------------------------------

def convert_existing_logs(input_dir: str, output_dir: str):
    """Convert existing AetherBrowse session JSONs to SFT format."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger = TrajectoryLogger(output_dir=output_dir)
    
    for json_file in input_path.glob("*.json"):
        try:
            data = json.loads(json_file.read_text())
            # Adapt to your existing session log format
            logger.start_session(
                task=data.get("task", "unknown"),
                repo=data.get("repo", "unknown"),
            )
            
            for turn in data.get("turns", []):
                phase = turn.get("phase", "").upper()
                if phase == "PERCEIVE":
                    logger.log_perception(turn.get("observation", {}))
                elif phase == "PLAN":
                    logger.log_plan(turn.get("actions", []), reasoning=turn.get("reasoning"))
                elif phase == "EXECUTE":
                    logger.log_execution(
                        result=turn.get("result", ""),
                        action_type=turn.get("action_type", "unknown"),
                        diff=turn.get("diff"),
                    )
            
            logger.finish_session(outcome=data.get("outcome", "unknown"))
            print(f"Converted: {json_file.name}")
            
        except Exception as e:
            print(f"Failed: {json_file.name} — {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "convert":
        # python trajectory_logger.py convert <input_dir> <output_dir>
        convert_existing_logs(sys.argv[2], sys.argv[3])
    else:
        # Demo
        logger = TrajectoryLogger()
        logger.start_session(task="Add a new API endpoint")
        logger.log_perception({"page": "api_server.py", "lines": 200})
        logger.log_plan([{"action": "add_endpoint", "path": "/v1/new"}])
        logger.log_governance("ALLOW", [3, 7, 12])
        logger.log_execution("success", "edit_file", diff="+ @app.post('/v1/new')")
        logger.finish_session("success", tests_passed=True)
        print("Demo session logged.")
