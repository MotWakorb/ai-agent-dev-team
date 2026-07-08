---
name: onboard
description: Project onboarding — spawns all 10 personas to assess an existing project cold. Reads the codebase, docs, infrastructure, and git history, then produces a baseline assessment with gaps, risks, and an initial backlog.
when_to_use: onboarding, new project, project assessment, baseline, first look, getting started, project health check
user-invocable: true
version: 0.2.0
---

# Project Onboarding

This skill brings the full team up to speed on an existing project they've never seen. Each persona assesses the project from their domain, producing a baseline understanding with gaps, risks, and recommendations. The lens for every assessment is user value: is this project delivering value to its users, and what's getting in the way?

## Model Selection

When spawning agents, pass `model:` explicitly per `_shared/orchestration.md` (Agent Model Selection). For this skill:
- **IT Architect (leads component identification + tier proposal)**: `opus` — needs reasoning to draft the component list and propose tiers from observable signals
- **Other personas**: `sonnet`

Onboarding runs *before* `COMPONENTS.md` exists, so no tier modulation applies. Use the assignments above as written.

## Process

### Step 0: Gather Project Context

Before spawning agents, collect what's available:

**Project structure:**
```bash
find . -type f -name "*.md" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" -o -name "*.toml" -o -name "*.tf" -o -name "*.py" -o -name "*.ts" -o -name "*.js" | head -100
```

**Documentation (read, not just list):**
```bash
cat README.md 2>/dev/null
cat CLAUDE.md 2>/dev/null
cat CONTRIBUTING.md 2>/dev/null
cat DEVELOPMENT.md 2>/dev/null
cat SECURITY.md 2>/dev/null
cat CHANGELOG.md 2>/dev/null | head -50
ls docs/ adrs/ docs/adrs/ runbooks/ 2>/dev/null
```

**Git history — activity, contributors, releases:**
```bash
git log --oneline -20 2>/dev/null
git shortlog -sn --since="3 months ago" 2>/dev/null
git tag -l --sort=-version:refname | head -10 2>/dev/null
```

**Stack — packages, toolchain versions:**
```bash
cat package.json 2>/dev/null | head -40
cat pyproject.toml 2>/dev/null | head -40
cat requirements.txt 2>/dev/null | head -20
cat go.mod 2>/dev/null | head -10
cat .tool-versions .nvmrc .python-version mise.toml 2>/dev/null
```

**Infrastructure & service topology (read, not just list):**
```bash
cat docker-compose*.yml 2>/dev/null
cat Dockerfile* 2>/dev/null
ls -la terraform/ infrastructure/ deploy/ ansible/ 2>/dev/null
cat .env.example 2>/dev/null
```

**CI/CD (read full workflows):**
```bash
cat .github/workflows/*.yml 2>/dev/null
```

**Database — schema, ORM, migrations:**
```bash
ls -la migrations/ alembic/ 2>/dev/null
cat schema.sql schema.prisma 2>/dev/null | head -50
find . -name "models.py" -o -name "*.entity.ts" -o -name "schema.prisma" 2>/dev/null | head -10
```

**Security — secrets, scanning, auth:**
```bash
ls -la .env .env.* secrets/ vault/ 2>/dev/null
grep -r "SAST\|DAST\|SCA\|security\|trivy\|semgrep\|bandit\|gitleaks" .github/workflows/ 2>/dev/null
```

**Testing — config, fixtures, coverage:**
```bash
ls -la tests/ test/ __tests__/ spec/ 2>/dev/null
cat pytest.ini jest.config.* playwright.config.* .coveragerc 2>/dev/null | head -30
ls -la fixtures/ factories/ conftest.py k6/ locust/ 2>/dev/null
```

**Observability — monitoring, alerting config:**
```bash
cat prometheus.yml alertmanager.yml otel-collector-config.yaml 2>/dev/null | head -30
ls -la grafana/ 2>/dev/null
grep -rl "health\|readiness\|liveness" --include="*.py" --include="*.ts" --include="*.js" | head -5 2>/dev/null
```

**Code quality — linting, formatting, PR templates:**
```bash
cat .eslintrc* .prettierrc* ruff.toml .editorconfig 2>/dev/null | head -30
cat pyproject.toml 2>/dev/null | grep -A 20 "\[tool.ruff\]"
cat .github/pull_request_template.md 2>/dev/null
```

**Design system — frontend artifacts:**
```bash
ls -la storybook/ 2>/dev/null
find . -name "*.stories.*" -o -name "tokens.json" -o -name "theme.ts" 2>/dev/null | head -10
```

**Documentation site:**
```bash
cat mkdocs.yml docusaurus.config.js conf.py 2>/dev/null | head -20
```

**Task runners:**
```bash
cat Makefile justfile 2>/dev/null | head -30
```

**Beads:**
```bash
bd status 2>/dev/null
bd list --status open 2>/dev/null | head -20
```

Collect what's available. **Read files, don't just check existence** — the content is what agents need. Missing items are findings in themselves.

### Step 1: Determine Depth

**Quick mode** — high-level assessment, 30-minute read:
- Each agent produces a status (Green/Yellow/Red) + top 3 findings
- Output is a concise project health scorecard

**Full mode** — deep assessment, thorough analysis:
- Each agent does a complete domain review
- Output is a comprehensive baseline document with detailed findings

Default to **quick** for initial orientation. Use **full** when making investment decisions or before a major project phase.

### Step 2: Spawn Parallel Agents

Launch all 10 persona agents simultaneously using the Agent tool. **IMPORTANT: All agents must be spawned as `general-purpose` type** (subagent_type: "general-purpose"). The persona identity comes from the prompt, not the agent type. Each agent reads its persona skill file as its first action.

**Tier signals during onboarding:** No `COMPONENTS.md` exists yet — that's an output of this onboarding run. Each agent prompt includes the instruction below; the orchestrator synthesizes their tier signals in Step 3.

Add this snippet to **every** agent prompt:

```
Read ~/.claude/skills/_shared/deployment-tier.md.

In addition to your domain assessment:
- Note any **components** you can identify in your domain (services, modules, deployable units, data stores, dashboards, customer-facing surfaces vs. internal tools)
- For each component you mention, propose a deployment tier (home-lab / small-team / startup / enterprise) with a one-line reason based on what you can observe (deployment target, customer-facing references, presence/absence of security scanning, backup discipline, formal docs, etc.)
- If you cannot tell, say so — do not guess
```

The IT Architect leads component identification (the primary author). Other personas contribute tier signals from their domain. The orchestrator reconciles in Step 3.

#### Security Engineer Agent
```
Read ~/.claude/skills/security-engineer/SKILL.md and ~/.claude/skills/_shared/engineering-discipline.md.

You are the Security Engineer. You are seeing this project for the first time. Assess it from a security perspective.

Depth: [quick|full]

Project Context:
[paste gathered context from Step 0]

Assess:
- Attack surface — what's exposed? APIs, endpoints, authentication mechanisms, exposed ports, CORS config
- Dependency health — run vulnerability checks if possible (npm audit, pip-audit, trivy). Known CVEs?
- Security scanning — is SAST/DAST/SCA in the CI/CD pipeline? What tools, what's missing?
- Secrets management — hardcoded credentials? .env files committed? Vault integration?
- Authentication/authorization — how is it implemented? Session management? Any obvious gaps?
- Compliance posture — any regulatory requirements visible? Which frameworks apply?
- Data handling — PII, encryption at rest/transit, data classification, security headers

Rate: RED (active vulnerabilities or critical gaps) / YELLOW (concerns developing) / GREEN (reasonably secure)
```

#### IT Architect Agent
```
Read ~/.claude/skills/it-architect/SKILL.md and ~/.claude/skills/_shared/engineering-discipline.md.

You are the IT Architect. You are seeing this project for the first time. Assess the architecture.

Depth: [quick|full]

Project Context:
[paste gathered context]

Assess:
- Architecture style — monolith, microservices, serverless? Is it appropriate for the problem?
- Technology choices — are they portable? Open-source? Vendor lock-in risks? Exit paths?
- API surface — what APIs exist? Versioned? OpenAPI spec? Data flow between components?
- Scalability path — can this handle 10x? Where are the bottlenecks?
- Operational model — IaC, CI/CD, observability, deployment strategy
- Cost model — any obvious cost inefficiencies?
- Phase assessment — is this Phase 1 (getting started) or Phase 2 (scaling)?
- Single points of failure — what breaks if one component goes down?
- ADR inventory — do architectural decision records exist? Are they current?

**Component inventory (you lead this):** Produce a draft component list — every deployable unit, service, dashboard, data store, or distinct surface you can identify. For each, propose a deployment tier (home-lab / small-team / startup / enterprise) per `deployment-tier.md`, with the signal that drove your choice (e.g., "kubernetes manifests + customer references → startup", "single docker-compose + LAN bind → home-lab"). This draft becomes `COMPONENTS.md` after PO confirmation.

Rate: RED / YELLOW / GREEN
```

#### Project Manager Agent
```
Read ~/.claude/skills/project-manager/SKILL.md and ~/.claude/skills/_shared/engineering-discipline.md.

You are the Project Manager. You are seeing this project for the first time. Assess delivery health.

Depth: [quick|full]

Project Context:
[paste gathered context]

Assess:
- Project organization — is work tracked? Beads, issues, board?
- Backlog health — is there a backlog? Is it groomed? Stale items?
- Velocity signals — git commit frequency, PR merge rate, release cadence, release tags
- Risk visibility — any documented risks? Any obvious undocumented ones?
- Team structure — who's contributing? Bus factor? Stakeholder map?
- Process — any visible ceremonies, conventions, or workflow? CONTRIBUTING.md?
- Documentation of decisions — ADRs, meeting notes, design docs?
- Release history — git tags, versioning convention, release cadence

Rate: RED / YELLOW / GREEN
```

#### Project Engineer Agent
```
Read ~/.claude/skills/project-engineer/SKILL.md and ~/.claude/skills/_shared/engineering-discipline.md.

You are the Project Engineer. You are seeing this project for the first time. Assess implementation quality.

Depth: [quick|full]

Project Context:
[paste gathered context]

Assess:
- Stack — languages, frameworks, versions. Are they current? Toolchain version management (.tool-versions, .nvmrc)?
- Code organization — project structure, module boundaries, separation of concerns, monorepo vs. polyrepo
- Test coverage — unit, integration, E2E. TDD evidence? Test quality?
- CI/CD — pipeline exists? What does it run? Security scans? Deployment automation?
- IaC — Terraform, Ansible, or manual? State management?
- Developer experience — can you set up locally? docker-compose? Makefile/justfile? README setup instructions actually work?
- Technical debt signals — TODO comments, disabled tests, workarounds, version pinning
- Build tooling — task runners, code generation, build artifacts

Rate: RED / YELLOW / GREEN
```

#### UX Designer Agent
```
Read ~/.claude/skills/ux-designer/SKILL.md and ~/.claude/skills/_shared/engineering-discipline.md.

You are the UX Designer. You are seeing this project for the first time. Assess user experience.

Depth: [quick|full]

Project Context:
[paste gathered context]

Assess:
- User-facing interfaces — web, mobile, API, CLI? What exists?
- Design system — is there one? Storybook, design tokens, component library? What CSS approach?
- Accessibility — any evidence of accessibility consideration?
- Error handling UX — loading states, error states, empty states present?
- API design — if API-first, are the contracts clean? Swagger/OpenAPI?
- User documentation — does the end user have docs, help, onboarding?
- Responsive/cross-platform — if web, is it responsive? If multi-platform, consistent?
- Note: if no user-facing interface exists (API-only/backend), focus on API ergonomics and developer experience instead

Rate: RED / YELLOW / GREEN
```

#### Code Reviewer Agent
```
Read ~/.claude/skills/code-reviewer/SKILL.md and ~/.claude/skills/_shared/engineering-discipline.md.

You are the Code Reviewer. You are seeing this project for the first time. Assess code quality and standards.

Depth: [quick|full]

Project Context:
[paste gathered context]

Assess:
- Code style consistency — linting configured (.eslintrc, ruff.toml, .prettierrc)? Formatting enforced? .editorconfig?
- Naming conventions — consistent? Self-describing? Any drift?
- Test quality — meaningful assertions? Anti-patterns? Flaky tests?
- API conventions — naming, response structure, error handling, versioning
- PR practices — branch strategy, review requirements, merge policy, PR templates?
- Dependencies — up to date? Unnecessary? Duplicated functionality?
- Code comments — "why" comments or noise? Missing context on complex logic?
- Branch protection — configured? What blocks merge?

Rate: RED / YELLOW / GREEN
```

#### Database Engineer Agent
```
Read ~/.claude/skills/database-engineer/SKILL.md and ~/.claude/skills/_shared/engineering-discipline.md.

You are the Database Engineer. You are seeing this project for the first time. Assess the data layer.

Depth: [quick|full]

Project Context:
[paste gathered context]

Assess:
- Database engine(s) — what's used? Check docker-compose services and connection strings. Appropriate for the workload?
- Schema design — normalized? Constraints in the database? Foreign keys? Read ORM model files
- Migrations — tooling, versioning, reversibility? Any pending?
- ORM usage — if present, is it generating efficient SQL? ORM configuration?
- Indexing — coverage based on visible query patterns?
- Backup/recovery — any evidence of backup strategy?
- Data volume — any signals about scale? Growth trajectory?
- Database connection patterns — pooling configured? Connection management?

Rate: RED / YELLOW / GREEN
```

#### SRE Agent
```
Read ~/.claude/skills/sre/SKILL.md and ~/.claude/skills/_shared/engineering-discipline.md.

You are the SRE. You are seeing this project for the first time. Assess operational readiness.

Depth: [quick|full]

Project Context:
[paste gathered context]

Assess:
- SLOs — defined? Measured? Error budgets? Check for SLO definition files
- Observability — metrics, logging, tracing present? Structured? Correlated? Check for prometheus.yml, alertmanager.yml, OTel config
- Instrumentation standards — metric naming, log format, cardinality management?
- Alerting — alerts configured? Runbooks exist? Alert fatigue? Check for alerting rules
- Deployment — health checks, readiness probes, graceful shutdown, rollback? Grep for health endpoints
- Dashboards — Grafana provisioning files? Dashboard-as-code?
- Capacity — resource sizing, auto-scaling, headroom?
- Incident preparedness — on-call, escalation, postmortem process? Status page?
- Observability cost — any signals about data volume, retention, cost?

Rate: RED / YELLOW / GREEN
```

#### QA Engineer Agent
```
Read ~/.claude/skills/qa-engineer/SKILL.md and ~/.claude/skills/_shared/engineering-discipline.md.

You are the QA Engineer. You are seeing this project for the first time. Assess test strategy.

Depth: [quick|full]

Project Context:
[paste gathered context]

Assess:
- Test pyramid — shape? Inverted? Missing layers? Check test config files (pytest.ini, jest.config)
- Test environments — local, CI, preprod, performance? Parity with prod?
- Test data — production snapshots, synthetic, hardcoded fixtures? Check fixtures/, factories/, conftest.py
- Performance testing — evidence of load testing (k6/, locust/)? Baselines established?
- Flaky tests — any visible? Skipped tests? Disabled tests?
- Coverage — configured? Reports available? What's the coverage?
- Regression strategy — curated suite or accumulated? Run frequency?
- CI test integration — tests in pipeline? What blocks merge?

Rate: RED / YELLOW / GREEN
```

#### Technical Writer Agent
```
Read ~/.claude/skills/technical-writer/SKILL.md and ~/.claude/skills/_shared/engineering-discipline.md.

You are the Technical Writer. You are seeing this project for the first time. Assess documentation.

Depth: [quick|full]

Project Context:
[paste gathered context]

Assess:
- README — exists? Current? Actually read it — do the setup instructions work, or is it a stub?
- API documentation — exists? Swagger endpoint? Accurate? Docs site (mkdocs, docusaurus, sphinx)?
- Architecture docs — exist? Current? Diagrams? Do they match the actual architecture?
- Runbooks — exist? Tested? Cover all alerts?
- Onboarding guide — can a new person get productive from the docs alone?
- Changelog — exists? Maintained? Follows Keep a Changelog?
- Code comments — sample 2-3 complex files. "Why" comments or noise?
- ADRs — exist? Current? Referenced? Produce an inventory
- CONTRIBUTING.md — exists? Covers branching, PR process, conventions?
- Documentation site — configured? Deployed? Current?
- Produce a documentation inventory as a first-class artifact for the onboarding report

Rate: RED / YELLOW / GREEN
```

### Step 3: Component Inventory & Tier Confirmation

After agents report back, before producing the baseline, reconcile component identification across all personas.

**3a. Consolidate the component list.**
- Start with the IT Architect's draft.
- Add any components other personas mentioned that the architect missed.
- De-duplicate — different personas may name the same component differently. Pick one name per component.

**3b. Reconcile tier proposals.**
For each component, look at every persona's tier proposal. If they agree, that's the proposed tier. If they disagree, pick the highest tier any persona proposed *and* note the disagreement so the PO can adjudicate.

**3c. Present the tier proposal to the PO.**

```markdown
## Proposed Component Tiers

See `_shared/deployment-tier.md` for what each tier expects from each persona.

| Component | Proposed Tier | Reasoning | Persona Disagreement |
|-----------|---------------|-----------|---------------------|
| [name] | [tier] | [signal that drove the proposal] | [if any persona proposed differently, note it; otherwise blank] |

**PO**: confirm or override. Once you confirm, the orchestrator writes `COMPONENTS.md` to the repo root, and subsequent skills (`/team-plan`, `/grooming`, `/standup`, `/spike`, `/team-review`, `/postmortem`) use it to calibrate persona rigor.
```

**3d. After PO confirmation, write `COMPONENTS.md` at the repo root** in the format from `_shared/deployment-tier.md`.

If the PO declines to commit to tiers right now, the onboarding still produces the baseline assessment, but every other team skill will refuse to run until `COMPONENTS.md` exists. Make this trade-off visible: "Without `COMPONENTS.md`, personas will default to enterprise rigor across the board, which is the failure mode this system is designed to prevent."

**3e. Offer to write the project `CLAUDE.md` block** from `_shared/claude-md-project-template.md`. Fill the slots from what onboarding observed — gates from the project engineer's assessment, branching from CONTRIBUTING.md (technical writer), board from whether beads is initialized, deploy from the SRE/architect findings. Present the filled block to the PO before writing. Append inside the managed markers; never touch content outside them — re-onboarding replaces only the block.

### Step 4: Produce the Baseline Assessment

Synthesize all 10 agent assessments into a unified onboarding report.

```markdown
# Project Onboarding: [Project Name]

## Date: [Date]
## Assessed By: Security Engineer, IT Architect, Project Manager, Project Engineer, UX Designer, Code Reviewer, Database Engineer, SRE, QA Engineer, Technical Writer
## Depth: [Quick | Full]

## User Value Assessment

Before the domain scorecard, answer the big question:

- **Who are the users/customers of this project?** [Identified from README, docs, code, or PO input]
- **What value does this project deliver to them?** [What user problem does it solve?]
- **Is the project actively delivering that value?** [Shipped, used, and solving the stated problem — or still building?]
- **What's the biggest risk to user value delivery?** [Cross-domain — not a single persona's concern]

## Health Scorecard

| Domain | Persona | Status | Top Concern (User Impact) |
|--------|---------|:------:|-------------|
| Security | Security Engineer | [R/Y/G] | [One-line — framed by user impact] |
| Architecture | IT Architect | [R/Y/G] | [One-line — framed by user impact] |
| Delivery | Project Manager | [R/Y/G] | [One-line — framed by user impact] |
| Implementation | Project Engineer | [R/Y/G] | [One-line — framed by user impact] |
| User Experience | UX Designer | [R/Y/G] | [One-line — framed by user impact] |
| Code Quality | Code Reviewer | [R/Y/G] | [One-line — framed by user impact] |
| Data Layer | Database Engineer | [R/Y/G] | [One-line — framed by user impact] |
| Operations | SRE | [R/Y/G] | [One-line — framed by user impact] |
| Testing | QA Engineer | [R/Y/G] | [One-line — framed by user impact] |
| Documentation | Technical Writer | [R/Y/G] | [One-line — framed by user impact] |

## Critical Findings (RED items)
[Any domain that rated RED — full details, immediate action required]

## Concerns (YELLOW items)
[Any domain that rated YELLOW — developing issues that need attention]

## What's Working Well (GREEN items)
[Domains that are healthy — credit what's done well]

## Component Inventory & Deployment Tiers

Confirmed in Step 3 and written to `COMPONENTS.md`. See `_shared/deployment-tier.md` for tier definitions.

| Component | Tier | Purpose |
|-----------|------|---------|
| [name] | [tier] | [one-line purpose] |

If `COMPONENTS.md` was deferred (PO declined to set tiers), note that here and flag it as a P0 follow-up — every other team skill will refuse to run until it exists.

## Documentation Inventory

This is a cross-cutting reference — every persona needs to know what docs exist.

| Document | Location | Status | Notes |
|----------|----------|--------|-------|
| README | ./README.md | [Current / Stale / Missing] | [Has setup instructions? / Stub?] |
| API Reference / Swagger | [path or URL] | [Current / Stale / Missing] | ... |
| Architecture Overview | [path] | [Current / Stale / Missing] | ... |
| ADRs | [path] | [X found / Missing] | ... |
| Onboarding Guide | [path] | [Current / Stale / Missing] | ... |
| Runbooks | [path] | [X found / Missing] | ... |
| Changelog | ./CHANGELOG.md | [Current / Stale / Missing] | ... |
| Contributing Guide | ./CONTRIBUTING.md | [Current / Stale / Missing] | ... |
| Security Policy | ./SECURITY.md | [Current / Stale / Missing] | ... |
| Developer Guide | [path] | [Current / Stale / Missing] | ... |
| Design System Docs | [path] | [Current / Stale / Missing] | ... |
| Docs Site | [mkdocs.yml / docusaurus / etc.] | [Exists / Missing] | ... |

## ADR Inventory

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-001] | ... | [Accepted / Superseded / Missing] | ... |
| ... or "No ADRs found" | | | |

## Cross-Domain Findings
[Issues flagged by multiple personas — these are the strongest signals]

| Finding | Flagged By | Impact |
|---------|-----------|--------|
| ... | [Multiple personas] | ... |

## Conflicts Between Personas
[Where personas disagree about the project state — surface both perspectives]

## Recommended First Actions
| # | Action | User Value | Priority | Owner | Rationale |
|---|--------|-----------|----------|-------|-----------|
| 1 | ... | [Who benefits and how] | P0-P3 | [Persona] | ... |
| 2 | ... | [Who benefits and how] | P0-P3 | [Persona] | ... |

## PO Decisions Needed
[If the assessment reveals decisions that need PO input before work begins]

| Decision | Context | Options |
|----------|---------|---------|
| ... | ... | ... |
```

### Step 5: Set Up Project Infrastructure

If beads is not initialized:
```bash
bd init
```

Create initial beads from findings — but apply the value gate first:
- RED findings with direct user impact → Priority 0-1 beads (with user value statement)
- RED findings without direct user impact → discuss with PO before creating beads
- YELLOW findings with user impact → Priority 2 beads (with user value statement)
- YELLOW findings without user impact → note for consideration, not automatic beads
- GREEN items → No beads needed
- Every bead must answer: "Who benefits and how will we know?"

### Step 6: Recommend Next Steps

Based on the assessment, recommend which ceremony to run next:
- Many RED findings → `/team-review` in full mode to deep-dive
- Architecture concerns → `/spike` with Architect + relevant personas
- Backlog empty → `/team-plan` to create the roadmap
- Everything green → Start building, use `/standup` daily

## Rules

- **This is a first impression, not a verdict.** The team is seeing the project cold. Findings may be wrong — context the team doesn't have yet may explain things that look like problems
- **Missing things are findings — but only if they affect users.** No tests on a user-facing checkout flow is a gap. No tests on an internal helper script may be fine. Evaluate missing things by user impact, not by checklist completeness
- **Credit what's done well.** An onboarding report that only lists problems is demoralizing and incomplete. Acknowledge good work explicitly — especially work that clearly delivers user value
- **Cross-domain signals are strongest.** When the Security Engineer and the Code Reviewer independently flag the same issue, that's a higher-confidence finding than either alone
- **Don't prescribe solutions in onboarding.** Identify problems and recommend the right ceremony to solve them. The onboarding report says "what is" — the team-plan says "what to do about it"
- **Onboarding is not work generation.** Resist the urge to find a problem in every domain. Some domains may be fine. "No concerns" from 4 of 10 personas is a healthy project, not an incomplete assessment
