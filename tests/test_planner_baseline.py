from persistence import PluginState
from planner import advance_baselines

AGG = {"solar": 1, "home": 2, "ev": 3}


def test_seed_from_prev_counter_when_base_missing():
    state = PluginState(last_processed_date="2026-06-30", base_wh={}, unit_alloc={}, auto_names={})
    today = {"gep": 3_600_000}  # solar today = 1000 Wh
    prev = {1: 5000.0, 2: 0.0, 3: 0.0}  # solar device already reads 5000 Wh cumulative
    new = advance_baselines(state, [], today, prev, AGG, 25.0, "2026-07-01")
    # base seeded so that base + today == prev: 5000 - 1000 = 4000
    assert new.base_wh["1"] == 4000.0
    # last_processed = the day BEFORE today (today is not folded into base)
    assert new.last_processed_date == "2026-06-30"


def test_backfill_folds_missing_days_once():
    state = PluginState(
        last_processed_date="2026-06-28",
        base_wh={"1": 100.0},
        unit_alloc={},
        auto_names={},
    )
    # two missing whole days, each 1000 Wh of solar
    days = [{"gep": 3_600_000}, {"gep": 3_600_000}]
    new = advance_baselines(
        state, days, {"gep": 0}, {1: 0.0, 2: 0.0, 3: 0.0}, AGG, 25.0, "2026-07-01"
    )
    assert new.base_wh["1"] == 100.0 + 2000.0  # folded both days once


def test_midnight_rollover_folds_yesterday_no_freeze():
    # End of day D the state says last_processed = D-1 and base holds through D-1.
    # On D+1 the shell folds [D] via backfill; base must grow by D's full total so the
    # counter keeps climbing instead of freezing.
    state = PluginState(
        last_processed_date="2026-06-30",
        base_wh={"1": 1000.0, "2": 0.0, "3": 0.0},
        unit_alloc={},
        auto_names={},
    )
    yesterday_full = {"gep": 3_600_000}  # day 2026-07-01 total = 1000 Wh
    new = advance_baselines(
        state, [yesterday_full], {"gep": 0}, {1: 0.0, 2: 0.0, 3: 0.0}, AGG, 25.0, "2026-07-02"
    )
    assert new.base_wh["1"] == 2000.0  # yesterday folded in, base grew
    assert new.last_processed_date == "2026-07-01"
