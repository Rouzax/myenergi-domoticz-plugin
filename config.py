"""Pure parsing of the Domoticz Parameters dict into a typed Config."""

from dataclasses import dataclass, field

from model import harvi_names_from_slots
from translations import LANGUAGES


@dataclass
class Config:
    hub_serial: str
    api_key: str
    language: str
    live_interval: int
    counter_multiple: int
    max_system_kw: float
    debug_level: int
    harvi_names: "dict[str, str]" = field(default_factory=dict)


def _int(params, key, default, lo, hi):
    try:
        val = int(str(params.get(key, "")).strip())
    except (ValueError, TypeError):
        return default
    return max(lo, min(hi, val))


def _float(params, key, default):
    try:
        return float(str(params.get(key, "")).strip())
    except (ValueError, TypeError):
        return default


def parse_config(params: dict) -> Config:
    language = str(params.get("Language", "English"))
    if language not in LANGUAGES:
        language = "English"
    api_key = str(params.get("ApiKey") or params.get("Password") or "").strip()
    return Config(
        hub_serial=str(params.get("Username", "")).strip(),
        api_key=api_key,
        language=language,
        live_interval=_int(params, "LivePoll", 20, 15, 300),
        counter_multiple=_int(params, "CounterEvery", 6, 1, 60),
        max_system_kw=_float(params, "MaxSystemKW", 25.0),
        debug_level=_int(params, "DebugLevel", 0, 0, 2),
        harvi_names=harvi_names_from_slots(params),
    )
