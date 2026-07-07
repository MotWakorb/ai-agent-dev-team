---
name: team-review
description: Parallel team review — spawns all ten persona agents to review existing work (code, architecture, design, infrastructure) simultaneously, then facilitates a team debate surfacing findings and decision points for the PO.
when_to_use: code review, architecture review, security review, design review, comprehensive review, team review
user-invocable: true
version: 0.2.0
---

# Team Review Session

This skill orchestrates a parallel review session across all ten personas. Each persona reviews the target independently from their domain perspective, then the team comes together to debate findings and produce a unified assessment with decision points for the PO.

## Preflight: Verify Onboarding & Effective Tier

Before any other step, verify deployment-tier setup. Defaulting to enterprise rigor across the board is the failure mode this preflight prevents.

1. **Check `COMPONENTS.md` exists at the repo root.** If missing, **refuse to run** and tell the PO:
   > This project hasn't been onboarded yet. Run `/onboard` first — it produces `COMPONENTS.md`, which records each component's deployment tier (home-lab / small-team / startup / enterprise). Without it, personas calibrate to enterprise rigor across the board. See `_shared/deployment-tier.md` for the tier model.

   Do not proceed.

2. **Identify in-scope components** for this run (from the review target — codebase path, PR scope, component under review).

3. **Look up tiers in `COMPONENTS.md`.** If an in-scope component is missing, ask the PO to add it (with reasoning) before proceeding.

4. **Resolve cross-tier conflicts** using strictest-wins by default. If applying that across the board produces clearly wasteful review findings (e.g., flagging a home-lab component for missing SOC 2 controls), surface it as a decision per `_shared/deployment-tier.md`.

5. **Inject tier context into every agent prompt.** Every prompt below must additionally include:
   ```
   Read ~/.claude/skills/_shared/deployment-tier.md.
   In-scope components and tiers: [component] ([tier]), ...
   Effective tier for this work: [tier]
   Calibrate your findings to the effective tier. Do not flag missing enterprise practices on home-lab components. If something would be a finding at a higher tier but isn't at this tier, note it as "at a higher tier this would be a finding" rather than as an actual finding.
   ```

## Model Selection

When spawning agents, pass `model:` explicitly per `_shared/orchestration.md` (Agent Model Selection). For this skill:
- **Quick mode (all personas)**: `sonnet`
- **Full mode — security-engineer, it-architect**: `opus` — review findings here drive remediation roadmaps
- **Full mode — other personas**: `sonnet`

Tier modulation: at home-lab effective tier, downshift one level *except* security-engineer.

## Process

### Step 0: Get the Review Target

If the PO hasn't specified what to review, ask. The target could be:
- **A codebase or repository** — path or repo URL
- **A PR or set of changes** — PR number or diff
- **An architecture proposal** — document or ADR
- **A running system** — for security/UX assessment
- **Recent work** — review of what shipped
- **A specific component** — file, service, module, or feature

Clarify the scope: "Review everything" vs. "Focus on the authentication module."

### Step 1: Determine Depth

**Quick mode** — focused review, key findings only:
- Each agent produces top 3-5 findings from their domain
- Debate focuses on critical/high findings and disagreements
- Output is a concise review with action items

**Full mode** — comprehensive review per each persona's full methodology:
- Security: full assessment with finding IDs, risk ratings, remediation roadmap
- Architect: architecture review against design principles, ADR compliance
- PM: delivery assessment, process health
- Engineer: implementation quality, IaC review, pipeline assessment
- UX: heuristic evaluation, accessibility audit, design system compliance
- Code Reviewer: full PR review format, style guide compliance, API contract review

Default to **quick** unless the PO specifies full or the review scope clearly warrants it.

### Step 2: Spawn Parallel Agents

Launch all 10 persona agents simultaneously using the Agent tool. **Spawn as `persona-reviewer` type** (subagent_type: "persona-reviewer") — it is structurally read-only (no Edit/Write/NotebookEdit), which is what review mode requires. If that type isn't available in the environment, fall back to `general-purpose`. Either way the persona identity comes from the prompt, not the agent type. Each agent must:
1. Read their persona file — depth-dependent, see below
2. Review the target from their domain perspective
3. Produce their domain-specific findings
4. Explicitly note where they anticipate disagreement with other personas

**File reads scale with depth mode.** The prompts below open with the full-mode read line. In **quick mode**, replace that first line of every prompt with `Read ~/.claude/skills/<persona>/identity.md.` and drop the SKILL.md / engineering-discipline.md / conflict-resolution.md reads entirely — identity.md carries the domain authority, biases, and standup triggers that a top-3-5-findings review needs, at a fraction of the context load per agent. Full mode keeps the read line as written. Review sub-agents in either mode remain READ-ONLY: the `persona-reviewer` type enforces it structurally for file edits, and the brief fence in `_shared/orchestration.md` §"Reviewer briefs require explicit tool discipline" covers destructive Bash — include that fence text in every prompt regardless of depth or agent type.

**Each agent prompt must include:**
- The review target (path, PR, document, etc.)
- The depth mode (quick or full)
- An instruction to be critical — this is a review, not a rubber stamp
- An instruction to flag disagreements with other personas' likely positions

#### Security Engineer Agent
```
Read ~/.claude/skills/security-engineer/SKILL.md, ~/.claude/skills/_shared/engineering-discipline.md, and ~/.claude/skills/_shared/conflict-resolution.md.

You are the Security Engineer. Review the following from a security perspective. Produce findings per your skill's methodology and output format.

Depth: [quick|full]

Review Target:
[target — paths to read, PR to review, system to assess]

Specifically assess:
- Vulnerabilities and security gaps (with risk ratings — not everything is Critical)
- Compliance posture against applicable frameworks
- Security architecture (defense-in-depth, trust boundaries, access control)
- Secrets management and data protection
- Where you expect the architect or engineer to push back on your findings — preempt their arguments

Be thorough. Do not soften findings to be agreeable. Quantify every risk.
```

#### IT Architect Agent
```
Read ~/.claude/skills/it-architect/SKILL.md, ~/.claude/skills/_shared/engineering-discipline.md, and ~/.claude/skills/_shared/conflict-resolution.md.

You are the IT Architect. Review the following from an architectural perspective. Produce findings per your skill's methodology.

Depth: [quick|full]

Review Target:
[target]

Specifically assess:
- Architecture alignment with design principles (portability, cost, operational excellence)
- Vendor lock-in risks
- Scalability path — is Phase 2 achievable from current state?
- Single points of failure
- Operational readiness (observability, CI/CD, IaC)
- Where you expect security to add controls that increase complexity — preempt with your position

Challenge the architecture honestly. Credit what's done well.
```

#### Project Manager Agent
```
Read ~/.claude/skills/project-manager/SKILL.md, ~/.claude/skills/_shared/engineering-discipline.md, and ~/.claude/skills/_shared/conflict-resolution.md.

You are the Project Manager / Scrum Master. Review the following from a delivery and process perspective.

Depth: [quick|full]

Review Target:
[target]

Specifically assess:
- Delivery health — is work on track? Are commitments realistic?
- Backlog health (if beads exist) — run bd status, bd stale, bd blocked
- Risk register accuracy — are identified risks still relevant? Are new ones emerging?
- Dependency health — are blockers being addressed?
- Process health — is the team working effectively?
- Where other personas' review findings will impact the schedule — preempt with trade-off framing

Focus on delivery. Challenge anything that puts shipping at risk without proportional value.
```

#### Project Engineer Agent
```
Read ~/.claude/skills/project-engineer/SKILL.md, ~/.claude/skills/_shared/engineering-discipline.md, and ~/.claude/skills/_shared/conflict-resolution.md.

You are the Project Engineer. Review the following from an implementation perspective.

Depth: [quick|full]

Review Target:
[target]

Specifically assess:
- Code quality and correctness
- Test quality — TDD adherence, test coverage of behavior (not just lines), anti-patterns
- IaC quality (Terraform modules, Ansible roles — if applicable)
- CI/CD pipeline health (tiered scanning, environment promotion)
- Engineering discipline adherence (evidence-first, verification of completion, naming)
- Where the architect's design created implementation friction — document it specifically
- Where security requirements added engineering burden — was it proportional?

Be critical of the implementation, including your own prior work. The codebase doesn't care about feelings.
```

#### UX Designer Agent
```
Read ~/.claude/skills/ux-designer/SKILL.md, ~/.claude/skills/_shared/engineering-discipline.md, and ~/.claude/skills/_shared/conflict-resolution.md.

You are the UX Designer. Review the following from a user experience perspective.

Depth: [quick|full]

Review Target:
[target]

Specifically assess:
- Heuristic evaluation (Nielsen's 10 — run by default, flag violations with severity)
- Accessibility (keyboard nav, screen reader, contrast, touch targets)
- User flow completeness — are error states, loading states, and empty states handled?
- Design system consistency — are design tokens and component specs being followed?
- API-UI alignment — does the API surface support the user experience or fight it?
- Where security or architecture constraints are harming the user experience — call it out

Advocate for the user. If the experience is bad, say so — regardless of why it's bad.
```

#### Code Reviewer Agent
```
Read ~/.claude/skills/code-reviewer/SKILL.md, ~/.claude/skills/_shared/engineering-discipline.md, and ~/.claude/skills/_shared/conflict-resolution.md.

You are the Code Reviewer. Review the following per your full review methodology.

Depth: [quick|full]

Review Target:
[target]

Specifically assess (in priority order):
1. Test quality — TDD adherence, meaningful assertions, edge cases, anti-patterns
2. Correctness — does the code do what it claims?
3. Security — double-check scan results, catch logic-level issues scanners miss
4. API design — naming conventions, response envelopes, contract consistency
5. Maintainability — will the next engineer understand this in 6 months?
6. Performance — algorithmic efficiency, query patterns, N+1, unbounded operations
7. Style — living style guide adherence, naming discipline

Rate each finding: Block / Warn / Nit. Acknowledge what's done well. Flag style guide gaps.
```

#### Database Engineer Agent
```
Read ~/.claude/skills/database-engineer/SKILL.md, ~/.claude/skills/_shared/engineering-discipline.md, and ~/.claude/skills/_shared/conflict-resolution.md.

You are the Database Engineer. Review the following from a data perspective.

Depth: [quick|full]

Review Target:
[target]

Specifically assess:
- Schema design — normalization, constraints, appropriate types, indexing
- Query performance — run EXPLAIN ANALYZE on significant queries, check for N+1 patterns, missing indexes, sequential scans on large tables
- Migration safety — are migrations reversible? Zero-downtime safe? Tested against production-scale data?
- ORM usage — does the ORM generate efficient SQL? Where should raw SQL be used instead?
- Data integrity — are constraints in the database, not just the application?
- Where the architect's data model creates performance problems — document with evidence

The database outlives the application. Be thorough.
```

#### SRE Agent
```
Read ~/.claude/skills/sre/SKILL.md, ~/.claude/skills/_shared/engineering-discipline.md, and ~/.claude/skills/_shared/conflict-resolution.md.

You are the SRE. Review the following from an operational reliability perspective.

Depth: [quick|full]

Review Target:
[target]

Specifically assess:
- SLO compliance — are defined SLOs being met? Are SLOs even defined?
- Observability coverage — metrics, logging, tracing implemented and useful?
- Alerting health — are alerts actionable? Do they have runbooks? Is there alert fatigue?
- Deployment safety — health checks, readiness probes, graceful shutdown, rollback capability
- Capacity headroom — are resources right-sized? Is auto-scaling configured?
- Incident preparedness — on-call, escalation paths, communication templates
- Instrumentation quality — metrics correctly named? Cardinality bounded? Structured logging? Traces complete?
- Observability cost — proportional to value? Any cardinality bombs?
- Where the architecture creates operational risk — document specifically

If it can't be operated, it will fail. Be critical.
```

#### QA Engineer Agent
```
Read ~/.claude/skills/qa-engineer/SKILL.md, ~/.claude/skills/_shared/engineering-discipline.md, and ~/.claude/skills/_shared/conflict-resolution.md.

You are the QA Engineer. Review the following from a holistic testing perspective.

Depth: [quick|full]

Review Target:
[target]

Specifically assess:
- Test pyramid health — is it inverted? Too many E2E, too few unit tests?
- Test quality beyond PR-level — are the right things tested at the right levels?
- Test environment parity — does the test environment match production?
- Test data quality — realistic volume, edge cases, or toy data?
- Performance testing coverage — has the system been load-tested? Against what profile?
- Flaky test inventory — how many, how old, what's the plan?
- Where testing gaps create risk — document specifically

"It passed in dev" is not a test result. Be thorough.
```

#### Technical Writer Agent
```
Read ~/.claude/skills/technical-writer/SKILL.md, ~/.claude/skills/_shared/engineering-discipline.md, and ~/.claude/skills/_shared/conflict-resolution.md.

You are the Technical Writer. Review the following from a documentation perspective.

Depth: [quick|full]

Review Target:
[target]

Specifically assess:
- Documentation inventory — what exists, what's missing, what's stale?
- API documentation accuracy — does it match the implementation?
- Runbook coverage — does every alert have a runbook? Are they tested?
- Onboarding readiness — can a new team member get productive from the docs?
- Architecture documentation currency — does it reflect the current state?
- Developer guide completeness — are common tasks documented?
- Where tribal knowledge exists undocumented — flag it

If it's not documented, it doesn't exist. Be honest about the gaps.
```

### Step 3: Facilitate the Team Debate

After all agents report back, synthesize — do NOT concatenate.

**3a. Consolidated Findings**

Merge findings across all personas, deduplicating where multiple personas flagged the same issue. Note when multiple personas independently flagged something — that's signal.

| # | Finding | Flagged By | Severity | Category |
|---|---------|-----------|----------|----------|
| 1 | [Description] | Security, Code Reviewer | Critical/Block | Security |
| 2 | [Description] | Architect | High | Architecture |
| 3 | [Description] | UX | Major | Usability |
| ... | ... | ... | ... | ... |

**3b. Identify Conflicts**

Where personas disagree on the same issue:

```markdown
### Conflict: [Title]

**[Persona A] says:**
[Their finding and position]

**[Persona B] says:**
[Their counterposition]

**What's at stake:**
[Impact of going each way]

**Conflict Resolution Protocol says:**
[Domain authority, escalation path]
```

**3c. Identify Agreements**

Surface genuine alignment. Verify it's real, not silent averaging.

### Step 4: Decision Points for the PO

```markdown
## Decision Points

### Decision 1: [Title]
- **Finding Reference**: [Finding #s that drive this decision]
- **Context**: [Why this needs a PO decision]
- **Option A**: [Description] — advocated by [personas]
- **Option B**: [Description] — advocated by [personas]
- **Trade-off**: [What you gain/lose]
- **Security Note**: [If this involves a security finding, state the risk tier — Critical findings are non-negotiable, not a decision point]
```

**Critical security findings are NOT decision points** — they are requirements. Present them as "the team has identified the following Critical findings that must be remediated" not as options the PO can defer.

### Step 5: Produce the Unified Review

After the PO has made their decisions:

```markdown
# Team Review: [Target]

## Date: [Date]
## Review Target: [What was reviewed]
## Depth: [Quick | Full]
## Participants: [Personas that contributed]

## Summary
[2-3 sentences — overall health assessment]

## Critical / Must-Fix
| # | Finding | Owner | Priority | Action |
|---|---------|-------|----------|--------|
| ... | ... | ... | ... | ... |

## Important / Should-Fix
| # | Finding | Owner | Priority | Action |
|---|---------|-------|----------|--------|
| ... | ... | ... | ... | ... |

## Improvements / Could-Fix
| # | Finding | Owner | Priority | Action |
|---|---------|-------|----------|--------|
| ... | ... | ... | ... | ... |

## Positive Observations
[What's working well — credit good work]

## Decisions Made
| Decision | Choice | Rationale | Dissent |
|----------|--------|-----------|---------|
| ... | ... | PO's reasoning | [Who disagreed and why] |

## Action Items
| # | Action | Owner | Bead ID | Priority | When |
|---|--------|-------|---------|----------|--------|
| ... | ... | ... | ... | ... | ... |

## Dissent Record
[Any persona that disagreed with a decision — what they said and why, for the record]
```

### Step 6: Create Beads

If a beads database is initialized, create action items as beads with appropriate priorities and dependencies. If no database exists, present the `bd create` commands.

Findings map to beads:
- Critical security → Priority 0, type bug, immediate
- High / Block → Priority 1, type bug
- Medium / Warn → Priority 2, type task or bug
- Low / Nit → Priority 3-4, type chore, backlog

**Creating a bead is not starting the work.** Beads go into the backlog for the PO to prioritize and sequence. Do not propose immediately working on findings after creating them. The review produces a prioritized list — the PO decides what gets worked and when, through grooming and planning ceremonies.
