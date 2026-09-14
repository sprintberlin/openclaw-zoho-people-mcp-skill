#!/usr/bin/env python3
"""Fetch Zoho People leave balances for one employee through mcporter."""

import argparse
import json
import os
import subprocess
import sys

MCP_URL = os.environ.get("ZOHO_PEOPLE_MCP_URL", "")
TOOL = "ZohoPeople_getLeaveBalance"


def positive_int(value):
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def year_value(value):
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed not in {-3, -2, -1, 0, 1}:
        raise argparse.ArgumentTypeError("must be 0, 1, or -1 to -3")
    return parsed


def build_parser():
    parser = argparse.ArgumentParser(description="Fetch Zoho People leave balances.")
    parser.add_argument("--erecno", required=True, help="employee erecno")
    parser.add_argument("--year", type=year_value, default=0, help="relative year: 0 current, 1 next, -1 to -3 past (default: 0)")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    parser.add_argument("--timeout", type=positive_int, default=30, help="MCP call timeout in seconds (default: 30)")
    return parser


def _mcporter_call(tool, args, timeout=30):
    if not MCP_URL:
        print("Error: ZOHO_PEOPLE_MCP_URL not set. Please set the environment variable.", file=sys.stderr)
        sys.exit(1)

    cmd = ["mcporter", "call", f"{MCP_URL}.{tool}", "--args", json.dumps(args, ensure_ascii=False)]
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


def normalize_people_result(result):
    if "error" in result:
        return None, None

    def rows_from(node):
        if isinstance(node, list):
            return node
        if isinstance(node, dict):
            for key in ("data", "leaveBalance", "balances", "response", "result"):
                if key in node:
                    inner = rows_from(node[key])
                    if inner is not None:
                        return inner
        return None

    payload = result.get("data", result)
    data = rows_from(payload)
    if data is None and isinstance(payload, dict):
        if "message" in payload:
            return [], {}
        return [payload], result.get("info", {})
    if data is None:
        return [], result.get("info", {})
    return data, result.get("info", {})


def pick_field(record, wanted):
    lower = {str(key).lower(): key for key in record}
    for candidate in wanted:
        if candidate in lower:
            return record[lower[candidate]]
    return ""


def fetch_leave_balance(erecno, year=0, timeout=30):
    body = {"erecno": str(erecno), "year": year}
    return _mcporter_call(TOOL, {"body": body}, timeout=timeout)


def print_table(data):
    if not data:
        print("No leave balances found.")
        return

    columns = [
        ("name", "Leave Type", ["leavetypename", "name", "type"]),
        ("available", "Available", ["available", "balance", "availablebalance"]),
        ("taken", "Taken", ["taken", "availed", "used"]),
        ("unit", "Unit", ["unit"]),
    ]
    rows = []
    for record in data:
        if pick_field(record, ["donotdisplaybalance"]) in {True, "true", "True"}:
            continue
        rows.append([str(pick_field(record, wanted) or "-") for _, _, wanted in columns])

    if not rows:
        print("No leave balances found.")
        return

    widths = [max(len(label), *(len(row[i]) for row in rows)) for i, (_, label, _) in enumerate(columns)]
    print(" | ".join(label.ljust(widths[i]) for i, (_, label, _) in enumerate(columns)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.ljust(widths[i]) for i, value in enumerate(row)))
    print(f"\n{len(rows)} leave type(s)")


def main(argv=None):
    args = build_parser().parse_args(argv)
    result = fetch_leave_balance(args.erecno, args.year, args.timeout)
    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    data, _info = normalize_people_result(result)
    if data is None:
        print(f"Error: {result.get('error') or 'Zoho People response could not be normalized'}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print_table(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
