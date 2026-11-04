#!/usr/bin/env bash
# Use gh's OAuth keyring login, not a limited GITHUB_TOKEN PAT.
# GITHUB_TOKEN overrides gh auth and breaks `gh pr create` GraphQL calls.
#
# AGENT_GH_ROLE=<role> runs this one gh call as that agent role's GitHub user (the login in project.md).
# Unset, or a role whose login is `none`: the active gh account, as before. A login that gh does not
# have exits 2 instead of falling back, so a wrong setup cannot post as the owner.
role="${AGENT_GH_ROLE:-}"
if [ -n "$role" ]; then
  if ! login="$(python3 -I "$(dirname "$0")/project_config.py" login "$role" 2>&1)"; then
    echo "gh.sh: $login" >&2
    exit 2
  fi
  if [ -n "$login" ]; then
    if ! token="$(env -u GITHUB_TOKEN -u GH_TOKEN gh auth token -u "$login" 2>/dev/null)" || [ -z "$token" ]; then
      echo "gh.sh: no gh login for $login; run gh auth login, then gh auth switch -u <owner>" >&2
      exit 2
    fi
    exec env -u GITHUB_TOKEN GH_TOKEN="$token" gh "$@"
  fi
fi
exec env -u GITHUB_TOKEN -u GH_TOKEN gh "$@"
