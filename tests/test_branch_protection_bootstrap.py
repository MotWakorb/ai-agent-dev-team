#!/usr/bin/env python3
"""Network-free tests for scripts/apply-branch-protection.sh."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply-branch-protection.sh"

FAKE_GH = """#!/usr/bin/env python3
import json
import os
import sys

args = sys.argv[1:]
joined = " ".join(args)
if "--method" in args or "-X" in args:
    body = sys.stdin.read() if "--input" in args else ""
    with open(os.environ["GH_CAPTURE"], "a", encoding="utf-8") as capture:
        capture.write(json.dumps({"args": args, "body": body}) + "\\n")
    print("{}")
elif joined.startswith("api repos/") and joined.endswith("/rulesets"):
    print(os.environ.get("RULESETS", "[]"))
else:
    print("unexpected gh invocation: " + joined, file=sys.stderr)
    raise SystemExit(2)
"""

DEFAULT_CHECKS = [
    "ai-team/code-review",
    "ai-team/data-integrity-classification",
    "ai-team/dba-review",
]


class BranchProtectionBootstrapTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.temp = Path(self.tempdir.name)
        self.capture = self.temp / "calls.jsonl"
        fake_gh = self.temp / "gh"
        fake_gh.write_text(FAKE_GH, encoding="utf-8")
        fake_gh.chmod(0o755)

    def tearDown(self):
        self.tempdir.cleanup()

    def run_script(self, *args, rulesets="[]"):
        env = os.environ.copy()
        env.update({
            "PATH": f"{self.temp}{os.pathsep}{env['PATH']}",
            "GH_CAPTURE": str(self.capture),
            "RULESETS": rulesets,
        })
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            env=env, capture_output=True, text=True)

    def calls(self):
        if not self.capture.exists():
            return []
        return [json.loads(line)
                for line in self.capture.read_text().splitlines()]

    def test_creates_ruleset_when_absent(self):
        result = self.run_script("acme/widgets")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls()
        self.assertEqual(len(calls), 1)
        self.assertIn("POST", calls[0]["args"])
        self.assertIn("repos/acme/widgets/rulesets", " ".join(calls[0]["args"]))
        body = json.loads(calls[0]["body"])
        self.assertEqual(body["name"], "ai-team-review-gate")
        self.assertEqual(body["enforcement"], "active")
        self.assertEqual(
            body["conditions"]["ref_name"]["include"], ["~DEFAULT_BRANCH"])
        rules = {rule["type"]: rule for rule in body["rules"]}
        self.assertIn("pull_request", rules)
        checks = rules["required_status_checks"]["parameters"][
            "required_status_checks"]
        self.assertEqual([c["context"] for c in checks], DEFAULT_CHECKS)
        self.assertTrue(all(c["integration_id"] == 15368 for c in checks))

    def test_updates_existing_ruleset_in_place(self):
        rulesets = json.dumps(
            [{"id": 7, "name": "ai-team-review-gate"},
             {"id": 8, "name": "unrelated"}])
        result = self.run_script("acme/widgets", rulesets=rulesets)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls()
        self.assertEqual(len(calls), 1)
        self.assertIn("PUT", calls[0]["args"])
        self.assertIn(
            "repos/acme/widgets/rulesets/7", " ".join(calls[0]["args"]))

    def test_custom_check_names_override_defaults(self):
        result = self.run_script("acme/widgets", "ai-team/code-review")
        self.assertEqual(result.returncode, 0, result.stderr)
        body = json.loads(self.calls()[0]["body"])
        rules = {rule["type"]: rule for rule in body["rules"]}
        checks = rules["required_status_checks"]["parameters"][
            "required_status_checks"]
        self.assertEqual([c["context"] for c in checks],
                         ["ai-team/code-review"])

    def test_missing_repo_argument_fails(self):
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
