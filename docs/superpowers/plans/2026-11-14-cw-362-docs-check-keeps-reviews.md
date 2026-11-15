# CW-362 plan: keep the reviews when only the docs check changed the head

Spec: [design](../specs/2026-11-14-cw-362-docs-check-keeps-reviews-design.md). Follow it; it wins over this list.

## Tasks

1. **`pr_diff_delta.py` + `project_config.py`.** Add the `living` kind to `delta` per the spec's § A third kind: one fix commit with one parent equal to the reviewed head, exact subject `docs: bring docs in line with <PREFIX>-<N>`, every differing file a docs file or a regular `.md` living doc from the `Living docs to search:` line of `project.md` § Docs check as committed on `origin/<target>` (add a reader in `project_config.py`, built on `_committed_rows`), none on `approval_policy.on_hands_path`. Any failure inside the new check gives `changed`. `same` and `docs` win first. Update the docstring and `main`'s output.
2. **`review_gate.py`.** Accept `living`; print the spec's note wording and `note head <head> reviewed <sha>`. Update the docstring.
3. **`merge_pr.py`.** Third `NOTE` alternative; `stands` accepts `living`; docstring.
4. **`cos_brief.py`.** Same `MOVED_RE` alternative; `moved_line` prints `head moved by the docs check fix commit since <sha>; reviews stand <url>`.
5. **Skills.** `open-pr` § Docs check step 4 and `ship-loop` phase 4 `note` sentence, per the spec.
6. **Tests** (AGENTS.md § Testing: table-driven, one per rule): `test_pr_diff_delta.py`, `test_review_gate.py`, `test_merge_pr.py`, `test_cos_brief_moved.py`, rows listed in the spec's § Tests.

## Verify

`python3 -I -m pytest -q agent-team/scripts` (use `uvx pytest -q agent-team/scripts` if pytest is missing) and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
