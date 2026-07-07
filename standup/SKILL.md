---
name: standup
description: Daily standup — parallel status check across all personas using red/yellow/green scale. Leads with blockers. Green personas stay silent. Fast, focused, action-oriented.
when_to_use: standup, daily standup, status check, daily sync, what's blocked, where are we
user-invocable: true
version: 0.2.0
---

# Daily Standup

Fast. Focused. User value first, blockers second. If everything is green, say so and move on. This is not a planning session, not a review, not a retro. This is "are we delivering user value, what's stuck, what does the PO need to know right now."

## Preflight: Verify Onboarding & Effective Tier

Before any other step, verify deployment-tier setup. Defaulting to enterprise rigor across the board is the failure mode this preflight prevents.

1. **Check `COMPONENTS.md` exists at the repo root.** If missing, **refuse to run** and tell the PO:
   > This project hasn't been onboarded yet. Run `/onboard` first — it produces `COMPONENTS.md`, which records each component's deployment tier. Without it, the standup will surface home-lab components as RED for missing enterprise practices. See `_shared/deployment-tier.md` for the tier model.

   Do not proceed.

2. **Read `COMPONENTS.md`** to know each component's tier. The standup is project-wide, so all components are in scope, but each is rated against its own tier — a home-lab metrics stack is not RED for missing SLOs.

3. **Inject tier context into every agent prompt.** Every prompt below must additionally include:
   ```
   Read ~/.claude/skills/_shared/deployment-tier.md.
   Components and tiers in this project: [component] ([tier]), ...
   When rating R/Y/G, calibrate to each component's tier. A home-lab component is not YELLOW for missing enterprise baseline expectations — it's GREEN if it meets its own tier's baseline. Only flag concerns relative to the component's own tier.
   ```

## Model Selection

When spawning agents, pass `model:` explicitly per `_shared/orchestration.md` (Agent Model Selection). For this skill:
- **Phase 1 (all 10 identity.md triage agents)**: `haiku` — short, formulaic R/Y/G across many parallel agents
- **Phase 2 (non-green deep assessment, 1-3 agents)**: `sonnet` — needs depth on a small number of personas

Tier modulation applies to Phase 2 only. If a persona is assessing a home-lab component, downshift to haiku — except security-engineer, which holds at sonnet (a home-lab CVE is still a CVE).

## Process

### Step 0: Check the Board

Run these commands to get the current state:

```bash
bd status          # Overall project health
bd blocked         # What's stuck and why
bd ready           # What's unblocked and ready to work
bd stale           # What hasn't been touched recently
bd list --status in_progress  # What's actively being worked
```

If no beads database exists, skip to Step 1 and work from conversation context.

### Step 1: Phase 1 — Lightweight Triage (All 10 Voices)

Launch all 10 persona agents simultaneously using the Agent tool. **Spawn as `persona-reviewer` type** (subagent_type: "persona-reviewer") — status triage is read-only. Fall back to `general-purpose` if the type isn't available. Each agent loads ONLY their identity file — not the full persona. This is a triage, not a deep dive:

**Each agent prompt:**
```
Read ~/.claude/skills/[persona]/identity.md for your domain scope and standup triggers.

You are the [Persona]. This is a daily standup triage — be brief.
Advocate for your domain with evidence. Flag concerns, not accommodations.

Current board state:
[paste bd status/blocked/ready/stale output]

Project context:
[brief description of current project state from conversation]

Rate your domain status — framed by user impact:

- RED: Something is actively preventing user value delivery — blocked, broken, or users are being harmed. The PO needs to know NOW
- YELLOW: A concern is developing that could delay or diminish user value delivery. Not blocked yet, but heading that way without action
- GREEN: No concerns from your domain. User value delivery is on track

Rules:
- Use absolute dates, not relative day/week counts. Reframe any tool output that uses days/weeks into absolute dates or hours. See engineering-discipline.md "AI-Native Time Model"
- If you are GREEN, respond with ONLY: "GREEN — no concerns"
- If you are YELLOW, respond in 2-3 sentences: what the concern is, how it affects user value delivery, and what would prevent it from going red
- If you are RED, respond with: what's blocked/broken, what the user/customer impact is, and what you need to unblock it
- Frame everything in terms of user impact. "The architecture isn't elegant" is not RED. "Users will experience 10s page loads because of the architecture" is RED

Do NOT pad your response. Do NOT list what's going well. Do NOT flag domain concerns that don't affect user value delivery.
```

### Step 2: Phase 2 — Deep Assessment (Non-Green Only)

After Phase 1, identify which personas reported RED or YELLOW. **Only for those personas**, spawn a second round of agents that load the **full persona SKILL.md** to provide deeper analysis:

**Each Phase 2 agent prompt:**
```
Read ~/.claude/skills/[persona]/SKILL.md for your full domain expertise.

You are the [Persona]. You flagged a [RED/YELLOW] concern in standup triage:
"[paste their Phase 1 response]"

Advocate for your domain with evidence. Flag specific disagreements with other personas if relevant.

Current board state:
[paste bd status/blocked/ready/stale output]

Project context:
[brief description of current project state from conversation]

Rules:
- Use absolute dates, not relative day/week counts. Reframe any tool output that uses days/weeks into absolute dates or hours. See engineering-discipline.md "AI-Native Time Model"

Provide a deeper assessment (still concise — 5-8 sentences max):
1. What specifically is the issue? Name beads, files, systems, or metrics
2. What is the impact if unaddressed? (Use absolute dates or hours, not "X-week delay")
3. What concrete action resolves or mitigates this?
4. Does this conflict with or depend on another persona's domain?
```

**If ALL personas report GREEN in Phase 1, skip Phase 2 entirely.**

### Step 3: Synthesize — Exception-Based Reporting

After both phases complete, present ONLY the non-green statuses. This is exception-based reporting — silence is good news.

**Output format:**

```markdown
## Standup — [Date]

### Value Delivery Status
- **User value shipped since last standup**: [What user outcomes were delivered, if any]
- **User value at risk**: [Any committed user outcomes that may not be delivered]

### Board Snapshot
- **In Progress**: [count]
- **Blocked**: [count] 
- **Ready**: [count]
- **Stale**: [count] (last activity before [absolute date threshold])

### RED — Immediate Attention
[If any persona reported RED, present their Phase 2 deep assessment]

#### [Persona Name] — RED
[What's blocked/broken, impact, what's needed to unblock — from Phase 2]

### YELLOW — Developing Concerns  
[If any persona reported YELLOW, present their Phase 2 assessment]

#### [Persona Name] — YELLOW
[Concern, trajectory, what prevents it from going red — from Phase 2]

### GREEN — All Clear
[List personas that reported green — one line]
[Persona 1], [Persona 2], [Persona 3], ...

### Blocked Beads
[From bd blocked output — if any]
| Bead ID | Title | Blocked By | Action Needed |
|---------|-------|-----------|---------------|
| ... | ... | ... | ... |

### Stale Beads
[From bd stale output — if any warrant attention. Report last-activity as absolute date, not relative day count]
| Bead ID | Title | Last Activity Date | Assigned To |
|---------|-------|--------------------|-------------|
| ... | ... | YYYY-MM-DD | ... |

### PO Decisions Needed
[If any RED/YELLOW items require a PO decision, list them here. Context column uses absolute dates and hours, not day/week counts]
| Decision | Context | Urgency | Raised By |
|----------|---------|---------|-----------|
| ... | ... | Now / Soon | [Persona] |
```

### Step 4: Done

That's it. No discussion, no deep dive, no planning. If a RED or YELLOW item needs a deeper conversation, suggest the appropriate follow-up:
- Architecture concern → `/it-architect`
- Security concern → `/security-engineer`
- Full team discussion → `/team-review`
- Replanning needed → `/project-manager`

The standup identifies problems. Other skills solve them.

## What Each Persona Checks

Quick reference — every trigger is framed by user/customer impact:

| Persona | RED if... | YELLOW if... |
|---------|----------|-------------|
| **Security Engineer** | Users' data is actively at risk (exploitable vulnerability, breach in progress), security issue blocking feature users need | Compliance deadline approaching that could shut down service for users, medium risk aging without remediation |
| **IT Architect** | Architectural gap preventing delivery of user-facing feature, design choice causing user-visible performance/reliability problems | Architecture decision pending that blocks user value delivery, scaling concern with evidence of real growth |
| **Project Manager** | User value commitment at risk, multiple user-facing items blocked, team producing work without user impact | Scope creep adding work that doesn't serve users, carry-over of user-facing items accumulating |
| **Project Engineer** | Build/deploy broken (can't ship user value), blocked on dependency for user-facing feature, critical user-facing bug | Test failures blocking user-facing feature delivery, technical debt measurably slowing user value delivery |
| **UX Designer** | Design gap blocking user-facing feature, critical usability issue users are actively experiencing | User friction identified but not yet addressed, accessibility regression in shipped feature |
| **Code Reviewer** | Quality issue in user-facing code path, PR for user-facing feature blocked on review | Review queue delaying user value delivery, test quality declining on user-facing features |
| **Database Engineer** | Migration failed blocking user-facing feature, query performance degraded causing user-visible latency, data integrity issue affecting user data | Slow queries approaching user-visible threshold, migration plan missing for upcoming user feature |
| **SRE** | SLO breach (users experiencing degraded service), active incident affecting users, error budget exhausted, can't detect user-facing problems | Error budget burning (users will be affected soon), capacity approaching limits users will hit, alert gaps for user-facing services |
| **QA Engineer** | Test gap on critical user path, flaky tests blocking delivery of user feature, test environment down | Test coverage declining on user-facing features, performance testing overdue for user-facing SLOs |
| **Technical Writer** | Users can't find how to use a shipped feature, runbook gap causing longer user-facing outages, API docs wrong for external consumers | Docs drifting from reality on user-facing features, onboarding docs creating user confusion |

## Rules

- **Standups are fast.** If it takes more than 5 minutes to read the output, it's too long
- **Green is silent.** Don't list what's going well. The PO's attention is for problems
- **Red is specific.** "Things are concerning" is not a standup report. Name the bead, the blocker, the impact
- **Yellow is actionable.** "I'm a bit worried" is not a standup report. State the concern and what prevents it from becoming red
- **No solutioning in standup.** Identify the problem, suggest the follow-up skill, move on
- **Board is truth.** If the board says everything is in progress but nothing has had activity since the last standup, that's a YELLOW at minimum — from the PM if nobody else
- **Domain concerns without user impact are not standup items.** "The code could be cleaner" or "we should add more monitoring" are not RED or YELLOW — they're backlog candidates that need to pass the value gate first
