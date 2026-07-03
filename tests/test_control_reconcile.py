from config import Config
from control import (
    UNIT_BOOST,
    UNIT_BOOST_KWH,
    UNIT_BOOST_TIME,
    UNIT_LOCK_STATE,
    UNIT_MIN_GREEN,
    UNIT_MODE,
    boost_resting_level,
    plan_control_updates,
)
from model import SystemStatus


def _cfg(allow_control=False):
    return Config(
        "10000001",
        "k",
        "English",
        20,
        6,
        25.0,
        0,
        allow_control=allow_control,
    )


def _status(zappi=None, lck=None):
    return SystemStatus(devices=[], zappi=zappi or {}, zappi_lck=lck)


def test_no_updates_when_gates_off():
    status = _status(zappi={"zmo": 1}, lck=16)
    assert plan_control_updates(status, _cfg()) == []


def test_mode_reconciled_when_control_on():
    status = _status(zappi={"zmo": 3})  # Eco+
    updates = {u.unit: u for u in plan_control_updates(status, _cfg(allow_control=True))}
    assert updates[UNIT_MODE].nvalue == 30  # ZMO_TO_LEVEL[3]


def test_mode_and_boost_use_button_set_style_and_car_charger_icon():
    status = _status(zappi={"zmo": 1, "bsm": 0})
    updates = {u.unit: u for u in plan_control_updates(status, _cfg(allow_control=True))}
    assert updates[UNIT_MODE].options["SelectorStyle"] == "0"
    assert updates[UNIT_MODE].image == 30
    assert updates[UNIT_BOOST].options["SelectorStyle"] == "0"
    assert updates[UNIT_BOOST].image == 30


def test_mode_and_boost_hide_level_zero_slot():
    status = _status(zappi={"zmo": 1, "bsm": 0})
    updates = {u.unit: u for u in plan_control_updates(status, _cfg(allow_control=True))}
    assert updates[UNIT_MODE].options["LevelOffHidden"] == "true"
    assert updates[UNIT_MODE].options["LevelNames"] == "Off|Fast|Eco|Eco+|Stop"
    assert updates[UNIT_BOOST].options["LevelOffHidden"] == "true"
    assert updates[UNIT_BOOST].options["LevelNames"] == "Off|Manual|Smart|Stop All"


def test_mode_absent_field_not_reconciled():
    status = _status(zappi={})  # no zmo
    updates = {u.unit: u for u in plan_control_updates(status, _cfg(allow_control=True))}
    assert UNIT_MODE not in updates


def test_mode_bool_zmo_not_reconciled():
    status = _status(zappi={"zmo": True})  # bool is an int subclass; must not match
    updates = {u.unit: u for u in plan_control_updates(status, _cfg(allow_control=True))}
    assert UNIT_MODE not in updates


def test_min_green_bool_mgl_not_reconciled():
    status = _status(zappi={"zmo": 1, "mgl": True})  # bool is an int subclass; must not match
    updates = {u.unit: u for u in plan_control_updates(status, _cfg(allow_control=True))}
    assert UNIT_MIN_GREEN not in updates


def test_lock_state_emitted_when_control_on():
    status = _status(zappi={"zmo": 1}, lck=1)
    updates = {u.unit: u for u in plan_control_updates(status, _cfg(allow_control=True))}
    assert UNIT_LOCK_STATE in updates
    assert "Locked Now" in updates[UNIT_LOCK_STATE].svalue


def test_boost_resting_level_hidden_when_inactive():
    assert boost_resting_level({"bsm": 0}) == 0


def test_boost_resting_level_manual_when_active():
    assert boost_resting_level({"bsm": 1}) == 10


def test_boost_resting_level_smart_when_active():
    # Verified live: Smart boost -> bsm=1, bss=1; Manual -> bsm=1, bss=0.
    assert boost_resting_level({"bsm": 1, "bss": 1}) == 20
    assert boost_resting_level({"bsm": 1, "bss": 0}) == 10


def test_control_on_emits_boost_and_green_widgets():
    status = _status(zappi={"zmo": 1, "bsm": 0, "mgl": 40})
    units = {u.unit for u in plan_control_updates(status, _cfg(allow_control=True))}
    assert {UNIT_BOOST, UNIT_BOOST_KWH, UNIT_BOOST_TIME, UNIT_MIN_GREEN} <= units


def test_control_widgets_carry_car_charger_icon():
    status = _status(zappi={"zmo": 1, "bsm": 0, "mgl": 40}, lck=1)
    updates = {u.unit: u for u in plan_control_updates(status, _cfg(allow_control=True))}
    assert updates[UNIT_BOOST_KWH].image == 30
    assert updates[UNIT_BOOST_TIME].image == 30
    assert updates[UNIT_MIN_GREEN].image == 30
    assert updates[UNIT_LOCK_STATE].image == 0


def test_min_green_reconciled_value():
    status = _status(zappi={"zmo": 1, "mgl": 50})
    updates = {u.unit: u for u in plan_control_updates(status, _cfg(allow_control=True))}
    assert updates[UNIT_MIN_GREEN].svalue == "60"  # 50% -> level 60


def test_min_green_reconciles_to_nearest_menu_level():
    status = _status(zappi={"zmo": 3, "mgl": 50})
    ups = {u.unit: u for u in plan_control_updates(status, _cfg(allow_control=True))}
    mg = ups[UNIT_MIN_GREEN]
    assert mg.type_name == "Selector Switch" and mg.nvalue == 60  # 50% -> level 60


def test_boost_kwh_and_time_not_reemitted_once_created():
    status = _status(zappi={"zmo": 1, "bsm": 0, "mgl": 40})
    updates = {
        u.unit: u
        for u in plan_control_updates(
            status,
            _cfg(allow_control=True),
            existing_units={UNIT_BOOST_KWH, UNIT_BOOST_TIME},
        )
    }
    assert UNIT_BOOST_KWH not in updates
    assert UNIT_BOOST_TIME not in updates
    assert UNIT_BOOST in updates
    assert UNIT_MIN_GREEN in updates


def test_boost_inputs_created_as_selectors_input_only():
    status = _status(zappi={"zmo": 1})
    ups = {u.unit: u for u in plan_control_updates(status, _cfg(allow_control=True))}  # created
    assert ups[UNIT_BOOST_KWH].type_name == "Selector Switch" and ups[UNIT_BOOST_KWH].nvalue == 10
    assert ups[UNIT_BOOST_TIME].type_name == "Selector Switch" and ups[UNIT_BOOST_TIME].nvalue == 10
    # input-only: not re-emitted when they already exist
    ups2 = {
        u.unit
        for u in plan_control_updates(
            status, _cfg(allow_control=True), existing_units={UNIT_BOOST_KWH, UNIT_BOOST_TIME}
        )
    }
    assert UNIT_BOOST_KWH not in ups2 and UNIT_BOOST_TIME not in ups2
