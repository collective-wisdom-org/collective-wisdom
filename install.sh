#!/usr/bin/env bash
# Install this clone for the machine: link the agent team into $HOME. It installs nothing into an app.
# Usage: ./install.sh [--dry-run]
set -euo pipefail

usage() {
  echo "Usage: $0 [--dry-run]" >&2
  exit 2
}

# Any other argument is a form that used to install into an app (a target path, --update, --to, ...): refuse it.
DRY=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    -h|--help) usage ;;
    *)
      case "$1" in -*) echo "unknown option: $1" >&2 ;; esac
      echo "install.sh no longer installs into an app. Run ./install.sh with no path to install on this machine. To remove an old copy from an app, run ~/.collective-wisdom/scripts/remove_app_copies.py in it." >&2
      exit 2 ;;
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
    try:
        if existed:
            with open(path, encoding="utf-8") as f:
                old = f.read()
        return block_merge(block, old, existed)
    except (OSError, ValueError):  # a folder or a file that is not UTF-8 text at the target
        return "invalid"


def block_merge(block, old, existed):
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

  # Every call site reads scripts through this one path, so it must be this clone's. Refuse before any write.
  if [ -L "$HOME/.collective-wisdom" ]; then
    [ "$(readlink "$HOME/.collective-wisdom")" = "$ROOT/agent-team" ] || { echo "Refusing: ~/.collective-wisdom already points to $(readlink "$HOME/.collective-wisdom"), not to $ROOT/agent-team. Remove it and run ./install.sh again." >&2; exit 1; }
  elif [ -e "$HOME/.collective-wisdom" ]; then
    echo "Refusing: ~/.collective-wisdom already exists and is not a link to $ROOT/agent-team. Remove it and run ./install.sh again." >&2; exit 1
  fi

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
  status="$(mpython hook "$HOME/.claude/settings.json" 'python3 -I "$HOME/.collective-wisdom/scripts/cos_rotation_check.py" --hook || true')"
  case "$status" in
    added|created) msay "$status  ~/.claude/settings.json (Stop hook)"; MCHANGED=$((MCHANGED + 1)) ;;
    invalid) MTODOS+=("Add the Chief of Staff Stop hook to ~/.claude/settings.json by hand (the file is not a JSON object with a list under hooks.Stop, so it was left alone): a Stop hook running  python3 -I \"\$HOME/.collective-wisdom/scripts/cos_rotation_check.py\" --hook || true") ;;
  esac

  for f in .claude/CLAUDE.md .codex/AGENTS.md; do
    status="$(mpython block "$HOME/$f" "$ROOT/agent-team/templates/machine-instruction.md")"
    case "$status" in
      added|created|updated) msay "$status  ~/$f (agent team instruction)"; MCHANGED=$((MCHANGED + 1)) ;;
      invalid) MTODOS+=("Fix ~/$f by hand: it could not be read as text, or it has one collective-wisdom marker comment without the other, so it was left alone.") ;;
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

machine_install
