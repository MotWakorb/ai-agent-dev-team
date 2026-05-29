# Changelog

All notable changes to this project are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) at the system level.

Each `SKILL.md` carries a `version:` field in its frontmatter showing the system version it last meaningfully changed in. To check what's installed: `grep -E "^name:|^version:" ~/.claude/skills/*/SKILL.md`.

## [Unreleased]

Second-wave retro-driven rule additions (7 retros, 2026-05-17 → 2026-05-29). Tightens reviewer sub-agent discipline, introduces verification-against-the-live-surface as a tier-invariant rule, codifies "no orchestrator-finish" on mid-run termination, and adds a recurring-regression test-strategy pattern.

### Added
- **`code-reviewer/SKILL.md` §"Tool Discipline When Spawned as Sub-Agent"** — read-only effective tool set when dispatched as a review sub-agent. Explicitly forbids `Edit`/`Write`/`NotebookEdit` and state-mutating Bash regardless of inherited tool access. Brief-level instruction is the fence.
- **`code-reviewer/SKILL.md` §"PR Review Summary"** — verdict header must match body severity. `Approved`-class headers reserved for non-blocking observations; any blocker in the body requires `Changes Requested` or `Blocked`. Downstream readers and orchestrators key on the header for merge decisions.
- **`qa-engineer/SKILL.md` §"When Spawned as a Review Sub-Agent"** — combined tool discipline + verdict-header rule for QA when invoked in review mode (`/team-review`, `/release-check`, or direct dispatch).
- **`qa-engineer/SKILL.md` §"Recurring Regressions Are a Test-Strategy Signal"** — when the same surface regresses across 3+ rounds with unit tests green, the missing layer is integration-with-real-data. Golden-fixture end-to-end tests and parity/boundary tests as the response, not more unit tests.
- **`_shared/engineering-discipline.md` §"Persisted and Live-Surface Verification"** (subsection of Verification of Completion) — for reporting/integration bugs, inspect the persisted artifact and trace `compute → persist → serialize → format` before editing the compute layer. Synthetic verification (hand-built inputs to one function) produces false confidence; live verification requires the real surface.
- **`_shared/engineering-discipline.md` §"Stage Unvalidated Fixes"** — when a fix is speculative and shipped alongside instrumentation, ship instrumentation alone first so the next data round can isolate variables. Bead state for unvalidated fixes must be distinguishable from closed-and-proven.
- **`_shared/orchestration.md` §"Mid-run termination is not orchestrator-finish authorization"** (subsection of Claude Orchestrates — Personas Implement) — when a persona sub-agent terminates mid-run with uncommitted work, the orchestrator re-dispatches the persona; it does NOT commit, push, or finalize the persona's pending work itself.
- **`_shared/orchestration.md` §"Reviewer briefs require explicit tool discipline"** (subsection of Worktree Isolation) — verbatim brief language requiring read-only operations for any persona dispatched in review mode. Pair to the `code-reviewer`/`qa-engineer` SKILL-level discipline.

### Changed
- **`_shared/orchestration.md` §"Verify Premises Before Briefing"** — added two data-check bullets: post-disconnect / post-gap re-verify (re-query board and PR state after any context gap before forwarding to the next agent) and HEAD-over-working-tree (verify briefs that assert "engineer's pushed code does/doesn't X" against `git show HEAD:<file>`, not the working tree).

## [0.3.0]

Orchestration discipline upgrades from retro analysis (18 sessions, 2026-04-19 → 2026-05-14). New `/release-check` skill, expanded orchestrator rules, and a pre-existing-failure escalation clause.

### Added
- **`/release-check` skill** — pre-release semantic readiness check. Verifies open P0/P1 bugs in sprint scope, in-flight verification agents, open PRs targeting the release branch, and security gate state. Produces a checklist for PO confirmation and refuses to fire release-execution without explicit go.
- **`_shared/orchestration.md` §"Authorization Verbs"** — verb-mapping table ("ship it" → push+PR, "merge it" → merge, "go" → execute the immediately-prior proposed action) and rule for catch-all instructions vs flagged decisions.
- **`_shared/orchestration.md` §"Findings From Personas Are Notes, Not Beads"** — orchestrator-level rule against filing beads on persona-surfaced sibling concerns without PO authorization.
- **`_shared/orchestration.md` §"Re-Verify Gates on Engineer Report"** — engineer's "gates green" report is the start of verification, not the end; orchestrator re-runs gates against the merged or worktree state before declaring done.
- **`_shared/orchestration.md` §"Definition of Done for User-Reported Bugs"** — merged ≠ deployed ≠ reporter notified ≠ reporter confirmed.

### Changed
- **`_shared/orchestration.md` §"Claude Orchestrates — Personas Implement"** — rewritten around "skills define each persona's scope." Adds hard limit of 3 pre-dispatch reads, explicit orchestrator-territory vs persona-territory enumeration (durable artifacts are always persona work, including bead descriptions, ADRs, in-repo docs), named-rationalization rejections, and a mid-task drift clause.
- **`_shared/orchestration.md` §"Worktree Isolation for Write-Mode Agents"** — trigger expanded from "will commit" to "might commit." New subsections: orchestrator-self discipline (verify `pwd`/`branch`/`status` before destructive git ops; delegate cleanup to engineer when parallel agents are running) and CWD drift (prefer absolute paths over `cd` chains).
- **`_shared/orchestration.md` §"Verify Premises Before Briefing"** — added framing checks (source/environment, already-shipped, inherited premise) alongside the existing data checks (pagination, child counts, status). Default assumption for user reports is now "customer in production."
- **`_shared/orchestration.md` §"Decision Prompts"** (renamed from "Decision Prompt Compression") — structured `## DECISIONS NEEDED` block at end of message, dependency notation, hard cap of 3 decisions per message, one-by-one mode for complex decisions.
- **`_shared/engineering-discipline.md` §"Pre-Existing Failures Are Not Background Noise"** — added escalation clause: pre-existing failures recurring across sessions escalate to RED at the next standup.

## [0.2.0]

Tier-aware personas, per-task model selection, and explicit versioning.

### Added
- `_shared/deployment-tier.md` — defines four deployment tiers (`home-lab`, `small-team`, `startup`, `enterprise`) and per-persona calibration tables. Personas read this and the project's `COMPONENTS.md` to right-size recommendations to the deployment context.
- `COMPONENTS.md` (per-project artifact) produced by `/onboard`. Lists each component in the project with its deployment tier. Required for the team ceremonies to run.
- New Step 3 in `/onboard` — Component Inventory & Tier Confirmation. The IT Architect drafts a component list with proposed tiers; other personas contribute tier signals; the PO confirms; `COMPONENTS.md` is written.
- **Preflight check** in `/team-plan`, `/team-review`, `/standup`, `/grooming`, `/spike`, `/postmortem` — refuse to run if `COMPONENTS.md` is missing, directing the user to `/onboard`.
- **Cross-tier resolution rule** — when work spans components at different tiers, strictest tier wins by default. Surface as a decision when applying it across the board would be clearly wasteful.
- **Agent Model Selection** section in `_shared/orchestration.md` — per-task-type model assignments (`haiku` for triage, `sonnet` for most domain work, `opus` for sticky decisions). Tier modulation: home-lab effective tier downshifts one level *except* for security-engineer.
- `model:` field in every persona `SKILL.md` frontmatter (default `sonnet`) — declares the persona's default when invoked directly.
- `version:` field in every `SKILL.md` frontmatter — echoes the system version the skill last changed in.
- README sections: "Project Onboarding (Required Before Team Skills Run)", "Tier-Aware Personas", "Per-Task Model Selection", "Versioning & Rollback".
- `CHANGELOG.md` (this file).
- `CONTRIBUTING.md` updates: documented `model:` and `version:` frontmatter, semver policy, and per-skill version bump expectations.

### Changed
- Persona "Hard Rules" sections in `sre/`, `technical-writer/`, `qa-engineer/`, `database-engineer/`, `it-architect/` reframed from absolute (`No exceptions`) to tier-conditional. Maximum-rigor wording preserved as the *enterprise-tier* baseline; lower tiers documented per-rule.
- Persona preambles (sre, technical-writer, qa-engineer, database-engineer, it-architect) now reference `_shared/deployment-tier.md` and instruct the persona to read `COMPONENTS.md` before producing recommendations.
- `/standup` agent prompts now instruct personas to rate R/Y/G against each component's own tier — a home-lab service is not RED for missing enterprise practices.
- Single-persona invocations (`/sre`, etc.) ask which tier the work is for if `COMPONENTS.md` doesn't cover the in-scope component.

### Tier-Invariant Behavior (Unchanged)
- Critical security findings (CVSS 9.0+) remain non-negotiable at every tier. The CVE in a home-lab service is still a CVE.
- Engineering Discipline (`_shared/engineering-discipline.md`), the Conflict Resolution Protocol, naming discipline, the value gate, and AI-realistic effort estimates apply at every tier.
- Vendor portability and open-source-tooling rules in `it-architect/` remain tier-invariant.

## [0.1.0]

Initial release. Baseline of the Claude Agent Dev Team — 10 personas with domain authority, professional biases, and conflict-resolution protocols, plus eight ceremonies (`/team-plan`, `/team-review`, `/standup`, `/grooming`, `/spike`, `/postmortem`, `/onboard`, `/retro`). See [README.md](./README.md) for the feature list as of this release.

[Unreleased]: https://github.com/MotWakorb/claude-agent-dev-team/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/MotWakorb/claude-agent-dev-team/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/MotWakorb/claude-agent-dev-team/releases/tag/v0.1.0
