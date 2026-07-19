#!/usr/bin/env python3
"""Network-free tests for the trusted review-gate workflow's inline Bash."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ai-team-review-gate.yml"
HEAD = "a" * 40


def extract_script():
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    start = lines.index("        run: |") + 1
    script = []
    for line in lines[start:]:
        if line.startswith("          "):
            script.append(line[10:])
        elif not line:
            script.append("")
        else:
            break
    if not script:
        raise AssertionError("workflow inline Bash was not found")
    return "\n".join(script) + "\n"


FAKE_GH = """#!/usr/bin/env python3
import json
import os
import sys

args = sys.argv[1:]
joined = " ".join(args)
failure = os.environ.get("GH_FAIL_ON", "")
if failure and failure in joined:
    print("simulated provider failure", file=sys.stderr)
    raise SystemExit(1)
if "--method" in args and "POST" in args:
    with open(os.environ["GH_CAPTURE"], "a", encoding="utf-8") as capture:
        capture.write(json.dumps(args) + "\\n")
    print("{}")
elif "/pulls/" in joined:
    print(os.environ["PR_FIELDS"])
elif "/check-runs?" in joined:
    print(os.environ.get("CHECK_HISTORY", ""))
else:
    print("unexpected gh invocation", file=sys.stderr)
    raise SystemExit(2)
"""


class ReviewGateWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.temp = Path(self.tempdir.name)
        self.capture = self.temp / "posts.jsonl"
        fake_gh = self.temp / "gh"
        fake_gh.write_text(FAKE_GH, encoding="utf-8")
        fake_gh.chmod(0o755)
        self.script = extract_script()

    def tearDown(self):
        self.tempdir.cleanup()

    def environment(self, **overrides):
        env = os.environ.copy()
        env.update({
            "PATH": f"{self.temp}{os.pathsep}{env['PATH']}",
            "GH_TOKEN": "test-token",
            "GH_CAPTURE": str(self.capture),
            "EXPECTED_ACTOR": "MotWakorb",
            "EXPECTED_ACTOR_ID": "31100779",
            "EXPECTED_REPOSITORY": "MotWakorb/ai-agent-dev-team",
            "INPUT_PR_NUMBER": "1",
            "INPUT_HEAD_SHA": HEAD,
            "INPUT_CLASSIFICATION": "other",
            "INPUT_CODE_REVIEW_APPROVED": "true",
            "INPUT_DBA_REVIEW_APPROVED": "false",
            "DISPATCH_ACTOR": "MotWakorb",
            "DISPATCH_ACTOR_ID": "31100779",
            "DISPATCH_REF": "refs/heads/main",
            "DISPATCH_REPOSITORY": "MotWakorb/ai-agent-dev-team",
            "PR_FIELDS": f"open\tMotWakorb/ai-agent-dev-team\t{HEAD}",
            "CHECK_HISTORY": "",
        })
        env.update(overrides)
        return env

    def run_gate(self, **overrides):
        return subprocess.run(
            ["bash", "-c", self.script],
            env=self.environment(**overrides),
            capture_output=True,
            text=True,
        )

    def posts(self):
        if not self.capture.exists():
            return []
        return [
            json.loads(line)
            for line in self.capture.read_text(encoding="utf-8").splitlines()
        ]

    @staticmethod
    def fields(post):
        values = {}
        for index, argument in enumerate(post):
            if argument == "-f":
                key, value = post[index + 1].split("=", 1)
                values[key] = value
        return values

    def assert_rejected(self, **overrides):
        result = self.run_gate(**overrides)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.posts(), [])

    def test_concurrency_serializes_by_pr_not_raw_head_input(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        group_line = next(
            line.strip() for line in workflow.splitlines()
            if line.strip().startswith("group:")
        )
        self.assertIn("${{ inputs.pr_number }}", group_line)
        self.assertNotIn("head_sha", group_line)

    def test_history_query_uses_paginated_per_page_jq(self):
        script = extract_script()
        history_command = script.split('classification_history="$(', 1)[1].split(
            ')"', 1)[0]
        self.assertIn("--paginate", history_command)
        self.assertIn("--jq", history_command)
        self.assertNotIn("--slurp", history_command)
        self.assertIn("filter=all&per_page=100", history_command)

    def test_invalid_dispatch_and_input_states_reject(self):
        cases = (
            {"DISPATCH_ACTOR": "attacker"},
            {"DISPATCH_ACTOR_ID": "999"},
            {"DISPATCH_REPOSITORY": "MotWakorb/other"},
            {"DISPATCH_REF": "refs/heads/feature"},
            {"INPUT_PR_NUMBER": "1;echo"},
            {"INPUT_HEAD_SHA": "abc"},
            {"INPUT_CLASSIFICATION": "unknown"},
            {"INPUT_CODE_REVIEW_APPROVED": "false"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                self.assert_rejected(**overrides)

    def test_invalid_pull_request_states_reject(self):
        cases = (
            {"PR_FIELDS": f"closed\tMotWakorb/ai-agent-dev-team\t{HEAD}"},
            {"PR_FIELDS": f"open\tMotWakorb/other\t{HEAD}"},
            {"PR_FIELDS": f"open\tMotWakorb/ai-agent-dev-team\t{'b' * 40}"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                self.assert_rejected(**overrides)

    def test_other_publishes_exact_three_checks(self):
        result = self.run_gate()
        self.assertEqual(result.returncode, 0, result.stderr)
        posts = [self.fields(post) for post in self.posts()]
        self.assertEqual(
            [post["name"] for post in posts],
            [
                "ai-team/code-review",
                "ai-team/data-integrity-classification",
                "ai-team/dba-review",
            ],
        )
        self.assertTrue(all(post["head_sha"] == HEAD for post in posts))
        self.assertTrue(all(post["status"] == "completed" for post in posts))
        self.assertTrue(all(post["conclusion"] == "success" for post in posts))
        self.assertEqual(
            posts[1]["output[title]"], "classification:other")
        self.assertEqual(posts[2]["output[title]"], "dba-review:not-required")

    def test_data_integrity_requires_dba_then_succeeds(self):
        self.assert_rejected(
            INPUT_CLASSIFICATION="data-integrity",
            INPUT_DBA_REVIEW_APPROVED="false",
        )
        result = self.run_gate(
            INPUT_CLASSIFICATION="data-integrity",
            INPUT_DBA_REVIEW_APPROVED="true",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        posts = [self.fields(post) for post in self.posts()]
        self.assertEqual(
            posts[1]["output[title]"], "classification:data-integrity")
        self.assertEqual(posts[2]["output[title]"], "dba-review:approved")

    def test_same_classification_replay_is_allowed(self):
        history = (
            "11\tcompleted\tsuccess\tclassification:other\n"
            "12\tcompleted\tsuccess\tclassification:other"
        )
        result = self.run_gate(CHECK_HISTORY=history)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.posts()), 3)

    def test_data_integrity_cannot_be_downgraded(self):
        history = "12\tcompleted\tsuccess\tclassification:data-integrity"
        self.assert_rejected(CHECK_HISTORY=history)

    def test_malformed_or_conflicting_history_fails_closed(self):
        cases = (
            "bad\tcompleted\tsuccess\tclassification:other",
            "13\tin_progress\t\tclassification:other",
            "14\tcompleted\tfailure\tclassification:other",
            "15\tcompleted\tsuccess\tmalformed",
            (
                "16\tcompleted\tsuccess\tclassification:other\n"
                "17\tcompleted\tsuccess\tclassification:data-integrity"
            ),
        )
        for history in cases:
            with self.subTest(history=history):
                self.assert_rejected(CHECK_HISTORY=history)

    def test_provider_failures_stop_without_posting(self):
        for failure in ("/pulls/", "/check-runs?", "POST"):
            with self.subTest(failure=failure):
                self.assert_rejected(GH_FAIL_ON=failure)


if __name__ == "__main__":
    unittest.main(verbosity=2)
