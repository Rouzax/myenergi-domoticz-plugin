"""Thin adapter over the DomoticzEx device API. The ONLY module importing Domoticz."""

import Domoticz


def device_id(hardware_id) -> str:
    return f"myenergi_hub{hardware_id}"


def _existing_unit(dev_id, unit):
    dev = Domoticz.Devices.get(dev_id)
    if dev is None:
        return None
    return dev.Units.get(unit)


def apply_updates(dev_id, updates, auto_names) -> dict:
    names = dict(auto_names)
    for up in updates:
        unit = _existing_unit(dev_id, up.unit)
        if unit is None:
            Domoticz.Unit(
                Name=up.name,
                DeviceID=dev_id,
                Unit=up.unit,
                TypeName=up.type_name,
                Options=up.options,
                Used=1,
            ).Create()
            unit = Domoticz.Devices[dev_id].Units[up.unit]
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
            # Not owned: the user renamed it, or ownership is unknown (fresh start
            # before any persisted auto_names). Update values only; NEVER write the
            # name and NEVER claim ownership of a name we did not set.
            unit.Update(Log=False)
    return names
