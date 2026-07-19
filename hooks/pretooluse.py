#!/usr/bin/env python3
"""PreToolUse enforcement dispatcher for the AI Agent Dev Team.

Registered in ~/.claude/settings.json by install.sh (matcher:
Edit|Write|NotebookEdit|Bash|Skill). Converts the mechanically decidable
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

Semantic rules (merge authorization, definition of done, backlog sign-off)
stay in _shared/orchestration.md — they are not mechanically decidable.

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
ORCH_WRITABLE_BASENAMES = {"COMPONENTS.md", "CLAUDE.md"}


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


def git_root(path):
    path = os.path.realpath(path)
    while path != os.path.dirname(path):
        if os.path.isdir(os.path.join(path, ".git")):
            return path
        path = os.path.dirname(path)
    return None


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

    root = git_root(cwd) or os.path.realpath(cwd)
    if root == os.path.realpath(REPO_DIR):
        return  # meta-work exception: this repo governs itself, direct edits are fine

    onboarded = os.path.isfile(os.path.join(root, "COMPONENTS.md"))
    uses_beads = os.path.isdir(os.path.join(root, ".beads"))

    # Rule 1: ceremony gate
    if tool == "Skill":
        skill = (tool_input.get("skill") or "").split(":")[-1]
        if skill in CEREMONIES and not onboarded:
            deny(f"/{skill} requires COMPONENTS.md at the repo root — without it, "
                 "personas default to enterprise rigor. Run /onboard first.")
        return

    # Rule A: orchestrator edit block
    if agent_id is None and tool in ("Edit", "Write", "NotebookEdit"):
        if not onboarded:
            return
        path = os.path.realpath(tool_input.get("file_path")
                                or tool_input.get("notebook_path") or "")
        if not path.startswith(root + os.sep):
            return  # scratchpad, retros, ~/.claude — outside the project tree
        if os.path.basename(path) in ORCH_WRITABLE_BASENAMES:
            return
        if f"{os.sep}.claude{os.sep}" in path:
            return  # hook/settings config is orchestrator territory
        deny("Orchestrator edit blocked: this is an onboarded team project — "
             "personas implement, the orchestrator dispatches. Identify the "
             "owning persona (project-engineer for code, technical-writer for "
             "docs, database-engineer for schema) and dispatch with a brief. "
             "See ~/.claude/skills/_shared/orchestration.md.")

    if tool == "Bash":
        cmd = tool_input.get("command") or ""
        # Quoted spans are data, not command syntax: a `>=` or backtick inside a
        # bd description must not read as a redirect (field false-positive, 3x).
        scan = re.sub(r"'[^']*'|\"[^\"]*\"", " ", cmd)

        # Rule A2: orchestrator Bash-mutation block (the Bash loophole in rule A).
        # ponytail: heuristic — catches sed -i/perl -i/patch and redirect/tee into
        # project-tree paths; cp/mv and exotic shapes are out of scope until a retro
        # shows them in the field.
        if agent_id is None and onboarded:
            if re.search(r"\b(sed|perl)\s+(-\w+\s+)*-\w*i|(?:^|[;&|]\s*)patch\s", scan):
                deny("Orchestrator Bash edit blocked: in-place file edits (sed -i, "
                     "perl -i, patch) in an onboarded team project are persona work — "
                     "dispatch the owning persona. For orchestrator-territory files "
                     "(CLAUDE.md, .claude/) use the Edit/Write tools.")
            for m in re.finditer(r"(?:^|[\s|;&])\d*>{1,2}(?!=)\s*([^\s;&|)]+)|\btee\s+(?:-a\s+)?([^\s;&|-][^\s;&|]*)", scan):
                target = m.group(1) or m.group(2)
                if target.startswith(("&", "/dev/")):
                    continue
                expanded = os.path.expandvars(os.path.expanduser(target))
                resolved = os.path.realpath(expanded if os.path.isabs(expanded)
                                            else os.path.join(cwd, expanded))
                if resolved == root or resolved.startswith(root + os.sep):
                    deny("Orchestrator Bash edit blocked: writing into the project "
                         "tree via redirect/tee in an onboarded team project is "
                         "persona work — dispatch the owning persona.")

        # Rule 2: persona bead firewall (beads:* agent types manage their own tasks)
        if agent_id is not None and not agent_type.startswith("beads:"):
            if re.search(r"\bbd\s+(create|close|delete|reopen)\b", cmd):
                deny("Board state transitions are orchestrator territory. "
                     "Report this as a finding in your response — the "
                     "orchestrator surfaces it to the PO, who decides whether "
                     "to file or close a bead. (bd update on beads you own is "
                     "allowed.)")

        # Rule 3: bead-referenced commits. Two accepted id shapes: any
        # prefix with a numeric suffix (proj-42), or the repo's OWN prefix
        # with a bd-style alphanumeric suffix and optional dotted children
        # (myrepo-wccvo, myrepo-0vao3.2). Own-prefix-only keeps hyphenated
        # English ("well-tested") from passing as a bead reference.
        if (uses_beads
                and re.search(r"\bgit\s+commit\b", cmd)
                and re.search(r"(^|\s)(-[a-zA-Z]*m|--message)\b", cmd)
                and "[no-bead]" not in cmd
                and not re.search(r"\b[A-Za-z][A-Za-z0-9_]*-\d+\b", cmd)
                and not re.search(r"\b" + re.escape(bead_prefix(root))
                                  + r"-[a-z0-9]+(?:\.\d+)*\b", cmd, re.I)):
            deny("This repo uses beads: commit messages must reference a bead "
                 "id (e.g. proj-42 or " + bead_prefix(root) + "-ab1c2). If this "
                 "commit genuinely has no bead, include the literal token "
                 "[no-bead].")


def _self_check():
    import subprocess
    import tempfile

    def run(payload, setup=None):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, ".git"))
            if setup:
                setup(tmp)
            payload = json.loads(json.dumps(payload).replace("<root>", tmp)
                                 .replace("<rootname>", os.path.basename(tmp)))
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
    assert not run({"tool_name": "Bash", "tool_input": {"command": 'git commit -m "zork-ab1c2: fix"'}}, beaded_with_prefix)
    assert run({"tool_name": "Bash", "tool_input": {"command": 'git commit -m "<rootname>-wccvo: fix"'}}, beaded_with_prefix)
    print("all checks passed")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        _self_check()
    else:
        main()
