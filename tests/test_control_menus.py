from control import (
    BOOST_KWH_MENU,
    COMPLETE_BY_MENU,
    MIN_GREEN_MENU,
    _boost_kwh_options,
    _complete_by_options,
    _menu_selector_options,
    _min_green_options,
    menu_level,
    menu_value,
)


def test_menu_value_exact_and_bounds():
    assert menu_value(BOOST_KWH_MENU, 10) == 0  # first option
    assert menu_value(BOOST_KWH_MENU, 80) == 99  # last option (8th)
    assert menu_value(BOOST_KWH_MENU, 0) is None  # "Off"/level 0 -> no value
    assert menu_value(BOOST_KWH_MENU, 90) is None  # past the last option
    assert menu_value(BOOST_KWH_MENU, None) is None
    assert menu_value(COMPLETE_BY_MENU, 80) == 700  # 8th hour -> 07:00 -> HHMM 700


def test_menu_level_snaps_to_nearest():
    assert menu_level(MIN_GREEN_MENU, 50) == 60  # exact -> the 50% option (level 60)
    assert menu_level(MIN_GREEN_MENU, 52) == 60  # nearest 50%
    assert menu_level(BOOST_KWH_MENU, 12) == 30  # nearest 10 kWh (3rd option)
    assert menu_level(MIN_GREEN_MENU, 1) == 10  # first option
    assert menu_level(MIN_GREEN_MENU, 100) == 110  # last option (11th)


def test_menu_selector_options_shape():
    opts = _menu_selector_options(["1%", "10%"])
    assert opts["LevelNames"] == "Off|1%|10%"
    assert opts["LevelActions"] == "||"  # one per option
    assert opts["LevelOffHidden"] == "true"
    assert opts["SelectorStyle"] == "0"


def test_unit_bearing_labels():
    assert _min_green_options()["LevelNames"] == "Off|" + "|".join(f"{v}%" for v in MIN_GREEN_MENU)
    assert _boost_kwh_options()["LevelNames"].startswith("Off|0 kWh|5 kWh|")
    assert _complete_by_options()["LevelNames"].split("|")[1] == "00:00"
    assert _complete_by_options()["LevelNames"].split("|")[-1] == "23:00"
