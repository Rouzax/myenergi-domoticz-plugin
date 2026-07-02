import pytest

from config import parse_config


@pytest.mark.parametrize(
    "value,expected",
    [
        ("true", True),
        ("True ", True),
        ("TRUE", True),
        ("false", False),
        ("", False),
        ("0", False),
        ("1", False),
        ("yes", False),
        ("garbage", False),
        (None, False),
    ],
)
def test_bool_parse_is_fail_closed(value, expected):
    params = {"Username": "10000001", "ApiKey": "k"}
    if value is not None:
        params["AllowControl"] = value
    cfg = parse_config(params)
    assert cfg.allow_control is expected


def test_control_gates_default_off_when_absent():
    cfg = parse_config({"Username": "10000001", "ApiKey": "k"})
    assert cfg.allow_control is False
    assert cfg.allow_lock is False


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


def test_parse_harvi_names_slots():
    cfg = parse_config({"Username": "1", "Harvi1Serial": "21460322", "Harvi1Name": "SolarEdge"})
    assert cfg.harvi_names == {"21460322": "SolarEdge"}


def test_api_key_whitespace_is_trimmed():
    cfg = parse_config({"Username": "10000001", "ApiKey": "  abc123  \n"})
    assert cfg.api_key == "abc123"


def test_api_key_internal_chars_preserved():
    cfg = parse_config({"Username": "10000001", "ApiKey": "ab c1-2_3"})
    assert cfg.api_key == "ab c1-2_3"
