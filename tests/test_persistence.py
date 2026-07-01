import json

from persistence import STATE_VERSION, PluginState, dumps, loads


def test_roundtrip():
    state = PluginState(
        last_processed_date="2026-06-30",
        unit_alloc={"10000001": 1},
        base_wh={"1": 4800.0},
        auto_names={"1": "myenergi - Solar Total"},
    )
    restored = loads(dumps(state))
    assert restored == state


def test_dumps_includes_version():
    state = PluginState(None, {}, {}, {})
    assert json.loads(dumps(state))["version"] == STATE_VERSION


def test_loads_empty_returns_blank_state():
    blank = loads("")
    assert blank == PluginState(None, {}, {}, {})


def test_loads_tolerates_missing_keys():
    restored = loads(json.dumps({"version": 1, "base_wh": {"1": 10.0}}))
    assert restored.base_wh == {"1": 10.0}
    assert restored.unit_alloc == {}
