#!/usr/bin/env bash
set -euo pipefail

# Claude Agent Dev Team — Installer
# Symlinks skills into ~/.claude/skills/ so git pull updates automatically
# Use --copy to copy instead of symlink (for customization)

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="${HOME}/.claude/skills"
RETRO_DIR="${HOME}/retros"
MODE="symlink"

# Parse flags
for arg in "$@"; do
  case $arg in
    --copy)
      MODE="copy"
      shift
      ;;
    --help|-h)
      echo "Usage: ./install.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  (default)    Symlink skills into ~/.claude/skills/ (git pull updates automatically)"
      echo "  --copy       Copy skills instead of symlink (for customization)"
      echo "  --help       Show this help"
      exit 0
      ;;
  esac
done

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
  team-plan
  team-review
  standup
  grooming
  spike
  postmortem
  onboard
  release-check
)

echo "Installing Claude Agent Dev Team skills..."
echo "  Mode: ${MODE}"
echo "  From: ${REPO_DIR}"
echo "  To:   ${SKILLS_DIR}"
echo ""

# Create skills directory if it doesn't exist
mkdir -p "$SKILLS_DIR"

# Create retro directory
mkdir -p "$RETRO_DIR"

# Track results
installed=0
skipped=0
updated=0

for skill in "${SKILLS[@]}"; do
  source="${REPO_DIR}/${skill}"
  target="${SKILLS_DIR}/${skill}"

  if [ ! -d "$source" ]; then
    echo "  WARN: ${skill} not found in repo, skipping"
    skipped=$((skipped + 1))
    continue
  fi

  # Check if already installed
  if [ -L "$target" ]; then
    # Existing symlink — check if it points to us
    existing="$(readlink "$target")"
    if [ "$existing" = "$source" ]; then
      echo "  OK:   ${skill} (already linked)"
      skipped=$((skipped + 1))
      continue
    else
      echo "  UPDATE: ${skill} (repointing symlink)"
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
    echo "  LINK: ${skill}"
  else
    cp -R "$source" "$target"
    echo "  COPY: ${skill}"
  fi
  installed=$((installed + 1))
done

echo ""

# --- Manage ~/.claude/CLAUDE.md orchestration block ---
CLAUDE_MD="${HOME}/.claude/CLAUDE.md"
MARKER_START="# --- Claude Agent Dev Team (managed) ---"
MARKER_END="# --- End Claude Agent Dev Team ---"

BLOCK="${MARKER_START}
# Orchestration discipline — read before spawning agents or doing implementation work.
# This file is managed by install.sh. To update, re-run the installer.
Read ~/.claude/skills/_shared/orchestration.md before spawning any agent or doing any implementation work.
${MARKER_END}"

if [ -f "$CLAUDE_MD" ] && grep -qF "$MARKER_START" "$CLAUDE_MD"; then
  # Remove existing managed block first (idempotent update)
  awk '
    /^# --- Claude Agent Dev Team \(managed\) ---$/ { skip=1; next }
    skip && /^# --- End Claude Agent Dev Team ---$/ { skip=0; next }
    !skip { print }
  ' "$CLAUDE_MD" > "${CLAUDE_MD}.tmp" && mv "${CLAUDE_MD}.tmp" "$CLAUDE_MD"
fi

# Append managed block (fresh install or after removing old block)
if [ -f "$CLAUDE_MD" ] && [ -s "$CLAUDE_MD" ]; then
  # Add a blank line before the block if file doesn't end with one
  [ "$(tail -c 1 "$CLAUDE_MD")" != "" ] && echo "" >> "$CLAUDE_MD"
  echo "" >> "$CLAUDE_MD"
fi
echo "$BLOCK" >> "$CLAUDE_MD"

if grep -qF "$MARKER_START" "$CLAUDE_MD"; then
  echo "  CLAUDE.md: orchestration block in ${CLAUDE_MD}"
fi

echo ""
echo "Done!"
echo "  Installed: ${installed}"
echo "  Updated:   ${updated}"
echo "  Skipped:   ${skipped}"
echo "  Retro dir: ${RETRO_DIR}"
echo ""

if [ "$MODE" = "symlink" ]; then
  echo "Skills are symlinked — run 'git pull' in this repo to update them."
  echo "To customize a skill without affecting the repo, copy it manually:"
  echo "  cp -R ${SKILLS_DIR}/<skill> ${SKILLS_DIR}/<skill>-custom"
else
  echo "Skills are copied — changes to the repo won't auto-update."
  echo "Run './install.sh --copy' again after 'git pull' to update."
fi
