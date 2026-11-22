import io
import json

import pytest

import cos_route
import project_config

ME = "me"


def tk(stage, **kw):
    return {"stage": stage, "parentThreadId": ME, **kw}


def route(tmp_path, capsys, monkeypatch, tickets, args, stdin=""):
    monkeypatch.setattr(project_config, "review_after_conflict", lambda: "off")
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    f = tmp_path / "state.json"
    f.write_text(json.dumps({"chiefThreadId": ME, "tickets": tickets}))
    code = cos_route.main(["ABC-1", *args, "--file", str(f)])
    return code, capsys.readouterr().out


MERGE = tk("awaiting-merge", pr=12, headSha="abcdef1234567890")
SPEC_USER = 'CHIEF OF STAFF: the user approved the spec: "go ahead". Continue to the build stage.\nApproval in thread: T1'
FULL = {"ABC-8": tk("build"), "ABC-9": tk("build")}


@pytest.mark.parametrize(
    "ticket, args, stdin, route_line, relay",
    [
        # the user's words, quoted as given; a trailing newline is dropped, inner ones stay
        (tk("awaiting-build"), ["approve-spec", "--thread", "T1"], "go ahead\n", "route: send build", SPEC_USER),
        (MERGE, ["approve-merge"], "approve 1", "route: send merge", 'CHIEF OF STAFF: the user approved the merge of PR #12 at head abcdef1: "approve 1".'),
        (tk("awaiting-review"), ["changes"], "fix the\nname", "route: send build", 'CHIEF OF STAFF: the user asked for changes: "fix the\nname".'),
        (tk("blocked", resumeStage="spec"), ["answer"], "use B", "route: send spec", 'CHIEF OF STAFF: the user says: "use B". Continue the spec stage.'),
        # no words needed
        (tk("blocked", resumeStage="build"), ["resume"], "", "route: send build", "CHIEF OF STAFF: continue the build stage from where the branch is."),
        (tk("blocked", resumeStage="merge"), ["rate-limit"], "", "route: send merge", "CHIEF OF STAFF: continue the merge stage from where the branch is."),
        # auto variants read no stdin; No Hands has no Risk part on a spec; a missing rating is `unrated`
        (tk("awaiting-build"), ["approve-spec", "--auto", "Low", "--risk", "Low (docs only)"], "", "route: send build",
         "CHIEF OF STAFF: auto-approved the spec under `Low` (Risk: Low (docs only)). Continue to the build stage."),
        (tk("awaiting-build"), ["approve-spec", "--auto", "No Hands"], "", "route: send build", "CHIEF OF STAFF: auto-approved the spec under No Hands. Continue to the build stage."),
        (tk("awaiting-build"), ["approve-spec", "--auto", "Medium"], "", "route: send build", "CHIEF OF STAFF: auto-approved the spec under `Medium` (Risk: unrated). Continue to the build stage."),
        (MERGE, ["approve-merge", "--auto", "No Hands", "--risk", "High (auth)"], "", "route: send merge",
         "CHIEF OF STAFF: auto-approved the merge of PR #12 at head abcdef1 under `No Hands` (Risk: High (auth))."),
    ],
)
def test_relay_text(tmp_path, capsys, monkeypatch, ticket, args, stdin, route_line, relay):
    code, out = route(tmp_path, capsys, monkeypatch, {"ABC-1": ticket}, [*args, "--relay"], stdin)
    lines = out.split("\nrelay:\n")
    assert code == 0 and lines[0].splitlines()[-1] == route_line and lines[1] == relay + "\n"
    # without --relay the same call prints what it printed before: the lines before the relay
    plain_args = [a for i, a in enumerate(args) if a not in ("--auto", "--risk") and args[i - 1] not in ("--auto", "--risk")]
    code, plain = route(tmp_path, capsys, monkeypatch, {"ABC-1": ticket}, plain_args)
    assert code == 0 and plain == lines[0] + "\n"


@pytest.mark.parametrize(
    "others, thread_arg, want_route",
    [
        (FULL, ["--thread", "T1"], "route: queue build"),
        ({}, ["--thread", "T1"], "route: send build"),
    ],
)
def test_a_queued_relay_has_the_same_text(tmp_path, capsys, monkeypatch, others, thread_arg, want_route):
    _, out = route(tmp_path, capsys, monkeypatch, {"ABC-1": tk("awaiting-build"), **others}, ["approve-spec", "--relay", *thread_arg], "go ahead")
    assert want_route in out and out.endswith("relay:\n" + SPEC_USER + "\n")


def test_a_continuation_carries_the_relay(tmp_path, capsys, monkeypatch):
    code, out = route(tmp_path, capsys, monkeypatch, {"ABC-1": tk("awaiting-review", parentThreadId="old")}, ["changes", "--relay"], "x")
    assert code == 0 and "route: continuation build" in out and out.endswith('relay:\nCHIEF OF STAFF: the user asked for changes: "x".\n')


@pytest.mark.parametrize(
    "ticket, args, stdin, code, msg",
    [
        (tk("awaiting-build"), ["approve-spec", "--relay"], "ok", 2, "route: cannot give --thread"),
        (tk("awaiting-build"), ["approve-spec", "--relay", "--thread", "T1"], " \n", 2, "route: cannot read the user's words"),
        (tk("awaiting-review"), ["changes", "--relay"], "", 2, "route: cannot read the user's words"),
        (tk("awaiting-merge"), ["approve-merge", "--relay"], "ok", 2, "route: cannot read pr and headSha"),
        (MERGE, ["changes", "--relay", "--auto", "Low"], "", 2, "route: cannot give --auto only to approve-spec or approve-merge, not changes"),
        (MERGE, ["approve-merge", "--auto", "Low"], "", 2, "route: cannot use --auto and --risk with --relay"),
        (MERGE, ["approve-merge", "--relay", "--risk", "Low (x)"], "ok", 2, "route: cannot use --risk with --auto"),
        # route: no sends nothing and prints no relay; callers without a relay text here print none
        (tk("awaiting-build"), ["approve-merge", "--relay"], "ok", 1, "route: no approve-merge does not apply from awaiting-build"),
    ],
)
def test_relay_errors(tmp_path, capsys, monkeypatch, ticket, args, stdin, code, msg):
    got, out = route(tmp_path, capsys, monkeypatch, {"ABC-1": ticket}, args, stdin)
    assert got == code and out.strip().startswith(msg)


def test_a_caller_with_no_relay_text_prints_none(tmp_path, capsys, monkeypatch):
    code, out = route(tmp_path, capsys, monkeypatch, {"ABC-1": tk("awaiting-merge")}, ["head-moved", "--relay"], "")
    assert code == 0 and "relay:" not in out
