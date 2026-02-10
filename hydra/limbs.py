"""
HYDRA Limbs - Execution Backends
================================

The limbs that execute actions in different environments:
- BrowserLimb: Multi-tab browser control
- TerminalLimb: Shell command execution
- APILimb: HTTP API calls

All limbs are governed by SCBE before execution.
"""

import asyncio
import subprocess
import os
import sys
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import hashlib
import json
import uuid

# Add parent for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class HydraLimb(ABC):
    """Base class for execution limbs."""

    limb_type: str = "base"

    def __init__(self, scbe_url: str = "http://127.0.0.1:8080"):
        self.limb_id = f"{self.limb_type}-{uuid.uuid4().hex[:8]}"
        self.scbe_url = scbe_url
        self.active = False
        self.action_count = 0

    @abstractmethod
    async def execute(self, action: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action."""
        pass

    async def activate(self) -> bool:
        """Activate this limb."""
        self.active = True
        print(f"[{self.limb_type.upper()}] Limb {self.limb_id} activated")
        return True

    async def deactivate(self) -> None:
        """Deactivate this limb."""
        self.active = False
        print(f"[{self.limb_type.upper()}] Limb {self.limb_id} deactivated")

    async def _check_governance(self, action: str, target: str, sensitivity: float = 0.5) -> Dict[str, Any]:
        """Check SCBE governance before execution."""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.scbe_url}/v1/authorize",
                    json={
                        "agent_id": self.limb_id,
                        "action": action.upper(),
                        "target": target,
                        "context": {"sensitivity": sensitivity}
                    },
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            print(f"[GOVERNANCE] Check failed: {e}")

        # Default allow if SCBE unavailable
        return {"decision": "ALLOW", "score": 0.5}


class BrowserLimb(HydraLimb):
    """
    Browser execution limb.

    Supports multiple browser backends and multi-tab operation.
    Each tab can be controlled independently.
    """

    limb_type = "browser"

    def __init__(
        self,
        backend_type: str = "chrome_mcp",
        tab_id: int = None,
        scbe_url: str = "http://127.0.0.1:8080"
    ):
        super().__init__(scbe_url)
        self.backend_type = backend_type
        self.tab_id = tab_id
        self.current_url = ""
        self._backend = None

    async def activate(self) -> bool:
        """Activate browser limb."""
        await super().activate()

        # Import the appropriate backend
        try:
            if self.backend_type == "chrome_mcp":
                from agents.browsers import ChromeMCPBackend
                self._backend = ChromeMCPBackend(tab_id=self.tab_id)
            elif self.backend_type == "playwright":
                from agents.browsers import PlaywrightBackend
                self._backend = PlaywrightBackend(headless=True)
            elif self.backend_type == "selenium":
                from agents.browsers import SeleniumBackend
                self._backend = SeleniumBackend(headless=True)
            elif self.backend_type == "cdp":
                from agents.browsers import CDPBackend
                self._backend = CDPBackend()
            else:
                print(f"[BROWSER] Unknown backend: {self.backend_type}")
                return False

            await self._backend.initialize()
            return True

        except ImportError as e:
            print(f"[BROWSER] Backend not available: {e}")
            # Continue without backend for mock operation
            return True

    async def execute(self, action: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute browser action."""
        self.action_count += 1

        # Check governance
        sensitivity = self._calculate_sensitivity(action, target)
        gov = await self._check_governance(action, target, sensitivity)

        if gov.get("decision") == "DENY":
            return {
                "success": False,
                "decision": "DENY",
                "action": action,
                "target": target,
                "reason": gov.get("explanation", "Blocked by SCBE")
            }

        # Execute via backend
        result = {"success": True, "decision": gov.get("decision", "ALLOW")}

        if self._backend:
            try:
                if action == "navigate":
                    data = await self._backend.navigate(target)
                    self.current_url = target
                    result["data"] = data

                elif action == "click":
                    data = await self._backend.click(target)
                    result["data"] = data

                elif action == "type":
                    text = params.get("text", "")
                    data = await self._backend.type_text(target, text)
                    result["data"] = data

                elif action == "screenshot":
                    data = await self._backend.screenshot()
                    result["data"] = {"bytes": len(data)}

                elif action == "scroll":
                    direction = params.get("direction", "down")
                    amount = params.get("amount", 300)
                    data = await self._backend.scroll(direction, amount)
                    result["data"] = data

                elif action == "get_content":
                    content = await self._backend.get_page_content()
                    result["data"] = {"length": len(content)}

            except Exception as e:
                result["success"] = False
                result["error"] = str(e)

        else:
            # Mock execution
            result["mock"] = True
            result["would_execute"] = {"action": action, "target": target, "params": params}

        result["action"] = action
        result["target"] = target
        result["limb_id"] = self.limb_id
        result["tab_id"] = self.tab_id

        return result

    def _calculate_sensitivity(self, action: str, target: str) -> float:
        """Calculate action sensitivity for governance."""
        # Base sensitivity by action
        base = {
            "navigate": 0.3,
            "click": 0.4,
            "type": 0.5,
            "submit": 0.7,
            "download": 0.8,
            "screenshot": 0.2,
            "scroll": 0.1,
        }.get(action, 0.5)

        # Increase for sensitive domains
        target_lower = target.lower()
        if any(x in target_lower for x in ["bank", "pay", "finance", "crypto"]):
            base = min(1.0, base + 0.4)
        elif any(x in target_lower for x in ["login", "auth", "password"]):
            base = min(1.0, base + 0.3)
        elif any(x in target_lower for x in ["admin", "sudo", "root"]):
            base = min(1.0, base + 0.5)

        return base


class TerminalLimb(HydraLimb):
    """
    Terminal execution limb.

    Executes shell commands with SCBE governance.
    Dangerous commands are blocked or escalated.
    """

    limb_type = "terminal"

    # Commands that require escalation
    DANGEROUS_COMMANDS = [
        "rm -rf", "rm -r", "rmdir", "del /s",
        "format", "fdisk", "mkfs",
        "dd if=", ":(){ :|:& };:",
        "> /dev/sd", "chmod 777",
        "curl | sh", "wget | sh",
        "sudo", "su -", "runas"
    ]

    # Commands that are always blocked
    BLOCKED_COMMANDS = [
        "rm -rf /",
        "rm -rf /*",
        ":(){ :|:& };:",
        "> /dev/sda",
    ]

    def __init__(
        self,
        shell: str = None,
        cwd: str = None,
        scbe_url: str = "http://127.0.0.1:8080"
    ):
        super().__init__(scbe_url)

        # Detect shell
        if shell is None:
            if sys.platform == "win32":
                shell = "powershell"
            else:
                shell = os.environ.get("SHELL", "/bin/bash")

        self.shell = shell
        self.cwd = cwd or os.getcwd()

    async def execute(self, action: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute terminal command."""
        self.action_count += 1
        command = target

        # Check for blocked commands
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in command:
                return {
                    "success": False,
                    "decision": "DENY",
                    "action": action,
                    "command": command,
                    "reason": "Command is permanently blocked for safety"
                }

        # Check sensitivity
        sensitivity = 0.3
        for dangerous in self.DANGEROUS_COMMANDS:
            if dangerous in command:
                sensitivity = 0.9
                break

        # Check governance
        gov = await self._check_governance("EXECUTE", command, sensitivity)

        if gov.get("decision") == "DENY":
            return {
                "success": False,
                "decision": "DENY",
                "command": command,
                "reason": gov.get("explanation", "Blocked by SCBE")
            }

        if gov.get("decision") == "ESCALATE":
            return {
                "success": False,
                "decision": "ESCALATE",
                "command": command,
                "reason": "Command requires human approval",
                "sensitivity": sensitivity
            }

        # Execute command
        try:
            if sys.platform == "win32":
                result = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.cwd
                )
            else:
                result = await asyncio.create_subprocess_exec(
                    self.shell, "-c", command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.cwd
                )

            stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=30.0)

            return {
                "success": result.returncode == 0,
                "decision": gov.get("decision", "ALLOW"),
                "command": command,
                "returncode": result.returncode,
                "stdout": stdout.decode("utf-8", errors="replace")[:5000],
                "stderr": stderr.decode("utf-8", errors="replace")[:1000],
                "limb_id": self.limb_id
            }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "decision": "QUARANTINE",
                "command": command,
                "error": "Command timed out after 30s"
            }

        except Exception as e:
            return {
                "success": False,
                "decision": "ERROR",
                "command": command,
                "error": str(e)
            }


class APILimb(HydraLimb):
    """
    API execution limb.

    Makes HTTP requests with SCBE governance.
    Integrates with AI Workflow Architect and other services.
    """

    limb_type = "api"

    def __init__(
        self,
        base_url: str = None,
        headers: Dict[str, str] = None,
        scbe_url: str = "http://127.0.0.1:8080"
    ):
        super().__init__(scbe_url)
        self.base_url = base_url or ""
        self.default_headers = headers or {"Content-Type": "application/json"}

    async def execute(self, action: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API call."""
        self.action_count += 1

        method = params.get("method", "GET").upper()
        url = target if target.startswith("http") else f"{self.base_url}{target}"
        body = params.get("body", {})
        headers = {**self.default_headers, **params.get("headers", {})}

        # Calculate sensitivity
        sensitivity = 0.3
        if method in ["POST", "PUT", "PATCH", "DELETE"]:
            sensitivity = 0.6
        if "api_key" in str(body).lower() or "token" in str(body).lower():
            sensitivity = 0.8
        if any(x in url.lower() for x in ["bank", "pay", "transfer"]):
            sensitivity = 0.95

        # Check governance
        gov = await self._check_governance(f"API_{method}", url, sensitivity)

        if gov.get("decision") == "DENY":
            return {
                "success": False,
                "decision": "DENY",
                "url": url,
                "method": method,
                "reason": gov.get("explanation", "Blocked by SCBE")
            }

        # Execute request
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    json=body if method != "GET" else None,
                    params=body if method == "GET" else None,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    response_text = await resp.text()

                    try:
                        response_json = json.loads(response_text)
                    except json.JSONDecodeError:
                        response_json = None

                    return {
                        "success": resp.status < 400,
                        "decision": gov.get("decision", "ALLOW"),
                        "url": url,
                        "method": method,
                        "status": resp.status,
                        "response": response_json or response_text[:2000],
                        "limb_id": self.limb_id
                    }

        except Exception as e:
            return {
                "success": False,
                "decision": "ERROR",
                "url": url,
                "method": method,
                "error": str(e)
            }


class MultiTabBrowserLimb(HydraLimb):
    """
    Multi-tab browser limb.

    Controls multiple browser tabs simultaneously.
    Each tab is an independent execution context.
    """

    limb_type = "multi_browser"

    def __init__(
        self,
        backend_type: str = "playwright",
        max_tabs: int = 6,
        scbe_url: str = "http://127.0.0.1:8080"
    ):
        super().__init__(scbe_url)
        self.backend_type = backend_type
        self.max_tabs = max_tabs
        self.tabs: Dict[str, BrowserLimb] = {}

    async def activate(self) -> bool:
        """Activate multi-tab browser."""
        await super().activate()
        return True

    async def create_tab(self, tab_name: str = None) -> str:
        """Create a new browser tab."""
        if len(self.tabs) >= self.max_tabs:
            return None

        tab_id = tab_name or f"tab-{len(self.tabs)}"
        tab = BrowserLimb(
            backend_type=self.backend_type,
            tab_id=len(self.tabs),
            scbe_url=self.scbe_url
        )
        await tab.activate()
        self.tabs[tab_id] = tab

        print(f"[MULTI-TAB] Created tab: {tab_id}")
        return tab_id

    async def execute(self, action: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute on specified tab or create new one."""
        tab_id = params.get("tab_id")

        if action == "create_tab":
            new_tab_id = await self.create_tab(target)
            return {"success": True, "tab_id": new_tab_id}

        if action == "list_tabs":
            return {
                "success": True,
                "tabs": list(self.tabs.keys()),
                "count": len(self.tabs)
            }

        if action == "close_tab":
            if tab_id in self.tabs:
                await self.tabs[tab_id].deactivate()
                del self.tabs[tab_id]
                return {"success": True, "closed": tab_id}
            return {"success": False, "error": "Tab not found"}

        # Execute on specified tab
        if not tab_id:
            # Use first tab or create one
            if not self.tabs:
                tab_id = await self.create_tab()
            else:
                tab_id = list(self.tabs.keys())[0]

        if tab_id not in self.tabs:
            return {"success": False, "error": f"Tab {tab_id} not found"}

        result = await self.tabs[tab_id].execute(action, target, params)
        result["tab_id"] = tab_id
        return result

    async def execute_parallel(self, commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute multiple commands in parallel across tabs.

        This is the "Hydra" power - multiple heads working simultaneously.
        """
        # Ensure we have enough tabs
        while len(self.tabs) < len(commands) and len(self.tabs) < self.max_tabs:
            await self.create_tab()

        # Assign commands to tabs
        tasks = []
        tab_ids = list(self.tabs.keys())

        for i, cmd in enumerate(commands):
            if i < len(tab_ids):
                tab_id = tab_ids[i]
                cmd["tab_id"] = tab_id
                tasks.append(self.execute(cmd["action"], cmd.get("target", ""), cmd))

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            r if isinstance(r, dict) else {"success": False, "error": str(r)}
            for r in results
        ]
