# As-built: friendly dashboard

**Shipped:** in PR #340
**Ticket:** CW-266
**Spec:** [2026-11-14-cw-266-friendly-dashboard-design.md](../specs/2026-11-14-cw-266-friendly-dashboard-design.md)

## Differs from the spec

- The spec shows an Up next row as `CW-251 · Low risk · Waiting to build`. Rows in a queued group show the group label plus ` since HH:MM` (`Waiting to build since 15:46`). Rows in the `Other` group show the stage sentence instead, because `Blocked or waiting` says too little.
- A blocked Up next row is laid out like a card (sentence, then **Open issue**, then the footer). Other rows keep the meta line and the toggles on one line.
- An open Agents or Details section on a row moves to its own full-width line below it.
- The Chief of Staff state dot is drawn in CSS, not with a `●` character, and sits on the meta line.
- The Gantt container uses a soft background, with the track in the card colour.
