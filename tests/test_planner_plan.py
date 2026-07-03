import json
from pathlib import Path

from config import Config
from model import SystemStatus, parse_jstatus
from persistence import PluginState
from planner import (
    UNIT_CHARGE_STATUS,
    UNIT_EV,
    UNIT_FREQUENCY,
    UNIT_GRID_EXPORT,
    UNIT_GRID_IMPORT,
    UNIT_HOME,
    UNIT_MODE,
    UNIT_PLUG,
    UNIT_SOLAR,
    UNIT_VOLTAGE,
    plan,
)

_fixture_path = Path(__file__).parent / "fixtures" / "jstatus.json"
STATUS = parse_jstatus(json.loads(_fixture_path.read_text()))
CFG = Config("20000002", "k", "English", 20, 6, 25.0, 0)


def _by_unit(updates):
    return {u.unit: u for u in updates}


def test_solar_power_clamped_non_negative():
    # Inverter standby can read gen slightly negative at night; a PV tile never shows < 0.
    status = SystemStatus(devices=[], zappi={"gen": -4, "grd": 500, "div": 0}, zappi_lck=None)
    updates, _ = plan(status, None, PluginState(), {UNIT_SOLAR: 1000.0}, CFG, max_step_wh=1e6)
    u = _by_unit(updates)
    assert u[UNIT_SOLAR].svalue.startswith("0;")


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


def test_live_beat_clamps_negative_prior_counter():
    # A device that persisted a negative counter (e.g. base seeded negative before the
    # seed fix) must never render a negative kWh energy: the display clamps at 0.
    state = PluginState(base_wh={"1": 4000.0}, last_processed_date="2026-07-01")
    prev = {UNIT_SOLAR: -500.0}
    updates, _ = plan(STATUS, None, state, prev, CFG, max_step_wh=1e6)
    u = _by_unit(updates)
    assert u[UNIT_SOLAR].svalue == "1215;0.0000"


def test_live_beat_remaining_devices():
    # Covers the five units not asserted in test_live_beat_keeps_prior_energy:
    # Home (4), EV (5), Zappi Mode (7), Charge Status (8), Frequency (11).
    # Fixture: gen=1215, grd=734, div=0, che=2.34, frq=49.96, zmo=1, sta=4, pst="A"
    state = PluginState(base_wh={"1": 4000.0}, last_processed_date="2026-07-01")
    prev = {UNIT_SOLAR: 5000.0}
    updates, _ = plan(STATUS, None, state, prev, CFG, max_step_wh=1e6)
    u = _by_unit(updates)

    # Home: power = max(0, gen + grd - div) = 1215 + 734 - 0 = 1949; energy = prev 0.0
    assert u[UNIT_HOME].type_name == "kWh"
    assert u[UNIT_HOME].svalue == "1949;0.0000"

    # EV: power = div = 0; energy = prev 0.0
    assert u[UNIT_EV].type_name == "kWh"
    assert u[UNIT_EV].svalue == "0;0.0000"

    # Zappi Mode: zmo=1 -> "Fast"
    assert u[UNIT_MODE].type_name == "Text"
    assert u[UNIT_MODE].svalue == "Fast"

    # Charge Status: sta=4 but pst="A" (unplugged) -> "Idle" (not stale "Boosting")
    assert u[UNIT_CHARGE_STATUS].type_name == "Text"
    assert u[UNIT_CHARGE_STATUS].svalue == "Idle"

    # Frequency: jstatus frq is already Hz -> displayed as-is
    assert u[UNIT_FREQUENCY].type_name == "Custom"
    assert u[UNIT_FREQUENCY].svalue == "49.96"


def test_refresh_beat_sets_counter_from_base_plus_today():
    state = PluginState(base_wh={"1": 4000.0, "4": 0.0, "5": 0.0}, last_processed_date="2026-07-01")
    prev = {UNIT_SOLAR: 4000.0, UNIT_HOME: 0.0, UNIT_EV: 0.0}
    today = {"gep": 3_600_000}  # +1000 Wh solar today
    updates, _ = plan(STATUS, today, state, prev, CFG, max_step_wh=1e6)
    u = _by_unit(updates)
    assert u[UNIT_SOLAR].svalue == "1215;5000.0000"  # 4000 base + 1000 today


def test_plan_emits_grid_import_export():
    # fixture zappi: gen=1215, grd=734, div=0 -> import 734 W, export 0 W
    state = PluginState(base_wh={}, last_processed_date="2026-07-01")
    updates, _ = plan(STATUS, None, state, {}, CFG, max_step_wh=1e6)
    u = _by_unit(updates)
    assert u[UNIT_GRID_IMPORT].type_name == "kWh"
    assert u[UNIT_GRID_IMPORT].options == {"EnergyMeterMode": "0"}
    assert u[UNIT_GRID_IMPORT].svalue.startswith("734;")
    assert u[UNIT_GRID_EXPORT].svalue.startswith("0;")


def test_solar_total_has_return_switchtype():
    state = PluginState(base_wh={"1": 4000.0}, last_processed_date="2026-07-01")
    prev = {UNIT_SOLAR: 5000.0}
    updates, _ = plan(STATUS, None, state, prev, CFG, max_step_wh=1e6)
    u = _by_unit(updates)
    assert u[UNIT_SOLAR].switchtype == 4  # Return (generation)
    assert u[UNIT_HOME].switchtype == 0
    assert u[UNIT_EV].switchtype == 0
    assert u[UNIT_GRID_IMPORT].switchtype == 0  # Usage (from grid)
    assert u[UNIT_GRID_EXPORT].switchtype == 4  # Return (to grid)


def test_grid_export_when_exporting():
    # Negative grd means exporting: import power is 0, export power is +abs(grd).
    z = {"gen": 0, "grd": -500, "div": 0, "vol": 2300, "frq": 50.0, "sta": 1, "pst": "A", "zmo": 1}
    updates, _ = plan(
        SystemStatus(devices=[], zappi=z), None, PluginState(), {}, CFG, max_step_wh=1e6
    )
    u = _by_unit(updates)
    assert u[UNIT_GRID_IMPORT].svalue.startswith("0;")
    assert u[UNIT_GRID_EXPORT].svalue.startswith("500;")
