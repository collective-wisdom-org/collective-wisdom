# WISE-424: Show who owns a dashboard ticket and hide Agents on tickets built by someone else

**Status:** Shipped
**Ticket:** [#424](https://github.com/collective-wisdom-org/collective-wisdom/issues/424)
**Shipped:** in PR #PRN, with differences: [as-built](../as-built/2026-11-15-wise-424-ticket-owner-avatar-as-built.md)

## Goal

Each dashboard card for a ticket shows its owner's GitHub avatar and login in the top right. A card owned by someone other than the person running the dashboard drops the dead `Agents 0` control, since that ticket's agent sessions live on the owner's machine.

## Today

Facts from main at `de35269`, `agent-team/scripts/dashboard/`.

- `merged.ts` `createMerged` runs `gh pr list --state merged --json number,title,headRefName,mergedAt,url`; `parseMerged` builds `MergedEntry` with no author.
- `open.ts` `createOpenPrs` runs `gh pr list --state open --json number,headRefName`; `parseOpen` gives a map of ticket id to PR number, used by `buildApi` for a status row's PR link.
- `backlog.ts` already reads `author` for each open issue (to keep only team authors) but drops it from `BacklogItem`.
- `titles.ts` reads each state ticket's title with `gh issue view N --json title --jq .title` (GitHub tracker only).
- The dashboard has no viewer login. `gh api user --jq .login` gives it.
- `server.ts` sends `Content-Security-Policy: default-src 'self'; style-src 'self' 'unsafe-inline'` on `/`, so no image from another origin loads, and no inline event handler runs.
- `app.js`: `ticket()` (Status and Backlog tabs) and `renderMerged()` (Done tab) draw the head with `rowHead(idHtml, title, extra)` and the foot with `panelSwitch(scope, id, { gantt, view, details })`, which always draws an Agents segment, disabled as `Agents 0` when the Gantt has no tasks.
- `https://avatars.githubusercontent.com/<login>?s=N` answers 200 with the image directly (no redirect); `https://github.com/<login>.png` redirects there.

## Design

### Owner and viewer in the API

- Login rule: a GitHub login, `^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$`. Anything else (a missing author, a bot shown as `app/name`) gives no owner.
- `merged.ts`: ask for `author` too; `parseMerged` sets `owner: <login>` on an entry whose `author.login` passes the rule.
- `open.ts`: ask for `author` too; `parseOpen` keeps the author next to each PR number (the higher PR number's author when a ticket has two). `createOpenPrs` gets a second getter for the owner map, so the existing number map and its callers stay as they are.
- `backlog.ts`: `BacklogItem` gets `owner` (the author login it already reads and checks).
- `titles.ts`: the per-issue read asks for `title,author` and keeps the author login beside the title, with a new getter for the owner map. A ticket whose title read failed has no owner.
- `buildApi`:
  - Done entries carry `owner` from `parseMerged`.
  - A status row's owner is the author of its open PR when `openPrs` has one, else the issue author from `titles`, else none.
  - Todo and Backlog rows carry the `BacklogItem` owner.
  - Ticket helper rows, project manager rows and the Chief of Staff carry no owner.
- `server.ts`: reads the viewer once with `gh api user --jq .login` in the background at start, keeps it for the life of the process, and tries again at most every 5 minutes after a failure or a value that fails the login rule. `/api` gets a top-level `viewer` (the login, or null).

### Avatar (`app.js`, `index.html`)

- New `ownerBadge(login)`: empty for no owner; else `<span class="owner" title="<login>"><span class="avatar" aria-hidden="true"><span class="initial">L</span><img src="https://avatars.githubusercontent.com/<login>?s=40" alt="" loading="lazy" width="20" height="20"></span><span class="login"><login></span></span>`, with the login escaped. `L` is the first letter, upper case.
- `rowHead` takes the badge as a new trailing argument and places it at the right end of the head, beside the copy button.
- The initial circle sits under the image, so a slow or failed image shows the initial. A document-level `error` listener in the capture phase (image errors do not bubble) hides any `.avatar img` that fails, which also hides the browser's broken-image glyph. No inline handler, so the CSP stays free of `unsafe-inline` for scripts.
- CSP: add `img-src 'self' https://avatars.githubusercontent.com`. Only that one host, and no proxy in the server.
- Style: 20px round avatar, login in `--muted` at the meta line's size, the badge pushed right in the head's grid with `margin-left:auto` (or its own grid column). On a narrow card the login text truncates with an ellipsis before the title does.

### Agents rule

- New exported `foreign(owner, viewer)`: true when both are logins and they differ, compared case-insensitively (GitHub logins are). No owner, or no viewer, gives false.
- `panelSwitch` takes a `hideAgents` flag. With it, and when the Gantt has no tasks, the Agents segment is left out; the Details segment and its panel stay, and the switch still draws when Details is there. With no segment left, the switch draws nothing.
- `ticket()` and `renderMerged()` pass `hideAgents: foreign(r.owner, viewer)`. `renderStatus`, `renderBacklog` and `renderMerged` gain a `viewer` argument (default null), and the shell passes `last.viewer`. A change of `viewer` redraws the tabs.

### Other places checked

- Details panel: stays on every card. It already says only what it knows; for someone else's ticket it shows the PR and spec facts read from GitHub and leaves out the local usage rows.
- Spend line (Done tab `$` and tokens) and the status summary line: already drawn only when the local ledger or Gantt has data, so someone else's ticket shows none. No change.
- Status tab cards with an owner other than the viewer: same rule as Done.
- Todo and Backlog cards: show the issue author, and drop Agents (no sessions exist for an unstarted ticket) when the author is not the viewer.
- Linear and Jira repos: Todo, Backlog and spec-stage cards get no owner (their lists carry no GitHub login); PR-stage and Done cards still do, since the PRs are on GitHub.

### Tests

Per `AGENTS.md` § Testing, one table-driven test per rule:

- `merged.test.ts`: `parseMerged` with a valid author, no author, a bad login (`app/dependabot`), keeps `owner` only for the valid one.
- `open.test.ts`: `parseOpen` owner map, including two PRs for one ticket.
- `api.test.ts`: the owner precedence for a status row (open PR author, else issue author, else none), Backlog owner, and no owner on helper and project manager rows; `viewer` in the API.
- `app.test.js`: one table over card type (Done, Status, Backlog) by owner (viewer, other, other in different case, none) by viewer (known, null) by Gantt (empty, with tasks): avatar present or not, Agents present or not, Details always present where it was. Plus `ownerBadge` escaping a login.
- `server.test.ts`: the `/` CSP has the `img-src` host.

## Leaves out

- Mapping a GitHub login to a display name or a Linear or Jira user.
- Filtering tabs by owner.
- Showing another person's agent sessions.
- A same-origin avatar proxy.

## Calls I made

- **Agents is hidden only when the card has no local sessions.** The ticket says to drop Agents whenever the owner is not the viewer. A ticket someone else wrote, still in spec here, has an issue owner who is not the viewer but real sessions on this machine; hiding them would lose data. So a foreign owner drops Agents only when it would read `Agents 0`. Every Done-tab case in the acceptance still holds, since a ticket built elsewhere has no sessions here.
- **Before a PR exists, a status card shows the issue author**, as the ticket says. A ticket David builds from Noah's issue shows Noah until the PR opens, then David.
- **Avatar from `avatars.githubusercontent.com/<login>`, not `github.com/<login>.png`.** The `.png` form redirects to the avatars host, so the CSP would need both hosts; the direct form needs one.
- **CSP `img-src` for one host instead of a proxy.** Tighter code and no new server route; the cost is that the browser asks GitHub for the avatar.
- **No viewer means today's behaviour.** A failed `gh api user` read keeps Agents on every card and still shows avatars.
- **Logins compare case-insensitively**, as GitHub treats them.
- **A bot PR author (`app/…`) gives no owner**, so its card keeps today's look.
- **Details stays on every card, and the spend and summary lines need no change**; they already draw nothing without local data.
- **Avatar size 20px with the login beside it**, both in the head's right end; the login truncates on narrow cards.

## Touches

None of: data, money, auth, user email, migrations. It reads the viewer's GitHub login through the existing `gh` wrapper and shows public GitHub logins and avatars.
