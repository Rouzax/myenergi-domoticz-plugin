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


def test_mode_text_hidden_roundtrips():
    st = PluginState(
        last_processed_date="2026-07-01",
        unit_alloc={},
        base_wh={},
        auto_names={},
        mode_text_hidden=True,
    )
    assert loads(dumps(st)).mode_text_hidden is True


def test_mode_text_hidden_defaults_false_on_old_state():
    old = loads("")  # empty -> fresh default state
    assert old.mode_text_hidden is False
