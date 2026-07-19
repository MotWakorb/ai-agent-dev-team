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
  4. Provider review fence — direct `gh pr merge` commands require trusted
     GitHub check runs bound to the canonical repository and immutable PR head;
     direct git merges and unsupported shell wrappers fail closed.

Semantic rules (live merge authorization, definition of done, backlog sign-off)
stay in _shared/orchestration.md — they are not mechanically decidable.

Self-check after edits: python3 pretooluse.py --check
"""
import json
import os
import re
import shlex
import subprocess
import sys
import time

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


REQUIRED_CHECKS = (
    "ai-team/code-review",
    "ai-team/data-integrity-classification",
    "ai-team/dba-review",
)


def merge_shaped(command):
    """Recognize merge executables while treating ordinary arguments as data."""
    command = strip_heredoc_bodies(command)
    if re.search(r"\$\([^)]*(?:gh\s+pr\s+merge|git\s+merge)\b", command, re.S):
        return True
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return bool(re.search(r"\b(?:gh\s+pr\s+merge|git\s+merge)\b", command))
    start = 0
    while start < len(tokens):
        end = start
        while end < len(tokens) and tokens[end] not in (";", "&&", "||", "|", "&"):
            end += 1
        segment = tokens[start:end]
        if executable_segment_is_merge(segment):
            return True
        start = end + 1
    return False


def strip_heredoc_bodies(command):
    """Remove heredoc payload lines; their contents are not shell commands."""
    lines = command.splitlines(keepends=True)
    output = []
    terminator = None
    for line in lines:
        if terminator is not None:
            if line.strip() == terminator:
                terminator = None
                output.append(line)
            else:
                output.append("\n")
            continue
        output.append(line)
        match = re.search(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", line)
        if match:
            terminator = match.group(2)
    return "".join(output)


def executable_segment_is_merge(tokens):
    if not tokens:
        return False
    cursor = 0
    while cursor < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[cursor]):
        cursor += 1
    if cursor >= len(tokens):
        return False
    executable = os.path.basename(tokens[cursor])
    rest = tokens[cursor + 1:]
    if executable in ("env", "command"):
        while rest and (rest[0].startswith("-") or "=" in rest[0]):
            rest = rest[1:]
        return executable_segment_is_merge(rest)
    if executable in ("sh", "bash", "zsh") and "-c" in rest:
        index = rest.index("-c")
        return index + 1 < len(rest) and merge_shaped(rest[index + 1])
    if executable == "gh":
        return rest[:2] == ["pr", "merge"]
    if executable == "git":
        cursor = 0
        while cursor < len(rest) and rest[cursor] != "merge":
            if rest[cursor] in ("-C", "-c", "--git-dir", "--work-tree", "--namespace"):
                cursor += 2
            elif rest[cursor].startswith("-"):
                cursor += 1
            else:
                return False
        return cursor < len(rest) and rest[cursor] == "merge"
    return False


def parse_merge_command(command):
    """Parse the one supported merge form: direct `gh pr merge <number> ...`."""
    if not merge_shaped(command):
        return None, "not a merge-shaped command"
    if any(marker in command for marker in ("$(", "`", "\n", "\r", ";", "&&", "||", "|")):
        return None, "dynamic, nested, or compound shell merge commands are unsupported"
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None, "malformed shell quoting"
    if tokens[:3] != ["gh", "pr", "merge"]:
        return None, "only the direct `gh pr merge` form is supported"
    if len(tokens) < 4 or not tokens[3].isdigit():
        return None, "an explicit numeric PR must immediately follow `gh pr merge`"
    result = {"pr": int(tokens[3]), "repo": None, "head": None}
    flag_only = {
        "--admin", "--auto", "--delete-branch", "--disable-auto", "--merge",
        "--rebase", "--squash",
    }
    value_options = {
        "-b": "ignored", "--body": "ignored", "-F": "ignored",
        "--body-file": "ignored", "-s": "ignored", "--subject": "ignored",
        "-R": "repo", "--repo": "repo", "--match-head-commit": "head",
    }
    cursor = 4
    while cursor < len(tokens):
        token = tokens[cursor]
        if token == "--":
            if cursor != len(tokens) - 1:
                return None, "multiple merge targets are unsupported"
            cursor += 1
            continue
        if token in flag_only:
            cursor += 1
            continue
        option, separator, attached = token.partition("=")
        if not separator and len(token) > 2 and token[:2] in ("-b", "-F", "-s", "-R"):
            option, attached = token[:2], token[2:]
            separator = "="
        if option in value_options:
            if separator:
                value = attached
            elif cursor + 1 < len(tokens):
                cursor += 1
                value = tokens[cursor]
            else:
                return None, f"{option} requires a value"
            field = value_options[option]
            if not value or (field != "ignored" and result[field] is not None):
                return None, f"invalid or repeated {option}"
            if field != "ignored":
                result[field] = value
            cursor += 1
            continue
        return None, f"unsupported merge argument: {token}"
    if not result["head"] or not re.fullmatch(r"[0-9a-fA-F]{40}", result["head"]):
        return None, "supply the full 40-character PR head with --match-head-commit <sha>"
    return result, None


def load_review_config(root):
    path = os.path.join(root, ".agents", "review-gate.json")
    try:
        with open(path, encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, ValueError):
        return None, "missing or invalid .agents/review-gate.json"
    if not isinstance(config, dict):
        return None, "invalid .agents/review-gate.json object"
    return config, None


def validate_review_config(config):
    if not isinstance(config, dict):
        return "review-gate config must be a JSON object"
    if config.get("version") != 1:
        return "review-gate config version must be 1"
    if not isinstance(config.get("github_repository"), str) or not re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", config["github_repository"]):
        return "review-gate github_repository is invalid"
    if not isinstance(config.get("github_hostname"), str) or not re.fullmatch(
            r"[A-Za-z0-9.-]+", config["github_hostname"]):
        return "review-gate github_hostname is invalid"
    apps = config.get("required_check_apps")
    if not isinstance(apps, dict):
        return "review-gate required_check_apps must be an object"
    for name in REQUIRED_CHECKS:
        app = apps.get(name)
        if (not isinstance(app, dict)
                or not isinstance(app.get("id"), int)
                or isinstance(app.get("id"), bool)
                or app["id"] <= 0
                or not isinstance(app.get("slug"), str)
                or not re.fullmatch(r"[A-Za-z0-9-]+", app["slug"])):
            return f"trusted app id/slug is invalid for {name}"
    return None


def trusted_check(config, name, head, checks):
    app = config["required_check_apps"][name]
    candidates = [
        check for check in checks
        if isinstance(check, dict)
        and check.get("name") == name
        and isinstance(check.get("head_sha"), str)
        and check["head_sha"] == head
        and isinstance(check.get("app"), dict)
        and check["app"].get("id") == app["id"]
        and check["app"].get("slug") == app["slug"]
        and isinstance(check.get("id"), int)
    ]
    if not candidates:
        return None, f"trusted {name} check is missing for {head}"
    latest = max(candidates, key=lambda check: check.get("id") or 0)
    if latest.get("status") != "completed" or latest.get("conclusion") != "success":
        return None, f"latest trusted {name} check is not successful"
    return latest, None


def provider_gate(config, canonical_repo, head, checks):
    """Validate trusted GitHub check runs for one canonical repo and head SHA."""
    error = validate_review_config(config)
    if error:
        return False, error
    if not isinstance(canonical_repo, str) or not isinstance(head, str):
        return False, "canonical repository or head SHA has an invalid type"
    checks, error = validate_check_runs_response({
        "total_count": len(checks) if isinstance(checks, list) else None,
        "check_runs": checks,
    })
    if error:
        return False, error
    if config["github_repository"].lower() != canonical_repo.lower():
        return False, "configured repository does not match the canonical GitHub repository"
    _, error = trusted_check(config, REQUIRED_CHECKS[0], head, checks)
    if error:
        return False, error
    classification, error = trusted_check(config, REQUIRED_CHECKS[1], head, checks)
    if error:
        return False, error
    title = ((classification.get("output") or {}).get("title") or "").strip()
    if title not in ("classification:data-integrity", "classification:other"):
        return False, "classification check output.title is malformed"
    if title == "classification:data-integrity":
        _, error = trusted_check(config, REQUIRED_CHECKS[2], head, checks)
        if error:
            return False, error
    return True, None


def gh_json(args, cwd, hostname, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return None, "GitHub provider deadline exceeded"
    environment = os.environ.copy()
    environment["GH_HOST"] = hostname
    try:
        process = subprocess.run(
            ["gh", *args], cwd=cwd, env=environment, capture_output=True,
            text=True, timeout=min(4, remaining))
    except (OSError, subprocess.TimeoutExpired):
        return None, "GitHub provider query unavailable or timed out"
    if process.returncode:
        return None, "GitHub provider query failed"
    try:
        return json.loads(process.stdout), None
    except ValueError:
        return None, "GitHub provider returned invalid JSON"


def validate_check_runs_response(response):
    if not isinstance(response, dict):
        return None, "GitHub check-run response must be an object"
    total = response.get("total_count")
    checks = response.get("check_runs")
    if (not isinstance(total, int) or isinstance(total, bool)
            or not isinstance(checks, list) or total != len(checks)):
        return None, "GitHub check-run state is unavailable or ambiguous"
    for check in checks:
        if not isinstance(check, dict):
            return None, "GitHub check-run entry must be an object"
        if (not isinstance(check.get("id"), int)
                or isinstance(check.get("id"), bool)
                or not isinstance(check.get("name"), str)
                or not isinstance(check.get("head_sha"), str)
                or not isinstance(check.get("status"), str)
                or not isinstance(check.get("conclusion"), (str, type(None)))
                or not isinstance(check.get("app"), dict)
                or not isinstance(check["app"].get("id"), int)
                or isinstance(check["app"].get("id"), bool)
                or not isinstance(check["app"].get("slug"), str)
                or not isinstance(check.get("output"), dict)
                or not isinstance(check["output"].get("title"), (str, type(None)))):
            return None, "GitHub check-run entry has invalid field types"
    return checks, None


def verify_github_merge(parsed, root):
    deadline = time.monotonic() + 18
    config, error = load_review_config(root)
    if error:
        return error
    error = validate_review_config(config)
    if error:
        return error
    hostname = config["github_hostname"]
    requested_repo = parsed["repo"]
    if requested_repo:
        repo_data, error = gh_json(
            ["api", "--hostname", hostname, f"repos/{requested_repo}"],
            root, hostname, deadline)
    else:
        view, error = gh_json(
            ["repo", "view", "--json", "nameWithOwner"],
            root, hostname, deadline)
        if error:
            return error
        requested_repo = view.get("nameWithOwner") if isinstance(view, dict) else None
        if not requested_repo:
            return "cannot resolve the current GitHub repository"
        repo_data, error = gh_json(
            ["api", "--hostname", hostname, f"repos/{requested_repo}"],
            root, hostname, deadline)
    if error:
        return error
    canonical_repo = repo_data.get("full_name") if isinstance(repo_data, dict) else None
    if not isinstance(canonical_repo, str) or not re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", canonical_repo):
        return "GitHub repository identity is ambiguous"
    pull, error = gh_json(
        ["api", "--hostname", hostname,
         f"repos/{canonical_repo}/pulls/{parsed['pr']}"],
        root, hostname, deadline)
    if error:
        return error
    if not isinstance(pull, dict):
        return "GitHub PR state is unavailable or ambiguous"
    base = pull.get("base")
    head_state = pull.get("head")
    if (not isinstance(base, dict)
            or not isinstance(base.get("repo"), dict)
            or not isinstance(base["repo"].get("full_name"), str)
            or not isinstance(head_state, dict)
            or not isinstance(head_state.get("sha"), str)
            or not re.fullmatch(r"[0-9a-fA-F]{40}", head_state["sha"])):
        return "GitHub PR state has invalid field types"
    if base["repo"]["full_name"].lower() != canonical_repo.lower():
        return "PR base repository does not match the canonical repository"
    head = head_state["sha"]
    if not head or head.lower() != parsed["head"].lower():
        return "PR head moved or --match-head-commit does not match"
    checks_data, error = gh_json(
        ["api", "--hostname", hostname, "-H", "Accept: application/vnd.github+json",
         f"repos/{canonical_repo}/commits/{head}/check-runs?filter=all&per_page=100"],
        root, hostname, deadline)
    if error:
        return error
    checks, error = validate_check_runs_response(checks_data)
    if error:
        return error
    allowed, error = provider_gate(config, canonical_repo, head, checks)
    return None if allowed else error


def enforce_merge(command, root, verifier=verify_github_merge):
    """Return a sanitized denial reason, or None when provider checks allow."""
    try:
        parsed, error = parse_merge_command(command)
        if error:
            return error
        return verifier(parsed, root)
    except Exception:
        return "internal provider review-gate error"


def rule4_error(command, root):
    """Run merge discovery and enforcement behind one no-crash boundary."""
    try:
        if not isinstance(command, str) or not merge_shaped(command):
            return None
        return enforce_merge(command, root)
    except Exception:
        return "internal provider review-gate error"


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
    onboarded = os.path.isfile(os.path.join(root, "COMPONENTS.md"))
    uses_beads = os.path.isdir(os.path.join(root, ".beads"))

    # Rule 1: ceremony gate
    if tool == "Skill":
        skill = (tool_input.get("skill") or "").split(":")[-1]
        if skill in CEREMONIES and not onboarded:
            deny(f"/{skill} requires COMPONENTS.md at the repo root — without it, "
                 "personas default to enterprise rigor. Run /onboard first.")
        return

    if root == os.path.realpath(REPO_DIR) and tool != "Bash":
        return  # meta-work exception; Bash merge enforcement runs below

    # Rule A: orchestrator edit block
    if agent_id is None and tool in ("Edit", "Write", "NotebookEdit", "apply_patch"):
        if not onboarded:
            return
        if tool == "apply_patch":
            candidates = patch_paths(tool_input.get("patch") or tool_input.get("input") or "")
        else:
            candidates = [tool_input.get("file_path") or tool_input.get("notebook_path") or ""]
        for candidate in candidates:
            path = os.path.realpath(candidate if os.path.isabs(candidate)
                                    else os.path.join(cwd, candidate))
            if not path.startswith(root + os.sep):
                continue  # scratchpad, retros, user-level config
            if os.path.basename(path) in ORCH_WRITABLE_BASENAMES:
                continue
            if (f"{os.sep}.claude{os.sep}" in path
                    or f"{os.sep}.codex{os.sep}" in path
                    or f"{os.sep}.agents{os.sep}" in path):
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
        # Quoted spans are data, not command syntax: a `>=` or backtick inside a
        # bd description must not read as a redirect (field false-positive, 3x).
        scan = re.sub(r"'[^']*'|\"[^\"]*\"", " ", cmd)

        # Rule 4: provider-authoritative review fence. The supported command keeps
        # the literal `gh pr merge` prefix so the independent installer ask-gate
        # still requires a live authorization click.
        error = rule4_error(cmd, root)
        if error:
            deny("Merge blocked: provider review gate failed: " + error + ". "
                 "Use direct `gh pr merge <number> ... --match-head-commit "
                 "<full-40-character-sha>`; direct git merges and shell wrappers "
                 "cannot be bound safely to provider review state. "
                 "Required trusted checks: " + ", ".join(REQUIRED_CHECKS) + ". "
                 "This does not replace the separate live merge-authorization gate.")

        if root == os.path.realpath(REPO_DIR):
            return  # meta-work exemption excludes merge enforcement above

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
    # Rule 4 parser: only the ask-gate-compatible direct gh prefix is supported.
    parsed, error = parse_merge_command(
        "gh pr merge 42 --squash --repo Owner/Repo --match-head-commit aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert not error
    assert parsed == {"pr": 42, "repo": "Owner/Repo", "head": "a" * 40}
    parsed, error = parse_merge_command(
        "gh pr merge 42 -ROwner/Repo --match-head-commit=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert not error and parsed["repo"] == "Owner/Repo"
    for command in (
        "gh pr merge 42 --squash",
        "gh pr merge --squash",
        "/usr/bin/gh pr merge 42 --match-head-commit aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "env gh pr merge 42 --match-head-commit aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "command gh pr merge 42 --match-head-commit aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "sh -c 'gh pr merge 42 --match-head-commit aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'",
        "gh pr merge 42 43 --match-head-commit aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "gh pr merge 42 --match-head-commit=$(git rev-parse HEAD)",
        "git merge feature",
        "git -C /tmp/worktree merge feature",
        "git merge feature other",
    ):
        assert merge_shaped(command)
        _, error = parse_merge_command(command)
        assert error, command
    assert not merge_shaped("git merge-base main HEAD")
    for command in (
        'echo "gh pr merge 42"',
        'git commit -m "document gh pr merge 42"',
        "bd update x-1 --notes 'never run git merge feature'",
        "python3 - <<'PY'\nprint('gh pr merge 42')\nPY",
    ):
        assert not merge_shaped(command), command
    assert run({
        "tool_name": "Bash",
        "tool_input": {"command": "gh pr merge 42 --match-head-commit aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
    }, onboarded)

    # The skill-system repo's meta-work exemption does not exempt merges.
    meta_proc = subprocess.run(
        [sys.executable, os.path.abspath(__file__)],
        input=json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr merge 42 --match-head-commit aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
            "cwd": REPO_DIR,
        }),
        capture_output=True, text=True)
    assert "deny" in meta_proc.stdout
    assert enforce_merge(
        "gh pr merge 42 --match-head-commit aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", REPO_DIR,
        verifier=lambda parsed, root: (_ for _ in ()).throw(RuntimeError("secret"))) \
        == "internal provider review-gate error"
    assert enforce_merge(
        "gh pr merge 42 --match-head-commit aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", REPO_DIR,
        verifier=lambda parsed, root: "GitHub provider deadline exceeded") \
        == "GitHub provider deadline exceeded"

    # Provider validation is bound to canonical repo, immutable head, and trusted apps.
    config = {
        "version": 1,
        "github_repository": "Owner/Repo",
        "github_hostname": "github.com",
        "required_check_apps": {
            "ai-team/code-review": {"id": 101, "slug": "trusted-review"},
            "ai-team/data-integrity-classification": {"id": 102, "slug": "trusted-classifier"},
            "ai-team/dba-review": {"id": 103, "slug": "trusted-dba"},
        },
    }
    def check(name, app_id, slug, title=""):
        return {
            "id": app_id * 10,
            "name": name,
            "head_sha": "a" * 40,
            "status": "completed",
            "conclusion": "success",
            "app": {"id": app_id, "slug": slug},
            "output": {"title": title},
        }
    other_checks = [
        check("ai-team/code-review", 101, "trusted-review"),
        check("ai-team/data-integrity-classification", 102, "trusted-classifier",
              "classification:other"),
    ]
    assert provider_gate(config, "Owner/Repo", "a" * 40, other_checks) == (True, None)
    data_checks = other_checks[:-1] + [
        check("ai-team/data-integrity-classification", 102, "trusted-classifier",
              "classification:data-integrity"),
        check("ai-team/dba-review", 103, "trusted-dba"),
    ]
    assert provider_gate(config, "owner/repo", "a" * 40, data_checks) == (True, None)
    assert validate_check_runs_response({
        "total_count": len(data_checks), "check_runs": data_checks,
    }) == (data_checks, None)
    for malformed_response in (
        [],
        {"total_count": "2", "check_runs": data_checks},
        {"total_count": 1, "check_runs": ["malformed"]},
        {"total_count": 1, "check_runs": [{"id": 1, "app": []}]},
    ):
        assert validate_check_runs_response(malformed_response)[0] is None
    for bad_config, repo, head, checks in (
        ([], "Owner/Repo", "a" * 40, other_checks),
        ({}, "Owner/Repo", "a" * 40, other_checks),
        (config, "Other/Repo", "a" * 40, other_checks),
        (config, "Owner/Repo", "b" * 40, other_checks),
        (config, "Owner/Repo", "a" * 40,
         [check("ai-team/code-review", 999, "attacker")] + other_checks[1:]),
        (config, "Owner/Repo", "a" * 40,
         other_checks[:-1] + [check("ai-team/data-integrity-classification",
                                   102, "trusted-classifier", "other")]),
        (config, "Owner/Repo", "a" * 40, data_checks[:-1]),
        (config, "Owner/Repo", "a" * 40, ["malformed"]),
        (config, "Owner/Repo", "a" * 40,
         other_checks[:-1] + [{"name": "ai-team/data-integrity-classification",
                              "head_sha": "a" * 40, "app": []}]),
    ):
        assert provider_gate(bad_config, repo, head, checks)[0] is False
    print("all checks passed")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        _self_check()
    else:
        main()
