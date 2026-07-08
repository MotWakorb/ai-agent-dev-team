# Contributing

Thanks for your interest in contributing to the Claude Agent Dev Team. Whether you want to improve an existing persona, add a new one, or refine a ceremony — contributions are welcome.

## How to Contribute

1. Fork the repo and create a branch from `main`
2. Make your changes (see guidelines below)
3. Open a pull request with a clear description of what changed and why

## Adding a New Persona

Each persona lives in its own directory with two files:

```
my-persona/
├── SKILL.md       # Full domain expertise, methodology, and activities
└── identity.md    # Brief identity card used for fast-load contexts (standups)
```

### SKILL.md

Start with YAML frontmatter:

```yaml
---
name: my-persona
description: One-line summary of the role and its focus area.
when_to_use: comma, separated, keywords, that, trigger, this, persona
user-invocable: true
model: sonnet              # default model for direct invocation; orchestrators may override
version: 0.2.0             # system version this skill last changed in
---
```

`model:` declares the persona's default model when invoked directly (`/my-persona ...`). Skill orchestrators (team-plan, standup, etc.) override per task type — see `_shared/orchestration.md` "Agent Model Selection." Most personas default to `sonnet`.

`version:` is an echo of the system semver this skill last meaningfully changed in. When you make a meaningful change, bump it to the next system version you expect to ship (or leave it for the maintainer to update at release time).

Then the body should include:

- **Preamble** — role title, reference to `../_shared/engineering-discipline.md`
- **Philosophy** — what this persona believes about their domain
- **Domain authority** — what decisions they own
- **Professional biases** — what they advocate for, what they're skeptical of
- **Methodology / Activities** — how they actually do the work
- **Output format** — what their analysis looks like when spawned as an agent

Look at any existing persona (e.g., `sre/SKILL.md`, `security-engineer/SKILL.md`) for the pattern.

### identity.md

A brief file used when the full SKILL.md isn't needed (e.g., standup triage). Structure:

```markdown
# [Role Name] — Identity

One-paragraph description of who this persona is and what they protect or deliver.

## Domain Authority
What they own. One paragraph.

## Professional Biases
Bulleted list of strong opinions and skepticisms.

## Standup Triggers
- **RED**: Conditions that mean something is broken or at risk right now
- **YELLOW**: Conditions that need attention soon
```

### Design Principles for Personas

These are the things that make personas in this project work well:

- **Give them a real bias.** A persona that hedges everything is useless. The Security Engineer should fight for security. The SRE should fight for reliability. The tension between personas is the point.
- **Define what they own.** Domain authority prevents personas from stepping on each other. Be explicit about what decisions belong to this role.
- **Define what they defer.** Equally important — a persona that has opinions about everything is just another generalist.
- **Include failure modes.** LLMs have specific tendencies (subsampling, theorizing before reading, premature agreement). Call these out so the persona actively resists them.
- **Reference shared foundations.** Every persona should follow `_shared/engineering-discipline.md` and participate in `_shared/conflict-resolution.md`.

### Integrating with Ceremonies

If you add a new persona, the existing ceremonies won't automatically include it. For a persona to participate in team ceremonies, you'll need to update the ceremony files that should include it:

- `team-plan/SKILL.md` — parallel planning sessions
- `team-review/SKILL.md` — full team code/design review
- `standup/SKILL.md` — daily pulse check
- `onboard/SKILL.md` — project assessment

Not every persona needs to be in every ceremony. Use judgment — a specialized role might only participate in `team-plan` and `team-review`.

## Modifying an Existing Persona

- Update both `SKILL.md` and `identity.md` to stay in sync
- Maintain the persona's voice and bias — don't sand down the edges
- If you change domain authority boundaries, check for conflicts with other personas and update `_shared/conflict-resolution.md` if needed

## Modifying Ceremonies

Ceremonies live in their own directories with a single `SKILL.md`. They orchestrate personas through a structured workflow. When modifying:

- Follow the existing step structure (Step 0, Step 1, etc.)
- Include agent spawning prompt templates — these are the exact prompts sent to each persona
- Define clear output format and success criteria
- Test with the relevant personas to make sure prompts produce useful output

## Agent Definitions

`agents/` holds custom subagent types installed to `~/.claude/agents/` (or `<project>/.claude/agents/` for `--project` installs) by install.sh — e.g., `persona-reviewer`, the read-only dispatch target for personas in review/analysis mode. These are Claude Code agent definitions: YAML frontmatter (`name`, `description`, `tools`, `model`) plus a short system prompt. Keep them thin — persona identity comes from the dispatch prompt, not the agent definition, so each persona keeps a single source of truth in its SKILL.md.

## Enforcement Hooks

`hooks/pretooluse.py` is the PreToolUse dispatcher install.sh registers in settings.json. It enforces only mechanically decidable rules (orchestrator edit block, ceremony gate, persona bead firewall, bead-referenced commits) — judgment calls stay in `_shared/orchestration.md` as prose. Two rules for changes:

- **Run the self-check after any edit**: `python3 hooks/pretooluse.py --check`. Add an assertion for every new rule or exemption — the check is the only automated verification the hook gets.
- **Fail open.** The hook must never block on its own bugs — malformed input, missing fields, and unrecognized tools all return silently. A broken enforcement hook that denies everything is worse than no hook.

Stdlib-only Python 3; no dependencies. Project-scoped installs get a copy at `.claude/hooks/pretooluse.py`, so hook changes reach project installs only when the installer is re-run.

## Modifying Shared Foundations

Changes to `_shared/conflict-resolution.md` or `_shared/engineering-discipline.md` affect every persona. Be deliberate — these are the rules of engagement for the whole team.

## Style Guide

- **Directories**: lowercase kebab-case (`database-engineer`, not `DatabaseEngineer`)
- **Skill files**: always `SKILL.md` (uppercase)
- **Identity files**: always `identity.md` (lowercase)
- **Tone**: direct, professional, opinionated. These aren't documentation — they're role definitions that give an LLM permission to have a strong point of view
- **Evidence over assertion**: if a persona claims something matters, explain why

## What Makes a Good Contribution

- Fills a genuine gap in team coverage (e.g., a DevOps Engineer, Data Engineer, or Accessibility Specialist)
- Sharpens an existing persona's domain expertise with real-world methodology
- Improves ceremony flow based on actual usage experience
- Fixes conflicts or gaps in the shared foundations

## What to Avoid

- Personas that overlap heavily with existing ones without clear differentiation
- Removing or softening a persona's bias — the disagreements are features, not bugs
- Adding personas that don't have a clear domain authority boundary
- Changes that break the `_shared/` contract without updating all affected personas

## Versioning

This project uses semantic versioning at the system level. Releases are tagged in git (`v0.1.0`, `v0.2.0`, ...) and tracked in [CHANGELOG.md](./CHANGELOG.md).

- **MAJOR** (`v1.0.0` → `v2.0.0`): Breaking changes — frontmatter format changes, skill removals, behavioral changes that require user action
- **MINOR** (`v0.2.0` → `v0.3.0`): New skills, new shared docs, new persona capabilities, additive changes to skill behavior
- **PATCH** (`v0.2.0` → `v0.2.1`): Bug fixes, doc fixes, no behavioral change

Each `SKILL.md` carries a `version:` field showing the system version it last meaningfully changed in. Bump it in your PR if you make a meaningful change.

Update `CHANGELOG.md` in the same PR. Use [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format. The maintainer tags releases.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
