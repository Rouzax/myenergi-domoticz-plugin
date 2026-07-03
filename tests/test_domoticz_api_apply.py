import Domoticz

from domoticz_api import activate_units, apply_updates, deactivate_units, device_id
from planner import DeviceUpdate


def _u(unit, name, sval, tn="kWh", opts=None):
    return DeviceUpdate(unit, tn, opts or {"EnergyMeterMode": "0"}, name, 0, sval)


def test_creates_missing_device_with_name_and_values():
    did = device_id(7)
    names = apply_updates(Domoticz.Devices, did, [_u(1, "Solar Total", "10;1.0")], {})
    unit = Domoticz.Devices[did].Units[1]
    assert unit.Name == "Solar Total" and unit.sValue == "10;1.0"
    assert unit.Options == {"EnergyMeterMode": "0"}
    assert names["1"] == "Solar Total"


def test_updates_value_and_respects_manual_rename():
    did = device_id(7)
    names = apply_updates(Domoticz.Devices, did, [_u(1, "Solar Total", "10;1.0")], {})
    # user manually renamed the tile
    Domoticz.Devices[did].Units[1].Name = "My Panels"
    names = apply_updates(Domoticz.Devices, did, [_u(1, "Solar Total", "20;2.0")], names)
    unit = Domoticz.Devices[did].Units[1]
    assert unit.sValue == "20;2.0"  # value updated
    assert unit.Name == "My Panels"  # manual rename preserved


def test_relocalized_name_applied_when_still_owned():
    did = device_id(7)
    names = apply_updates(Domoticz.Devices, did, [_u(1, "Solar Total", "10;1.0")], {})
    names = apply_updates(Domoticz.Devices, did, [_u(1, "Zonne-opbrengst totaal", "10;1.0")], names)
    assert Domoticz.Devices[did].Units[1].Name == "Zonne-opbrengst totaal"


def test_owned_name_unchanged_updates_value_no_spurious_rename():
    # Apply once to create + record name, then apply again with the SAME name but
    # a new value. The value must update; no rename/UpdateProperties should fire,
    # and the ownership map must be identical (no churn).
    did = device_id(7)
    names = apply_updates(Domoticz.Devices, did, [_u(1, "Solar Total", "10;1.0")], {})
    names2 = apply_updates(Domoticz.Devices, did, [_u(1, "Solar Total", "20;2.0")], names)
    unit = Domoticz.Devices[did].Units[1]
    assert unit.sValue == "20;2.0"
    assert unit.Name == "Solar Total"
    # Ownership map must be identical: same keys, same values, no new entries.
    assert names2 == names


def test_creates_harvi_device_with_image():
    did = device_id(7)
    up = DeviceUpdate(20, "Usage", {}, "SolarEdge", 0, "528", 19)
    apply_updates(Domoticz.Devices, did, [up], {})
    assert Domoticz.Devices[did].Units[20].Image == 19


def test_creates_device_with_switchtype():
    did = device_id(7)
    up = DeviceUpdate(1, "kWh", {"EnergyMeterMode": "0"}, "Solar Total", 0, "1215;5000.0000", 0, 4)
    apply_updates(Domoticz.Devices, did, [up], {})
    assert Domoticz.Devices[did].Units[1].SwitchType == 4


def test_deactivate_sets_used_zero():
    did = device_id(1)
    apply_updates(
        Domoticz.Devices,
        did,
        [
            DeviceUpdate(
                unit=4,
                type_name="Text",
                options={},
                name="Zappi Mode",
                nvalue=0,
                svalue="Eco",
            )
        ],
        {},
    )
    deactivate_units(Domoticz.Devices, did, [4])
    assert Domoticz.Devices[did].Units[4].Used == 0


def test_deactivate_missing_unit_is_noop():
    did = device_id(1)
    deactivate_units(Domoticz.Devices, did, [99])  # must not raise


def _spy_update_calls(unit):
    calls = []
    orig = unit.Update

    def _wrapped(**kw):
        calls.append(kw)
        return orig(**kw)

    unit.Update = _wrapped
    return calls


def test_deactivate_idempotent_skips_update_when_already_hidden():
    did = device_id(1)
    apply_updates(
        Domoticz.Devices,
        did,
        [_u(4, "Zappi Mode", "Eco", tn="Text", opts={})],
        {},
    )
    unit = Domoticz.Devices[did].Units[4]
    unit.Used = 0
    calls = _spy_update_calls(unit)
    deactivate_units(Domoticz.Devices, did, [4])
    assert unit.Used == 0
    assert calls == []


def test_activate_sets_used_one():
    did = device_id(1)
    apply_updates(
        Domoticz.Devices,
        did,
        [_u(12, "Charge Mode", "0", tn="Selector Switch", opts={})],
        {},
    )
    unit = Domoticz.Devices[did].Units[12]
    unit.Used = 0
    activate_units(Domoticz.Devices, did, [12])
    assert unit.Used == 1


def test_activate_idempotent_skips_update_when_already_visible():
    did = device_id(1)
    apply_updates(
        Domoticz.Devices,
        did,
        [_u(12, "Charge Mode", "0", tn="Selector Switch", opts={})],
        {},
    )
    unit = Domoticz.Devices[did].Units[12]
    assert unit.Used == 1  # Create() defaults Used=1
    calls = _spy_update_calls(unit)
    activate_units(Domoticz.Devices, did, [12])
    assert unit.Used == 1
    assert calls == []


def test_activate_missing_unit_is_noop():
    did = device_id(1)
    activate_units(Domoticz.Devices, did, [99])  # must not raise
