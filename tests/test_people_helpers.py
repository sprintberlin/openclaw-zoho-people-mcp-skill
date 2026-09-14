"""Credential-free tests for the People helper CLIs."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


REPOSITORY = Path(__file__).resolve().parents[1]


def load_script(name):
    path = REPOSITORY / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"{path.stem}_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PeopleHelperCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.employees = load_script("list_employees.py")
        cls.inspect = load_script("inspect_employee.py")
        cls.leave_types = load_script("list_leave_types.py")
        cls.balances = load_script("leave_balances.py")
        cls.attendance = load_script("attendance_summary.py")

    def run_script(self, script, *arguments):
        env = os.environ.copy()
        env.pop("ZOHO_PEOPLE_MCP_URL", None)
        return subprocess.run(
            [sys.executable, str(REPOSITORY / "scripts" / script), *arguments],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )

    def test_help_needs_no_credentials(self):
        scripts = (
            "list_employees.py",
            "inspect_employee.py",
            "list_leave_types.py",
            "leave_balances.py",
            "attendance_summary.py",
        )
        for script in scripts:
            with self.subTest(script=script):
                result = self.run_script(script, "--help")
                self.assertEqual(result.returncode, 0)
                self.assertIn("usage:", result.stdout)
                self.assertEqual(result.stderr, "")

    def test_unknown_and_missing_options_use_exit_code_2(self):
        cases = (
            ("list_employees.py", ("--unknown",)),
            ("list_employees.py", ("--search",)),
            ("inspect_employee.py", ()),
            ("list_leave_types.py", ("--unknown",)),
            ("leave_balances.py", ()),
            ("leave_balances.py", ("--year", "9")),
            ("attendance_summary.py", ("--unknown",)),
        )
        for script, arguments in cases:
            with self.subTest(script=script, arguments=arguments):
                result = self.run_script(script, *arguments)
                self.assertEqual(result.returncode, 2)
                self.assertIn("usage:", result.stderr)

    def test_employee_limit_bounds_first_request_and_result(self):
        rows = [{"erecno": str(index), "name": "Example"} for index in range(1, 5)]
        calls = []

        def fake_page(search=None, s_index=1, limit=50, timeout=30):
            calls.append({"search": search, "s_index": s_index, "limit": limit, "timeout": timeout})
            return {"data": rows, "info": {"more_records": True}}

        with patch.object(self.employees, "query_employees_page", side_effect=fake_page):
            result = self.employees.query_all_employees(
                search="Miller", per_page=50, max_records=3, timeout=17
            )

        self.assertEqual(
            calls,
            [{"search": "Miller", "s_index": 1, "limit": 3, "timeout": 17}],
        )
        self.assertEqual(len(result["data"]), 3)

    def test_leave_type_limit_bounds_first_request_and_result(self):
        rows = [{"id": str(index), "name": "Vacation"} for index in range(1, 5)]
        calls = []

        def fake_page(start_index=1, limit=30, timeout=30):
            calls.append({"start_index": start_index, "limit": limit, "timeout": timeout})
            return {"data": rows, "info": {}}

        with patch.object(self.leave_types, "query_leave_types_page", side_effect=fake_page):
            result = self.leave_types.query_all_leave_types(
                per_page=30, max_records=2, timeout=19
            )

        self.assertEqual(calls, [{"start_index": 1, "limit": 2, "timeout": 19}])
        self.assertEqual(len(result["data"]), 2)

    def test_seconds_to_hhmm(self):
        self.assertEqual(self.attendance.seconds_to_hhmm(3660), "01:01")
        self.assertEqual(self.attendance.seconds_to_hhmm("08:30"), "08:30")
        self.assertEqual(self.attendance.seconds_to_hhmm(None), "-")


if __name__ == "__main__":
    unittest.main()
