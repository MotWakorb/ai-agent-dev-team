# Decision Prompts — Format Reference

The rule lives in `orchestration.md` §"Decision Prompts": any message containing both synthesis/status/findings AND something for the PO to decide ends with a `## DECISIONS NEEDED` block. This file is the full format — read it before writing your first decision block of a session.

## When the block fires

The trigger is "decision exists," not "decision count" — a single buried decision is the failure mode this guards against.

Exempt: messages that are *only* a question with no surrounding synthesis. The message itself is the decision; no block needed.

## Block format

The block uses a numbered list. Each entry has three lines: state, decision, options. Keep entries short — comprehensive context (persona excerpts, bead cross-references) belongs in artifacts, not in the block.

Example shape (literal):

    ## DECISIONS NEEDED

    1. **MCP key rotation cadence**
       - State: bd-826k3 open; user waiting on guidance
       - Decision: rotate every 30d or 90d?
       - Options:
         - 30d — tighter security, more ops toil
         - 90d — industry baseline, less friction

    2. **Stats v2 backfill window**
       - State: backfill script ready, run not scheduled
       - Decision: backfill full history or last 90d only? (depends on #1 if rotation forces a re-key)
       - Options:
         - Full — ~6h runtime, complete data
         - 90d — ~30m runtime, recent-only

Numbered so the PO can answer "1: 90d, 2: full" and move on.

## Dependencies and ordering

If decisions depend on each other, order them so dependents come after their dependency, and note the dependency in plain text inside the dependent's entry ("depends on #1"). The PO can answer in sequence or override.

## Cap and one-by-one mode

Hard cap: 3 decisions per message. 4+ means split across messages — dumping is the failure mode this guards against.

One-by-one mode: surface decisions sequentially when:
- A decision has 4+ options
- A decision has cross-cutting implications across personas
- The PO has signaled they want focused discussion ("let's talk through it")

The orchestrator can offer one-by-one explicitly ("Walk through these one at a time, or stack them?"); the PO can request it at any time.

## Single-digit answers are not validation

When the PO answers with a single digit ("2") or a single word ("Go"), that's a signal the format is working. But it's also a signal there's no backpressure when a prompt is overloaded — the PO will push through rather than push back. Don't rely on the PO to tell you a prompt is too dense; keep them short by default.

## Anti-pattern

A decision prompt that requires scrolling back through 3+ prior messages to understand the options. If you're tempted to write "as discussed above" or "per the earlier analysis," the entry in the block needs a self-contained recap, not a back-reference.
