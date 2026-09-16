#!/usr/bin/env python3
"""List Zoho People leave types, optionally with full configuration details."""

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

LIST_TOOL = "ZohoPeople_fetchLeaveTypes"
DETAILS_TOOL = "ZohoPeople_fetchLeaveTypeDetails"


def positive_int(value):
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def build_parser():
    parser = argparse.ArgumentParser(description="List Zoho People leave types.")
    parser.add_argument("--details", metavar="NAME_OR_ID", help="show full configuration for one leave type")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    parser.add_argument("--limit", type=positive_int, default=30, help="page size / maximum types (default: 30)")
    parser.add_argument("--page-size", type=positive_int, default=30, help="request page size (default: 30)")
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


def normalize_people_result(result):
    """Return a consistent (data, info) tuple across People MCP response variants."""
    if "error" in result:
        return None, None

    def rows_from(node):
        if isinstance(node, list):
            return node
        if isinstance(node, dict):
            for key in ("data", "leaveTypes", "response", "result"):
                if key in node:
                    inner = rows_from(node[key])
                    if inner is not None:
                        return inner
        return None

    payload = result.get("data", result)
    data = rows_from(payload)
    if data is None and isinstance(payload, dict) and "message" in payload:
        return [], {}
    if data is None:
        return [], result.get("info", {})
    return data, result.get("info", {})


def query_leave_types_page(start_index=1, limit=30, timeout=30):
    body = {"startIndex": start_index, "limit": limit}
    return _mcporter_call(LIST_TOOL, {"body": body}, timeout=timeout)


def query_all_leave_types(per_page=30, max_records=None, timeout=30):
    all_data = []
    start_index = 1
    seen = set()

    while True:
        request_limit = per_page
        if max_records is not None:
            remaining = max_records - len(all_data)
            if remaining <= 0:
                break
            request_limit = min(request_limit, remaining)

        result = query_leave_types_page(start_index, request_limit, timeout)
        if "error" in result:
            return result

        data, info = normalize_people_result(result)
        if data is None:
            return {"error": "Zoho People response could not be normalized"}

        fresh = [row for row in data if id(row) not in seen and not seen.add(id(row))]
        all_data.extend(fresh)
        if max_records is not None and len(all_data) >= max_records:
            break

        page_size = len(data)
        if not page_size or page_size < request_limit:
            break
        start_index += page_size

    if max_records is not None:
        all_data = all_data[:max_records]
    return {"data": all_data, "info": {"count": len(all_data), "more_records": False}}


def pick_field(record, wanted):
    lower = {str(key).lower(): key for key in record}
    for candidate in wanted:
        if candidate in lower:
            return record[lower[candidate]]
    return ""


def resolve_leave_type_id(data, needle):
    needle_lower = str(needle).strip().lower()
    for row in data:
        row_id = pick_field(row, ["id", "leavetypeid"])
        name = pick_field(row, ["name", "leavetypename"])
        if str(row_id) == str(needle) or str(name).strip().lower() == needle_lower:
            return row_id, name
    return None, None


def fetch_leave_type_details(leave_type_id, timeout=30):
    return _mcporter_call(DETAILS_TOOL, {"body": {"leaveTypeId": str(leave_type_id)}}, timeout=timeout)


def print_table(data):
    columns = [
        ("id", "ID", ["id", "leavetypeid"]),
        ("name", "Name", ["name", "leavetypename"]),
        ("unit", "Unit", ["unit"]),
        ("type", "Paid/Unpaid", ["type", "leavetype"]),
        ("code", "Code", ["code"]),
    ]
    rows = []
    for row in data:
        rows.append([str(pick_field(row, wanted) or "-") for _, _, wanted in columns])

    widths = [max(len(label), *(len(row[i]) for row in rows)) if rows else len(label) for _, label, _ in columns]
    print(" | ".join(label.ljust(widths[i]) for i, (_, label, _) in enumerate(columns)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.ljust(widths[i])[: widths[i]] for i, value in enumerate(row)))
    print(f"\n{len(data)} leave type(s)")


def main(argv=None):
    args = build_parser().parse_args(argv)
    ENDPOINT.configure(args)

    result = query_all_leave_types(per_page=args.page_size, max_records=args.limit, timeout=args.timeout)
    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    data, _info = normalize_people_result(result)

    if args.details:
        leave_type_id, name = resolve_leave_type_id(data, args.details)
        if leave_type_id in (None, ""):
            print(f"Error: leave type '{args.details}' not found.", file=sys.stderr)
            return 1
        details = fetch_leave_type_details(leave_type_id, args.timeout)
        if "error" in details:
            print(f"Error: {details['error']}", file=sys.stderr)
            return 1
        print(json.dumps(details, indent=2, ensure_ascii=False))
        return 0

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print_table(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
