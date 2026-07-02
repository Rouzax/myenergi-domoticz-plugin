"""Pure EN/NL string tables for device names and status/mode values."""

import sanitize

LANGUAGES = ("English", "Nederlands")
_DEFAULT = "English"

_NAMES = {
    "solar_total": {"English": "Solar Total", "Nederlands": "Zonne-opbrengst totaal"},
    "home": {"English": "Home Consumption", "Nederlands": "Huisverbruik"},
    "ev": {"English": "EV Charging", "Nederlands": "EV laden"},
    "grid_import": {"English": "Grid Import", "Nederlands": "Netafname"},
    "grid_export": {"English": "Grid Export", "Nederlands": "Netinvoer"},
    "zappi_mode": {"English": "Zappi Mode", "Nederlands": "Zappi modus"},
    "charge_status": {"English": "Charge Status", "Nederlands": "Laadstatus"},
    "plug_status": {"English": "Plug Status", "Nederlands": "Stekkerstatus"},
    "charge_added": {"English": "Charge Added", "Nederlands": "Toegevoegd laden"},
    "voltage": {"English": "Grid Voltage", "Nederlands": "Netspanning"},
    "frequency": {"English": "Grid Frequency", "Nederlands": "Netfrequentie"},
}
_CONTROL_LEVELS = {
    "mode": {
        "English": "Fast|Eco|Eco+|Stopped",
        "Nederlands": "Snel|Eco|Eco+|Gestopt",
    },
    "boost": {
        "English": "Stop|Manual|Smart",
        "Nederlands": "Stop|Handmatig|Slim",
    },
}
_CONTROL_NAMES = {
    "mode": {"English": "Charge Mode", "Nederlands": "Laadmodus"},
    "boost": {"English": "Boost", "Nederlands": "Boost"},
    "boost_kwh": {"English": "Boost kWh", "Nederlands": "Boost kWh"},
    "boost_time": {"English": "Boost Complete By", "Nederlands": "Boost Klaar Om"},
    "min_green": {"English": "Min Green Level", "Nederlands": "Min Groen Niveau"},
    "lock_state": {"English": "Charger Lock State", "Nederlands": "Lader Vergrendelstatus"},
}
_ZMO = {
    1: {"English": "Fast", "Nederlands": "Snel"},
    2: {"English": "Eco", "Nederlands": "Eco"},
    3: {"English": "Eco+", "Nederlands": "Eco+"},
    4: {"English": "Stopped", "Nederlands": "Gestopt"},
}
_STA = {
    1: {"English": "Paused", "Nederlands": "Gepauzeerd"},
    3: {"English": "Diverting", "Nederlands": "Omleiden"},
    4: {"English": "Boosting", "Nederlands": "Boosten"},
    5: {"English": "Complete", "Nederlands": "Voltooid"},
}
_IDLE = {"English": "Idle", "Nederlands": "Inactief"}
_PST = {
    "A": {"English": "Disconnected", "Nederlands": "Niet verbonden"},
    "B1": {"English": "Connected", "Nederlands": "Verbonden"},
    "B2": {"English": "Connected", "Nederlands": "Verbonden"},
    "C1": {"English": "Charging", "Nederlands": "Laden"},
    "C2": {"English": "Charging", "Nederlands": "Laden"},
    "F": {"English": "Fault", "Nederlands": "Storing"},
}


def _lookup(table, key, lang, fallback_value):
    entry = table.get(key)
    if entry is None:
        return fallback_value
    return entry.get(lang, entry[_DEFAULT])


def device_name(key: str, lang: str) -> str:
    return _lookup(_NAMES, key, lang, key)


def zappi_mode(zmo: int, lang: str) -> str:
    return _lookup(_ZMO, zmo, lang, "Unknown")


def charge_status(sta: int, pst: str, lang: str) -> str:
    # The zappi holds a stale sta (e.g. 4/Boosting) after the EV is unplugged, so
    # gate on the plug status: pst "A" means EV disconnected -> report Idle.
    if str(pst)[:1].upper() == "A":
        return _IDLE.get(lang, _IDLE[_DEFAULT])
    return _lookup(_STA, sta, lang, "Unknown")


def plug_status(pst: str, lang: str) -> str:
    # Unknown code passes through sanitized (untrusted cloud string on a Text device).
    return _lookup(_PST, pst, lang, sanitize.clean_label(str(pst), max_len=4))


def harvi_default_name(serial: str, lang: str) -> str:
    return f"Harvi {serial}"


def control_level_names(kind: str, language: str) -> str:
    table = _CONTROL_LEVELS[kind]
    return table.get(language, table[_DEFAULT])


def control_device_name(key: str, language: str) -> str:
    table = _CONTROL_NAMES[key]
    return table.get(language, table[_DEFAULT])
