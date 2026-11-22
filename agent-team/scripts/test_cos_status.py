"""`cos_status.py`: the status tables from state (chief-of-staff/status.md § Status layout)."""

import json
import sys
import types

import pytest

import cos_status

ENV = "env-1"


def t(stage, title, status, child=None, **kw):
    return {"stage": stage, "title": title, "status": status, "childThreadId": child, **kw}


STATE = {
    "tickets": {
        "ABC-240": t("spec", "Example feature", "spec since 2026-11-01 2:05 pm UTC: child started; no BUILD READY yet.", "c240"),
        "ABC-199": t("build", "Background jobs", "build since 2026-11-01 3:00 pm UTC: PR #181, code review pass 2. Risk: Medium (changes slot fill, 4 Builds bullets).", "c199"),
        "ABC-197": t("awaiting-merge", "CSV export", "awaiting-merge since 2026-11-01 4:00 pm UTC: PR #180, reviews PASS. Risk: High (touches auth).", "c197"),
        "ABC-154": t("build", "Retry button", "build since 2026-11-01 1:00 pm UTC: restarted: stalled after code review PASS. Risk: Low (docs only, 2 Builds bullets).", "c154"),
        "ABC-238": t("build-queued", "Export filters", "build-queued since 2026-11-01 5:00 pm UTC: spec approved, waiting for a build slot. Risk: Low (prose only, 3 Builds bullets).", "c238", queuedAt="2026-11-01T17:00:00Z"),
    },
}
LINK = lambda child: f"[ABC-{child[1:]}](t3-thread://v2/{ENV}/{child})"  # noqa: E731

EXPECTED = f"""**Awaiting merge approval (1)**

| Ticket | Risk | Next |
|---|---|---|
| **ABC-197** CSV export<br>{LINK('c197')} | High (touches auth) | awaiting-merge since 2026-11-01 4:00 pm UTC: PR #180, reviews PASS. |

**Speccing (1)**

| Ticket | Risk | Next |
|---|---|---|
| **ABC-240** Example feature<br>{LINK('c240')} | not rated yet | spec since 2026-11-01 2:05 pm UTC: child started; no BUILD READY yet. |

**Building (2)**

| Ticket | Risk | Next |
|---|---|---|
| **ABC-199** Background jobs<br>{LINK('c199')} | Medium (changes slot fill, 4 Builds bullets) | build since 2026-11-01 3:00 pm UTC: PR #181, code review pass 2. |
| **ABC-154** Retry button<br>{LINK('c154')} | Low (docs only, 2 Builds bullets) | build since 2026-11-01 1:00 pm UTC: restarted: stalled after code review PASS. |

**Queued to build (1)**

| Ticket | Risk | Next |
|---|---|---|
| **ABC-238** Export filters<br>{LINK('c238')} | Low (prose only, 3 Builds bullets) | build-queued since 2026-11-01 5:00 pm UTC: spec approved, waiting for a build slot. |"""


@pytest.fixture
def world(tmp_path, monkeypatch, capsys):
    (tmp_path / "environment-id").write_text(ENV)
    monkeypatch.setattr(cos_status, "cost_of", lambda tid: "")

    def go(state, *argv, code=0):
        f = tmp_path / "state.json"
        f.write_text(state if isinstance(state, str) else json.dumps(state))
        got = cos_status.main(["--file", str(f), "--db", str(tmp_path / "statev2.sqlite"), *argv])
        assert got == code
        return capsys.readouterr().out

    return go


def test_groups_in_order_with_counts_and_cells_from_state(world):
    assert world(STATE).rstrip("\n") == EXPECTED


@pytest.mark.parametrize(
    "tickets, order",
    [
        # queued groups: queuedAt order (the `queue <lane>:` order), a ticket with no time first; the other groups keep state order
        ({"ABC-3": t("merge-queued", "C", "s", queuedAt="2026-11-01T03:00:00Z"), "ABC-1": t("merge-queued", "A", "s", queuedAt="2026-11-01T01:00:00Z"), "ABC-2": t("merge-queued", "B", "s")}, ["ABC-2", "ABC-1", "ABC-3"]),
        ({"ABC-3": t("build", "C", "s"), "ABC-1": t("build", "A", "s")}, ["ABC-3", "ABC-1"]),
    ],
)
def test_row_order(world, tickets, order):
    out = world({"tickets": tickets})
    assert sorted(order, key=out.index) == order


@pytest.mark.parametrize(
    "stage, header",
    [(s, h) for h, s in cos_status.GROUPS],
)
def test_each_stage_has_its_group(world, stage, header):
    out = world({"tickets": {"ABC-1": t(stage, "A", "s")}})
    assert out.splitlines()[0] == f"**{header} (1)**"
    assert len(out.splitlines()) == 5


@pytest.mark.parametrize(
    "status, risk, detail",
    [
        ("awaiting-build since x: spec ready. Risk: High (touches auth).", "High (touches auth)", "awaiting-build since x: spec ready."),
        ("build since x: building.", "not rated yet", "build since x: building."),
        # only a tail at the very end counts: a quoted Risk: in the middle does not, and neither does an unknown level
        ('blocked since x: "Risk: High (x)" asked.', "not rated yet", 'blocked since x: "Risk: High (x)" asked.'),
        ("build since x: y. Risk: Huge (z).", "not rated yet", "build since x: y. Risk: Huge (z)."),
        # a reason with its own parentheses and dots
        ("build since x: y. Risk: Medium (changes scripts/ (the tick), 2 Builds).", "Medium (changes scripts/ (the tick), 2 Builds)", "build since x: y."),
        (None, "not rated yet", ""),
    ],
)
def test_risk_cell_and_detail_from_the_status_line(status, risk, detail):
    assert cos_status.split_risk(status) == (detail, risk)


def test_cells_escape_pipes_and_line_breaks_and_leave_titles_to_display_title(world):
    state = {"tickets": {
        "ABC-1": t("build", "Fix a | b\nnow", "build since x: a | b\nsecond line"),
        "ABC-2": t("build", "MERGE READY: do it", "s"),
        "ABC-3": t("build", None, "s"),
        "ABC-4": t("build", "One two three four five six seven eight", "s"),
    }}
    rows = world(state).splitlines()[4:8]
    assert rows[0].startswith("| **ABC-1** Fix a \\| b now | not rated yet | build since x: a \\| b second line |")
    assert rows[1].startswith("| **ABC-2** | ") and rows[2].startswith("| **ABC-3** | ")  # a marker word or no title: the ID alone
    assert rows[3].startswith("| **ABC-4** One two three four five six | ")


@pytest.mark.parametrize("child, link", [(None, False), ("", False), ("bad id\n", False), ("c1", True)])
def test_the_link_needs_a_child_thread(world, child, link):
    out = world({"tickets": {"ABC-1": t("build", "A", "s", child)}})
    assert ("<br>[ABC-1](t3-thread://v2/env-1/c1)" in out) == link and ("<br>" in out) == link


def test_no_environment_id_means_no_link(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cos_status, "cost_of", lambda tid: "")
    f = tmp_path / "s.json"
    f.write_text(json.dumps({"tickets": {"ABC-1": t("build", "A", "s", "c1")}}))
    assert cos_status.main(["--file", str(f), "--db", str(tmp_path / "none" / "statev2.sqlite")]) == 0
    out = capsys.readouterr().out
    assert "| **ABC-1** A | not rated yet | s |" in out and "<br>" not in out


@pytest.mark.parametrize(
    "line, want",
    [
        ("cost $14.20 API-equivalent (0.12% of the subscription), 3.1M tokens, spec $2.10 / build $11.66 / merge $0.44, 3 child runs, wall 1h 02m", " $14.20 so far"),
        ("cost unknown (no price for gpt-9; $3.00 priced), 1.0M tokens", " cost unknown"),
        (None, ""),  # no session ran the ticket: adds nothing
        (RuntimeError("boom"), " cost unknown"),
        (SystemExit(2), " cost unknown"),
    ],
)
def test_cost_per_row_from_agent_usage(monkeypatch, line, want):
    def ticket_line(*a):
        if isinstance(line, BaseException):
            raise line
        return line

    monkeypatch.setitem(sys.modules, "agent_usage", types.SimpleNamespace(ticket_line=ticket_line))
    assert cos_status.cost_of("ABC-1") == want


def test_the_detail_cell_ends_with_the_cost(tmp_path, monkeypatch, capsys):
    (tmp_path / "environment-id").write_text(ENV)
    monkeypatch.setattr(cos_status, "cost_of", lambda tid: " $14.20 so far")
    f = tmp_path / "s.json"
    f.write_text(json.dumps({"tickets": {"ABC-1": t("build", "A", "build since x: PR #7. Risk: Low (docs).")}}))
    cos_status.main(["--file", str(f), "--db", str(tmp_path / "x.sqlite")])
    assert "| Low (docs) | build since x: PR #7. $14.20 so far |" in capsys.readouterr().out


def test_merged_and_untracked_lines_from_the_sweep_line(world):
    sweep = "sweep: read in full: ABC-1 (ready); merged: ABC-2 #14, ABC-3 #15; untracked: ABC-5 #12, ABC-6; review: ABC-7 approved"
    out = world({"tickets": {}}, "--sweep", sweep).splitlines()
    assert out == ["Merged: ABC-2 (#14); ABC-3 (#15)", "Not in my state: ABC-5 (#12); ABC-6"]
    assert world({"tickets": {}}, "--sweep", "sweep: read in full: none; merged: none") == ""
    # anything not an `<ID>` or `<ID> #N` is dropped, and an empty state prints no tables
    assert world({"tickets": {}}, "--sweep", "sweep: read in full: none; merged: x\nhead #1, ABC-8 #x, ABC-9 #4") == "Merged: ABC-9 (#4)\n"


def test_ticket_prints_one_group_and_row_and_merged_tickets(world):
    out = world(STATE, "--ticket", "ABC-154").splitlines()
    assert out[0] == "**Building (1)**" and len(out) == 5 and "ABC-154" in out[4]
    assert world({"tickets": {}, "merged": {"ABC-9": {"pr": 12, "at": "2026-11-02T09:30:00Z"}}}, "--ticket", "ABC-9") == "ABC-9, merged (#12)\n"
    assert world({"tickets": {}}, "--ticket", "ABC-9", code=1) == "cos_status: ABC-9 is not in state\n"
    assert world({"tickets": {}}, "--ticket", "nope", code=2) == "cos_status: --ticket needs an id like <PREFIX>-N\n"


@pytest.mark.parametrize("state, out", [({"tickets": {}}, ""), ({"tickets": {"ABC-1": "junk", "ABC-2": {"stage": "weird"}}}, ""), ("not json", "cos_status: unreadable state file\n")])
def test_empty_and_unreadable_state(world, state, out):
    assert world(state, code=2 if "json" in str(state) else 0) == out
