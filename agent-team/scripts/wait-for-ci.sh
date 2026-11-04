#!/usr/bin/env bash
# Wait for a PR's CI checks and print a last line the caller can check.
# Usage: scripts/wait-for-ci.sh <PR number>
# Exit 0: checks passed, or the PR has no checks and project.md declares no CI. Exit 1: checks failed.
# Exit 2: could not read or watch.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cd "$(git rev-parse --show-toplevel)"

if [ "$#" -ne 1 ] || ! [[ "$1" =~ ^[0-9]+$ ]]; then
  echo "usage: scripts/wait-for-ci.sh <PR number>" >&2
  exit 2
fi
n="$1"

if ! sha=$("$here/gh.sh" pr view "$n" --json headRefOid -q .headRefOid) || [ -z "$sha" ]; then
  echo "wait-for-ci: cannot read PR #$n"
  exit 2
fi

# Whether docs/agents/project.md declares no CI (`Required CI checks` is `none (no CI yet)`).
# The helper sits next to this script, and a failure is shown, not read as "CI required".
if ! declared=$(python3 -I "$here/project_config.py" no-ci); then
  echo "wait-for-ci: cannot read project.md for PR #$n at $sha"
  exit 2
fi

# True when gh printed at least one check row: name, status, ...
has_rows() {
  awk -F'\t' '$2 ~ /^(pass|fail|pending|skipping|cancel)$/ { f = 1 } END { exit !f }' <<<"$1"
}

# Right after a push GitHub can report no checks yet, and --watch exits at once.
# Poll every 15 s for up to 5 min until at least one check exists.
# A repo that declares no CI polls twice (one 15 s wait). A check that registers later is still caught:
# merge_pr.py reads the rollup at merge and holds the PR until every check on it has passed.
tries=20
[ "$declared" = yes ] && tries=2
found=0
for i in $(seq 1 "$tries"); do
  rc=0
  out=$("$here/gh.sh" pr checks "$n" 2>/dev/null) || rc=$?
  if { [ "$rc" -eq 0 ] || [ "$rc" -eq 1 ] || [ "$rc" -eq 8 ]; } && has_rows "$out"; then
    found=1
    break
  fi
  [ "$i" -lt "$tries" ] && sleep 15
done
if [ "$found" -ne 1 ]; then
  if [ "$declared" = yes ]; then
    # `gh pr checks` exits 1 for "no checks" and for a network error alike, so ask for the rollup itself.
    if ! rollup=$("$here/gh.sh" pr view "$n" --json statusCheckRollup -q '.statusCheckRollup | length'); then
      echo "wait-for-ci: cannot watch PR #$n at $sha"
      exit 2
    fi
    if [ "$rollup" = 0 ]; then
      echo "wait-for-ci: PR #$n at $sha: no CI declared"
      exit 0
    fi
  fi
  echo "wait-for-ci: no checks on PR #$n at $sha"
  exit 2
fi

if "$here/gh.sh" pr checks "$n" --watch --interval 20; then
  echo "wait-for-ci: PR #$n at $sha: pass"
  exit 0
fi
# --watch also exits non-zero on a gh error. Read the checks once to tell.
rc=0
out=$("$here/gh.sh" pr checks "$n" 2>/dev/null) || rc=$?
if has_rows "$out"; then
  if awk -F'\t' '$2 ~ /^(fail|cancel)$/ { f = 1 } END { exit !f }' <<<"$out"; then
    echo "wait-for-ci: PR #$n at $sha: fail"
    exit 1
  fi
  if ! awk -F'\t' '$2 == "pending" { f = 1 } END { exit !f }' <<<"$out"; then
    echo "wait-for-ci: PR #$n at $sha: pass"
    exit 0
  fi
fi
echo "wait-for-ci: cannot watch PR #$n at $sha"
exit 2
