"""Pure parsing, discovery, and conversion for myenergi cloud data."""

from dataclasses import dataclass, field

from sanitize import clean_label, clean_serial

_JOULES_PER_WH = 3600.0
_JOULES_PER_KWH = 3_600_000.0


def joules_to_wh(j: float) -> float:
    return j / _JOULES_PER_WH


def joules_to_kwh(j: float) -> float:
    return j / _JOULES_PER_KWH


def deci_volts_to_v(v: int) -> float:
    return round(v / 10.0, 1)


def harvi_names_from_slots(params: dict, slots: int = 4) -> "dict[str, str]":
    """Build a serial -> friendly-name map from HarviNSerial/HarviNName param pairs.

    Each filled pair (both serial and name present, serial valid) contributes one
    entry. Blank or invalid slots are ignored.
    """
    out: "dict[str, str]" = {}
    for i in range(1, slots + 1):
        serial = clean_serial(str(params.get(f"Harvi{i}Serial", "")))
        name = clean_label(str(params.get(f"Harvi{i}Name", "")).strip())
        if serial and name:
            out[serial] = name
    return out


# myenergi CT-type (ectt) -> internal role, matched case-insensitively and trimmed.
# Confirmed ectt strings (twonk API ref): Grid, Generation, Internal Load, DCPV, None, "".
# Unlisted types (Internal Load, AC Battery, Storage, Monitor, Load, and any unknown) -> "other"
# via the fallback, which renders as the bidirectional signed tile (correct for batteries/loads).
_ROLE_BY_CTT = {
    "grid": "grid",
    "generation": "solar",
    "dcpv": "solar",  # DC-coupled/hybrid inverter AC output; myenergi treats it as generation
}

# Unassigned CT types: the CT is dropped, never summed into a device's power.
_EXCLUDE_CTT = {"none", ""}


@dataclass
class CT:
    index: int
    role: str
    power_w: int


@dataclass
class Device:
    kind: str
    serial: str
    cts: "list[CT]" = field(default_factory=list)


@dataclass
class SystemStatus:
    devices: "list[Device]"
    zappi: dict
    zappi_lck: "int | None" = None


def _extract_cts(raw: dict) -> "list[CT]":
    cts = []
    for i in range(1, 7):
        ctt = raw.get(f"ectt{i}")
        if ctt is None:
            continue
        key = str(ctt).strip().lower()
        if key in _EXCLUDE_CTT:
            continue
        role = _ROLE_BY_CTT.get(key, "other")
        cts.append(CT(index=i, role=role, power_w=int(raw.get(f"ectp{i}", 0) or 0)))
    return cts


def parse_jstatus(payload: list) -> SystemStatus:
    devices: "list[Device]" = []
    zappi_raw: dict = {}
    for block in payload:
        if not isinstance(block, dict):
            continue
        for kind_key, kind in (("zappi", "zappi"), ("harvi", "harvi")):
            for raw in block.get(kind_key, []) or []:
                serial = clean_serial(raw.get("sno", ""))
                if serial is None:
                    continue
                devices.append(Device(kind=kind, serial=serial, cts=_extract_cts(raw)))
                if kind == "zappi":
                    zappi_raw = raw
    lck_raw = zappi_raw.get("lck") if isinstance(zappi_raw, dict) else None
    zappi_lck = lck_raw if isinstance(lck_raw, int) and not isinstance(lck_raw, bool) else None
    return SystemStatus(devices=devices, zappi=zappi_raw, zappi_lck=zappi_lck)


_VALID_ROLES = {"solar", "grid", "ev", "other"}
_MAX_MAPPING_LINES = 64


@dataclass
class FeedOverride:
    name: str
    role: str


def parse_feed_mapping(text: str, valid_serials: "set[str]"):
    overrides: "dict[str, FeedOverride]" = {}
    warnings: "list[str]" = []
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if len(lines) > _MAX_MAPPING_LINES:
        warnings.append(
            f"feed mapping exceeds line cap ({_MAX_MAPPING_LINES}); extra lines ignored"
        )
        lines = lines[:_MAX_MAPPING_LINES]
    for ln in lines:
        if "=" not in ln or ":" not in ln:
            warnings.append(f"malformed mapping line skipped: {ln[:40]!r}")
            continue
        serial_part, rest = ln.split("=", 1)
        name_part, role_part = rest.rsplit(":", 1)
        serial = clean_serial(serial_part)
        role = role_part.strip().lower()
        if serial is None or serial not in valid_serials:
            warnings.append(f"mapping for unknown serial skipped: {serial_part.strip()!r}")
            continue
        if role not in _VALID_ROLES:
            warnings.append(f"mapping with unknown role skipped: {role!r}")
            continue
        overrides[serial] = FeedOverride(name=clean_label(name_part.strip()), role=role)
    return overrides, warnings


JDAY_MAX_ROWS = 2000
_ENERGY_FIELDS = {
    "imp",
    "exp",
    "gep",
    "gen",
    "pect1",
    "pect2",
    "pect3",
    "nect1",
    "nect2",
    "nect3",
    "h1d",
    "h2d",
    "h3d",
    "h1b",
    "h2b",
    "h3b",
}


def _jday_rows(payload: dict) -> list:
    for key, val in payload.items():
        if key != "asn" and isinstance(val, list):
            return val
    return []


def parse_jday(payload: dict, max_rows: int = JDAY_MAX_ROWS) -> "dict[str, float]":
    sums: "dict[str, float]" = {}
    for row in _jday_rows(payload)[:max_rows]:
        if not isinstance(row, dict):
            continue
        for field_name, value in row.items():
            if field_name in _ENERGY_FIELDS and isinstance(value, (int, float)):
                sums[field_name] = sums.get(field_name, 0.0) + value
    return sums


def jday_date(payload: dict) -> "str | None":
    for row in _jday_rows(payload):
        if isinstance(row, dict) and {"yr", "mon", "dom"} <= row.keys():
            return f"{int(row['yr']):04d}-{int(row['mon']):02d}-{int(row['dom']):02d}"
    return None
