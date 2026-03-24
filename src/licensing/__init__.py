"""
SCBE Licensing & Monetization Module
=====================================

Supports three distribution models:
  1. OEM License (Black Box) — White-label, support-free
  2. Usage-Based Billing — Per-1k decisions + platform floor
  3. Source-Available (As-Is) — Air-gap compatible, no warranty

Compliance:
  - NIST AI RMF 1.0
  - NIST SP 800-53 Rev 5
  - FIPS 140-3
  - CMMC 2.0

@module licensing
@version 1.0.0
"""

from .oem_license import (
    LicenseTier,
    LicenseModel,
    LicenseClaims,
    LicenseKey,
    ValidationResult,
    generate_license_key,
    validate_license_key,
    create_tier_license,
)

from .usage_meter import (
    UsageMeter,
    DecisionRecord,
)

from .nist_ai_rmf import (
    ComplianceCheck,
    ComplianceReport,
    generate_compliance_report,
    TradeWindsProfile,
    SBIRDeliverable,
    PolicyPillarAlignment,
    PolicyFrameworkReport,
    generate_policy_framework_report,
    generate_combined_compliance_summary,
)

__all__ = [
    "LicenseTier",
    "LicenseModel",
    "LicenseClaims",
    "LicenseKey",
    "ValidationResult",
    "generate_license_key",
    "validate_license_key",
    "create_tier_license",
    "UsageMeter",
    "DecisionRecord",
    "ComplianceCheck",
    "ComplianceReport",
    "generate_compliance_report",
    "TradeWindsProfile",
    "SBIRDeliverable",
    "PolicyPillarAlignment",
    "PolicyFrameworkReport",
    "generate_policy_framework_report",
    "generate_combined_compliance_summary",
]
