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
    assert decide_write(UNIT_MODE, "Set Level", 40, {}).mode == 4  # Stop


def test_mode_unknown_level_is_none():
    assert decide_write(UNIT_MODE, "Set Level", 99, {}) is None


def test_mode_off_command_is_none():
    # Domoticz sends command "Off" for the hidden level-0 slot; the real
    # options (level 10+) always send "Set Level", so "Off" never maps.
    assert decide_write(UNIT_MODE, "Off", 0, {}) is None


def test_boost_stop_all_cancels():
    intent = decide_write(UNIT_BOOST, "Set Level", 30, {})
    assert intent.kind == "boost_cancel"


def test_boost_manual_reads_kwh_selector_level():
    siblings = {UNIT_BOOST_KWH: 40}  # level 40 -> 20 kWh
    intent = decide_write(UNIT_BOOST, "Set Level", 10, siblings)
    assert intent.kind == "boost_manual" and intent.kwh == 20


def test_boost_manual_zero_kwh_selection_is_no_write():
    siblings = {UNIT_BOOST_KWH: 10}  # level 10 -> 0 kWh -> validate_kwh None
    assert decide_write(UNIT_BOOST, "Set Level", 10, siblings) is None


def test_boost_manual_rejects_missing_kwh_sibling():
    assert decide_write(UNIT_BOOST, "Set Level", 10, {}) is None


def test_boost_smart_reads_kwh_and_time_selector_levels():
    siblings = {UNIT_BOOST_KWH: 30, UNIT_BOOST_TIME: 80}  # 10 kWh, 07:00
    intent = decide_write(UNIT_BOOST, "Set Level", 20, siblings)
    assert intent.kind == "boost_smart" and intent.kwh == 10 and intent.hhmm == "0700"


def test_boost_smart_rejects_out_of_range_time_level():
    siblings = {UNIT_BOOST_KWH: 30, UNIT_BOOST_TIME: 9999}
    assert decide_write(UNIT_BOOST, "Set Level", 20, siblings) is None


def test_boost_smart_rejects_missing_kwh():
    assert decide_write(UNIT_BOOST, "Set Level", 20, {UNIT_BOOST_TIME: 80}) is None


def test_min_green_selector_level_maps_to_percent():
    intent = decide_write(UNIT_MIN_GREEN, "Set Level", 60, siblings={})  # level 60 -> 50%
    assert intent is not None and intent.kind == "min_green" and intent.pct == 50
    assert decide_write(UNIT_MIN_GREEN, "Set Level", 0, siblings={}) is None  # "Off"


def test_unknown_unit_is_none():
    assert decide_write(999, "Set Level", 0, {}) is None


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "abc", None])
def test_mode_bad_level_returns_none(bad):
    assert decide_write(UNIT_MODE, "Set Level", bad, {}) is None


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "abc", None])
def test_boost_bad_level_returns_none(bad):
    assert decide_write(UNIT_BOOST, "Set Level", bad, {UNIT_BOOST_KWH: "5"}) is None
