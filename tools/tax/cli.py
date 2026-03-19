"""CLI entry point for the SCBE Tax Tool.

Usage:
    python -m tools.tax.cli template --output my_taxes.json
    python -m tools.tax.cli calculate --input my_taxes.json
    python -m tools.tax.cli calculate --input my_taxes.json --pdf return.pdf
    python -m tools.tax.cli calculate --input my_taxes.json --json results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .calculator import calculate
from .exporter import generate_json_output, generate_pdf, generate_text_summary
from .parser import generate_template, parse_tax_input


def cmd_template(args: argparse.Namespace) -> int:
    """Generate a sample input JSON template."""
    template = generate_template()
    output = Path(args.output) if args.output else None

    text = json.dumps(template, indent=2)
    if output:
        output.write_text(text, encoding="utf-8")
        print(f"Template written to: {output}")
        print("Edit the file with your actual tax data, then run:")
        print(f"  python -m tools.tax.cli calculate --input {output}")
    else:
        print(text)
    return 0


def cmd_calculate(args: argparse.Namespace) -> int:
    """Calculate taxes from input file."""
    try:
        tax_input = parse_tax_input(args.input)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        return 1

    result = calculate(tax_input)

    # Always print text summary
    summary = generate_text_summary(tax_input, result)
    print(summary)

    # Optional PDF output
    if args.pdf:
        pdf_path = generate_pdf(tax_input, result, args.pdf)
        print(f"\nPDF written to: {pdf_path}")

    # Optional JSON output
    if args.json:
        json_text = generate_json_output(tax_input, result)
        Path(args.json).write_text(json_text, encoding="utf-8")
        print(f"JSON written to: {args.json}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="scbe-tax",
        description="SCBE Tax Tool — Personal 1040 calculator for Tax Year 2025",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # template
    tpl = subparsers.add_parser("template", help="Generate a sample input JSON template")
    tpl.add_argument("--output", "-o", default="", help="Output file path (prints to stdout if omitted)")

    # calculate
    calc = subparsers.add_parser("calculate", help="Calculate taxes from input file")
    calc.add_argument("--input", "-i", required=True, help="Path to tax input JSON file")
    calc.add_argument("--pdf", default="", help="Output PDF file path")
    calc.add_argument("--json", default="", help="Output JSON file path")

    args = parser.parse_args()
    if args.command == "template":
        return cmd_template(args)
    elif args.command == "calculate":
        return cmd_calculate(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
