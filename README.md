# Claude Agent Dev Team

A set of Claude Code skills that simulate a full software development team with distinct professional personas. Each persona has domain expertise, professional biases, and the authority to disagree with the others. This is not a committee that politely agrees — it's a team that argues, commits, and ships.

## Installation

**macOS / Linux:**
```bash
git clone https://github.com/MotWakorb/claude-agent-dev-team.git
cd claude-agent-dev-team
./install.sh
```

**Windows (PowerShell 5.1+):**
```powershell
git clone https://github.com/MotWakorb/claude-agent-dev-team.git
cd claude-agent-dev-team
./install.ps1
```

Updates are just `git pull` — symlinks pick up changes automatically. If upgrading from a version before orchestration discipline was added, re-run the installer to set up `~/.claude/CLAUDE.md` and the enforcement hook.

The installer also registers a PreToolUse hook in `~/.claude/settings.json` (`hooks/pretooluse.py`) that converts the mechanically decidable orchestration rules from prose to guarantees — see [Enforcement Hooks](#enforcement-hooks). Windows: the hook is not yet wired into `install.ps1`.

### Project-Scoped Install

If you don't want the team in your entire Claude workflow, install it into a single project instead:

```bash
./install.sh --project /path/to/your/project
```

Everything lands under that project — skills in `.claude/skills/`, the `persona-reviewer` agent in `.claude/agents/`, the enforcement hook in `.claude/hooks/` + `.claude/settings.json`, and the orchestration block in the project's `CLAUDE.md`. Claude Code picks all of it up only in that project; the rest of your workflow is untouched.

Project installs are copies, not symlinks, so they're self-contained: commit `.claude/` and `CLAUDE.md` and every teammate who clones the project gets the whole team with zero setup. The hook command uses `$CLAUDE_PROJECT_DIR`, so nothing user-specific is baked in. After a `git pull` in this repo, re-run the installer to update the copies.

For a personal install that stays out of the project's git history, add `--local` — the hook registers in `.claude/settings.local.json` and the installer prints the `.gitignore` lines to add. Uninstall with `./uninstall.sh --project /path/to/your/project`.

One global exception either way: `/retro` writes to `~/retros`, so retrospectives span projects.

### Recommended: beads

The team works best with [beads](https://github.com/steveyegge/beads) (`bd`) as its work board. Every ceremony assumes it by default: `/team-plan` files epics and beads, `/grooming` refines them, `/standup` reads them, `/release-check` gates on them, and the PM tracks risk through them. Without beads the skills still run — they fall back to conversation context — but nothing persists between sessions, which defeats much of the point of a standing team.

Install beads, then run `bd init` in each project alongside `/onboard`. If you use a different tracker (Jira, Linear, GitHub Issues), swap the board tool in `project-manager/SKILL.md` — see [Customization](#customization).

## Why

LLMs have a tendency to "silently average" — producing safe, consensus-driven output that avoids conflict. In real teams, the best outcomes come from domain experts who advocate hard for their perspective, disagree openly, and then commit fully once a decision is made. 99% alignment, 1% vision.

This project creates that dynamic by giving each persona:
- **Domain authority** — each role owns their decisions within their expertise
- **Professional bias** — each role naturally advocates for and is skeptical of specific things
- **Known failure modes** — documented LLM tendencies (subsampling, theorizing before reading evidence, premature implementation) with corrective behaviors front-loaded
- **Conflict resolution protocol** — structured disagreement with clear escalation paths
- **A voice in retrospectives** — every persona evaluates the session through their lens

The result: when you run `/team-plan` or `/team-review`, ten agents work in parallel, each bringing their genuine domain perspective, and the synthesis surfaces real conflicts for the Product Owner to decide — not smoothed-over consensus.

## Project Onboarding (Required Before Team Skills Run)

After installing the skills, you need to onboard each project before the team ceremonies (`/team-plan`, `/grooming`, `/standup`, `/spike`, `/team-review`, `/postmortem`) will run. Onboarding produces a `COMPONENTS.md` at the repo root that identifies each component and assigns it a **deployment tier**.

### Why This Exists

LLM training data is saturated with enterprise practices. Without a tier signal, personas default to recommending SLOs, on-call rotations, formal threat models, and SOC 2 controls for *every* project — including a Raspberry Pi running a home Plex server. That's wasteful and produces noise that crowds out real findings.

`COMPONENTS.md` tells personas what rigor each component actually expects. A home-lab metrics stack is rated against home-lab expectations. A customer-facing API is rated against startup or enterprise expectations. Right rigor for the right context.

### The Flow

```bash
# 1. Install the skills (one time per machine)
./install.sh

# 2. In each project, run /onboard
cd /path/to/your/project
# In Claude Code: /onboard
#   - Reads the codebase, docs, infra config, and CI/CD
#   - Identifies components (services, dashboards, deployable units)
#   - Proposes a deployment tier per component with observed signals
#   - You confirm or override
#   - Writes COMPONENTS.md at the repo root
#   - Offers to write a project CLAUDE.md block (gates, branching, board,
#     deploy — the per-project facts personas need every session)

# 3. Now the team ceremonies work
# In Claude Code: /team-plan, /grooming, /standup, /team-review, /spike, /postmortem
```

### What Happens Without Onboarding

`/team-plan`, `/grooming`, `/standup`, `/spike`, `/team-review`, and `/postmortem` **refuse to run** if `COMPONENTS.md` is missing. They tell you to run `/onboard` first.

`/onboard` itself does not require `COMPONENTS.md` — producing it is the job. `/retro` is session-scoped (not component-scoped) and runs without `COMPONENTS.md`.

Single-persona invocations (e.g., `/sre`, `/security-engineer`) ask which tier the work is for if `COMPONENTS.md` doesn't exist or doesn't cover the component.

### The Tier Model

| Tier | What it means | Stakes if it breaks |
|------|---------------|---------------------|
| **home-lab** | Personal infrastructure, single user, hobbyist context | Inconvenience for the operator |
| **small-team** | Internal tool used by a small group, not customer-facing | Team productivity hit |
| **startup** | External users, real business stakes, resource-constrained | Customer churn, revenue impact |
| **enterprise** | Large user base, regulatory or contractual obligations | Legal exposure, regulatory penalty |

Tier is **per-component, not per-project** — a project can have a home-lab metrics stack alongside a startup-tier customer API. When work spans tiers, **strictest tier wins** by default (or surface as a decision when applying it across the board would be clearly wasteful).

See [`_shared/deployment-tier.md`](./_shared/deployment-tier.md) for the full per-persona calibration table — what each tier expects from SRE, security, architect, DBA, code reviewer, tech writer, QA, etc.

## The Team

| Persona | Slash Command | Domain |
|---------|--------------|--------|
| **Security Engineer** | `/security-engineer` | **Protector role.** Guards the system and its users from harm. AppSec, infrastructure/network security, multi-cloud, compliance (OWASP, NIST CSF, CIS, ISO 27001, SOC 2, Zero Trust). Risk ratings measured by harm prevented, not checklist completeness |
| **IT Architect** | `/it-architect` | Right architecture for the user's problem, not the most impressive one. Phase 1 (solve user's problem) and Phase 2 (only when evidence demands it). Open-source first, no vendor lock-in, cost-aware |
| **Project Manager** | `/project-manager` | Project coordinator. Optimizes for user value delivery — every bead must trace to a user need. Work planning, backlog management, **value gate** owner, risk tracking using [beads](https://github.com/steveyegge/beads) (`bd`). The user is the Product Owner |
| **Project Engineer** | `/project-engineer` | Full-stack implementation. Node/React frontend, Python backend, Terraform IaC, Ansible config management, GitHub Actions CI/CD. TDD — tests first. Simplest implementation that delivers user value |
| **UX Designer** | `/ux-designer` | The user's advocate. Solves actual user problems with the simplest design that works. API-first — every wireframe includes the API call that powers it. Evidence-based design over design intuition |
| **Code Reviewer** | `/code-reviewer` | Quality conscience — focuses rigor on code paths that affect users. Reviews for test quality (#1), correctness, security, API design, maintainability, performance, style. Quality proportional to user impact. Mentoring tone |
| **Database Engineer** | `/database-engineer` | **Protector role.** Guards data integrity, system stability, and performance. Schema design, query optimization, migration safety. Constraints belong in the database. Safety first, then access patterns |
| **SRE** | `/sre` | **Protector role.** Guards production reliability and operational stability. SLOs, observability platform & instrumentation standards, incident response, capacity planning, on-call, chaos engineering, observability cost management |
| **QA Engineer** | `/qa-engineer` | **Protector role.** Last line of defense before code reaches users. Test strategy, test environments, test data, performance testing, regression curation. Test investment proportional to risk, not feature visibility |
| **Technical Writer** | `/technical-writer` | Every doc answers "who reads this and what do they need?" API docs, runbooks, onboarding guides, architecture docs, changelogs. Documentation effort proportional to user impact |

## Team Skills

| Skill | Command | Purpose |
|-------|---------|---------|
| **Team Plan** | `/team-plan` | Spawns all 10 personas in parallel to analyze a project brief. Surfaces conflicts, facilitates debate, produces unified plan with PO decision points |
| **Team Review** | `/team-review` | Spawns all 10 personas in parallel to review existing work. Consolidates findings, surfaces disagreements, produces prioritized action items |
| **Standup** | `/standup` | Two-phase daily pulse. Phase 1: lightweight triage (identity tier only) — red/yellow/green, green stays silent. Phase 2: deep assessment for non-green personas only. User value framing throughout |
| **Grooming** | `/grooming` | Backlog refinement with **user value gate** — items must articulate who benefits before personas evaluate. Batch mode: all items in one pass per persona. Sizes effort, identifies dependencies, defines acceptance criteria |
| **Spike** | `/spike` | Targeted investigation — spawns only relevant personas to answer a specific question blocking a decision. Thorough, evidence-based |
| **Postmortem** | `/postmortem` | Blameless incident analysis — SRE-led, timeline-driven, evidence-based. Contributing factors from each relevant persona, action items tracked as beads |
| **Onboard** | `/onboard` | Project onboarding — all 10 personas assess an existing project cold, produce a health scorecard (R/Y/G), documentation inventory, and initial backlog |
| **Retrospective** | `/retro` | End-of-session retrospective. Honest assessment including PO feedback, agent self-critique, and each persona's perspective with disagreements |

## Operational Skills

Single-purpose orchestrator skills that guard a specific operational concern. They don't spawn personas — they enforce a checklist or gate against the orchestrator's own actions.

| Skill | Command | Purpose |
|-------|---------|---------|
| **Release Check** | `/release-check` | Pre-release semantic readiness — verifies open P0/P1 bugs are clear, in-flight verification agents have completed, and the PO has explicitly confirmed before any release-execution agent fires |
| **Retro Sync** | `/retro-sync` | Scrub, pseudonymize, and push local retros in `~/retros/` to the shared public corpus at [EndofLineTech/retros](https://github.com/EndofLineTech/retros). Push-only — `/retro-mine` pulls the corpus down |
| **Retro Mine** | `/retro-mine` | Mine the retro corpus for recurring patterns and turn them into proposed rule changes for this skill system. Evidence-clustered (≥2 retros = rule candidate, 1 = watch item), detects rules that aren't working, PO approves before any edit |

## Shared Foundations

| File | Purpose |
|------|---------|
| `_shared/conflict-resolution.md` | How personas disagree and resolve conflicts. Domain authority, escalation to PO, disagree-and-commit protocol. Critical security findings are non-negotiable |
| `_shared/engineering-discipline.md` | Evidence over intuition. Verify before asserting. Completeness over sampling. Known failure modes. Naming discipline. One-way door protocol |
| `_shared/orchestration.md` | Orchestrator discipline — how Claude dispatches agents, isolates worktrees, picks models per task, compresses decisions, and avoids merging past in-flight verification. Auto-loaded via `~/.claude/CLAUDE.md` (or the project's `CLAUDE.md` for project-scoped installs) |
| `_shared/deployment-tier.md` | Tier definitions (home-lab / small-team / startup / enterprise) and per-persona calibration tables. Personas read this to right-size their recommendations to the deployment context |
| `_shared/claude-md-project-template.md` | Template for the project `CLAUDE.md` block `/onboard` offers to write — the per-project facts (board, gates, branching, deploy) personas need every session |
| `*/identity.md` | Condensed identity tier for each persona — used by two-phase standup, quick-mode `/team-plan` and `/team-review`, default `/grooming`, and lightweight triage. Domain authority, professional biases, and standup triggers in ~15 lines |

## Key Design Decisions

### Conflict Is Expected
Each persona has a "Professional Perspective" section that defines what they advocate for, what they're skeptical of, and when they should push back even if everyone else agrees. The security engineer fights for security. The PM fights for shipping. The UX designer fights for the user. These biases collide — by design.

### Protector Roles
Four personas are explicitly framed as **protectors** — their domain authority exists to guard something, not to serve feature delivery on demand:
- **Security Engineer** — guards the system and its users from harm
- **Database Engineer** — guards data integrity, stability, and performance
- **SRE** — guards production reliability and operational stability
- **QA Engineer** — last line of defense before code reaches users

Protectors can say no. Their findings don't need to justify themselves through feature delivery — preventing harm is the justification. This framing counteracts the LLM tendency to accommodate and smooth over legitimate domain concerns.

### User Value Lens
Every persona is oriented toward delivering **user outcomes**, not domain work. The PM owns a **value gate** — no work enters the backlog without a stated user benefit ("who benefits and how will we know?"). Standup triggers are framed by user impact ("users will experience 10s page loads" not "the architecture isn't elegant"). Domain expertise serves user needs — it doesn't generate them.

### Tier-Aware Personas
Personas calibrate to the **deployment tier** of the component they're working on (`home-lab` / `small-team` / `startup` / `enterprise`). The SRE doesn't recommend SLOs and on-call rotations for a Raspberry Pi; the security engineer doesn't write a SOC 2 gap analysis for an internal scratch tool. Tier is set per-component in `COMPONENTS.md` (produced by `/onboard`) and read by every team ceremony before agents spawn. See `_shared/deployment-tier.md` for the per-persona calibration tables.

### Per-Task Model Selection
Each persona's `SKILL.md` declares a default model in frontmatter (`model: sonnet`). Skill orchestrators override per task type — `haiku` for fast triage (Phase 1 standup), `sonnet` for most domain work, `opus` for sticky decisions (architecture proposals, security findings, root cause analysis). At home-lab tier, models downshift one level (except security-engineer holds — a home-lab CVE is still a CVE). See `_shared/orchestration.md` "Agent Model Selection" for the full mapping.

### Two-Tier Identity System
Each persona has two files:
- **`SKILL.md`** — Full persona definition with methodologies, frameworks, output formats (~200+ lines)
- **`identity.md`** — Condensed identity for lightweight triage (~15 lines: domain authority, biases, standup triggers)

The standup uses a **two-phase approach**: Phase 1 loads only `identity.md` for fast red/yellow/green triage across all 10 personas. Phase 2 loads the full `SKILL.md` only for personas that reported non-green. This optimizes token usage — a fully green standup costs ~10% of what loading all full personas would.

### Security Escalation Tiers
- **Critical (9.0-10.0)**: Non-negotiable. PO cannot override. Work stops
- **High (7.0-8.9)**: Gets priority. PO sequences but can't defer indefinitely
- **Medium (4.0-6.9)**: PO weighs cost of fix against actual risk
- **Low/Informational (0.0-3.9)**: Lowest priority. Address when convenient

### Engineering Discipline
Front-loading known LLM failure modes into each persona produces significantly better session outcomes. The project engineer gets a deep version with explicit failure modes. All personas reference the shared principles. The cost of ~100 lines of context at session start is far cheaper than reworking things because the agent wouldn't follow instructions the first time.

### Tiered Security Scanning
- **Dev**: No scan gates. Move fast, break things
- **Preprod**: All scans must pass (SAST, DAST, SCA, IaC, secrets, containers). This is the gate
- **Prod**: Same artifact that passed preprod. Manual approval + smoke tests

### The PO Has Final Say (With One Exception)
The Product Owner makes all product and priority decisions. The one exception: Critical security findings are non-negotiable — no one overrides them, not even the PO.

### Enforcement Hooks

Prompt-level rules (CLAUDE.md, SKILL.md) are advisory — they lose to context drift, compaction, and "it's just a 1-line edit" rationalizations. `hooks/pretooluse.py`, registered by install.sh, enforces the mechanically decidable rules deterministically, and its deny messages act as just-in-time reminders at the exact moment of violation:

| Rule | Trigger | Effect |
|------|---------|--------|
| **Orchestrator edit block** | Main agent calls Edit/Write/NotebookEdit on a project file in an onboarded project (`COMPONENTS.md` present) | Denied — dispatch the owning persona. `COMPONENTS.md`, `CLAUDE.md`, `.claude/` config, and files outside the project tree stay writable (orchestrator territory) |
| **Ceremony gate** | A team ceremony (`/team-plan`, `/grooming`, `/standup`, `/spike`, `/team-review`, `/postmortem`) invoked without `COMPONENTS.md` | Denied — run `/onboard` first. The prose "refuses to run" is now a guarantee |
| **Persona bead firewall** | A subagent runs `bd create/close/delete/reopen` | Denied — board state transitions are orchestrator territory; findings are reported, the PO decides. `bd update` stays allowed |
| **Bead-referenced commits** | `git commit -m` without a bead id in a repo with `.beads/` | Denied — include the bead id, or the literal `[no-bead]` for genuinely untracked commits |

The hook distinguishes orchestrator from subagent via the `agent_id` field in hook input (present only for subagents). Semantic rules — merge authorization, definition of done, backlog sign-off — can't be mechanically decided and stay in `_shared/orchestration.md`. This repo itself is exempt (meta-work on the skill system is direct-edit territory). Self-check: `python3 hooks/pretooluse.py --check`.

## Install Options

> **Windows note:** Creating symlinks may require running as Administrator or enabling Developer Mode (Settings > Update & Security > For developers).

**Bash:**
```bash
./install.sh                        # Symlink (default) — git pull updates automatically
./install.sh --copy                 # Copy instead — for customization without affecting the repo
./install.sh --project <dir>        # Project-scoped install into <dir>/.claude (copies, committable)
./install.sh --project <dir> --local  # Project-scoped, personal (settings.local.json, gitignored)
./install.sh --help                 # Show options
```

**PowerShell:**
```powershell
./install.ps1            # Symlink (default)
./install.ps1 -Copy      # Copy instead
```

> **Windows gap:** `install.ps1` does not yet register the enforcement hook, install the `persona-reviewer` agent definition, or support `--project`. Skills and the CLAUDE.md orchestration block install fine.

**Uninstall:**
```bash
./uninstall.sh                    # macOS/Linux (global)
./uninstall.sh --project <dir>    # Remove a project-scoped install
./uninstall.ps1                   # Windows
```

### Manual Install

If you prefer to copy specific skills:

```bash
mkdir -p ~/.claude/skills
cp -R _shared ~/.claude/skills/_shared
cp -R security-engineer ~/.claude/skills/security-engineer
# ... copy whichever skills you want
mkdir -p ~/retros
```

### Project-Specific Install

To install for a single project instead of globally, copy into your project's `.claude/skills/` directory.

## Versioning & Rollback

This project uses semantic versioning at the system level. Releases are git tags (`v0.2.0`, etc.). Each `SKILL.md` carries a `version:` field in its frontmatter showing the system version it last changed in.

**Check what's installed:**
```bash
grep -E "^name:|^version:" ~/.claude/skills/*/SKILL.md
```

**Update to latest** (symlink installs pick up changes automatically):
```bash
cd /path/to/claude-agent-dev-team
git pull
```

**Pin to a specific version** (or roll back):
```bash
cd /path/to/claude-agent-dev-team
git checkout v0.2.0    # or any tag
# Symlink installs now resolve to that tag's content
```

**If you installed with `--copy`**, re-run the installer after switching tags:
```bash
git checkout v0.2.0
./install.sh --copy
```

See [CHANGELOG.md](./CHANGELOG.md) for what changed in each release.

## Usage

### Individual Personas

Invoke any persona directly for domain-specific consultation:

```bash
/security-engineer Review the authentication module for vulnerabilities
/it-architect Design a system for real-time event processing
/project-manager Plan the next work cycle based on the current backlog
/project-engineer Implement the user registration endpoint
/ux-designer Design the onboarding flow for new users
/code-reviewer Review this PR for quality and consistency
/database-engineer Design the schema for the orders system
/sre Define SLOs and instrumentation plan for the payment service
/qa-engineer Create a test strategy for the checkout flow
/technical-writer Audit the documentation for the API
```

### Ceremonies

Use ceremonies to coordinate the full team:

```bash
/standup             # Daily pulse — red/yellow/green, blockers only
/grooming            # Refine backlog items for readiness
/team-plan           # Full team planning for a new project or work cycle
/spike               # Targeted investigation to unblock a decision
/team-review         # Full team review of existing work
/postmortem          # Blameless incident analysis
/retro               # End-of-session retrospective
/retro-sync          # Scrub + push local retros to the shared public corpus
/retro-mine          # Mine the retro corpus into proposed skill-system rule changes
```

### Operational Skills

Single-purpose orchestrator skills — no persona spawns, just a checklist or gate:

```bash
/release-check       # Pre-release readiness gate — verifies P0/P1 bugs clear, in-flight verification done, PO confirms
```

### Ceremony Workflow

Here's when to use each ceremony in a typical project lifecycle:

```
Any Project (Required First — see "Project Onboarding" above)
  └─ /onboard ──────────── Identify components, assign deployment tiers, write COMPONENTS.md
                            + health scorecard + initial backlog

New Project (after /onboard)
  └─ /team-plan (full) ─── Deep planning, all personas, architecture + security + UX + implementation
       └─ Creates initial epics and beads

Work Cycle
  ├─ /grooming ─────────── Refine upcoming backlog items before planning
  ├─ /team-plan (quick) ── Work planning — commit work, identify dependencies
  ├─ /standup ──────────── Status check — red/yellow/green, blockers, PO decisions
  ├─ /spike ───────────── As needed — unblock decisions with targeted investigation
  ├─ /team-review ─────── Review — evaluate what shipped
  └─ /retro ───────────── End of session — honest assessment, persona perspectives

When Things Break
  └─ /postmortem ────────── Blameless analysis, timeline, root cause, action items as beads
```

### Quick vs Full Mode

`/team-plan`, `/team-review`, and `/grooming` support depth modes:
- **Quick**: Bullet points, top 2-3 conflicts, concise output. Agents load `identity.md` only — a fraction of the per-agent context of a full persona load
- **Full**: Complete structured output per each persona's format. Agents load full `SKILL.md` plus the shared discipline docs

`/spike` always targets only relevant personas (2-4), not all 10.
`/standup` uses two-phase triage — Phase 1 loads `identity.md` only for fast R/Y/G, Phase 2 loads full `SKILL.md` for non-green personas only. Green is silent.
`/grooming` runs in batch mode — each persona evaluates all items in a single pass, with a user value gate before any persona is spawned. Grooming agents load `identity.md` by default; **deep-groom** (PO-requested, or beads flagged complex at the value gate) loads full `SKILL.md` for the relevant personas only.
`/postmortem` includes only personas relevant to the incident.

## How the Team Interacts

Every persona carries a "Relationship to Other Personas" section documenting its side of each significant relationship — its own obligations and expectations, not a restatement of the other side's. The two sides of a relationship are complementary by design (the engineer's "argue a Block with technical reasoning" pairs with the reviewer's "welcome pushback and evaluate it"). Each persona knows:
- What they own (domain authority)
- What other personas own (where to defer)
- Where they'll naturally disagree (professional bias)
- How to resolve conflicts (shared protocol)

### Key Tension Points

These are by design — the personas will argue about these:

| Tension | Personas | What They'll Argue About |
|---------|----------|------------------------|
| Security vs. Speed | Security ↔ PM, Engineer | How much security for Phase 1? Scope vs. remediation |
| Complexity vs. Simplicity | Architect ↔ Engineer | Is this design over-engineered or appropriately future-proof? |
| Quality vs. Velocity | Code Reviewer ↔ Engineer, PM | Style blocks when there's pressure to ship |
| User Experience vs. Constraints | UX ↔ Security, Architect, Engineer | Security friction, architectural limits, technical feasibility |
| Reliability vs. Features | SRE ↔ PM | Error budget spent — feature freeze or keep shipping? |
| Data Integrity vs. Speed | DBA ↔ Engineer, Architect | Normalize or denormalize? Migration safety vs. velocity |
| Observability Cost vs. Signal | SRE ↔ Architect, Engineer | 100% trace sampling vs. budget — SRE owns both sides since the Observability Engineer merged into the SRE role |
| Test Coverage vs. Shipping | QA ↔ PM, Engineer | Performance testing before launch or after? |
| Documentation vs. "Later" | Technical Writer ↔ Everyone | Is docs part of done, or a follow-up that never happens? |

### RACI Matrix

R = Responsible (does the work), A = Accountable (final decision), C = Consulted (input before decision), I = Informed (notified after)

This matrix was reviewed by all personas in parallel. Contested decisions were resolved by the PO. The Observability Engineer was merged into the SRE — the SRE now owns the observability platform, instrumentation standards, and cost management in addition to reliability.

#### Design & Planning

| Activity | PO | PM | Arch | SecEng | Eng | UX | CR | DBA | SRE | QA | TW |
|----------|:--:|:--:|:----:|:------:|:---:|:--:|:--:|:---:|:---:|:--:|:--:|
| **Requirements & Scope** | A | R | C | C | I | C | I | C | I | C | C |
| **Architecture Design** | A | I | R | C | C | C | I | C | C | C | C |
| **Technology Selection** | A | C | R | C | C | C | C | C | C | C | I |
| **API Contract Design** | A | I | R | C | C | C | C | C | I | C | C |
| **ADRs** | A | C | R | C | C | I | C | C | C | I | C |
| **UX Design** | A | I | C | C | I | R | I | I | I | C | C |
| **Design System Definition** | A | I | C | C | C | R | C | I | I | I | C |
| **Schema / Data Modeling** | A | I | C | C | C | I | I | R | I | I | I |
| **DR/HA Design** | A | C | R | C | C | C | I | C | C | C | C |
| **Cost Modeling** | A | C | R | I | C | I | I | C | C | I | I |

#### Security & Compliance

| Activity | PO | PM | Arch | SecEng | Eng | UX | CR | DBA | SRE | QA | TW |
|----------|:--:|:--:|:----:|:------:|:---:|:--:|:--:|:---:|:---:|:--:|:--:|
| **Security Assessment** | A | I | C | R | C | I | C | C | C | I | C |
| **Threat Modeling** | A | I | C | R | C | I | I | C | I | C | C |
| **Compliance & Audit** | A | C | C | R | C | I | I | C | I | I | C |
| **Secrets Management** | I | C | C | A | R | I | C | I | C | I | C |
| **Security Scan Pipeline** | I | I | C | A | C | I | I | I | R | I | I |

#### Implementation & Quality

| Activity | PO | PM | Arch | SecEng | Eng | UX | CR | DBA | SRE | QA | TW |
|----------|:--:|:--:|:----:|:------:|:---:|:--:|:--:|:---:|:---:|:--:|:--:|
| **Implementation** | A | I | C | C | R | C | C | C | C | C | I |
| **Code Review** | I | I | I | C | C | C | R | C | C | I | I |
| **TDD / Unit+Integration Tests** | I | I | I | C | R | I | C | C | I | C | I |
| **Test Strategy** | A | I | C | C | C | I | C | C | C | R | I |
| **Test Environment Management** | I | C | C | C | C | I | I | C | C | R | I |
| **Test Data Strategy** | I | I | I | C | C | I | I | C | I | R | I |
| **Performance Testing** | I | I | C | C | C | I | I | C | C | R | I |
| **Chaos / Resilience Testing** | I | C | C | C | C | I | I | C | R | C | C |

#### Infrastructure & Operations

| Activity | PO | PM | Arch | SecEng | Eng | UX | CR | DBA | SRE | QA | TW |
|----------|:--:|:--:|:----:|:------:|:---:|:--:|:--:|:---:|:---:|:--:|:--:|
| **IaC (Terraform/Ansible)** | A | I | R | C | R | I | I | I | C | C | C |
| **CI/CD — Build & Deploy** | I | C | C | C | R | I | C | C | R | C | I |
| **CI/CD — Test Gates** | I | I | I | C | C | I | C | I | C | R | I |
| **Deployment** | A | C | C | C | R | C | C | C | R | C | C |
| **Database Migration** | A | I | C | C | C | I | C | R | C | C | C |
| **Backup & Recovery** | A | C | C | C | C | I | I | R | C | C | C |
| **Capacity Planning** | A | C | C | I | C | I | I | C | R | I | I |

#### Observability & Reliability

| Activity | PO | PM | Arch | SecEng | Eng | UX | CR | DBA | SRE | QA | TW |
|----------|:--:|:--:|:----:|:------:|:---:|:--:|:--:|:---:|:---:|:--:|:--:|
| **Observability Design** | A | I | C | C | C | C | C | C | R | C | I |
| **Observability Platform & Standards** | I | I | C | C | C | C | C | C | R | C | C |
| **SLO Definition** | A | I | C | C | C | C | I | I | R | I | C |
| **Alert / Runbook Design** | I | I | C | C | C | I | I | I | R | I | C |
| **Incident Response** | I | C | C | R | C | C | I | C | R | I | C |
| **Postmortem** | I | C | C | R | C | I | I | C | R | C | C |

#### Process & Documentation

| Activity | PO | PM | Arch | SecEng | Eng | UX | CR | DBA | SRE | QA | TW |
|----------|:--:|:--:|:----:|:------:|:---:|:--:|:--:|:---:|:---:|:--:|:--:|
| **Work Planning** | A | R | I | I | C | I | I | C | C | C | C |
| **Backlog Grooming** | A | R | C | C | C | C | C | C | C | C | C |
| **Release Management** | A | R | C | C | C | C | C | I | R | C | C |
| **Risk Management** | A | R | C | C | C | I | I | I | C | I | I |
| **Documentation** | I | I | C | C | C | C | C | C | C | C | R |
| **Documentation Audit** | I | C | I | I | I | C | I | I | I | I | R |
| **Onboarding Guide** | I | C | C | C | C | C | C | C | C | C | R |

**Key principles:**
- **PO is Accountable** for all product decisions — requirements, scope, architecture, deployment, risk acceptance
- **PM is Responsible** for process — work planning, grooming, release management, risk management
- **Domain experts are Responsible** for their domain — Security owns assessments and threat modeling, DBA owns schema and backups, SRE owns incidents and capacity, QA owns test strategy and environments
- **Architect is Responsible** for API contract design, ADRs, DR/HA design, cost modeling, and co-R on IaC
- **Security Engineer is Accountable** for secrets management and the scan pipeline — sets policy, others implement
- **Activities are split where co-ownership was contested** — CI/CD (Build & Deploy vs. Test Gates), Test Strategy vs. TDD/Unit+Integration
- **Everyone is Consulted** during grooming — every persona evaluates backlog items
- **Implementation involves the whole team** — DBA, SRE, UX, QA, and CR are all Consulted, not just Informed

### Conflict Resolution

All conflicts follow the shared protocol (`_shared/conflict-resolution.md`):
1. **Domain authority decides within their domain** — Security on risk, Architect on design, Code Reviewer on quality
2. **Cross-domain conflicts escalate to the PO** — the PO weighs trade-offs and decides
3. **Critical security findings are non-negotiable** — no one overrides, not even the PO
4. **Disagree and commit is documented** — the ADR or bead captures what, who, and why

## Customization

These skills are designed to be adapted. If you install with `--copy`, you can modify freely. If you install with symlinks (default), fork the repo first or copy individual skills you want to customize.

### What to Customize

| What | Where | Why |
|------|-------|-----|
| **Technology stack** | `project-engineer/SKILL.md` | Default is Node/React + Python + Terraform + Ansible. Change to your stack |
| **Security frameworks** | `security-engineer/SKILL.md` | Default is OWASP, NIST CSF, CIS, ISO 27001, SOC 2, Zero Trust. Add HIPAA, PCI-DSS, GDPR, etc. |
| **Board tool** | `project-manager/SKILL.md` | Default is [beads](https://github.com/steveyegge/beads) (`bd`). Swap for Jira CLI, Linear, GitHub Issues, etc. |
| **API conventions** | `code-reviewer/SKILL.md` | Default is REST with snake_case, versioned URLs, standard envelopes. Adjust for GraphQL, gRPC, etc. |
| **Design system** | `ux-designer/SKILL.md` | Default is build-from-scratch. Point to your existing design system |
| **Observability stack** | `sre/SKILL.md` | Default evaluates per-project. Set your standard stack (Datadog, Grafana Cloud, etc.) |
| **Database preferences** | `database-engineer/SKILL.md` | Default is PostgreSQL-primary. Adjust for your data platform |
| **Retro location** | `retro/SKILL.md` | Default is `~/retros/`. Change to your preferred location |
| **Retro sync target** | `retro-sync/SKILL.md` | Default is the shared public [EndofLineTech/retros](https://github.com/EndofLineTech/retros). Point at your own repo (private if you prefer) — the scrub still runs |
| **Conflict resolution** | `_shared/conflict-resolution.md` | Adjust domain authority boundaries, security escalation tiers, or the disagree-and-commit protocol |
| **Engineering discipline** | `_shared/engineering-discipline.md` | Add your own known failure modes, naming conventions, or principles |
| **Orchestration rules** | `_shared/orchestration.md` | Default rules for agent dispatch, worktree isolation, decision compression. Adjust for your workflow |

### Adding New Personas

To add a new persona, create a directory with a `SKILL.md`:

```
~/.claude/skills/my-persona/SKILL.md
```

Follow the pattern established by existing personas:
1. YAML frontmatter (`name`, `description`, `when_to_use`, `user-invocable: true`)
2. Reference the shared engineering discipline and conflict resolution protocol
3. Define the persona's domain, philosophy, and methodology
4. Add a Professional Perspective section (what they advocate for, what they're skeptical of)
5. Add a Conflict Resolution section with domain-specific guidance
6. Add Relationship sections for every other persona they interact with
7. Define structured output formats
8. Create an `identity.md` — condensed identity (~15 lines) with domain authority, professional biases, and standup triggers
9. Update `team-plan/SKILL.md` and `team-review/SKILL.md` to include the new persona's agent prompt

## Project Structure

```
claude-agent-dev-team/
├── _shared/
│   ├── claude-md-project-template.md # Project CLAUDE.md block template (written by /onboard)
│   ├── conflict-resolution.md       # Conflict resolution protocol
│   ├── decision-prompts.md          # DECISIONS NEEDED block format reference
│   ├── deployment-tier.md           # Tier definitions + per-persona calibration tables
│   ├── engineering-discipline.md    # Engineering discipline principles
│   └── orchestration.md            # Orchestrator discipline (agent dispatch, isolation, model selection, decisions)
├── agents/
│   └── persona-reviewer.md          # Read-only agent type for review-mode dispatch (no Edit/Write) — installed to ~/.claude/agents/
├── hooks/
│   └── pretooluse.py                # PreToolUse enforcement dispatcher (see Enforcement Hooks) — registered in settings.json by install.sh
├── security-engineer/
│   ├── SKILL.md                     # Full persona — Security Engineer (protector)
│   └── identity.md                  # Condensed identity for triage
├── it-architect/
│   ├── SKILL.md                     # Full persona — IT Architect
│   └── identity.md
├── project-manager/
│   ├── SKILL.md                     # Full persona — Project Manager (value gate owner)
│   └── identity.md
├── project-engineer/
│   ├── SKILL.md                     # Full persona — Project Engineer
│   └── identity.md
├── ux-designer/
│   ├── SKILL.md                     # Full persona — UX Designer (user advocate)
│   └── identity.md
├── code-reviewer/
│   ├── SKILL.md                     # Full persona — Code Reviewer
│   └── identity.md
├── database-engineer/
│   ├── SKILL.md                     # Full persona — Database Engineer (protector)
│   └── identity.md
├── sre/
│   ├── SKILL.md                     # Full persona — SRE + Observability (protector)
│   └── identity.md
├── qa-engineer/
│   ├── SKILL.md                     # Full persona — QA Engineer (protector)
│   └── identity.md
├── technical-writer/
│   ├── SKILL.md                     # Full persona — Technical Writer
│   └── identity.md
├── team-plan/SKILL.md               # Team planning ceremony
├── team-review/SKILL.md             # Team review ceremony
├── standup/SKILL.md                 # Two-phase daily standup ceremony
├── grooming/SKILL.md                # Backlog refinement with value gate
├── spike/SKILL.md                   # Technical spike ceremony
├── postmortem/SKILL.md              # Incident postmortem ceremony
├── onboard/SKILL.md                 # Project onboarding ceremony
├── release-check/SKILL.md           # Pre-release semantic readiness gate
├── retro/SKILL.md                   # Session retrospective ceremony
├── retro-sync/                      # Retro scrub + push to shared public corpus
│   ├── SKILL.md
│   └── scrub.sh                     # Deterministic redaction/pseudonymization pass
├── retro-mine/                      # Retro corpus → proposed skill-system rule changes
│   ├── SKILL.md
│   └── LAST_MINED                   # Watermark: newest retro covered by the last pass
├── install.sh                       # Installer script (macOS/Linux)
├── install.ps1                      # Installer script (Windows)
├── uninstall.sh                     # Uninstaller script (macOS/Linux)
├── uninstall.ps1                    # Uninstaller script (Windows)
├── CHANGELOG.md                     # Per-release changes — Keep a Changelog format
├── CONTRIBUTING.md                  # Contributor guide (versioning, PR conventions)
├── LICENSE                          # MIT License
└── README.md                        # This file
```

## Credits

- The concept of a multi-persona bot crew was inspired by [warrentc3](https://github.com/warrentc3)
- The engineering discipline and identity primer approach was inspired by collaborative work with the dev community building effective agent-assisted development patterns.

## License

MIT
