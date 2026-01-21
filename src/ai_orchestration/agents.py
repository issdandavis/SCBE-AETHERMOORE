"""
AI Agent Framework
==================

Defines agent types, capabilities, and communication protocols.
Agents can be specialized roles like security, research, business, etc.

AGENT TYPES:
============
- SecurityAgent: Monitors threats, audits, compliance
- ResearchAgent: Knowledge lookup, paper search, analysis
- BusinessAgent: Portfolio management, reports, projections
- EngineerAgent: Code generation, testing, debugging
- AnalystAgent: Data analysis, visualization, insights
- CoordinatorAgent: Task routing, load balancing, orchestration

Version: 1.0.0
"""

import uuid
import time
import json
import hashlib
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from abc import ABC, abstractmethod


class AgentRole(Enum):
    """Predefined agent roles."""
    SECURITY = "security"
    RESEARCH = "research"
    BUSINESS = "business"
    ENGINEER = "engineer"
    ANALYST = "analyst"
    COORDINATOR = "coordinator"
    CUSTOM = "custom"


class AgentStatus(Enum):
    """Agent operational status."""
    IDLE = "idle"
    BUSY = "busy"
    PAUSED = "paused"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class AgentCapability:
    """Defines what an agent can do."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    requires_approval: bool = False
    max_execution_time: int = 300  # seconds
    cost_estimate: float = 0.0  # for tracking resource usage


@dataclass
class AgentMessage:
    """Secure message between agents."""
    id: str
    sender_id: str
    receiver_id: str
    timestamp: datetime
    content: str
    encrypted: bool
    signature: str
    message_type: str  # request, response, notification, error
    correlation_id: Optional[str] = None  # links request/response
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
            "encrypted": self.encrypted,
            "signature": self.signature,
            "message_type": self.message_type,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }


@dataclass
class AgentConfig:
    """Agent configuration."""
    role: AgentRole
    name: str
    description: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    max_concurrent_tasks: int = 5
    memory_limit_mb: int = 1024
    allowed_communications: List[str] = field(default_factory=list)  # agent IDs
    knowledge_bases: List[str] = field(default_factory=list)  # science pack names
    custom_prompts: Dict[str, str] = field(default_factory=dict)


class Agent(ABC):
    """
    Base class for AI agents in the orchestration system.

    Each agent runs locally, has defined capabilities, and communicates
    securely with other agents using the SCBE encryption layers.
    """

    def __init__(self, config: AgentConfig):
        self.id = str(uuid.uuid4())
        self.config = config
        self.status = AgentStatus.IDLE
        self.created_at = datetime.now()
        self.last_active = datetime.now()
        self.task_count = 0
        self.error_count = 0
        self.message_queue: List[AgentMessage] = []
        self.knowledge_cache: Dict[str, Any] = {}
        self._handlers: Dict[str, Callable] = {}

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def role(self) -> AgentRole:
        return self.config.role

    @property
    def capabilities(self) -> List[AgentCapability]:
        return self.config.capabilities

    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for a message type."""
        self._handlers[message_type] = handler

    async def receive_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Receive and process a message."""
        self.last_active = datetime.now()
        self.message_queue.append(message)

        # Find handler
        handler = self._handlers.get(message.message_type)
        if handler:
            try:
                response_content = await handler(message)
                if response_content:
                    return AgentMessage(
                        id=str(uuid.uuid4()),
                        sender_id=self.id,
                        receiver_id=message.sender_id,
                        timestamp=datetime.now(),
                        content=response_content,
                        encrypted=message.encrypted,
                        signature="",  # Will be signed by security layer
                        message_type="response",
                        correlation_id=message.id,
                    )
            except Exception as e:
                self.error_count += 1
                return AgentMessage(
                    id=str(uuid.uuid4()),
                    sender_id=self.id,
                    receiver_id=message.sender_id,
                    timestamp=datetime.now(),
                    content=json.dumps({"error": str(e)}),
                    encrypted=message.encrypted,
                    signature="",
                    message_type="error",
                    correlation_id=message.id,
                )

        return None

    @abstractmethod
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task. Must be implemented by subclasses."""
        pass

    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "status": self.status.value,
            "task_count": self.task_count,
            "error_count": self.error_count,
            "last_active": self.last_active.isoformat(),
            "capabilities": [c.name for c in self.capabilities],
        }

    def load_knowledge(self, pack_name: str, data: Dict[str, Any]):
        """Load knowledge from a science pack into cache."""
        self.knowledge_cache[pack_name] = data


# =============================================================================
# SPECIALIZED AGENTS
# =============================================================================

class SecurityAgent(Agent):
    """
    Agent specialized for security monitoring, threat detection, and compliance.

    Capabilities:
    - Monitor system for threats
    - Audit agent communications
    - Check compliance rules
    - Generate security reports
    """

    def __init__(self, name: str = "SecurityGuard"):
        config = AgentConfig(
            role=AgentRole.SECURITY,
            name=name,
            description="Monitors threats, audits communications, ensures compliance",
            capabilities=[
                AgentCapability(
                    name="threat_scan",
                    description="Scan input for security threats",
                    input_schema={"content": "string"},
                    output_schema={"threats": "list", "risk_level": "string"},
                ),
                AgentCapability(
                    name="audit_log",
                    description="Review and audit activity logs",
                    input_schema={"log_entries": "list"},
                    output_schema={"findings": "list", "compliance": "boolean"},
                ),
                AgentCapability(
                    name="generate_report",
                    description="Generate security report",
                    input_schema={"period": "string"},
                    output_schema={"report": "object"},
                ),
            ],
        )
        super().__init__(config)
        self.threat_log: List[Dict[str, Any]] = []

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task_data.get("type")

        if task_type == "threat_scan":
            return await self._scan_threats(task_data.get("content", ""))
        elif task_type == "audit_log":
            return await self._audit_logs(task_data.get("log_entries", []))
        elif task_type == "generate_report":
            return await self._generate_report(task_data.get("period", "day"))

        return {"error": f"Unknown task type: {task_type}"}

    async def _scan_threats(self, content: str) -> Dict[str, Any]:
        """Scan content for threats."""
        threats = []
        risk_level = "low"

        # Basic pattern checks (real implementation would be more sophisticated)
        threat_patterns = [
            ("sql injection", r"('|\")\s*(or|and)\s*('|\"|1|true)", "high"),
            ("xss", r"<script|javascript:|on\w+=", "high"),
            ("path traversal", r"\.\./|\.\.\\", "medium"),
            ("command injection", r";\s*(ls|cat|rm|wget|curl)", "critical"),
        ]

        import re
        for name, pattern, level in threat_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                threats.append({"type": name, "level": level})
                if level in ("high", "critical"):
                    risk_level = level

        self.threat_log.append({
            "timestamp": datetime.now().isoformat(),
            "threats_found": len(threats),
            "risk_level": risk_level,
        })

        return {
            "threats": threats,
            "risk_level": risk_level,
            "scanned_at": datetime.now().isoformat(),
        }

    async def _audit_logs(self, log_entries: List[Dict]) -> Dict[str, Any]:
        """Audit log entries for compliance."""
        findings = []
        compliance = True

        for entry in log_entries:
            # Check for suspicious patterns
            if entry.get("failed_attempts", 0) > 5:
                findings.append({
                    "type": "brute_force_attempt",
                    "entry": entry,
                    "severity": "high",
                })
                compliance = False

            if entry.get("privilege_change"):
                findings.append({
                    "type": "privilege_escalation",
                    "entry": entry,
                    "severity": "medium",
                })

        return {
            "findings": findings,
            "compliance": compliance,
            "entries_reviewed": len(log_entries),
        }

    async def _generate_report(self, period: str) -> Dict[str, Any]:
        """Generate security report."""
        return {
            "period": period,
            "total_scans": len(self.threat_log),
            "threats_detected": sum(t["threats_found"] for t in self.threat_log),
            "high_risk_events": sum(1 for t in self.threat_log if t["risk_level"] in ("high", "critical")),
            "generated_at": datetime.now().isoformat(),
        }


class ResearchAgent(Agent):
    """
    Agent specialized for knowledge lookup and research tasks.

    Has access to the science pack knowledge base for offline research.
    """

    def __init__(self, name: str = "Researcher", knowledge_bases: List[str] = None):
        config = AgentConfig(
            role=AgentRole.RESEARCH,
            name=name,
            description="Performs research using local knowledge bases",
            knowledge_bases=knowledge_bases or [],
            capabilities=[
                AgentCapability(
                    name="search_knowledge",
                    description="Search knowledge bases for information",
                    input_schema={"query": "string", "domains": "list"},
                    output_schema={"results": "list", "sources": "list"},
                ),
                AgentCapability(
                    name="summarize",
                    description="Summarize documents or findings",
                    input_schema={"content": "string", "max_length": "int"},
                    output_schema={"summary": "string"},
                ),
                AgentCapability(
                    name="compare",
                    description="Compare multiple sources or methods",
                    input_schema={"items": "list"},
                    output_schema={"comparison": "object"},
                ),
            ],
        )
        super().__init__(config)

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task_data.get("type")

        if task_type == "search_knowledge":
            return await self._search(
                task_data.get("query", ""),
                task_data.get("domains", [])
            )
        elif task_type == "summarize":
            return await self._summarize(
                task_data.get("content", ""),
                task_data.get("max_length", 500)
            )

        return {"error": f"Unknown task type: {task_type}"}

    async def _search(self, query: str, domains: List[str]) -> Dict[str, Any]:
        """Search knowledge bases."""
        results = []
        sources = []

        # Search through loaded knowledge bases
        for pack_name, knowledge in self.knowledge_cache.items():
            if domains and pack_name not in domains:
                continue

            # Simple keyword search (real implementation would use embeddings)
            if isinstance(knowledge, dict):
                for key, value in knowledge.items():
                    if query.lower() in str(key).lower() or query.lower() in str(value).lower():
                        results.append({
                            "source": pack_name,
                            "key": key,
                            "content": str(value)[:500],
                        })
                        sources.append(pack_name)

        return {
            "results": results[:10],  # Limit results
            "sources": list(set(sources)),
            "query": query,
            "searched_at": datetime.now().isoformat(),
        }

    async def _summarize(self, content: str, max_length: int) -> Dict[str, Any]:
        """Summarize content."""
        # Simple extractive summary (real implementation would use ML)
        sentences = content.split('. ')
        summary = '. '.join(sentences[:max(1, len(sentences) // 3)])

        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return {
            "summary": summary,
            "original_length": len(content),
            "summary_length": len(summary),
        }


class BusinessAgent(Agent):
    """
    Agent specialized for business operations, portfolio management, and reporting.
    """

    def __init__(self, name: str = "BusinessManager"):
        config = AgentConfig(
            role=AgentRole.BUSINESS,
            name=name,
            description="Manages business portfolio, generates reports, tracks metrics",
            capabilities=[
                AgentCapability(
                    name="portfolio_analysis",
                    description="Analyze business portfolio",
                    input_schema={"portfolio_data": "object"},
                    output_schema={"analysis": "object", "recommendations": "list"},
                ),
                AgentCapability(
                    name="generate_report",
                    description="Generate business report",
                    input_schema={"report_type": "string", "data": "object"},
                    output_schema={"report": "object"},
                ),
                AgentCapability(
                    name="forecast",
                    description="Generate business forecasts",
                    input_schema={"metrics": "list", "period": "string"},
                    output_schema={"forecast": "object"},
                ),
            ],
        )
        super().__init__(config)
        self.portfolio_data: Dict[str, Any] = {}

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task_data.get("type")

        if task_type == "portfolio_analysis":
            return await self._analyze_portfolio(task_data.get("portfolio_data", {}))
        elif task_type == "generate_report":
            return await self._generate_report(
                task_data.get("report_type", "summary"),
                task_data.get("data", {})
            )

        return {"error": f"Unknown task type: {task_type}"}

    async def _analyze_portfolio(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze business portfolio."""
        self.portfolio_data = portfolio

        # Basic analysis
        total_value = sum(
            item.get("value", 0)
            for item in portfolio.get("assets", [])
        )

        return {
            "analysis": {
                "total_value": total_value,
                "asset_count": len(portfolio.get("assets", [])),
                "analyzed_at": datetime.now().isoformat(),
            },
            "recommendations": [
                "Review high-risk assets quarterly",
                "Diversify portfolio across sectors",
            ],
        }

    async def _generate_report(self, report_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate business report."""
        return {
            "report": {
                "type": report_type,
                "generated_at": datetime.now().isoformat(),
                "data": data,
                "summary": f"Business {report_type} report generated",
            }
        }


class EngineerAgent(Agent):
    """
    Agent specialized for code generation, testing, and debugging.
    """

    def __init__(self, name: str = "Engineer"):
        config = AgentConfig(
            role=AgentRole.ENGINEER,
            name=name,
            description="Generates code, runs tests, debugs issues",
            capabilities=[
                AgentCapability(
                    name="generate_code",
                    description="Generate code for a given specification",
                    input_schema={"spec": "string", "language": "string"},
                    output_schema={"code": "string", "explanation": "string"},
                ),
                AgentCapability(
                    name="run_tests",
                    description="Run tests on code",
                    input_schema={"code": "string", "test_cases": "list"},
                    output_schema={"results": "list", "passed": "boolean"},
                ),
                AgentCapability(
                    name="debug",
                    description="Debug code issues",
                    input_schema={"code": "string", "error": "string"},
                    output_schema={"fix": "string", "explanation": "string"},
                ),
            ],
        )
        super().__init__(config)

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task_data.get("type")

        if task_type == "generate_code":
            return await self._generate_code(
                task_data.get("spec", ""),
                task_data.get("language", "python")
            )
        elif task_type == "run_tests":
            return await self._run_tests(
                task_data.get("code", ""),
                task_data.get("test_cases", [])
            )

        return {"error": f"Unknown task type: {task_type}"}

    async def _generate_code(self, spec: str, language: str) -> Dict[str, Any]:
        """Generate code from specification."""
        # Placeholder - real implementation would use local LLM
        return {
            "code": f"# Generated {language} code for: {spec}\n# TODO: Implement",
            "explanation": f"Code skeleton generated for '{spec}' in {language}",
            "language": language,
        }

    async def _run_tests(self, code: str, test_cases: List[Dict]) -> Dict[str, Any]:
        """Run tests on code."""
        results = []
        all_passed = True

        for test in test_cases:
            # Placeholder test execution
            result = {
                "test_name": test.get("name", "unnamed"),
                "passed": True,  # Would actually run the test
                "output": "Test executed",
            }
            results.append(result)

        return {
            "results": results,
            "passed": all_passed,
            "tests_run": len(test_cases),
        }


class CoordinatorAgent(Agent):
    """
    Master agent that coordinates other agents, routes tasks, and manages workflows.
    """

    def __init__(self, name: str = "Coordinator"):
        config = AgentConfig(
            role=AgentRole.COORDINATOR,
            name=name,
            description="Coordinates agents, routes tasks, manages workflows",
            capabilities=[
                AgentCapability(
                    name="route_task",
                    description="Route a task to the appropriate agent",
                    input_schema={"task": "object"},
                    output_schema={"assigned_to": "string", "task_id": "string"},
                ),
                AgentCapability(
                    name="check_status",
                    description="Check status of all agents",
                    input_schema={},
                    output_schema={"agents": "list"},
                ),
                AgentCapability(
                    name="balance_load",
                    description="Balance load across agents",
                    input_schema={"tasks": "list"},
                    output_schema={"assignments": "list"},
                ),
            ],
        )
        super().__init__(config)
        self.managed_agents: Dict[str, Agent] = {}
        self.task_assignments: Dict[str, str] = {}  # task_id -> agent_id

    def register_agent(self, agent: Agent):
        """Register an agent under this coordinator."""
        self.managed_agents[agent.id] = agent

    def unregister_agent(self, agent_id: str):
        """Unregister an agent."""
        if agent_id in self.managed_agents:
            del self.managed_agents[agent_id]

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task_data.get("type")

        if task_type == "route_task":
            return await self._route_task(task_data.get("task", {}))
        elif task_type == "check_status":
            return await self._check_all_status()
        elif task_type == "balance_load":
            return await self._balance_load(task_data.get("tasks", []))

        return {"error": f"Unknown task type: {task_type}"}

    async def _route_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route task to appropriate agent based on requirements."""
        task_id = str(uuid.uuid4())
        required_role = task.get("required_role")

        # Find best agent for task
        best_agent = None
        for agent in self.managed_agents.values():
            if agent.status != AgentStatus.IDLE:
                continue
            if required_role and agent.role.value != required_role:
                continue
            best_agent = agent
            break

        if not best_agent:
            return {"error": "No available agent for task"}

        self.task_assignments[task_id] = best_agent.id
        best_agent.status = AgentStatus.BUSY

        return {
            "assigned_to": best_agent.id,
            "agent_name": best_agent.name,
            "task_id": task_id,
        }

    async def _check_all_status(self) -> Dict[str, Any]:
        """Check status of all managed agents."""
        return {
            "agents": [
                agent.get_status()
                for agent in self.managed_agents.values()
            ],
            "total": len(self.managed_agents),
            "active": sum(
                1 for a in self.managed_agents.values()
                if a.status in (AgentStatus.IDLE, AgentStatus.BUSY)
            ),
        }

    async def _balance_load(self, tasks: List[Dict]) -> Dict[str, Any]:
        """Balance tasks across available agents."""
        assignments = []
        available = [
            a for a in self.managed_agents.values()
            if a.status == AgentStatus.IDLE
        ]

        for i, task in enumerate(tasks):
            if available:
                agent = available[i % len(available)]
                task_id = str(uuid.uuid4())
                assignments.append({
                    "task_id": task_id,
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                })
                self.task_assignments[task_id] = agent.id

        return {
            "assignments": assignments,
            "tasks_assigned": len(assignments),
            "tasks_pending": len(tasks) - len(assignments),
        }


# Factory function for creating agents
def create_agent(role: AgentRole, name: str, **kwargs) -> Agent:
    """Factory function to create agents by role."""
    agent_classes = {
        AgentRole.SECURITY: SecurityAgent,
        AgentRole.RESEARCH: ResearchAgent,
        AgentRole.BUSINESS: BusinessAgent,
        AgentRole.ENGINEER: EngineerAgent,
        AgentRole.COORDINATOR: CoordinatorAgent,
    }

    agent_class = agent_classes.get(role)
    if agent_class:
        return agent_class(name=name, **kwargs)

    raise ValueError(f"Unknown agent role: {role}")
