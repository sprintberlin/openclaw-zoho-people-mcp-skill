#!/usr/bin/env python3
"""Inspect one Zoho People employee record by erecno through mcporter."""

import argparse
import json
import os
import subprocess
import sys

MCP_URL = os.environ.get("ZOHO_PEOPLE_MCP_URL", "")
TOOL = "ZohoPeople_fetchEmployeeRecordById"


def positive_int(value):
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def build_parser():
    parser = argparse.ArgumentParser(description="Inspect one Zoho People employee record.")
    parser.add_argument("erecno", type=positive_int, help="employee erecno / record ID")
    parser.add_argument("--json", action="store_true", help="print raw JSON (default)")
    parser.add_argument("--timeout", type=positive_int, default=30, help="MCP call timeout in seconds (default: 30)")
    return parser


def fetch_employee(erecno, timeout=30):
    if not MCP_URL:
        print("Error: ZOHO_PEOPLE_MCP_URL not set. Please set the environment variable.", file=sys.stderr)
        sys.exit(1)

    cmd = [
        "mcporter",
        "call",
        f"{MCP_URL}.{TOOL}",
        "--args",
        json.dumps({"query_params": {"recordId": str(erecno)}}, ensure_ascii=False),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError:
        return {"error": "mcporter executable not found"}
    except subprocess.TimeoutExpired:
        return {"error": "mcporter call timed out"}

    if result.returncode != 0:
        return {"error": result.stderr.strip() or "mcporter call failed"}
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": result.stderr.strip() or "mcporter returned invalid JSON"}
    if parsed.get("status") in {"error", "failure"}:
        return {"error": parsed.get("error") or parsed.get("data") or parsed.get("message") or "Zoho People request failed"}
    return parsed


def main(argv=None):
    args = build_parser().parse_args(argv)

    result = fetch_employee(args.erecno, args.timeout)
    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
