"""
Agent Monitoring Dashboard
==========================

Production-ready monitoring dashboard for multi-cloud AI agents.
Provides health checks, metrics aggregation, alerting, and visualization.

FEATURES:
=========
1. Real-time Health Monitoring
2. Metrics Aggregation
3. Alert Management
4. Cross-Cloud Status
5. Performance Analytics

Version: 1.0.0
"""

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import statistics

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class Alert:
    """Monitoring alert."""
    alert_id: str
    severity: AlertSeverity
    title: str
    message: str
    source: str  # agent_id or system
    cloud: Optional[str] = None
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    status: AlertStatus = AlertStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class AgentSnapshot:
    """Point-in-time snapshot of agent state."""
    agent_id: str
    agent_type: str
    cloud: str
    region: str
    status: str
    health: str
    invocations: int
    errors: int
    avg_latency_ms: float
    memory_mb: float
    last_activity: datetime
    custom_metrics: Dict[str, float] = field(default_factory=dict)


class MetricsCollector:
    """
    Collects and aggregates metrics from agents.
    """

    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self.aggregations: Dict[str, Dict[str, float]] = {}

    def record(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """Record a metric value."""
        point = MetricPoint(
            timestamp=datetime.now(),
            value=value,
            labels=labels or {}
        )

        self.metrics[metric_name].append(point)
        self._cleanup_old_metrics(metric_name)
        self._update_aggregations(metric_name)

    def _cleanup_old_metrics(self, metric_name: str):
        """Remove metrics older than retention period."""
        cutoff = datetime.now() - timedelta(hours=self.retention_hours)
        self.metrics[metric_name] = [
            p for p in self.metrics[metric_name]
            if p.timestamp > cutoff
        ]

    def _update_aggregations(self, metric_name: str):
        """Update aggregated statistics."""
        points = self.metrics[metric_name]
        if not points:
            return

        values = [p.value for p in points]

        self.aggregations[metric_name] = {
            "count": len(values),
            "sum": sum(values),
            "avg": statistics.mean(values),
            "min": min(values),
            "max": max(values),
            "stddev": statistics.stdev(values) if len(values) > 1 else 0,
            "last": values[-1],
            "last_updated": datetime.now().isoformat()
        }

    def get_metric(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> List[MetricPoint]:
        """Get metric data points."""
        points = self.metrics.get(metric_name, [])

        if start_time:
            points = [p for p in points if p.timestamp >= start_time]
        if end_time:
            points = [p for p in points if p.timestamp <= end_time]
        if labels:
            points = [
                p for p in points
                if all(p.labels.get(k) == v for k, v in labels.items())
            ]

        return points

    def get_aggregation(self, metric_name: str) -> Dict[str, float]:
        """Get aggregated statistics for a metric."""
        return self.aggregations.get(metric_name, {})

    def get_all_metrics(self) -> List[str]:
        """Get list of all metric names."""
        return list(self.metrics.keys())


class HealthChecker:
    """
    Performs health checks on agents.
    """

    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.health_status: Dict[str, Dict[str, Any]] = {}
        self.check_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._running = False
        self._callbacks: List[Callable] = []

    def register_callback(self, callback: Callable):
        """Register callback for health status changes."""
        self._callbacks.append(callback)

    async def check_agent(self, agent_id: str, agent: Any) -> Dict[str, Any]:
        """Perform health check on an agent."""
        start_time = time.time()

        try:
            result = await agent.health_check()

            health_data = {
                "agent_id": agent_id,
                "healthy": result.status.value in ["healthy", "degraded"],
                "status": result.status.value,
                "latency_ms": result.latency_ms,
                "checks_passed": result.checks_passed,
                "checks_failed": result.checks_failed,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            health_data = {
                "agent_id": agent_id,
                "healthy": False,
                "status": "error",
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000,
                "timestamp": datetime.now().isoformat()
            }

        # Store result
        previous = self.health_status.get(agent_id, {})
        self.health_status[agent_id] = health_data
        self.check_history[agent_id].append(health_data)

        # Keep only last 100 checks
        self.check_history[agent_id] = self.check_history[agent_id][-100:]

        # Notify callbacks if status changed
        if previous.get("healthy") != health_data["healthy"]:
            for callback in self._callbacks:
                try:
                    await callback(agent_id, previous, health_data)
                except Exception as e:
                    logger.error(f"Health callback error: {e}")

        return health_data

    def get_health(self, agent_id: str) -> Dict[str, Any]:
        """Get current health status for an agent."""
        return self.health_status.get(agent_id, {"healthy": False, "status": "unknown"})

    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status for all agents."""
        return self.health_status.copy()

    def get_uptime(self, agent_id: str) -> float:
        """Calculate uptime percentage for an agent."""
        history = self.check_history.get(agent_id, [])
        if not history:
            return 0.0

        healthy_count = sum(1 for h in history if h.get("healthy", False))
        return (healthy_count / len(history)) * 100


class AlertManager:
    """
    Manages monitoring alerts.
    """

    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.rules: List[Dict[str, Any]] = []
        self.notification_handlers: Dict[str, Callable] = {}
        self.alert_history: List[Alert] = []

    def add_rule(
        self,
        name: str,
        metric_name: str,
        condition: str,  # gt, lt, eq
        threshold: float,
        severity: AlertSeverity,
        cooldown_seconds: int = 300
    ):
        """Add an alerting rule."""
        self.rules.append({
            "name": name,
            "metric_name": metric_name,
            "condition": condition,
            "threshold": threshold,
            "severity": severity,
            "cooldown_seconds": cooldown_seconds,
            "last_triggered": None
        })

    def register_handler(self, channel: str, handler: Callable):
        """Register notification handler."""
        self.notification_handlers[channel] = handler

    def check_rules(self, metrics_collector: MetricsCollector) -> List[Alert]:
        """Check all rules against current metrics."""
        triggered = []

        for rule in self.rules:
            agg = metrics_collector.get_aggregation(rule["metric_name"])
            if not agg:
                continue

            value = agg.get("last", 0)
            threshold = rule["threshold"]

            # Check condition
            triggered_condition = False
            if rule["condition"] == "gt" and value > threshold:
                triggered_condition = True
            elif rule["condition"] == "lt" and value < threshold:
                triggered_condition = True
            elif rule["condition"] == "eq" and value == threshold:
                triggered_condition = True

            if triggered_condition:
                # Check cooldown
                if rule["last_triggered"]:
                    elapsed = (datetime.now() - rule["last_triggered"]).total_seconds()
                    if elapsed < rule["cooldown_seconds"]:
                        continue

                alert = self.create_alert(
                    severity=rule["severity"],
                    title=f"Alert: {rule['name']}",
                    message=f"Metric {rule['metric_name']} is {value} ({rule['condition']} {threshold})",
                    source="system",
                    metric_name=rule["metric_name"],
                    metric_value=value,
                    threshold=threshold
                )

                rule["last_triggered"] = datetime.now()
                triggered.append(alert)

        return triggered

    def create_alert(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        source: str,
        cloud: Optional[str] = None,
        **kwargs
    ) -> Alert:
        """Create a new alert."""
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            severity=severity,
            title=title,
            message=message,
            source=source,
            cloud=cloud,
            **kwargs
        )

        self.alerts[alert.alert_id] = alert
        self.alert_history.append(alert)

        # Send notifications
        asyncio.create_task(self._notify(alert))

        return alert

    async def _notify(self, alert: Alert):
        """Send alert notifications."""
        for channel, handler in self.notification_handlers.items():
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Notification error for {channel}: {e}")

    def acknowledge(self, alert_id: str):
        """Acknowledge an alert."""
        if alert_id in self.alerts:
            self.alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
            self.alerts[alert_id].acknowledged_at = datetime.now()

    def resolve(self, alert_id: str):
        """Resolve an alert."""
        if alert_id in self.alerts:
            self.alerts[alert_id].status = AlertStatus.RESOLVED
            self.alerts[alert_id].resolved_at = datetime.now()

    def get_active(self) -> List[Alert]:
        """Get all active alerts."""
        return [a for a in self.alerts.values() if a.status == AlertStatus.ACTIVE]

    def get_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Get alerts by severity."""
        return [a for a in self.alerts.values() if a.severity == severity]


class MonitoringDashboard:
    """
    Main monitoring dashboard.
    Aggregates data from all monitoring components.
    """

    def __init__(self):
        self.metrics = MetricsCollector()
        self.health_checker = HealthChecker()
        self.alert_manager = AlertManager()
        self.agents: Dict[str, Any] = {}
        self.snapshots: List[Dict[str, AgentSnapshot]] = []
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

        # Setup default alerting rules
        self._setup_default_rules()

        # Register health change callback
        self.health_checker.register_callback(self._on_health_change)

    def _setup_default_rules(self):
        """Setup default alerting rules."""
        self.alert_manager.add_rule(
            name="High Error Rate",
            metric_name="error_rate",
            condition="gt",
            threshold=0.05,
            severity=AlertSeverity.ERROR
        )

        self.alert_manager.add_rule(
            name="High Latency",
            metric_name="avg_latency_ms",
            condition="gt",
            threshold=1000,
            severity=AlertSeverity.WARNING
        )

        self.alert_manager.add_rule(
            name="High Memory Usage",
            metric_name="memory_percent",
            condition="gt",
            threshold=90,
            severity=AlertSeverity.WARNING
        )

    async def _on_health_change(
        self,
        agent_id: str,
        previous: Dict[str, Any],
        current: Dict[str, Any]
    ):
        """Handle health status changes."""
        if current.get("healthy") == False and previous.get("healthy") == True:
            # Agent became unhealthy
            self.alert_manager.create_alert(
                severity=AlertSeverity.ERROR,
                title=f"Agent Unhealthy: {agent_id}",
                message=f"Agent {agent_id} health check failed",
                source=agent_id
            )
        elif current.get("healthy") == True and previous.get("healthy") == False:
            # Agent recovered
            self.alert_manager.create_alert(
                severity=AlertSeverity.INFO,
                title=f"Agent Recovered: {agent_id}",
                message=f"Agent {agent_id} is healthy again",
                source=agent_id
            )

    def register_agent(self, agent_id: str, agent: Any):
        """Register an agent for monitoring."""
        self.agents[agent_id] = agent
        logger.info(f"Registered agent for monitoring: {agent_id}")

    def unregister_agent(self, agent_id: str):
        """Unregister an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]

    async def start(self, interval_seconds: int = 30):
        """Start the monitoring dashboard."""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval_seconds))
        logger.info("Monitoring dashboard started")

    async def stop(self):
        """Stop the monitoring dashboard."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Monitoring dashboard stopped")

    async def _monitor_loop(self, interval: int):
        """Main monitoring loop."""
        while self._running:
            try:
                # Collect metrics from all agents
                snapshot = {}

                for agent_id, agent in list(self.agents.items()):
                    try:
                        # Health check
                        health = await self.health_checker.check_agent(agent_id, agent)

                        # Get metrics
                        agent_metrics = agent.get_metrics()

                        # Record metrics
                        self.metrics.record(f"{agent_id}.invocations", agent_metrics.invocations)
                        self.metrics.record(f"{agent_id}.errors", agent_metrics.errors)
                        self.metrics.record(f"{agent_id}.latency", agent_metrics.avg_latency_ms)

                        # Calculate error rate
                        if agent_metrics.invocations > 0:
                            error_rate = agent_metrics.errors / agent_metrics.invocations
                            self.metrics.record("error_rate", error_rate, {"agent_id": agent_id})

                        # Create snapshot
                        snapshot[agent_id] = AgentSnapshot(
                            agent_id=agent_id,
                            agent_type=agent.name,
                            cloud=agent.cloud_config.provider.value,
                            region=agent.cloud_config.region,
                            status=agent.status.value,
                            health=health["status"],
                            invocations=agent_metrics.invocations,
                            errors=agent_metrics.errors,
                            avg_latency_ms=agent_metrics.avg_latency_ms,
                            memory_mb=agent_metrics.memory_used_mb,
                            last_activity=agent.last_invocation or agent.created_at,
                            custom_metrics=agent_metrics.custom_metrics
                        )

                    except Exception as e:
                        logger.error(f"Error monitoring agent {agent_id}: {e}")

                # Store snapshot
                self.snapshots.append(snapshot)
                self.snapshots = self.snapshots[-1000:]  # Keep last 1000

                # Check alerting rules
                self.alert_manager.check_rules(self.metrics)

                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(interval)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data."""
        # Latest snapshot
        latest_snapshot = self.snapshots[-1] if self.snapshots else {}

        # Aggregate by cloud
        by_cloud = {"aws": [], "gcp": [], "local": []}
        for agent_id, snap in latest_snapshot.items():
            by_cloud[snap.cloud].append({
                "agent_id": snap.agent_id,
                "type": snap.agent_type,
                "health": snap.health,
                "invocations": snap.invocations
            })

        # Health summary
        health_summary = {
            "total": len(latest_snapshot),
            "healthy": sum(1 for s in latest_snapshot.values() if s.health == "healthy"),
            "degraded": sum(1 for s in latest_snapshot.values() if s.health == "degraded"),
            "unhealthy": sum(1 for s in latest_snapshot.values() if s.health in ["unhealthy", "error"])
        }

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "agents": health_summary,
                "clouds": {
                    cloud: len(agents) for cloud, agents in by_cloud.items()
                },
                "alerts": {
                    "active": len(self.alert_manager.get_active()),
                    "critical": len(self.alert_manager.get_by_severity(AlertSeverity.CRITICAL)),
                    "warning": len(self.alert_manager.get_by_severity(AlertSeverity.WARNING))
                }
            },
            "agents": {
                agent_id: {
                    "type": snap.agent_type,
                    "cloud": snap.cloud,
                    "region": snap.region,
                    "status": snap.status,
                    "health": snap.health,
                    "metrics": {
                        "invocations": snap.invocations,
                        "errors": snap.errors,
                        "avg_latency_ms": snap.avg_latency_ms,
                        "memory_mb": snap.memory_mb
                    },
                    "uptime": self.health_checker.get_uptime(agent_id),
                    "last_activity": snap.last_activity.isoformat()
                }
                for agent_id, snap in latest_snapshot.items()
            },
            "by_cloud": by_cloud,
            "alerts": [
                {
                    "id": a.alert_id,
                    "severity": a.severity.value,
                    "title": a.title,
                    "message": a.message,
                    "source": a.source,
                    "created_at": a.created_at.isoformat(),
                    "status": a.status.value
                }
                for a in self.alert_manager.get_active()
            ]
        }

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            metric_name: self.metrics.get_aggregation(metric_name)
            for metric_name in self.metrics.get_all_metrics()
        }

    def get_agent_detail(self, agent_id: str) -> Dict[str, Any]:
        """Get detailed data for a specific agent."""
        if agent_id not in self.agents:
            return {"error": "Agent not found"}

        agent = self.agents[agent_id]

        # Health history
        health_history = self.health_checker.check_history.get(agent_id, [])[-50:]

        # Metric history
        metric_data = {}
        for metric_name in self.metrics.get_all_metrics():
            if metric_name.startswith(f"{agent_id}."):
                short_name = metric_name.replace(f"{agent_id}.", "")
                points = self.metrics.get_metric(metric_name)[-100:]
                metric_data[short_name] = [
                    {"timestamp": p.timestamp.isoformat(), "value": p.value}
                    for p in points
                ]

        return {
            "agent_id": agent_id,
            "type": agent.name,
            "cloud": agent.cloud_config.provider.value,
            "region": agent.cloud_config.region,
            "current_health": self.health_checker.get_health(agent_id),
            "uptime_percent": self.health_checker.get_uptime(agent_id),
            "health_history": health_history,
            "metrics": metric_data,
            "alerts": [
                a.__dict__ for a in self.alert_manager.alerts.values()
                if a.source == agent_id
            ]
        }

    def export_report(self, format: str = "json") -> str:
        """Export monitoring report."""
        data = {
            "generated_at": datetime.now().isoformat(),
            "dashboard": self.get_dashboard_data(),
            "metrics": self.get_metrics_summary(),
            "alert_history": [
                {
                    "id": a.alert_id,
                    "severity": a.severity.value,
                    "title": a.title,
                    "status": a.status.value,
                    "created_at": a.created_at.isoformat()
                }
                for a in self.alert_manager.alert_history[-100:]
            ]
        }

        if format == "json":
            return json.dumps(data, indent=2, default=str)
        else:
            # Could add CSV, HTML formats
            return json.dumps(data, default=str)
