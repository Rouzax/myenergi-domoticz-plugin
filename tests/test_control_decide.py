import pytest

from control import (
    UNIT_BOOST,
    UNIT_BOOST_KWH,
    UNIT_BOOST_TIME,
    UNIT_MIN_GREEN,
    UNIT_MODE,
    decide_write,
)


def test_mode_selector_maps_level_to_zmo():
    intent = decide_write(UNIT_MODE, "Set Level", 10, {})
    assert intent.kind == "mode"
    assert intent.mode == 1  # Fast
    assert decide_write(UNIT_MODE, "Set Level", 40, {}).mode == 4  # Stopped


def test_mode_unknown_level_is_none():
    assert decide_write(UNIT_MODE, "Set Level", 99, {}) is None


def test_mode_off_command_is_none():
    # Domoticz sends command "Off" for the hidden level-0 slot; the real
    # options (level 10+) always send "Set Level", so "Off" never maps.
    assert decide_write(UNIT_MODE, "Off", 0, {}) is None


def test_boost_stop_cancels():
    intent = decide_write(UNIT_BOOST, "Set Level", 10, {})
    assert intent.kind == "boost_cancel"


def test_boost_manual_reads_kwh_sibling():
    intent = decide_write(UNIT_BOOST, "Set Level", 20, {UNIT_BOOST_KWH: "5"})
    assert intent.kind == "boost_manual"
    assert intent.kwh == 5


def test_boost_manual_rejects_zero_kwh():
    assert decide_write(UNIT_BOOST, "Set Level", 20, {UNIT_BOOST_KWH: "0"}) is None


def test_boost_smart_reads_kwh_and_time():
    intent = decide_write(
        UNIT_BOOST, "Set Level", 30, {UNIT_BOOST_KWH: "5", UNIT_BOOST_TIME: "1400"}
    )
    assert intent.kind == "boost_smart"
    assert intent.kwh == 5
    assert intent.hhmm == "1400"


def test_boost_smart_rejects_bad_time():
    assert (
        decide_write(UNIT_BOOST, "Set Level", 30, {UNIT_BOOST_KWH: "5", UNIT_BOOST_TIME: "1275"})
        is None
    )


def test_min_green_setpoint_clamps():
    intent = decide_write(UNIT_MIN_GREEN, "Set Level", 60.0, {})
    assert intent.kind == "min_green"
    assert intent.pct == 60


def test_unknown_unit_is_none():
    assert decide_write(999, "Set Level", 0, {}) is None


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "abc", None])
def test_mode_bad_level_returns_none(bad):
    assert decide_write(UNIT_MODE, "Set Level", bad, {}) is None


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "abc", None])
def test_boost_bad_level_returns_none(bad):
    assert decide_write(UNIT_BOOST, "Set Level", bad, {UNIT_BOOST_KWH: "5"}) is None
