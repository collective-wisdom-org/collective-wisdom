# CW-281: Create user.md at start: plan

**Spec:** [design](../specs/2026-11-13-cw-281-create-user-md-design.md)

## Task 1: script (`agent-team/scripts/setup_repo.py`)

- Add a pure `user_md_need(exists, mapped_login, error)` returning `error`, `no-file`, `no-row` or `ok` (in that order of precedence). `facts()` adds it as `user_md`; existing keys stay.
- Add `user --dry-run`: same validation and exit codes, prints `would write <path>` then the full text a real run would write, and writes nothing (no mkdir either). Refactor `cmd_user` so one function builds the text and the real run writes it.
- Tests in `test_setup_repo.py`: one table-driven test of `user_md` through `status` (no file, no row, complete, malformed login row); one test that `--dry-run` output matches the later real write for a missing file and for a file without the row, and leaves the file untouched.

## Task 2: skill and docs (markdown only)

- `agent-team/.claude/skills/chief-of-staff/startup.md`: add § User settings check as the first step of § Start-up clean-up, as in the spec (once per start, take over, resume; the second pass in `resume` skips it).
- `SKILL.md`: add the reply row (`yes`, another login or figure, anything else) to the commands table, checked with `cos_user_check.py latest` on the whole message.
- `setup.md`: add `user_md` to the facts list and `user --dry-run` to the command table.
- `agent-team/templates/user.md`: "`set up this repo` or the Chief of Staff's start writes it".

Verify: `python3 -I -m pytest -q agent-team/scripts`; `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
