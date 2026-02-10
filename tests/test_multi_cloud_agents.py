"""
Test Suite for Multi-Cloud AI Agents
====================================

Comprehensive tests for:
- Agent creation and lifecycle
- Security testing agent
- Performance monitoring agent
- Hallucination detection agent
- Multi-cloud orchestrator
- Cross-cloud communication
- Monitoring dashboard

Run with: pytest tests/test_multi_cloud_agents.py -v
"""

import asyncio
import pytest

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio(loop_scope="function")
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Import modules to test
import sys
sys.path.insert(0, '.')

from src.cloud.multi_cloud_agents import (
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

from src.cloud.cross_cloud_comms import (
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

from src.cloud.monitoring_dashboard import (
    AlertSeverity,
    AlertStatus,
    Alert,
    MetricsCollector,
    HealthChecker,
    AlertManager,
    MonitoringDashboard
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def aws_config():
    """AWS cloud configuration."""
    return CloudConfig(
        provider=CloudProvider.AWS,
        region="us-west-2",
        memory_mb=512,
        timeout_seconds=300
    )


@pytest.fixture
def gcp_config():
    """GCP cloud configuration."""
    return CloudConfig(
        provider=CloudProvider.GCP,
        region="us-central1",
        memory_mb=512,
        timeout_seconds=300
    )


@pytest.fixture
def security_agent(aws_config):
    """Security tester agent."""
    return SecurityTesterAgent(cloud_config=aws_config)


@pytest.fixture
def performance_agent(aws_config):
    """Performance monitor agent."""
    return PerformanceMonitorAgent(cloud_config=aws_config)


@pytest.fixture
def hallucination_agent(gcp_config):
    """Hallucination detector agent."""
    return HallucinationDetectorAgent(cloud_config=gcp_config)


@pytest.fixture
def orchestrator_agent(aws_config):
    """Multi-cloud orchestrator agent."""
    return MultiCloudOrchestratorAgent(cloud_config=aws_config)


@pytest.fixture
def service_registry():
    """Service registry for testing."""
    return ServiceRegistry()


@pytest.fixture
def circuit_breaker():
    """Circuit breaker for testing."""
    return CircuitBreaker(failure_threshold=3, recovery_timeout=1)


@pytest.fixture
def metrics_collector():
    """Metrics collector for testing."""
    return MetricsCollector(retention_hours=1)


@pytest.fixture
def alert_manager():
    """Alert manager for testing."""
    return AlertManager()


# =============================================================================
# AGENT FACTORY TESTS
# =============================================================================

class TestAgentFactory:
    """Tests for AgentFactory."""

    def test_create_security_tester(self, aws_config):
        """Test creating security tester agent."""
        agent = AgentFactory.create("security_tester", aws_config)
        assert isinstance(agent, SecurityTesterAgent)
        assert agent.name == "SecurityTester"
        assert agent.cloud_config.provider == CloudProvider.AWS

    def test_create_performance_monitor(self, gcp_config):
        """Test creating performance monitor agent."""
        agent = AgentFactory.create("performance_monitor", gcp_config)
        assert isinstance(agent, PerformanceMonitorAgent)
        assert agent.name == "PerformanceMonitor"
        assert agent.cloud_config.provider == CloudProvider.GCP

    def test_create_hallucination_detector(self, aws_config):
        """Test creating hallucination detector agent."""
        agent = AgentFactory.create("hallucination_detector", aws_config)
        assert isinstance(agent, HallucinationDetectorAgent)
        assert agent.name == "HallucinationDetector"

    def test_create_orchestrator(self, aws_config):
        """Test creating multi-cloud orchestrator."""
        agent = AgentFactory.create("multi_cloud_orchestrator", aws_config)
        assert isinstance(agent, MultiCloudOrchestratorAgent)
        assert agent.name == "MultiCloudOrchestrator"

    def test_create_unknown_type(self, aws_config):
        """Test creating unknown agent type raises error."""
        with pytest.raises(ValueError):
            AgentFactory.create("unknown_type", aws_config)

    def test_list_types(self):
        """Test listing available agent types."""
        types = AgentFactory.list_types()
        assert "security_tester" in types
        assert "performance_monitor" in types
        assert "hallucination_detector" in types
        assert "multi_cloud_orchestrator" in types


# =============================================================================
# SECURITY TESTER AGENT TESTS
# =============================================================================

class TestSecurityTesterAgent:
    """Tests for SecurityTesterAgent."""

    @pytest.mark.asyncio
    async def test_health_check(self, security_agent):
        """Test health check."""
        result = await security_agent.process({"type": "health_check"}, {})
        assert result["status"] == "healthy"
        assert result["agent"] == "SecurityTester"

    @pytest.mark.asyncio
    async def test_vulnerability_scan(self, security_agent):
        """Test vulnerability scanning."""
        result = await security_agent.process({
            "type": "vulnerability_scan",
            "target": "https://example.com",
            "depth": "basic"
        }, {})

        assert "scan_id" in result
        assert "vulnerabilities" in result
        assert "total_found" in result
        assert result["target"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_api_security_test(self, security_agent):
        """Test API security testing."""
        result = await security_agent.process({
            "type": "api_security_test",
            "endpoint": "/api/v1/users",
            "method": "POST"
        }, {})

        assert result["endpoint"] == "/api/v1/users"
        assert result["method"] == "POST"
        assert "findings" in result
        assert "secure" in result

    @pytest.mark.asyncio
    async def test_auth_test(self, security_agent):
        """Test authentication testing."""
        result = await security_agent.process({
            "type": "auth_test",
            "target": "https://example.com/login"
        }, {})

        assert "tests" in result
        assert "all_passed" in result

    @pytest.mark.asyncio
    async def test_rate_limit_test(self, security_agent):
        """Test rate limit testing."""
        result = await security_agent.process({
            "type": "rate_limit_test",
            "endpoint": "/api/v1/data",
            "rps": 100
        }, {})

        assert result["endpoint"] == "/api/v1/data"
        assert "rate_limit_detected" in result

    @pytest.mark.asyncio
    async def test_input_validation_test(self, security_agent):
        """Test input validation testing."""
        result = await security_agent.process({
            "type": "input_validation_test",
            "endpoint": "/api/v1/submit"
        }, {})

        assert "payloads_tested" in result
        assert "all_blocked" in result
        assert "results" in result

    def test_metrics_collection(self, security_agent):
        """Test custom metrics collection."""
        metrics = security_agent._collect_custom_metrics()
        assert "vulnerabilities_found" in metrics
        assert "scans_completed" in metrics


# =============================================================================
# PERFORMANCE MONITOR AGENT TESTS
# =============================================================================

class TestPerformanceMonitorAgent:
    """Tests for PerformanceMonitorAgent."""

    @pytest.mark.asyncio
    async def test_health_check(self, performance_agent):
        """Test health check."""
        result = await performance_agent.process({"type": "health_check"}, {})
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_collect_metrics(self, performance_agent):
        """Test metrics collection."""
        result = await performance_agent.process({
            "type": "collect_metrics",
            "target": "api-server",
            "metrics": ["latency", "throughput", "errors"]
        }, {})

        assert result["target"] == "api-server"
        assert "metrics" in result
        assert "latency" in result["metrics"]
        assert "throughput" in result["metrics"]

    @pytest.mark.asyncio
    async def test_check_latency(self, performance_agent):
        """Test latency checking."""
        result = await performance_agent.process({
            "type": "check_latency",
            "endpoint": "/api/health",
            "samples": 5
        }, {})

        assert result["samples"] == 5
        assert "avg_ms" in result
        assert "p95_ms" in result

    @pytest.mark.asyncio
    async def test_check_throughput(self, performance_agent):
        """Test throughput checking."""
        result = await performance_agent.process({
            "type": "check_throughput",
            "endpoint": "/api/data",
            "duration": 5
        }, {})

        assert "requests_per_second" in result
        assert "bytes_transferred" in result

    @pytest.mark.asyncio
    async def test_detect_anomalies(self, performance_agent):
        """Test anomaly detection."""
        # First collect some metrics
        for _ in range(10):
            await performance_agent.process({
                "type": "collect_metrics",
                "target": "test",
                "metrics": ["latency"]
            }, {})

        result = await performance_agent.process({
            "type": "detect_anomalies"
        }, {})

        assert "anomalies" in result
        assert "anomaly_count" in result

    @pytest.mark.asyncio
    async def test_generate_report(self, performance_agent):
        """Test report generation."""
        result = await performance_agent.process({
            "type": "generate_report",
            "period": "1h"
        }, {})

        assert result["period"] == "1h"
        assert "summary" in result
        assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_set_threshold(self, performance_agent):
        """Test threshold setting."""
        result = await performance_agent.process({
            "type": "set_threshold",
            "metric": "latency_ms",
            "value": 500
        }, {})

        assert result["metric"] == "latency_ms"
        assert result["new_value"] == 500


# =============================================================================
# HALLUCINATION DETECTOR AGENT TESTS
# =============================================================================

class TestHallucinationDetectorAgent:
    """Tests for HallucinationDetectorAgent."""

    @pytest.mark.asyncio
    async def test_health_check(self, hallucination_agent):
        """Test health check."""
        result = await hallucination_agent.process({"type": "health_check"}, {})
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_verify_output(self, hallucination_agent):
        """Test output verification."""
        result = await hallucination_agent.process({
            "type": "verify_output",
            "output": "The sky is blue. Water boils at 100 degrees Celsius.",
            "source_agent": "agent_1",
            "confidence": 0.9
        }, {})

        assert "verification_id" in result
        assert "claims_analyzed" in result
        assert "status" in result

    @pytest.mark.asyncio
    async def test_register_facts(self, hallucination_agent):
        """Test fact registration."""
        result = await hallucination_agent.process({
            "type": "register_facts",
            "facts": {
                "water_boiling_point": "100°C",
                "earth_circumference": "40075 km"
            }
        }, {})

        assert result["facts_added"] == 2
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_verify_with_known_facts(self, hallucination_agent):
        """Test verification against known facts."""
        # Register a fact
        await hallucination_agent.process({
            "type": "register_facts",
            "facts": {"python_version": "3.11"}
        }, {})

        # Verify claim that matches
        result = await hallucination_agent.process({
            "type": "verify_output",
            "output": "Python version 3.11 is the latest stable release.",
            "source_agent": "agent_1"
        }, {})

        assert result["claims_analyzed"] >= 1

    @pytest.mark.asyncio
    async def test_cross_validate(self, hallucination_agent):
        """Test cross-validation."""
        result = await hallucination_agent.process({
            "type": "cross_validate",
            "output": "This is a test statement.",
            "validators": ["validator_1", "validator_2", "validator_3"]
        }, {})

        assert result["validators"] == 3
        assert "agreement_rate" in result
        assert "consensus" in result

    @pytest.mark.asyncio
    async def test_get_stats(self, hallucination_agent):
        """Test statistics retrieval."""
        result = await hallucination_agent.process({"type": "get_stats"}, {})

        assert "total_verifications" in result
        assert "total_hallucinations_detected" in result
        assert "known_facts_count" in result


# =============================================================================
# MULTI-CLOUD ORCHESTRATOR AGENT TESTS
# =============================================================================

class TestMultiCloudOrchestratorAgent:
    """Tests for MultiCloudOrchestratorAgent."""

    @pytest.mark.asyncio
    async def test_health_check(self, orchestrator_agent):
        """Test health check."""
        result = await orchestrator_agent.process({"type": "health_check"}, {})
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_register_agent(self, orchestrator_agent):
        """Test agent registration."""
        result = await orchestrator_agent.process({
            "type": "register_agent",
            "agent_id": "agent_001",
            "agent_type": "security_tester",
            "cloud": "aws",
            "endpoint": "https://lambda.aws.com/agent_001"
        }, {})

        assert result["agent_id"] == "agent_001"
        assert result["status"] == "registered"
        assert result["cloud"] == "aws"

    @pytest.mark.asyncio
    async def test_route_request(self, orchestrator_agent):
        """Test request routing."""
        # First register an agent
        await orchestrator_agent.process({
            "type": "register_agent",
            "agent_id": "agent_001",
            "agent_type": "security_tester",
            "cloud": "aws",
            "endpoint": "https://example.com"
        }, {})

        # Then route a request
        result = await orchestrator_agent.process({
            "type": "route_request",
            "target_agent": "agent_001",
            "payload": {"action": "scan"}
        }, {})

        assert result["routed_to"] == "agent_001"
        assert "endpoint" in result

    @pytest.mark.asyncio
    async def test_check_cloud_health(self, orchestrator_agent):
        """Test cloud health checking."""
        # Register agents on both clouds
        await orchestrator_agent.process({
            "type": "register_agent",
            "agent_id": "aws_agent",
            "agent_type": "monitor",
            "cloud": "aws",
            "endpoint": "https://aws.example.com"
        }, {})

        await orchestrator_agent.process({
            "type": "register_agent",
            "agent_id": "gcp_agent",
            "agent_type": "monitor",
            "cloud": "gcp",
            "endpoint": "https://gcp.example.com"
        }, {})

        result = await orchestrator_agent.process({
            "type": "check_cloud_health"
        }, {})

        assert "clouds" in result
        assert "aws" in result["clouds"]
        assert "gcp" in result["clouds"]

    @pytest.mark.asyncio
    async def test_execute_failover(self, orchestrator_agent):
        """Test failover execution."""
        # Register an AWS agent
        await orchestrator_agent.process({
            "type": "register_agent",
            "agent_id": "aws_agent",
            "agent_type": "monitor",
            "cloud": "aws",
            "endpoint": "https://aws.example.com"
        }, {})

        result = await orchestrator_agent.process({
            "type": "failover",
            "from_cloud": "aws",
            "to_cloud": "gcp"
        }, {})

        assert result["from_cloud"] == "aws"
        assert result["to_cloud"] == "gcp"
        assert "agents_failed_over" in result

    @pytest.mark.asyncio
    async def test_get_topology(self, orchestrator_agent):
        """Test topology retrieval."""
        result = await orchestrator_agent.process({
            "type": "get_topology"
        }, {})

        assert "total_agents" in result
        assert "by_cloud" in result
        assert "by_type" in result

    @pytest.mark.asyncio
    async def test_balance_load(self, orchestrator_agent):
        """Test load balancing."""
        result = await orchestrator_agent.process({
            "type": "balance_load",
            "strategy": "round_robin"
        }, {})

        assert result["strategy"] == "round_robin"
        assert "aws_agents" in result
        assert "gcp_agents" in result
        assert "balanced" in result


# =============================================================================
# CROSS-CLOUD COMMUNICATION TESTS
# =============================================================================

class TestServiceRegistry:
    """Tests for ServiceRegistry."""

    def test_register_endpoint(self, service_registry):
        """Test endpoint registration."""
        endpoint = CloudEndpoint(
            endpoint_id="ep_001",
            cloud="aws",
            region="us-west-2",
            url="https://lambda.aws.com/ep_001",
            agent_type="security_tester"
        )

        result = service_registry.register(endpoint)
        assert result == "ep_001"
        assert len(service_registry.endpoints) == 1

    def test_discover_by_type(self, service_registry):
        """Test discovery by agent type."""
        # Register multiple endpoints
        for i in range(3):
            endpoint = CloudEndpoint(
                endpoint_id=f"ep_{i}",
                cloud="aws" if i % 2 == 0 else "gcp",
                region="us-west-2",
                url=f"https://example.com/ep_{i}",
                agent_type="security_tester" if i < 2 else "monitor"
            )
            service_registry.register(endpoint)

        results = service_registry.discover(agent_type="security_tester")
        assert len(results) == 2

    def test_discover_by_cloud(self, service_registry):
        """Test discovery by cloud."""
        for i, cloud in enumerate(["aws", "aws", "gcp"]):
            endpoint = CloudEndpoint(
                endpoint_id=f"ep_{i}",
                cloud=cloud,
                region="us-west-2",
                url=f"https://example.com/ep_{i}",
                agent_type="monitor"
            )
            service_registry.register(endpoint)

        results = service_registry.discover(cloud="aws")
        assert len(results) == 2

    def test_update_health(self, service_registry):
        """Test health status update."""
        endpoint = CloudEndpoint(
            endpoint_id="ep_001",
            cloud="aws",
            region="us-west-2",
            url="https://example.com",
            agent_type="monitor"
        )
        service_registry.register(endpoint)

        service_registry.update_health("ep_001", False, 100.5)

        updated = service_registry.get("ep_001")
        assert updated.healthy == False
        assert updated.latency_ms == 100.5


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_initial_state_closed(self, circuit_breaker):
        """Test initial state is closed."""
        state = circuit_breaker.get_state("test_circuit")
        assert state == CircuitState.CLOSED

    def test_can_execute_when_closed(self, circuit_breaker):
        """Test execution allowed when closed."""
        assert circuit_breaker.can_execute("test_circuit") == True

    def test_opens_after_failures(self, circuit_breaker):
        """Test circuit opens after threshold failures."""
        for _ in range(3):
            circuit_breaker.record_failure("test_circuit")

        state = circuit_breaker.get_state("test_circuit")
        assert state == CircuitState.OPEN

    def test_cannot_execute_when_open(self, circuit_breaker):
        """Test execution blocked when open."""
        for _ in range(3):
            circuit_breaker.record_failure("test_circuit")

        assert circuit_breaker.can_execute("test_circuit") == False

    def test_success_closes_half_open(self, circuit_breaker):
        """Test success closes half-open circuit."""
        # Open the circuit
        for _ in range(3):
            circuit_breaker.record_failure("test_circuit")

        # Wait for recovery timeout (set to 1 second in fixture)
        import time
        time.sleep(1.1)

        # Should be half-open now
        state = circuit_breaker.get_state("test_circuit")
        assert state == CircuitState.HALF_OPEN

        # Success should close it
        circuit_breaker.record_success("test_circuit")
        state = circuit_breaker.get_state("test_circuit")
        assert state == CircuitState.CLOSED


class TestMessageEncryption:
    """Tests for MessageEncryption."""

    def test_encrypt_decrypt(self):
        """Test encryption and decryption."""
        encryption = MessageEncryption()
        data = {"message": "hello", "count": 42}

        encrypted = encryption.encrypt(data)
        decrypted = encryption.decrypt(encrypted)

        assert decrypted == data

    def test_sign_verify(self):
        """Test signing and verification."""
        encryption = MessageEncryption()
        data = {"message": "hello"}

        signature = encryption.sign(data)
        assert encryption.verify(data, signature) == True

    def test_verify_tampered_fails(self):
        """Test verification fails for tampered data."""
        encryption = MessageEncryption()
        data = {"message": "hello"}

        signature = encryption.sign(data)
        tampered = {"message": "goodbye"}

        assert encryption.verify(tampered, signature) == False


# =============================================================================
# MONITORING DASHBOARD TESTS
# =============================================================================

class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_record_metric(self, metrics_collector):
        """Test recording a metric."""
        metrics_collector.record("cpu_usage", 45.5)
        metrics_collector.record("cpu_usage", 50.0)

        points = metrics_collector.get_metric("cpu_usage")
        assert len(points) == 2
        assert points[0].value == 45.5
        assert points[1].value == 50.0

    def test_get_aggregation(self, metrics_collector):
        """Test getting aggregated statistics."""
        for value in [10, 20, 30, 40, 50]:
            metrics_collector.record("test_metric", value)

        agg = metrics_collector.get_aggregation("test_metric")
        assert agg["count"] == 5
        assert agg["sum"] == 150
        assert agg["avg"] == 30
        assert agg["min"] == 10
        assert agg["max"] == 50

    def test_filter_by_time(self, metrics_collector):
        """Test filtering metrics by time."""
        metrics_collector.record("test", 1.0)

        start_time = datetime.now()
        metrics_collector.record("test", 2.0)
        metrics_collector.record("test", 3.0)

        filtered = metrics_collector.get_metric("test", start_time=start_time)
        assert len(filtered) == 2

    def test_filter_by_labels(self, metrics_collector):
        """Test filtering metrics by labels."""
        metrics_collector.record("requests", 100, {"region": "us-west"})
        metrics_collector.record("requests", 200, {"region": "us-east"})
        metrics_collector.record("requests", 150, {"region": "us-west"})

        filtered = metrics_collector.get_metric("requests", labels={"region": "us-west"})
        assert len(filtered) == 2


class TestAlertManager:
    """Tests for AlertManager."""

    def test_create_alert(self, alert_manager):
        """Test creating an alert."""
        alert = alert_manager.create_alert(
            severity=AlertSeverity.WARNING,
            title="High CPU Usage",
            message="CPU usage exceeded 80%",
            source="agent_001"
        )

        assert alert.alert_id is not None
        assert alert.severity == AlertSeverity.WARNING
        assert alert.status == AlertStatus.ACTIVE

    def test_acknowledge_alert(self, alert_manager):
        """Test acknowledging an alert."""
        alert = alert_manager.create_alert(
            severity=AlertSeverity.ERROR,
            title="Test",
            message="Test",
            source="test"
        )

        alert_manager.acknowledge(alert.alert_id)
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_at is not None

    def test_resolve_alert(self, alert_manager):
        """Test resolving an alert."""
        alert = alert_manager.create_alert(
            severity=AlertSeverity.ERROR,
            title="Test",
            message="Test",
            source="test"
        )

        alert_manager.resolve(alert.alert_id)
        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_at is not None

    def test_get_active_alerts(self, alert_manager):
        """Test getting active alerts."""
        # Create multiple alerts
        alert_manager.create_alert(AlertSeverity.INFO, "Info", "Info", "test")
        alert_manager.create_alert(AlertSeverity.WARNING, "Warning", "Warning", "test")
        alert3 = alert_manager.create_alert(AlertSeverity.ERROR, "Error", "Error", "test")

        # Resolve one
        alert_manager.resolve(alert3.alert_id)

        active = alert_manager.get_active()
        assert len(active) == 2

    def test_add_alerting_rule(self, alert_manager):
        """Test adding alerting rule."""
        alert_manager.add_rule(
            name="High CPU",
            metric_name="cpu_percent",
            condition="gt",
            threshold=80,
            severity=AlertSeverity.WARNING
        )

        assert len(alert_manager.rules) == 1
        assert alert_manager.rules[0]["name"] == "High CPU"

    def test_check_rules(self, alert_manager, metrics_collector):
        """Test checking alerting rules."""
        # Add rule
        alert_manager.add_rule(
            name="High Latency",
            metric_name="latency_ms",
            condition="gt",
            threshold=100,
            severity=AlertSeverity.WARNING,
            cooldown_seconds=0
        )

        # Record metric that triggers rule
        metrics_collector.record("latency_ms", 150)

        # Check rules
        triggered = alert_manager.check_rules(metrics_collector)
        assert len(triggered) == 1
        assert triggered[0].title == "Alert: High Latency"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for the complete system."""

    @pytest.mark.asyncio
    async def test_agent_lifecycle(self, aws_config):
        """Test complete agent lifecycle."""
        # Create agent
        agent = AgentFactory.create("security_tester", aws_config)
        assert agent.status == DeploymentStatus.PENDING

        # Health check
        health = await agent.health_check()
        assert health.status in [AgentHealth.HEALTHY, AgentHealth.DEGRADED]

        # Process request
        result = await agent.process({
            "type": "vulnerability_scan",
            "target": "https://example.com"
        }, {})

        assert agent.invocation_count == 1
        assert "vulnerabilities" in result

        # Get metrics
        metrics = agent.get_metrics()
        assert metrics.invocations == 1

    @pytest.mark.asyncio
    async def test_cross_cloud_workflow(self, aws_config, gcp_config):
        """Test cross-cloud workflow."""
        # Create agents on different clouds
        aws_agent = AgentFactory.create("security_tester", aws_config)
        gcp_agent = AgentFactory.create("performance_monitor", gcp_config)

        # Create orchestrator
        orchestrator = AgentFactory.create("multi_cloud_orchestrator", aws_config)

        # Register agents
        await orchestrator.process({
            "type": "register_agent",
            "agent_id": aws_agent.agent_id,
            "agent_type": "security_tester",
            "cloud": "aws",
            "endpoint": "https://aws.example.com"
        }, {})

        await orchestrator.process({
            "type": "register_agent",
            "agent_id": gcp_agent.agent_id,
            "agent_type": "performance_monitor",
            "cloud": "gcp",
            "endpoint": "https://gcp.example.com"
        }, {})

        # Check topology
        topology = await orchestrator.process({"type": "get_topology"}, {})
        assert topology["total_agents"] == 2
        assert len(topology["by_cloud"]["aws"]) == 1
        assert len(topology["by_cloud"]["gcp"]) == 1

    @pytest.mark.asyncio
    async def test_monitoring_integration(self, aws_config):
        """Test monitoring dashboard integration."""
        # Create agent
        agent = AgentFactory.create("performance_monitor", aws_config)

        # Create dashboard
        dashboard = MonitoringDashboard()
        dashboard.register_agent(agent.agent_id, agent)

        # Manually trigger health check
        health = await dashboard.health_checker.check_agent(agent.agent_id, agent)
        assert health["agent_id"] == agent.agent_id

        # Check dashboard data
        data = dashboard.get_dashboard_data()
        assert "summary" in data
        assert "alerts" in data


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
