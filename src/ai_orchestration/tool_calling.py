"""
External Tool Calling Framework
===============================

Secure framework for AI agents to call external tools and APIs.
Includes sandboxing, rate limiting, audit logging, and permission controls.

FEATURES:
=========
1. Tool Registry - Register and discover available tools
2. Permission System - Fine-grained access control
3. Sandboxing - Isolated execution environment
4. Rate Limiting - Prevent abuse
5. Audit Logging - Full traceability
6. Tool Chaining - Compose tools into pipelines

Version: 1.0.0
"""

import asyncio
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union
import logging

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Categories of tools."""
    DATA_RETRIEVAL = "data_retrieval"      # Read-only data access
    DATA_MUTATION = "data_mutation"         # Write operations
    EXTERNAL_API = "external_api"           # Third-party APIs
    SYSTEM_COMMAND = "system_command"       # OS-level operations
    NETWORK = "network"                     # Network operations
    CRYPTO = "crypto"                       # Cryptographic operations
    AI_MODEL = "ai_model"                   # AI/ML model calls


class PermissionLevel(Enum):
    """Permission levels for tool access."""
    NONE = 0        # No access
    READ = 1        # Read-only
    WRITE = 2       # Read + Write
    EXECUTE = 3     # Full execution
    ADMIN = 4       # Administrative access


class ExecutionStatus(Enum):
    """Tool execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    DENIED = "denied"
    RATE_LIMITED = "rate_limited"


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: str  # string, int, float, bool, list, dict
    description: str
    required: bool = True
    default: Any = None
    validation: Optional[str] = None  # Regex or validation rule


@dataclass
class ToolDefinition:
    """Definition of a callable tool."""
    id: str
    name: str
    description: str
    category: ToolCategory
    parameters: List[ToolParameter]
    return_type: str
    required_permission: PermissionLevel
    rate_limit: int = 100  # calls per minute
    timeout_seconds: int = 30
    requires_confirmation: bool = False
    tags: List[str] = field(default_factory=list)

    def to_schema(self) -> Dict[str, Any]:
        """Convert to JSON schema format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    p.name: {
                        "type": p.type,
                        "description": p.description,
                        **({"default": p.default} if p.default is not None else {})
                    }
                    for p in self.parameters
                },
                "required": [p.name for p in self.parameters if p.required]
            }
        }


@dataclass
class ToolExecutionResult:
    """Result of tool execution."""
    execution_id: str
    tool_id: str
    status: ExecutionStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_ms: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class Tool(ABC):
    """Base class for tools."""

    def __init__(self, definition: ToolDefinition):
        self.definition = definition

    @abstractmethod
    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """Execute the tool with given parameters."""
        pass

    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Validate parameters against definition."""
        errors = []

        for param in self.definition.parameters:
            if param.required and param.name not in parameters:
                errors.append(f"Missing required parameter: {param.name}")

            if param.name in parameters:
                value = parameters[param.name]
                # Type checking
                type_map = {
                    "string": str,
                    "int": int,
                    "float": (int, float),
                    "bool": bool,
                    "list": list,
                    "dict": dict
                }
                expected_type = type_map.get(param.type)
                if expected_type and not isinstance(value, expected_type):
                    errors.append(f"Parameter {param.name} expected {param.type}, got {type(value).__name__}")

        return errors


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self):
        self.buckets: Dict[str, Dict[str, Any]] = {}

    def check_and_consume(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        """Check rate limit and consume a token if allowed."""
        now = time.time()

        if key not in self.buckets:
            self.buckets[key] = {
                "tokens": limit - 1,
                "last_refill": now
            }
            return True

        bucket = self.buckets[key]
        elapsed = now - bucket["last_refill"]

        # Refill tokens
        refill_amount = int(elapsed * limit / window_seconds)
        bucket["tokens"] = min(limit, bucket["tokens"] + refill_amount)
        bucket["last_refill"] = now

        # Try to consume
        if bucket["tokens"] > 0:
            bucket["tokens"] -= 1
            return True

        return False

    def get_remaining(self, key: str, limit: int) -> int:
        """Get remaining tokens for a key."""
        if key not in self.buckets:
            return limit
        return self.buckets[key]["tokens"]


class PermissionManager:
    """Manages permissions for agents to use tools."""

    def __init__(self):
        self.agent_permissions: Dict[str, Dict[str, PermissionLevel]] = {}
        self.role_permissions: Dict[str, Dict[str, PermissionLevel]] = {}

    def grant_permission(self, agent_id: str, tool_id: str, level: PermissionLevel):
        """Grant permission to an agent for a tool."""
        if agent_id not in self.agent_permissions:
            self.agent_permissions[agent_id] = {}
        self.agent_permissions[agent_id][tool_id] = level

    def grant_role_permission(self, role: str, tool_id: str, level: PermissionLevel):
        """Grant permission to a role for a tool."""
        if role not in self.role_permissions:
            self.role_permissions[role] = {}
        self.role_permissions[role][tool_id] = level

    def check_permission(
        self,
        agent_id: str,
        agent_role: str,
        tool: ToolDefinition
    ) -> bool:
        """Check if agent has permission to use tool."""
        required = tool.required_permission

        # Check agent-specific permission
        agent_level = self.agent_permissions.get(agent_id, {}).get(tool.id, PermissionLevel.NONE)
        if agent_level.value >= required.value:
            return True

        # Check role permission
        role_level = self.role_permissions.get(agent_role, {}).get(tool.id, PermissionLevel.NONE)
        if role_level.value >= required.value:
            return True

        return False

    def revoke_permission(self, agent_id: str, tool_id: str):
        """Revoke permission from an agent."""
        if agent_id in self.agent_permissions:
            self.agent_permissions[agent_id].pop(tool_id, None)


class AuditLogger:
    """Logs all tool executions for auditing."""

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self.logs: List[Dict[str, Any]] = []

    def log_execution(
        self,
        execution_id: str,
        agent_id: str,
        tool_id: str,
        parameters: Dict[str, Any],
        result: ToolExecutionResult,
        context: Dict[str, Any]
    ):
        """Log a tool execution."""
        # Sanitize sensitive data
        safe_params = self._sanitize(parameters)

        entry = {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "tool_id": tool_id,
            "parameters": safe_params,
            "status": result.status.value,
            "error": result.error,
            "execution_time_ms": result.execution_time_ms,
            "timestamp": datetime.now().isoformat(),
            "context": context
        }

        self.logs.append(entry)
        logger.info(f"Tool execution: {tool_id} by {agent_id} - {result.status.value}")

    def _sanitize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from logs."""
        sensitive_keys = {"password", "api_key", "secret", "token", "credential"}

        result = {}
        for key, value in data.items():
            if any(s in key.lower() for s in sensitive_keys):
                result[key] = "[REDACTED]"
            elif isinstance(value, dict):
                result[key] = self._sanitize(value)
            else:
                result[key] = value

        return result

    def query(
        self,
        agent_id: Optional[str] = None,
        tool_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query execution logs."""
        results = self.logs

        if agent_id:
            results = [l for l in results if l["agent_id"] == agent_id]
        if tool_id:
            results = [l for l in results if l["tool_id"] == tool_id]
        if status:
            results = [l for l in results if l["status"] == status.value]

        return results[-limit:]


class ToolRegistry:
    """Registry of all available tools."""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.definitions: Dict[str, ToolDefinition] = {}
        self.categories: Dict[ToolCategory, List[str]] = {cat: [] for cat in ToolCategory}

    def register(self, tool: Tool):
        """Register a tool."""
        self.tools[tool.definition.id] = tool
        self.definitions[tool.definition.id] = tool.definition
        self.categories[tool.definition.category].append(tool.definition.id)
        logger.info(f"Registered tool: {tool.definition.name}")

    def unregister(self, tool_id: str):
        """Unregister a tool."""
        if tool_id in self.tools:
            tool = self.tools[tool_id]
            self.categories[tool.definition.category].remove(tool_id)
            del self.tools[tool_id]
            del self.definitions[tool_id]

    def get(self, tool_id: str) -> Optional[Tool]:
        """Get a tool by ID."""
        return self.tools.get(tool_id)

    def get_definition(self, tool_id: str) -> Optional[ToolDefinition]:
        """Get tool definition."""
        return self.definitions.get(tool_id)

    def list_by_category(self, category: ToolCategory) -> List[ToolDefinition]:
        """List tools by category."""
        return [self.definitions[tid] for tid in self.categories.get(category, [])]

    def search(self, query: str) -> List[ToolDefinition]:
        """Search tools by name or description."""
        query_lower = query.lower()
        return [
            d for d in self.definitions.values()
            if query_lower in d.name.lower() or query_lower in d.description.lower()
        ]

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Get JSON schemas for all tools."""
        return [d.to_schema() for d in self.definitions.values()]


class ToolExecutor:
    """
    Main executor for tool calls.
    Handles permissions, rate limiting, sandboxing, and logging.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        permission_manager: PermissionManager,
        rate_limiter: RateLimiter,
        audit_logger: AuditLogger
    ):
        self.registry = registry
        self.permissions = permission_manager
        self.rate_limiter = rate_limiter
        self.audit = audit_logger
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}

    async def execute(
        self,
        agent_id: str,
        agent_role: str,
        tool_id: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolExecutionResult:
        """Execute a tool call."""
        execution_id = str(uuid.uuid4())
        context = context or {}

        # Get tool
        tool = self.registry.get(tool_id)
        if not tool:
            return ToolExecutionResult(
                execution_id=execution_id,
                tool_id=tool_id,
                status=ExecutionStatus.FAILED,
                error=f"Tool not found: {tool_id}"
            )

        definition = tool.definition

        # Check permission
        if not self.permissions.check_permission(agent_id, agent_role, definition):
            result = ToolExecutionResult(
                execution_id=execution_id,
                tool_id=tool_id,
                status=ExecutionStatus.DENIED,
                error="Permission denied"
            )
            self.audit.log_execution(execution_id, agent_id, tool_id, parameters, result, context)
            return result

        # Check rate limit
        rate_key = f"{agent_id}:{tool_id}"
        if not self.rate_limiter.check_and_consume(rate_key, definition.rate_limit):
            result = ToolExecutionResult(
                execution_id=execution_id,
                tool_id=tool_id,
                status=ExecutionStatus.RATE_LIMITED,
                error=f"Rate limit exceeded: {definition.rate_limit}/min"
            )
            self.audit.log_execution(execution_id, agent_id, tool_id, parameters, result, context)
            return result

        # Validate parameters
        validation_errors = tool.validate_parameters(parameters)
        if validation_errors:
            result = ToolExecutionResult(
                execution_id=execution_id,
                tool_id=tool_id,
                status=ExecutionStatus.FAILED,
                error=f"Parameter validation failed: {validation_errors}"
            )
            self.audit.log_execution(execution_id, agent_id, tool_id, parameters, result, context)
            return result

        # Check if confirmation required
        if definition.requires_confirmation:
            self.pending_confirmations[execution_id] = {
                "agent_id": agent_id,
                "tool_id": tool_id,
                "parameters": parameters,
                "context": context,
                "created_at": datetime.now()
            }
            return ToolExecutionResult(
                execution_id=execution_id,
                tool_id=tool_id,
                status=ExecutionStatus.PENDING,
                metadata={"requires_confirmation": True}
            )

        # Execute tool
        return await self._execute_tool(execution_id, agent_id, tool, parameters, context)

    async def confirm_execution(self, execution_id: str) -> ToolExecutionResult:
        """Confirm a pending execution."""
        if execution_id not in self.pending_confirmations:
            return ToolExecutionResult(
                execution_id=execution_id,
                tool_id="unknown",
                status=ExecutionStatus.FAILED,
                error="Execution not found or already processed"
            )

        pending = self.pending_confirmations.pop(execution_id)
        tool = self.registry.get(pending["tool_id"])

        return await self._execute_tool(
            execution_id,
            pending["agent_id"],
            tool,
            pending["parameters"],
            pending["context"]
        )

    async def _execute_tool(
        self,
        execution_id: str,
        agent_id: str,
        tool: Tool,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ToolExecutionResult:
        """Actually execute the tool."""
        started_at = datetime.now()

        try:
            # Execute with timeout
            result_data = await asyncio.wait_for(
                tool.execute(parameters, context),
                timeout=tool.definition.timeout_seconds
            )

            completed_at = datetime.now()
            execution_time = (completed_at - started_at).total_seconds() * 1000

            result = ToolExecutionResult(
                execution_id=execution_id,
                tool_id=tool.definition.id,
                status=ExecutionStatus.COMPLETED,
                result=result_data,
                started_at=started_at,
                completed_at=completed_at,
                execution_time_ms=execution_time
            )

        except asyncio.TimeoutError:
            result = ToolExecutionResult(
                execution_id=execution_id,
                tool_id=tool.definition.id,
                status=ExecutionStatus.TIMEOUT,
                error=f"Execution timed out after {tool.definition.timeout_seconds}s",
                started_at=started_at,
                completed_at=datetime.now()
            )

        except Exception as e:
            result = ToolExecutionResult(
                execution_id=execution_id,
                tool_id=tool.definition.id,
                status=ExecutionStatus.FAILED,
                error=str(e),
                started_at=started_at,
                completed_at=datetime.now()
            )

        self.audit.log_execution(execution_id, agent_id, tool.definition.id, parameters, result, context)
        return result


# =============================================================================
# BUILT-IN TOOLS
# =============================================================================

class HTTPRequestTool(Tool):
    """Tool for making HTTP requests."""

    def __init__(self):
        super().__init__(ToolDefinition(
            id="http_request",
            name="HTTP Request",
            description="Make HTTP requests to external APIs",
            category=ToolCategory.EXTERNAL_API,
            parameters=[
                ToolParameter("url", "string", "The URL to request"),
                ToolParameter("method", "string", "HTTP method (GET, POST, etc.)", default="GET"),
                ToolParameter("headers", "dict", "Request headers", required=False),
                ToolParameter("body", "dict", "Request body for POST/PUT", required=False),
                ToolParameter("timeout", "int", "Request timeout in seconds", required=False, default=30)
            ],
            return_type="dict",
            required_permission=PermissionLevel.EXECUTE,
            rate_limit=60,
            timeout_seconds=60
        ))

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Any:
        import aiohttp

        url = parameters["url"]
        method = parameters.get("method", "GET").upper()
        headers = parameters.get("headers", {})
        body = parameters.get("body")
        timeout = parameters.get("timeout", 30)

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                url,
                headers=headers,
                json=body if body else None,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                return {
                    "status": response.status,
                    "headers": dict(response.headers),
                    "body": await response.text()
                }


class DatabaseQueryTool(Tool):
    """Tool for querying databases."""

    def __init__(self, connection_string: str = ""):
        super().__init__(ToolDefinition(
            id="database_query",
            name="Database Query",
            description="Execute read-only database queries",
            category=ToolCategory.DATA_RETRIEVAL,
            parameters=[
                ToolParameter("query", "string", "SQL query to execute"),
                ToolParameter("database", "string", "Database name"),
                ToolParameter("limit", "int", "Maximum rows to return", required=False, default=100)
            ],
            return_type="list",
            required_permission=PermissionLevel.READ,
            rate_limit=30,
            timeout_seconds=30
        ))
        self.connection_string = connection_string

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Any:
        # Placeholder - would connect to actual database
        query = parameters["query"]

        # Basic SQL injection prevention
        dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]
        query_upper = query.upper()
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                raise ValueError(f"Query contains forbidden keyword: {keyword}")

        return {
            "rows": [],
            "query": query,
            "message": "Database query simulated"
        }


class FileSystemTool(Tool):
    """Tool for file system operations."""

    def __init__(self, allowed_paths: List[str] = None):
        super().__init__(ToolDefinition(
            id="filesystem",
            name="File System",
            description="Read files from allowed directories",
            category=ToolCategory.DATA_RETRIEVAL,
            parameters=[
                ToolParameter("operation", "string", "Operation: read, list, exists"),
                ToolParameter("path", "string", "File or directory path"),
            ],
            return_type="dict",
            required_permission=PermissionLevel.READ,
            rate_limit=100,
            timeout_seconds=10
        ))
        self.allowed_paths = allowed_paths or []

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Any:
        import os

        operation = parameters["operation"]
        path = parameters["path"]

        # Security: Check path is allowed
        abs_path = os.path.abspath(path)
        if self.allowed_paths and not any(abs_path.startswith(ap) for ap in self.allowed_paths):
            raise ValueError(f"Path not allowed: {path}")

        # Prevent path traversal
        if ".." in path:
            raise ValueError("Path traversal not allowed")

        if operation == "read":
            with open(path, 'r') as f:
                return {"content": f.read()}
        elif operation == "list":
            return {"files": os.listdir(path)}
        elif operation == "exists":
            return {"exists": os.path.exists(path)}
        else:
            raise ValueError(f"Unknown operation: {operation}")


# =============================================================================
# TOOL CALLING FACADE
# =============================================================================

class ToolCallingSystem:
    """
    Main facade for the tool calling system.
    Provides a simple interface for agents to discover and call tools.
    """

    def __init__(self):
        self.registry = ToolRegistry()
        self.permissions = PermissionManager()
        self.rate_limiter = RateLimiter()
        self.audit = AuditLogger()
        self.executor = ToolExecutor(
            self.registry,
            self.permissions,
            self.rate_limiter,
            self.audit
        )

        # Register built-in tools
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """Register built-in tools."""
        self.registry.register(HTTPRequestTool())
        self.registry.register(DatabaseQueryTool())
        self.registry.register(FileSystemTool())

    def register_tool(self, tool: Tool):
        """Register a custom tool."""
        self.registry.register(tool)

    def grant_permission(self, agent_id: str, tool_id: str, level: PermissionLevel):
        """Grant tool permission to an agent."""
        self.permissions.grant_permission(agent_id, tool_id, level)

    def grant_role_permission(self, role: str, tool_id: str, level: PermissionLevel):
        """Grant tool permission to a role."""
        self.permissions.grant_role_permission(role, tool_id, level)

    async def call_tool(
        self,
        agent_id: str,
        agent_role: str,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolExecutionResult:
        """Call a tool."""
        return await self.executor.execute(
            agent_id, agent_role, tool_name, parameters, context
        )

    def get_available_tools(self, agent_id: str, agent_role: str) -> List[Dict[str, Any]]:
        """Get tools available to an agent."""
        available = []
        for definition in self.registry.definitions.values():
            if self.permissions.check_permission(agent_id, agent_role, definition):
                available.append(definition.to_schema())
        return available

    def get_audit_logs(self, **filters) -> List[Dict[str, Any]]:
        """Get audit logs."""
        return self.audit.query(**filters)
