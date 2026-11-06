# CW-104: Open-source readiness sweep

**Ticket:** [CW-104](https://github.com/collective-wisdom-org/collective-wisdom/issues/104)
**Status:** Shipped
**Shipped:** in PR #120, as specified

## Goal

Make the repo ready to be made public: nothing personal or secret in the tree or its history, and the files a public repo is expected to carry. The visibility flip itself stays a decision for the approver and is out of scope.

## Today

- The repo is private. It has no `LICENSE`, `SECURITY.md` or `CONTRIBUTING.md`.
- The README's update section says the repo is private and the clone needs credentials.
- `agent-team/docs/agents/trackers/github.md` names the old personal repo path in its verified line.
- `agent-team/scripts/test_cos_peer.py` uses another private project's name and repo as fixtures.
- No secret shape, key file or home path appears in the tree or in the history of any branch (checked with pattern scans over `git log -p --all`).

## Change

- Add `LICENSE` (MIT), `SECURITY.md` (private vulnerability reporting through GitHub, what counts) and `CONTRIBUTING.md` (the PR checklist).
- README: drop the private-repo sentence, link the checklist from Propose changes, add a License section.
- GitHub adapter doc: point the verified line at the org repo; tell public repos to require approval for Actions runs from outside collaborators.
- Replace the fixture names in `test_cos_peer.py` with `acme/mail` and `Acme Mail`.
- Record the sweep results and the steps left for the approver on the ticket.

## Acceptance

- No secret appears in the repo or its history, shown by the scans recorded on the ticket.
- `git grep -nIiE 'fathom|I Have a Guy|MacBook|repo is private' -- . ':!docs/superpowers'` prints nothing on the branch.
- `LICENSE`, `SECURITY.md` and `CONTRIBUTING.md` exist and the README links them.
- Tests and shellcheck pass.

## Out of scope

- Flipping the repo to public, GitHub settings, and the history rewrite that removed personal commit emails and the hostname email in the CW-92 spec (done outside this PR and recorded on the ticket).
