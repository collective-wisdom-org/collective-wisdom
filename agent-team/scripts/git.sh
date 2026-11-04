#!/usr/bin/env bash
# git as an agent role's GitHub user: author, commit and push with that user's identity and keyring token.
#
# AGENT_GH_ROLE=<role> ./scripts/git.sh <git args> runs this one git call as the role's login in project.md.
# Unset, or a role whose login is `none`: plain git with the machine's identity and credential, as before.
# A login gh does not have exits 2 instead of falling back, so a wrong setup cannot commit or push as the owner.
# The token lives only in this process's environment. It is never written to git config, a file or a URL.
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
if ! info="$(env -u GITHUB_TOKEN GH_TOKEN="$token" gh api user --jq '(.id | tostring), (.name // "")' 2>/dev/null)"; then
  fail "could not read the GitHub user for $login"
fi
{ read -r id; read -r name; } <<<"$info"
[ -n "$id" ] || fail "could not read the GitHub user for $login"
email="$id+$login@users.noreply.github.com"
export GIT_AUTHOR_NAME="${name:-$login}" GIT_AUTHOR_EMAIL="$email"
export GIT_COMMITTER_NAME="${name:-$login}" GIT_COMMITTER_EMAIL="$email"
export GIT_SH_TOKEN="$token"

# Find the subcommand past git's own options (`-C <dir>`, `-c <k=v>`), so they cannot hide a push.
# The checks below run git with those same options, so they look at the repo the push will use.
n=1
while [ "$n" -le "$#" ]; do
  case "${!n}" in
    -C | -c | --git-dir | --work-tree | --namespace) n=$((n + 2)) ;;
    -*) n=$((n + 1)) ;;
    *) break ;;
  esac
done
if [ "$n" -le "$#" ] && [ "${!n}" = push ]; then
  remote=origin
  for arg in "${@:n+1}"; do
    case "$arg" in -*) ;; *) remote="$arg"; break ;; esac
  done
  url="$(git "${@:1:n-1}" remote get-url --push "$remote" 2>/dev/null)" || url="$remote"
  # https gets the token. A local path or file:// needs no credential. ssh and git:// would use the machine's key.
  case "$url" in
    https://* | file://* | /*) ;;
    *) fail "push remote $remote is not https, so it would not use the $login token" ;;
  esac
  while read -r sha; do
    author="$(git "${@:1:n-1}" log -1 --format=%ae "$sha")"
    [ "$author" = "$email" ] ||
      fail "commit $sha is by $author, not $email; nothing pushed. Fix with: AGENT_GH_ROLE=$role ./scripts/git.sh rebase -r <base> --exec 'git commit --amend --no-edit --reset-author'"
  done < <(git "${@:1:n-1}" rev-list HEAD --not --remotes=origin 2>/dev/null)
fi

# shellcheck disable=SC2016  # $1 and $GIT_SH_TOKEN expand in git's credential helper shell, not here
exec git -c credential.helper= \
  -c 'credential.helper=!f() { test "$1" = get && echo username=x-access-token && echo "password=$GIT_SH_TOKEN"; }; f' "$@"
