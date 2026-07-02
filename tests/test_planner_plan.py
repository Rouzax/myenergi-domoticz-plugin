import json
from pathlib import Path

from config import Config
from model import parse_jstatus
from persistence import PluginState
from planner import UNIT_EV, UNIT_PLUG, UNIT_SOLAR, UNIT_VOLTAGE, plan

_fixture_path = Path(__file__).parent / "fixtures" / "jstatus.json"
STATUS = parse_jstatus(json.loads(_fixture_path.read_text()))
CFG = Config("20000002", "k", "English", 20, 120, 25.0, 0)


def _by_unit(updates):
    return {u.unit: u for u in updates}


def test_live_beat_keeps_prior_energy():
    state = PluginState(base_wh={"1": 4000.0}, last_processed_date="2026-07-01")
    prev = {UNIT_SOLAR: 5000.0}
    updates, new_state = plan(STATUS, None, state, prev, CFG, max_step_wh=1e6)
    u = _by_unit(updates)
    # Solar power = gen (1215); energy kept at prev 5000.0
    assert u[UNIT_SOLAR].type_name == "kWh"
    assert u[UNIT_SOLAR].options == {"EnergyMeterMode": "0"}
    assert u[UNIT_SOLAR].svalue == "1215;5000.0000"
    assert new_state is state  # unchanged on a live beat
    # Plug status text localized (fixture pst = "A")
    assert u[UNIT_PLUG].type_name == "Text"
    assert u[UNIT_PLUG].svalue == "Disconnected"
    # Voltage 2343 -> 234.3
    assert u[UNIT_VOLTAGE].svalue == "234.3"


def test_refresh_beat_sets_counter_from_base_plus_today():
    state = PluginState(base_wh={"1": 4000.0, "2": 0.0, "3": 0.0}, last_processed_date="2026-07-01")
    prev = {UNIT_SOLAR: 4000.0, 2: 0.0, UNIT_EV: 0.0}
    today = {"gep": 3_600_000}  # +1000 Wh solar today
    updates, _ = plan(STATUS, today, state, prev, CFG, max_step_wh=1e6)
    u = _by_unit(updates)
    assert u[UNIT_SOLAR].svalue == "1215;5000.0000"  # 4000 base + 1000 today
