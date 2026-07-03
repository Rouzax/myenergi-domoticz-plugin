"""Durable plugin state <-> JSON for Domoticz.Configuration()."""

import json
from dataclasses import dataclass, field

STATE_VERSION = 3


@dataclass
class PluginState:
    """Persisted plugin state serialized to/from Domoticz.Configuration().

    Key domains:
    - unit_alloc: device SERIAL string -> Domoticz Unit number (int). Assigns a
      stable Unit per dynamically-discovered device (e.g. one per harvi), so a
      device keeps the same Unit across restarts.
    - base_wh: Domoticz Unit number (as string) -> cumulative Wh baseline
      (float). Stores the folded energy total so live session values are added
      on top without double-counting days already processed.
    - auto_names: Domoticz Unit number (as string) -> last auto-generated
      device name. Used to detect renames and avoid overwriting user edits.
    - last_processed_date: hub-local date YYYY-MM-DD (or None) of the last
      day whose energy data was fully folded into base_wh.
    - mode_text_hidden: whether the read-only Mode Text device has already
      been hidden as a one-time step when charger control was first enabled.
    - control_shown: whether the control units are currently shown by us for
      the enabled state. Gates the one-time show/hide on the AllowControl
      transition so a user's manual hide of a control device is never re-forced.
    """

    last_processed_date: "str | None" = None
    unit_alloc: "dict[str, int]" = field(default_factory=dict)
    base_wh: "dict[str, float]" = field(default_factory=dict)
    auto_names: "dict[str, str]" = field(default_factory=dict)
    mode_text_hidden: bool = False
    control_shown: bool = False


def migrate(raw: dict) -> dict:
    """Transform older payloads to current shape."""
    raw.setdefault("mode_text_hidden", False)
    raw.setdefault("control_shown", False)
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
            "mode_text_hidden": state.mode_text_hidden,
            "control_shown": state.control_shown,
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
        mode_text_hidden=raw.get("mode_text_hidden", False),
        control_shown=raw.get("control_shown", False),
    )
