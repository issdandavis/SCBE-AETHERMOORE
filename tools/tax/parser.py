"""Parse tax input from JSON files into typed models."""

from __future__ import annotations

import json
from pathlib import Path

from .models import (
    FilingStatus,
    Income1099,
    ItemizedDeductions,
    TaxCredits,
    TaxInput,
    TaxpayerInfo,
    W2,
)


def _parse_w2(data: dict) -> W2:
    return W2(
        employer_name=str(data.get("employer_name", "")),
        employer_ein=str(data.get("employer_ein", "")),
        wages=float(data.get("wages", 0)),
        federal_tax_withheld=float(data.get("federal_tax_withheld", 0)),
        social_security_wages=float(data.get("social_security_wages", 0)),
        social_security_tax=float(data.get("social_security_tax", 0)),
        medicare_wages=float(data.get("medicare_wages", 0)),
        medicare_tax=float(data.get("medicare_tax", 0)),
        state=str(data.get("state", "")),
        state_wages=float(data.get("state_wages", 0)),
        state_tax_withheld=float(data.get("state_tax_withheld", 0)),
    )


def _parse_1099(data: dict) -> Income1099:
    return Income1099(
        type=str(data.get("type", "")),
        payer_name=str(data.get("payer_name", "")),
        amount=float(data.get("amount", 0)),
        federal_tax_withheld=float(data.get("federal_tax_withheld", 0)),
    )


def _parse_itemized(data: dict | None) -> ItemizedDeductions | None:
    if not data:
        return None
    return ItemizedDeductions(
        medical_expenses=float(data.get("medical_expenses", 0)),
        state_local_taxes=float(data.get("state_local_taxes", 0)),
        real_estate_taxes=float(data.get("real_estate_taxes", 0)),
        mortgage_interest=float(data.get("mortgage_interest", 0)),
        charitable_cash=float(data.get("charitable_cash", 0)),
        charitable_noncash=float(data.get("charitable_noncash", 0)),
        other_deductions=float(data.get("other_deductions", 0)),
    )


def _parse_credits(data: dict | None) -> TaxCredits:
    if not data:
        return TaxCredits()
    return TaxCredits(
        child_tax_credit_dependents=int(data.get("child_tax_credit_dependents", 0)),
        other_dependents=int(data.get("other_dependents", 0)),
        education_credits=float(data.get("education_credits", 0)),
        retirement_savings_credit=float(data.get("retirement_savings_credit", 0)),
        earned_income_credit=float(data.get("earned_income_credit", 0)),
        estimated_tax_payments=float(data.get("estimated_tax_payments", 0)),
    )


def _parse_filing_status(raw: str) -> FilingStatus:
    normalized = raw.strip().lower().replace(" ", "_").replace("-", "_")
    for status in FilingStatus:
        if status.value == normalized:
            return status
    valid = [s.value for s in FilingStatus]
    raise ValueError(f"Invalid filing status '{raw}'. Valid options: {valid}")


def parse_tax_input(file_path: str | Path) -> TaxInput:
    """Load a JSON file and return a TaxInput."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Tax input file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    tp = data.get("taxpayer", {})

    taxpayer = TaxpayerInfo(
        first_name=str(tp.get("first_name", "")),
        last_name=str(tp.get("last_name", "")),
        ssn=str(tp.get("ssn", "")),
        filing_status=_parse_filing_status(tp.get("filing_status", "single")),
        age=int(tp.get("age", 0)),
        is_blind=bool(tp.get("is_blind", False)),
        spouse_first_name=str(tp.get("spouse_first_name", "")),
        spouse_last_name=str(tp.get("spouse_last_name", "")),
        spouse_ssn=str(tp.get("spouse_ssn", "")),
        spouse_age=int(tp.get("spouse_age", 0)),
        spouse_is_blind=bool(tp.get("spouse_is_blind", False)),
        address=str(tp.get("address", "")),
        city=str(tp.get("city", "")),
        state=str(tp.get("state", "")),
        zip_code=str(tp.get("zip_code", "")),
        can_be_claimed_as_dependent=bool(tp.get("can_be_claimed_as_dependent", False)),
    )

    return TaxInput(
        taxpayer=taxpayer,
        w2s=[_parse_w2(w) for w in data.get("w2s", [])],
        income_1099s=[_parse_1099(i) for i in data.get("income_1099s", [])],
        other_income=float(data.get("other_income", 0)),
        itemized_deductions=_parse_itemized(data.get("itemized_deductions")),
        credits=_parse_credits(data.get("credits")),
        ira_deduction=float(data.get("ira_deduction", 0)),
        student_loan_interest=float(data.get("student_loan_interest", 0)),
        hsa_deduction=float(data.get("hsa_deduction", 0)),
    )


def generate_template() -> dict:
    """Return a sample JSON template with all fields documented."""
    return {
        "_comment": "SCBE Tax Tool — Tax Year 2025 input template. Fill in your values.",
        "taxpayer": {
            "first_name": "Jane",
            "last_name": "Doe",
            "ssn": "000-00-0000",
            "filing_status": "single",
            "_filing_status_options": [
                "single",
                "married_filing_jointly",
                "married_filing_separately",
                "head_of_household",
                "qualifying_surviving_spouse",
            ],
            "age": 30,
            "is_blind": False,
            "spouse_first_name": "",
            "spouse_last_name": "",
            "spouse_ssn": "",
            "spouse_age": 0,
            "spouse_is_blind": False,
            "address": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "zip_code": "90210",
            "can_be_claimed_as_dependent": False,
        },
        "w2s": [
            {
                "_comment": "One entry per W-2. Copy values from your W-2 form.",
                "employer_name": "Acme Corp",
                "employer_ein": "12-3456789",
                "wages": 65000.00,
                "federal_tax_withheld": 8500.00,
                "social_security_wages": 65000.00,
                "social_security_tax": 4030.00,
                "medicare_wages": 65000.00,
                "medicare_tax": 942.50,
                "state": "CA",
                "state_wages": 65000.00,
                "state_tax_withheld": 3200.00,
            }
        ],
        "income_1099s": [
            {
                "_comment": "One entry per 1099. type: INT, DIV, NEC, or MISC.",
                "type": "INT",
                "payer_name": "Chase Bank",
                "amount": 150.00,
                "federal_tax_withheld": 0.00,
            }
        ],
        "other_income": 0.00,
        "itemized_deductions": {
            "_comment": "Fill this out OR delete this section to use standard deduction.",
            "medical_expenses": 0.00,
            "state_local_taxes": 0.00,
            "real_estate_taxes": 0.00,
            "mortgage_interest": 0.00,
            "charitable_cash": 0.00,
            "charitable_noncash": 0.00,
            "other_deductions": 0.00,
        },
        "credits": {
            "child_tax_credit_dependents": 0,
            "other_dependents": 0,
            "education_credits": 0.00,
            "retirement_savings_credit": 0.00,
            "earned_income_credit": 0.00,
            "estimated_tax_payments": 0.00,
        },
        "ira_deduction": 0.00,
        "student_loan_interest": 0.00,
        "hsa_deduction": 0.00,
    }
