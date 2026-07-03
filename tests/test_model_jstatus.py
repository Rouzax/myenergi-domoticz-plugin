import json
from pathlib import Path

from model import parse_jstatus

FIX = Path(__file__).parent / "fixtures" / "jstatus.json"


def _roles(block):
    return [ct.role for ct in parse_jstatus([block]).devices[0].cts]


def test_ct_role_case_insensitive_and_trimmed():
    block = {
        "harvi": [
            {"sno": "10000001", "ectt1": "  GENERATION  ", "ectt2": "grid", "ectp1": 5, "ectp2": 6}
        ]
    }
    assert _roles(block) == ["solar", "grid"]


def test_ct_role_dcpv_is_generation():
    block = {"harvi": [{"sno": "10000001", "ectt1": "DCPV", "ectp1": 9}]}
    assert _roles(block) == ["solar"]


def test_ct_role_internal_load_is_other_not_ev():
    block = {"harvi": [{"sno": "10000001", "ectt1": "Internal Load", "ectp1": 3}]}
    assert _roles(block) == ["other"]


def test_ct_role_unknown_types_fall_back_to_other():
    block = {
        "harvi": [
            {
                "sno": "10000001",
                "ectt1": "AC Battery",
                "ectt2": "Storage",
                "ectt3": "Wibble",
                "ectp1": 1,
                "ectp2": 2,
                "ectp3": 3,
            }
        ]
    }
    assert _roles(block) == ["other", "other", "other"]


def test_ct_none_and_blank_are_excluded():
    block = {
        "harvi": [
            {
                "sno": "10000001",
                "ectt1": "Generation",
                "ectt2": "None",
                "ectt3": " ",
                "ectp1": 7,
                "ectp2": 8,
                "ectp3": 9,
            }
        ]
    }
    dev = parse_jstatus([block]).devices[0]
    assert [(ct.index, ct.role) for ct in dev.cts] == [(1, "solar")]


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
    assert roles == ["other", "other", "other", "grid", "grid", "grid"]
    assert status.zappi["gen"] == 1215


def test_parse_jstatus_ignores_empty_and_unknown_serial():
    payload = [{"zappi": [{"sno": "not-a-serial", "ectt1": "Grid", "ectp1": 5}]}]
    assert parse_jstatus(payload).devices == []


def test_parse_jstatus_extracts_lck():
    payload = [{"zappi": [{"sno": 10000001, "zmo": 1, "lck": 16}]}]
    status = parse_jstatus(payload)
    assert status.zappi_lck == 16


def test_parse_jstatus_lck_absent_is_none():
    payload = [{"zappi": [{"sno": 10000001, "zmo": 1}]}]
    status = parse_jstatus(payload)
    assert status.zappi_lck is None
