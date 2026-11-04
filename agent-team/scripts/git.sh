#!/usr/bin/env bash
# git as an agent role's GitHub user: author, commit and push with that user's identity and keyring token.
#
# AGENT_GH_ROLE=<role> ./scripts/git.sh <git args> runs this one git call as the role's login in project.md.
# Unset, or a role whose login is `none`: plain git with the machine's identity and credential, as before.
# A login gh does not have exits 2 instead of falling back, so a wrong setup cannot commit or push as the owner.
# The token is never exported, written to git config or a file, or put in a URL or argv. This script reads it once to look up the
# user id. For fetch, push and the like, git's credential helper fetches it again on demand, and only for https://github.com.
fail() {
  echo "git.sh: $*" >&2
  exit 2
}

role="${AGENT_GH_ROLE:-}"
[ -n "$role" ] || exec git "$@"
login="$(python3 -I "$(dirname "$0")/project_config.py" login "$role" 2>&1)" || fail "$login"
[ -n "$login" ] || exec git "$@"

if ! token="$(env -u GITHUB_TOKEN -u GH_TOKEN gh auth token -u "$login" 2>/dev/null)" || [ -z "$token" ]; then
  fail "no gh login for $login; run gh auth login, then gh auth switch -u <owner>"
fi
if ! info="$(GH_TOKEN="$token" env -u GITHUB_TOKEN gh api user --jq '(.id | tostring), (.name // "")' 2>/dev/null)"; then
  fail "could not read the GitHub user for $login"
fi
{ read -r id; read -r name; } <<<"$info"
[ -n "$id" ] || fail "could not read the GitHub user for $login"
email="$id+$login@users.noreply.github.com"
export GIT_AUTHOR_NAME="${name:-$login}" GIT_AUTHOR_EMAIL="$email"
export GIT_COMMITTER_NAME="${name:-$login}" GIT_COMMITTER_EMAIL="$email"
unset token

# Find the subcommand past git's own options (`-C <dir>`, `-c <k=v>`), so they cannot hide a push.
# The checks below run git with those same options, so they look at the repo the push will use.
# The push check is a guardrail against mistakes. An alias or `rebase --exec 'git push'` gets past it.
n=1
while [ "$n" -le "$#" ]; do
  case "${!n}" in
    -C | -c | --git-dir | --work-tree | --namespace | --config-env | --attr-source) n=$((n + 2)) ;;
    -*) n=$((n + 1)) ;;
    *) break ;;
  esac
done
sub=""
[ "$n" -le "$#" ] && sub="${!n}"
gopts=("${@:1:n-1}")

if [ "$sub" = push ]; then
  pos=() scope=() revs=()
  skip="" deleting=""
  for arg in "${@:n+1}"; do
    if [ -n "$skip" ]; then skip=""; continue; fi
    case "$arg" in
      -o | --push-option | --receive-pack | --exec | --repo) skip=1 ;;
      --all) scope+=(--branches) ;;
      --mirror) scope+=(--all) ;;
      --tags) scope+=(--tags) ;;
      -d | --delete) deleting=1 ;;
      -*) ;;
      *) pos+=("$arg") ;;
    esac
  done
  # The remote git would push to: the argument, else pushRemote, pushDefault, the branch's remote, then origin.
  remote="${pos[0]:-}"
  if [ -z "$remote" ]; then
    branch="$(git "${gopts[@]}" symbolic-ref -q --short HEAD)"
    for key in "branch.$branch.pushRemote" remote.pushDefault "branch.$branch.remote"; do
      remote="$(git "${gopts[@]}" config --get "$key")" && break
    done
    : "${remote:=origin}"
  fi
  # Only https://github.com gets the token. A local path or file:// needs no credential. ssh and git:// would use the machine's key.
  urls="$(git "${gopts[@]}" remote get-url --push --all "$remote" 2>/dev/null)" && [ -n "$urls" ] ||
    fail "push remote $remote is not https://github.com (not a configured remote), so it would not use the $login token"
  while read -r url; do
    case "$url" in
      https://github.com/* | file://* | /*) ;;
      *) fail "push remote $remote is not https://github.com, so it would not use the $login token" ;;
    esac
  done <<<"$urls"
  # Check what the refspecs push (their source side), not just HEAD. Globs and other odd refspecs fail closed.
  if [ -z "$deleting" ]; then
    for spec in "${pos[@]:1}"; do
      spec="${spec#+}"
      revs+=("${spec%%:*}")
    done
    [ "${#pos[@]}" -gt 1 ] || [ "${#scope[@]}" -gt 0 ] || revs=(HEAD)
    for i in "${!revs[@]}"; do [ -n "${revs[i]}" ] || revs[i]=HEAD; done
    commits="$(git "${gopts[@]}" rev-list "${revs[@]}" "${scope[@]}" --not "--remotes=$remote")" ||
      fail "could not list the unpushed commits for $remote; nothing pushed"
    while read -r sha; do
      [ -n "$sha" ] || continue
      author="$(git "${gopts[@]}" log -1 --format=%ae "$sha")"
      [ "$author" = "$email" ] ||
        fail "commit $sha is by $author, not $email; nothing pushed. Fix with: AGENT_GH_ROLE=$role ./scripts/git.sh rebase -r <base> --exec 'git commit --amend --no-edit --reset-author'"
    done <<<"$commits"
  fi
fi

# Only commands that talk to a remote get the credential helper. It answers `get` for https://github.com alone and
# fetches the token itself, so the token is never exported to hooks or other child processes. `credential` stays on the list
# so the helper can be tested. The login is checked against LOGIN_RE in project_config.py, so it is safe to embed.
helper=()
case "$sub" in
  push | fetch | pull | clone | ls-remote | credential)
    # shellcheck disable=SC2016  # the $ expand in git's credential helper shell, not here
    tmpl='!f() { test "$1" = get || return 0; p=; h=; while read -r l; do case "$l" in protocol=https) p=1 ;; host=github.com) h=1 ;; esac; done; test "$p$h" = 11 || return 0; echo username=x-access-token; echo "password=$(env -u GITHUB_TOKEN -u GH_TOKEN gh auth token -u "@LOGIN@")"; }; f'
    helper=(-c credential.helper= -c "credential.helper=${tmpl//@LOGIN@/$login}")
    ;;
esac
exec git "${helper[@]}" "$@"
