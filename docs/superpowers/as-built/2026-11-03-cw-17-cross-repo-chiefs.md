# As-built: Cross-repo requests between Chiefs of Staff

**Shipped:** in PR #26
**Ticket:** CW-17 (#17)
**Spec:** [2026-11-03-cw-17-cross-repo-chiefs-design.md](../specs/2026-11-03-cw-17-cross-repo-chiefs-design.md)
**Plan:** [2026-11-03-cw-17-cross-repo-chiefs.md](../plans/2026-11-03-cw-17-cross-repo-chiefs.md)

## What shipped

- `scripts/cos_peer.py` (read only): `find` maps a repo name to a project in `t3_project_list` and its Chief of Staff thread from that project's `.agent-team/state.json`; `check` re-reads the user's message in T3's store and accepts a request only if the sender is a Chief of Staff thread, the text matches the stored message, the words name this repo and are not a Chief of Staff command; `reply` reduces a reply to ticket lines.
- `chief-of-staff` skill: new § Cross-repo requests (sending, receiving, replying, receiving a reply), two § Commands rows, a § Guardrails line, a `Request from` part in the ticket helper's first line, a § Tools bullet, and a line in § Lean turns' helper-notice bullet that sends the reply. The intro's wake list and "no full pass" exemption name the request and reply messages. Retired threads forward requests and replies (reference.md).
- `docs/agents/chief-of-staff.md`: a Scope bullet and a Done-when line.
- Tests: `test_cos_peer.py` tables, and a `test_cos.py` user-check row showing an agent `CHIEF OF STAFF REQUEST` quoting `approve 12` is `not-user`.

## Differs from the spec

- `resume` is refused as a command word anywhere in a request, so "fix resume upload" is refused. It fails safe; the user says it in the receiving thread.
- `check` uses `--thread` only to look up this repo's T3 title as one of the names a request may use.
- The `For:` line is parsed but not checked; the check runs on the user's words.
- The words may name this repo by `owner/name`, repo name or this thread's T3 project title. The product name in `project.md` is not matched.
- `find` skips deleted projects and does not fold hyphens, so "collective wisdom" matches the title but not the repo name.
