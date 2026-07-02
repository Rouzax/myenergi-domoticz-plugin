from control import (
    ZMO_TO_LEVEL,
    clamp_min_green,
    decode_lck,
    validate_hhmm,
    validate_kwh,
)


def test_validate_kwh_clamps_and_int_coerces():
    assert validate_kwh(5.0) == 5
    assert validate_kwh(5.7) == 6
    assert validate_kwh(-5) is None
    assert validate_kwh(0) is None
    assert validate_kwh(10_000) == 100
    assert validate_kwh(float("nan")) is None
    assert validate_kwh(float("inf")) is None


def test_validate_hhmm_rejects_bad_times_and_formats():
    assert validate_hhmm(1400) == "1400"
    assert validate_hhmm(730) == "0730"
    assert validate_hhmm(0) == "0000"
    assert validate_hhmm(1275) is None  # MM >= 60
    assert validate_hhmm(2400) is None  # HH >= 24
    assert validate_hhmm(-1) is None
    assert validate_hhmm(float("nan")) is None


def test_clamp_min_green():
    assert clamp_min_green(60) == 60
    assert clamp_min_green(-1) == 0
    assert clamp_min_green(150) == 100
    assert clamp_min_green(float("inf")) is None


def test_decode_lck_reports_bits():
    text = decode_lck(1)
    assert "1" in text
    assert "Locked Now" in text


def test_zmo_level_maps_are_inverse():
    assert ZMO_TO_LEVEL[1] == 0
    assert ZMO_TO_LEVEL[4] == 30
