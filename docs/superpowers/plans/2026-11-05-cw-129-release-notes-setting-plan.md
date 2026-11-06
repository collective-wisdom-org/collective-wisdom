# CW-129: Release notes setting: plan

**Ticket:** [CW-129](https://github.com/collective-wisdom-org/collective-wisdom/issues/129)
**Spec:** [2026-11-05-cw-129-release-notes-setting-design.md](../specs/2026-11-05-cw-129-release-notes-setting-design.md)

Edit under `agent-team/` only (plus this repo's `docs/agents/project.md`, which is local). Do not touch `scripts/release_notes.py`.

## Tasks

1. **`agent-team/scripts/project_config.py`.** Add `release_notes_enabled()` after `no_ci()`: reads the first backticked value of the row whose Key starts with `Publish release notes`; `off` (any case) is `False`; missing row or anything else is `True`.
2. **`agent-team/scripts/merge_pr.py`.**
   - `read_facts()`: `f["notesOn"] = project_config.release_notes_enabled()` next to `noCi`; only collect added `RELEASE` files into `want` when on.
   - `gate()`: wrap the release note block (the `notes`/section check and the dated-heading loop) in `if f.get("notesOn", True):`. Keep the Proof checks outside it.
   - `main()`: call `publish(...)` only when `f.get("notesOn", True)`.
   - Module docstring: publishing depends on the `Publish release notes` row.
3. **Test** at the end of `agent-team/scripts/test_merge_pr.py`: one table-driven test, rows missing, `on`, `off`, `maybe`. Each writes a project.md with that row (or none) to `tmp_path`, sets `PROJECT_MD` via monkeypatch, and builds facts with `project_config.release_notes_enabled()` stored as `notesOn`. Check `gate()` on a body with no `## Release note` section (cause line for all but `off`, `None` for off) and, via `main()` with a fake runner and a monkeypatched `merge_pr.publish` recorder, that publish ran for all but `off`. Reuse `green()` and `fake()`.
4. **Template** `agent-team/templates/project.md`: replace the § Docs `Release notes` row with `| Publish release notes (`on` or `off`) | `off`. ... |` (spec § The setting; keep the first backticked token `off`, keep notes free of other backticks before it). Drop the Repo invariants bullet about the `release-notes` branch and move its rule into the new row's text.
5. **This repo's** `docs/agents/project.md`: add the same row with `on`, keep the invariant bullet and the existing Release notes row content folded into it.
6. **Docs and skills** (say it applies only when `Publish release notes` in project.md § Docs is not `off`): `open-pr` (line ~70 PR body bullet, ~99 release note paragraph; later mentions "if any"), `merge-pr` (Closeout in PR paragraph and its last sentence), `agent-team/docs/agents/documenter.md` check 5 and the re-run line, `agent-team/docs/superpowers/README.md` § Release notes and § Merge gate, `agent-team/docs/agents/README.md` release notes line, passing mentions in `kickoff-feature`, `ship-loop` § Close, `security-review`.
7. Run `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.

No `test_project_config.py` row: the one test in step 3 covers the rule.
