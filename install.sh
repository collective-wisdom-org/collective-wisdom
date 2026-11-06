#!/usr/bin/env bash
# Install this clone for the machine, or install, update or check the agent team in a consuming repo.
# Usage: ./install.sh [--dry-run]
#        ./install.sh [--dry-run] [--to <ref> | --from <tag>] <target-repo-path>
#        ./install.sh [--dry-run] --update [--to <ref> | --from <tag>] [--force] <target-repo-path>
#        ./install.sh --check <target-repo-path>
# --from <tag> is --to for a release tag (v0.N): it fetches the tag from origin and records it in the pin.
set -euo pipefail
export GIT_NO_REPLACE_OBJECTS=1  # a replace ref must not change which tree gets copied for a pinned SHA

usage() {
  {
    echo "Usage: $0 [--dry-run]"
    echo "       $0 [--dry-run] [--to <ref> | --from <tag>] <target-repo-path>"
    echo "       $0 [--dry-run] --update [--to <ref> | --from <tag>] [--force] <target-repo-path>"
    echo "       $0 --check <target-repo-path>"
  } >&2
  exit 2
}

DRY=0 UPDATE=0 FORCE=0 CHECK=0 REF="" FROM="" TARGET=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --update) UPDATE=1 ;;
    --force) FORCE=1 ;;
    --check) CHECK=1 ;;
    --to) [ "$#" -ge 2 ] || usage; REF="$2"; shift ;;
    --from) [ "$#" -ge 2 ] || usage; FROM="$2"; shift ;;
    -h|--help) usage ;;
    -*) echo "unknown option: $1" >&2; usage ;;
    *) [ -z "$TARGET" ] || usage; TARGET="$1" ;;
  esac
  shift
done

# --- Machine install: no target path. Links this clone into $HOME; touches no app. ---

# tilde <path>: the path with $HOME shortened to ~, for messages.
tilde() { case "$1" in "$HOME"/*) echo "~${1#"$HOME"}" ;; *) echo "$1" ;; esac; }

# mlink <src> <dest>: link dest to src. A real file or folder, or a link to somewhere else, stays and is listed.
mlink() {
  local src="$1" dest="$2" cur
  if [ -L "$dest" ]; then
    cur="$(readlink "$dest")"
    [ "$cur" = "$src" ] && return 0
    MTODOS+=("Kept $dest: it is a link to $cur, not to $src. Remove it and run ./install.sh again to use this clone's.")
    return 0
  elif [ -e "$dest" ]; then
    MTODOS+=("Kept $dest: it is your own file or folder, not a link to $src. Move or remove it and run ./install.sh again to use this clone's.")
    return 0
  fi
  msay "link    $(tilde "$dest") -> $src"; MCHANGED=$((MCHANGED + 1))
  [ "$DRY" -eq 1 ] || { mkdir -p -- "$(dirname "$dest")" && ln -s -- "$src" "$dest"; }
}

# mprune <dir>: remove the links in dir that point into this clone and now dangle (a skill a newer release dropped).
mprune() {
  local l
  for l in "$1"/*; do
    { [ -L "$l" ] && [ ! -e "$l" ]; } || continue
    case "$(readlink "$l")" in
      "$MCLONE"/*)
        msay "remove  $(tilde "$l") (its target is gone)"; MCHANGED=$((MCHANGED + 1))
        [ "$DRY" -eq 1 ] || rm -- "$l" ;;
    esac
  done
}

# mpython <mode> <path> <arg>: merge the Stop hook (mode hook, arg = command) or the instruction block
# (mode block, arg = template file) into a user file. Prints one status word; writes through a temp file and rename.
mpython() {
  python3 -I - "$1" "$2" "$3" "$DRY" <<'PY'
import json, os, sys, tempfile

mode, path, arg, dry = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == "1"
BEGIN, END = "<!-- collective-wisdom:begin -->", "<!-- collective-wisdom:end -->"


def write(text):
    real = os.path.realpath(path)  # a settings file kept as a link (dotfiles) stays a link
    os.makedirs(os.path.dirname(real), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(real), prefix=".cw-install-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        if os.path.exists(real):
            os.chmod(tmp, os.stat(real).st_mode & 0o777)
        os.replace(tmp, real)
    except BaseException:
        os.unlink(tmp)
        raise


def hook():
    existed = os.path.exists(path)
    data = {}
    if existed:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (ValueError, OSError):
            return "invalid"
        if not isinstance(data, dict):
            return "invalid"
    if "cos_rotation_check.py" in json.dumps(data.get("hooks")):
        return "present"
    hooks = data.setdefault("hooks", {})
    stop = hooks.setdefault("Stop", []) if isinstance(hooks, dict) else None
    if not isinstance(stop, list):
        return "invalid"
    stop.append({"hooks": [{"type": "command", "command": arg}]})
    if not dry:
        write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return "added" if existed else "created"


def block():
    with open(arg, encoding="utf-8") as f:
        block = BEGIN + "\n" + f.read().rstrip("\n") + "\n" + END
    existed = os.path.exists(path)
    old = ""
    if existed:
        with open(path, encoding="utf-8") as f:
            old = f.read()
    b, e = old.find(BEGIN), old.find(END)
    if b < 0 and e < 0:
        new = old + ("\n" if old and not old.endswith("\n") else "") + ("\n" if old else "") + block + "\n"
    elif 0 <= b < e:
        new = old[:b] + block + old[e + len(END):]
    else:
        return "invalid"
    if new == old:
        return "present"
    if not dry:
        write(new)
    return "updated" if b >= 0 else ("added" if existed else "created")


print({"hook": hook, "block": block}[mode]())
PY
}

machine_install() {
  MCHANGED=0
  MTODOS=()
  msay() { if [ "$DRY" -eq 1 ]; then echo "[dry-run] $*"; else echo "$*"; fi; }
  local ROOT TOP gitdir common sha tag s a p status f
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
  MCLONE="$ROOT"
  { [ -n "${HOME:-}" ] && [ -d "$HOME" ]; } || { echo "Refusing: HOME is not set to a folder." >&2; exit 1; }
  git -C "$ROOT" rev-parse --show-toplevel >/dev/null 2>&1 || { echo "Refusing: $ROOT is not a git repo." >&2; exit 1; }
  TOP="$(cd "$(git -C "$ROOT" rev-parse --show-toplevel)" && pwd -P)"
  [ "$TOP" = "$ROOT" ] || { echo "Refusing: $ROOT is inside the git repo at $TOP, not its own repo root." >&2; exit 1; }
  # A linked worktree (a T3 or .worktrees/ checkout) goes away, and the links to it would dangle.
  gitdir="$(cd "$ROOT" && cd "$(git rev-parse --git-dir)" && pwd -P)"
  common="$(cd "$ROOT" && cd "$(git rev-parse --git-common-dir)" && pwd -P)"
  [ "$gitdir" = "$common" ] || { echo "Refusing: $ROOT is a linked git worktree, which can go away. Run ./install.sh from the main clone." >&2; exit 1; }
  [ -d "$ROOT/agent-team/.claude/skills" ] || { echo "Refusing: $ROOT has no agent-team/.claude/skills." >&2; exit 1; }
  [ -f "$ROOT/agent-team/templates/machine-instruction.md" ] || { echo "Refusing: $ROOT has no agent-team/templates/machine-instruction.md." >&2; exit 1; }

  sha="$(git -C "$ROOT" rev-parse HEAD)"
  tag="$(git -C "$ROOT" describe --tags --exact-match --match 'v0.*' HEAD 2>/dev/null || true)"

  mlink "$ROOT/agent-team" "$HOME/.collective-wisdom"
  for s in "$ROOT/agent-team/.claude/skills"/*/; do
    [ -d "$s" ] || continue
    s="${s%/}"
    for p in .claude/skills .agents/skills .cursor/skills; do
      mlink "$s" "$HOME/$p/$(basename "$s")"
    done
  done
  for a in "$ROOT/agent-team/.claude/agents"/*; do
    [ -f "$a" ] || continue
    mlink "$a" "$HOME/.claude/agents/$(basename "$a")"
  done
  for p in .claude/skills .agents/skills .cursor/skills .claude/agents; do
    mprune "$HOME/$p"
  done

  # shellcheck disable=SC2016  # $HOME is expanded when the hook runs, not now
  status="$(mpython hook "$HOME/.claude/settings.json" 'python3 "$HOME/.collective-wisdom/scripts/cos_rotation_check.py" --hook || true')"
  case "$status" in
    added|created) msay "$status  ~/.claude/settings.json (Stop hook)"; MCHANGED=$((MCHANGED + 1)) ;;
    invalid) MTODOS+=("Add the Chief of Staff Stop hook to ~/.claude/settings.json by hand (the file is not a JSON object with a list under hooks.Stop, so it was left alone): a Stop hook running  python3 \"\$HOME/.collective-wisdom/scripts/cos_rotation_check.py\" --hook || true") ;;
  esac

  for f in .claude/CLAUDE.md .codex/AGENTS.md; do
    status="$(mpython block "$HOME/$f" "$ROOT/agent-team/templates/machine-instruction.md")"
    case "$status" in
      added|created|updated) msay "$status  ~/$f (agent team instruction)"; MCHANGED=$((MCHANGED + 1)) ;;
      invalid) MTODOS+=("Fix ~/$f by hand: it has one collective-wisdom marker comment without the other, so it was left alone.") ;;
    esac
  done
  MTODOS+=("Paste this into Cursor's user rules (Cursor Settings, Rules; it has no file to write):
$(sed '/./s/^/      /' "$ROOT/agent-team/templates/machine-instruction.md")")

  echo
  echo "Done$([ "$DRY" -eq 1 ] && echo ' (dry run, nothing written)'): $MCHANGED change(s) under $HOME"
  echo "TODO:"
  for p in "${MTODOS[@]}"; do echo "  - $p"; done
  echo "$([ "$DRY" -eq 1 ] && echo 'would install' || echo installed) collective-wisdom $sha${tag:+ $tag} from $ROOT"
}

if [ -z "$TARGET" ]; then
  { [ "$UPDATE$CHECK$FORCE" = "000" ] && [ -z "$REF" ] && [ -z "$FROM" ]; } || usage
  machine_install
  exit 0
fi
case "$REF" in -*) echo "bad ref: $REF" >&2; usage ;; esac
[ -z "$FROM" ] || [ -z "$REF" ] || { echo "--from and --to cannot be used together" >&2; usage; }
# Release tags are v0.N only, the shape the pin records; this also rules out a name that starts with "-".
[ -z "$FROM" ] || [[ "$FROM" =~ ^v0\.[0-9]+$ ]] || { echo "bad tag: $FROM (expected v0.N)" >&2; usage; }
if [ "$CHECK" -eq 1 ] && { [ -n "$REF" ] || [ -n "$FROM" ] || [ "$UPDATE$FORCE" != "00" ]; }; then usage; fi
[ "$FORCE" -eq 0 ] || [ "$UPDATE" -eq 1 ] || { echo "--force only goes with --update" >&2; usage; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The version pin written below names a commit of this clone, so the clone must be its own repo.
git -C "$ROOT" rev-parse --show-toplevel >/dev/null 2>&1 || { echo "Refusing: $ROOT is not a git repo, so the install cannot be pinned to a commit." >&2; exit 1; }
# A copy vendored inside another repo would otherwise pin the parent repo's commit.
TOP="$(cd "$(git -C "$ROOT" rev-parse --show-toplevel)" && pwd -P)"
[ "$TOP" = "$(cd "$ROOT" && pwd -P)" ] || { echo "Refusing: $ROOT is inside the git repo at $TOP, not its own repo root, so the install cannot be pinned to its commit." >&2; exit 1; }
[ -d "$TARGET" ] || { echo "not a directory: $TARGET" >&2; exit 1; }
TARGET="$(cd "$TARGET" && pwd)"
git -C "$TARGET" rev-parse --show-toplevel >/dev/null 2>&1 || { echo "not a git repo: $TARGET" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT

# extract <sha> <dest>: this clone's agent-team/ at that commit, so copies are exactly the pinned commit.
extract() {
  mkdir -p -- "$2"
  git -C "$ROOT" archive "$1" agent-team | tar -x -C "$2" || { echo "cannot extract agent-team/ from $1" >&2; exit 2; }
}

# shipped <dir>: sorted paths of the files the installer syncs from an extracted agent-team/ (the same paths in the app).
shipped() {
  local p
  for p in .claude/skills .claude/agents .claude/mods scripts docs/agents; do
    [ -d "$1/$p" ] && (cd "$1" && find "$p" -type f)
  done | awk '$0 !~ /(^|\/)__pycache__\// && $0 !~ /\.pyc$/ && $0 !~ /\.DS_Store$/' | LC_ALL=C sort
  return 0
}

# drift <dir>: fill DRIFT with "changed"/"missing" lines for shipped files that differ in the app.
DRIFT=()
drift() {
  local f
  DRIFT=()
  while IFS= read -r f; do
    if [ ! -e "$TARGET/$f" ] && [ ! -L "$TARGET/$f" ]; then
      DRIFT+=("missing  $f")
    elif ! cmp -s -- "$1/$f" "$TARGET/$f"; then
      DRIFT+=("changed  $f")
    fi
  done < <(shipped "$1")
}

# The pin of an installed app: which collective-wisdom commit its files came from.
PIN="$TARGET/docs/agents/installed-from.txt"
OLD="" OLD_TAG=""
if [ "$CHECK" -eq 1 ] || [ "$UPDATE" -eq 1 ]; then
  if [ ! -e "$PIN" ]; then
    if [ "$CHECK" -eq 1 ]; then
      echo "check: cannot check: no docs/agents/installed-from.txt in $TARGET" >&2; exit 2
    fi
    echo "Refusing: no docs/agents/installed-from.txt in $TARGET, so there is nothing to update. Run a plain install (without --update) first." >&2; exit 1
  fi
  PIN_RE='^collective-wisdom ([0-9a-f]{40})( (v0\.[0-9]+))?$'
  PIN_LINE="$(cat -- "$PIN")"
  [[ "$PIN_LINE" =~ $PIN_RE ]] || { echo "docs/agents/installed-from.txt in $TARGET is not 'collective-wisdom <40-character SHA>' (optionally followed by a v0.N tag)." >&2; exit 2; }
  OLD="${BASH_REMATCH[1]}" OLD_TAG="${BASH_REMATCH[3]:-}"
  # The old files come from the pinned commit, so this clone must have it.
  git -C "$ROOT" cat-file -e "$OLD^{commit}" 2>/dev/null || { echo "collective-wisdom $OLD is not in $ROOT; run 'git fetch origin' there and try again." >&2; exit 2; }
  extract "$OLD" "$TMP/old"
  drift "$TMP/old/agent-team"
fi

if [ "$CHECK" -eq 1 ]; then
  if [ "${#DRIFT[@]}" -gt 0 ]; then
    printf '%s\n' "${DRIFT[@]}"
    echo "check: drift in ${#DRIFT[@]} file(s) against collective-wisdom $OLD${OLD_TAG:+ ($OLD_TAG)}"; exit 1
  fi
  echo "check: matches collective-wisdom $OLD${OLD_TAG:+ ($OLD_TAG)}"; exit 0
fi

# Resolve the target commit. It must be on origin/main, so an app is never pinned to an unmerged branch.
# Look the branch up by its exact ref name: rev-parse and merge-base guess (tags, heads) when a short or missing name is given.
if [ -n "$FROM" ]; then
  # The "+" lets origin's tag replace a stale or hand-made local tag of the same name.
  git -C "$ROOT" fetch -q --no-tags origin main "+refs/tags/$FROM:refs/tags/$FROM" || { echo "cannot fetch origin main and tag $FROM in $ROOT" >&2; exit 1; }
  REF="refs/tags/$FROM"
elif [ -z "$REF" ] && [ "$UPDATE" -eq 1 ]; then
  git -C "$ROOT" fetch -q --no-tags origin || { echo "cannot fetch origin in $ROOT" >&2; exit 1; }
fi
MAIN="$(git -C "$ROOT" show-ref --verify --hash refs/remotes/origin/main 2>/dev/null)" || { echo "Refusing: $ROOT has no origin/main; run 'git fetch origin' there." >&2; exit 1; }
if [ -z "$REF" ]; then
  if [ "$UPDATE" -eq 1 ]; then REF="$MAIN"; else REF="HEAD"; fi
fi
SHA="$(git -C "$ROOT" rev-parse --verify --quiet "$REF^{commit}")" || { echo "Refusing: $REF is not a commit in $ROOT." >&2; exit 1; }
git -C "$ROOT" merge-base --is-ancestor "$SHA" "$MAIN" 2>/dev/null || { echo "Refusing: $SHA ($REF) is not on origin/main, so the install cannot be pinned to it. Merge it, or run 'git fetch origin' in $ROOT." >&2; exit 1; }

# The pin names a tag only when the files came from --from, so it never names a tag they did not come from.
PIN_TEXT="collective-wisdom $SHA${FROM:+ $FROM}"

TOUCHED=(.claude scripts docs/agents docs/superpowers/README.md .agents .gitignore AGENTS.md)
DIRTY="$(git -C "$TARGET" status --porcelain -- "${TOUCHED[@]}")"
if [ -n "$DIRTY" ]; then
  echo "Refusing: uncommitted changes in paths this installer touches:" >&2
  echo "$DIRTY" >&2
  echo "Commit or stash them first." >&2
  exit 1
fi

if [ "$UPDATE" -eq 1 ]; then
  # A release tag can be older than the pin (an app updated from origin/main after the last tag), so --from never moves backwards unless forced.
  if [ -n "$FROM" ] && [ "$FORCE" -eq 0 ] && ! git -C "$ROOT" merge-base --is-ancestor "$OLD" "$SHA" 2>/dev/null; then
    echo "Refusing: $FROM (${SHA:0:12}) is older than the pin ${OLD:0:12} (or not built on it), so the update would move the app backwards. Run again with --force to do it anyway." >&2
    exit 1
  fi
  if [ "${#DRIFT[@]}" -gt 0 ] && [ "$FORCE" -eq 0 ]; then
    echo "Refusing: ${#DRIFT[@]} file(s) differ from collective-wisdom $OLD, and an update would overwrite them:" >&2
    printf '%s\n' "${DRIFT[@]}" >&2
    echo "Commit them upstream or revert them, or run again with --force to overwrite." >&2
    exit 1
  fi
  if [ "$PIN_LINE" = "$PIN_TEXT" ] && [ "${#DRIFT[@]}" -eq 0 ]; then
    echo "already at $SHA, nothing to do"; exit 0
  fi
  N="$(git -C "$ROOT" rev-list --count "$OLD..$SHA" -- agent-team)"
  echo "collective-wisdom ${OLD_TAG:+$OLD_TAG }${OLD:0:12} -> ${FROM:+$FROM }${SHA:0:12} ($N commit$([ "$N" -eq 1 ] || echo s))"
  git -C "$ROOT" log --oneline "$OLD..$SHA" -- agent-team | sed 's/^/  /'
fi
extract "$SHA" "$TMP/new"
SRC="$TMP/new/agent-team"

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
sync_dir "$SRC/.claude/mods" "$TARGET/.claude/mods"

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
  # A text search, not a JSON parse: a hook written by hand in another shape still counts.
  if ! grep -qF -- cos_rotation_check.py "$SET"; then
    TODOS+=("Add the Chief of Staff Stop hook to .claude/settings.json by hand (the file has its own settings, so it was left alone). Merge this into its \"hooks\" key:
$(sed 's/^/      /' "$SRC/.claude/settings.json")")
  fi
fi

sync_dir "$SRC/scripts" "$TARGET/scripts"

sync_dir "$SRC/docs/agents" "$TARGET/docs/agents"

# Version pin: which collective-wisdom commit the installed files came from.
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

# Decided before seed_file, so a dry run (which seeds nothing) still knows whether the file was already there.
AGENTS_EXISTED=0
[ ! -e "$TARGET/AGENTS.md" ] || AGENTS_EXISTED=1

seed_file "$SRC/templates/project.md" "$TARGET/docs/agents/project.md" \
  "Fill in every <placeholder> in docs/agents/project.md (prefix, repo, commands, invariants), and pick an Approval risk tolerance (strict if you leave it as is). The scripts will not run until the prefix and repo rows are real."
seed_file "$SRC/templates/AGENTS.md" "$TARGET/AGENTS.md" \
  "Fill in the <placeholders> in AGENTS.md (project name, product, stack). Add a CLAUDE.md containing @AGENTS.md if you use Claude Code."

# Codex discovers skills through a relative symlink.
if [ ! -e "$TARGET/.agents/skills" ] && [ ! -L "$TARGET/.agents/skills" ]; then
  say "link    .agents/skills -> ../.claude/skills"; CHANGED=$((CHANGED + 1))
  run mkdir -p "$TARGET/.agents"; run ln -s ../.claude/skills "$TARGET/.agents/skills"
fi

# These checks never write. An app's own AGENTS.md and .agents/skills are merged by hand.
if [ "$AGENTS_EXISTED" -eq 1 ]; then
  missing=""
  for h in "Required reading" "GitHub" "Workflow" "Agent config"; do
    grep -qiE -- "^[[:space:]]*##[[:space:]]+${h}[[:space:]]*\$" "$TARGET/AGENTS.md" || missing="${missing:+$missing, }$h"
  done
  if [ -n "$missing" ]; then
    TODOS+=("AGENTS.md has no $missing section(s). Copy them from agent-team/templates/AGENTS.md in collective-wisdom (at ${SHA:0:12}) and fill them in for this repo.")
  fi
fi

AS="$TARGET/.agents/skills"
why=""
if [ -L "$AS" ]; then
  link="$(readlink "$AS")"
  [ "$link" = "../.claude/skills" ] || why=".agents/skills links to $link, not to ../.claude/skills"
elif [ -d "$AS" ]; then
  why=".agents/skills is a real directory, not a link to ../.claude/skills"
elif [ -e "$AS" ]; then
  why=".agents/skills is a file"
fi
if [ -n "$why" ]; then
  TODOS+=("$why, so Codex will not see the shipped skills. Move any skills of your own from it into .claude/skills/, then replace it: rm -r .agents/skills && ln -s ../.claude/skills .agents/skills")
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

if [ "$UPDATE" -eq 1 ]; then
  while IFS= read -r f; do
    [ -e "$TARGET/$f" ] || [ -L "$TARGET/$f" ] || continue
    TODOS+=("Delete $f: collective-wisdom no longer ships it (shipped at ${OLD:0:12}, gone at ${SHA:0:12}).")
  done < <(LC_ALL=C comm -23 <(shipped "$TMP/old/agent-team") <(shipped "$SRC"))
fi

echo
echo "Done$([ "$DRY" -eq 1 ] && echo ' (dry run, nothing written)'): $CHANGED change(s) in $TARGET"
if [ "${#TODOS[@]}" -gt 0 ]; then
  echo "TODO:"
  for t in "${TODOS[@]}"; do echo "  - $t"; done
fi
echo "Review with 'git -C $TARGET status', then commit."
