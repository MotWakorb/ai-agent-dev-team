#!/usr/bin/env bash
set -euo pipefail

# Claude Agent Dev Team — Claude Code + Codex Installer
# Default: symlinks skills into ~/.claude/skills/ and ~/.agents/skills/
# --copy: copy instead of symlink (for customization)
# --project <dir>: install into <dir>/.claude instead of ~/.claude (forces copy mode)
# --local: with --project, register the hook in settings.local.json (personal, not committed)

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="symlink"
PROJECT_DIR=""
LOCAL_SETTINGS=0

usage() {
  echo "Usage: ./install.sh [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  (default)        Symlink skills into ~/.claude/skills/ (git pull updates automatically)"
  echo "  --copy           Copy skills instead of symlink (for customization)"
  echo "  --project <dir>  Install into <dir>/.claude and <dir>/.agents instead of globally —"
  echo "                   available only in that project. Forces copy mode so the install"
  echo "                   is self-contained and committable (teammates get it via git)."
  echo "  --local          With --project: register the enforcement hook in"
  echo "                   settings.local.json instead of settings.json (personal install;"
  echo "                   gitignore .claude/skills, .claude/agents, .claude/hooks too)"
  echo "  --help           Show this help"
}

while [ $# -gt 0 ]; do
  case $1 in
    --copy)
      MODE="copy"
      ;;
    --project)
      shift
      [ $# -gt 0 ] || { echo "ERROR: --project requires a path" >&2; exit 1; }
      PROJECT_DIR="$1"
      ;;
    --local)
      LOCAL_SETTINGS=1
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

if [ "$LOCAL_SETTINGS" -eq 1 ] && [ -z "$PROJECT_DIR" ]; then
  echo "ERROR: --local only applies to project installs (use with --project)" >&2
  exit 1
fi

if [ -n "$PROJECT_DIR" ]; then
  [ -d "$PROJECT_DIR" ] || { echo "ERROR: ${PROJECT_DIR} is not a directory" >&2; exit 1; }
  PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
  if [ "$PROJECT_DIR" = "$REPO_DIR" ]; then
    echo "ERROR: --project target is this repo itself — point it at the project that should get the team" >&2
    exit 1
  fi
  # Symlinks into a personal clone break for anyone else who clones the project
  MODE="copy"
  CLAUDE_ROOT="${PROJECT_DIR}/.claude"
  CLAUDE_MD="${PROJECT_DIR}/CLAUDE.md"
  CODEX_SKILLS_DIR="${PROJECT_DIR}/.agents/skills"
  CODEX_MD="${PROJECT_DIR}/AGENTS.md"
  CODEX_ORCH_PATH=".agents/skills/_shared/orchestration.md"
  ORCH_PATH=".claude/skills/_shared/orchestration.md"
  # Literal $CLAUDE_PROJECT_DIR — Claude Code expands it at hook time, so the
  # committed settings entry has no user-specific absolute path in it
  HOOK_CMD='python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/pretooluse.py"'
  if [ "$LOCAL_SETTINGS" -eq 1 ]; then
    SETTINGS_JSON="${CLAUDE_ROOT}/settings.local.json"
  else
    SETTINGS_JSON="${CLAUDE_ROOT}/settings.json"
  fi
else
  CLAUDE_ROOT="${HOME}/.claude"
  CLAUDE_MD="${CLAUDE_ROOT}/CLAUDE.md"
  CODEX_SKILLS_DIR="${HOME}/.agents/skills"
  CODEX_MD="${CODEX_HOME:-${HOME}/.codex}/AGENTS.md"
  CODEX_ORCH_PATH="~/.agents/skills/_shared/orchestration.md"
  ORCH_PATH="~/.claude/skills/_shared/orchestration.md"
  HOOK_CMD="python3 \"${REPO_DIR}/hooks/pretooluse.py\""
  SETTINGS_JSON="${CLAUDE_ROOT}/settings.json"
fi

SKILLS_DIR="${CLAUDE_ROOT}/skills"
AGENTS_DIR="${CLAUDE_ROOT}/agents"
RETRO_DIR="${HOME}/retros"

# All skill directories (order doesn't matter)
SKILLS=(
  _shared
  security-engineer
  it-architect
  project-manager
  project-engineer
  ux-designer
  code-reviewer
  database-engineer
  sre
  qa-engineer
  technical-writer
  retro
  retro-sync
  retro-mine
  team-plan
  team-review
  standup
  grooming
  spike
  postmortem
  onboard
  release-check
)

echo "Installing Claude Agent Dev Team skills for Claude Code and Codex..."
echo "  Mode: ${MODE}"
echo "  From: ${REPO_DIR}"
echo "  Claude: ${SKILLS_DIR}"
echo "  Codex:  ${CODEX_SKILLS_DIR}"
echo ""

# Create skills directory if it doesn't exist
mkdir -p "$SKILLS_DIR" "$CODEX_SKILLS_DIR"

# Create retro directory (the retro skill writes to ~/retros regardless of install scope)
mkdir -p "$RETRO_DIR"

# Track results
installed=0
skipped=0
updated=0

for destination in "$SKILLS_DIR" "$CODEX_SKILLS_DIR"; do
  for skill in "${SKILLS[@]}"; do
  source="${REPO_DIR}/${skill}"
  target="${destination}/${skill}"

  if [ ! -d "$source" ]; then
    echo "  WARN: ${skill} not found in repo, skipping"
    skipped=$((skipped + 1))
    continue
  fi

  # Check if already installed
  if [ -L "$target" ]; then
    # Existing symlink — check if it points to us
    existing="$(readlink "$target")"
    if [ "$MODE" = "symlink" ] && [ "$existing" = "$source" ]; then
      echo "  OK:   ${skill} (already linked)"
      skipped=$((skipped + 1))
      continue
    else
      echo "  UPDATE: ${skill} (replacing symlink)"
      rm "$target"
      updated=$((updated + 1))
    fi
  elif [ -d "$target" ]; then
    if [ "$MODE" = "symlink" ]; then
      echo "  SKIP: ${skill} (directory exists — use --copy to overwrite, or remove manually)"
      skipped=$((skipped + 1))
      continue
    else
      echo "  UPDATE: ${skill} (overwriting)"
      rm -rf "$target"
      updated=$((updated + 1))
    fi
  fi

  if [ "$MODE" = "symlink" ]; then
    ln -s "$source" "$target"
    echo "  LINK: ${target}"
  else
    cp -R "$source" "$target"
    echo "  COPY: ${target}"
  fi
  installed=$((installed + 1))
  done
done

echo ""

# --- Install agent definitions (custom subagent types) ---
mkdir -p "$AGENTS_DIR"
for agent_file in "${REPO_DIR}/agents/"*.md; do
  [ -e "$agent_file" ] || continue
  base="$(basename "$agent_file")"
  target="${AGENTS_DIR}/${base}"

  if [ -L "$target" ]; then
    rm "$target"
  elif [ -f "$target" ] && [ "$MODE" = "symlink" ]; then
    echo "  SKIP: agents/${base} (file exists — use --copy to overwrite, or remove manually)"
    skipped=$((skipped + 1))
    continue
  fi

  if [ "$MODE" = "symlink" ]; then
    ln -s "$agent_file" "$target"
    echo "  LINK: agents/${base}"
  else
    cp "$agent_file" "$target"
    echo "  COPY: agents/${base}"
  fi
  installed=$((installed + 1))
done

echo ""

# --- Hook script (project installs get their own copy; global runs from the repo) ---
if [ -n "$PROJECT_DIR" ]; then
  mkdir -p "${CLAUDE_ROOT}/hooks"
  cp "${REPO_DIR}/hooks/pretooluse.py" "${CLAUDE_ROOT}/hooks/pretooluse.py"
  echo "  COPY: hooks/pretooluse.py"
fi

# --- Manage orchestration blocks in CLAUDE.md and AGENTS.md ---
MARKER_START="# --- Claude Agent Dev Team (managed) ---"
MARKER_END="# --- End Claude Agent Dev Team ---"

manage_instructions_file() {
  local instructions_file="$1"
  local orchestration_path="$2"
  local product="$3"
  local block="${MARKER_START}
# Orchestration discipline — read before spawning agents or doing implementation work.
# This file is managed by install.sh. To update, re-run the installer.
Read ${orchestration_path} before spawning any agent or doing any implementation work.
${MARKER_END}"

if [ -f "$instructions_file" ] && grep -qF "$MARKER_START" "$instructions_file"; then
  # Remove existing managed block first (idempotent update)
  awk '
    /^# --- Claude Agent Dev Team \(managed\) ---$/ { skip=1; next }
    skip && /^# --- End Claude Agent Dev Team ---$/ { skip=0; next }
    !skip { print }
  ' "$instructions_file" > "${instructions_file}.tmp" && mv "${instructions_file}.tmp" "$instructions_file"
fi

# Append managed block (fresh install or after removing old block)
mkdir -p "$(dirname "$instructions_file")"
if [ -f "$instructions_file" ] && [ -s "$instructions_file" ]; then
  # Add a blank line before the block if file doesn't end with one
  [ "$(tail -c 1 "$instructions_file")" != "" ] && echo "" >> "$instructions_file"
  echo "" >> "$instructions_file"
fi
echo "$block" >> "$instructions_file"

if grep -qF "$MARKER_START" "$instructions_file"; then
  echo "  ${product}: orchestration block in ${instructions_file}"
fi
}

manage_instructions_file "$CLAUDE_MD" "$ORCH_PATH" "Claude Code"
manage_instructions_file "$CODEX_MD" "$CODEX_ORCH_PATH" "Codex"

# --- Register PreToolUse enforcement hook ---
python3 - "$SETTINGS_JSON" "$HOOK_CMD" <<'PY'
import json, os, sys

path, cmd = sys.argv[1], sys.argv[2]
settings = {}
if os.path.isfile(path):
    with open(path) as f:
        settings = json.load(f)

entries = settings.setdefault("hooks", {}).setdefault("PreToolUse", [])
# Idempotent: drop any prior registration of our dispatcher, then re-add
entries[:] = [e for e in entries if "pretooluse.py" not in json.dumps(e)]
entries.append({
    "matcher": "Edit|Write|NotebookEdit|Bash|Skill",
    "hooks": [{"type": "command", "command": cmd}],
})

# Merge ask-gate: merge-shaped commands always require a live human click.
# An agent cannot infer merge authorization — retro-mined rule (2026-07).
ask = settings.setdefault("permissions", {}).setdefault("ask", [])
for rule in ("Bash(gh pr merge*)", "Bash(git merge*)"):
    if rule not in ask:
        ask.append(rule)

os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")
print(f"  settings: PreToolUse enforcement hook in {path}")
print(f"  settings: merge ask-gate (gh pr merge / git merge require live approval)")
PY

echo ""
echo "Done!"
echo "  Installed: ${installed}"
echo "  Updated:   ${updated}"
echo "  Skipped:   ${skipped}"
echo "  Retro dir: ${RETRO_DIR}"
echo ""

if [ -n "$PROJECT_DIR" ]; then
  echo "Project-scoped install: the team is available only in ${PROJECT_DIR}."
  echo "Files are copies — after 'git pull' in this repo, re-run:"
  echo "  ./install.sh --project ${PROJECT_DIR}$([ "$LOCAL_SETTINGS" -eq 1 ] && echo " --local")"
  if [ "$LOCAL_SETTINGS" -eq 1 ]; then
    echo ""
    echo "Personal install (--local): add these to the project's .gitignore:"
    echo "  .claude/skills/"
    echo "  .claude/agents/"
    echo "  .claude/hooks/"
    echo "  .claude/settings.local.json"
    echo "  .agents/skills/"
    echo "  AGENTS.md (only if it contains no shared project guidance)"
  else
    echo "Commit .claude/, .agents/, CLAUDE.md, and AGENTS.md to share the team."
  fi
elif [ "$MODE" = "symlink" ]; then
  echo "Skills are symlinked — run 'git pull' in this repo to update them."
  echo "To customize a skill without affecting the repo, copy it manually:"
  echo "  cp -R ${SKILLS_DIR}/<skill> ${SKILLS_DIR}/<skill>-custom"
else
  echo "Skills are copied — changes to the repo won't auto-update."
  echo "Run './install.sh --copy' again after 'git pull' to update."
fi
