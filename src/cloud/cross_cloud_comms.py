"""
Cross-Cloud Communication Layer
===============================

Enables secure communication between agents deployed on AWS and GCP.
Provides unified messaging, service discovery, and failover capabilities.

FEATURES:
=========
1. Service Discovery - Find agents across clouds
2. Message Routing - Intelligent cross-cloud routing
3. Circuit Breaker - Fault tolerance
4. Message Queue - Async communication
5. Encryption - End-to-end encryption

Version: 1.0.0
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import base64

logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    """Message priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class MessageStatus(Enum):
    """Message delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    TIMEOUT = "timeout"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CloudEndpoint:
    """Represents a cloud service endpoint."""
    endpoint_id: str
    cloud: str  # aws, gcp
    region: str
    url: str
    agent_type: str
    health_check_url: Optional[str] = None
    last_health_check: Optional[datetime] = None
    healthy: bool = True
    latency_ms: float = 0


@dataclass
class CrossCloudMessage:
    """Message for cross-cloud communication."""
    message_id: str
    source_cloud: str
    source_agent: str
    target_cloud: str
    target_agent: str
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    status: MessageStatus = MessageStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    encrypted: bool = True
    signature: Optional[str] = None


class ServiceRegistry:
    """
    Service discovery registry for cross-cloud agents.
    """

    def __init__(self):
        self.endpoints: Dict[str, CloudEndpoint] = {}
        self.by_cloud: Dict[str, List[str]] = {"aws": [], "gcp": []}
        self.by_type: Dict[str, List[str]] = {}

    def register(self, endpoint: CloudEndpoint) -> str:
        """Register an endpoint."""
        self.endpoints[endpoint.endpoint_id] = endpoint
        self.by_cloud[endpoint.cloud].append(endpoint.endpoint_id)

        if endpoint.agent_type not in self.by_type:
            self.by_type[endpoint.agent_type] = []
        self.by_type[endpoint.agent_type].append(endpoint.endpoint_id)

        logger.info(f"Registered endpoint: {endpoint.endpoint_id} on {endpoint.cloud}")
        return endpoint.endpoint_id

    def unregister(self, endpoint_id: str):
        """Unregister an endpoint."""
        if endpoint_id not in self.endpoints:
            return

        endpoint = self.endpoints[endpoint_id]
        self.by_cloud[endpoint.cloud].remove(endpoint_id)
        self.by_type[endpoint.agent_type].remove(endpoint_id)
        del self.endpoints[endpoint_id]

    def discover(
        self,
        agent_type: Optional[str] = None,
        cloud: Optional[str] = None,
        healthy_only: bool = True
    ) -> List[CloudEndpoint]:
        """Discover endpoints matching criteria."""
        results = list(self.endpoints.values())

        if agent_type:
            results = [e for e in results if e.agent_type == agent_type]

        if cloud:
            results = [e for e in results if e.cloud == cloud]

        if healthy_only:
            results = [e for e in results if e.healthy]

        # Sort by latency
        results.sort(key=lambda e: e.latency_ms)

        return results

    def get(self, endpoint_id: str) -> Optional[CloudEndpoint]:
        """Get endpoint by ID."""
        return self.endpoints.get(endpoint_id)

    def update_health(self, endpoint_id: str, healthy: bool, latency_ms: float = 0):
        """Update endpoint health status."""
        if endpoint_id in self.endpoints:
            self.endpoints[endpoint_id].healthy = healthy
            self.endpoints[endpoint_id].latency_ms = latency_ms
            self.endpoints[endpoint_id].last_health_check = datetime.now()


class CircuitBreaker:
    """
    Circuit breaker for fault tolerance.
    Prevents cascading failures across clouds.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.circuits: Dict[str, Dict[str, Any]] = {}

    def get_state(self, circuit_id: str) -> CircuitState:
        """Get circuit state."""
        if circuit_id not in self.circuits:
            self.circuits[circuit_id] = {
                "state": CircuitState.CLOSED,
                "failures": 0,
                "last_failure": None,
                "half_open_calls": 0
            }

        circuit = self.circuits[circuit_id]

        if circuit["state"] == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if circuit["last_failure"]:
                elapsed = (datetime.now() - circuit["last_failure"]).total_seconds()
                if elapsed >= self.recovery_timeout:
                    circuit["state"] = CircuitState.HALF_OPEN
                    circuit["half_open_calls"] = 0

        return circuit["state"]

    def can_execute(self, circuit_id: str) -> bool:
        """Check if execution is allowed."""
        state = self.get_state(circuit_id)

        if state == CircuitState.CLOSED:
            return True

        if state == CircuitState.HALF_OPEN:
            circuit = self.circuits[circuit_id]
            if circuit["half_open_calls"] < self.half_open_max_calls:
                circuit["half_open_calls"] += 1
                return True
            return False

        return False  # OPEN

    def record_success(self, circuit_id: str):
        """Record successful call."""
        if circuit_id not in self.circuits:
            return

        circuit = self.circuits[circuit_id]

        if circuit["state"] == CircuitState.HALF_OPEN:
            # Successful call in half-open state, close circuit
            circuit["state"] = CircuitState.CLOSED
            circuit["failures"] = 0

    def record_failure(self, circuit_id: str):
        """Record failed call."""
        if circuit_id not in self.circuits:
            self.circuits[circuit_id] = {
                "state": CircuitState.CLOSED,
                "failures": 0,
                "last_failure": None,
                "half_open_calls": 0
            }

        circuit = self.circuits[circuit_id]
        circuit["failures"] += 1
        circuit["last_failure"] = datetime.now()

        if circuit["failures"] >= self.failure_threshold:
            circuit["state"] = CircuitState.OPEN
            logger.warning(f"Circuit {circuit_id} opened after {circuit['failures']} failures")


class MessageQueue:
    """
    Async message queue for cross-cloud communication.
    """

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.queues: Dict[str, asyncio.Queue] = {}
        self.message_store: Dict[str, CrossCloudMessage] = {}
        self.delivery_callbacks: Dict[str, Callable] = {}

    def get_queue(self, target: str) -> asyncio.Queue:
        """Get or create queue for target."""
        if target not in self.queues:
            self.queues[target] = asyncio.Queue(maxsize=self.max_size)
        return self.queues[target]

    async def enqueue(self, message: CrossCloudMessage) -> str:
        """Add message to queue."""
        queue = self.get_queue(message.target_agent)
        self.message_store[message.message_id] = message

        await queue.put(message.message_id)
        return message.message_id

    async def dequeue(self, target: str, timeout: float = 30) -> Optional[CrossCloudMessage]:
        """Get next message for target."""
        queue = self.get_queue(target)

        try:
            message_id = await asyncio.wait_for(queue.get(), timeout=timeout)
            message = self.message_store.get(message_id)

            if message and message.expires_at and datetime.now() > message.expires_at:
                # Message expired
                del self.message_store[message_id]
                return None

            return message

        except asyncio.TimeoutError:
            return None

    def acknowledge(self, message_id: str, success: bool = True):
        """Acknowledge message delivery."""
        if message_id in self.message_store:
            message = self.message_store[message_id]
            message.status = MessageStatus.DELIVERED if success else MessageStatus.FAILED

            if message_id in self.delivery_callbacks:
                self.delivery_callbacks[message_id](success)
                del self.delivery_callbacks[message_id]

    def on_delivery(self, message_id: str, callback: Callable):
        """Register delivery callback."""
        self.delivery_callbacks[message_id] = callback

    def get_pending(self, target: Optional[str] = None) -> List[CrossCloudMessage]:
        """Get pending messages."""
        messages = list(self.message_store.values())

        if target:
            messages = [m for m in messages if m.target_agent == target]

        return [m for m in messages if m.status == MessageStatus.PENDING]


class MessageEncryption:
    """
    End-to-end encryption for cross-cloud messages.
    """

    def __init__(self, shared_key: Optional[bytes] = None):
        self.shared_key = shared_key or self._generate_key()

    def _generate_key(self) -> bytes:
        """Generate encryption key."""
        import secrets
        return secrets.token_bytes(32)

    def encrypt(self, data: Dict[str, Any]) -> str:
        """Encrypt message payload."""
        try:
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

            # Derive key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'scbe_cross_cloud',
                iterations=100000
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.shared_key))

            f = Fernet(key)
            plaintext = json.dumps(data).encode()
            return f.encrypt(plaintext).decode()

        except ImportError:
            # Fallback: Base64 encode (not secure, just for demo)
            return base64.b64encode(json.dumps(data).encode()).decode()

    def decrypt(self, encrypted: str) -> Dict[str, Any]:
        """Decrypt message payload."""
        try:
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'scbe_cross_cloud',
                iterations=100000
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.shared_key))

            f = Fernet(key)
            plaintext = f.decrypt(encrypted.encode())
            return json.loads(plaintext.decode())

        except ImportError:
            # Fallback
            return json.loads(base64.b64decode(encrypted).decode())

    def sign(self, data: Dict[str, Any]) -> str:
        """Sign message for integrity."""
        content = json.dumps(data, sort_keys=True)
        signature = hashlib.sha256(
            (content + self.shared_key.hex()).encode()
        ).hexdigest()
        return signature

    def verify(self, data: Dict[str, Any], signature: str) -> bool:
        """Verify message signature."""
        expected = self.sign(data)
        return signature == expected


class CrossCloudRouter:
    """
    Intelligent message router for cross-cloud communication.
    """

    def __init__(
        self,
        registry: ServiceRegistry,
        circuit_breaker: CircuitBreaker,
        encryption: MessageEncryption
    ):
        self.registry = registry
        self.circuit_breaker = circuit_breaker
        self.encryption = encryption
        self.routing_stats: Dict[str, Dict[str, int]] = {}

    async def route(
        self,
        message: CrossCloudMessage,
        prefer_same_cloud: bool = True
    ) -> Optional[CloudEndpoint]:
        """Route message to best endpoint."""
        # Find target endpoints
        endpoints = self.registry.discover(
            agent_type=message.target_agent.split(":")[0] if ":" in message.target_agent else None,
            healthy_only=True
        )

        if not endpoints:
            return None

        # Filter by target cloud preference
        if prefer_same_cloud:
            same_cloud = [e for e in endpoints if e.cloud == message.source_cloud]
            if same_cloud:
                endpoints = same_cloud

        # Check circuit breakers
        available = []
        for endpoint in endpoints:
            circuit_id = f"{endpoint.cloud}:{endpoint.endpoint_id}"
            if self.circuit_breaker.can_execute(circuit_id):
                available.append(endpoint)

        if not available:
            return None

        # Select best endpoint (lowest latency)
        selected = min(available, key=lambda e: e.latency_ms)

        # Update routing stats
        route_key = f"{message.source_cloud}->{selected.cloud}"
        if route_key not in self.routing_stats:
            self.routing_stats[route_key] = {"count": 0, "failures": 0}
        self.routing_stats[route_key]["count"] += 1

        return selected

    def record_delivery(self, endpoint: CloudEndpoint, success: bool):
        """Record delivery result."""
        circuit_id = f"{endpoint.cloud}:{endpoint.endpoint_id}"

        if success:
            self.circuit_breaker.record_success(circuit_id)
        else:
            self.circuit_breaker.record_failure(circuit_id)

            route_key = f"*->{endpoint.cloud}"
            if route_key in self.routing_stats:
                self.routing_stats[route_key]["failures"] += 1


class CrossCloudCommunicator:
    """
    Main facade for cross-cloud communication.
    """

    def __init__(self, shared_key: Optional[bytes] = None):
        self.registry = ServiceRegistry()
        self.circuit_breaker = CircuitBreaker()
        self.encryption = MessageEncryption(shared_key)
        self.router = CrossCloudRouter(
            self.registry,
            self.circuit_breaker,
            self.encryption
        )
        self.queue = MessageQueue()
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the communicator."""
        self._running = True
        self._processor_task = asyncio.create_task(self._process_queue())
        logger.info("Cross-cloud communicator started")

    async def stop(self):
        """Stop the communicator."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Cross-cloud communicator stopped")

    def register_endpoint(
        self,
        cloud: str,
        region: str,
        url: str,
        agent_type: str,
        endpoint_id: Optional[str] = None
    ) -> str:
        """Register a cloud endpoint."""
        endpoint = CloudEndpoint(
            endpoint_id=endpoint_id or str(uuid.uuid4()),
            cloud=cloud,
            region=region,
            url=url,
            agent_type=agent_type
        )
        return self.registry.register(endpoint)

    async def send(
        self,
        source_cloud: str,
        source_agent: str,
        target_agent: str,
        payload: Dict[str, Any],
        target_cloud: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        ttl_seconds: int = 300
    ) -> str:
        """Send a cross-cloud message."""
        message = CrossCloudMessage(
            message_id=str(uuid.uuid4()),
            source_cloud=source_cloud,
            source_agent=source_agent,
            target_cloud=target_cloud or "",
            target_agent=target_agent,
            payload=self.encryption.encrypt(payload) if True else payload,
            priority=priority,
            expires_at=datetime.now() + timedelta(seconds=ttl_seconds),
            signature=self.encryption.sign(payload)
        )

        await self.queue.enqueue(message)
        return message.message_id

    async def receive(
        self,
        agent_id: str,
        timeout: float = 30
    ) -> Optional[Dict[str, Any]]:
        """Receive messages for an agent."""
        message = await self.queue.dequeue(agent_id, timeout)

        if not message:
            return None

        # Decrypt payload
        try:
            payload = self.encryption.decrypt(message.payload) if message.encrypted else message.payload
            return {
                "message_id": message.message_id,
                "source_cloud": message.source_cloud,
                "source_agent": message.source_agent,
                "payload": payload,
                "priority": message.priority.value,
                "created_at": message.created_at.isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to decrypt message: {e}")
            return None

    def acknowledge(self, message_id: str, success: bool = True):
        """Acknowledge message receipt."""
        self.queue.acknowledge(message_id, success)

    async def health_check(self, endpoint_id: str) -> bool:
        """Check endpoint health."""
        endpoint = self.registry.get(endpoint_id)
        if not endpoint:
            return False

        try:
            # Would make actual HTTP request in production
            start = time.time()
            # Simulated health check
            await asyncio.sleep(0.01)
            latency = (time.time() - start) * 1000

            self.registry.update_health(endpoint_id, True, latency)
            return True

        except Exception as e:
            self.registry.update_health(endpoint_id, False)
            return False

    async def _process_queue(self):
        """Background queue processor."""
        while self._running:
            try:
                # Process messages for all registered endpoints
                for endpoint_id in list(self.registry.endpoints.keys()):
                    endpoint = self.registry.get(endpoint_id)
                    if not endpoint or not endpoint.healthy:
                        continue

                    message = await self.queue.dequeue(endpoint.agent_type, timeout=0.1)
                    if message:
                        # Route and deliver message
                        target = await self.router.route(message)
                        if target:
                            # Would make actual HTTP request
                            success = True  # Simulated
                            self.router.record_delivery(target, success)
                            self.queue.acknowledge(message.message_id, success)

                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(1)

    def get_stats(self) -> Dict[str, Any]:
        """Get communication statistics."""
        return {
            "endpoints": {
                "total": len(self.registry.endpoints),
                "healthy": len([e for e in self.registry.endpoints.values() if e.healthy]),
                "by_cloud": {
                    cloud: len(endpoints)
                    for cloud, endpoints in self.registry.by_cloud.items()
                }
            },
            "routing": self.router.routing_stats,
            "circuits": {
                cid: circuit["state"].value
                for cid, circuit in self.circuit_breaker.circuits.items()
            },
            "queue": {
                "pending": len(self.queue.message_store)
            }
        }
