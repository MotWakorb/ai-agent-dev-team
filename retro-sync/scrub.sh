#!/usr/bin/env bash
# Scrub sensitive data from retro markdown files before pushing to the public retros repo.
# Usage: scrub.sh [dir]   (default: ~/retros)
# Optional denylist:    ~/.claude/retro-scrub.txt       — one literal string per line, replaced with [REDACTED]
# Optional project map: ~/.claude/retro-project-map.txt — "real-name=pseudonym" per line, stable pseudonymization
set -euo pipefail

DIR="${1:-$HOME/retros}"
DENYLIST="$HOME/.claude/retro-scrub.txt"
PROJECT_MAP="$HOME/.claude/retro-project-map.txt"
changed=0

for f in "$DIR"/*.md; do
  [ -e "$f" ] || continue
  case "$(basename "$f")" in README.md) continue ;; esac  # corpus README names real public repos on purpose
  before=$(cksum "$f")
  perl -0pi -e '
    s/-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----/[PRIVATE-KEY]/gs;
    s/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/[EMAIL]/g;
    s/\b(?:\d{1,3}\.){3}\d{1,3}\b/[IP]/g;
    s/\bAKIA[0-9A-Z]{16}\b/[AWS-KEY]/g;
    s/\bgh[pousr]_[A-Za-z0-9]{20,}\b/[GH-TOKEN]/g;
    s/\bgithub_pat_[A-Za-z0-9_]{20,}\b/[GH-TOKEN]/g;
    s/\bsk-ant-[A-Za-z0-9-]{20,}\b/[API-KEY]/g;
    s/\bsk-[A-Za-z0-9]{20,}\b/[API-KEY]/g;
    s/\bxox[baprs]-[A-Za-z0-9-]{10,}\b/[SLACK-TOKEN]/g;
    s/\b(Bearer|bearer) [A-Za-z0-9._~+\/-]{16,}=*/Bearer [TOKEN]/g;
  ' "$f"
  if [ -f "$PROJECT_MAP" ]; then
    while IFS='=' read -r real pseudo; do
      [ -n "$real" ] && [ -n "$pseudo" ] || continue
      perl -pi -e 's/\Q'"$real"'\E/'"$pseudo"'/gi' "$f"
    done < "$PROJECT_MAP"
  fi
  if [ -f "$DENYLIST" ]; then
    while IFS= read -r term; do
      [ -n "$term" ] || continue
      perl -pi -e 's/\Q'"$term"'\E/[REDACTED]/gi' "$f"
    done < "$DENYLIST"
  fi
  # pseudonymize project names appearing in the filename itself
  newname=$(basename "$f")
  if [ -f "$PROJECT_MAP" ]; then
    while IFS='=' read -r real pseudo; do
      [ -n "$real" ] && [ -n "$pseudo" ] || continue
      newname=$(printf '%s' "$newname" | perl -pe 's/\Q'"$real"'\E/'"$pseudo"'/gi')
    done < "$PROJECT_MAP"
  fi
  if [ "$newname" != "$(basename "$f")" ]; then
    mv "$f" "$DIR/$newname"
    echo "renamed: $(basename "$f") -> $newname"
    f="$DIR/$newname"
    changed=$((changed + 1))
  elif [ "$before" != "$(cksum "$f")" ]; then
    echo "scrubbed: $(basename "$f")"
    changed=$((changed + 1))
  fi
done

echo "scrub complete: $changed file(s) modified"
