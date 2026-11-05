#!/usr/bin/env bash
# Use gh's OAuth keyring login, not a limited GITHUB_TOKEN PAT.
# GITHUB_TOKEN overrides gh auth and breaks `gh pr create` GraphQL calls.
exec env -u GITHUB_TOKEN -u GH_TOKEN gh "$@"
