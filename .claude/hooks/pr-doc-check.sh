#!/usr/bin/env bash
# PostToolUse hook (matcher: Bash). Fires after every Bash call; cheaply no-ops
# unless the command was `gh pr create` or `git push` and the branch has an
# open PR targeting master. When it matches, asks the main agent to run the
# technical-writer subagent against the PR diff.
set -euo pipefail

input="$(cat)"

# Skip if the last commit is technical-writer's own doc-sync commit, to avoid
# re-triggering on the push that follows its fix.
last_msg=$(git log -1 --format=%s 2>/dev/null || true)
if [[ "$last_msg" == *"[docs-sync]"* ]]; then
    exit 0
fi

triggered=false

if grep -qE '"command"[[:space:]]*:[[:space:]]*"[^"]*gh pr create' <<<"$input"; then
    if ! grep -qE '"command"[[:space:]]*:[[:space:]]*"[^"]*--base ' <<<"$input" \
        || grep -qE '"command"[[:space:]]*:[[:space:]]*"[^"]*--base master' <<<"$input"; then
        triggered=true
    fi
elif grep -qE '"command"[[:space:]]*:[[:space:]]*"[^"]*git push' <<<"$input"; then
    pr_info=$(gh pr view --json baseRefName,state -q '"\(.baseRefName) \(.state)"' 2>/dev/null || true)
    if [[ "$pr_info" == "master OPEN" ]]; then
        triggered=true
    fi
fi

if [[ "$triggered" == true ]]; then
    reason="A PR to master was just opened or updated. Invoke the technical-writer subagent (.claude/agents/technical-writer.md) via the Agent tool to check README.md, Mathematical_Specification.md, and backend/app/ docstrings for drift against this PR's diff. If it makes changes, commit them with a message containing the tag [docs-sync] and push to this branch."
    esc=$(printf '%s' "$reason" | sed 's/\\/\\\\/g; s/"/\\"/g')
    printf '{"decision": "block", "reason": "%s"}\n' "$esc"
fi

exit 0
