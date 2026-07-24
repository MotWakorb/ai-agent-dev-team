#!/usr/bin/env python3
"""Network-free tests for hooks/pretooluse.py false-positive fixes.

Complements the hook's own `--check` self-test with named cases for the
three field-documented false positives (retros 2026-07-20-08, 2026-07-20-22,
2026-07-23-15) and their adversarial counterparts.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "pretooluse.py"


class HookTest(unittest.TestCase):
    def setUp(self):
        self._dirs = []

    def tearDown(self):
        for path in self._dirs:
            shutil.rmtree(path, ignore_errors=True)

    def mkdir(self, *, git=False, onboarded=False, beads=False, prefix=None):
        path = tempfile.mkdtemp()
        self._dirs.append(path)
        if git or onboarded or beads:
            os.makedirs(os.path.join(path, ".git"))
        if onboarded:
            open(os.path.join(path, "COMPONENTS.md"), "w").close()
        if beads:
            os.makedirs(os.path.join(path, ".beads"))
            if prefix:
                with open(os.path.join(path, ".beads", "config.yaml"), "w") as f:
                    f.write(f"issue-prefix: {prefix}\n")
        return path

    def hook(self, command, cwd, agent_id=None):
        payload = {"tool_name": "Bash", "tool_input": {"command": command},
                   "cwd": cwd}
        if agent_id is not None:
            payload["agent_id"] = agent_id
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        if not proc.stdout.strip():
            return None
        return json.loads(proc.stdout)["hookSpecificOutput"]

    def assert_allowed(self, command, cwd, **kwargs):
        decision = self.hook(command, cwd, **kwargs)
        self.assertIsNone(decision, decision and decision.get(
            "permissionDecisionReason"))

    def assert_denied(self, command, cwd, **kwargs):
        decision = self.hook(command, cwd, **kwargs)
        self.assertIsNotNone(decision, f"expected deny for: {command}")
        self.assertEqual(decision["permissionDecision"], "deny")
        return decision["permissionDecisionReason"]

    # --- Fix 1: scratchpad redirects are not project-tree writes (2026-07-20-08)

    def test_heredoc_redirect_to_quoted_scratchpad_path_is_allowed(self):
        root = self.mkdir(onboarded=True)
        scratch = self.mkdir()
        self.assert_allowed(
            f'cat > "{scratch}/notes.md" <<\'EOF\'\n'
            "body with > inner.md and ; semicolons\n"
            "EOF",
            cwd=root)

    def test_unquoted_scratchpad_redirect_is_allowed(self):
        root = self.mkdir(onboarded=True)
        scratch = self.mkdir()
        self.assert_allowed(f"echo hi > {scratch}/out.txt", cwd=root)

    def test_quoted_project_tree_redirect_is_still_denied(self):
        # Adversarial: quoting the target must not evade the guard.
        root = self.mkdir(onboarded=True)
        self.assert_denied(f'echo hi > "{root}/src/x.txt"', cwd=root)

    def test_symlink_from_scratchpad_into_project_is_denied(self):
        # Adversarial: a scratchpad-looking prefix that resolves into the tree.
        root = self.mkdir(onboarded=True)
        scratch = self.mkdir()
        os.symlink(root, os.path.join(scratch, "link"))
        self.assert_denied(f"echo hi > {scratch}/link/x.txt", cwd=root)

    def test_dotdot_traversal_into_project_is_denied(self):
        # Adversarial: ../ hops from a scratch dir back into the tree.
        root = self.mkdir(onboarded=True)
        scratch = self.mkdir()
        sneaky = f"{scratch}/../{os.path.basename(root)}/src/x.txt"
        self.assert_denied(f"echo hi > {sneaky}", cwd=root)

    def test_fake_heredoc_marker_in_quotes_does_not_hide_redirect(self):
        # Adversarial: a quoted "<<X" must not swallow the real redirect.
        root = self.mkdir(onboarded=True)
        self.assert_denied(
            f'echo "<<X" > {root}/src/x.txt\nX', cwd=root)

    def test_quoted_heredoc_marker_does_not_swallow_next_line_redirect(self):
        # Adversarial (kickback PTU round, reviewer #2): a quoted "<<EOF"
        # with the redirect on the NEXT line and a matching terminator line
        # must still deny — quoted markers are data, not heredoc operators.
        root = self.mkdir(onboarded=True)
        self.assert_denied(
            f'echo "<<EOF"\necho hi > {root}/src/x.txt\nEOF', cwd=root)

    def test_quoted_tee_word_is_data_not_a_write(self):
        # Kickback (reviewer #1): `tee` inside quoted data must not read as
        # a tee command with the next word as its target.
        root = self.mkdir(onboarded=True)
        self.assert_allowed(
            'git commit -m "docs: explain tee usage [no-bead]"', cwd=root)

    def test_quoted_tee_target_in_tree_is_still_denied(self):
        # Adversarial: quoting the tee target must not evade the guard.
        root = self.mkdir(onboarded=True)
        self.assert_denied(f'cat a | tee "{root}/README.md"', cwd=root)

    # --- Fix 2: compound denies name the offending segment (2026-07-20-22)

    def test_compound_deny_names_triggering_segment(self):
        root = self.mkdir(onboarded=True)
        reason = self.assert_denied(
            f"cat > {root}/body.md <<EOF\nPR body\nEOF\n"
            "gh pr create --fill",
            cwd=root)
        self.assertIn("segment", reason)
        self.assertIn(f"cat > {root}/body.md", reason)
        self.assertIn("separate", reason)
        # The innocent half is not blamed.
        self.assertNotIn("gh pr create", reason.split("`")[1])

    def test_compound_deny_with_and_chain(self):
        root = self.mkdir(onboarded=True)
        reason = self.assert_denied(
            f"echo hi > {root}/x.txt && gh pr create --fill", cwd=root)
        self.assertIn(f"echo hi > {root}/x.txt", reason)

    def test_quoted_separator_does_not_split_segments(self):
        # Adversarial: a quoted "&&" is data, not a segment boundary.
        root = self.mkdir(onboarded=True)
        reason = self.assert_denied(
            f'echo "a && b" > {root}/x.txt && gh pr create --fill', cwd=root)
        culprit = reason.split("`")[1]
        self.assertIn(f'> {root}/x.txt', culprit)
        self.assertTrue(culprit.startswith("echo"), culprit)

    def test_single_command_deny_has_no_segment_note(self):
        root = self.mkdir(onboarded=True)
        reason = self.assert_denied(f"echo hi > {root}/x.txt", cwd=root)
        self.assertNotIn("segment", reason)

    def test_separator_adjacent_redirect_blames_its_own_segment(self):
        # Kickback (reviewer #5): the redirect op match starts on the
        # separator char itself; the note must not blame the last segment.
        root = self.mkdir(onboarded=True)
        reason = self.assert_denied(
            "true;>x.txt && gh pr create --fill", cwd=root)
        culprit = reason.split("`")[1]
        self.assertIn(">x.txt", culprit)
        self.assertNotIn("gh pr create", culprit)

    # --- Fix 3: git context follows the command's cwd, not spawn cwd
    #     (2026-07-23-15)

    def test_cd_prefix_commit_is_judged_against_target_repo(self):
        beaded = self.mkdir(onboarded=True, beads=True)
        plain = self.mkdir(git=True)
        self.assert_allowed(
            f'cd {plain} && git commit -m "plain message"', cwd=beaded)

    def test_cd_prefix_into_beads_repo_is_still_enforced(self):
        # Adversarial: cd-ing INTO a beads repo must not evade the gate.
        beaded = self.mkdir(onboarded=True, beads=True)
        plain = self.mkdir(git=True)
        self.assert_denied(
            f'cd {beaded} && git commit -m "no bead here"', cwd=plain)

    def test_cd_prefix_uses_target_repo_bead_prefix(self):
        beaded = self.mkdir(onboarded=True, beads=True, prefix="zork")
        plain = self.mkdir(git=True)
        self.assert_allowed(
            f'cd {beaded} && git commit -m "zork-ab1c2: fix"', cwd=plain)

    def test_quoted_cd_target_is_still_honored(self):
        # Adversarial: quoting the cd path must not evade the gate.
        beaded = self.mkdir(onboarded=True, beads=True)
        plain = self.mkdir(git=True)
        self.assert_denied(
            f'cd "{beaded}" && git commit -m "no bead"', cwd=plain)

    def test_cd_out_of_tree_does_not_disarm_write_guard(self):
        # Kickback (security PTU-1): a leading cd to an out-of-tree dir must
        # not disable Rule A2 for a target inside the onboarded spawn tree.
        root = self.mkdir(onboarded=True)
        scratch = self.mkdir()
        self.assert_denied(
            f"cd {scratch} && echo hi > {root}/src/x.txt", cwd=root)

    def test_cd_nonexistent_dir_does_not_disarm_write_guard(self):
        root = self.mkdir(onboarded=True)
        self.assert_denied(
            f"cd /no/such/dir && echo x > {root}/src/x.py", cwd=root)

    def test_cd_out_of_tree_does_not_disarm_sed_guard(self):
        root = self.mkdir(onboarded=True)
        self.assert_denied(
            f"cd /tmp && sed -i '' s/a/b/ {root}/f.css", cwd=root)

    def test_chained_cd_back_into_tree_is_denied(self):
        # Kickback PTU-5: only the first cd was captured, so a later cd
        # re-entering the tree desynced relative-target resolution. More
        # than one cd bails the re-anchor back to the spawn cwd.
        root = self.mkdir(onboarded=True)
        self.assert_denied(
            f"cd /tmp && cd {root}/src && echo x > evil.py", cwd=root)
        self.assert_denied(
            f"cd /tmp && cd {root} && echo x | tee src/evil.py", cwd=root)

    def test_single_cd_scratchpad_relative_redirect_still_allowed(self):
        # The fix-3 win holds: one leading cd out of tree, relative target
        # resolves at the cd destination, not the spawn cwd.
        root = self.mkdir(onboarded=True)
        scratch = self.mkdir()
        self.assert_allowed(f"cd {scratch} && echo hi > x.txt", cwd=root)

    # --- The hook's own self-check stays green

    def test_self_check_passes(self):
        proc = subprocess.run(
            [sys.executable, str(HOOK), "--check"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("all checks passed", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
