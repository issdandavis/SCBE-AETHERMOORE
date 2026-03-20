"""Tax Year 2025 tax tables, brackets, and constants.

Sources:
- IRS Revenue Procedure 2024-40 (inflation adjustments for TY2025)
- https://www.irs.gov/newsroom/irs-provides-tax-inflation-adjustments-for-tax-year-2025
"""

from __future__ import annotations

from .models import FilingStatus

# ---------------------------------------------------------------------------
# 2025 Federal Income Tax Brackets
# Each entry: (upper_bound, rate). The last entry uses float("inf").
# ---------------------------------------------------------------------------
TAX_BRACKETS: dict[FilingStatus, list[tuple[float, float]]] = {
    FilingStatus.SINGLE: [
        (11_925, 0.10),
        (48_475, 0.12),
        (103_350, 0.22),
        (197_300, 0.24),
        (250_525, 0.32),
        (626_350, 0.35),
        (float("inf"), 0.37),
    ],
    FilingStatus.MARRIED_FILING_JOINTLY: [
        (23_850, 0.10),
        (96_950, 0.12),
        (206_700, 0.22),
        (394_600, 0.24),
        (501_050, 0.32),
        (751_600, 0.35),
        (float("inf"), 0.37),
    ],
    FilingStatus.MARRIED_FILING_SEPARATELY: [
        (11_925, 0.10),
        (48_475, 0.12),
        (103_350, 0.22),
        (197_300, 0.24),
        (250_525, 0.32),
        (375_800, 0.35),
        (float("inf"), 0.37),
    ],
    FilingStatus.HEAD_OF_HOUSEHOLD: [
        (17_000, 0.10),
        (64_850, 0.12),
        (103_350, 0.22),
        (197_300, 0.24),
        (250_500, 0.32),
        (626_350, 0.35),
        (float("inf"), 0.37),
    ],
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: [
        (23_850, 0.10),
        (96_950, 0.12),
        (206_700, 0.22),
        (394_600, 0.24),
        (501_050, 0.32),
        (751_600, 0.35),
        (float("inf"), 0.37),
    ],
}

# ---------------------------------------------------------------------------
# Standard Deductions (TY2025)
# ---------------------------------------------------------------------------
STANDARD_DEDUCTION: dict[FilingStatus, float] = {
    FilingStatus.SINGLE: 15_000,
    FilingStatus.MARRIED_FILING_JOINTLY: 30_000,
    FilingStatus.MARRIED_FILING_SEPARATELY: 15_000,
    FilingStatus.HEAD_OF_HOUSEHOLD: 22_500,
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 30_000,
}

# Additional standard deduction for age 65+ or blind (per person)
ADDITIONAL_DEDUCTION_AGED_BLIND: dict[str, float] = {
    "single_or_hoh": 2_000,  # Single or Head of Household
    "married": 1_600,  # Married (filing jointly or separately) or QSS
}

# ---------------------------------------------------------------------------
# Social Security & Medicare (FICA) — TY2025
# ---------------------------------------------------------------------------
SOCIAL_SECURITY_RATE = 0.062
SOCIAL_SECURITY_WAGE_BASE = 176_100  # 2025 wage base
MEDICARE_RATE = 0.0145
ADDITIONAL_MEDICARE_RATE = 0.009  # On wages above threshold
ADDITIONAL_MEDICARE_THRESHOLD: dict[FilingStatus, float] = {
    FilingStatus.SINGLE: 200_000,
    FilingStatus.MARRIED_FILING_JOINTLY: 250_000,
    FilingStatus.MARRIED_FILING_SEPARATELY: 125_000,
    FilingStatus.HEAD_OF_HOUSEHOLD: 200_000,
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 250_000,
}

# Self-employment tax rate (both halves of FICA)
SELF_EMPLOYMENT_TAX_RATE = 0.153  # 12.4% SS + 2.9% Medicare
SELF_EMPLOYMENT_DEDUCTION_RATE = 0.5  # Deduct employer-equivalent half

# ---------------------------------------------------------------------------
# Child Tax Credit (TY2025)
# ---------------------------------------------------------------------------
CHILD_TAX_CREDIT_AMOUNT = 2_000  # Per qualifying child under 17
OTHER_DEPENDENT_CREDIT = 500  # Per other dependent
CHILD_TAX_CREDIT_PHASEOUT_START: dict[FilingStatus, float] = {
    FilingStatus.SINGLE: 200_000,
    FilingStatus.MARRIED_FILING_JOINTLY: 400_000,
    FilingStatus.MARRIED_FILING_SEPARATELY: 200_000,
    FilingStatus.HEAD_OF_HOUSEHOLD: 200_000,
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 400_000,
}
CHILD_TAX_CREDIT_PHASEOUT_RATE = 0.05  # $50 per $1,000 over threshold

# Refundable portion (Additional Child Tax Credit)
ADDITIONAL_CHILD_TAX_CREDIT_MAX = 1_700  # Max refundable per child for TY2025

# ---------------------------------------------------------------------------
# SALT Cap
# ---------------------------------------------------------------------------
SALT_CAP = 10_000  # State and Local Tax deduction cap

# ---------------------------------------------------------------------------
# Student Loan Interest Deduction
# ---------------------------------------------------------------------------
STUDENT_LOAN_INTEREST_MAX = 2_500
STUDENT_LOAN_PHASEOUT_START: dict[FilingStatus, float] = {
    FilingStatus.SINGLE: 80_000,
    FilingStatus.MARRIED_FILING_JOINTLY: 165_000,
    FilingStatus.MARRIED_FILING_SEPARATELY: 0,  # Not available
    FilingStatus.HEAD_OF_HOUSEHOLD: 80_000,
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 165_000,
}
STUDENT_LOAN_PHASEOUT_RANGE: dict[FilingStatus, float] = {
    FilingStatus.SINGLE: 15_000,
    FilingStatus.MARRIED_FILING_JOINTLY: 30_000,
    FilingStatus.MARRIED_FILING_SEPARATELY: 0,
    FilingStatus.HEAD_OF_HOUSEHOLD: 15_000,
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 30_000,
}

# ---------------------------------------------------------------------------
# Earned Income Credit (simplified — full tables are enormous)
# Max credit amounts for TY2025 (approximate, subject to final IRS pub)
# ---------------------------------------------------------------------------
EIC_MAX_INVESTMENT_INCOME = 11_950

# ---------------------------------------------------------------------------
# IRA Contribution Limits
# ---------------------------------------------------------------------------
IRA_CONTRIBUTION_LIMIT = 7_000
IRA_CONTRIBUTION_LIMIT_AGE_50_PLUS = 8_000

# ---------------------------------------------------------------------------
# Qualified Business Income (QBI) Deduction — Section 199A
# ---------------------------------------------------------------------------
QBI_DEDUCTION_RATE = 0.20  # 20% of qualified business income
QBI_TAXABLE_INCOME_THRESHOLD: dict[FilingStatus, float] = {
    FilingStatus.SINGLE: 191_950,
    FilingStatus.MARRIED_FILING_JOINTLY: 383_900,
    FilingStatus.MARRIED_FILING_SEPARATELY: 191_950,
    FilingStatus.HEAD_OF_HOUSEHOLD: 191_950,
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 383_900,
}
