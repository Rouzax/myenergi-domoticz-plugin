"""Durable plugin state <-> JSON for Domoticz.Configuration()."""

import json
from dataclasses import dataclass, field

STATE_VERSION = 1


@dataclass
class PluginState:
    last_processed_date: "str | None" = None
    unit_alloc: "dict[str, int]" = field(default_factory=dict)
    base_wh: "dict[str, float]" = field(default_factory=dict)
    auto_names: "dict[str, str]" = field(default_factory=dict)


def migrate(raw: dict) -> dict:
    """Transform older payloads to current shape."""
    raw.setdefault("version", STATE_VERSION)
    return raw


def dumps(state: PluginState) -> str:
    """Serialize PluginState to compact JSON with version."""
    return json.dumps(
        {
            "version": STATE_VERSION,
            "last_processed_date": state.last_processed_date,
            "unit_alloc": state.unit_alloc,
            "base_wh": state.base_wh,
            "auto_names": state.auto_names,
        },
        separators=(",", ":"),
    )


def loads(text: str) -> PluginState:
    """Deserialize JSON to PluginState; tolerates empty/missing keys via migrate."""
    if not text:
        return PluginState()
    raw = migrate(json.loads(text))
    return PluginState(
        last_processed_date=raw.get("last_processed_date"),
        unit_alloc=raw.get("unit_alloc", {}),
        base_wh=raw.get("base_wh", {}),
        auto_names=raw.get("auto_names", {}),
    )
