import json
from pathlib import Path

from model import parse_jstatus, ROLE_BY_CTT

FIX = Path(__file__).parent / "fixtures" / "jstatus.json"


def test_role_mapping():
    assert ROLE_BY_CTT["Generation"] == "solar"
    assert ROLE_BY_CTT["Grid"] == "grid"
    assert ROLE_BY_CTT["Internal Load"] == "ev"


def test_parse_jstatus_discovers_devices():
    status = parse_jstatus(json.loads(FIX.read_text()))
    serials = {d.serial: d for d in status.devices}
    assert set(serials) == {"10000001", "20000002"}

    harvi = serials["10000001"]
    assert harvi.kind == "harvi"
    assert [ct.role for ct in harvi.cts] == ["solar", "solar", "solar"]

    zappi = serials["20000002"]
    assert zappi.kind == "zappi"
    roles = [ct.role for ct in zappi.cts]
    assert roles == ["ev", "ev", "ev", "grid", "grid", "grid"]
    assert status.zappi["gen"] == 1215


def test_parse_jstatus_ignores_empty_and_unknown_serial():
    payload = [{"zappi": [{"sno": "not-a-serial", "ectt1": "Grid", "ectp1": 5}]}]
    assert parse_jstatus(payload).devices == []
