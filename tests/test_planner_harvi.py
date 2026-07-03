from model import CT, Device, parse_jstatus
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


def test_generation_harvi_negative_standby_draw_clamps_to_zero():
    # FB12: idle-standby draw can sum slightly negative on a generation harvi; a
    # generation tile (Usage + sun icon) never shows a negative value.
    h = Device(kind="harvi", serial="19000001", cts=[CT(1, "solar", -4)])
    ups = plan_harvi_updates([h], {"19000001": 20}, {}, "English")
    assert ups[0].svalue == "0"


def test_generation_harvi_positive_power_is_unaffected():
    h = Device(kind="harvi", serial="19000001", cts=[CT(1, "solar", 100)])
    ups = plan_harvi_updates([h], {"19000001": 20}, {}, "English")
    assert ups[0].svalue == "100"


def test_non_generation_harvi_negative_value_stays_signed():
    # Non-generation (battery/other) harvis keep their raw signed value; only the
    # generation branch is clamped.
    h = Device(kind="harvi", serial="22000001", cts=[CT(1, "other", -50)])
    ups = plan_harvi_updates([h], {"22000001": 20}, {}, "English")
    assert ups[0].svalue == "-50"


def _harvi_updates_from_raw(*harvi_raws):
    status = parse_jstatus([{"harvi": list(harvi_raws)}])
    harvis = [d for d in status.devices if d.kind == "harvi"]
    units = assign_harvi_units({}, [h.serial for h in harvis])
    return plan_harvi_updates(harvis, units, {}, "English"), harvis


def test_none_cts_excluded_from_harvi_power_sum():
    ups, _ = _harvi_updates_from_raw(
        {
            "sno": "19000001",
            "ectt1": "Generation",
            "ectt2": "Generation",
            "ectt3": "None",
            "ectp1": 100,
            "ectp2": 200,
            "ectp3": 999,
        }
    )
    assert ups[0].type_name == "Usage"
    assert ups[0].svalue == "300"  # 100 + 200; the None CT's 999 is excluded


def test_dcpv_harvi_renders_as_generation():
    ups, _ = _harvi_updates_from_raw({"sno": "19000001", "ectt1": "DCPV", "ectp1": 250})
    assert ups[0].type_name == "Usage" and ups[0].image == 19 and ups[0].svalue == "250"


def test_all_none_harvi_has_no_cts_and_zero_power():
    ups, harvis = _harvi_updates_from_raw(
        {"sno": "19000001", "ectt1": "None", "ectt2": " ", "ectp1": 5, "ectp2": 6}
    )
    assert harvis[0].cts == []
    assert len(ups) == 1 and ups[0].svalue == "0"


def test_multiple_harvis_classify_independently():
    ups, harvis = _harvi_updates_from_raw(
        {"sno": "19000001", "ectt1": "Generation", "ectp1": 100},
        {"sno": "22000001", "ectt1": "AC Battery", "ectp1": -50},
    )
    kinds = {h.serial: u.type_name for h, u in zip(harvis, ups)}
    assert kinds["19000001"] == "Usage"  # generation tile
    assert kinds["22000001"] == "Custom"  # battery -> signed tile
