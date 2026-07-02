from config import parse_config


def test_parse_defaults_and_clamps():
    cfg = parse_config(
        {
            "Username": "20000002",
            "ApiKey": "secret",
            "Language": "Nederlands",
            "LivePoll": "5",
            "CounterEvery": "10000",
            "MaxSystemKW": "30",
            "DebugLevel": "1",
        }
    )
    assert cfg.hub_serial == "20000002"
    assert cfg.api_key == "secret"
    assert cfg.language == "Nederlands"
    assert cfg.live_interval == 15  # clamped up from 5
    assert cfg.counter_multiple == 60  # clamped down from 10000
    assert cfg.max_system_kw == 30.0
    assert cfg.debug_level == 1


def test_parse_unknown_language_and_missing_fields():
    cfg = parse_config({"Username": "1", "Password": "k"})
    assert cfg.api_key == "k"  # falls back to legacy Password field
    assert cfg.language == "English"  # missing -> default
    assert cfg.live_interval == 20 and cfg.counter_multiple == 6


def test_parse_rejects_garbage_numbers():
    cfg = parse_config({"LivePoll": "abc", "CounterEvery": "", "MaxSystemKW": "x"})
    assert cfg.live_interval == 20 and cfg.counter_multiple == 6
    assert cfg.max_system_kw == 25.0
