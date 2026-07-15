---
name: retro
description: End-of-session retrospective capturing what went well, what the PO could improve, what the agent got wrong, and what would make the project better — with input from every persona that participated.
when_to_use: end of session, retrospective, session review, lessons learned
user-invocable: true
version: 0.1.0
---

# Session Retrospective

Write a retrospective for the current session. Be honest — the PO can take meaningful feedback and expects it.

## Model Selection

If you spawn agents to gather per-persona perspectives, pass `model: sonnet`. Tier modulation does not apply — retros are session-scoped, not component-scoped.

## Process

1. Review the full conversation to understand what happened this session
2. Identify which personas were invoked or relevant (even if not explicitly called via `/skill`)
3. Gather each persona's perspective on the session
4. Write the retrospective file
5. If relevant, update memory with durable lessons learned
6. Run `/retro-sync` to push the retro to the shared repo

## Output Location

Write the retrospective to `~/retros/` named `YYYY-MM-DD-HH_(three-word-topic).md`.

## Anonymization

Retros are synced to a **public, multi-contributor** GitHub repo (see `retro-sync`) so everyone using these skills can learn from them. Keep sensitive data out at generation time:

- Refer to the project by its pseudonym from `~/.claude/retro-project-map.txt` (`project-a` style) — in the filename's topic words and the body. If the project has no entry yet, assign the next unused pseudonym and append it to the map. Never use the real project, product, client, or employer name. Exception: the skill system itself (claude-agent-dev-team) — it's public and the corpus README links to it, so pseudonymizing it is theater
- Never include credentials, tokens, API keys, or connection strings — not even expired or example ones from the session
- No customer/client names, emails, or any PII; refer to people by role ("the PO", "a user")
- No internal hostnames, IPs, or private URLs
- Don't paste verbatim file contents, command output, or data payloads — describe what happened, not the payload. Retros are about process
- Domain specifics that identify the project (unique feature names, table names, ticket prefixes) should be generalized when the lesson doesn't depend on them
- Before writing the file, reread the draft for those categories

The sync step runs a deterministic scrub as a backstop, but a scrub hit means this section failed — write clean in the first place.

## Format

### Header

Begin the file with a level-1 heading derived from the filename (underscore replaced with ` — `). Immediately under the heading, bullet the session metadata:

```markdown
# 2026-04-19-14 — three-word-topic

- **ModelID**: [full model identifier including suffix]
- **TurnCount**: [total user + assistant messages in conversation]
- **SessionDepth**: [light / moderate / deep — how much of the codebase and problem space was explored]
- **Personas Active**: [list of personas invoked or consulted during session]
- **Beads Touched**: [bead IDs created/updated/closed, or "None"]
```

**TurnCount:** Count all user and assistant messages in the conversation. This is a critical metric — failure modes surface late in sessions, not early. The turn count contextualizes when corrections occurred.

**SessionDepth:** Estimate from available signals — how many files read, personas invoked, investigation branches explored. Light = focused single-topic session. Moderate = multi-topic with some exploration. Deep = extensive investigation across multiple domains.

### Section 1: User Value Delivered

What user/customer value did this session actually produce? Be specific:
- What user problem did we address?
- What user outcome did we achieve or move closer to?
- If we shipped something — how will users benefit?
- If we didn't ship — did the work we did move toward a user outcome, or did we create work that creates more work?

If the session produced no measurable user value, say so. That's the most important finding a retro can surface.

### Section 2: What We Did Well Together

One thing — with a concrete moment from the session. Not "good collaboration" — name the specific exchange, decision, or outcome that worked.

### Section 3: What the PO Could Improve

One thing the PO did that made the work harder, slower, or lower quality — even slightly. This is the hardest section to write honestly and the most valuable one. Be specific. Reference the moment. The PO asked for this feedback because they want to improve.

Examples of real feedback, not softened generalizations:
- "The PO changed direction on X after we'd already implemented Y — earlier framing of the constraint would have saved the rework"
- "The PO provided requirements for the security engineer and architect in the same message, which created ambiguity about which persona should lead"
- "The PO answered a clarifying question with 'just do whatever makes sense' — but the question had two reasonable answers with different downstream consequences"

Do NOT write "the PO could provide more context" or other vague politeness. Name the moment.

### Section 4: What the Agent Got Wrong

One thing the agent got wrong or could have handled better. Reference the specific turn or action. This is accountability, not self-deprecation.

Examples:
- "At turn 14, I started implementing before the PO finished framing the architecture — built on a partial frame and had to redo it"
- "I subsampled the beads output instead of reading all of it, which led to a missed dependency"
- "I should have pushed back on the timeline instead of silently accepting scope I knew was too large"

### Section 5: What Would Make the Project Better

One thing that would improve the project, team, or process. This is forward-looking. It could be:
- A gap in the skills/personas
- A process improvement
- A tooling need
- An architectural concern that surfaced during the session
- A pattern that keeps recurring and should be addressed

### Section 6: Persona Perspectives

For each persona that was active or relevant during the session, capture their specific view. Each persona evaluates the session through their professional lens — they do NOT silently agree with each other. Every perspective must address user value.

```markdown
## Persona Perspectives

### Security Engineer
- **User value assessment**: [Did security work this session protect users from real harm, or was it domain-driven compliance?]
- **Session assessment**: [Did security concerns get adequate attention? Were they heard?]
- **What I'd flag**: [Security-relevant observations — framed by user impact]
- **Disagreement**: [Where I disagreed with another persona's approach, if applicable]

### IT Architect
- **User value assessment**: [Did architecture decisions serve the user's needs, or did we architect for the architecture's sake?]
- **Session assessment**: [Were architectural decisions made thoughtfully? Were trade-offs explicit?]
- **What I'd flag**: [Architectural concerns — framed by user impact]
- **Disagreement**: [Where I disagreed with another persona's approach, if applicable]

### Project Manager
- **User value assessment**: [Did the work we organized this session deliver or advance user outcomes? Was any work created that doesn't serve users?]
- **Session assessment**: [Was work organized effectively? Were commitments realistic?]
- **What I'd flag**: [Process or delivery concerns — especially work-creation without user value]
- **Disagreement**: [Where I disagreed with another persona's approach, if applicable]

### Project Engineer
- **User value assessment**: [Did the implementation deliver the user value, or did we build technically sound features nobody asked for?]
- **Session assessment**: [Was the implementation approach sound? Were engineering disciplines followed?]
- **What I'd flag**: [Technical concerns — framed by user impact]
- **Disagreement**: [Where I disagreed with another persona's approach, if applicable]

### UX Designer
- **User value assessment**: [Did we solve the user's actual problem, or did we design for an idealized user?]
- **Session assessment**: [Were user experience implications considered? Was the user's perspective represented?]
- **What I'd flag**: [UX concerns — framed by evidence of user impact, not design preference]
- **Disagreement**: [Where I disagreed with another persona's approach, if applicable]

### Code Reviewer
- **User value assessment**: [Did quality standards serve users (catching bugs they'd experience) or serve internal aesthetics?]
- **Session assessment**: [Was code quality, test quality, and naming discipline maintained?]
- **What I'd flag**: [Quality concerns — framed by user impact]
- **Disagreement**: [Where I disagreed with another persona's approach, if applicable]

### Database Engineer
- **User value assessment**: [Did data work serve user-facing features and performance, or was it schema aesthetics?]
- **Session assessment**: [Were data modeling and schema decisions sound? Were query patterns considered?]
- **What I'd flag**: [Data concerns — framed by user impact]
- **Disagreement**: [Where I disagreed with another persona's approach, if applicable]

### SRE
- **User value assessment**: [Did reliability work protect users' experience, or was it observability for its own sake?]
- **Session assessment**: [Were operational and observability concerns addressed? Were SLOs, instrumentation, and reliability considered?]
- **What I'd flag**: [Reliability concerns — framed by user impact]
- **Disagreement**: [Where I disagreed with another persona's approach, if applicable]

### QA Engineer
- **User value assessment**: [Did testing focus on user-facing behavior, or on coverage metrics?]
- **Session assessment**: [Was the test strategy sound? Were testing gaps identified?]
- **What I'd flag**: [Test concerns — framed by user impact]
- **Disagreement**: [Where I disagreed with another persona's approach, if applicable]

### Technical Writer
- **User value assessment**: [Did documentation serve someone who needs it (user, operator, new dev), or was it documentation for completeness?]
- **Session assessment**: [Was documentation considered? Were decisions and knowledge captured?]
- **What I'd flag**: [Documentation gaps — framed by who is harmed by the gap]
- **Disagreement**: [Where I disagreed with another persona's approach, if applicable]
```

**Rules for persona perspectives:**
- Every persona that was relevant to the session gets a voice — even if they weren't explicitly invoked. If we discussed architecture, the architect has a perspective. If we wrote code, the code reviewer has a perspective
- Personas should disagree with each other when warranted. If the PM thinks the session went great because we shipped fast, and the code reviewer thinks quality was sacrificed, BOTH views go in the retro
- "No concerns" is acceptable only if genuinely true. Do not fill in "no concerns" as a default — think through the session from that persona's lens
- The Disagreement field is the most important one. If every persona agrees, either the session was genuinely excellent or the retro is silently averaging. Check which one it is

### Section 7: Lessons for Future Sessions

Durable lessons that should inform future work. These are candidates for memory — things that won't be obvious from the code or git history.

```markdown
## Lessons

- **Keep**: [Pattern or approach that delivered user value and should be repeated]
- **Stop**: [Pattern or approach that created work without user value]
- **Start**: [Something we should try next time to deliver more user value or less wasted work]
- **Value learning**: [What did we learn about what users actually need vs. what we assumed they needed?]
```

If a lesson is durable enough to warrant saving to memory, do so. If it's session-specific, leave it in the retro.

## Writing Standards

- **Explanatory mode** — thorough, detailed, with specific turn references and concrete moments
- **Honest over diplomatic** — the PO asked for real feedback. Give it
- **Specific over general** — "At turn 23, when we..." not "Sometimes we could..."
- **No self-congratulation** — "What we did well" is about the collaboration, not about how great the agent is
- **No hedging on Section 2** — if the PO made the session harder in any way, say so. Hedging defeats the purpose
- **Personas must not silently average** — if there's tension between perspectives, surface it. That's the point
