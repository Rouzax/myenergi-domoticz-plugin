from model import harvi_names_from_slots


def test_slots_build_serial_name_map():
    params = {
        "Harvi1Serial": "21460322",
        "Harvi1Name": "SolarEdge",
        "Harvi2Serial": "21460323",
        "Harvi2Name": "Solis",
    }
    assert harvi_names_from_slots(params) == {"21460322": "SolarEdge", "21460323": "Solis"}


def test_slots_ignore_blank_and_half_filled():
    # Empty params -> empty map; a serial without a name (or vice versa) is skipped.
    assert harvi_names_from_slots({}) == {}
    assert harvi_names_from_slots({"Harvi1Serial": "21460322"}) == {}
    assert harvi_names_from_slots({"Harvi1Name": "SolarEdge"}) == {}


def test_slots_reject_invalid_serial():
    assert harvi_names_from_slots({"Harvi1Serial": "not-a-serial", "Harvi1Name": "X"}) == {}
