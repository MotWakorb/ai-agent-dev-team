---
name: release-check
description: Pre-release semantic readiness check. Verifies P0/P1 bugs are clear, in-flight verification agents have completed, and the PO has explicitly confirmed before any release-execution agent fires.
when_to_use: pre-release check, release readiness, release gate, cut a release, ship a release, ready to release
user-invocable: true
version: 0.3.0
---

# Release Readiness Check

Release-execution agents fire on mechanical triggers ("PRs merged, branch protection on"). This skill validates the *semantic* state mechanical triggers miss: are there open P0/P1 bugs the release would skip, verification agents still running, PRs awaiting review? The PO is the decider; this skill produces the checklist.

See `_shared/orchestration.md` §"Pre-Release Semantic Checks" for the underlying rule.

## Model Selection

This skill runs as the orchestrator — no persona dispatches. Model inherits from the parent. If a specific item on the checklist needs a persona's read ("is this CVE release-blocking at our tier?"), spawn that persona separately at `sonnet`.

## Preflight

1. **Identify the release.** Version, tag, or branch. If the PO invoked `/release-check 0.17.0`, use that. If bare, ask.
2. **Identify sprint scope.** Look for `docs/sprint-scope.md`, `SPRINT.md`, or a label convention in the bead system. If unclear, ask: "What's the sprint label or milestone for this release?"
3. **Identify the bead system.** Default: `bd` if `bd list` succeeds. Otherwise, ask the PO how to query open bugs.

## Process

### Step 1: Query open bugs in sprint scope

    bd list --status open --priority 0 --label sprint:<sprint>
    bd list --status open --priority 1 --label sprint:<sprint>

Adjust syntax for the actual bead system. Record counts and IDs per priority.

### Step 2: Check in-flight verification agents

Identify any agents the orchestrator spawned for QA, security review, code review, or test verification that are still running against artifacts this release would include. Record agent IDs and what they're verifying.

### Step 3: Check open PRs targeting the release branch

    gh pr list --search "is:open base:<release-branch>" --json number,title,reviewDecision,statusCheckRollup

Open PRs targeting the release branch are decisions the release would skip. Record numbers and states.

### Step 4: Check security gate state

If the project uses CodeQL or similar, verify the last scan on the release branch is green. If gated to `main` only, note that the release-cut PR to main is the validation point.

### Step 5: Check version/changelog consistency

If the project maintains a CHANGELOG with an `[Unreleased]` section and per-artifact version fields (`version:` in SKILL.md frontmatter for skill repos, `package.json`/`pyproject.toml` versions in code repos), verify every artifact listed under `[Unreleased]` carries the new release version before tagging. In this skill system: `grep -E "^version:" */SKILL.md` and cross-check against the `[Unreleased]` entries — any skill changed there still showing an older version is a finding.

### Step 6: Produce the checklist and surface to PO

Present in a `## DECISIONS NEEDED` block per `_shared/orchestration.md` §"Decision Prompts":

    ## RELEASE READINESS — v<version>

    | Check | Status | Detail |
    |---|---|---|
    | Open P0 bugs in sprint scope | <count> | <bead IDs> |
    | Open P1 bugs in sprint scope | <count> | <bead IDs> |
    | In-flight verification agents | <count> | <agent IDs + what they verify> |
    | Open PRs targeting release branch | <count> | <PR numbers> |
    | Last security scan | <green/red/N/A> | <link or commit> |
    | Version/changelog consistency | <consistent/drift/N/A> | <artifacts still on old version> |

    ## DECISIONS NEEDED

    1. **Release v<version>**
       - State: <one-line summary — all green, or which items are open>
       - Decision: proceed with release-execution, or hold?
       - Options:
         - Proceed — accept the open items as non-blocking
         - Hold — clear the open items first
         - Defer specific items — waive specific beads with reasoning

### Step 7: Refuse to fire release-execution without explicit confirmation

If the PO answers "proceed," "go," or explicitly waives the open items, fire the release-execution agent. If the PO replies with a catch-all that doesn't address the checklist ("ship it," "let's go"), do NOT fire — per `_shared/orchestration.md` §"Authorization Verbs," re-surface the checklist with a 1-line clarification.

## Rules

- **No mechanical-only triggers.** Mechanical triggers are insufficient; that's why this skill exists. Don't fire release-execution based on "all PRs merged" alone.
- **Open items are not always blockers.** Some P1 bugs are deliberately deferred. The checklist surfaces them; the PO decides whether each is a blocker.
- **In-flight verification is always a blocker.** Per `_shared/orchestration.md` §"Don't Merge Past In-Flight Verification" — if QA is running against the release artifact, the release waits.
- **One check per release.** Don't re-run mid-release unless something material changed (new P0 surfaced, verification agent completed). Repeated checks erode the PO's signal-noise ratio.
- **The ship checklist is not the CI gate.** Every merge in scope should have followed the project's documented shipping process — version advanced (incremented, not merely consistent), CHANGELOG entry in the same PR, documented local checkers run. Nine PRs once shipped through green gates with none of these; if the release-check finds checklist debt, it's a blocker to surface, and the fix is running the project's own documented commands, not hand-reconstructing history.
