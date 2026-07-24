#!/usr/bin/env bash
# Apply the AI-team review-requiring ruleset to a repo's default branch.
#
# Closes the gap where the review-gate checks exist (.github/workflows/
# ai-team-review-gate.yml) but nothing on the repo requires them, so
# "every merged PR gets a review pass" stays prose-only. Idempotent:
# re-running updates the same ruleset in place.
#
# Usage:
#   scripts/apply-branch-protection.sh <owner>/<repo> [check-name ...]
#
# Defaults to requiring the three checks published by the review-gate
# workflow. Requires `gh` authenticated with admin access to the repo.
# Network-free test: python3 tests/test_branch_protection_bootstrap.py
set -euo pipefail

RULESET_NAME="ai-team-review-gate"
# Check Runs from the review-gate workflow are emitted by the shared
# github-actions App (see .agents/review-gate.json); pinning the
# integration id stops other apps from satisfying the check by name.
GITHUB_ACTIONS_APP_ID=15368

repo="${1:?usage: $0 <owner>/<repo> [check-name ...]}"
shift
checks=("$@")
if [ ${#checks[@]} -eq 0 ]; then
  checks=(
    ai-team/code-review
    ai-team/data-integrity-classification
    ai-team/dba-review
  )
fi

body="$(python3 - "$RULESET_NAME" "$GITHUB_ACTIONS_APP_ID" "${checks[@]}" <<'PY'
import json
import sys

name, app_id, checks = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
print(json.dumps({
    "name": name,
    "target": "branch",
    "enforcement": "active",
    "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
    "rules": [
        # Changes land via PR (no direct pushes); the AI-team checks are the
        # review gate, so no human approval count is imposed here.
        {"type": "pull_request", "parameters": {
            "required_approving_review_count": 0,
            "dismiss_stale_reviews_on_push": False,
            "require_code_owner_review": False,
            "require_last_push_approval": False,
            "required_review_thread_resolution": False,
        }},
        {"type": "required_status_checks", "parameters": {
            "strict_required_status_checks_policy": False,
            "required_status_checks": [
                {"context": check, "integration_id": app_id}
                for check in checks
            ],
        }},
    ],
}))
PY
)"

existing_id="$(gh api "repos/${repo}/rulesets" | python3 -c '
import json, sys
matches = [r["id"] for r in json.load(sys.stdin)
           if r.get("name") == sys.argv[1]]
print(matches[0] if matches else "")
' "$RULESET_NAME")"

if [ -n "$existing_id" ]; then
  gh api --method PUT "repos/${repo}/rulesets/${existing_id}" \
    --input - <<<"$body" >/dev/null
  echo "Updated ruleset '${RULESET_NAME}' (id ${existing_id}) on ${repo}"
else
  gh api --method POST "repos/${repo}/rulesets" \
    --input - <<<"$body" >/dev/null
  echo "Created ruleset '${RULESET_NAME}' on ${repo}"
fi
echo "Required checks on the default branch: ${checks[*]}"
