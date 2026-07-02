import json

import pytest

from myenergi_client import AsnValidationError, MyEnergiClient, WriteError


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


# ---------------------------------------------------------------------------
# Write-method tests (gated control endpoints)
# ---------------------------------------------------------------------------


class _RecordingOpener:
    """Records the last requested URL and returns a canned control-endpoint response."""

    def __init__(self):
        self.url = None

    def open(self, req, timeout=None):  # noqa: ARG002
        self.url = req.full_url
        return _FakeResponse(b'{"status":0}', {})


def _write_client(writes=True, lock=True):
    rec = _RecordingOpener()
    c = MyEnergiClient(
        "10000001",
        "k",
        opener_factory=lambda: rec,
        writes_enabled=writes,
        lock_enabled=lock,
    )
    c._asn = "s18.myenergi.net"
    return c, rec


class TestWriteMethods:
    def test_set_mode_builds_expected_url(self):
        c, rec = _write_client()
        resp = c.set_zappi_mode("10000001", 1)
        assert rec.url == "https://s18.myenergi.net/cgi-zappi-mode-Z10000001-1-0-0-0000"
        assert resp == {"status": 0}

    def test_write_blocked_when_gate_off(self):
        c, _ = _write_client(writes=False)
        with pytest.raises(WriteError):
            c.set_zappi_mode("10000001", 1)

    def test_lock_blocked_when_lock_gate_off(self):
        c, _ = _write_client(lock=False)
        with pytest.raises(WriteError):
            c.set_lock("10000001", "01000000")

    def test_non_digit_serial_refused(self):
        c, _ = _write_client()
        with pytest.raises(WriteError):
            c.set_zappi_mode("10000001/../evil", 1)

    def test_smart_boost_url(self):
        c, rec = _write_client()
        c.set_boost_smart("10000001", 5, "1400")
        assert rec.url == "https://s18.myenergi.net/cgi-zappi-mode-Z10000001-0-11-5-1400"

    def test_smart_boost_rejects_path_injection(self):
        c, rec = _write_client()
        with pytest.raises(WriteError):
            c.set_boost_smart("10000001", 5, "../evil")
        assert rec.url is None

    def test_smart_boost_rejects_wrong_length(self):
        c, rec = _write_client()
        with pytest.raises(WriteError):
            c.set_boost_smart("10000001", 5, "140")
        assert rec.url is None

    def test_manual_boost_url(self):
        c, rec = _write_client()
        c.set_boost_manual("10000001", 5)
        assert rec.url == "https://s18.myenergi.net/cgi-zappi-mode-Z10000001-0-10-5-0000"

    def test_cancel_boost_url(self):
        c, rec = _write_client()
        c.cancel_boost("10000001")
        assert rec.url == "https://s18.myenergi.net/cgi-zappi-mode-Z10000001-0-2-0-0000"

    def test_min_green_url(self):
        c, rec = _write_client()
        c.set_min_green("10000001", 50)
        assert rec.url == "https://s18.myenergi.net/cgi-set-min-green-Z10000001-50"

    def test_lock_url(self):
        c, rec = _write_client()
        c.set_lock("10000001", "01000000")
        assert rec.url == "https://s18.myenergi.net/cgi-jlock-10000001-01000000"

    def test_lock_rejects_path_injection(self):
        c, rec = _write_client()
        with pytest.raises(WriteError):
            c.set_lock("10000001", "0100/000")
        assert rec.url is None

    def test_lock_rejects_wrong_length(self):
        c, rec = _write_client()
        with pytest.raises(WriteError):
            c.set_lock("10000001", "012")
        assert rec.url is None

    def test_write_requires_base_url(self):
        c, _ = _write_client()
        c._asn = None
        with pytest.raises(WriteError):
            c.set_zappi_mode("10000001", 1)
