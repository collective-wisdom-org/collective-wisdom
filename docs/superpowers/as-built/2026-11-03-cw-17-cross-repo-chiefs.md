# As-built: Cross-repo requests between Chiefs of Staff

**Shipped:** in PR #26
**Ticket:** CW-17 (#17)
**Spec:** [2026-11-03-cw-17-cross-repo-chiefs-design.md](../specs/2026-11-03-cw-17-cross-repo-chiefs-design.md)
**Plan:** [2026-11-03-cw-17-cross-repo-chiefs.md](../plans/2026-11-03-cw-17-cross-repo-chiefs.md)

## What shipped

- `scripts/cos_peer.py` (read only): `find` maps a repo name to a project in `t3_project_list` and its Chief of Staff thread from that project's `.agent-team/state.json`; `check` re-reads the user's message in T3's store and accepts a request only if the sender is a Chief of Staff thread in another project than this one, the text matches the stored message, the words name this repo and are not a Chief of Staff command, and prints the sender project's T3 title as the label; `reply` checks that its `from` thread is a Chief of Staff thread, prints `source <project title> <thread id>` and reduces the reply to ticket lines (a long line loses title, never URL, and never exceeds 200 characters). A `from` thread whose project has no readable state file is "not a chief" (exit 1, no output). `check` and `reply` take `--thread` (this thread's id) and `--item` (the `itemId` T3 gave the incoming message) and read the message from T3's store (a finished user-role message in `--thread`); neither reads stdin. `find` still reads the project list on stdin. Unreadable data (a non-list `retiredThreads`, a project without `id`, an `--item` outside `[A-Za-z0-9:._%-]{1,200}`) exits 2. An `--item` that is not a finished user-role message in `--thread`, including an unknown `--thread`, gives `refuse: malformed` from `check` and exit 1 with no output from `reply`.
- `chief-of-staff` skill: new § Cross-repo requests (sending, receiving, replying, receiving a reply), two § Commands rows, a § Guardrails line, a `Request from` part in the ticket helper's first line (with a rule that such a helper only creates new Backlog tickets: it may set the new ticket's parent epic and its blockedBy/relatedTo links, and never edits an existing ticket's description, title, labels or state; the epic line `write-ticket` would add goes under `Needs the user`), a § Tools bullet, and a line in § Lean turns' helper-notice bullet that sends the reply. The intro's wake list and "no full pass" exemption name the request and reply messages. Retired threads forward requests and replies (reference.md). The Chief finds `<itemId>` by reading the last few items of its thread for the `user_message` that starts `CHIEF OF STAFF REQUEST`/`REPLY` with the right `from`; a helper counts as request-born only when `Request from` is on its first line.
- `docs/agents/chief-of-staff.md`: a Scope bullet, a Done-when line, and a wake-list edit to the existing "Fills a slot" Scope bullet. `docs/agents/org-chart.md`: the Chief of Staff row (woken by another repo's request or reply) and the Ticket helper row (new-ticket-only when started by a request). The `SKILL.md` frontmatter description's wake list.
- Tests: `test_cos_peer.py` tables, and a `test_cos.py` user-check row showing an agent `CHIEF OF STAFF REQUEST` quoting `approve 12` is `not-user`.

## Differs from the spec

- `resume` is refused as a command word anywhere in a request, so "fix resume upload" is refused. It fails safe; the user says it in the receiving thread.
- The spec had `check` and `reply` read the message on stdin. The security review found that puts another agent's text in a shell heredoc, where a line `EOF` ends it early and the rest runs as commands, so both read it from T3's store by item id.
- `check` uses `--thread` to look up this repo's T3 title as one of the names a request may use and to refuse a sender in the same project (`refuse: same repo`).
- Sending step 2 in `SKILL.md` merges every page of `t3_project_list` and handles `find` exit 2 (reply `Could not look up the other repo's Chief of Staff.` plus a Cleanup line). The spec's Sending step 2 has neither.
- Request and reply labels come only from what the script printed (the sender project's T3 title and the ids), never from the message header.
- `reply` reads the store: it refuses a reply whose `from` thread is not a Chief of Staff thread and prints `source <project title> <thread id>` first. The spec had it as a pure parser.
- A refusal reply goes to the sender only for `same repo`, `not for this repo` and `command: ...`, after `check` verified the sender. For `malformed`, `not-user`, `words differ`, `not a chief of staff thread` and exit 2 the refusal is posted locally and nothing is sent.
- A reply's `(from <thread link>)` names the thread the message claims, shown for the user to check; it is not proof of the sender.
- A ticket helper started from a request may only create new Backlog tickets (plus the new ticket's parent epic and links). The spec said the helper template changes by one line only.
- When a request's helper files nothing (its `Tickets:` lists no ticket), the receiver sends the sender `Refused: nothing filed; details in the receiving Chief of Staff thread`. The spec allowed only ticket lines or `Refused: ticket helper ended without a report`.
- For a helper whose first line carries `Request from`, the helper-notice bullet and the `TICKET HELPER DONE` template also surface an epic line or an edit to an existing ticket the helper left undone, under `Needs the user:`. The spec allowed only a duplicate ticket or a proposed epic.
- The `For:` line is parsed but not checked; the check runs on the user's words.
- The words may name this repo by `owner/name`, repo name or this thread's T3 project title. The product name in `project.md` is not matched.
- `find` skips this repo only when `project.md` names one, and skips deleted projects and does not fold hyphens, so "collective wisdom" matches the title but not the repo name.
