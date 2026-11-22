#!/usr/bin/env bash
# Wait for a PR's CI checks and print a last line the caller can check.
# Usage: ~/.collective-wisdom/scripts/wait-for-ci.sh <PR number> [--attempt <n>] [--conflicts <n>] [--next]
# Exit 0: checks passed, or the PR has no checks and project.md declares no CI. Exit 1: checks failed.
# Exit 2: could not read or watch, or no checks showed up.
# Exit 3: the PR conflicts with the merge target branch, so CI cannot start. Resolve the conflict, push and run it again.
# The last line is `wait-for-ci: PR #N at <sha>: pass|fail|no CI declared`, `wait-for-ci: PR #N at <sha>: conflict with <target>`,
# `wait-for-ci: no checks on PR #N at <sha> (mergeable <m>, mergeStateStatus <s>)` or `wait-for-ci: cannot read|watch ...`.
# --next prints `next: <instruction>` after that line, from the next_text table below. The caller passes the counts, since the script
# keeps no state: --attempt <n> is which run of this wait it is (1 for the first, 2 for the retry after exit 2; default 1) and
# --conflicts <n> is how many `conflict with` lines the task has already seen (default 0). Without --next the output is unchanged.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cd "$(git rev-parse --show-toplevel)"

# --next: the instruction after the result line, by kind. Where ship-loop § CI waits used to hold this table.
# $1 is the kind; the counts and the target come from the flags and the line itself.
next_text() {
  case "$1" in
    pass) echo "go on. If anything was pushed since the SHA in that line, run wait-for-ci.sh again." ;;
    fail) echo "CI failed: read the failing checks, fix them, push, and run wait-for-ci.sh again." ;;
    no-ci) echo "treat it like pass (merge_pr.py repeats the check at merge). If anything was pushed since the SHA in that line, run wait-for-ci.sh again." ;;
    conflict)
      if [ "$((conflicts + 1))" -ge 3 ]; then
        echo "this is the third conflict line in this run: stop with BLOCKED: quoting this line."
      else
        echo "the PR conflicts with the merge target branch, so CI cannot start: merge origin/$target, resolve what has one clear answer, run the Test command, push, and run wait-for-ci.sh again with --conflicts $((conflicts + 1)); BLOCKED: <question> for anything unclear. Before the first MERGE READY that is open-pr § Primary loop step 1; in an open-pr § Conflict resolution run, that section's step 1."
      fi ;;
    *)
      if [ "$attempt" -ge 2 ]; then
        echo "it did not watch twice: stop with BLOCKED: quoting this line."
      else
        echo "it did not watch: run wait-for-ci.sh again once, with --attempt 2."
      fi ;;
  esac
}

# Print the result line ($2), then its instruction when --next is given. $1 is the kind for next_text.
say() {
  echo "$2"
  if [ "$want_next" -eq 1 ]; then echo "next: $(next_text "$1")"; fi
  return 0
}

n=""
attempt=1
conflicts=0
want_next=0
flags=0
bad=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --next) want_next=1; flags=1; shift ;;
    --attempt | --conflicts)
      flags=1
      if [[ "${2-}" =~ ^[0-9]+$ ]]; then
        if [ "$1" = --attempt ]; then attempt="$2"; else conflicts="$2"; fi
        shift 2
      else
        bad=1
        shift
      fi ;;
    -*) flags=1; bad=1; shift ;;
    *)
      if [ -n "$n" ] || ! [[ "$1" =~ ^[0-9]+$ ]]; then bad=1; fi
      n="$1"
      shift ;;
  esac
done
if [ "$bad" -ne 0 ] || [ -z "$n" ]; then
  if [ "$flags" -eq 1 ]; then
    echo "usage: ~/.collective-wisdom/scripts/wait-for-ci.sh <PR number> [--attempt <n>] [--conflicts <n>] [--next]" >&2
  else
    echo "usage: ~/.collective-wisdom/scripts/wait-for-ci.sh <PR number>" >&2
  fi
  exit 2
fi

if ! sha=$("$here/gh.sh" pr view "$n" --json headRefOid -q .headRefOid) || [ -z "$sha" ]; then
  say cannot "wait-for-ci: cannot read PR #$n"
  exit 2
fi

# Whether docs/agents/project.md declares no CI (`Required CI checks` is `none (no CI yet)`).
# The helper sits next to this script, and a failure is shown, not read as "CI required".
if ! declared=$(python3 -I "$here/project_config.py" no-ci); then
  say cannot "wait-for-ci: cannot read project.md for PR #$n at $sha"
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
# A conflicting PR gets no CI, so each try without checks also reads the PR's merge state.
tries=20
[ "$declared" = yes ] && tries=2
found=0
mergeable=unknown
mstate=unknown
for i in $(seq 1 "$tries"); do
  rc=0
  out=$("$here/gh.sh" pr checks "$n" 2>/dev/null) || rc=$?
  if { [ "$rc" -eq 0 ] || [ "$rc" -eq 1 ] || [ "$rc" -eq 8 ]; } && has_rows "$out"; then
    found=1
    break
  fi
  # UNKNOWN (not computed yet), any other value or a failed read is not a conflict: keep polling.
  if st=$("$here/gh.sh" pr view "$n" --json mergeable,mergeStateStatus -q '.mergeable + " " + .mergeStateStatus' 2>/dev/null) \
    && [[ "$st" =~ ^[A-Z_]+\ [A-Z_]+$ ]]; then
    mergeable="${st% *}"
    mstate="${st#* }"
    if [ "$mergeable" = CONFLICTING ] || [ "$mstate" = DIRTY ]; then
      if ! target=$(python3 -I "$here/project_config.py" target); then
        say cannot "wait-for-ci: cannot read project.md for PR #$n at $sha"
        exit 2
      fi
      say conflict "wait-for-ci: PR #$n at $sha: conflict with $target"
      exit 3
    fi
  fi
  [ "$i" -lt "$tries" ] && sleep 15
done
if [ "$found" -ne 1 ]; then
  if [ "$declared" = yes ]; then
    # `gh pr checks` exits 1 for "no checks" and for a network error alike, so ask for the rollup itself.
    if ! rollup=$("$here/gh.sh" pr view "$n" --json statusCheckRollup -q '.statusCheckRollup | length'); then
      say cannot "wait-for-ci: cannot watch PR #$n at $sha"
      exit 2
    fi
    if [ "$rollup" = 0 ]; then
      say no-ci "wait-for-ci: PR #$n at $sha: no CI declared"
      exit 0
    fi
  fi
  say cannot "wait-for-ci: no checks on PR #$n at $sha (mergeable $mergeable, mergeStateStatus $mstate)"
  exit 2
fi

if "$here/gh.sh" pr checks "$n" --watch --interval 20; then
  say pass "wait-for-ci: PR #$n at $sha: pass"
  exit 0
fi
# --watch also exits non-zero on a gh error. Read the checks once to tell.
rc=0
out=$("$here/gh.sh" pr checks "$n" 2>/dev/null) || rc=$?
if has_rows "$out"; then
  if awk -F'\t' '$2 ~ /^(fail|cancel)$/ { f = 1 } END { exit !f }' <<<"$out"; then
    say fail "wait-for-ci: PR #$n at $sha: fail"
    exit 1
  fi
  if ! awk -F'\t' '$2 == "pending" { f = 1 } END { exit !f }' <<<"$out"; then
    say pass "wait-for-ci: PR #$n at $sha: pass"
    exit 0
  fi
fi
say cannot "wait-for-ci: cannot watch PR #$n at $sha"
exit 2
