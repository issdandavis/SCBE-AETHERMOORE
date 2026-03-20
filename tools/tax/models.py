"""Data models for tax filing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FilingStatus(Enum):
    SINGLE = "single"
    MARRIED_FILING_JOINTLY = "married_filing_jointly"
    MARRIED_FILING_SEPARATELY = "married_filing_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"
    QUALIFYING_SURVIVING_SPOUSE = "qualifying_surviving_spouse"


@dataclass
class W2:
    """IRS Form W-2 fields."""

    employer_name: str = ""
    employer_ein: str = ""
    wages: float = 0.0  # Box 1: Wages, tips, other compensation
    federal_tax_withheld: float = 0.0  # Box 2: Federal income tax withheld
    social_security_wages: float = 0.0  # Box 3: Social security wages
    social_security_tax: float = 0.0  # Box 4: Social security tax withheld
    medicare_wages: float = 0.0  # Box 5: Medicare wages and tips
    medicare_tax: float = 0.0  # Box 6: Medicare tax withheld
    state: str = ""  # Box 15: State
    state_wages: float = 0.0  # Box 16: State wages
    state_tax_withheld: float = 0.0  # Box 17: State income tax


@dataclass
class Income1099:
    """Simplified 1099 income (interest, dividends, freelance)."""

    type: str = ""  # "INT", "DIV", "NEC", "MISC"
    payer_name: str = ""
    amount: float = 0.0
    federal_tax_withheld: float = 0.0


@dataclass
class ItemizedDeductions:
    """Schedule A itemized deductions."""

    medical_expenses: float = 0.0  # Line 1 (subject to 7.5% AGI floor)
    state_local_taxes: float = 0.0  # Line 5 (SALT, capped at $10,000)
    real_estate_taxes: float = 0.0  # Line 5b
    mortgage_interest: float = 0.0  # Line 8a
    charitable_cash: float = 0.0  # Line 11
    charitable_noncash: float = 0.0  # Line 12
    other_deductions: float = 0.0  # Line 16


@dataclass
class TaxCredits:
    """Common tax credits."""

    child_tax_credit_dependents: int = 0  # Number of qualifying children under 17
    other_dependents: int = 0  # Number of other dependents
    education_credits: float = 0.0  # American Opportunity / Lifetime Learning
    retirement_savings_credit: float = 0.0  # Saver's Credit
    earned_income_credit: float = 0.0  # EIC (simplified — full calc is complex)
    estimated_tax_payments: float = 0.0  # Quarterly estimated payments made


@dataclass
class TaxpayerInfo:
    """Core taxpayer information."""

    first_name: str = ""
    last_name: str = ""
    ssn: str = ""  # XXX-XX-XXXX
    filing_status: FilingStatus = FilingStatus.SINGLE
    age: int = 0
    is_blind: bool = False
    spouse_first_name: str = ""
    spouse_last_name: str = ""
    spouse_ssn: str = ""
    spouse_age: int = 0
    spouse_is_blind: bool = False
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    can_be_claimed_as_dependent: bool = False


@dataclass
class TaxInput:
    """Everything needed to compute a 1040."""

    taxpayer: TaxpayerInfo = field(default_factory=TaxpayerInfo)
    w2s: list[W2] = field(default_factory=list)
    income_1099s: list[Income1099] = field(default_factory=list)
    other_income: float = 0.0  # Line 8 catch-all
    itemized_deductions: Optional[ItemizedDeductions] = None  # None = use standard
    credits: TaxCredits = field(default_factory=TaxCredits)
    ira_deduction: float = 0.0
    student_loan_interest: float = 0.0  # Max $2,500
    hsa_deduction: float = 0.0


@dataclass
class TaxResult:
    """Computed 1040 results."""

    # Income
    total_wages: float = 0.0  # Line 1
    interest_income: float = 0.0  # Line 2b
    dividend_income: float = 0.0  # Line 3b
    other_income: float = 0.0  # Line 8
    total_income: float = 0.0  # Line 9
    adjustments: float = 0.0  # Line 10
    adjusted_gross_income: float = 0.0  # Line 11

    # Deductions
    standard_deduction: float = 0.0
    itemized_deduction: float = 0.0
    deduction_used: str = "standard"  # "standard" or "itemized"
    qualified_business_deduction: float = 0.0  # Line 13 (QBI)
    total_deductions: float = 0.0  # Line 14
    taxable_income: float = 0.0  # Line 15

    # Tax computation
    tax: float = 0.0  # Line 16
    child_tax_credit: float = 0.0  # Line 19
    other_credits: float = 0.0  # Line 21
    total_credits: float = 0.0
    tax_after_credits: float = 0.0

    # Other taxes
    self_employment_tax: float = 0.0  # Line 23
    total_tax: float = 0.0  # Line 24

    # Payments
    federal_withheld: float = 0.0  # Line 25
    estimated_payments: float = 0.0  # Line 26
    total_payments: float = 0.0  # Line 33

    # Result
    refund: float = 0.0  # Line 34 (if payments > tax)
    amount_owed: float = 0.0  # Line 37 (if tax > payments)

    # Breakdown for transparency
    bracket_breakdown: list[dict] = field(default_factory=list)
    effective_rate: float = 0.0
    marginal_rate: float = 0.0
