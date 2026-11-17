#!/usr/bin/env bash
# Bounded at-least-once delivery. Consumers must remain idempotent.
set -euo pipefail
workflow=${1:?workflow required}
case "$workflow" in
  stock-recommendations.yml|stock-entry-plan.yml|audit-stock-radar-accuracy.yml) ;;
  *) echo 'Unsupported stock handoff target' >&2; exit 2 ;;
esac
[[ ${GITHUB_REPOSITORY:-} =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || exit 2
[[ -n ${GH_TOKEN:-} ]] || exit 2
for attempt in 1 2 3; do
  if gh api --method POST "repos/${GITHUB_REPOSITORY}/actions/workflows/${workflow}/dispatches" -f ref=main; then
    exit 0
  fi
  echo "Stock handoff attempt ${attempt}/3 failed" >&2
  if [[ $attempt -lt 3 ]]; then sleep "$((attempt * 5))"; fi
done
exit 1
