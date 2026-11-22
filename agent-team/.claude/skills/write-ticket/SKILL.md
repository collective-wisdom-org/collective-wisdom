---
name: write-ticket
description: >-
  Writes or edits tickets in the house shape: checks the
  code, places the ticket under an epic, sets links and labels, and reports back.
  Use for new ticket, add a ticket, a ticket for X, capture tickets, edit
  ticket N, update <PREFIX>-N, or organize the tracker (place and link the tickets the user
  names).
user-invocable: true
---

# Write a ticket

Read **ship-loop** § Repo invariants and `docs/agents/project.md` (tracker scope `<TEAM>`, issue prefix `<PREFIX>`, labels) first. The operations below are in `~/.collective-wisdom/docs/agents/trackers/README.md`. Whole-backlog tidying (ranking, empty priority and labels, state drift, duplicates) is **project-manager**'s.

## Steps

1. **Check the code first.** Find how the feature works today and name the files and functions in a short **Today** section; skip it when the thing doesn't exist yet.
2. **Check external facts** the ticket names (a subreddit, an API, a library, a site's page layout) before they go in.
3. **Look for an existing ticket:** `list-tickets`, scope <TEAM>, title words. If one covers it, offer to edit that one instead.
4. **Write it** in the shape below, **place it** under an epic (§ Placement), add links (§ Links) and labels (§ Labels).
5. **Save** with `create-ticket` (or the edit operations); new tickets go to Backlog. **Report back** (§ Report).

## Shape

```markdown
<One line: the problem or goal.>

## Today
<How it works now, with file and function names. When relevant.>

## Scope
- <What to build or change.>

## Acceptance
- <What a reviewer checks to call it done.>

## Out of scope
- <Nearby work this ticket doesn't do. When there is any.>
```

Small tickets stay small: a bug fix can be the one line, **Today** and **Acceptance**. No Wave, branch name, project or plan task link. Titles describe the change plainly ("Add a writing-tickets skill"), no category prefix; epic titles keep `Epic:`.

## Don't invent requirements

For a terse request, fill only the gaps needed to make the ticket actionable, each small, and list every assumed detail in the report. Add no features, settings or edge cases the user didn't ask for.

## Placement

- Find epics at run time (`list-tickets`, scope <TEAM>, title text `Epic:`).
- `set-parent` to the matching epic and add a line for the ticket to the epic's list in its description, as a patch: read it, add one line in the list's style, write it back with nothing else changed.
- No epic fits: leave it without a parent and say so in the report. Propose a new epic only when 3 or more open tickets share a theme no epic covers; create it only if the user agrees.

## Links

- `set-blocked-by` only for a real ordering dependency (this ticket can't be built or can't work until the other ships); never on a Canceled or Duplicate ticket, so check state first.
- `set-related` for tickets that touch the same code or behaviour.

## Labels

- One type (`Feature`, `Improvement` or `Bug`) and one or two areas from `docs/agents/project.md` § Areas and labels. Never add `agent` or `agent-skip` (the Chief of Staff and the user own them).
- Priority only when the user gives one or the request makes it plain (a bug that breaks sign-in); otherwise empty, for the project manager hygiene child.
- Status: Backlog for new tickets. Never move a ticket to Todo; that is the user's call.

## Editing

Patch the description (read, change only what needs it, write back). When the scope shifts, update the title; when an edit changes what the ticket depends on, update its links.

## Product rules

Follow `docs/agents/project.md` § Product rules. A ticket that exposes data beyond its owner (public links, shared items, admin views) says so in **Scope**, and the report flags it.

## Writing

Plain sentences (`human-writing`), no em dashes; name files, functions and tickets.

## Report

After saving, tell the user: the ticket link; its placement (epic, or none and why); its links; the labels and priority set; every assumption and every fact you couldn't check.
