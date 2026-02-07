"""
SCBE Multi-Cloud AI Agent Framework
====================================

Production-ready framework for deploying and managing AI agents
across AWS and Google Cloud Platform.

Modules:
--------
- multi_cloud_agents: Agent types (Security, Performance, Hallucination, Orchestrator)
- cross_cloud_comms: Cross-cloud communication layer
- monitoring_dashboard: Health monitoring and alerting

Usage:
------
    from src.cloud import (
        AgentFactory,
        CloudConfig,
        CloudProvider,
        CrossCloudCommunicator,
        MonitoringDashboard
    )

    # Create an agent
    config = CloudConfig(provider=CloudProvider.AWS, region="us-west-2")
    agent = AgentFactory.create("security_tester", config)

    # Start monitoring
    dashboard = MonitoringDashboard()
    dashboard.register_agent(agent.agent_id, agent)
    await dashboard.start()

Version: 1.0.0
"""

from .multi_cloud_agents import (
    CloudProvider,
    AgentHealth,
    DeploymentStatus,
    CloudConfig,
    AgentMetrics,
    HealthCheckResult,
    CloudAgent,
    SecurityTesterAgent,
    PerformanceMonitorAgent,
    HallucinationDetectorAgent,
    MultiCloudOrchestratorAgent,
    AgentFactory
)

from .cross_cloud_comms import (
    MessagePriority,
    MessageStatus,
    CircuitState,
    CloudEndpoint,
    CrossCloudMessage,
    ServiceRegistry,
    CircuitBreaker,
    MessageQueue,
    MessageEncryption,
    CrossCloudRouter,
    CrossCloudCommunicator
)

from .monitoring_dashboard import (
    AlertSeverity,
    AlertStatus,
    Alert,
    MetricPoint,
    AgentSnapshot,
    MetricsCollector,
    HealthChecker,
    AlertManager,
    MonitoringDashboard
)

__all__ = [
    # Enums
    "CloudProvider",
    "AgentHealth",
    "DeploymentStatus",
    "MessagePriority",
    "MessageStatus",
    "CircuitState",
    "AlertSeverity",
    "AlertStatus",

    # Data classes
    "CloudConfig",
    "AgentMetrics",
    "HealthCheckResult",
    "CloudEndpoint",
    "CrossCloudMessage",
    "Alert",
    "MetricPoint",
    "AgentSnapshot",

    # Agents
    "CloudAgent",
    "SecurityTesterAgent",
    "PerformanceMonitorAgent",
    "HallucinationDetectorAgent",
    "MultiCloudOrchestratorAgent",
    "AgentFactory",

    # Communication
    "ServiceRegistry",
    "CircuitBreaker",
    "MessageQueue",
    "MessageEncryption",
    "CrossCloudRouter",
    "CrossCloudCommunicator",

    # Monitoring
    "MetricsCollector",
    "HealthChecker",
    "AlertManager",
    "MonitoringDashboard"
]
