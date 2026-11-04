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

# `Required CI checks` from docs/agents/project.md (PROJECT_MD overrides the file). Empty when unset.
required=$(python3 -I -c 'import sys; sys.path.insert(0, sys.argv[1]); import project_config; print(project_config.value("Required CI checks") or "")' "$PWD/scripts" 2>/dev/null || true)
no_ci="none (no CI yet)"

# True when gh printed at least one check row: name, status, ...
has_rows() {
  awk -F'\t' '$2 ~ /^(pass|fail|pending|skipping|cancel)$/ { f = 1 } END { exit !f }' <<<"$1"
}

# Right after a push GitHub can report no checks yet, and --watch exits at once.
# Poll every 15 s for up to 5 min until at least one check exists.
# A repo that declares no CI polls twice (one 15 s wait): enough to catch a check that shows up late.
tries=20
[ "$required" = "$no_ci" ] && tries=2
found=0
gh_error=0
for i in $(seq 1 "$tries"); do
  rc=0
  out=$("$here/gh.sh" pr checks "$n" 2>/dev/null) || rc=$?
  if { [ "$rc" -eq 0 ] || [ "$rc" -eq 1 ] || [ "$rc" -eq 8 ]; } && has_rows "$out"; then
    found=1
    break
  fi
  # An exit other than 0, 1 or 8 (gh gives auth failures code 4) is not "no checks"; it must not read as no CI.
  # Other gh errors (network, 5xx, rate limit) also exit 1, like "no checks reported", and still read as no checks.
  if [ "$rc" -ne 0 ] && [ "$rc" -ne 1 ] && [ "$rc" -ne 8 ]; then gh_error=1; fi
  [ "$i" -lt "$tries" ] && sleep 15
done
if [ "$found" -ne 1 ] && [ "$gh_error" -eq 0 ] && [ "$required" = "$no_ci" ]; then
  echo "wait-for-ci: PR #$n at $sha: no CI declared"
  exit 0
fi
if [ "$found" -ne 1 ]; then
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
