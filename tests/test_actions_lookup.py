"""Tests for actions catalog, profiles, and lookup CLI."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPOSITORY / "references" / "actions.jsonl"
PROFILES_PATH = REPOSITORY / "references" / "profiles.json"
LOOKUP_SCRIPT = REPOSITORY / "scripts" / "lookup_actions.py"
IMPORT_SCRIPT = REPOSITORY / "scripts" / "import_actions.py"

sys.path.insert(0, str(REPOSITORY / "scripts"))
import lookup_actions  # noqa: E402
import import_actions  # noqa: E402


class ActionsCatalogAndLookupTests(unittest.TestCase):
    def test_catalog_file_is_valid_jsonl(self):
        self.assertTrue(CATALOG_PATH.exists(), f"missing {CATALOG_PATH}")
        lines = [
            line.strip()
            for line in CATALOG_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertGreaterEqual(len(lines), 369)
        keys = set()
        for idx, line in enumerate(lines, start=1):
            data = json.loads(line)
            self.assertIn("key", data)
            self.assertIn("name", data)
            self.assertIn("summary", data)
            self.assertIn("description", data)
            self.assertNotIn(data["key"], keys, f"duplicate key {data['key']} at line {idx}")
            keys.add(data["key"])

    def test_profiles_file_is_valid_and_consistent(self):
        self.assertTrue(PROFILES_PATH.exists(), f"missing {PROFILES_PATH}")
        data = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
        self.assertEqual(data.get("version"), 1)
        self.assertEqual(data.get("service"), "people")
        self.assertIn("profiles", data)
        self.assertIn("tasks", data)

        res = subprocess.run(
            [sys.executable, str(LOOKUP_SCRIPT), "--validate"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"validation failed:\n{res.stdout}\n{res.stderr}")
        self.assertIn("Validation OK", res.stdout)

    def test_lookup_cli_profiles_listing(self):
        res = subprocess.run(
            [sys.executable, str(LOOKUP_SCRIPT), "--profiles"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("employee-self-service", res.stdout)
        self.assertIn("hr-admin", res.stdout)

    def test_lookup_cli_task_inspection(self):
        res = subprocess.run(
            [sys.executable, str(LOOKUP_SCRIPT), "--task", "leave-booking"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("applyLeave", res.stdout)
        self.assertIn("leavePreview", res.stdout)

    def test_lookup_cli_search_names_only(self):
        res = subprocess.run(
            [sys.executable, str(LOOKUP_SCRIPT), "--search", "holiday", "--names-only"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("listholidays", res.stdout)

    def test_lookup_cli_action_inspection(self):
        res = subprocess.run(
            [sys.executable, str(LOOKUP_SCRIPT), "--action", "applyLeave", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data.get("key"), "applyLeave")
        self.assertIn("Applies for a leave on behalf of the user.", data.get("description", ""))

    def test_profile_inheritance_and_denials(self):
        data = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
        profiles = data["profiles"]
        hr_actions = lookup_actions.resolve_profile_actions("hr-admin", profiles)
        self.assertIn("addRecord", hr_actions)
        self.assertIn("applyLeave", hr_actions)
        self.assertIn("approvalReject", hr_actions)
        self.assertNotIn("deleteCandidate", hr_actions)
        self.assertNotIn("fetchEmployeeSalaries", hr_actions)

    def test_importer_parses_dump_and_handles_variants(self):
        sample_dump = (
            "Authorize On Demand\n"
            "Group view\n"
            "All Tools\n"
            "Tools Name\n"
            "applyLeave Applies for a leave on behalf of the user.\n"
            "lms courses Search for LMS courses for a user.\n"
            "lms enroll course Enroll users into an LMS course.\n"
        )
        parsed = import_actions.parse_dump(sample_dump)
        keys = {entry["key"]: entry for entry in parsed}
        self.assertIn("applyLeave", keys)
        self.assertEqual(keys["applyLeave"]["name"], "applyLeave")
        self.assertIn("lms.courses", keys)
        self.assertEqual(keys["lms.courses"]["name"], "lms courses")
        self.assertIn("lms.enroll_course", keys)
        self.assertEqual(keys["lms.enroll_course"]["name"], "lms enroll course")

    def test_importer_merges_additions_and_marks_removals(self):
        known = {
            "oldAction": {
                "key": "oldAction",
                "name": "oldAction",
                "summary": "Old",
                "description": "Old action",
                "added": "2026-08-01",
            }
        }
        current_entries = [
            {
                "key": "newAction",
                "name": "newAction",
                "summary": "New",
                "description": "New action",
            }
        ]
        merged = import_actions.merge(current_entries, known, today="2026-09-17")
        by_key = {item["key"]: item for item in merged}
        self.assertEqual(by_key["newAction"]["added"], "2026-09-17")
        self.assertNotIn("removed", by_key["newAction"])
        self.assertEqual(by_key["oldAction"]["added"], "2026-08-01")
        self.assertEqual(by_key["oldAction"]["removed"], "2026-09-17")


if __name__ == "__main__":
    unittest.main()
