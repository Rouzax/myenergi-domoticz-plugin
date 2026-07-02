from translations import charge_status, device_name, plug_status, zappi_mode


def test_device_name_en_nl_and_fallback():
    assert device_name("solar_total", "English") == "Solar Total"
    assert device_name("solar_total", "Nederlands") == "Zonne-opbrengst totaal"
    assert device_name("ev", "Klingon") == "EV Charging"  # unknown lang -> English
    assert device_name("grid_import", "English") == "Grid Import"
    assert device_name("grid_export", "Nederlands") == "Netinvoer"


def test_status_value_maps():
    assert zappi_mode(1, "English") == "Fast"
    assert zappi_mode(3, "Nederlands") == "Eco+"
    # Connected plug (B1): the sta map applies.
    assert charge_status(4, "B1", "English") == "Boosting"
    assert charge_status(99, "B1", "English") == "Unknown"
    assert plug_status("C2", "English") == "Charging"
    assert plug_status("A", "Nederlands") == "Niet verbonden"
    assert plug_status("Z9", "English") == "Z9"  # unknown code -> raw


def test_charge_status_idle_when_unplugged():
    # pst "A" = EV disconnected; a stale sta (e.g. 4/Boosting) must report Idle.
    assert charge_status(4, "A", "English") == "Idle"
    assert charge_status(4, "A", "Nederlands") == "Inactief"
    assert charge_status(1, "", "English") == "Paused"  # no plug info -> sta map
