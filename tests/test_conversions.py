from model import deci_volts_to_v, joules_to_kwh, joules_to_wh


def test_joule_conversions():
    assert joules_to_wh(3_600_000) == 1000.0
    assert joules_to_kwh(3_600_000) == 1.0
    assert joules_to_kwh(0) == 0.0


def test_scalar_conversions():
    assert deci_volts_to_v(2343) == 234.3
