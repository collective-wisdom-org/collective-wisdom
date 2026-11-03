#!/usr/bin/env bash
# Wait for a PR's CI checks and print a last line the caller can check.
# Usage: scripts/wait-for-ci.sh <PR number>
# Exit 0: checks passed. Exit 1: checks failed. Exit 2: could not read or watch.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "$#" -ne 1 ] || ! [[ "$1" =~ ^[0-9]+$ ]]; then
  echo "usage: scripts/wait-for-ci.sh <PR number>" >&2
  exit 2
fi
n="$1"

if ! sha=$(./scripts/gh.sh pr view "$n" --json headRefOid -q .headRefOid) || [ -z "$sha" ]; then
  echo "wait-for-ci: cannot read PR #$n"
  exit 2
fi

# True when gh printed at least one check row: name, status, ...
has_rows() {
  awk -F'\t' '$2 ~ /^(pass|fail|pending|skipping|cancel)$/ { f = 1 } END { exit !f }' <<<"$1"
}

# Right after a push GitHub can report no checks yet, and --watch exits at once.
# Poll every 15 s for up to 5 min until at least one check exists.
found=0
for _ in $(seq 1 20); do
  rc=0
  out=$(./scripts/gh.sh pr checks "$n" 2>/dev/null) || rc=$?
  if { [ "$rc" -eq 0 ] || [ "$rc" -eq 1 ] || [ "$rc" -eq 8 ]; } && has_rows "$out"; then
    found=1
    break
  fi
  sleep 15
done
if [ "$found" -ne 1 ]; then
  echo "wait-for-ci: no checks on PR #$n at $sha"
  exit 2
fi

if ./scripts/gh.sh pr checks "$n" --watch --interval 20; then
  echo "wait-for-ci: PR #$n at $sha: pass"
  exit 0
fi
# --watch also exits non-zero on a gh error. Read the checks once to tell.
rc=0
out=$(./scripts/gh.sh pr checks "$n" 2>/dev/null) || rc=$?
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
