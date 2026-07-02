from control import UNIT_BOOST_KWH, UNIT_BOOST_TIME, UNIT_MODE, persist_input_setpoint


def test_persist_boost_kwh_setpoint():
    update = persist_input_setpoint(UNIT_BOOST_KWH, 5, "English")
    assert update.unit == UNIT_BOOST_KWH
    assert update.svalue == "5"
    assert update.type_name == "Setpoint"


def test_persist_boost_time_setpoint():
    update = persist_input_setpoint(UNIT_BOOST_TIME, 1400, "English")
    assert update.unit == UNIT_BOOST_TIME
    assert update.svalue == "1400"
    assert update.type_name == "Setpoint"


def test_persist_setpoint_rejects_non_finite_level():
    assert persist_input_setpoint(UNIT_BOOST_KWH, float("nan"), "English") is None
    assert persist_input_setpoint(UNIT_BOOST_TIME, float("inf"), "English") is None
    assert persist_input_setpoint(UNIT_BOOST_KWH, None, "English") is None


def test_persist_setpoint_clamps_over_range():
    assert persist_input_setpoint(UNIT_BOOST_KWH, 10_000, "English").svalue == "100"
    assert persist_input_setpoint(UNIT_BOOST_KWH, -5, "English").svalue == "0"
    assert persist_input_setpoint(UNIT_BOOST_TIME, 9_999, "English").svalue == "2359"
    assert persist_input_setpoint(UNIT_BOOST_TIME, -5, "English").svalue == "0"


def test_persist_setpoint_unknown_unit_returns_none():
    assert persist_input_setpoint(UNIT_MODE, 20, "English") is None
