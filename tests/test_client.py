import json

import pytest

from myenergi_client import AsnValidationError, MyEnergiClient


def _client():
    return MyEnergiClient(serial="20000002", api_key="TESTKEY")


# ---------------------------------------------------------------------------
# Fake transport helpers
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Minimal response stub: context manager + read() + headers dict."""

    def __init__(self, body: bytes, headers: dict):
        self.headers = headers
        self._body = body

    def read(self, n: int = -1) -> bytes:
        if n < 0 or n >= len(self._body):
            return self._body
        return self._body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


class _FakeOpener:
    """Records full_url of every request and returns a single canned response."""

    def __init__(self, response: _FakeResponse):
        self._response = response
        self.urls: list = []

    def open(self, req, timeout=None):  # noqa: ARG002
        self.urls.append(req.full_url)
        return self._response


# ---------------------------------------------------------------------------
# Transport tests (injected opener_factory)
# ---------------------------------------------------------------------------


class TestTransport:
    def test_discover_from_director(self):
        """discover_from_director() hits the director URL and caches the ASN."""
        body = json.dumps([{"E": {"sno": 20000001}}]).encode()
        response = _FakeResponse(body, {"X_MYENERGI-asn": "s18.myenergi.net"})
        fake_opener = _FakeOpener(response)
        client = MyEnergiClient(
            serial="20000001",
            api_key="TESTKEY",
            opener_factory=lambda: fake_opener,
        )
        asn = client.discover_from_director()
        assert asn == "s18.myenergi.net"
        assert client.base_url == "https://s18.myenergi.net"
        assert fake_opener.urls == ["https://director.myenergi.net/cgi-jstatus-E"]

    def test_fetch_status_after_discovery(self):
        """fetch_status() requests cgi-jstatus-* on the discovered ASN host."""
        payload = [{"zappi": [{"sno": 20000001, "sta": 1}]}]
        body = json.dumps(payload).encode()
        response = _FakeResponse(body, {})
        fake_opener = _FakeOpener(response)
        client = MyEnergiClient(
            serial="20000001",
            api_key="TESTKEY",
            opener_factory=lambda: fake_opener,
        )
        client._asn = "s18.myenergi.net"
        result = client.fetch_status()
        assert fake_opener.urls == ["https://s18.myenergi.net/cgi-jstatus-*"]
        assert result == payload

    def test_fetch_jday(self):
        """fetch_jday() builds the correct cgi-jday URL and returns parsed JSON."""
        payload = [{"U20000002": [{"yr": 2026, "mon": 7, "dom": 1}]}]
        body = json.dumps(payload).encode()
        response = _FakeResponse(body, {})
        fake_opener = _FakeOpener(response)
        client = MyEnergiClient(
            serial="20000002",
            api_key="TESTKEY",
            opener_factory=lambda: fake_opener,
        )
        client._asn = "s18.myenergi.net"
        result = client.fetch_jday("Z", "20000002", "2026-7-1")
        assert fake_opener.urls == ["https://s18.myenergi.net/cgi-jday-Z20000002-2026-7-1"]
        assert result == payload


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


def test_asn_host_credentials_registered_for_digest():
    c = MyEnergiClient(serial="20000002", api_key="TESTKEY")
    c.discover_asn({"X_MYENERGI-asn": "s18.myenergi.net"})
    # Server challenges with its own realm; default-realm fallback must return our creds
    user, pw = c._pwmgr.find_user_password(
        "MyEnergi Telemetry", "https://s18.myenergi.net/cgi-jstatus-*"
    )
    assert (user, pw) == ("20000002", "TESTKEY")
