# Jira adapter reference

Read from `jira.md`, by whoever first has Jira access.

## Assumptions to check

Run these and edit `jira.md` to match.

- [ ] The tool names in `jira.md` exist in the connected server.
- [ ] Discovery works for the tools that are not Primary.
- [ ] `searchJiraIssuesUsingJql` accepts a field list.
- [ ] `listJiraIssueTransitions` returns target statuses, not only transition names.
- [ ] The status map matches the project's workflow.
- [ ] `parent = KEY` finds the children of an epic.
- [ ] `createJiraIssueLink` direction for `Blocks` is as described.
- [ ] Labels with no spaces work, and adding one keeps the others.
- [ ] The `updated >=` clause works with a timestamp.
- [ ] Comments render in the format sent (ADF or markdown).
