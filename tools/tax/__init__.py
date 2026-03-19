"""SCBE Tax Tool — Personal 1040 tax calculator and PDF exporter.

Built for Tax Year 2025 (filing in 2026).
Supports: W-2 income, standard/itemized deductions, common credits.
Output: Print-ready PDF or text summary.

Usage:
    python -m tools.tax.cli calculate --input my_w2.json
    python -m tools.tax.cli calculate --input my_w2.json --pdf output.pdf
    python -m tools.tax.cli template --output sample_input.json
"""
