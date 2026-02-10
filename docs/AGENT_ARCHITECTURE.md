# SCBE-AETHERMOORE Agent Architecture

**Version**: 3.0.0

**IP Classification**: Public / Private / Hidden

**Agent Types**: 6 Sacred Tongues (KO, AV, RU, CA, UM, DR)

---

## IP Classification Hierarchy

### Three-Tier Security Model

```
┌─────────────────────────────────────────────────────────────┐
│                    PUBLIC IP LAYER                          │
│  • Internet-facing agents                                   │
│  • API gateways, load balancers                             │
│  • Rate limiting, DDoS protection                           │
│  • Example: SCBE Gateway (8080), Web UI (443)               │
└─────────────────────┬───────────────────────────────────────┘
                      ↓ (Firewall/NAT)
┌─────────────────────────────────────────────────────────────┐
│                   PRIVATE IP LAYER                          │
│  • Internal service mesh                                    │
│  • Agent-to-agent coordination                              │
│  • Kafka, Temporal, Postgres                                │
│  • Example: Kafka broker (10.0.2.15:9093)                   │
└─────────────────────┬───────────────────────────────────────┘
                      ↓ (Zero-Trust Auth)
┌─────────────────────────────────────────────────────────────┐
│                    HIDDEN IP LAYER                          │
│  • Vault secrets                                            │
│  • Master encryption keys                                   │
│  • SCBE L14 decision engine                                 │
│  • Sacred Egg ritual keys                                   │
│  • No direct routing (accessed via proxy only)              │
└─────────────────────────────────────────────────────────────┘
```

---

## IP Tier Specifications

### Public IP Agents

**Exposure**: Internet-accessible

**Security**: TLS 1.3, WAF, rate limiting

**Use Cases**: Client ingress, monitoring dashboards

**Example Configuration**:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: scbe-gateway-public
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
spec:
  type: LoadBalancer
  selector:
    app: scbe-gateway
  ports:
  - port: 443
    targetPort: 8080
    protocol: TCP
```

**Allowed Operations**:

- ✅ SCBE decision requests (authenticated)
- ✅ Health checks
- ✅ Metrics scraping (read-only)
- ❌ Direct database access
- ❌ Secret retrieval
- ❌ Admin commands

---

### Private IP Agents

**Exposure**: VPC-internal only

**Security**: mTLS, network policies, service mesh

**Use Cases**: Agent coordination, event bus, workflow orchestration

**Example Configuration**:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: kafka-internal
spec:
  type: ClusterIP  # Private IP only
  clusterIP: 10.0.2.15
  selector:
    app: kafka
  ports:
  - port: 9093
    targetPort: 9093
    protocol: TCP
```

**Network Policy** (restrict access):

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: kafka-private-policy
spec:
  podSelector:
    matchLabels:
      app: kafka
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: agent  # Only agents can connect
    ports:
    - protocol: TCP
      port: 9093
```

**Allowed Operations**:

- ✅ Kafka pub/sub
- ✅ Temporal workflow execution
- ✅ Postgres read/write
- ✅ Agent-to-agent RWP envelopes
- ❌ Internet egress (except via NAT)
- ❌ Vault direct access (use proxy)

---

### Hidden IP Agents

**Exposure**: No direct routing

**Security**: Air-gapped, proxy-only access, hardware security modules

**Use Cases**: Master keys, SCBE Layer 14 decisions, Sacred Eggs

**Architecture**:

```
[Agent] → [Vault Proxy] → [Hidden Vault Pod]
           (mTLS auth)      (No ingress)
                              |
                              v
                        [AWS KMS/HSM]
                        (Encrypted at rest)
```

**Kubernetes Configuration**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: vault-hidden
  annotations:
    sidecar.istio.io/inject: "false"  # No service mesh
spec:
  hostNetwork: false  # Isolated network namespace
  containers:
  - name: vault
    image: vault:1.15.0
    ports: []  # No exposed ports!
    volumeMounts:
    - name: vault-tls
      mountPath: /vault/tls
      readOnly: true
    env:
    - name: VAULT_ADDR
      value: unix:///vault/sock/vault.sock  # Unix socket only
  volumes:
  - name: vault-tls
    secret:
      secretName: vault-ca-cert
```

**Access Pattern** (proxy-only):

```typescript
// Agents cannot access Vault directly
// Must go through authenticated proxy

import { VaultProxy } from './proxy';

const proxy = new VaultProxy({
  endpoint: 'vault-proxy.internal:8200',  // Proxy, not Vault
  auth: {
    method: 'approle',
    roleId: process.env.VAULT_ROLE_ID,
    secretId: process.env.VAULT_SECRET_ID,
  },
});

// Proxy validates agent identity, rate limits, audits
const secret = await proxy.getSecret('scbe/master-key');
```

**Allowed Operations**:

- ✅ Secret retrieval (via proxy + AppRole)
- ✅ Sacred Egg unsealing (multi-party ritual)
- ✅ SCBE Layer 14 Omega Gate decisions
- ❌ Direct network access
- ❌ SSH/console access
- ❌ Log streaming (audit logs written to immutable storage)

---

## Agent Structure by Tongue

### Agent Anatomy

Each agent has:

1. **Tongue Identity** (KO, AV, RU, CA, UM, DR)
2. **IP Tier** (public, private, or hidden)
3. **Phase Offset** (0°, 60°, 120°, 180°, 240°, 300°)
4. **Weight** (φⁿ, where n = tongue index)
5. **Position** (x, y, z in Poincaré ball)
6. **Coherence Score** (0.0 - 1.0)

```typescript
interface Agent {
  id: string;  // UUID
  tongue: 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
  ipTier: 'public' | 'private' | 'hidden';

  // Geometric properties
  position: [number, number, number];  // Poincaré ball (||pos|| < 1)
  phase: number;  // Radians (0 to 2π)
  weight: number;  // φⁿ (golden ratio power)

  // State
  coherence: number;  // PHDM polyhedral coherence
  lastHeartbeat: number;  // Unix timestamp
  status: 'active' | 'degraded' | 'offline';

  // Security
  publicKey: Buffer;  // ML-DSA-65 public key
  vaultRoleId: string;  // For secret access
}
```

---

### Tongue-to-IP Mapping (Typical Deployment)

| Tongue | Phase | Weight | IP Tier | Purpose | Example Host |
| --- | --- | --- | --- | --- | --- |
| **KO** | 0° | 1.00 | Public | Control/Orchestration | scbe-gateway:8080 |
| **AV** | 60° | 1.618 | Private | Transport/Init | kafka-broker:9093 |
| **RU** | 120° | 2.618 | Private | Policy/Rules | temporal-worker:7233 |
| **CA** | 180° | 4.236 | Private | Compute/Encryption | notion-worker:8080 |
| **UM** | 240° | 6.854 | Hidden | Security/Redaction | vault-hidden:unix |
| **DR** | 300° | 11.090 | Hidden | Schema/Auth | scbe-l14-engine:unix |

**Rationale**:

- **KO** (Control) = Public-facing gateway (needs internet access)
- **AV/RU/CA** (Transport/Policy/Compute) = Private mesh (internal coordination)
- **UM/DR** (Security/Auth) = Hidden (master keys, final decisions)

---

## Agent Lifecycle

### 1. Initialization

```typescript
// src/agent/lifecycle.ts

import { generateKeyPair } from './crypto';
import { registerWithVault } from './vault';
import { joinPoincareSwarm } from './swarm';

export async function initializeAgent(tongue: Tongue, ipTier: IPTier): Promise<Agent> {
  // Step 1: Generate PQC keypair
  const { publicKey, privateKey } = await generateKeyPair('ML-DSA-65');

  // Step 2: Register with Vault (get role ID)
  const vaultRoleId = await registerWithVault({
    tongue,
    publicKey: publicKey.toString('base64'),
    ipTier,
  });

  // Step 3: Calculate geometric properties
  const phase = TONGUE_PHASES[tongue];  // 0°, 60°, ...
  const weight = Math.pow(GOLDEN_RATIO, TONGUE_INDICES[tongue]);

  // Step 4: Join Poincaré swarm (find initial position)
  const position = await joinPoincareSwarm(tongue, ipTier);

  // Step 5: Create agent object
  const agent: Agent = {
    id: randomUUID(),
    tongue,
    ipTier,
    position,
    phase,
    weight,
    coherence: 1.0,  // Start perfect
    lastHeartbeat: Date.now(),
    status: 'active',
    publicKey,
    vaultRoleId,
  };

  // Step 6: Announce to swarm
  await publishKafkaEvent({
    type: 'agent.joined',
    payload: agent,
  });

  return agent;
}
```

---

### 2. Heartbeat Protocol

```typescript
// Send heartbeat every 5 seconds
setInterval(async () => {
  const heartbeat = {
    agentId: agent.id,
    tongue: agent.tongue,
    position: agent.position,
    coherence: await computeCoherence(agent),
    timestamp: Date.now(),
  };

  await publishKafkaEvent({
    type: 'agent.heartbeat',
    payload: heartbeat,
  });

  agent.lastHeartbeat = Date.now();
}, 5000);

// Detect dead agents
setInterval(async () => {
  const agents = await db.query('SELECT * FROM agents');
  const now = Date.now();

  for (const a of agents) {
    if (now - a.lastHeartbeat > 15000) {  // 15s timeout
      await markAgentDead(a.id);
      await publishKafkaEvent({
        type: 'agent.offline',
        payload: { agentId: a.id },
      });
    }
  }
}, 10000);
```

---

### 3. Graceful Shutdown

```typescript
process.on('SIGTERM', async () => {
  console.log('🛑 Shutting down agent...');

  // Step 1: Stop accepting new work
  await httpServer.close();

  // Step 2: Finish in-flight tasks (up to 30s)
  await Promise.race([
    finishInFlightTasks(),
    sleep(30000),
  ]);

  // Step 3: Announce departure
  await publishKafkaEvent({
    type: 'agent.leaving',
    payload: { agentId: agent.id },
  });

  // Step 4: Disconnect from services
  await kafka.disconnect();
  await db.disconnect();

  console.log('✅ Agent shutdown complete');
  process.exit(0);
});
```

---

## IP Tier Transition Scenarios

### Promoting Private → Public

**Use Case**: Scale out public API capacity

```bash
# 1. Create public LoadBalancer
kubectl apply -f public-lb.yaml

# 2. Update agent config
kubectl set env deployment/scbe-gateway IP_TIER=public

# 3. Verify external IP assigned
kubectl get svc scbe-gateway-public

# 4. Update DNS (A record)
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123 \
  --change-batch '{"Changes":[{"Action":"UPSERT","ResourceRecordSet":{"Name":"api.aethermoore.com","Type":"A","TTL":300,"ResourceRecords":[{"Value":"54.213.12.45"}]}}]}'
```

---

### Demoting Public → Private

**Use Case**: Retire public endpoint, consolidate to internal mesh

```bash
# 1. Drain traffic (wait 5 minutes)
kubectl scale deployment scbe-gateway --replicas=0

# 2. Delete public service
kubectl delete svc scbe-gateway-public

# 3. Recreate as ClusterIP
kubectl apply -f private-svc.yaml

# 4. Update agent config
kubectl set env deployment/scbe-gateway IP_TIER=private

# 5. Scale back up
kubectl scale deployment scbe-gateway --replicas=3
```

---

### Isolating to Hidden

**Use Case**: Move SCBE L14 decision engine to air-gapped environment

```bash
# 1. Deploy hidden pod (no ports)
kubectl apply -f hidden-pod.yaml

# 2. Deploy proxy pod
kubectl apply -f vault-proxy.yaml

# 3. Update network policy (deny all ingress)
kubectl apply -f deny-all-policy.yaml

# 4. Verify no external routes
kubectl exec -it scbe-l14-engine -- ip route
# Output: (empty, no default gateway)

# 5. Test access via proxy only
curl http://vault-proxy:8200/v1/scbe/master-key \
  -H "X-Vault-Token: $TOKEN"
```

---

## Security Boundaries

### Trust Zones

```
┌───────────────────────────────────────────────────────────┐
│  ZONE 1: INTERNET (Untrusted)                            │
│  • DDoS attacks, credential stuffing, scraping           │
│  • Defense: WAF, rate limiting, CAPTCHA                   │
└─────────────────────┬─────────────────────────────────────┘
                      ↓ (TLS 1.3, mTLS)
┌───────────────────────────────────────────────────────────┐
│  ZONE 2: PUBLIC IP LAYER (Semi-Trusted)                  │
│  • Authenticated clients, monitoring tools                │
│  • Defense: JWT validation, IP allowlist, audit logs      │
└─────────────────────┬─────────────────────────────────────┘
                      ↓ (Network Policy, Service Mesh)
┌───────────────────────────────────────────────────────────┐
│  ZONE 3: PRIVATE IP LAYER (Trusted)                      │
│  • Internal agents, databases, event bus                  │
│  • Defense: Zero-trust auth, encrypted transit, RBAC      │
└─────────────────────┬─────────────────────────────────────┘
                      ↓ (Proxy-only, AppRole, HSM)
┌───────────────────────────────────────────────────────────┐
│  ZONE 4: HIDDEN IP LAYER (Maximum Trust)                 │
│  • Master keys, SCBE L14, Sacred Eggs                     │
│  • Defense: Air-gap, no ingress, hardware security        │
└───────────────────────────────────────────────────────────┘
```

---

## Deployment Checklist

### Public IP Agents

- [ ] TLS certificate valid (Let's Encrypt or AWS ACM)
- [ ] WAF rules configured (OWASP Top 10)
- [ ] Rate limiting enabled (100 req/s per IP)
- [ ] DDoS protection active (CloudFlare or AWS Shield)
- [ ] Health checks passing (HTTP 200 on /health)
- [ ] DNS A record updated
- [ ] Monitoring alerts configured

### Private IP Agents

- [ ] Network policy applied (deny-all + allowlist)
- [ ] Service mesh injected (Istio sidecar)
- [ ] mTLS certificates provisioned
- [ ] Kafka ACLs configured (topic-level permissions)
- [ ] Postgres roles created (least privilege)
- [ ] No public IP assigned (ClusterIP only)
- [ ] Egress blocked (except to NAT gateway)

### Hidden IP Agents

- [ ] No ingress ports exposed
- [ ] Unix socket communication only
- [ ] Proxy pod deployed and tested
- [ ] AppRole authentication working
- [ ] Hardware security module (HSM) integrated
- [ ] Immutable audit log enabled
- [ ] No SSH access (console disabled)
- [ ] Encrypted at rest (LUKS or AWS KMS)

---

## Related Documentation

- [Swarm Deployment Formations](./SWARM_FORMATIONS.md) - 6-agent Poincaré ball coordination patterns
- [Byzantine Fault Tolerance](./BYZANTINE_FAULT_TOLERANCE.md) - BFT configurations
- [Rogue Agent Detection](./ROGUE_DETECTION.md) - Detection and quarantine procedures
- [SpaceX Swarm Demo](./SPACEX_DEMO.md) - Demo architecture
