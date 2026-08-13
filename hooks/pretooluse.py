#!/usr/bin/env python3
"""PreToolUse enforcement dispatcher for the AI Agent Dev Team.

Registered for Claude Code in ~/.claude/settings.json and for Codex in
~/.codex/hooks.json by install.sh. Converts the mechanically decidable
orchestration rules from prose to guarantees:

  A. Orchestrator edit block — in onboarded projects (COMPONENTS.md present),
     the main agent may not Edit/Write project files; personas implement.
  A2. Orchestrator Bash-mutation block — same rule, Bash loophole: in-place
     editors (sed -i, perl -i, patch) and redirects/tee into project files
     are denied for the main agent in onboarded projects.
  1. Ceremony gate — team ceremonies deny without COMPONENTS.md (run /onboard).
  2. Persona bead firewall — subagents may not create/close/delete/reopen
     beads; board state transitions are orchestrator territory.
  3. Bead-referenced commits — in repos with .beads/, `git commit -m` must
     reference a bead id (escape hatch: literal [no-bead]).

Merge authorization (once "Rule 4", a provider review fence) now lives entirely
in _shared/orchestration.md as a semantic rule — it is not enforced here.

Self-check after edits: python3 pretooluse.py --check
"""
import json
import os
import re
import sys

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CEREMONIES = {"team-plan", "team-review", "grooming", "standup", "spike", "postmortem"}
# Orchestrator territory per orchestration.md: COMPONENTS.md, the project
# CLAUDE.md block, hook/settings config. Everything else is persona work.
ORCH_WRITABLE_BASENAMES = {"AGENTS.md", "COMPONENTS.md", "CLAUDE.md"}


def patch_paths(patch):
    """Return paths targeted by Claude/Codex apply_patch input."""
    paths = []
    for line in patch.splitlines():
        match = re.match(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", line)
        if not match:
            match = re.match(r"^\*\*\* Move to: (.+)$", line)
        if match:
            paths.append(match.group(1))
    return paths


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


def git_roots(path):
    """All enclosing git roots, nearest first.

    .git is a directory in a main checkout but a gitdir-pointer FILE in a
    linked worktree (retro 2026-07-30-22) — both mark a root. Guards walk
    ALL ancestor roots, never just the nearest: any file named .git marks a
    root, so a planted `touch src/.git` — or a real submodule/vendored
    nested repo — would otherwise make the nearest root look un-onboarded
    and strip the enclosing project's guard (nearest-root injection,
    PR #12 review F1).
    """
    path = os.path.realpath(path)
    roots = []
    while path != os.path.dirname(path):
        if os.path.exists(os.path.join(path, ".git")):
            roots.append(path)
        path = os.path.dirname(path)
    return roots


def onboarded_root(path):
    """Nearest enclosing git root that carries COMPONENTS.md, or None."""
    return next((r for r in git_roots(path)
                 if os.path.isfile(os.path.join(r, "COMPONENTS.md"))), None)


def bash_scans(cmd):
    """Length-preserving scan variants of a Bash command.

    Heredoc bodies and quoted spans are data, not syntax: a `>` inside a
    heredoc body or a quoted string must not read as a redirect (field
    false-positives, retros 2026-07-20-08 and earlier). Both scans blank
    heredoc body lines (the `<<EOF` line itself stays — its redirects are
    real syntax). `scan` blanks quoted spans entirely, for detecting command
    syntax; `pscan` keeps quoted content minus shell metachars, so quoted
    redirect targets and cd destinations stay resolvable as paths. Both
    preserve offsets into the original command for segment attribution.
    """
    quoted = r"'[^']*'|\"[^\"]*\""
    blank = lambda m: " " * len(m.group(0))
    # Heredoc operators are located on quote-blanked text so a quoted "<<EOF"
    # is data and cannot swallow following lines; delimiter and body come
    # from the raw text at the operator's position.
    qblank = re.sub(quoted, blank, cmd)
    out = list(cmd)
    blanked = []
    for op in re.finditer(r"<<-?(?!<)", qblank):
        if any(a <= op.start() < b for a, b in blanked):
            continue  # operator text inside an already-blanked body
        d = re.match(r"<<-?\s*(['\"]?)(\w+)\1", cmd[op.start():])
        line_end = cmd.find("\n", op.start())
        if not d or line_end < 0:
            continue
        term = re.search(r"\n" + re.escape(d.group(2)) + r"(?=\n|$)",
                         cmd[line_end:])
        if not term:
            continue
        body = (line_end + 1, line_end + term.start())
        blanked.append(body)
        for i in range(*body):
            if out[i] != "\n":
                out[i] = " "
    cmd = "".join(out)
    scan = re.sub(quoted, blank, cmd)
    pscan = re.sub(quoted,
                   lambda m: re.sub(r"[<>|;&`\\]", "",
                                    m.group(0)[1:-1]).ljust(len(m.group(0))),
                   cmd)
    return scan, pscan


def segment_note(cmd, scan, pos):
    """Fix for denied compound commands (retro 2026-07-20-22): a PreToolUse
    hook can only deny the whole call, so when a compound command is denied,
    name the segment that triggered it and tell the agent to re-run the
    innocent setup segments separately."""
    cuts = [0]
    for m in re.finditer(r"&&|\|\||[;&|\n]", scan):
        cuts += [m.start(), m.end()]
    cuts.append(len(cmd))
    spans = [(cuts[i], cuts[i + 1]) for i in range(0, len(cuts), 2)
             if cmd[cuts[i]:cuts[i + 1]].strip()]
    if len(spans) < 2:
        return ""
    # pos may land on a separator char (e.g. the `;` in `true;>x`): clamp to
    # the nearest containing-or-following span, never the last by default.
    start, end = next(((a, b) for a, b in spans if pos < b), spans[-1])
    culprit = " ".join(cmd[start:end].split())
    if len(culprit) > 120:
        culprit = culprit[:117] + "..."
    return (" This denial applies to the whole compound command, but only "
            f"this segment triggered it: `{culprit}`. The other segments "
            "were NOT run — re-run them as separate commands.")


def bead_prefix(root):
    """The repo's own bead prefix: .beads/config.yaml issue-prefix, else dirname."""
    try:
        with open(os.path.join(root, ".beads", "config.yaml")) as f:
            m = re.search(r'^\s*issue-prefix:\s*["\']?([A-Za-z][A-Za-z0-9_]*)',
                          f.read(), re.M)
            if m:
                return m.group(1)
    except OSError:
        pass
    return os.path.basename(root)


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return  # malformed input: never block on our own bug

    tool = data.get("tool_name") or ""
    tool_input = data.get("tool_input") or {}
    cwd = data.get("cwd") or os.getcwd()
    agent_id = data.get("agent_id")  # absent => main agent (orchestrator)
    agent_type = data.get("agent_type") or ""

    # `onboarded` (Rules 1/A2) is any-ancestor: cwd inside a nested repo is
    # still inside the enclosing onboarded project. `root` is the onboarded
    # ancestor when one exists — A2's tree boundary — else the nearest root.
    roots = git_roots(cwd)
    nroot = roots[0] if roots else os.path.realpath(cwd)
    root = onboarded_root(cwd) or nroot
    onboarded = os.path.isfile(os.path.join(root, "COMPONENTS.md"))

    # Rule 1: ceremony gate
    if tool == "Skill":
        skill = (tool_input.get("skill") or "").split(":")[-1]
        if skill in CEREMONIES and not onboarded:
            deny(f"/{skill} requires COMPONENTS.md at the repo root — without it, "
                 "personas default to enterprise rigor. Run /onboard first.")
        return

    # Meta-work on the skill-system repo itself is exempt. The ancestor
    # clause (`meta in roots`) covers running from a REPO_DIR source
    # checkout, but must NOT strip guards off a genuinely-onboarded project
    # nested inside it — that mirrors the ancestor-stripping F1 closed. So
    # the ancestor exemption only fires when cwd is NOT inside an onboarded
    # project (`onboarded` == onboarded_root(cwd) is not None here).
    meta = os.path.realpath(REPO_DIR)
    if meta == nroot or (meta in roots and not onboarded):
        return

    # Rule A: orchestrator edit block. The root resolves from the EDITED
    # path, not cwd — cwd resets between tool calls, so a cwd-derived root
    # misclassified linked-worktree edits as out-of-project and bypassed
    # this guard entirely (retro 2026-07-30-22).
    if agent_id is None and tool in ("Edit", "Write", "NotebookEdit", "apply_patch"):
        if tool == "apply_patch":
            candidates = patch_paths(tool_input.get("patch") or tool_input.get("input") or "")
        else:
            candidates = [tool_input.get("file_path") or tool_input.get("notebook_path") or ""]
        for candidate in candidates:
            if not candidate:
                continue
            path = os.path.realpath(candidate if os.path.isabs(candidate)
                                    else os.path.join(cwd, candidate))
            # Guarded if ANY ancestor root is onboarded — a nearer planted
            # or nested .git cannot strip the enclosing project's guard.
            if onboarded_root(path) is None:
                continue  # scratchpad, retros, un-onboarded projects
            if os.path.basename(path) in ORCH_WRITABLE_BASENAMES:
                continue
            # Config exemption is judged under the NEAREST root: a worktree
            # living at <main>/.claude/worktrees/x is a project tree, not
            # tool configuration.
            rel = path[len(git_roots(path)[0]):]
            if (f"{os.sep}.claude{os.sep}" in rel
                    or f"{os.sep}.codex{os.sep}" in rel
                    or f"{os.sep}.agents{os.sep}" in rel):
                continue  # tool configuration is orchestrator territory
            break
        else:
            return
        deny("Orchestrator edit blocked: this is an onboarded team project — "
             "personas implement, the orchestrator dispatches. Identify the "
             "owning persona (project-engineer for code, technical-writer for "
             "docs, database-engineer for schema) and dispatch with a brief. "
             "See the installed _shared/orchestration.md.")

    if tool == "Bash":
        cmd = tool_input.get("command") or ""
        scan, pscan = bash_scans(cmd)
        # A leading `cd <path>` re-anchors the git context for the commit
        # gate and for resolving relative write targets (retro 2026-07-23-15).
        # Rules A2/A keep the spawn cwd's root/onboarded: an out-of-tree cd
        # must never disarm the orchestrator write block (kickback PTU-1).
        # Re-anchor ONLY when the leading cd is the command's sole cd: a
        # second cd (or subshell cd) desyncs ecwd from the shell's real cwd
        # (kickback PTU-5), so those shapes fall back to the spawn cwd.
        # ponytail: known ceiling, parity with main — a sole cd INTO an
        # onboarded tree from an un-onboarded spawn cwd is not judged at the
        # cd target; PO scope decision if a retro shows it in the field.
        ecwd = cwd
        m = re.match(r"\s*cd\s+([^\s;&|]+)\s*(?:&&|;|\n)", pscan)
        if m and len(re.findall(r"\bcd\s", scan)) == 1:
            dest = os.path.expandvars(os.path.expanduser(m.group(1)))
            ecwd = dest if os.path.isabs(dest) else os.path.join(cwd, dest)

        # Rule A2: orchestrator Bash-mutation block (the Bash loophole in rule A).
        # ponytail: heuristic — catches sed -i/perl -i/patch and redirect/tee into
        # project-tree paths; cp/mv and exotic shapes are out of scope until a retro
        # shows them in the field.
        if agent_id is None and onboarded:
            m = re.search(r"\b(sed|perl)\s+(-\w+\s+)*-\w*i|(?:^|[;&|]\s*)patch\s", scan)
            if m:
                deny("Orchestrator Bash edit blocked: in-place file edits (sed -i, "
                     "perl -i, patch) in an onboarded team project are persona work — "
                     "dispatch the owning persona. For orchestrator-territory files "
                     "(CLAUDE.md, .claude/) use the Edit/Write tools."
                     + segment_note(cmd, scan, m.start()))
            # Redirect/tee STRUCTURE is detected on scan (quoted words are
            # data — a commit message saying "tee" is not a tee command);
            # the TARGET characters are read from pscan at the same offsets,
            # where quoted content survives, so a quoted scratchpad target
            # resolves out-of-tree and a quoted project-tree target still
            # denies (retro 2026-07-20-08 + kickback round).
            for m in re.finditer(r"(?:^|[\s|;&])\d*>{1,2}(?!=)|\btee(?=\s)", scan):
                if m.group(0).endswith("tee"):
                    t = re.match(r"\s+(?:-a\s+)?([^\s;&|-][^\s;&|]*)",
                                 pscan[m.end():])
                else:
                    t = re.match(r"\s*([^\s;&|)]+)", pscan[m.end():])
                if not t:
                    continue
                target = t.group(1)
                if target.startswith(("&", "/dev/")):
                    continue
                expanded = os.path.expandvars(os.path.expanduser(target))
                resolved = os.path.realpath(expanded if os.path.isabs(expanded)
                                            else os.path.join(ecwd, expanded))
                if resolved == root or resolved.startswith(root + os.sep):
                    deny("Orchestrator Bash edit blocked: writing into the project "
                         "tree via redirect/tee in an onboarded team project is "
                         "persona work — dispatch the owning persona."
                         + segment_note(cmd, scan, m.start()))

        # Rule 2: persona bead firewall (beads:* agent types manage their own tasks)
        if agent_id is not None and not agent_type.startswith("beads:"):
            m = re.search(r"\bbd\s+(create|close|delete|reopen)\b", cmd)
            if m:
                deny("Board state transitions are orchestrator territory. "
                     "Report this as a finding in your response — the "
                     "orchestrator surfaces it to the PO, who decides whether "
                     "to file or close a bead. (bd update on beads you own is "
                     "allowed.)" + segment_note(cmd, scan, m.start()))

        # Rule 3: bead-referenced commits. Two accepted id shapes: any
        # prefix with a numeric suffix (proj-42), or the repo's OWN prefix
        # with a bd-style alphanumeric suffix and optional dotted children
        # (myrepo-wccvo, myrepo-0vao3.2, myrepo-09x38.17). Own-prefix-only
        # keeps hyphenated English ("well-tested") from passing as a bead
        # reference. The commit is judged against the repo the command runs
        # in (ecwd, honoring a leading cd — retro 2026-07-23-15), not the
        # spawn cwd. The check follows the message wherever it travels:
        # -m/--message text in the command itself, or the -F/--file message
        # file read at hook time — the gate is on bead-reference presence,
        # not on delivery mechanism. Messages the hook cannot see (stdin
        # via `-F -`, a file written later in the same compound command,
        # paths with shell substitutions) fail open: never block on a
        # message we cannot read.
        # Any-ancestor for the same nearest-root-injection reason as Rule A:
        # the beads root is the nearest ancestor root carrying .beads.
        broots = git_roots(ecwd)
        broot = next((r for r in broots
                      if os.path.isdir(os.path.join(r, ".beads"))),
                     broots[0] if broots else os.path.realpath(ecwd))
        commit = re.search(r"\bgit\s+commit\b", cmd)
        if (commit
                and broot != os.path.realpath(REPO_DIR)
                and os.path.isdir(os.path.join(broot, ".beads"))):
            def has_bead_ref(text):
                return ("[no-bead]" in text
                        or re.search(r"\b[A-Za-z][A-Za-z0-9_]*-\d+\b", text)
                        or re.search(r"\b" + re.escape(bead_prefix(broot))
                                     + r"-[a-z0-9]+(?:\.\d+)*\b", text, re.I))

            message = None
            if re.search(r"(^|\s)(-[a-zA-Z]*m|--message)\b", cmd):
                message = cmd
            else:
                fm = re.search(r"(?:^|\s)(?:-[a-zA-Z]*F|--file)(?:=|\s+)"
                               r"('[^']*'|\"[^\"]*\"|\S+)", cmd)
                if fm:
                    target = fm.group(1).strip("'\"")
                    if target != "-" and not re.search(r"[$`]", target):
                        path = os.path.expanduser(target)
                        if not os.path.isabs(path):
                            path = os.path.join(ecwd, path)
                        try:
                            with open(path) as f:
                                message = f.read()
                        except OSError:
                            message = None
            if message is not None and not has_bead_ref(message):
                deny("This repo uses beads: commit messages must reference a bead "
                     "id (e.g. proj-42 or " + bead_prefix(broot) + "-ab1c2). If this "
                     "commit genuinely has no bead, include the literal token "
                     "[no-bead]." + segment_note(cmd, scan, commit.start()))


def _self_check():
    import subprocess
    import tempfile

    def run(payload, setup=None):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as scratch:
            os.makedirs(os.path.join(tmp, ".git"))
            if setup:
                setup(tmp)
            payload = json.loads(json.dumps(payload).replace("<root>", tmp)
                                 .replace("<rootname>", os.path.basename(tmp))
                                 .replace("<scratch>", scratch))
            payload.setdefault("cwd", tmp)
            proc = subprocess.run(
                [sys.executable, os.path.abspath(__file__)],
                input=json.dumps(payload), capture_output=True, text=True)
            return "deny" in proc.stdout

    def onboarded(tmp):
        open(os.path.join(tmp, "COMPONENTS.md"), "w").close()

    def beaded(tmp):
        onboarded(tmp)
        os.makedirs(os.path.join(tmp, ".beads"))

    def beaded_with_prefix(tmp):
        beaded(tmp)
        with open(os.path.join(tmp, ".beads", "config.yaml"), "w") as f:
            f.write("issue-prefix: zork\n")

    # Rule 1: ceremony denied without COMPONENTS.md, allowed with; retro exempt
    assert run({"tool_name": "Skill", "tool_input": {"skill": "team-plan"}})
    assert not run({"tool_name": "Skill", "tool_input": {"skill": "team-plan"}}, onboarded)
    assert not run({"tool_name": "Skill", "tool_input": {"skill": "retro"}})
    # Rule A: orchestrator edit denied in onboarded project; subagent, COMPONENTS.md,
    # out-of-tree, and non-onboarded all allowed
    edit = {"tool_name": "Edit", "tool_input": {"file_path": "<root>/src/app.py"}}
    assert run(edit, onboarded)
    assert not run(edit)
    assert not run(dict(edit, agent_id="a1"), onboarded)
    assert not run({"tool_name": "Write", "tool_input": {"file_path": "<root>/COMPONENTS.md"}}, onboarded)
    assert not run({"tool_name": "Write", "tool_input": {"file_path": "/somewhere/else/notes.md"}}, onboarded)
    codex_patch = {
        "tool_name": "apply_patch",
        "tool_input": {"patch": "*** Begin Patch\n*** Update File: src/app.py\n@@\n-old\n+new\n*** End Patch\n"},
    }
    assert run(codex_patch, onboarded)
    assert not run(codex_patch)
    assert not run(dict(codex_patch, agent_id="a1"), onboarded)
    assert not run({
        "tool_name": "apply_patch",
        "tool_input": {"patch": "*** Begin Patch\n*** Update File: AGENTS.md\n@@\n-old\n+new\n*** End Patch\n"},
    }, onboarded)
    # Rule A in a linked worktree (retro 2026-07-30-22): .git is a gitdir-
    # pointer FILE, and the root resolves from the edited path — a stale cwd
    # outside the tree must not disarm the guard
    def onboarded_worktree(tmp):
        os.rmdir(os.path.join(tmp, ".git"))
        with open(os.path.join(tmp, ".git"), "w") as f:
            f.write("gitdir: /main/.git/worktrees/wt\n")
        os.makedirs(os.path.join(tmp, "src"))
        onboarded(tmp)

    # cwd sits in a SUBDIR of the worktree: with cwd at the root itself the
    # pre-fix realpath(cwd) fallback passed by accident (review F2)
    assert run(dict(edit, cwd="<root>/src"), onboarded_worktree)
    assert run(dict(edit, cwd="<scratch>"), onboarded_worktree)
    assert not run(dict(edit, agent_id="a1"), onboarded_worktree)
    # Rule A nearest-root injection (review F1): a planted .git in a subdir
    # must not strip the enclosing onboarded project's guard
    def planted(tmp):
        onboarded(tmp)
        os.makedirs(os.path.join(tmp, "src"))
        open(os.path.join(tmp, "src", ".git"), "w").close()

    assert run(edit, planted)
    assert run(dict(edit, cwd="<root>/src"), planted)
    # Rule A2: orchestrator sed -i / redirect into project denied when onboarded;
    # subagent, non-onboarded, /tmp and /dev/null targets all allowed
    sedi = {"tool_name": "Bash", "tool_input": {"command": "sed -i '' 's/a/b/' <root>/web/app.css"}}
    assert run(sedi, onboarded)
    assert not run(sedi)
    assert not run(dict(sedi, agent_id="a1"), onboarded)
    redir = {"tool_name": "Bash", "tool_input": {"command": "echo hi > <root>/src/x.txt"}}
    assert run(redir, onboarded)
    assert run({"tool_name": "Bash", "tool_input": {"command": "echo hi >> notes.md"}}, onboarded)
    assert not run({"tool_name": "Bash", "tool_input": {"command": "echo hi > /tmp/scratch.txt"}}, onboarded)
    assert not run({"tool_name": "Bash", "tool_input": {"command": "pytest > /dev/null 2>&1"}}, onboarded)
    assert run({"tool_name": "Bash", "tool_input": {"command": "cat a | tee <root>/README.md"}}, onboarded)
    # A2 false positives: metachars inside quoted data and bare >= are not redirects
    assert not run({"tool_name": "Bash", "tool_input": {"command": 'bd update x-1 --notes "score >= 0.5 uses `median`"'}}, onboarded)
    assert not run({"tool_name": "Bash", "tool_input": {"command": "awk $1 >= 3 file"}}, onboarded)
    assert not run({"tool_name": "Bash", "tool_input": {"command": "echo 'sed -i is blocked'"}}, onboarded)
    # A2 false positives (retro 2026-07-20-08): heredoc bodies and quoted
    # out-of-tree targets are not project-tree writes; quoted in-tree targets
    # still deny
    heredoc = 'cat > "<scratch>/pr.md" <<EOF\nbody with > x.md\nEOF'
    assert not run({"tool_name": "Bash", "tool_input": {"command": heredoc}}, onboarded)
    assert run({"tool_name": "Bash", "tool_input": {"command": 'echo hi > "<root>/src/x.txt"'}}, onboarded)
    # A2 invariant (kickback PTU-1): a leading cd — real or nonexistent —
    # never disarms the write guard for targets inside the onboarded spawn tree
    assert run({"tool_name": "Bash", "tool_input": {"command": "cd <scratch> && echo hi > <root>/src/x.txt"}}, onboarded)
    assert run({"tool_name": "Bash", "tool_input": {"command": "cd /no/such/dir && echo x > <root>/src/x.py"}}, onboarded)
    assert run({"tool_name": "Bash", "tool_input": {"command": "cd /tmp && sed -i '' s/a/b/ <root>/f.css"}}, onboarded)
    # chained cds bail the re-anchor to the spawn cwd (kickback PTU-5)
    assert run({"tool_name": "Bash", "tool_input": {"command": "cd /tmp && cd <root>/src && echo x > evil.py"}}, onboarded)
    # quoted `tee`/`<<EOF` are data (kickback reviewers #1/#2)
    assert not run({"tool_name": "Bash", "tool_input": {"command": 'git commit -m "docs: explain tee usage [no-bead]"'}}, onboarded)
    assert run({"tool_name": "Bash", "tool_input": {"command": 'echo "<<EOF"\necho hi > <root>/src/x.txt\nEOF'}}, onboarded)
    # Rule 2: subagent bd create denied; orchestrator, beads:*, and bd update allowed
    bd = {"tool_name": "Bash", "tool_input": {"command": "bd create 'thing'"}}
    assert run(dict(bd, agent_id="a1"))
    assert not run(bd)
    assert not run(dict(bd, agent_id="a1", agent_type="beads:task-agent"))
    assert not run({"tool_name": "Bash", "tool_input": {"command": "bd update x-1 --notes hi"}, "agent_id": "a1"})
    # Rule 3: commit without bead id denied in beads repo; id, [no-bead], no .beads allowed
    ci = {"tool_name": "Bash", "tool_input": {"command": 'git commit -m "fix the thing"'}}
    assert run(ci, beaded)
    assert not run({"tool_name": "Bash", "tool_input": {"command": 'git commit -m "proj-42: fix"'}}, beaded)
    assert not run({"tool_name": "Bash", "tool_input": {"command": 'git commit -m "chore [no-bead]"'}}, beaded)
    assert not run(ci, onboarded)
    # Rule 3 bd-style alphanumeric ids: own prefix (dirname or config override)
    # accepts, wrong prefix and hyphenated English still deny
    assert not run({"tool_name": "Bash", "tool_input": {"command": 'git commit -m "<rootname>-wccvo: fix"'}}, beaded)
    assert not run({"tool_name": "Bash", "tool_input": {"command": 'git commit -m "<rootname>-0vao3.2: fix"'}}, beaded)
    assert run({"tool_name": "Bash", "tool_input": {"command": 'git commit -m "add well-tested helper"'}}, beaded)
    assert run({"tool_name": "Bash", "tool_input": {"command": 'git commit -m "otherproj-wccvo: fix"'}}, beaded)
    assert not run({"tool_name": "Bash", "tool_input": {"command": 'git commit -m "<rootname>-09x38.17: fix"'}}, beaded)
    assert not run({"tool_name": "Bash", "tool_input": {"command": 'git commit -m "zork-ab1c2: fix"'}}, beaded_with_prefix)
    assert run({"tool_name": "Bash", "tool_input": {"command": 'git commit -m "<rootname>-wccvo: fix"'}}, beaded_with_prefix)
    # Rule 3 follows the command's cwd (retro 2026-07-23-15): a leading
    # `cd <path> &&` re-anchors the git context away from the spawn cwd
    assert not run({"tool_name": "Bash", "tool_input": {"command": 'cd <scratch> && git commit -m "no beads there"'}}, beaded)
    assert run({"tool_name": "Bash", "tool_input": {"command": 'cd <root> && git commit -m "still gated"'}, "cwd": "<scratch>"}, beaded)
    # Rule 3 via -F/--file: the message file is validated too — bead id,
    # [no-bead], or numeric id in the file passes; a file without any
    # denies; stdin and not-yet-written files fail open
    def beaded_msgfile(content):
        def setup(tmp):
            beaded(tmp)
            with open(os.path.join(tmp, "msg.txt"), "w") as f:
                f.write(content.replace("<rootname>", os.path.basename(tmp)))
        return setup

    fci = {"tool_name": "Bash", "tool_input": {"command": "git commit -F <root>/msg.txt"}}
    assert run(fci, beaded_msgfile("fix the thing\n"))
    assert not run(fci, beaded_msgfile("fix thing\n\n(bead <rootname>-wccvo)\n"))
    assert not run(fci, beaded_msgfile("fix thing (bead <rootname>-0vao3.2)\n"))
    assert not run(fci, beaded_msgfile("proj-42: fix\n"))
    assert not run(fci, beaded_msgfile("chore [no-bead]\n"))
    assert run({"tool_name": "Bash", "tool_input": {"command": "git commit --file=<root>/msg.txt"}}, beaded_msgfile("fix the thing\n"))
    assert run({"tool_name": "Bash", "tool_input": {"command": "git commit -F msg.txt"}}, beaded_msgfile("fix the thing\n"))  # relative to cwd
    assert not run({"tool_name": "Bash", "tool_input": {"command": "git commit -F <root>/absent.txt"}}, beaded)
    assert not run({"tool_name": "Bash", "tool_input": {"command": "git commit -F -"}}, beaded)
    # Rule 4 removed: gh pr merge is no longer fenced, in any repo including this one.
    assert not run({
        "tool_name": "Bash",
        "tool_input": {"command": "gh pr merge 42 --squash"},
    }, onboarded)
    meta_proc = subprocess.run(
        [sys.executable, os.path.abspath(__file__)],
        input=json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr merge 42 --squash"},
            "cwd": REPO_DIR,
        }),
        capture_output=True, text=True)
    assert "deny" not in meta_proc.stdout
    print("all checks passed")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        _self_check()
    else:
        main()
