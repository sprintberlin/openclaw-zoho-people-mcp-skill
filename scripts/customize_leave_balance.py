#!/usr/bin/env python3
"""Customize an employee's leave balance directly via Zoho People REST API.

Use when the MCP server cannot perform balance adjustments (see references/LIMITATIONS.md).
Requires environment variables:
    ZOHO_PEOPLE_CLIENT_ID
    ZOHO_PEOPLE_CLIENT_SECRET
    ZOHO_PEOPLE_REFRESH_TOKEN
    ZOHO_PEOPLE_DC (optional, default: eu)
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import people_api

ZOHO_ID = re.compile(r"^[0-9]+$")
PEOPLE_DATE = re.compile(r"^[0-9]{2}-[A-Za-z]{3}-[0-9]{4}$")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Set an employee's leave balance directly via Zoho People REST API."
    )
    parser.add_argument("--erecno", required=True, help="employee erecno")
    parser.add_argument("--leave-type-id", required=True, help="leave type ID")
    parser.add_argument(
        "--balance",
        required=True,
        type=float,
        help="new total entitlement/balance, not remaining leave (e.g. 9.5)",
    )
    parser.add_argument("--date", required=True, help="effective date in dd-MMM-yyyy (e.g. 07-Sep-2026)")
    parser.add_argument("--reason", required=True, help="reason for the adjustment")
    parser.add_argument("--dc", choices=sorted(people_api.PEOPLE_DC), help="Zoho DC (eu, com, in, etc.)")
    parser.add_argument("--apply", action="store_true", help="perform the update; otherwise print a dry run")
    parser.add_argument("--json", action="store_true", help="output raw JSON response")
    parser.add_argument("--timeout", type=int, default=30, help="request timeout in seconds (default: 30)")
    return parser


def build_request(erecno, leave_type_id, balance, date_str, reason):
    erecno = str(erecno).strip()
    leave_type_id = str(leave_type_id).strip()
    reason = str(reason).strip()
    if not ZOHO_ID.fullmatch(erecno):
        raise ValueError("erecno must contain digits only")
    if not ZOHO_ID.fullmatch(leave_type_id):
        raise ValueError("leave type ID must contain digits only")
    if not PEOPLE_DATE.fullmatch(date_str):
        raise ValueError("date must use dd-MMM-yyyy, e.g. 07-Sep-2026")
    if not math.isfinite(float(balance)):
        raise ValueError("balance must be finite")
    if not reason:
        raise ValueError("reason must not be empty")
    balance_data = {
        leave_type_id: {
            "date": date_str,
            "newBalance": float(balance),
            "reason": reason,
        }
    }
    params = {
        "balanceData": json.dumps(balance_data),
        "dateFormat": "dd-MMM-yyyy",
    }
    path = f"/people/api/v2/leavetracker/settings/customize-balance/{erecno}"
    return path, params


def customize_balance(
    erecno,
    leave_type_id,
    balance,
    date_str,
    reason,
    dc=None,
    timeout=30,
    credentials=None,
):
    path, params = build_request(erecno, leave_type_id, balance, date_str, reason)
    creds = credentials or people_api.load_credentials(dc=dc)
    return people_api.call(
        path,
        params=params,
        method="POST",
        credentials=creds,
        timeout=timeout,
        params_in_query=True,
    )


def fetch_leave_balance(erecno, leave_type_id, credentials, timeout=30):
    result = people_api.call(
        "/people/api/v2/leavetracker/reports/user",
        params={"employee": str(erecno)},
        method="GET",
        credentials=credentials,
        timeout=timeout,
    )
    for record in result.get("leavetypes", []):
        if str(record.get("leavetypeID")) == str(leave_type_id):
            return record
    raise people_api.PeopleApiError("leave type missing from verification report")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        path, params = build_request(
            args.erecno, args.leave_type_id, args.balance, args.date, args.reason
        )
        if not args.apply:
            preview = {"dry_run": True, "method": "POST", "path": path, "params": params}
            print(json.dumps(preview, indent=2, ensure_ascii=False))
            return 0
        credentials = people_api.load_credentials(dc=args.dc)
        res = customize_balance(
            erecno=args.erecno,
            leave_type_id=args.leave_type_id,
            balance=args.balance,
            date_str=args.date,
            reason=args.reason,
            dc=args.dc,
            timeout=args.timeout,
            credentials=credentials,
        )
        verified = fetch_leave_balance(
            args.erecno, args.leave_type_id, credentials, timeout=args.timeout
        )
        available = float(verified.get("available", 0))
        taken = float(verified.get("taken", 0))
        total = available + taken
        if not math.isclose(total, args.balance, abs_tol=0.0001):
            raise people_api.PeopleApiError(
                f"verification failed: available {available:g} + taken {taken:g} = {total:g}, expected {args.balance:g}"
            )
    except (ValueError, people_api.PeopleApiError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                {"update": res, "verification": verified},
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(
            f"Status: success — total {total:g}, available {available:g}, taken {taken:g}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
