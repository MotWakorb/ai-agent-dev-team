---
name: retro-mine
description: Mine the shared retro corpus (~/retros, synced from EndofLineTech/retros) for recurring patterns and turn them into proposed rule changes for the claude-agent-dev-team skill system. Evidence-clustered, PO-decided — the skill proposes, the PO approves.
when_to_use: mine retros, retro mining, retro analysis, retro-driven upgrades, what are the retros telling us, turn retros into actions
user-invocable: true
version: 0.1.0
---

# Retro Mine

Turn the retro corpus into actionable changes to this skill system. This formalizes the "retro-driven rule additions" passes previously done by hand (see CHANGELOG). Run it from the claude-agent-dev-team repo — the output targets its skill files.

Retros are the stress test for skill rules: patterns found here become rules, and future retros validate them. Both directions matter — new patterns need new rules, and *recurring* patterns that already have rules mean the rule isn't working.

## Process

1. **Sync** — run `/retro-sync` so `~/retros/` has everyone's latest retros.

2. **Watermark** — `retro-mine/LAST_MINED` in this repo holds the filename of the newest retro covered by the last pass. Retro filenames are date-prefixed, so "new" = every date-prefixed file (`~/retros/20*.md`) sorting after it — ignore the corpus README. Missing watermark = mine the whole corpus.

3. **Extract** — spawn reader agents (`persona-reviewer`, `model: sonnet`), ~5 retros per agent. Each returns, per retro, only what's structurally reusable:
   - Agent failure modes (what the agent got wrong, and at what point in the session)
   - PO friction (what made the work harder — process, not personality)
   - Process/skill gaps (Section 5 and persona "What I'd flag" entries)
   - Keep / Stop / Start lessons
   - For each: a one-line candidate rule and the skill file that would own it

   Readers quote the retro (filename + line) as evidence — no paraphrase-only findings.

4. **Cluster** (orchestrator) — group findings across retros by failure family and owning file:
   - **≥2 retros** showing the same pattern → rule candidate
   - **1 retro** → watch item; record it, don't propose a rule yet
   - Pattern already covered by an existing rule → check the rule's landing date (`git log` on the owning file). Recurrences in retros dated *after* the rule landed are a **rule-not-working** signal — propose strengthening or enforcement (hook), not a duplicate rule

5. **Propose** — for each rule candidate: owning file + section, draft rule text, and the evidence list (retro filenames). Present as a `## DECISIONS NEEDED` block per `_shared/decision-prompts.md`. Do NOT edit skill files before the PO approves — findings are proposals by default, not immediate work.

6. **Apply approved changes** — edit the approved files, add a CHANGELOG `[Unreleased]` entry naming the retro count and date range (existing convention: "N retros, YYYY-MM-DD → YYYY-MM-DD"), update `retro-mine/LAST_MINED` to the newest retro covered, and carry unapproved watch items in the report only — they'll resurface next pass if they recur.

## Model Selection

Readers: `sonnet`. Clustering and rule drafting stay with the orchestrator — cross-retro judgment is the deliverable. Tier modulation does not apply (session-scoped meta-work).

## Rules

- Evidence over vibes: every proposed rule cites ≥2 retro files; every watch item cites its one
- Corpus is pseudonymized (`project-a` style) — patterns are process-level, which is exactly what transfers to skill rules
- Don't frame proposals as needing a pre-ship gate — future retros are the validation mechanism
- Effort estimates in proposals use AI-realistic scale (minutes/hours, not weeks)
