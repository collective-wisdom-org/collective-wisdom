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

Before acting, read **ship-loop** § Repo invariants and `docs/agents/project.md` (tracker scope `<TEAM>`, issue prefix `<PREFIX>`, labels). The operations named below are defined in `docs/agents/trackers/README.md`.

Whole-backlog tidying (ranking, filling empty priority and labels, state drift, duplicates) belongs to **project-manager**, not this skill.

## Steps

1. **Check the code first.** Find how the feature works today: grep or read the files, and name the files and functions. This goes in a short **Today** section, so whoever picks the ticket up doesn't have to investigate again. Skip it when the ticket is about something that doesn't exist yet in any form.
2. **Check external facts.** Anything outside the repo that the ticket names (a subreddit, an API, a library, a site's page layout) gets checked before it goes in. Say in the report what you couldn't check.
3. **Look for an existing ticket.** Search open <PREFIX> tickets by title words (`list-tickets`, scope <TEAM>, title words). If one already covers it, offer to edit that one instead of making a duplicate.
4. **Write it** in the shape below.
5. **Place it** under an epic (§ Placement), then add links (§ Links) and labels (§ Labels).
6. **Save** with `create-ticket` (or the edit operations). New tickets go to Backlog.
7. **Report back** (§ Report).

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

Small tickets stay small: a bug fix can be the one line, **Today** and **Acceptance**. No Wave, branch name, project or plan task link.

Titles are a plain description of the change ("Add a writing-tickets skill"), not a category prefix. Epic titles keep their `Epic:` prefix.

## Don't invent requirements

When the request is terse, fill only the gaps needed to make the ticket actionable, and keep each addition small. List every detail you assumed in the report, so the user can strike it. Don't add features, settings or edge cases the user didn't ask for.

## Placement

- Find epics at run time: `list-tickets`, scope <TEAM>, title text `Epic:`. Don't rely on a list in this skill; epics come and go.
- Set the ticket's parent (`set-parent`) to the matching epic, and add a line for it to the epic's ticket list in the epic description. Edit the epic description as a patch: read it, add the one line in the list's style, write it back with nothing else changed.
- No epic fits: leave the ticket without a parent and say so in the report. Propose a new epic only when 3 or more open tickets share a theme no epic covers, and create it only if the user agrees.

## Links

- `set-blocked-by` only for a real ordering dependency: this ticket can't be built or can't work until the other one ships.
- `set-related` for tickets that touch the same code or behaviour.
- Never block on a Canceled or Duplicate ticket. Check state before linking.

## Labels

- One type: `Feature`, `Improvement` or `Bug`.
- One or two areas from the list in `docs/agents/project.md` § Areas and labels.
- Never add `agent` or `agent-skip`. Those belong to the Chief of Staff and the user.
- Priority: set it only when the user gives one or the request makes it plain (a bug that breaks sign-in). Otherwise leave it empty; the project manager hygiene child fills it.
- Status: Backlog for new tickets. Never move a ticket to Todo; that is the user's call.
- A ship-loop child changes only its own ticket, and this skill doesn't widen that.

## Editing

- Small change: patch the description. Read it, change the part that needs changing, write it back. Don't rewrite sections the user didn't ask about.
- When the scope grows or shifts, update the title to match.
- When an edit changes what the ticket depends on, update its links too.

## Product rules

Every ticket follows `docs/agents/project.md` § Product rules. A ticket that exposes data beyond its owner (public links, shared items, admin views) gets a line in **Scope** saying so, and the report flags it.

## Writing

Plain sentences, per the `human-writing` skill. No em dashes. Name files, functions and tickets; don't describe them vaguely.

## Report

After saving, tell the user:

- the ticket link,
- where it was placed (epic, or none and why),
- its links (blocked-by, related),
- the labels and priority set,
- every assumption you made and every fact you couldn't check.
