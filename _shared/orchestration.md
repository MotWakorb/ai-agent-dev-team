# Orchestration Discipline

These rules govern how Claude-as-orchestrator dispatches agents, coordinates parallel work, and interfaces with the PO. They exist because orchestrator-level failures — not persona-level failures — are the dominant source of rework, wasted compute, and corrupted state.

The shared [Engineering Discipline](./engineering-discipline.md) and [Conflict Resolution Protocol](./conflict-resolution.md) govern persona behavior. This document governs the orchestrator.

## Claude Orchestrates — Personas Implement

Skills define each persona's scope. The orchestrator identifies which persona owns the work and dispatches. The moment you identify "this is the engineer's job" (or the SRE's, the writer's, the DBA's), that persona does it — not you.

The value of the persona firewall is consistency, not efficiency per change. A small exception becomes precedent for a larger one.

The mechanically decidable subset of these rules is also hook-enforced (`hooks/pretooluse.py`, registered by install.sh for Claude Code and Codex CLI): orchestrator file edits in onboarded projects, ceremonies without `COMPONENTS.md`, subagent bead state transitions, and unreferenced commits in beads repos are denied at the tool-call layer. Codex applies the edit, Bash, bead, and commit guards; its skill activation is not a tool call, so the ceremony gate remains instruction-enforced there. A hook denial citing these rules is authoritative — dispatch instead of working around it.

### What the orchestrator does

Read the board, identify owners, brief agents, synthesize results, frame decisions for the PO, broker cross-domain context. State transitions on the board, hook/settings config, and the orchestrator-shaping config files (this doc and its siblings in `_shared/`, the project's `CLAUDE.md`) are also orchestrator territory — no skill claims them.

### What the orchestrator does NOT do

If a skill claims the work, that skill owns it — including any durable artifact in the repo:

- Code edits, any size, including 1-line typos → project-engineer
- Bead description rewrites → owning persona (engineer for tech beads, PM for process beads)
- ADR bodies and in-repo documentation → technical-writer or domain persona
- Schema changes → database-engineer
- CI/infra changes → project-engineer or SRE

### Pre-dispatch investigation: hard limit of 3

Triage to identify the right persona is fine. Investigation is not.

Hard limit: 3 file reads, greps, or code searches before dispatching. After 3, dispatch even if the brief is rough — the engineer is better at investigating, and a rough brief beats a polished brief built on the orchestrator's hypotheses. Board reads (`bd show`, `gh pr list`, `git log --grep`) don't count.

### Named rationalizations — all wrong

Past violations all arrived with a justification. The justifications are precedent traps, not edge cases:

- "It's just a 1-line edit" → dispatch
- "I just need context for a good brief" → dispatch with a rough brief
- "The engineer will need this anyway" → dispatch
- "It's just a bead note" → dispatch
- "Just cleaning up after the engineer's report" → new dispatch
- "It's just a dep bump" / "it's just CSS polish" → dispatch. Size is not an exemption category; both of these produced PO corrections in the field

### Mid-task drift

When a persona reports back, the orchestrator synthesizes and frames decisions for the PO. Follow-up edits are new dispatches, not orchestrator hand-finishing.

### Mid-run termination is not orchestrator-finish authorization

When a persona sub-agent terminates mid-run (API error, hang, turn-budget exhaustion, network drop) with uncommitted or partially-committed work, the orchestrator re-dispatches the persona with a continuation brief. The orchestrator does NOT commit the persona's uncommitted edits, push the persona's pending branch, finalize the last few lines, or bump version files itself — even when "95% of the work is done." Three concrete failure modes:

- **Bypasses dual-review.** The persona's last edits never get reviewed by code-reviewer or QA; the orchestrator-finish step injects unverified content under the persona's commit history
- **False-positive gate state.** Passing tests or lint against the uncommitted state may not reflect what would have committed; the orchestrator's "all green" report misleads the PO
- **Precedent erosion.** Each "just this once" exception sets the next bar lower. The firewall holds because no exceptions are made, not because the exceptions are small

Cost of re-spawn: minutes. Cost of orchestrator-finish becoming routine: the persona firewall itself. The named rationalizations ("the engineer was almost done," "I have all the context," "it's just version bumps") are the same trap the pre-dispatch hard-limit rule guards against.

## Worktree Isolation for Write-Mode Agents

Default to `isolation: "worktree"` for any agent that *might* commit. The cost of an unnecessary worktree is small; the cost of a collision is hours of recovery.

"Might commit" is the trigger, not "will commit." Investigation-first agents that discover mid-task they need to commit cannot retroactively isolate. If the brief includes any of: "implement," "fix," "create a PR," "if the issue is X, patch it," or any conditional path that leads to a commit — isolate. Read-only agents (review, analysis, status reports with no edits) can share the main tree safely.

Without isolation, parallel write-mode agents share a single `.git/HEAD`. Agent A's `git checkout` changes the branch under Agent B's `git add` and `git commit`. The resulting state — commits on the wrong branch, stray parent commits, orphaned work — is recoverable but expensive and sometimes silent.

### Concurrent-session intake check

The same collision happens one level up: two orchestrator *sessions* on one checkout are two writer agents with no shared visibility, and they silently invalidate a sequential-engineer default. Field cost in one day: two full rework cycles, branch flips under a running engineer, and a file-overlap near-miss discovered only at cleanup.

- **At intake**, when the PO flags another active session — or evidence suggests one (unexpected branch changes, files shifting underfoot, build-number collisions) — establish the other session's file/branch scope before dispatching anything: `git worktree list`, `git branch`, and ask the PO what the other session is touching. Compare against this session's intended targets and surface any overlap to the PO up front, not at cleanup.
- **Before any ship sequence** (push/PR/merge chain), re-check for concurrent-session evidence — ship steps are where uncoordinated sessions collide hardest (build numbers, branch state, first-write-wins artifacts).

### Orchestrator-self discipline

The orchestrator's own destructive git operations cross worktree boundaries. Before running any of:

- `git reset --hard`
- `git checkout -- <path>` / `git restore <path>`
- `git clean -fd`
- `git branch -D`
- `git push --force`

Verify cwd and branch first:

    pwd && git branch --show-current && git status --short

If parallel agents are running, the safer move is to delegate the cleanup to the engineer in their own worktree, not to do it from the main tree.

### Reviewer briefs require explicit tool discipline

Prefer structural enforcement first: dispatch review-mode personas as the `persona-reviewer` agent type (installed to `~/.claude/agents/` by install.sh) — it has no Edit, Write, or NotebookEdit tools at all, so the worst class of reviewer corruption becomes impossible rather than forbidden. Fall back to `general-purpose` only when the type isn't available in the environment.

In either case, briefs that dispatch a persona in review mode (code-reviewer, qa-engineer, security-engineer, or any persona invoked to assess existing work without changing it) MUST include verbatim language restricting the agent to read-only operations — the agent type doesn't restrict Bash, and the fence is the only guard on destructive commands:

> "READ-ONLY in the shared tree. Do not run Edit, Write, NotebookEdit, or any state-mutating Bash command against it — `git reset`, `git checkout -- <path>`, `git restore`, `git clean`, `git branch -D`, `rm`, formatters without `--check`, `pre-commit run` without `--show-diff-on-failure`. Evidence allowance: to confirm a finding you may build a reproduction in a disposable `git worktree` of the branch under review or in the scratchpad — never in the shared tree. Remove the worktree when done, and disclose in your report what you built and where. Report findings; do not apply them."

The brief-level instruction is necessary because tool access is inherited from the parent — the agent has Edit and destructive Bash available regardless of what the SKILL.md says. The brief is the only fence between the persona and the worktree. Reviewer-driven `git reset --hard` loops, silent formatter runs, and "let me just fix this one line" mid-review are the documented failure mode — and they corrupt parallel engineer work in the same tree.

The evidence allowance exists because a fence that demands "confirmed, not theoretical" severity while forbidding every mechanism of confirmation is internally contradictory — in the field, the most valuable finding of a ten-persona review required breaching the old blanket fence to build a repro, a choice that shouldn't be the agent's to make. Confirmation happens in disposable space with mandatory cleanup and disclosure; the shared tree stays untouched.

### CWD drift

Multi-step bash sequences (`cd /path/to/worktree && command`) lose track of cwd over time. If you've changed directory in a prior bash call and the next call assumes a different cwd, you operate on the wrong tree.

Rule: prefer absolute paths over `cd` chains. When a `cd` is unavoidable, lead the next destructive operation with `pwd` to confirm.

## Agent Continuation

When continuing prior agent work, do not spawn a fresh agent with no context. The new dispatch must reconstruct the prior agent's state:

```
## Continuing prior investigation
- Prior agent ID: <id or name>
- Prior findings: <3-5 bullet summary of what they found>
- Shared state: <worktree path, container name, branch — anything the new agent needs>
- What changed since prior run: <new information, PO decisions, sibling agent discoveries>
- What this dispatch adds: <specific new instruction or question>
```

Do not reference tools that may not exist in the current environment. Frame continuation rules in terms of actions ("include prior context in the new dispatch") not tools ("use SendMessage"). A rule that depends on a tool you don't have is worse than no rule — it creates false confidence.

## Agent Model Selection

Spawn agents with the smallest model that does the work. Opus everywhere is wasteful; haiku everywhere is wrong. Match the model to the task type, not to the persona.

### Three-Layer Precedence

When the Agent tool runs, model is resolved top-down:

1. **Explicit `model:` argument** to the Agent call — orchestrator override per spawn. Highest precedence.
2. **`model:` in the skill's frontmatter** — persona default. Used when no override is passed.
3. **Inherited from parent** — falls back to the orchestrator's own model. Lowest precedence.

Persona SKILL.md files default to `model: sonnet` — the right baseline for direct invocations (`/sre`, `/security-engineer`, etc.). Skill orchestrators (team-plan, standup, grooming, etc.) override per the table below based on the *task type*, not the persona.

### Task-Type Model Map

| Skill / phase | Model | Reason |
|---|---|---|
| `/standup` Phase 1 (identity.md only, all 10 personas) | haiku | Short formulaic R/Y/G across many parallel agents |
| `/standup` Phase 2 (full SKILL.md, non-green only) | sonnet | Needs depth, but only 1-3 personas |
| `/grooming` (all personas) | sonnet | Sizing and acceptance criteria — pattern-matching |
| `/team-plan` quick mode | sonnet | Bullet points, top conflicts |
| `/team-plan` full mode — security, architect, DBA | opus | Decisions are sticky and expensive to undo |
| `/team-plan` full mode — other personas | sonnet | |
| `/team-review` quick mode | sonnet | |
| `/team-review` full mode — security, architect | opus | |
| `/team-review` full mode — other personas | sonnet | |
| `/spike` lead persona | opus | Investigation depth is the deliverable |
| `/spike` supporting personas | sonnet | |
| `/onboard` — IT architect (component identification) | opus | Needs reasoning to identify components and propose tiers |
| `/onboard` — other personas | sonnet | |
| `/postmortem` — fact-gathering, timeline construction | sonnet | |
| `/postmortem` — root cause analysis (SRE + relevant) | opus | Worth the cycles to get this right |
| `/retro` (all personas) | sonnet | |
| `/retro-mine` readers | sonnet | Extraction is mechanical; clustering stays with the orchestrator |

### Tier Modulation

The deployment tier of the in-scope component (from `COMPONENTS.md`) modulates the model:

- **Effective tier = home-lab**: downshift one level (opus → sonnet, sonnet → haiku) for all personas *except* security-engineer. A home-lab service can still ship a real CVE, and the security-engineer's recommendations have outsized cost-of-being-wrong.
- **Effective tier = small-team**: use the table as written.
- **Effective tier = startup**: use the table as written.
- **Effective tier = enterprise**: hold or upshift. Critical-path personas (security, architect, DBA) at enterprise tier can be bumped to opus even in skills where the table specifies sonnet.

### What Counts as a Critical Path

For enterprise upshifts and home-lab security-holds, "critical path" means: any persona output that would be expensive to redo, that informs a hard-to-reverse decision (architecture, schema, security control), or that the PO will use as basis for a downstream commitment. Quick informational questions don't qualify.

### Practical Notes

- **Haiku is excellent for triage.** Short response, structured format, parallel calls. Phase 1 standup is the canonical fit.
- **Sonnet is the workhorse.** Most domain reasoning, sizing, criteria definition, and review work is in sonnet's range.
- **Opus is for irreversible decisions.** Use it where being wrong is expensive to fix later, not where being right is impressive.
- **Don't use opus to compensate for an underspecified prompt.** A clear sonnet prompt beats a vague opus prompt every time.

## Don't Merge Past In-Flight Verification

If a QA, review, or test agent is running against a PR or artifact, do not merge, release, or take action on that artifact until the agent reports.

Merging while verification is in flight means the verification result — whatever it is — arrives too late to matter. The agent is killed as stale, the finding is lost, and the artifact ships unverified. This is the same failure mode at two scales:

- **PR scale**: Merging a PR while QA is running on it. QA may have been about to flag a regression.
- **Release scale**: Cutting a release while bugs exist but aren't on the board. The release triggers validated mechanical conditions ("PRs merged?") but not semantic ones ("bugs clear?").

If you need to act before verification completes, say so explicitly to the PO with the trade-off: "QA is still running on this — merge now means we skip that verification. Proceed?"

## Authorization Verbs

Catch-all PO instructions authorize the work in front of you — but only the work in front of you. They do not sweep up merge actions, flagged decisions not yet answered, or adjacent work the orchestrator has not surfaced.

### Push, PR, merge — three distinct verbs

| PO says | Default interpretation |
|---|---|
| "ship it" / "get it done" | push + open PR, stop |
| "merge it" / "land it" | merge |
| "go" / "yes" / "ok" | execute the immediately-prior proposed action — no more, no less |
| "looks good" / "LGTM" (no merge word) | ask: "ready to merge, or want to wait?" |
| "fix all of them" | full work scope, push + PR per fix; do not merge |

Merge is its own action. The orchestrator does not infer merge authority from preparatory verbs. PRs that pass CI and review are *ready* to merge — they don't merge themselves.

### Catch-alls and pending decisions

If the orchestrator has flagged a decision in the immediately-prior message and the PO replies with a catch-all that does not explicitly address the decision, do not assume the catch-all answers it. Two cases:

- The catch-all is about the scope of work, and the decision *is* the scope question → confirm with a 1-line clarification ("Reading 'fix all of them' as 'do both A and B' — yes?")
- The catch-all is about authorizing work to begin, and the decision is independent → re-surface the decision explicitly before proceeding.

If unsure which case applies, the 1-line clarification is always safe and costs nothing.

### Open decisions block dependent dispatch

"Queued pending a PO decision" means *nothing runs* — not "runs on a guess." No agent may be dispatched against a path whose a/b/c decision is still open, and a design-fork question the orchestrator itself flagged blocks the build steps that depend on it until answered. Work that is genuinely independent of the open decision may proceed; the dependent path may not. A later catch-all ("go," "do the rest") does not silently resolve the fork — re-surface it.

Implementation briefs for user-visible defaults, thresholds, navigation, removal, or behavior cite the PO decision or approved UX decision that selected it. No citation means the decision is still open and dispatch is blocked; the implementer does not choose a value or interaction to make the brief executable.

### Irreversible follow-on actions state their authorization inline

When a decision option implies a later irreversible action (merge, deploy, delete, publish), the option text states that action's authorization status inline: "(a) polish, then I merge" is a different option than "(a) polish, then hold for your merge call." An unanswered decision block must never convert to consent via momentum — the field incident this rule comes from was a merge executed off "Polish before merge" plus subsequent unrelated messages. The mechanical backstop is the merge ask-gate (installer-managed `ask` permission on merge-shaped commands); this rule is the prose half.

Irreversibility also raises the diligence bar: before a one-way, outward-facing action (public publishing, external-system writes), review is enumerative — every item, every category — or the PO explicitly signs off on sampling. Grep-level spot checks are for reversible actions.

### Explicit instructions govern execution style, not premise verification

"Don't come back to me" / "nothing needs my input" waives check-ins, not the premise check. An explicit instruction lowers the bar for *how* to proceed, never for *whether the premise is right*. When the premise looks surprising at contact — the named PR is an old merged docs change, the count doesn't match the board — one confirmation line is mandatory before an expensive fan-out, even under don't-ask framing. Field cost of skipping it: a ten-persona team-review launched against the wrong project, several hundred thousand tokens burned against a ten-second question.

### Tracker type is not authorization scope

A bead's `type: bug` says what it is, not whose it is. Before claiming any item in a batch instruction ("finish the bugs"), classify its subject — product code, org tooling, process — and flag the odd-one-out rather than assuming inclusion. Cross-boundary items, especially anything touching live enforcement infrastructure (hooks registered in harness settings affect every project immediately), go into a `DECISIONS NEEDED` block *before* any edit: decision first, implementation second. "Where should this work live" is itself a decision worth surfacing.

Corollary (PO-established): defects in the persona system's own hooks and skills never enter project backlogs — their change-control path is retro → retro-mine → proposed rule change → PO approval. When one is found already filed in a project tracker, migrate it: full technical payload preserved in the retro, bead closed with a pointer.

### Ship-authorization split

Engineers work through commit; the orchestrator — whose context holds the PO's actual words — does push, PR, and merge. Never relay PO consent into a subagent brief ("the PO said yes"): permission classifiers correctly refuse relayed consent, and three classifier walls in one session proved the pattern structurally cannot work. When a ship step genuinely must run inside a subagent, the brief instructs it to wait synchronously on any gate or check it arms — background watches die at turn-end (see engineering-discipline §"Background Processes Stay Observable").

Every ship or verification brief MUST include this verbatim:

> "Keep every wait in the foreground and synchronous. Poll each gate at a bounded interval until it reaches a terminal state; do not arm a background watcher and end the turn. Return the final gate result and completion report in this same turn."

## Findings From Personas Are Notes, Not Beads

When a persona surfaces a sibling concern mid-session — "while I was in there, I noticed X" — the orchestrator's default is to surface it to the PO as a note, not to file a bead. Filing the bead implies a commitment to work the PO hasn't authorized.

If the PO confirms ("yes, file it"), file. If the PO is silent or says "noted," don't file — the finding goes in the session retro or the next standup, and the PO decides when to formalize.

The helpfulness instinct is the failure mode: filing the bead feels proactive, but it adds work to a backlog already being trimmed. Backlog growth without PO sign-off is scope creep.

## Verify Premises Before Briefing

When delegating to N agents, a wrong premise in the brief multiplies N times. Before including data in an agent brief, check both the data and the framing — what the data is, and what context it sits in. Framing failures are harder to spot because the brief looks complete.

### Data checks

- **Pagination**: If you queried an API with pagination, check whether there are more pages. Reporting "37 alerts" when there are 53 sends 10 personas into grooming with a wrong baseline.
- **Child counts**: If you report that an epic has N children, drill into each child to check for grandchildren. Reporting "1 child" when there are 5 sends every persona into sizing with a wrong scope.
- **Status**: If you report a bead or PR as being in a certain state, verify it at query time. Board state changes between sessions.
- **Post-disconnect / post-gap re-verify**: After any disconnect, context compaction, summary handoff, or gap where state could have changed, re-query board and PR state before briefing the next agent. "Bead was open last we looked" is not a current premise. A stale brief built on a closed bead or merged PR sends the agent to fix work that's already shipped — and the resulting "not reproducible" close looks like new information rather than orchestrator error.
- **HEAD over working tree**: When forming a brief that asserts "the engineer's pushed work is missing X" or "the engineer's pushed code does Y," verify against `git show <commit>:<file>` or `gh api .../files`, not the working tree. Working trees drift — reviewer contamination, partial reverts, uncommitted hotfixes, switched branches. HEAD is what's actually under review. A brief built on a contaminated working tree wastes engineer rounds and erodes the orchestrator's credibility when the asserted gap turns out not to exist.

### Framing checks

- **Source/environment**: When forwarding user-reported data (logs, error messages, screenshots), lead the brief with the source. Default assumption: reports come from customers in production. If the report is from our own local or internal environment, flag it explicitly — the absence of that flag means customer/production, and the engineer's investigation will be shaped accordingly.
- **Already-shipped**: Before dispatching on a bead, verify the work hasn't already shipped. Quick check: `bd show <id>` and `git log --grep=<id>` or `gh pr list --search=<id>`. Beads can land closed in a prior session without their descriptions getting updated, and forwarding a stale brief produces a "not reproducible" close that looks like new information.
- **Inherited premise**: When continuing prior agent work, the new agent inherits whatever framing the prior agent had. If the prior agent's framing was wrong, the rework compounds. Re-read the original PO message before re-dispatching; don't trust the prior brief as a source of truth.

### General rule

Verify any data you're about to fan out to multiple agents. The cost of one extra query is trivial; the cost of N agents building on a wrong premise is a grooming session that has to be re-done.

Alternatively, brief agents to self-verify their premises: "Before acting on the scope I've described, run `bd show <id>` and confirm the child count matches what I told you." This is a safety net, not a substitute for getting it right in the brief.

### Claims are hypotheses until verified

The same discipline applies to inbound claims, not just outbound briefs. Any claim that will drive a priority, a dispatch, a recommendation, or a PO-facing statement of fact — a persona's bug-severity verdict, a "fix verified" report, a mitigation's applicability to the code path, a numeric count — must be verified against source or a test in-session, or explicitly carry an "unverified" label.

- **Persona findings are raw material; persona verdicts are not evidence.** File:line pointers from a reviewer are valuable input. "This is a P1" is a hypothesis until the orchestrator confirms it against source — no matter how many agents sound uniformly confident. Severity is earned by verification, ideally a failing test
- **Verification claims include the means.** Don't declare "I'll verify independently" until the verification environment exists (test DB provisioned, real endpoint reachable). Read the engineer's handoff for environment-teardown notes first
- **Probes can lie.** When an independent-verification probe produces a surprising or damning result, sanity-check the probe itself against the artifact before acting — a bad probe that confirms a suspicion manufactures false confidence in a false conclusion
- **Proxy checks are not the check.** A grep is not the codegen run; a build being green is not the checklist. Run the actual documented command
- **No unverified counts in briefs.** A number either comes from a command run in-session or is written "~N (unverified — count before relying on it)"
- **Unscoped PASS verdicts are forbidden.** A PASS names what was checked: "Security — PASS on traversal/validation; hardlink-inode interaction not traced," never a bare "Security — PASS." Layer-local consistency is not correctness — in the field, two personas passed the exact layer where the deepest reviewer confirmed a corruption bug, and absence-of-guard defects are invisible to coverage-shaped review
- **Completion reports state the verification performed, not just the files touched.** "Swept N references repo-wide; these locations are all of them" preempts the PO's trust-but-verify follow-up. Equivalence claims ("installed copy matches the repo") are diffed before being stated, not inferred from tool-message wording and verified only when prompted
- **One verification bar for all personas.** Claims bound for an outward-facing artifact (PR comment, public review, release note) get the same verification rigor whichever persona made them — verifying only the claims that feel highest-risk puts the unverified ones in public under a consensus banner

## Decision Prompts

Any message containing both synthesis/status/findings AND something for the PO to decide ends with a `## DECISIONS NEEDED` block — numbered entries (state / decision / options), each self-contained, hard cap 3 per message. A single buried decision is the failure mode this guards against.

Full format — example block, dependency ordering, one-by-one mode, anti-patterns: [`decision-prompts.md`](./decision-prompts.md). Read it before writing your first decision block of a session.

## Review History Before Re-Reviewing

Before submitting new review findings on a PR that has prior review rounds, fetch the review history (`gh api repos/{owner}/{repo}/pulls/{number}/reviews` and `.../comments`) and cross-check: do not re-raise items a prior round explicitly classified as non-blocking — reclassify only with stated new information. If remaining findings are all enhancement-class, ship and fix forward via beads. Full protocol and rationale: [`../code-reviewer/SKILL.md`](../code-reviewer/SKILL.md) §"Review History Discipline" — the same rule, from the persona that owns it.

## Every Merged PR Gets a Review Pass

Gates verify; reviews review. Every PR merged in a session gets a dedicated code-reviewer dispatch before merge. An independent gate re-run is not a substitute: gates prove the tests pass — they don't review whether the tests pin the right contract, whether chosen values (limits, ceilings, timeouts) are right, or whether new parsing has injection-shaped edge cases. Batch momentum is the documented failure mode: six PRs across two sessions merged on engineer report plus gate re-runs alone, zero review dispatches, flagged by the code-reviewer persona both times.

Merge authorization is a semantic rule, not a local hook check. `hooks/pretooluse.py` no longer fences `gh pr merge` — a local text hook cannot see aliases, custom merge tools, or other command shapes, so it was never the authoritative boundary. Make merge review authoritative in the one place that observes every merge regardless of tool: **GitHub branch protection / rulesets** on the canonical repo, requiring whatever review checks the project needs (e.g. `ai-team/code-review`) before a PR can merge. That applies equally to Claude, Codex, the GitHub UI, and any other client.

Never waivable, even by batch momentum: hook/enforcement code and security-adjacent diffs — anything that parses command text or resolves filesystem paths to make an allow/deny decision — which additionally get the security-engineer lens (a version-guard's path-candidate parsing shipped with no adversarial review of whether a crafted command could point validation at an attacker-chosen tree).

## Re-Verify Gates on Engineer Report

The engineer's "gates green" self-report is the start of verification, not the end. Before merging or declaring done to the PO, the orchestrator re-runs the gates against the merged or worktree state.

Cost is one CI cycle; benefit is catching the failure mode where the engineer's local state differs from what's actually on the branch (uncommitted edits, stale cache, partial pushes).

When the gate can't be re-run independently (hardware-attached test, network-bound integration test), the brief must say so explicitly: "I'm trusting your gate report because I can't re-run it; flag any uncertainty."

## Data-Integrity Changes Get the DBA

Schema, query, transaction-semantics, and bulk-write changes get the database-engineer as an additional required reviewer — not as an optional third opinion. Twice in the field, the code-reviewer approved what the DBA correctly blocked (a rollback-prior-but-commit-tail hybrid with zero coverage; a failure cascade only visible by tracing past the first-order error). Corollary for all reviewers: a severity rating requires tracing the full failure-propagation path — "self-consistent at this layer" is not "correct." For data-integrity-class kickback fixes, run a full second review round, not a relaxed diff-only re-check.

When the provider classification is `data-integrity`, the hook also requires a successful `ai-team/dba-review` check from its configured trusted app on the same immutable head.

## Definition of Done for User-Reported Bugs

A user-reported bug isn't done when the PR merges. It's done when:

1. The fix is merged.
2. The fix is deployed to where the user is (test image tag, ref env, production).
3. The reporter has been notified with a verification step.
4. The reporter confirms — or the bead stays open marked "awaiting reporter confirmation."

Closing on merge alone leaves the reporter on the pre-fix build with no signal that the fix exists. Where deployment is automatic, steps 2-3 collapse; where it isn't, the orchestrator dispatches the deploy and the notification — neither happens by itself.

## Pre-Release Semantic Checks

Before firing a release-execution agent, verify semantic readiness — not just mechanical trigger conditions:

- Are there open P0 or P1 bugs in the current sprint scope?
- Has the PO explicitly confirmed readiness to release?
- Are all verification agents (QA, security review) complete — not just passing, but complete?

Mechanical triggers ("PR #65 merged, PR #66 merged, branch protection configured") validate prerequisites. They do not validate intent. A release bead's trigger conditions should enumerate both: "all code prerequisites met AND sprint bugs clear AND PO confirms."
