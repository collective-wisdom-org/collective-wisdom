# CW-259: Let tag-release.sh cut minor release versions

**Status:** Shipped
**Shipped:** in PR #268, as specified
**Ticket:** [#259](https://github.com/collective-wisdom-org/collective-wisdom/issues/259)

## Goal

`./tag-release.sh --minor` tags `origin/main` with `v0.N.M`, the next minor of the latest `v0.N`, so a small fix can ship between numbered releases. Plain `./tag-release.sh` keeps making `v0.N` the way it does now.

## Today

Facts from `main` at `cbc35dc`.

- `tag-release.sh` takes only `--dry-run`. It reads tags from `origin` with `ls-remote --tags origin 'refs/tags/v0.*'`, folds each annotated tag to its commit, and keeps the lines matching `^v0\.[0-9]+ `. A `v0.2.1` tag is dropped there, so it counts neither as the last release nor as "origin/main already tagged".
- It refuses (exit 1) when `origin/main` already carries a kept tag, then tags `origin/main` with `v0.(last+1)`, `v0.1` when there are none. N is compared as a number (`sort -t. -k2,2n`).
- Origin has `v0.1` and `v0.2`; `v0.2` is on `origin/main` today.
- `agent-team/scripts/test_install.py` `test_tag_release` is one table-driven test over a throwaway origin (tags `v0.1` on A, `v0.2` on B = `origin/main`, `v0.9` on an unpushed side commit S).
- README § Releases documents the two commands and the refusal rule.

## Design

### Flags

`./tag-release.sh [--minor] [--dry-run]`, in any order. Any other argument prints the usage line and exits 2, as now.

### Reading tags

The tag list keeps lines matching `^v0\.[0-9]+(\.[0-9]+)? ` instead of `^v0\.[0-9]+ `. Everything else about reading stays: origin only, local tags ignored, annotated tags folded to their commit.

### The "nothing new" refusal

It runs on the wider list in both modes: `origin/main` carrying either a `v0.N` or a `v0.N.M` tag refuses with `Refusing: nothing new since <tag> (origin/main is <sha>).`, exit 1.

### Next tag

- Plain: `LAST` is the highest `v0.N` among plain tags only, so a `v0.2.1` never shifts plain numbering. `v0.(N+1)`, or `v0.1` with none. Unchanged.
- `--minor`: take that same `LAST` (`v0.N`). With none, refuse with `Refusing: --minor needs a v0.N release to follow; there is none on origin.`, exit 1. Otherwise find the highest M among `v0.N.M` tags for that N, compared as a number (`v0.2.10` follows `v0.2.9`), and make `v0.N.(M+1)`, or `v0.N.1` with none. Minors of an older N (`v0.1.3` after `v0.2`) are ignored.

Tagging, pushing, the dry-run line and the local-tag cleanup on a failed push stay as they are, with the new tag name. The tag message stays `collective-wisdom <tag>`.

### Tests

New rows in `RELEASE` in `test_tag_release`, one per rule, plus a way for a row to add tags on origin at a named commit (the minors need commits the fixture does not tag today):

- `--minor` after `v0.2` makes `v0.2.1`.
- `--minor` with `v0.2.9` makes `v0.2.10` (numeric M), and ignores a `v0.1.5`.
- Plain with `v0.2.1` present still makes `v0.3`.
- `--minor` with no `v0.N` refuses.
- `--minor` when `origin/main` carries a `v0.N.M` refuses, and plain refuses too.
- No separate `--minor --dry-run` row: the dry-run branch is shared, and the plain dry-run row covers it. The numeric row uses `v0.2`, `v0.2.9`, `v0.2.10` and an older `v0.1.15`, so a text sort or counting every minor fails it.

### Docs

README § Releases: add the `--minor` line to the command block and one sentence on minor numbering and its refusals. The script's header comment and usage line name the new flag.

## Leaves out

Per the ticket: major versions (`v1.0`), pre-release suffixes, tags outside `v0.*`, the `plugin.json` versions, and `install.sh` or how a machine picks a release.

## Calls I made

- Plain `./tag-release.sh` now also refuses when `origin/main` carries a `v0.N.M` tag. The ticket says plain behavior stays as it is and names this refusal only for `--minor`, but promoting a commit that was just tagged `v0.2.1` to `v0.3` without new commits is the same "nothing new" case. No `v0.N.M` tag exists today, so nothing that works now stops working.
- `--minor` follows the highest `v0.N`, even if that tag is not an ancestor of `origin/main` (as plain numbering already does).
- The flag is `--minor` as the ticket names it, though semver would call the third number a patch.
- Minors of an older release (`v0.1.3` after `v0.2`) are ignored when picking the next minor.
- The test fixture gets a per-row "tags to add" column rather than more fixture tags, so existing rows keep their meaning.
