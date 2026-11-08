# As-built: dashboard layout overhaul

**Shipped:** in PR #203
**Ticket:** CW-195
**Spec:** [2026-11-08-cw-195-dashboard-layout-overhaul-design.md](../specs/2026-11-08-cw-195-dashboard-layout-overhaul-design.md)

## Differs from the spec

- The eight before and after screenshots are not in the PR. GitHub has no command-line way to attach an image and image files are never committed to the branch. The PR lists this under `Not proven`; the images are on the builder's machine.
- A stale session no longer fades as a whole. The spec kept "the stale fade", but a faded session failed 4.5:1 for muted text. Stale sessions now use normal muted text with the bars faded to 50% opacity, and keep the `stale` pill.
- The running bar and the build-approval edge use `#b07a00` instead of `#bf8700`, because the old amber missed 3:1 against the light track and tint.
- The card grid aligns cards to the top, so a short card is not stretched to the height of a tall neighbour with a Gantt open.
- The risk badge is left out when a row has no risk, and the Gantt agent name carries a `title` attribute with the full name.
