#!/usr/bin/env bash
set -euo pipefail

# AI Agent Dev Team — Claude Code + Codex Uninstaller

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR=""
ASSUME_YES=0

while [ $# -gt 0 ]; do
  case $1 in
    --yes|-y)
      ASSUME_YES=1
      ;;
    --project)
      shift
      [ $# -gt 0 ] || { echo "ERROR: --project requires a path" >&2; exit 1; }
      PROJECT_DIR="$1"
      ;;
    --help|-h)
      echo "Usage: ./uninstall.sh [--yes] [--project <dir>]"
      exit 0
      ;;
    *)
      echo "ERROR: unknown option: $1" >&2
      exit 1
      ;;
  esac
  shift
done

if [ -n "$PROJECT_DIR" ]; then
  [ -d "$PROJECT_DIR" ] || { echo "ERROR: ${PROJECT_DIR} is not a directory" >&2; exit 1; }
  PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
  CLAUDE_ROOT="${PROJECT_DIR}/.claude"
  CLAUDE_MD="${PROJECT_DIR}/CLAUDE.md"
  CODEX_SKILLS_DIR="${PROJECT_DIR}/.agents/skills"
  CODEX_MD="${PROJECT_DIR}/AGENTS.md"
  CODEX_ROOT="${PROJECT_DIR}/.codex"
  CODEX_HOOKS_JSON="${CODEX_ROOT}/hooks.json"
else
  CLAUDE_ROOT="${HOME}/.claude"
  CLAUDE_MD="${CLAUDE_ROOT}/CLAUDE.md"
  CODEX_SKILLS_DIR="${HOME}/.agents/skills"
  CODEX_ROOT="${CODEX_HOME:-${HOME}/.codex}"
  CODEX_MD="${CODEX_ROOT}/AGENTS.md"
  CODEX_HOOKS_JSON="${CODEX_ROOT}/hooks.json"
fi

SKILLS_DIR="${CLAUDE_ROOT}/skills"
AGENTS_DIR="${CLAUDE_ROOT}/agents"
RETRO_DIR="${HOME}/retros"

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

# Check if anything is installed
found=0
for destination in "$SKILLS_DIR" "$CODEX_SKILLS_DIR"; do
  for skill in "${SKILLS[@]}"; do
    target="${destination}/${skill}"
    if [ -L "$target" ] || [ -d "$target" ]; then
      found=$((found + 1))
    fi
  done
done

if [ "$found" -eq 0 ]; then
  echo "No AI Agent Dev Team skills found in ${SKILLS_DIR}; checking for managed residue."
else
  echo "Found ${found} installed skill(s) in ${SKILLS_DIR}"
  echo ""
fi

if [ "$found" -gt 0 ] && [ "$ASSUME_YES" -ne 1 ]; then
  read -rp "Remove all AI Agent Dev Team skills? [y/N] " confirm
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi
fi

echo ""
echo "Uninstalling AI Agent Dev Team skills from Claude Code and Codex..."
removed=0
for destination in "$SKILLS_DIR" "$CODEX_SKILLS_DIR"; do
  for skill in "${SKILLS[@]}"; do
    target="${destination}/${skill}"
    if [ -L "$target" ] || [ -d "$target" ]; then
      rm -rf "$target"
      echo "  Removed: $target"
      removed=$((removed + 1))
    fi
  done
done

# --- Remove agent definitions installed from this repo's agents/ ---
for agent_file in "${REPO_DIR}/agents/"*.md; do
  [ -e "$agent_file" ] || continue
  target="${AGENTS_DIR}/$(basename "$agent_file")"
  if [ -L "$target" ] || [ -f "$target" ]; then
    rm -f "$target"
    echo "  Removed: agents/$(basename "$agent_file")"
  fi
done

# --- Remove hook script copy (project installs only) ---
if [ -n "$PROJECT_DIR" ] && [ -f "${CLAUDE_ROOT}/hooks/pretooluse.py" ]; then
  rm -f "${CLAUDE_ROOT}/hooks/pretooluse.py"
  rmdir "${CLAUDE_ROOT}/hooks" 2>/dev/null || true
  echo "  Removed: hooks/pretooluse.py"
fi
if [ -n "$PROJECT_DIR" ] && [ -f "${CODEX_ROOT}/hooks/pretooluse.py" ]; then
  rm -f "${CODEX_ROOT}/hooks/pretooluse.py"
  rmdir "${CODEX_ROOT}/hooks" 2>/dev/null || true
  echo "  Removed: .codex/hooks/pretooluse.py"
fi

# --- Remove managed block from CLAUDE.md ---
MARKER_START="# --- AI Agent Dev Team (managed) ---"
MARKER_END="# --- End AI Agent Dev Team ---"
LEGACY_MARKER_START="# --- Claude Agent Dev Team (managed) ---"

for instructions_file in "$CLAUDE_MD" "$CODEX_MD"; do
  if [ -f "$instructions_file" ] &&
     { grep -qF "$MARKER_START" "$instructions_file" || grep -qF "$LEGACY_MARKER_START" "$instructions_file"; }; then
    awk '
      /^# --- (AI|Claude) Agent Dev Team \(managed\) ---$/ { skip=1; next }
      skip && /^# --- End (AI|Claude) Agent Dev Team ---$/ { skip=0; next }
      !skip { print }
    ' "$instructions_file" > "${instructions_file}.tmp" && mv "${instructions_file}.tmp" "$instructions_file"
    # Remove file if it's now empty (only whitespace)
    if [ ! -s "$instructions_file" ] || ! grep -q '[^[:space:]]' "$instructions_file" 2>/dev/null; then
      rm -f "$instructions_file"
      echo "  Removed: ${instructions_file} (was empty after cleanup)"
    else
      echo "  Cleaned: ${instructions_file} (removed managed block, preserved other content)"
    fi
  fi
done

# --- Remove Codex PreToolUse enforcement hook ---
if [ -f "$CODEX_HOOKS_JSON" ] && grep -qF "pretooluse.py" "$CODEX_HOOKS_JSON"; then
  python3 - "$CODEX_HOOKS_JSON" <<'PY'
import json, sys

path = sys.argv[1]
with open(path) as f:
    config = json.load(f)
entries = config.get("hooks", {}).get("PreToolUse", [])
entries[:] = [e for e in entries if "pretooluse.py" not in json.dumps(e)]
if not entries:
    config.get("hooks", {}).pop("PreToolUse", None)
if not config.get("hooks"):
    config.pop("hooks", None)
with open(path, "w") as f:
    json.dump(config, f, indent=2)
    f.write("\n")
print(f"  Cleaned: Codex PreToolUse hook removed from {path}")
PY
fi

# --- Remove PreToolUse enforcement hook from settings (both variants) ---
for settings_file in "${CLAUDE_ROOT}/settings.json" "${CLAUDE_ROOT}/settings.local.json"; do
  if [ -f "$settings_file" ]; then
    python3 - "$settings_file" <<'PY'
import json, sys

path = sys.argv[1]
with open(path) as f:
    settings = json.load(f)

if not isinstance(settings, dict):
    print(f"  Preserved: {path} (top-level settings value is not an object)")
    raise SystemExit(0)

hooks = settings.get("hooks")
if isinstance(hooks, dict):
    entries = hooks.get("PreToolUse")
    if isinstance(entries, list):
        hooks["PreToolUse"] = [
            entry for entry in entries
            if "pretooluse.py" not in json.dumps(entry)
        ]
        if not hooks["PreToolUse"]:
            hooks.pop("PreToolUse", None)
    if not hooks:
        settings.pop("hooks", None)

permissions = settings.get("permissions")
if isinstance(permissions, dict):
    ask = permissions.get("ask")
    if isinstance(ask, list):
        managed = {"Bash(gh pr merge*)", "Bash(git merge*)"}
        permissions["ask"] = [rule for rule in ask if rule not in managed]
        if not permissions["ask"]:
            permissions.pop("ask", None)
    if not permissions:
        settings.pop("permissions", None)

with open(path, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")
print(f"  Cleaned: managed enforcement hook and merge ask rules removed from {path}")
PY
  fi
done

# --- Project mode: tidy now-empty husks so .claude/ disappears if we created it ---
if [ -n "$PROJECT_DIR" ]; then
  for settings_file in "${CLAUDE_ROOT}/settings.json" "${CLAUDE_ROOT}/settings.local.json"; do
    if [ -f "$settings_file" ] && [ "$(tr -d '[:space:]' < "$settings_file")" = "{}" ]; then
      rm -f "$settings_file"
    fi
  done
  if [ -f "$CODEX_HOOKS_JSON" ] && [ "$(tr -d '[:space:]' < "$CODEX_HOOKS_JSON")" = "{}" ]; then
    rm -f "$CODEX_HOOKS_JSON"
  fi
  rmdir "$SKILLS_DIR" "$AGENTS_DIR" "$CLAUDE_ROOT" "$CODEX_SKILLS_DIR" "${PROJECT_DIR}/.agents" "$CODEX_ROOT" 2>/dev/null || true
fi

echo ""
echo "Done. Removed ${removed} skill installation(s)."
echo "Note: ${RETRO_DIR} was not removed (may contain your retrospectives)"
