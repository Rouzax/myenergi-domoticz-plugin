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


def centi_hz_to_hz(f: int) -> float:
    return round(f / 100.0, 2)


ROLE_BY_CTT = {
    "Generation": "solar",
    "Grid": "grid",
    "Internal Load": "ev",
}


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


def _extract_cts(raw: dict) -> "list[CT]":
    cts = []
    for i in range(1, 7):
        ctt = raw.get(f"ectt{i}")
        if ctt is None:
            continue
        role = ROLE_BY_CTT.get(str(ctt), "other")
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
    return SystemStatus(devices=devices, zappi=zappi_raw)


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
