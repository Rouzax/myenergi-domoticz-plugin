import Domoticz

from domoticz_api import apply_updates, device_id
from planner import DeviceUpdate


def _u(unit, name, sval, tn="kWh", opts=None):
    return DeviceUpdate(unit, tn, opts or {"EnergyMeterMode": "0"}, name, 0, sval)


def test_creates_missing_device_with_name_and_values():
    did = device_id(7)
    names = apply_updates(did, [_u(1, "Solar Total", "10;1.0")], {})
    unit = Domoticz.Devices[did].Units[1]
    assert unit.Name == "Solar Total" and unit.sValue == "10;1.0"
    assert unit.Options == {"EnergyMeterMode": "0"}
    assert names["1"] == "Solar Total"


def test_updates_value_and_respects_manual_rename():
    did = device_id(7)
    names = apply_updates(did, [_u(1, "Solar Total", "10;1.0")], {})
    # user manually renamed the tile
    Domoticz.Devices[did].Units[1].Name = "My Panels"
    names = apply_updates(did, [_u(1, "Solar Total", "20;2.0")], names)
    unit = Domoticz.Devices[did].Units[1]
    assert unit.sValue == "20;2.0"  # value updated
    assert unit.Name == "My Panels"  # manual rename preserved


def test_relocalized_name_applied_when_still_owned():
    did = device_id(7)
    names = apply_updates(did, [_u(1, "Solar Total", "10;1.0")], {})
    names = apply_updates(did, [_u(1, "Zonne-opbrengst totaal", "10;1.0")], names)
    assert Domoticz.Devices[did].Units[1].Name == "Zonne-opbrengst totaal"
