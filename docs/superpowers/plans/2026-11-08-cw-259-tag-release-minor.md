# CW-259 plan: tag-release.sh --minor

Spec: [design](../specs/2026-11-08-cw-259-tag-release-minor-design.md)

## Tasks

1. `tag-release.sh`
   - Accept `--minor` (any order with `--dry-run`); update the header comment and usage line.
   - Widen the tag filter to `^v0\.[0-9]+(\.[0-9]+)? ` so `v0.N.M` tags count for the "nothing new" refusal (both modes).
   - `LAST` stays the highest plain `v0.N` (plain tags only).
   - `--minor`: refuse (exit 1) with no `LAST`; else find the highest numeric M among `LAST.M` tags and tag `LAST.(M+1)`, or `LAST.1`.
   - Base-10 arithmetic (`10#`) as today. `shellcheck tag-release.sh` clean.
2. `agent-team/scripts/test_install.py`
   - Add a "tags to add on origin" column to `RELEASE` (name -> commit) and apply it before the run.
   - Rows: `--minor` after v0.2 -> v0.2.1; v0.2.9 present -> v0.2.10 and a v0.1.5 ignored; plain with v0.2.1 -> v0.3; `--minor` with no v0.N refuses; `--minor` and plain refuse when origin/main carries a v0.N.M.
3. `README.md` § Releases: add `--minor` to the command block, one sentence on minor numbering and refusals.

## Verify

`shellcheck tag-release.sh`, `python3 -I -m pytest -q agent-team/scripts`.
