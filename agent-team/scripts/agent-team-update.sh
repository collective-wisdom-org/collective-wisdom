#!/usr/bin/env bash
# Update this app's agent team to a release tag with one command.
# Usage: scripts/agent-team-update.sh [--dry-run] [--force] [<tag>]
# Clones collective-wisdom into a temp folder and runs that tag's own install.sh --update --from <tag> on this app.
# With no <tag> it takes the highest v0.N on origin/main. $COLLECTIVE_WISDOM_REPO overrides the clone URL.
set -euo pipefail

usage() { echo "Usage: $0 [--dry-run] [--force] [<tag>]" >&2; exit 2; }

PASS=() TAG=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run|--force) PASS+=("$1") ;;
    -h|--help) usage ;;
    -*) echo "unknown option: $1" >&2; usage ;;
    *) [ -z "$TAG" ] || usage; TAG="$1" ;;
  esac
  shift
done
TAG_RE='^v0\.[0-9]+$'
[ -z "$TAG" ] || [[ "$TAG" =~ $TAG_RE ]] || { echo "bad tag: $TAG (expected v0.N)" >&2; usage; }

APP="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "not inside a git repo: run this from your app" >&2; exit 1; }
# collective-wisdom itself has install.sh and agent-team/ at its top; it updates by merging, and an install would write through its links.
if [ -f "$APP/install.sh" ] && [ -d "$APP/agent-team" ]; then
  echo "Refusing: $APP is collective-wisdom itself, which updates by merging, not by installing." >&2; exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
CW="$TMP/cw"
URL="${COLLECTIVE_WISDOM_REPO:-https://github.com/collective-wisdom-org/collective-wisdom.git}"
git clone -q --no-checkout -- "$URL" "$CW" || { echo "cannot clone $URL. Check your git credentials for GitHub (for example 'gh auth setup-git'), or set COLLECTIVE_WISDOM_REPO to an SSH URL." >&2; exit 1; }

if [ -z "$TAG" ]; then
  TAG="$(git -C "$CW" tag --merged refs/remotes/origin/main --list 'v0.*' | { grep -E "$TAG_RE" || true; } | sort -t. -k2,2n | tail -n 1)"
  [ -n "$TAG" ] || { echo "no v0.N tag on origin/main in $URL; ask the maintainer to run tag-release.sh." >&2; exit 1; }
fi
git -C "$CW" rev-parse --verify --quiet "refs/tags/$TAG^{commit}" >/dev/null || { echo "no tag $TAG in $URL" >&2; exit 1; }
# Never run an installer from a commit that is not on origin/main: the installer's own check would be code from that commit checking itself.
git -C "$CW" merge-base --is-ancestor "refs/tags/$TAG" refs/remotes/origin/main 2>/dev/null || { echo "Refusing: $TAG is not on origin/main in $URL, so its installer will not be run." >&2; exit 1; }
git -C "$CW" checkout -q --detach "refs/tags/$TAG"
echo "collective-wisdom $TAG from $URL"

# The installer that runs is the one shipped with the tag, so it and the files come from the same release.
RC=0
bash "$CW/install.sh" --update --from "$TAG" ${PASS[@]+"${PASS[@]}"} "$APP" || RC=$?
exit "$RC"
