# Hardware Security Support For Autonomy Systems

Date: 2026-04-26

## Scope

This is a defensive hardware-security map for SCBE agent-bus, HYDRA, and autonomy-adjacent proposal work. It focuses on securing computing hardware, firmware, supply chain, telemetry, and lifecycle assurance. It does not provide tactical drone operation, payload, targeting, evasion, or countermeasure guidance.

## Direct Answer

Yes, we can find and package the things needed to secure hardware for autonomy-adjacent systems. The strongest path is not a single product. It is a layered assurance stack:

1. hardware inventory;
2. hardware bill of materials;
3. software bill of materials;
4. cryptographic bill of materials;
5. Trusted Platform Module or hardware root of trust;
6. secure boot and measured boot;
7. signed firmware updates;
8. firmware recovery path;
9. acceptance testing and configuration baseline;
10. runtime integrity telemetry;
11. lifecycle maintenance evidence;
12. red-team and regression testing before deployment.

For SCBE, this maps cleanly to the agent-bus rehearsal gate: a hardware-backed mission cannot pass strict mode unless the hardware identity, firmware state, telemetry sink, abort rule, and maintenance baseline are known.

## Official Guidance To Use

### NIST SP 800-193: Platform Firmware Resiliency

Use this as the firmware security backbone. NIST frames firmware resiliency around protecting the platform against unauthorized changes, detecting unauthorized changes, and recovering rapidly and securely.

SCBE transfer:

- add `firmware_integrity_required` to mission envelopes;
- require signed update evidence for hardware-backed runs;
- treat firmware recovery as part of rollback planning;
- score hardware lanes on protect/detect/recover coverage.

### NSA Trusted Platform Module Guidance

NSA states that Trusted Platform Modules protect keys used during acceptance testing and operational use to validate computing-system integrity. NSA also highlights TPM use for asset management, hardware supply-chain checks, and startup integrity monitoring.

SCBE transfer:

- add optional `tpm_attestation` metadata to HYDRA packets;
- require TPM 2.0 or equivalent hardware root of trust for high-risk hardware lanes;
- use measured boot/startup state as an input to the agent-bus rehearsal gate.

### CISA Hardware Bill of Materials Framework

Use Hardware Bill of Materials records to document equipment components and supply-chain risk. This gives the hardware side the same provenance posture we want for datasets and models.

SCBE transfer:

- add `hbom_path` to mission envelopes;
- require component provenance before hardware-backed proposal claims;
- connect hardware inventory to provider/device scoreboard records.

### CISA/NIST Software Bill of Materials Guidance

Use Software Bill of Materials records for firmware, embedded software, operator tooling, and local services. NIST notes that SBOMs are a transparency and vulnerability-management tool, not a replacement for risk management.

SCBE transfer:

- add `sbom_path` and `vulnerability_scan_path`;
- require SBOM freshness before remote/live hardware demos;
- connect vulnerability alerts to help-desk tickets.

## SAM.gov Signals Found

The SAM.gov API scan was run with the configured key without printing the key. Outputs:

- `artifacts/contracts/hardware_security_scan_20260426/sam_api_capture_scan_2026-04-26T15-42-48Z.json`
- `artifacts/contracts/hardware_security_scan_20260426/sam_api_capture_scan_2026-04-26T15-42-48Z.md`
- `artifacts/contracts/hardware_security_scan_20260426/hardware_security_shortlist_20260426.md`

Useful signals:

- `DARPA-PS-26-04` / CyPhER Forge: cyber-physical digital twin and AI test agent.
- `RFI-ARMY-DTSPO-2026-0420`: enterprise governance, data tagging, and records management.
- `N0017326Q5313`: annual software maintenance/support and hardware calibration.
- `N6523626QE138`: secure chat servers.
- `36C10B26Q0376`: supply chain management DevSecOps and integration.
- `CORHQ-26-Q-0059`: identity governance software.

These are not all direct bid fits. Their value is evidence: government buyers are asking for governance, maintenance, calibration, identity, cyber-physical test, and supply-chain assurance. Those are the same supports our system needs.

## Proposed SCBE Hardware Security Envelope

Add this optional block to HYDRA or agent-bus mission packets:

```json
{
  "hardware_security": {
    "asset_id": "device-or-kit-id",
    "risk_class": "low|medium|high",
    "hbom_path": "artifacts/hardware/<asset>/hbom.json",
    "sbom_path": "artifacts/hardware/<asset>/sbom.json",
    "cbom_path": "artifacts/hardware/<asset>/cbom.json",
    "firmware_version": "vendor-version-or-hash",
    "firmware_signature_verified": true,
    "secure_boot_required": true,
    "measured_boot_required": true,
    "tpm_or_root_of_trust": "tpm2|secure-element|hsm|none",
    "attestation_path": "artifacts/hardware/<asset>/attestation.json",
    "maintenance_baseline_path": "artifacts/hardware/<asset>/maintenance.json",
    "last_acceptance_test": "2026-04-26T00:00:00Z"
  }
}
```

## Feature Branches To Add

### `feat/hardware-security-envelope`

Add hardware-security fields to the mission envelope and gate validator.

### `feat/hardware-bom-registry`

Create a local `artifacts/hardware/` registry for Hardware Bill of Materials, Software Bill of Materials, Cryptographic Bill of Materials, firmware versions, and maintenance records.

### `feat/firmware-integrity-gate`

Block high-risk hardware-backed bus missions unless firmware signature, secure boot, measured boot, and rollback evidence are present.

### `feat/tpm-attestation-import`

Accept Trusted Platform Module or hardware-root-of-trust attestation reports as gate evidence.

### `feat/hardware-lifecycle-scoreboard`

Score assets by provenance completeness, patch age, firmware status, maintenance age, and failed gate history.

## How This Improves Our System

- Makes hardware claims proposal-ready instead of hand-wavy.
- Gives the agent bus a physical-world readiness layer.
- Makes demos safer because hardware state must be known before live use.
- Creates training data from hardware acceptance and maintenance events.
- Aligns SCBE with NIST, CISA, NSA, and DARPA language without overclaiming.

## Sources

- NIST SP 800-193, Platform Firmware Resiliency Guidelines: https://csrc.nist.gov/pubs/sp/800/193/final
- NSA, Trusted Platform Module Use Cases: https://www.nsa.gov/Press-Room/Press-Releases-Statements/Press-Release-View/Article/3959033/nsa-issues-guidance-for-using-trusted-platform-modules-tpms/
- CISA, Hardware Bill of Materials Framework: https://www.cisa.gov/news-events/news/cisa-releases-hardware-bill-materials-framework-hbom-supply-chain-risk-management-scrm
- CISA, Software Bill of Materials: https://www.cisa.gov/sbom
- NIST, Software Security in Supply Chains and SBOM: https://www.nist.gov/itl/executive-order-14028-improving-nations-cybersecurity/software-security-supply-chains-software-1
