# pyright: reportMissingImports=false
"""Thin adapter over the DomoticzEx device API. The ONLY module importing Domoticz."""

import DomoticzEx as Domoticz

import persistence


def device_id(hardware_id) -> str:
    return f"myenergi_hub{hardware_id}"


def _existing_unit(devices, dev_id, unit):
    dev = devices.get(dev_id)
    if dev is None:
        return None
    return dev.Units.get(unit)


def apply_updates(devices, dev_id, updates, auto_names) -> dict:
    names = dict(auto_names)
    for up in updates:
        unit = _existing_unit(devices, dev_id, up.unit)
        if unit is None:
            Domoticz.Unit(
                Name=up.name,
                DeviceID=dev_id,
                Unit=up.unit,
                TypeName=up.type_name,
                Options=up.options,
                Image=up.image,
                Used=1,
            ).Create()
            unit = devices[dev_id].Units[up.unit]
            unit.nValue = up.nvalue
            unit.sValue = up.svalue
            unit.Update(Log=False)
            names[str(up.unit)] = up.name
            continue

        unit.nValue = up.nvalue
        unit.sValue = up.svalue
        owned = unit.Name == names.get(str(up.unit))
        if owned and unit.Name != up.name:
            unit.Name = up.name
            unit.Update(Log=False, UpdateProperties=True)
            names[str(up.unit)] = up.name
        else:
            # Not owned (user renamed it, or ownership is unknown from a fresh start
            # before any persisted auto_names), OR owned but the name is already
            # correct and unchanged. In both cases: update values only; NEVER write
            # the name and NEVER claim ownership of a name we did not set.
            unit.Update(Log=False)
    return names


def read_prev_counters(devices, dev_id, units) -> dict:
    out = {}
    for unit in units:
        u = _existing_unit(devices, dev_id, unit)
        wh = 0.0
        if u is not None and ";" in str(u.sValue):
            try:
                wh = float(str(u.sValue).split(";", 1)[1])
            except (ValueError, IndexError):
                wh = 0.0
        out[unit] = wh
    return out


def load_state():
    return persistence.loads(Domoticz.Configuration().get("state", ""))


def save_state(state) -> None:
    # Read-modify-write so other Configuration keys (future plans) are preserved.
    cfg = Domoticz.Configuration()
    cfg["state"] = persistence.dumps(state)
    Domoticz.Configuration(cfg)


def log_redacted(level_fn, message, secret) -> None:
    text = str(message)
    if secret:
        text = text.replace(str(secret), "***")
    level_fn(text)
