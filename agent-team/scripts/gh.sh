#!/usr/bin/env bash
# Use gh's OAuth keyring login, not a limited GITHUB_TOKEN PAT.
# GITHUB_TOKEN overrides gh auth and breaks `gh pr create` GraphQL calls.
# When the user's user.md maps this repo to a gh login, that login's keyring token is used for this one command.
# The active gh account is never switched.

src="${BASH_SOURCE[0]}"
while [ -L "$src" ]; do
  dir="$(cd -P "$(dirname "$src")" && pwd)"
  src="$(readlink "$src")"
  case "$src" in /*) ;; *) src="$dir/$src" ;; esac
done
here="$(cd -P "$(dirname "$src")" && pwd)"

account="$(python3 -I "$here/user_config.py" account)" || exit 2
if [ -z "$account" ]; then
  exec env -u GITHUB_TOKEN -u GH_TOKEN gh "$@"
fi

read -r host login <<< "$account"
token="$(env -u GITHUB_TOKEN -u GH_TOKEN -u GH_ENTERPRISE_TOKEN -u GITHUB_ENTERPRISE_TOKEN gh auth token --hostname "$host" --user "$login" 2>/dev/null)"
if [ -z "$token" ]; then
  echo "gh.sh: no gh login $login on $host; run gh auth login -h $host" >&2
  exit 2
fi

case "$host" in
  github.com|*.ghe.com) var=GH_TOKEN ;;
  *) var=GH_ENTERPRISE_TOKEN ;;
esac
unset GITHUB_TOKEN GH_TOKEN GH_ENTERPRISE_TOKEN GITHUB_ENTERPRISE_TOKEN
export "$var=$token"
exec gh "$@"
