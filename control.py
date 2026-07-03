"""Pure control plane for the zappi: validators, command decision, reconciliation.

No Domoticz or HTTP imports. Every value that reaches a myenergi write URL is
validated and int-coerced here first; the client interpolates only validated ints.
"""

import math
from dataclasses import dataclass

from planner import DeviceUpdate
from translations import control_device_name, control_level_names

UNIT_MODE = 12
UNIT_BOOST = 13
UNIT_BOOST_KWH = 14
UNIT_BOOST_TIME = 15
UNIT_MIN_GREEN = 16
UNIT_LOCK_STATE = 18

MODE_LEVELS = {10: 1, 20: 2, 30: 3, 40: 4}
ZMO_TO_LEVEL = {1: 10, 2: 20, 3: 30, 4: 40}

MAX_KWH = 100
MAX_GREEN = 100

BOOST_KWH_MENU = (0, 5, 10, 20, 40, 60, 80, 99)
COMPLETE_BY_MENU = tuple(h * 100 for h in range(24))
MIN_GREEN_MENU = (1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)

LCK_BITS = (
    (0, "Locked Now"),
    (1, "EV Plugged"),
    (2, "EV Unplugged"),
    (3, "Charge"),
    (4, "Charge session allowed"),
)


def _finite(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def menu_value(menu, level) -> "int | None":
    if not _finite(level):
        return None
    i = int(level) // 10 - 1
    return menu[i] if 0 <= i < len(menu) else None


def menu_level(menu, value) -> int:
    i = min(range(len(menu)), key=lambda k: abs(menu[k] - value))
    return (i + 1) * 10


def validate_kwh(level) -> "int | None":
    if not _finite(level):
        return None
    kwh = int(round(float(level)))
    if kwh <= 0:
        return None
    return min(kwh, MAX_KWH)


def validate_hhmm(level) -> "str | None":
    if not _finite(level):
        return None
    hhmm = int(round(float(level)))
    if hhmm < 0:
        return None
    hh, mm = divmod(hhmm, 100)
    if hh >= 24 or mm >= 60:
        return None
    return f"{hhmm:04d}"


def clamp_min_green(level) -> "int | None":
    if not _finite(level):
        return None
    pct = int(round(float(level)))
    return max(0, min(pct, MAX_GREEN))


def decode_lck(lck: int) -> str:
    flags = [name for bit, name in LCK_BITS if lck & (1 << bit)]
    return f"{lck} ({', '.join(flags) if flags else 'none'})"


@dataclass
class WriteIntent:
    kind: str
    mode: "int | None" = None
    kwh: "int | None" = None
    hhmm: "str | None" = None
    pct: "int | None" = None


def _sibling_float(siblings, unit):
    try:
        return float(str(siblings.get(unit, "")).strip())
    except (TypeError, ValueError):
        return None


def decide_write(unit, command, level, siblings) -> "WriteIntent | None":
    if unit == UNIT_MODE:
        if command != "Set Level" or not _finite(level):
            return None
        zmo = MODE_LEVELS.get(int(level))
        return WriteIntent("mode", mode=zmo) if zmo is not None else None
    if unit == UNIT_BOOST:
        if command != "Set Level" or not _finite(level):
            return None
        lvl = int(level)
        if lvl == 30:
            return WriteIntent("boost_cancel")
        if lvl == 10:
            kwh = validate_kwh(_sibling_float(siblings, UNIT_BOOST_KWH))
            return WriteIntent("boost_manual", kwh=kwh) if kwh is not None else None
        if lvl == 20:
            kwh = validate_kwh(_sibling_float(siblings, UNIT_BOOST_KWH))
            if kwh is None:
                return None
            hhmm = validate_hhmm(_sibling_float(siblings, UNIT_BOOST_TIME))
            return WriteIntent("boost_smart", kwh=kwh, hhmm=hhmm) if hhmm is not None else None
        return None
    if unit == UNIT_MIN_GREEN:
        pct = clamp_min_green(level) if command == "Set Level" else None
        return WriteIntent("min_green", pct=pct) if pct is not None else None
    return None


def write_succeeded(kind: str, resp: object) -> bool:
    if not isinstance(resp, dict):
        return False
    if kind == "min_green":
        return "mgl" in resp
    return resp.get("status") == 0


def should_debounce(unit, now, last_write, min_gap) -> bool:
    prev = last_write.get(unit)
    return prev is not None and (now - prev) < min_gap


def allow_write_now(now, last_any_ts, min_gap) -> bool:
    return (now - last_any_ts) >= min_gap


def is_noop_update(current_nvalue, current_svalue, update) -> bool:
    return current_nvalue == update.nvalue and str(current_svalue) == str(update.svalue)


def _selector_options(kind, language, style="0"):
    level_names = "Off|" + control_level_names(kind, language)
    return {
        "LevelActions": "|" * (len(level_names.split("|")) - 1),
        "LevelNames": level_names,
        "LevelOffHidden": "true",
        "SelectorStyle": style,
    }


def _setpoint_options(unit_label, vmin, vmax, step):
    return {
        "ValueUnit": unit_label,
        "ValueMin": str(vmin),
        "ValueMax": str(vmax),
        "ValueStep": str(step),
    }


def _menu_selector_options(labels, style="0"):
    return {
        "LevelActions": "|" * len(labels),
        "LevelNames": "Off|" + "|".join(labels),
        "LevelOffHidden": "true",
        "SelectorStyle": style,
    }


def _boost_kwh_options():
    return _menu_selector_options([f"{v} kWh" for v in BOOST_KWH_MENU])


def _complete_by_options():
    return _menu_selector_options([f"{h:02d}:00" for h in range(24)])


def _min_green_options():
    return _menu_selector_options([f"{v}%" for v in MIN_GREEN_MENU])


def optimistic_update(unit, command, level, language) -> "DeviceUpdate | None":
    if unit == UNIT_MODE:
        if command != "Set Level" or not _finite(level):
            return None
        lvl = int(level)
        if lvl not in MODE_LEVELS:
            return None
        return DeviceUpdate(
            unit=UNIT_MODE,
            type_name="Selector Switch",
            options=_selector_options("mode", language),
            name=control_device_name("mode", language),
            nvalue=lvl,
            svalue=str(lvl),
            image=30,
            switchtype=18,
        )
    if unit == UNIT_BOOST:
        if command != "Set Level" or not _finite(level):
            return None
        lvl = int(level)
        if lvl not in (10, 20, 30):
            return None
        return DeviceUpdate(
            unit=UNIT_BOOST,
            type_name="Selector Switch",
            options=_selector_options("boost", language),
            name=control_device_name("boost", language),
            nvalue=lvl,
            svalue=str(lvl),
            image=30,
            switchtype=18,
        )
    if unit == UNIT_MIN_GREEN:
        pct = clamp_min_green(level) if command == "Set Level" else None
        if pct is None:
            return None
        return DeviceUpdate(
            unit=UNIT_MIN_GREEN,
            type_name="Setpoint",
            options=_setpoint_options("%", 1, MAX_GREEN, 10),
            name=control_device_name("min_green", language),
            nvalue=0,
            svalue=str(pct),
            image=30,
        )
    return None


def persist_input_setpoint(unit, level, language) -> "DeviceUpdate | None":
    if not _finite(level):
        return None
    if unit == UNIT_BOOST_KWH:
        kwh = max(0, min(int(round(float(level))), MAX_KWH))
        return DeviceUpdate(
            unit=UNIT_BOOST_KWH,
            type_name="Setpoint",
            options=_setpoint_options("kWh", 0, 99, 5),
            name=control_device_name("boost_kwh", language),
            nvalue=0,
            svalue=str(kwh),
            image=30,
        )
    if unit == UNIT_BOOST_TIME:
        hhmm = max(0, min(int(round(float(level))), 2359))
        return DeviceUpdate(
            unit=UNIT_BOOST_TIME,
            type_name="Setpoint",
            options=_setpoint_options("HHMM", 0, 2359, 15),
            name=control_device_name("boost_time", language),
            nvalue=0,
            svalue=str(hhmm),
            image=30,
        )
    return None


def boost_resting_level(zappi) -> int:
    # Verified on a plugged-in, actively-boosting zappi: Manual boost -> bsm=1,bss=0;
    # Smart boost -> bsm=1,bss=1; no boost -> both 0. So bss=1 means Smart, else
    # bsm=1 means Manual.
    if not isinstance(zappi, dict):
        return 0
    bss = zappi.get("bss")
    if isinstance(bss, int) and not isinstance(bss, bool) and bss == 1:
        return 20
    bsm = zappi.get("bsm")
    if isinstance(bsm, int) and not isinstance(bsm, bool) and bsm == 1:
        return 10
    return 0


def plan_control_updates(status, config, existing_units=frozenset()) -> "list[DeviceUpdate]":
    updates = []
    lang = config.language
    zappi = status.zappi if isinstance(status.zappi, dict) else {}
    if config.allow_control:
        zmo = zappi.get("zmo")
        if isinstance(zmo, int) and not isinstance(zmo, bool) and zmo in ZMO_TO_LEVEL:
            updates.append(
                DeviceUpdate(
                    unit=UNIT_MODE,
                    type_name="Selector Switch",
                    options=_selector_options("mode", lang),
                    name=control_device_name("mode", lang),
                    nvalue=ZMO_TO_LEVEL[zmo],
                    svalue=str(ZMO_TO_LEVEL[zmo]),
                    image=30,
                    switchtype=18,
                )
            )
        rest = boost_resting_level(zappi)
        updates.append(
            DeviceUpdate(
                unit=UNIT_BOOST,
                type_name="Selector Switch",
                options=_selector_options("boost", lang),
                name=control_device_name("boost", lang),
                nvalue=rest,
                svalue=str(rest),
                image=30,
                switchtype=18,
            )
        )
        if UNIT_BOOST_KWH not in existing_units:
            updates.append(
                DeviceUpdate(
                    unit=UNIT_BOOST_KWH,
                    type_name="Setpoint",
                    options=_setpoint_options("kWh", 0, 99, 5),
                    name=control_device_name("boost_kwh", lang),
                    nvalue=0,
                    svalue="0",
                    image=30,
                )
            )
        if UNIT_BOOST_TIME not in existing_units:
            updates.append(
                DeviceUpdate(
                    unit=UNIT_BOOST_TIME,
                    type_name="Setpoint",
                    options=_setpoint_options("HHMM", 0, 2359, 15),
                    name=control_device_name("boost_time", lang),
                    nvalue=0,
                    svalue="0",
                    image=30,
                )
            )
        mgl = zappi.get("mgl")
        if isinstance(mgl, int) and not isinstance(mgl, bool):
            updates.append(
                DeviceUpdate(
                    unit=UNIT_MIN_GREEN,
                    type_name="Setpoint",
                    options=_setpoint_options("%", 1, MAX_GREEN, 10),
                    name=control_device_name("min_green", lang),
                    nvalue=0,
                    svalue=str(mgl),
                    image=30,
                )
            )
    if config.allow_control and status.zappi_lck is not None:
        updates.append(
            DeviceUpdate(
                unit=UNIT_LOCK_STATE,
                type_name="Text",
                options={},
                name=control_device_name("lock_state", lang),
                nvalue=0,
                svalue=decode_lck(status.zappi_lck),
            )
        )
    return updates
