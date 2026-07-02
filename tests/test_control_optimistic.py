from control import UNIT_BOOST, UNIT_MIN_GREEN, UNIT_MODE, optimistic_update


def test_mode_level_optimistic_update():
    update = optimistic_update(UNIT_MODE, "Set Level", 20, "English")
    assert update.unit == 12
    assert update.nvalue == 20
    assert update.svalue == "20"
    assert update.type_name == "Selector Switch"
    assert update.image == 30


def test_boost_level_optimistic_update_carries_car_charger_icon():
    update = optimistic_update(UNIT_BOOST, "Set Level", 10, "English")
    assert update.unit == 13
    assert update.image == 30


def test_min_green_optimistic_update():
    update = optimistic_update(UNIT_MIN_GREEN, "Set Level", 60, "English")
    assert update.unit == 16
    assert update.svalue == "60"
    assert update.type_name == "Setpoint"


def test_mode_bad_level_returns_none():
    assert optimistic_update(UNIT_MODE, "Set Level", float("nan"), "English") is None
    assert optimistic_update(UNIT_MODE, "Set Level", 99, "English") is None


def test_unknown_unit_returns_none():
    assert optimistic_update(999, "Set Level", 0, "English") is None
