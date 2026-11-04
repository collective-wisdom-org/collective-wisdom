#!/usr/bin/env bash
# Install or update the agent team in a consuming repo.
# Usage: ./install.sh [--dry-run] <target-repo-path>
set -euo pipefail

usage() { echo "Usage: $0 [--dry-run] <target-repo-path>" >&2; exit 2; }

DRY=0
TARGET=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    -h|--help) usage ;;
    -*) echo "unknown option: $arg" >&2; usage ;;
    *) [ -z "$TARGET" ] || usage; TARGET="$arg" ;;
  esac
done
[ -n "$TARGET" ] || usage

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$ROOT/agent-team"
[ -d "$SRC" ] || { echo "missing $SRC" >&2; exit 1; }
# The version pin written below names HEAD, so the installed files must be exactly HEAD.
git -C "$ROOT" rev-parse --show-toplevel >/dev/null 2>&1 || { echo "Refusing: $ROOT is not a git repo, so the install cannot be pinned to a commit." >&2; exit 1; }
if [ -n "$(git -C "$ROOT" status --porcelain)" ]; then
  echo "Refusing: $ROOT has uncommitted changes, so the install cannot be pinned to a commit." >&2
  echo "Commit or stash them first." >&2
  exit 1
fi
SHA="$(git -C "$ROOT" rev-parse HEAD)"
[ -d "$TARGET" ] || { echo "not a directory: $TARGET" >&2; exit 1; }
TARGET="$(cd "$TARGET" && pwd)"
git -C "$TARGET" rev-parse --show-toplevel >/dev/null 2>&1 || { echo "not a git repo: $TARGET" >&2; exit 1; }

TOUCHED=(.claude scripts docs/agents docs/superpowers/README.md .agents .gitignore AGENTS.md)
DIRTY="$(git -C "$TARGET" status --porcelain -- "${TOUCHED[@]}")"
if [ -n "$DIRTY" ]; then
  echo "Refusing: uncommitted changes in paths this installer touches:" >&2
  echo "$DIRTY" >&2
  echo "Commit or stash them first." >&2
  exit 1
fi

CHANGED=0
TODOS=()
say() { if [ "$DRY" -eq 1 ]; then echo "[dry-run] $*"; else echo "$*"; fi; }
run() { [ "$DRY" -eq 1 ] || "$@"; }

# sync_dir <src dir> <dest dir>: copy files, overwriting; report files that are new or changed.
sync_dir() {
  local s="$1" d="$2" f rel
  while IFS= read -r f; do
    rel="${f#"$s"/}"
    case "$rel" in */__pycache__/*|*.DS_Store|*.pyc) continue ;; esac
    if [ ! -e "$d/$rel" ]; then
      say "add     ${d#"$TARGET"/}/$rel"; CHANGED=$((CHANGED + 1))
    elif ! cmp -s "$f" "$d/$rel"; then
      say "update  ${d#"$TARGET"/}/$rel"; CHANGED=$((CHANGED + 1))
    else
      continue
    fi
    run mkdir -p "$(dirname "$d/$rel")"
    run cp "$f" "$d/$rel"
  done < <(find "$s" -type f | LC_ALL=C sort)
}

# seed_file <src> <dest> <todo text>: copy only when dest is absent.
seed_file() {
  local rel="${2#"$TARGET"/}"
  if [ -e "$2" ]; then return; fi
  say "seed    $rel (from template)"; CHANGED=$((CHANGED + 1))
  run mkdir -p "$(dirname "$2")"
  run cp "$1" "$2"
  TODOS+=("$3")
}

sync_dir "$SRC/.claude/skills" "$TARGET/.claude/skills"
sync_dir "$SRC/.claude/agents" "$TARGET/.claude/agents"

# Skill folders the installer did not ship, named like a shipped skill with a prefix (for example
# acme-ship-loop next to ship-loop), are old copies. Warn; never delete.
for d in "$TARGET/.claude/skills"/*/; do
  [ -d "$d" ] || continue
  name="$(basename "$d")"
  [ -d "$SRC/.claude/skills/$name" ] && continue
  for s in "$SRC/.claude/skills"/*/; do
    shipped="$(basename "$s")"
    case "$name" in
      *-"$shipped")
        say "warn    .claude/skills/$name looks like an old copy of $shipped; delete it"
        TODOS+=("Delete .claude/skills/$name: it looks like an old copy of $shipped.")
        break ;;
    esac
  done
done

# settings.json holds the consumer's own settings too, so never overwrite a differing one.
SET="$TARGET/.claude/settings.json"
if [ ! -e "$SET" ]; then
  say "add     .claude/settings.json"; CHANGED=$((CHANGED + 1))
  run mkdir -p "$TARGET/.claude"; run cp "$SRC/.claude/settings.json" "$SET"
elif ! cmp -s "$SRC/.claude/settings.json" "$SET"; then
  TODOS+=("Merge the Stop hook from agent-team/.claude/settings.json into .claude/settings.json by hand (the file differs, so it was left alone).")
fi

sync_dir "$SRC/scripts" "$TARGET/scripts"

sync_dir "$SRC/docs/agents" "$TARGET/docs/agents"

# Version pin: which collective-wisdom commit the installed files came from.
PIN="$TARGET/docs/agents/installed-from.txt"
PIN_TEXT="collective-wisdom $SHA"
if [ ! -e "$PIN" ]; then
  say "add     docs/agents/installed-from.txt"; CHANGED=$((CHANGED + 1))
  run mkdir -p "$TARGET/docs/agents"; [ "$DRY" -eq 1 ] || echo "$PIN_TEXT" > "$PIN"
elif [ "$(cat "$PIN")" != "$PIN_TEXT" ]; then
  say "update  docs/agents/installed-from.txt"; CHANGED=$((CHANGED + 1))
  [ "$DRY" -eq 1 ] || echo "$PIN_TEXT" > "$PIN"
fi

if [ ! -e "$TARGET/docs/superpowers/README.md" ]; then
  say "add     docs/superpowers/README.md"; CHANGED=$((CHANGED + 1))
  run mkdir -p "$TARGET/docs/superpowers"; run cp "$SRC/docs/superpowers/README.md" "$TARGET/docs/superpowers/README.md"
fi

seed_file "$SRC/templates/project.md" "$TARGET/docs/agents/project.md" \
  "Fill in every <placeholder> in docs/agents/project.md (prefix, repo, commands, invariants). The scripts will not run until the prefix and repo rows are real."
seed_file "$SRC/templates/AGENTS.md" "$TARGET/AGENTS.md" \
  "Fill in the <placeholders> in AGENTS.md (project name, product, stack). Add a CLAUDE.md containing @AGENTS.md if you use Claude Code."

# Codex discovers skills through a relative symlink.
if [ ! -e "$TARGET/.agents/skills" ] && [ ! -L "$TARGET/.agents/skills" ]; then
  say "link    .agents/skills -> ../.claude/skills"; CHANGED=$((CHANGED + 1))
  run mkdir -p "$TARGET/.agents"; run ln -s ../.claude/skills "$TARGET/.agents/skills"
fi

# Append only the gitignore lines that are missing.
GI="$TARGET/.gitignore"
while IFS= read -r line; do
  [ -n "$line" ] || continue
  if [ ! -f "$GI" ] || ! grep -qxF -- "$line" "$GI"; then
    say "ignore  $line"; CHANGED=$((CHANGED + 1))
    if [ "$DRY" -eq 0 ]; then
      if [ -s "$GI" ] && [ -n "$(tail -c1 "$GI")" ]; then echo >> "$GI"; fi
      echo "$line" >> "$GI"
    fi
  fi
done < "$SRC/templates/gitignore"

echo
echo "Done$([ "$DRY" -eq 1 ] && echo ' (dry run, nothing written)'): $CHANGED change(s) in $TARGET"
if [ "${#TODOS[@]}" -gt 0 ]; then
  echo "TODO:"
  for t in "${TODOS[@]}"; do echo "  - $t"; done
fi
echo "Review with 'git -C $TARGET status', then commit."
