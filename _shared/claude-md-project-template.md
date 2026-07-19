# Project CLAUDE.md Template

Template for the managed block `/onboard` offers to write into a project's `CLAUDE.md` (Step 3e). It records the per-project facts personas need every session but can't reliably derive — gates, branching, board, deploy. It does NOT restate orchestration or engineering discipline; those load globally via the installer's `~/.claude/CLAUDE.md` block.

Rules for the block:

- Append to an existing `CLAUDE.md`; never overwrite content outside the markers. Re-running `/onboard` replaces only the marked block (same pattern as install.sh).
- Fill every slot from what onboarding actually observed, and confirm with the PO. Delete lines that don't apply — an empty slot is noise every session.
- Keep it under ~15 lines. This loads into every session in the project; each line must earn its tokens.

```markdown
# --- AI Agent Dev Team (project) ---
# Managed by /onboard. Re-run /onboard to update this block.
This project is run by the AI Agent Dev Team.

- **Tiers**: `COMPONENTS.md` at the repo root is the deployment-tier authority — read it before calibrating rigor.
- **Board**: [beads (`bd`) | GitHub issues | other — where work is tracked]
- **Gates**: [exact test / lint / build commands, e.g. `pytest -q` · `ruff check .` · `npm run build`]
- **Branching**: [convention, e.g. `feat/<bead-id>-slug`]; PRs target `[branch]`. Merge authority: PO only.
- **Deploy**: [how and where it deploys, who or what triggers it]
- **Off-limits without PO sign-off**: [paths, environments, or systems — delete if none]
# --- End AI Agent Dev Team (project) ---
```
