#!/usr/bin/env bash
set -euo pipefail

# Claude Agent Dev Team — Uninstaller
# Removes skills installed by install.sh from ~/.claude/ (default)
# or from a project's .claude/ (--project <dir>)

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
else
  CLAUDE_ROOT="${HOME}/.claude"
  CLAUDE_MD="${CLAUDE_ROOT}/CLAUDE.md"
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
for skill in "${SKILLS[@]}"; do
  target="${SKILLS_DIR}/${skill}"
  if [ -L "$target" ] || [ -d "$target" ]; then
    found=$((found + 1))
  fi
done

if [ "$found" -eq 0 ]; then
  echo "Nothing to uninstall — no Claude Agent Dev Team skills found in ${SKILLS_DIR}"
  exit 0
fi

echo "Found ${found} installed skill(s) in ${SKILLS_DIR}"
echo ""

if [ "$ASSUME_YES" -ne 1 ]; then
  read -rp "Remove all Claude Agent Dev Team skills? [y/N] " confirm
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi
fi

echo ""
echo "Uninstalling Claude Agent Dev Team skills..."
removed=0
for skill in "${SKILLS[@]}"; do
  target="${SKILLS_DIR}/${skill}"
  if [ -L "$target" ] || [ -d "$target" ]; then
    rm -rf "$target"
    echo "  Removed: $skill"
    removed=$((removed + 1))
  fi
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

# --- Remove managed block from CLAUDE.md ---
MARKER_START="# --- Claude Agent Dev Team (managed) ---"
MARKER_END="# --- End Claude Agent Dev Team ---"

if [ -f "$CLAUDE_MD" ] && grep -qF "$MARKER_START" "$CLAUDE_MD"; then
  awk -v start="$MARKER_START" -v end="$MARKER_END" '
    $0 == start { skip=1; next }
    skip && $0 == end { skip=0; next }
    !skip { print }
  ' "$CLAUDE_MD" > "${CLAUDE_MD}.tmp" && mv "${CLAUDE_MD}.tmp" "$CLAUDE_MD"
  # Remove file if it's now empty (only whitespace)
  if [ ! -s "$CLAUDE_MD" ] || ! grep -q '[^[:space:]]' "$CLAUDE_MD" 2>/dev/null; then
    rm -f "$CLAUDE_MD"
    echo "  Removed: ${CLAUDE_MD} (was empty after cleanup)"
  else
    echo "  Cleaned: ${CLAUDE_MD} (removed managed block, preserved other content)"
  fi
fi

# --- Remove PreToolUse enforcement hook from settings (both variants) ---
for settings_file in "${CLAUDE_ROOT}/settings.json" "${CLAUDE_ROOT}/settings.local.json"; do
  if [ -f "$settings_file" ] && grep -qF "pretooluse.py" "$settings_file"; then
    python3 - "$settings_file" <<'PY'
import json, sys

path = sys.argv[1]
with open(path) as f:
    settings = json.load(f)

entries = settings.get("hooks", {}).get("PreToolUse", [])
entries[:] = [e for e in entries if "pretooluse.py" not in json.dumps(e)]
if not entries:
    settings["hooks"].pop("PreToolUse", None)
if not settings.get("hooks"):
    settings.pop("hooks", None)

with open(path, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")
print(f"  Cleaned: PreToolUse enforcement hook removed from {path}")
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
  rmdir "$SKILLS_DIR" "$AGENTS_DIR" "$CLAUDE_ROOT" 2>/dev/null || true
fi

echo ""
echo "Done. Removed ${removed} skill(s) from ${SKILLS_DIR}"
echo "Note: ${RETRO_DIR} was not removed (may contain your retrospectives)"
