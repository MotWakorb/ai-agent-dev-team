# AI Team Review Gate Bootstrap

This home-lab bootstrap workflow creates the three Check Runs consumed by the
AI Agent Dev Team merge hook. Run its network-free test with:

```bash
python3 tests/test_ai_team_review_gate.py
```

To make these checks actually required before merge, apply the branch
ruleset to the target repo (idempotent, requires `gh` with admin access):

```bash
scripts/apply-branch-protection.sh <owner>/<repo>
```

## Accepted trust boundary

The checks are a maintainer attestation by GitHub actor ID `31100779`
(`MotWakorb`) that the named persona reviews completed for the exact pull
request head. They do **not** prove that an independent reviewer identity
performed those reviews.

The workflow uses `GITHUB_TOKEN`, so Check Runs are attributed to the generic
`github-actions` App shared by workflows in the repository. The same maintainer
credential can both ship code and dispatch this attestation. The Product Owner
explicitly accepts those residual risks for this one-time, home-lab bootstrap.

Do not reuse this trust model at a higher deployment tier. Small-team and above
require a dedicated GitHub App for the checks and a second authorization
principal who cannot unilaterally ship and attest.

## Replay behavior

Before publishing, the workflow reads every prior classification Check Run on
the immutable head with `filter=all` and pagination. A prior
`classification:data-integrity` can never be replaced by `classification:other`.
Malformed, unsuccessful, or conflicting prior classifier runs fail closed.
Repeating the same classification is allowed and refreshes all three checks.
