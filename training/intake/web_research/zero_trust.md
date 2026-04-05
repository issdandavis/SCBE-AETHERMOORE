# Zero Trust Architecture (NIST SP 800-207)

Zero trust is a security model based on the principle of maintaining strict access controls and not trusting any entity by default, even those already inside the network perimeter. Published by NIST as Special Publication 800-207, it provides a comprehensive framework for implementing zero trust principles.

## Core Tenets

Never trust, always verify. Every access request is fully authenticated, authorized, and encrypted before granting access. Assume breach — design security as if the network is already compromised. Verify explicitly using all available data points (user identity, device, location, service, workload, data classification, anomalies).

## Key Principles

### Least Privilege Access
Grant minimum permissions needed for the task. Time-bound and just-enough access. Regularly review and revoke unnecessary access. Use just-in-time (JIT) and just-enough-access (JEA) policies.

### Microsegmentation
Divide the network into small, isolated segments. Each segment has its own security controls. Lateral movement is restricted even after initial access. Software-defined perimeters replace traditional network perimeters.

### Continuous Verification
Authentication and authorization happen continuously, not just at initial login. Session risk is reassessed based on changing context. Behavioral analytics detect anomalous access patterns. Real-time policy enforcement based on trust score.

### Device Trust
Every device accessing resources must be identified and assessed. Device health, compliance, and patch status are verified. Managed and unmanaged devices have different access levels. Mobile device management (MDM) and endpoint detection and response (EDR) are integrated.

### Data-Centric Security
Protect data directly rather than just the perimeter. Classify and label data by sensitivity. Apply encryption, access controls, and DLP at the data level. Monitor data access patterns for anomalies.

## Architecture Components

### Policy Engine (PE)
Makes access decisions based on enterprise policy. Evaluates trust scores from multiple inputs. Grants, denies, or revokes access to resources.

### Policy Administrator (PA)
Executes PE decisions by configuring data plane components. Establishes and tears down communication paths. Generates session-specific authentication tokens.

### Policy Enforcement Point (PEP)
Enables, monitors, and terminates connections between subjects and resources. The gateway that actually enforces the PE's decisions.

## Implementation Approaches

### Enhanced Identity Governance
Use identity as the primary security perimeter. Strong authentication (MFA, passwordless, FIDO2). Fine-grained authorization based on identity attributes. Identity federation for cross-organizational access.

### Software Defined Perimeters (SDP)
Create dynamic, identity-based network perimeters. Resources are invisible to unauthorized users. Single-packet authorization before connection establishment.

### Micro-Perimeters
Protect individual workloads or applications. Each application has its own security boundary. Service mesh architectures (Istio, Linkerd) implement micro-perimeters. Mutual TLS (mTLS) between all services.

## Deployment Models

Agent/gateway model: agents on endpoints communicate with gateway. Enclave-based: protect groups of resources behind a gateway. Resource portal: single portal mediates all access. Device application sandboxing: isolate applications on user devices.
