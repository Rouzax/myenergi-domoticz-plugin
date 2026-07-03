"""FB24b regression against a real (sanitized) myenergi API sample.

jstatus_real.json / jday_real.json are a live zappi jstatus + a representative slice of
its jday, captured from the cloud with every serial replaced by a placeholder. Today's
sums are all > 0, so a fresh mid-day install (prev counter = 0, no persisted base) must
still seed a non-negative base and render non-negative energy counters."""

import json
from pathlib import Path

from config import Config
from model import parse_jday, parse_jstatus
from persistence import PluginState
from planner import AGG_UNITS, advance_baselines, aggregate_today_wh, plan

_FIX = Path(__file__).parent / "fixtures"
STATUS = parse_jstatus(json.loads((_FIX / "jstatus_real.json").read_text()))
TODAY_SUMS = parse_jday(json.loads((_FIX / "jday_real.json").read_text()))
CFG = Config("20000002", "k", "English", 20, 6, 25.0, 0)


def test_real_sample_has_positive_today_sums():
    # Guards the fixture: the whole point of FB24b is today > 0 while a fresh device is 0.
    agg = aggregate_today_wh(TODAY_SUMS)
    assert set(agg) == set(AGG_UNITS)
    assert all(v > 0 for v in agg.values())


def test_real_mid_day_install_seeds_non_negative_base():
    # Fresh install: empty base, every device counter at 0.
    state = PluginState(last_processed_date="2026-07-02", base_wh={}, unit_alloc={}, auto_names={})
    prev = {u: 0.0 for u in AGG_UNITS.values()}
    new = advance_baselines(state, [], TODAY_SUMS, prev, AGG_UNITS, 25.0, "2026-07-03")
    for unit in AGG_UNITS.values():
        assert new.base_wh[str(unit)] >= 0.0


def test_real_mid_day_install_renders_non_negative_energy():
    # End-to-end through plan(): seed the base, then render with the same today sums.
    state = PluginState(last_processed_date="2026-07-02", base_wh={}, unit_alloc={}, auto_names={})
    prev = {u: 0.0 for u in AGG_UNITS.values()}
    seeded = advance_baselines(state, [], TODAY_SUMS, prev, AGG_UNITS, 25.0, "2026-07-03")
    updates, _ = plan(STATUS, TODAY_SUMS, seeded, prev, CFG, max_step_wh=1e9)
    for u in updates:
        if u.type_name == "kWh":
            energy = float(u.svalue.split(";")[1])
            assert energy >= 0.0
