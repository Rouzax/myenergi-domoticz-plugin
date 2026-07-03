"""Pure planning: aggregate energy, advance baselines, and build device updates."""

from dataclasses import dataclass, replace
from datetime import date, timedelta

import translations
from energy import clamp_counter, seed_base_wh
from model import deci_volts_to_v, joules_to_wh
from persistence import PluginState

_EV_FIELDS = ("h1d", "h2d", "h3d", "h1b", "h2b", "h3b")


def aggregate_today_wh(day_sums: dict) -> dict:
    def j(field):
        return float(day_sums.get(field, 0) or 0)

    gep, imp, exp = j("gep"), j("imp"), j("exp")
    ev_j = sum(j(f) for f in _EV_FIELDS)
    home_j = max(0.0, gep + imp - exp - ev_j)
    return {
        "solar": joules_to_wh(gep),
        "ev": joules_to_wh(ev_j),
        "home": joules_to_wh(home_j),
        "grid_import": joules_to_wh(imp),
        "grid_export": joules_to_wh(exp),
    }


def _prev_date(iso: str) -> str:
    y, m, d = (int(p) for p in iso.split("-"))
    return (date(y, m, d) - timedelta(days=1)).isoformat()


def advance_baselines(
    state, backfill_day_sums, today_sums, prev_counters, agg_units, max_system_kw, hub_date
) -> PluginState:
    base = dict(state.base_wh)
    ceiling = max_system_kw * 1000.0 * 24.0 * 3650.0  # ~10y lifetime ceiling in Wh

    # Fold each fully-completed missing day once into the baseline.
    for day in backfill_day_sums:
        agg = aggregate_today_wh(day)
        for name, unit in agg_units.items():
            base[str(unit)] = base.get(str(unit), 0.0) + agg[name]

    # Seed any missing baseline from the device's current cumulative counter.
    today = aggregate_today_wh(today_sums)
    for name, unit in agg_units.items():
        key = str(unit)
        if key not in base:
            seeded = seed_base_wh(prev_counters.get(unit, 0.0), today[name], ceiling)
            base[key] = 0.0 if seeded is None else seeded

    # last_processed_date = the last COMPLETED day (the day BEFORE today). Today is
    # never folded here; it is added live in plan(). Using hub_date would drop today
    # from base at the next midnight and freeze the monotonic counter.
    return replace(state, base_wh=base, last_processed_date=_prev_date(hub_date))


UNIT_SOLAR = 1
UNIT_HOME = 2
UNIT_EV = 3
UNIT_MODE = 4
UNIT_CHARGE_STATUS = 5
UNIT_PLUG = 6
UNIT_CHARGE_ADDED = 7
UNIT_VOLTAGE = 8
UNIT_FREQUENCY = 9
UNIT_GRID_IMPORT = 10
UNIT_GRID_EXPORT = 11
RETURN_SWITCHTYPE = 4  # Domoticz "Return" meter type (energy returned to grid / generation)
AGG_UNITS = {
    "solar": UNIT_SOLAR,
    "home": UNIT_HOME,
    "ev": UNIT_EV,
    "grid_import": UNIT_GRID_IMPORT,
    "grid_export": UNIT_GRID_EXPORT,
}


@dataclass
class DeviceUpdate:
    unit: int
    type_name: str
    options: dict
    name: str
    nvalue: int
    svalue: str
    image: int = 0
    switchtype: int = 0


def _kwh(unit, key, power_w, energy_wh, lang, switchtype=0):
    return DeviceUpdate(
        unit,
        "kWh",
        {"EnergyMeterMode": "0"},
        translations.device_name(key, lang),
        0,
        f"{int(power_w)};{energy_wh:.4f}",
        switchtype=switchtype,
    )


def _text(unit, key, value, lang):
    return DeviceUpdate(unit, "Text", {}, translations.device_name(key, lang), 0, value)


def _int(v):
    # Crash-safe coercion of an untrusted cloud field to int; 0 on anything odd.
    try:
        return int(float(str(v)))
    except (ValueError, TypeError):
        return 0


def _float(v):
    try:
        return float(str(v))
    except (ValueError, TypeError):
        return 0.0


def plan(status, today_sums, state, prev_counters, config, max_step_wh):
    z = status.zappi
    lang = config.language
    gen, grd, div = _int(z.get("gen")), _int(z.get("grd")), _int(z.get("div"))
    powers = {
        "solar": gen,
        "ev": div,
        "home": max(0, gen + grd - div),
        "grid_import": max(0, grd),
        "grid_export": max(0, -grd),
    }

    if today_sums is None:
        energies = {n: prev_counters.get(u, 0.0) for n, u in AGG_UNITS.items()}
        new_state = state
    else:
        today = aggregate_today_wh(today_sums)
        energies = {}
        for name, unit in AGG_UNITS.items():
            candidate = state.base_wh.get(str(unit), 0.0) + today[name]
            prev = prev_counters.get(unit, 0.0)
            energies[name], _warn = clamp_counter(prev, candidate, max_step_wh)
        new_state = state

    mode_text = translations.zappi_mode(_int(z.get("zmo")), lang)
    status_text = translations.charge_status(_int(z.get("sta")), str(z.get("pst", "")), lang)
    plug_text = translations.plug_status(str(z.get("pst", "")), lang)
    charge_name = translations.device_name("charge_added", lang)
    voltage_name = translations.device_name("voltage", lang)
    frequency_name = translations.device_name("frequency", lang)

    updates = [
        _kwh(
            UNIT_SOLAR,
            "solar_total",
            powers["solar"],
            energies["solar"],
            lang,
            switchtype=RETURN_SWITCHTYPE,
        ),
        _kwh(UNIT_HOME, "home", powers["home"], energies["home"], lang),
        _kwh(UNIT_EV, "ev", powers["ev"], energies["ev"], lang),
        _text(UNIT_MODE, "zappi_mode", mode_text, lang),
        _text(UNIT_CHARGE_STATUS, "charge_status", status_text, lang),
        _text(UNIT_PLUG, "plug_status", plug_text, lang),
        DeviceUpdate(
            UNIT_CHARGE_ADDED,
            "Custom",
            {"Custom": "1;kWh"},
            charge_name,
            0,
            f"{_float(z.get('che')):.2f}",
        ),
        DeviceUpdate(
            UNIT_VOLTAGE, "Voltage", {}, voltage_name, 0, f"{deci_volts_to_v(_int(z.get('vol')))}"
        ),
        DeviceUpdate(
            UNIT_FREQUENCY,
            "Custom",
            {"Custom": "1;Hz"},
            frequency_name,
            0,
            f"{_float(z.get('frq')):.2f}",
        ),
        _kwh(UNIT_GRID_IMPORT, "grid_import", powers["grid_import"], energies["grid_import"], lang),
        _kwh(
            UNIT_GRID_EXPORT,
            "grid_export",
            powers["grid_export"],
            energies["grid_export"],
            lang,
            switchtype=RETURN_SWITCHTYPE,
        ),
    ]
    return updates, new_state


HARVI_UNIT_START = 20
HARVI_IMAGE = 19  # Domoticz built-in sun icon (matches test IDX 119 CustomImage=19)


def assign_harvi_units(existing, serials, start=HARVI_UNIT_START):
    result = dict(existing)
    used = set(result.values())
    nxt = start
    for serial in sorted(s for s in serials if s not in result):
        while nxt in used:
            nxt += 1
        result[serial] = nxt
        used.add(nxt)
    return result


def plan_harvi_updates(harvis, harvi_units, harvi_names, lang):
    updates = []
    for h in harvis:
        unit = harvi_units.get(h.serial)
        if unit is None:
            continue
        power = int(sum(ct.power_w for ct in h.cts))
        name = harvi_names.get(h.serial) or translations.harvi_default_name(h.serial, lang)
        if any(ct.role == "solar" for ct in h.cts):
            # Generation: unidirectional watts -> Usage device with the sun icon.
            # Standby draw can sum slightly negative; a generation tile never shows < 0.
            gen_power = max(0, power)
            updates.append(DeviceUpdate(unit, "Usage", {}, name, 0, f"{gen_power}", HARVI_IMAGE))
        else:
            # Anything else (load, battery, storage): a signed Custom watt sensor, no icon,
            # so a battery swinging charge/discharge (+/-) renders correctly.
            updates.append(DeviceUpdate(unit, "Custom", {"Custom": "1;W"}, name, 0, f"{power}", 0))
    return updates
