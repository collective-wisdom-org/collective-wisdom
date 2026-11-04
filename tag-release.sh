#!/usr/bin/env bash
# Tag origin/main with the next release number (v0.1, v0.2, ...) and push that one tag.
# Usage: ./tag-release.sh [--dry-run]
# This is the maintainer's step. It is not copied into apps and no skill runs it.
set -euo pipefail

usage() { echo "Usage: $0 [--dry-run]" >&2; exit 2; }

DRY=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    *) usage ;;
  esac
  shift
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
git -C "$ROOT" fetch -q --no-tags origin main || { echo "cannot fetch origin in $ROOT" >&2; exit 1; }
# Look the branch up by its exact ref name, so a tag called origin/main cannot stand in for it.
MAIN="$(git -C "$ROOT" show-ref --verify --hash refs/remotes/origin/main 2>/dev/null)" || { echo "Refusing: $ROOT has no origin/main." >&2; exit 1; }

# Release tags are v0.N only; N is compared as a number, so v0.10 follows v0.9.
# Origin is the only source: a local tag that was never pushed, or was deleted there, must not count (and a stale local tag with the next number is replaced).
# Each line is "<tag> <commit>"; an annotated tag lists its commit on a second "^{}" line.
TAG_RE='^v0\.[0-9]+$'
REMOTE="$(git -C "$ROOT" ls-remote --tags origin 'refs/tags/v0.*')" || { echo "cannot list tags on origin in $ROOT" >&2; exit 1; }
TAGS="$(printf '%s\n' "$REMOTE" | awk '{ n = $2; sub("^refs/tags/", "", n); peeled = (n ~ /\^\{\}$/); sub(/\^\{\}$/, "", n); if (peeled || !(n in c)) c[n] = $1 } END { for (n in c) print n, c[n] }' | { grep -E "^v0\.[0-9]+ " || true; })"
HERE="$(printf '%s\n' "$TAGS" | awk -v m="$MAIN" '$2 == m { print $1; exit }')"
[ -z "$HERE" ] || { echo "Refusing: nothing new since $HERE (origin/main is $MAIN)." >&2; exit 1; }

LAST="$(printf '%s\n' "$TAGS" | awk '{ print $1 }' | { grep -E "$TAG_RE" || true; } | sort -t. -k2,2n | tail -n 1)"
TAG="v0.1"
[ -z "$LAST" ] || TAG="v0.$((10#${LAST#v0.} + 1))"

if [ "$DRY" -eq 1 ]; then
  echo "[dry-run] would tag ${MAIN:0:12} as $TAG and push it"; exit 0
fi
git -C "$ROOT" tag -f -a "$TAG" "$MAIN" -m "collective-wisdom $TAG"
git -C "$ROOT" push -q origin "refs/tags/$TAG" || { git -C "$ROOT" tag -d "$TAG" >/dev/null; echo "cannot push $TAG to origin; the local tag was removed." >&2; exit 1; }
echo "tagged ${MAIN:0:12} as $TAG and pushed it"
