"""Credential-free tests for the direct REST fallback (people_api + customize_leave_balance)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPTS = REPOSITORY / "scripts"


def load_script(name):
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(f"{path.stem}_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PeopleApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = load_script("people_api.py")

    def test_resolve_dc_defaults_to_eu(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.api.resolve_dc(None), "eu")
            self.assertEqual(self.api.resolve_dc(), "eu")

    def test_resolve_dc_rejects_unknown_value(self):
        with patch.dict(os.environ, {"ZOHO_PEOPLE_DC": "mars"}, clear=True):
            with self.assertRaises(self.api.PeopleApiError):
                self.api.resolve_dc()

    def test_load_credentials_reports_missing_variables(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(self.api.PeopleApiError) as ctx:
                self.api.load_credentials()
        self.assertIn("ZOHO_PEOPLE_CLIENT_ID", str(ctx.exception))

    def test_load_credentials_reads_environment(self):
        env = {
            "ZOHO_PEOPLE_CLIENT_ID": "id",
            "ZOHO_PEOPLE_CLIENT_SECRET": "secret",
            "ZOHO_PEOPLE_REFRESH_TOKEN": "token",
            "ZOHO_PEOPLE_DC": "com",
        }
        with patch.dict(os.environ, env, clear=True):
            creds = self.api.load_credentials()
        self.assertEqual(creds["dc"], "com")
        self.assertEqual(creds["client_id"], "id")

    def test_token_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "tokens.json"
            with patch.dict(os.environ, {"ZOHO_PEOPLE_TOKEN_CACHE": str(cache)}, clear=True):
                self.api._write_cached_token("id", "refresh", "eu", "access", 3600)
                self.assertEqual(self.api._read_cached_token("id", "refresh", "eu"), "access")
                self.assertIsNone(self.api._read_cached_token("id", "other", "eu"))
                entry = json.loads(cache.read_text())
                entry[list(entry)[0]]["expires_at"] = time.time() - 1
                cache.write_text(json.dumps(entry))
                self.assertIsNone(self.api._read_cached_token("id", "refresh", "eu"))


class CustomizeBalanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = load_script("customize_leave_balance.py")

    def test_help_needs_no_credentials(self):
        env = os.environ.copy()
        for name in (
            "ZOHO_PEOPLE_CLIENT_ID",
            "ZOHO_PEOPLE_CLIENT_SECRET",
            "ZOHO_PEOPLE_REFRESH_TOKEN",
        ):
            env.pop(name, None)
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "customize_leave_balance.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage:", result.stdout)

    def test_missing_options_use_exit_code_2(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "customize_leave_balance.py")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)

    def test_customize_balance_builds_expected_request(self):
        recorded = {}

        def fake_call(path, params=None, method="POST", credentials=None, timeout=30):
            recorded["path"] = path
            recorded["params"] = params
            recorded["method"] = method
            return {"status": "success"}

        creds = {
            "client_id": "id",
            "client_secret": "secret",
            "refresh_token": "token",
            "dc": "eu",
        }
        with patch.object(self.tool.people_api, "call", side_effect=fake_call), patch.object(
            self.tool.people_api, "load_credentials", return_value=creds
        ):
            result = self.tool.customize_balance(
                erecno="123",
                leave_type_id="456",
                balance=9.5,
                date_str="07-Sep-2026",
                reason="Prorated entitlement",
            )

        self.assertEqual(result, {"status": "success"})
        self.assertEqual(recorded["path"], "/api/v2/leavetracker/settings/customize-balance/123")
        self.assertEqual(recorded["method"], "POST")
        balance_data = json.loads(recorded["params"]["balanceData"])
        self.assertEqual(
            balance_data["456"],
            {"date": "07-Sep-2026", "newBalance": 9.5, "reason": "Prorated entitlement"},
        )
        self.assertEqual(recorded["params"]["dataFormat"], "dd-MMM-yyyy")

    def test_build_request_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            self.tool.build_request("../123", "456", 9.5, "07-Sep-2026", "Reason")
        with self.assertRaises(ValueError):
            self.tool.build_request("123", "abc", 9.5, "07-Sep-2026", "Reason")
        with self.assertRaises(ValueError):
            self.tool.build_request("123", "456", 9.5, "2026-09-07", "Reason")
        with self.assertRaises(ValueError):
            self.tool.build_request("123", "456", 9.5, "07-Sep-2026", "  ")

    def test_cli_dry_run_without_apply_and_credentials(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "customize_leave_balance.py"),
                "--erecno", "123",
                "--leave-type-id", "456",
                "--balance", "9.5",
                "--date", "07-Sep-2026",
                "--reason", "Prorated entitlement",
            ],
            capture_output=True,
            text=True,
            check=False,
            env={"PATH": "/usr/bin:/bin"},
        )
        self.assertEqual(result.returncode, 0)
        preview = json.loads(result.stdout)
        self.assertTrue(preview["dry_run"])
        self.assertEqual(preview["path"], "/api/v2/leavetracker/settings/customize-balance/123")


if __name__ == "__main__":
    unittest.main()
