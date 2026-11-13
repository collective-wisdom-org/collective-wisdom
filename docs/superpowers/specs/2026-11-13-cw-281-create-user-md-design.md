# CW-281: Have the Chief of Staff create user.md when this machine has none

**Status:** Draft
**Ticket:** [#281](https://github.com/collective-wisdom-org/collective-wisdom/issues/281)

## Goal

On `start the team`, `take over` and `resume`, the Chief of Staff notices when `~/.config/collective-wisdom/user.md`, or this repo's row in it, is missing. It asks the user for the details, shows exactly what it will write, and writes it only after the user says yes. A repo that was set up before CW-162 and CW-163 then gets a working `cos_approve_pr.py` and `gh.sh` without a hand edit.

## Today

Facts from `main` at `34031d8`.

- `agent-team/scripts/user_config.py` reads `user.md`: `path()`, `login(root)` (raises `UserConfigError` on a duplicate or malformed row), `subscription_usage(provider)`. Template: `agent-team/templates/user.md`.
- `agent-team/scripts/setup_repo.py status` prints `set`, `missing` or `placeholders: ...`, then one JSON line of facts that includes `gh_logins` (from `gh auth status`, logins only), `mapped_login`, `user_md_exists` and, only on a malformed file, `user_md_error`.
- `setup_repo.py user --login L [--subscription N|none] [--repo-key K]` writes the row. It creates the file from the template when it is missing (the subscription figure applies only then), adds the row to an existing file and leaves the rest alone, or replaces an existing row for the same repo. It has no way to show what it would write.
- `chief-of-staff/startup.md` § Setup step 0 runs `setup_repo.py status` on `start the team` and reads `setup.md` only on `missing` or `placeholders`. On `set` it goes straight to step 1, so `user.md` is never checked.
- `take over` (`rotation.md` "Take over" step 4), `resume` (`kill-switch.md` § Resume step 4) and resume mode all run the lean take-over pass, whose step 4.1 is `startup.md` § Start-up clean-up and the dashboard step. None of them runs `setup_repo.py status`.
- `start the team` with empty state reaches § Start-up clean-up through Setup step 4. So § Start-up clean-up is the one place all three triggers pass through. `resume` from `kill-switch.md` reaches it twice (its step 4 names it and the lean pass runs it again).

## Design

### Script: `setup_repo.py`

1. **`user_md` in the status facts.** A new pure function `user_md_need(exists, mapped_login, error)` returns one of:
   - `error`: `user_md_error` is set (malformed file or duplicate row).
   - `no-file`: the file does not exist.
   - `no-row`: the file exists and has no row for this repo.
   - `ok`: the file has a valid row for this repo.

   `facts()` adds its result as `user_md`. The existing keys stay as they are, so `setup.md` keeps working unchanged.

2. **`user --dry-run`.** Prints the full text the command would write, after a first line `would write <path>`, and writes nothing. Same validation and exit codes as a real run. The Chief of Staff shows this text to the user, so what they agree to is what gets written.

### Skill: `chief-of-staff`

A new section, `startup.md` § User settings check, run as the first step of § Start-up clean-up, once per `start the team`, `take over` or `resume` (the second pass through § Start-up clean-up in `resume` skips it).

1. Run `python3 ~/.collective-wisdom/scripts/setup_repo.py status` from the root checkout (on `start the team`, reuse the output from Setup step 0). Read `user_md` from the JSON line.
2. `ok`: nothing to do, no report line.
3. `error`: put `user.md: <user_md_error>` under Needs you, leave the file alone and carry on with the pass.
4. `no-file` or `no-row` with an empty `gh_logins`: put `No gh login on this machine; run gh auth login, then resume.` under Needs you and carry on.
5. `no-file` or `no-row` otherwise: run `setup_repo.py user --dry-run --login <first of gh_logins>` (adding `--subscription none` for `no-file`) and post, under Needs you:
   - which logins `gh auth status` lists (logins only),
   - for `no-file`, that the subscription figure is a dollar amount or `none`,
   - the dry-run text (the whole file for `no-file`, the one new row for `no-row`),
   - `Reply yes to write it, give another login or figure, or no to skip.`

   Then carry on with the pass. The question does not hold up any ticket.

A new row in the SKILL.md commands table covers the reply, checked like every other answer with `cos_user_check.py latest` on the whole message:

- `yes`: run `setup_repo.py user` with the values last shown, then `setup_repo.py status` again and report the new `mapped_login`.
- A different login (one of `gh_logins`) or figure: run the dry run again with those values and ask again. Nothing is written until a plain `yes`.
- Anything else, including `no`: write nothing, report `Skipped user.md.` and do not ask again until the next start, take over or resume.

The write path never touches an existing row: the check only asks on `no-file` and `no-row`, and `setup_repo.py user` adds a row to an existing file without changing the rest.

### Docs

- `agent-team/templates/user.md`: "`set up this repo` writes it" becomes "`set up this repo` or the Chief of Staff's start writes it".
- `chief-of-staff/setup.md`: one line in the `status` facts list for `user_md`, and one for `user --dry-run` in the command table.
- `~/.collective-wisdom/docs/agents/chief-of-staff.md` (source `agent-team/docs/agents/chief-of-staff.md`) only if it describes start-up steps; the documenter decides.

### Tests

In `agent-team/scripts/test_setup_repo.py`:

- One table-driven test for the check that decides whether to ask: no file, file without this repo's row, complete file, malformed file (a row whose login is not a GitHub login), each run through `setup_repo.py status` with the temp `HOME` the file already uses, asserting `user_md`.
- One test for `user --dry-run`: on a missing file and on a file without the row, it prints the same text a real run then writes, and the file is unchanged (still missing, or byte-for-byte the same) after the dry run.

## Calls I made (surprising first)

- **A decline is remembered only by the conversation, not by state.** The check runs only on start, take over and resume, so "not asked again until the next one" holds without a state key. A rotation in between asks again, since take over is one of the triggers.
- **The question does not block the pass.** Tickets keep moving while the user decides; the only things that fail without `user.md` are merges through `cos_approve_pr.py` and `gh.sh` account switching, which already fail today.
- **The login offered first is the first of `gh_logins`, even when there is only one.** `setup.md` takes a single login unasked; here the ticket asks for the user's yes, so even one login is shown and confirmed.
- **The subscription figure defaults to `none`** in the first preview, as `setup.md` does.
- **A malformed file does not stop the start.** `setup.md` stops on `user_md_error`; here it goes under Needs you and the pass carries on, since the team was already running before this check existed.
- **A preview mode in the script (`--dry-run`) instead of the Chief of Staff composing the text itself.** The user sees the exact bytes `setup_repo.py user` writes, so there is no gap between what was shown and what was written.
- **A new `user_md` fact instead of having the skill combine three keys.** It is the "check that decides whether to ask" the ticket wants tested, in one place.
- **The check sits in § Start-up clean-up**, the one step all three triggers already pass through, rather than a new step in each of the three files.
- **Reply wording is plain `yes` / `no`**, not `approve N`, since this is not a ticket.

## Leaves out

- What `set up this repo` asks for a new repo.
- Changing an existing row. The user can still say so in setup.md's rerun or edit the file.
- `cos_approve_pr.py` on Python 3.9 (`sys.stdlib_module_names`), a separate fix.
- Tokens in `user.md`.

## Acceptance

- A machine with no `user.md` and a repo whose `status` is `set`: start, take over and resume each ask for the login and the figure, show the file they will write, and write it only after `yes`. `cos_approve_pr.py` and `gh.sh` then work without a hand edit.
- A file with no row for this repo gets only the row; the rest of the file is byte-for-byte unchanged.
- An existing row is left alone.
- A decline writes nothing and is not asked again within the same start, take over or resume.
- The table-driven `user_md` test covers no file, no row, complete file and malformed file.
- `python3 -I -m pytest -q agent-team/scripts` passes.
