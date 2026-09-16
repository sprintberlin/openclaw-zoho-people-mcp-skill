#!/usr/bin/env python3
"""Fetch Zoho People attendance summaries through mcporter."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from mcp_endpoint import EndpointResolutionError, EndpointSelector, add_endpoint_arguments

ENDPOINT = EndpointSelector("people", ("ZOHO_PEOPLE_MCP_URL",))

TOOL = "ZohoPeople_getAttendanceSummary"


def positive_int(value):
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def build_parser():
    parser = argparse.ArgumentParser(description="Fetch Zoho People attendance summaries.")
    parser.add_argument("--erecno", help="comma-separated employee erecno values; omit for all users")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    parser.add_argument("--limit", type=positive_int, help="return at most this many employees")
    parser.add_argument("--page-size", type=positive_int, default=200, help="batch size (default: 200)")
    parser.add_argument("--timeout", type=positive_int, default=30, help="MCP call timeout in seconds (default: 30)")
    add_endpoint_arguments(parser)
    return parser


def _mcporter_call(tool, args, timeout=30):
    """Call mcporter directly without a shell."""
    try:
        mcp_url = ENDPOINT.get()
    except EndpointResolutionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    cmd = ["mcporter", "call", f"{mcp_url}.{tool}", "--args", json.dumps(args, ensure_ascii=False)]
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


def seconds_to_hhmm(value):
    if value in (None, "", "-"):
        return "-"
    if isinstance(value, str) and ":" in value:
        return value
    try:
        total = int(float(value))
    except (TypeError, ValueError):
        return str(value)
    sign = "-" if total < 0 else ""
    total = abs(total)
    hours, remainder = divmod(total, 3600)
    minutes = remainder // 60
    return f"{sign}{hours:02d}:{minutes:02d}"


def normalize_people_result(result):
    if "error" in result:
        return None, None

    payload = result.get("data", result)
    if isinstance(payload, dict):
        for key in ("summaryReport", "data", "result", "response"):
            node = payload.get(key)
            if isinstance(node, list):
                return node, payload.get("info", {})
            if isinstance(node, dict):
                for nested in ("summaryReport", "data", "result"):
                    inner = node.get(nested)
                    if isinstance(inner, list):
                        return inner, payload.get("info", {})
        if "message" in payload:
            return [], {}
    if isinstance(payload, list):
        return payload, result.get("info", {})
    return [], result.get("info", {})


def query_attendance_page(erecno=None, s_index=0, timeout=30):
    body = {}
    if erecno:
        body["erecno"] = str(erecno)
    else:
        body["sIndex"] = s_index
    return _mcporter_call(TOOL, {"body": body}, timeout=timeout)


def query_all_attendance(erecno=None, per_page=200, max_records=None, timeout=30):
    all_data = []
    s_index = 0

    while True:
        result = query_attendance_page(erecno, s_index, timeout)
        if "error" in result:
            return result
        data, info = normalize_people_result(result)
        if data is None:
            return {"error": "Zoho People response could not be normalized"}
        all_data.extend(data)
        if erecno or max_records is not None and len(all_data) >= max_records:
            break
        if not data or len(data) < per_page:
            break
        s_index += len(data)

    if max_records is not None:
        all_data = all_data[:max_records]
    return {"data": all_data, "info": {"count": len(all_data), "more_records": False}}


def pick_field(record, wanted):
    lower = {str(key).lower(): key for key in record}
    for candidate in wanted:
        if candidate in lower:
            return record[lower[candidate]]
    return ""


def print_table(data):
    if not data:
        print("No attendance summaries found.")
        return

    columns = [
        ("name", "Name", ["name", "empname"]),
        ("email", "Email", ["emailid", "email"]),
        ("worked_days", "Worked Days", ["totalworkeddays"]),
        ("payable_days", "Payable Days", ["totalpayabledays"]),
        ("worked_hours", "Worked Hours", ["totalworkedhours"]),
        ("overtime", "Overtime", ["overtime", "netovertime"]),
    ]
    rows = []
    for record in data:
        row = []
        for key, _label, wanted in columns:
            value = pick_field(record, wanted)
            if key in {"worked_hours", "overtime"}:
                value = seconds_to_hhmm(value)
            row.append(str(value or "-"))
        rows.append(row)

    widths = [max(len(label), *(len(row[i]) for row in rows)) for i, (_, label, _) in enumerate(columns)]
    print(" | ".join(label.ljust(widths[i]) for i, (_, label, _) in enumerate(columns)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.ljust(widths[i]) for i, value in enumerate(row)))
    print(f"\n{len(data)} employee(s)")


def main(argv=None):
    args = build_parser().parse_args(argv)
    ENDPOINT.configure(args)
    result = query_all_attendance(
        erecno=args.erecno,
        per_page=args.page_size,
        max_records=args.limit,
        timeout=args.timeout,
    )
    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    data, _info = normalize_people_result(result)
    if data is None:
        print("Error: Zoho People response could not be normalized", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print_table(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
