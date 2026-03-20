"""1040 tax calculator engine for Tax Year 2025."""

from __future__ import annotations

from .models import FilingStatus, TaxInput, TaxResult
from .tax_tables import (
    ADDITIONAL_CHILD_TAX_CREDIT_MAX,
    ADDITIONAL_DEDUCTION_AGED_BLIND,
    CHILD_TAX_CREDIT_AMOUNT,
    CHILD_TAX_CREDIT_PHASEOUT_RATE,
    CHILD_TAX_CREDIT_PHASEOUT_START,
    OTHER_DEPENDENT_CREDIT,
    SALT_CAP,
    STANDARD_DEDUCTION,
    STUDENT_LOAN_INTEREST_MAX,
    STUDENT_LOAN_PHASEOUT_RANGE,
    STUDENT_LOAN_PHASEOUT_START,
    TAX_BRACKETS,
)


def _compute_bracket_tax(taxable_income: float, status: FilingStatus) -> tuple[float, list[dict], float]:
    """Compute federal income tax from brackets. Returns (tax, breakdown, marginal_rate)."""
    brackets = TAX_BRACKETS[status]
    tax = 0.0
    breakdown = []
    prev_bound = 0.0
    marginal_rate = 0.0

    for upper, rate in brackets:
        if taxable_income <= 0:
            break
        taxable_in_bracket = min(taxable_income, upper) - prev_bound
        if taxable_in_bracket <= 0:
            prev_bound = upper
            continue
        bracket_tax = taxable_in_bracket * rate
        tax += bracket_tax
        breakdown.append({
            "bracket": f"{prev_bound:,.0f} - {upper:,.0f}" if upper != float("inf") else f"{prev_bound:,.0f}+",
            "rate": f"{rate:.0%}",
            "income_in_bracket": round(taxable_in_bracket, 2),
            "tax": round(bracket_tax, 2),
        })
        marginal_rate = rate
        prev_bound = upper

    return round(tax, 2), breakdown, marginal_rate


def _compute_standard_deduction(inp: TaxInput) -> float:
    """Compute standard deduction including age/blind additions."""
    base = STANDARD_DEDUCTION[inp.taxpayer.filing_status]
    status = inp.taxpayer.filing_status
    is_married = status in (
        FilingStatus.MARRIED_FILING_JOINTLY,
        FilingStatus.MARRIED_FILING_SEPARATELY,
        FilingStatus.QUALIFYING_SURVIVING_SPOUSE,
    )
    add_amount = ADDITIONAL_DEDUCTION_AGED_BLIND["married" if is_married else "single_or_hoh"]

    additions = 0.0
    if inp.taxpayer.age >= 65:
        additions += add_amount
    if inp.taxpayer.is_blind:
        additions += add_amount

    if is_married and status != FilingStatus.MARRIED_FILING_SEPARATELY:
        if inp.taxpayer.spouse_age >= 65:
            additions += add_amount
        if inp.taxpayer.spouse_is_blind:
            additions += add_amount

    return base + additions


def _compute_itemized_deduction(inp: TaxInput, agi: float) -> float:
    """Compute Schedule A itemized deduction total."""
    item = inp.itemized_deductions
    if item is None:
        return 0.0

    # Medical: only amount exceeding 7.5% of AGI
    medical = max(0, item.medical_expenses - 0.075 * agi)

    # SALT: capped at $10,000
    salt = min(item.state_local_taxes + item.real_estate_taxes, SALT_CAP)

    # Mortgage interest (no additional limits in simplified calc)
    mortgage = item.mortgage_interest

    # Charitable contributions
    charitable = item.charitable_cash + item.charitable_noncash

    return medical + salt + mortgage + charitable + item.other_deductions


def _compute_student_loan_deduction(inp: TaxInput, agi: float) -> float:
    """Compute student loan interest deduction with phaseout."""
    if inp.student_loan_interest <= 0:
        return 0.0
    status = inp.taxpayer.filing_status
    if status == FilingStatus.MARRIED_FILING_SEPARATELY:
        return 0.0  # Not available for MFS

    base = min(inp.student_loan_interest, STUDENT_LOAN_INTEREST_MAX)
    start = STUDENT_LOAN_PHASEOUT_START[status]
    phase_range = STUDENT_LOAN_PHASEOUT_RANGE[status]

    if phase_range <= 0 or agi <= start:
        return base
    if agi >= start + phase_range:
        return 0.0

    reduction = base * (agi - start) / phase_range
    return max(0, round(base - reduction, 2))


def _compute_child_tax_credit(inp: TaxInput, agi: float, tax_liability: float) -> tuple[float, float]:
    """Compute child tax credit (nonrefundable + refundable portions).

    Returns (nonrefundable_credit, refundable_additional_ctc).
    """
    num_children = inp.credits.child_tax_credit_dependents
    num_other = inp.credits.other_dependents
    if num_children <= 0 and num_other <= 0:
        return 0.0, 0.0

    status = inp.taxpayer.filing_status
    total_credit = (num_children * CHILD_TAX_CREDIT_AMOUNT) + (num_other * OTHER_DEPENDENT_CREDIT)

    # Phaseout: $50 reduction per $1,000 (or fraction) over threshold
    threshold = CHILD_TAX_CREDIT_PHASEOUT_START[status]
    if agi > threshold:
        excess = agi - threshold
        # Round up to nearest $1,000
        reduction_units = -(-int(excess) // 1000)  # ceiling division
        reduction = reduction_units * (CHILD_TAX_CREDIT_PHASEOUT_RATE * 1000)
        total_credit = max(0, total_credit - reduction)

    # Nonrefundable portion: limited to tax liability
    nonrefundable = min(total_credit, tax_liability)

    # Refundable (Additional CTC): for qualifying children only
    child_credit_portion = min(num_children * CHILD_TAX_CREDIT_AMOUNT, total_credit)
    unused_child_credit = child_credit_portion - min(child_credit_portion, tax_liability)
    refundable = min(unused_child_credit, num_children * ADDITIONAL_CHILD_TAX_CREDIT_MAX)

    return round(nonrefundable, 2), round(refundable, 2)


def _compute_self_employment_tax(inp: TaxInput) -> tuple[float, float]:
    """Compute SE tax from 1099-NEC income. Returns (se_tax, deductible_half)."""
    nec_income = sum(i.amount for i in inp.income_1099s if i.type.upper() == "NEC")
    if nec_income <= 400:
        return 0.0, 0.0

    # 92.35% of net SE earnings
    se_earnings = nec_income * 0.9235
    # Social Security portion (capped at wage base minus W-2 SS wages)
    w2_ss_wages = sum(w.social_security_wages for w in inp.w2s)
    from .tax_tables import SOCIAL_SECURITY_WAGE_BASE, SOCIAL_SECURITY_RATE, MEDICARE_RATE

    ss_base = max(0, SOCIAL_SECURITY_WAGE_BASE - w2_ss_wages)
    ss_tax = min(se_earnings, ss_base) * SOCIAL_SECURITY_RATE
    med_tax = se_earnings * MEDICARE_RATE
    se_tax = round((ss_tax + med_tax) * 2, 2)  # Both halves

    deductible_half = round(se_tax / 2, 2)
    return se_tax, deductible_half


def calculate(inp: TaxInput) -> TaxResult:
    """Run the full 1040 calculation."""
    result = TaxResult()

    # --- INCOME (Lines 1-9) ---
    result.total_wages = round(sum(w.wages for w in inp.w2s), 2)
    result.interest_income = round(
        sum(i.amount for i in inp.income_1099s if i.type.upper() == "INT"), 2
    )
    result.dividend_income = round(
        sum(i.amount for i in inp.income_1099s if i.type.upper() == "DIV"), 2
    )
    nec_income = round(
        sum(i.amount for i in inp.income_1099s if i.type.upper() == "NEC"), 2
    )
    misc_income = round(
        sum(i.amount for i in inp.income_1099s if i.type.upper() == "MISC"), 2
    )
    result.other_income = round(nec_income + misc_income + inp.other_income, 2)
    result.total_income = round(
        result.total_wages + result.interest_income + result.dividend_income + result.other_income, 2
    )

    # --- ADJUSTMENTS (Line 10) ---
    se_tax, se_deductible = _compute_self_employment_tax(inp)
    result.self_employment_tax = se_tax

    adjustments = se_deductible + inp.ira_deduction + inp.hsa_deduction
    # Student loan needs preliminary AGI (income minus other adjustments)
    preliminary_agi = result.total_income - adjustments
    student_loan = _compute_student_loan_deduction(inp, preliminary_agi)
    adjustments += student_loan
    result.adjustments = round(adjustments, 2)

    # --- AGI (Line 11) ---
    result.adjusted_gross_income = round(result.total_income - result.adjustments, 2)
    agi = result.adjusted_gross_income

    # --- DEDUCTIONS (Lines 12-14) ---
    result.standard_deduction = _compute_standard_deduction(inp)
    result.itemized_deduction = _compute_itemized_deduction(inp, agi)

    if inp.itemized_deductions is not None and result.itemized_deduction > result.standard_deduction:
        result.deduction_used = "itemized"
        total_deduction = result.itemized_deduction
    else:
        result.deduction_used = "standard"
        total_deduction = result.standard_deduction

    result.total_deductions = round(total_deduction, 2)

    # --- TAXABLE INCOME (Line 15) ---
    result.taxable_income = round(max(0, agi - result.total_deductions), 2)

    # --- TAX (Line 16) ---
    result.tax, result.bracket_breakdown, result.marginal_rate = _compute_bracket_tax(
        result.taxable_income, inp.taxpayer.filing_status
    )

    # --- CREDITS (Lines 19-21) ---
    nonrefundable_ctc, refundable_ctc = _compute_child_tax_credit(inp, agi, result.tax)
    result.child_tax_credit = nonrefundable_ctc

    result.other_credits = round(
        inp.credits.education_credits + inp.credits.retirement_savings_credit, 2
    )
    result.total_credits = round(result.child_tax_credit + result.other_credits, 2)
    result.tax_after_credits = round(max(0, result.tax - result.total_credits), 2)

    # --- TOTAL TAX (Line 24) ---
    result.total_tax = round(result.tax_after_credits + result.self_employment_tax, 2)

    # --- PAYMENTS (Lines 25-33) ---
    result.federal_withheld = round(
        sum(w.federal_tax_withheld for w in inp.w2s)
        + sum(i.federal_tax_withheld for i in inp.income_1099s),
        2,
    )
    result.estimated_payments = round(
        inp.credits.estimated_tax_payments + refundable_ctc + inp.credits.earned_income_credit, 2
    )
    result.total_payments = round(result.federal_withheld + result.estimated_payments, 2)

    # --- REFUND OR AMOUNT OWED ---
    diff = result.total_payments - result.total_tax
    if diff >= 0:
        result.refund = round(diff, 2)
        result.amount_owed = 0.0
    else:
        result.refund = 0.0
        result.amount_owed = round(-diff, 2)

    # --- EFFECTIVE RATE ---
    if result.total_income > 0:
        result.effective_rate = round(result.total_tax / result.total_income, 4)

    return result
