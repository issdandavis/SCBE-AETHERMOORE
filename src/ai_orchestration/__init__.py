"""
SCBE AI Orchestration Framework
================================

A secure, multi-agent orchestration system for AI-to-AI communication,
task delegation, workflow management, and comprehensive logging.

CORE FEATURES:
==============
1. AGENT MANAGEMENT
   - Register/deregister AI agents
   - Agent capability discovery
   - Health monitoring
   - Load balancing

2. SECURE COMMUNICATION
   - Prompt injection prevention
   - Input sanitization
   - Output validation
   - Encrypted agent-to-agent messaging

3. TASK ORCHESTRATION
   - Workflow definition
   - Task delegation
   - Progress tracking
   - Result aggregation

4. LOGGING & AUDIT
   - Full conversation logging
   - File change tracking
   - Decision audit trail
   - Compliance reporting

Version: 1.0.0
"""

__version__ = "1.0.0"
__all__ = [
    # Core classes
    'Orchestrator',
    'Agent',
    'Task',
    'Workflow',

    # Security
    'SecurityGate',
    'PromptSanitizer',
    'OutputValidator',

    # Logging
    'AuditLogger',
    'WorkflowTracker',

    # Registry
    'AgentRegistry',
]

from .orchestrator import Orchestrator, AgentRegistry
from .agents import Agent, AgentCapability
from .tasks import Task, Workflow, TaskStatus
from .security import SecurityGate, PromptSanitizer, OutputValidator
from .logging import AuditLogger, WorkflowTracker
