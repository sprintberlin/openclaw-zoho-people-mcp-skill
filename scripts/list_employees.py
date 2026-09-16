#!/usr/bin/env python3
"""List or search Zoho People employees through mcporter."""

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

TOOL = "ZohoPeople_getEmployeeBasicDetails"

DEFAULT_COLUMNS = ["name", "email", "employeeid", "dept", "designation", "erecno"]

COLUMN_LABELS = {
    "name": "Name",
    "email": "Email",
    "employeeid": "Employee ID",
    "dept": "Department",
    "designation": "Designation",
    "erecno": "Erecno",
    "contact": "Contact",
    "manager": "Manager",
}


def positive_int(value):
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def build_parser():
    parser = argparse.ArgumentParser(description="List or search Zoho People employees.")
    parser.add_argument("--search", metavar="TEXT", help="search term (name, email, or employee ID)")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    parser.add_argument("--full", action="store_true", help="with --json, print complete records")
    parser.add_argument("--limit", type=positive_int, help="return at most this many employees")
    parser.add_argument("--page-size", type=positive_int, default=50, help="page size (default: 50)")
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
            for key in ("data", "employees", "response", "result"):
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
    info = result.get("info", {})
    if isinstance(payload, dict) and isinstance(info, dict):
        for key in ("totalRecords", "count"):
            if key in payload and key not in info:
                info[key] = payload[key]
    return data, info


def query_employees_page(search=None, s_index=1, limit=50, timeout=30):
    body = {"sIndex": s_index, "limit": limit}
    if search:
        body["searchText"] = search
    return _mcporter_call(TOOL, {"body": body}, timeout=timeout)


def query_all_employees(search=None, per_page=50, max_records=None, timeout=30):
    all_data = []
    s_index = 1
    seen = set()

    while True:
        request_limit = per_page
        if max_records is not None:
            remaining = max_records - len(all_data)
            if remaining <= 0:
                break
            request_limit = min(request_limit, remaining)

        result = query_employees_page(search, s_index, request_limit, timeout)
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
        if max_records is not None and info.get("totalRecords") and len(all_data) >= int(info["totalRecords"]):
            break
        s_index += page_size

    if max_records is not None:
        all_data = all_data[:max_records]
    return {"data": all_data, "info": {"count": len(all_data), "more_records": False}}


def pick_field(record, wanted):
    lower = {str(key).lower(): key for key in record}
    for candidate in wanted:
        if candidate in lower:
            return record[lower[candidate]]
    return ""


def extract_table_field(record, column):
    wanted = {
        "name": ["name", "empname", "fullname", "nickname", "firstname"],
        "email": ["email", "emailid", "mailid", "mail"],
        "employeeid": ["employeeid", "empid"],
        "dept": ["dept", "department", "deptname"],
        "designation": ["designation", "designationname"],
        "erecno": ["erecno", "erecnoofemployee"],
        "contact": ["contact", "phone", "mobile"],
        "manager": ["manager", "reportingto"],
    }[column]
    val = pick_field(record, wanted)
    if not val:
        return "-"
    if isinstance(val, dict):
        return str(val.get("name") or val)
    return str(val)


def print_table(data, columns):
    if not data:
        print("No employees found.")
        return

    col_widths = {}
    for column in columns:
        label = COLUMN_LABELS.get(column, column)
        max_val_len = max((len(extract_table_field(row, column)) for row in data), default=0)
        col_widths[column] = max(len(label), min(max_val_len, 40))

    print(" | ".join(COLUMN_LABELS.get(column, column).ljust(col_widths[column]) for column in columns))
    print("-+-".join("-" * col_widths[column] for column in columns))

    for row in data:
        parts = []
        for column in columns:
            val = extract_table_field(row, column)
            if len(val) > 40:
                val = val[:37] + "..."
            parts.append(val.ljust(col_widths[column]))
        print(" | ".join(parts))

    print(f"\n{len(data)} employee(s)")


def main(argv=None):
    args = build_parser().parse_args(argv)
    ENDPOINT.configure(args)

    result = query_all_employees(
        args.search,
        per_page=args.page_size,
        max_records=args.limit,
        timeout=args.timeout,
    )
    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    data, info = normalize_people_result(result)

    if args.json:
        if args.full:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            simplified = [{column: pick_field(row, [column]) for column in DEFAULT_COLUMNS} for row in data]
            print(json.dumps(simplified, indent=2, ensure_ascii=False))
    else:
        print_table(data, DEFAULT_COLUMNS)

    if info.get("more_records"):
        print(f"\nMore records available (showing {len(data)}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
