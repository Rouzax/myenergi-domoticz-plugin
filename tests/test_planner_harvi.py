from model import CT, Device
from planner import assign_harvi_units, plan_harvi_updates


def test_assign_units_is_stable_and_starts_at_20():
    a = assign_harvi_units({}, ["20000001", "19000001"])
    assert a == {"19000001": 20, "20000001": 21}  # sorted, from 20
    # adding a new serial keeps existing units, gives next free
    b = assign_harvi_units(a, ["19000001", "20000001", "22000001"])
    assert b["19000001"] == 20 and b["20000001"] == 21 and b["22000001"] == 22


def test_plan_harvi_updates_power_and_naming():
    h = Device(
        kind="harvi",
        serial="19000001",
        cts=[CT(1, "solar", 187), CT(2, "solar", 188), CT(3, "solar", 153)],
    )
    units = {"19000001": 20}
    ups = plan_harvi_updates([h], units, {"19000001": "SolarEdge"}, "English")
    assert len(ups) == 1
    u = ups[0]
    assert u.unit == 20 and u.type_name == "Usage" and u.name == "SolarEdge"
    assert u.svalue == "528"  # 187+188+153
    assert u.image == 19  # sun icon


def test_plan_harvi_updates_default_name_when_unmapped():
    h = Device(kind="harvi", serial="19000001", cts=[CT(1, "solar", 10)])
    ups = plan_harvi_updates([h], {"19000001": 20}, {}, "English")
    assert ups[0].name == "Harvi 19000001"


def test_non_generation_harvi_is_signed_custom_without_sun():
    # A harvi clamped to something else (role != solar) -> Custom (signed W), no sun icon.
    # Sum may be negative (e.g. a battery discharging), which Custom can display.
    h = Device(kind="harvi", serial="22000001", cts=[CT(1, "other", -300), CT(2, "other", 100)])
    ups = plan_harvi_updates([h], {"22000001": 20}, {}, "English")
    u = ups[0]
    assert u.type_name == "Custom" and u.options == {"Custom": "1;W"}
    assert u.image == 0 and u.svalue == "-200"
