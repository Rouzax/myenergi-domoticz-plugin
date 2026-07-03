from control import UNIT_BOOST_KWH, UNIT_BOOST_TIME, UNIT_MODE, persist_input_setpoint


def test_boost_kwh_persist_stores_selector_level():
    upd = persist_input_setpoint(UNIT_BOOST_KWH, 40, "English")  # level 40 -> 20 kWh
    assert upd.type_name == "Selector Switch" and upd.nvalue == 40 and upd.svalue == "40"
    assert upd.switchtype == 18
    assert persist_input_setpoint(UNIT_BOOST_KWH, 999, "English") is None  # out of range


def test_boost_time_persist_stores_selector_level():
    upd = persist_input_setpoint(UNIT_BOOST_TIME, 80, "English")  # level 80 -> 07:00
    assert upd.type_name == "Selector Switch" and upd.nvalue == 80


def test_persist_setpoint_rejects_non_finite_level():
    assert persist_input_setpoint(UNIT_BOOST_KWH, float("nan"), "English") is None
    assert persist_input_setpoint(UNIT_BOOST_TIME, float("inf"), "English") is None
    assert persist_input_setpoint(UNIT_BOOST_KWH, None, "English") is None


def test_persist_setpoint_unknown_unit_returns_none():
    assert persist_input_setpoint(UNIT_MODE, 20, "English") is None
