# CW-72 plan: context compacter agent

Spec: [2026-11-04-cw-72-context-compacter-design.md](../specs/2026-11-04-cw-72-context-compacter-design.md). All edits are under `agent-team/` except `docs/agents/*` entries, which are linked into `agent-team/docs/agents/` (edit `agent-team/docs/agents/...`; `org-chart.md` and `README.md` there too).

Task 0 (verification, every task): `python3 -I -m pytest -q agent-team/scripts` (use `uvx pytest -q agent-team/scripts` if pytest is missing).

1. **`agent-team/scripts/compact_check.py`** per spec § 1. Differences from the spec text, because `main` moved on: the default base is `project_config.target_ref()` (the merge target branch row, CW-125), evaluated only when `--base` is not given; follow the `pr_diff_delta.py` layout (`sys.path` insert, `app_root.root()`, `project_config`). Run git in `app_root.root()`. Skip with `compact: skip (not collective-wisdom)` when `<root>/install.sh` is missing (check this first, before reading git). Size is characters of the decoded text. Exit 2 with `compact: cannot read <what>` on git failure.
2. **`agent-team/scripts/test_compact_check.py`**: one table-driven test over a temp git repo, running the script in a subprocess with `--base`, covering the six cases in the spec § 1 plus the app case (no `install.sh`, skip).
3. **`agent-team/.claude/agents/compacter.md`** and **`agent-team/docs/agents/compacter.md`** per spec § 2.
4. **`agent-team/.claude/skills/build-from-plan/SKILL.md`**: new `## Compaction pass` before `## When all tasks pass`, per spec § 3. Keep it short.
5. **Docs** per spec § 4: `ship-loop` phase 2 line, `open-pr` § Create PR overlay (`Context size:` line), `org-chart.md` Compacter row and chart node, `docs/agents/README.md` row.
6. Verify: Task 0, then `python3 scripts/compact_check.py --base origin/main` run on this branch prints the sizes and a `compact:` line (expected: run, since the diff adds text).

The compaction pass then runs on this very change (dogfood) before the PR opens.
