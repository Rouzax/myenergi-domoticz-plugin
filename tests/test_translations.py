from translations import charge_status, device_name, plug_status, zappi_mode


def test_device_name_en_nl_and_fallback():
    assert device_name("solar_total", "English") == "Solar Total"
    assert device_name("solar_total", "Nederlands") == "Zonne-opbrengst totaal"
    assert device_name("ev", "Klingon") == "EV Charging"  # unknown lang -> English


def test_status_value_maps():
    assert zappi_mode(1, "English") == "Fast"
    assert zappi_mode(3, "Nederlands") == "Eco+"
    assert charge_status(4, "English") == "Boosting"
    assert charge_status(99, "English") == "Unknown"
    assert plug_status("C2", "English") == "Charging"
    assert plug_status("A", "Nederlands") == "Niet verbonden"
    assert plug_status("Z9", "English") == "Z9"  # unknown code -> raw
