"""prices.json against the published rates, and agent_usage.costs against the cases the mod's tests share (price_fixture.json)."""

import json
from pathlib import Path

import pytest

import agent_usage

FIXTURE = json.loads(Path(__file__).with_name("price_fixture.json").read_text())
KINDS = ("input", "output", "read", "write_5m", "write_1h")


def dollars(model, t):
    cc = {"ephemeral_5m_input_tokens": t["write_5m"], "ephemeral_1h_input_tokens": t["write_1h"]}
    usage = {"input_tokens": t["input"], "output_tokens": t["output"], "cache_read_input_tokens": t["read"], "cache_creation": cc}
    return sum(agent_usage.costs(model, usage).values())


@pytest.mark.parametrize("model, rates", FIXTURE["published"].items())
def test_prices_json_matches_the_published_rate_of_every_kind(model, rates):
    # A different count per kind, so a change to any one rate changes the total.
    t = dict(zip(KINDS, (1_000_000, 2_000_000, 3_000_000, 5_000_000, 7_000_000)))
    assert dollars(model, t) == pytest.approx(sum(t[k] * rates[k] for k in KINDS) / 1e6, abs=1e-9)


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda c: c["model"])
def test_costs_gives_the_dollars_the_mod_is_checked_against(case):
    assert dollars(case["model"], case["tokens"]) == pytest.approx(case["dollars"], abs=1e-9)
