from control import DeviceUpdate, allow_write_now, is_noop_update, should_debounce, write_succeeded


def test_write_succeeded_per_endpoint():
    assert write_succeeded("mode", {"status": 0}) is True
    assert write_succeeded("mode", {"status": 1}) is False
    assert write_succeeded("boost_manual", {"status": 0}) is True
    assert write_succeeded("min_green", {"mgl": 60}) is True
    assert write_succeeded("min_green", {"status": 0}) is False


def test_should_debounce_within_gap():
    last = {12: 100.0}
    assert should_debounce(12, now=100.5, last_write=last, min_gap=2.0) is True
    assert should_debounce(12, now=103.0, last_write=last, min_gap=2.0) is False
    assert should_debounce(13, now=100.5, last_write=last, min_gap=2.0) is False


def test_allow_write_now_rate_cap():
    assert allow_write_now(now=100.0, last_any_ts=99.5, min_gap=1.0) is False
    assert allow_write_now(now=101.5, last_any_ts=100.0, min_gap=1.0) is True


def _update(nvalue, svalue):
    return DeviceUpdate(
        unit=12, type_name="Selector Switch", options={}, name="x", nvalue=nvalue, svalue=svalue
    )


def test_is_noop_update_true_when_unchanged():
    assert is_noop_update(20, "20", _update(20, "20")) is True


def test_is_noop_update_false_when_nvalue_differs():
    assert is_noop_update(10, "20", _update(20, "20")) is False


def test_is_noop_update_false_when_svalue_differs():
    assert is_noop_update(20, "10", _update(20, "20")) is False


def test_is_noop_update_compares_svalue_as_string():
    assert is_noop_update(0, 40, _update(0, "40")) is True
