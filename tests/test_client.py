import pytest

from myenergi_client import AsnValidationError, MyEnergiClient


def _client():
    return MyEnergiClient(serial="20000002", api_key="TESTKEY")


def test_discover_asn_accepts_valid():
    c = _client()
    assert c.discover_asn({"X_MYENERGI-asn": "s18.myenergi.net"}) == "s18.myenergi.net"
    assert c.base_url == "https://s18.myenergi.net"


def test_discover_asn_rejects_hostile_and_holds():
    c = _client()
    c.discover_asn({"X_MYENERGI-asn": "s18.myenergi.net"})  # known-good
    with pytest.raises(AsnValidationError):
        c.discover_asn({"X_MYENERGI-asn": "attacker.com"})
    assert c.base_url == "https://s18.myenergi.net"  # held last-known-good


def test_discover_asn_missing_header():
    c = _client()
    with pytest.raises(AsnValidationError):
        c.discover_asn({})


def test_key_not_in_repr():
    assert "TESTKEY" not in repr(_client())
