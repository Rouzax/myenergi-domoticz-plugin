import Domoticz

import plugin
from config import Config
from control import UNIT_BOOST_KWH, UNIT_BOOST_TIME, UNIT_MODE


class _FakeClient:
    def __init__(self):
        self.calls = []
        self.base_url = "https://s18.myenergi.net"

    def set_zappi_mode(self, serial, mode):
        self.calls.append(("mode", serial, mode))
        return {"status": 0}


def _setup(allow_control=True):
    st = plugin._state
    st.config = Config("10000001", "k", "English", 20, 6, 25.0, 0, allow_control=allow_control)
    st.client = _FakeClient()
    st.zappi_serial = "10000001"
    return st


def test_oncommand_mode_write(monkeypatch):
    st = _setup()
    plugin.onCommand("myenergi_hub1", UNIT_MODE, "Set Level", 10, "")
    assert st.client.calls == [("mode", "10000001", 1)]


def test_oncommand_blocked_when_control_off():
    st = _setup(allow_control=False)
    plugin.onCommand("myenergi_hub1", UNIT_MODE, "Set Level", 10, "")
    assert st.client.calls == []


def test_oncommand_fail_closed_without_serial():
    st = _setup()
    st.zappi_serial = None
    plugin.onCommand("myenergi_hub1", UNIT_MODE, "Set Level", 10, "")
    assert st.client.calls == []


def test_oncommand_write_rejection_redacts_api_key_from_log():
    # Security requirement: the api_key must never reach the log, even when the
    # write is rejected and the myenergi response echoes back attacker/self
    # controlled text that happens to contain the key. If log_redacted were ever
    # bypassed on this path, the sentinel below would show up verbatim in _log.
    sentinel = "sk-myenergi-secret-9f3d2a1b"
    st = plugin._state
    st.config = Config("10000001", sentinel, "English", 20, 6, 25.0, 0, allow_control=True)

    class _RejectingClient:
        def __init__(self):
            self.calls = []
            self.base_url = "https://s18.myenergi.net"

        def set_zappi_mode(self, serial, mode):
            self.calls.append(("mode", serial, mode))
            return {"status": 1, "error": f"denied for key {sentinel}"}

    st.client = _RejectingClient()
    st.zappi_serial = "10000001"

    plugin.onCommand("myenergi_hub1", UNIT_MODE, "Set Level", 10, "")

    assert st.client.calls == [("mode", "10000001", 1)]
    assert not any(sentinel in line for line in Domoticz._log)
    assert any("myenergi write rejected" in line for line in Domoticz._log)


def _mode_unit(st):
    did = plugin.domoticz_api.device_id(plugin._hardware_id())
    return Domoticz.Devices[did].Units[UNIT_MODE]


def test_oncommand_optimistic_apply_on_success():
    st = _setup()
    plugin.onCommand("myenergi_hub1", UNIT_MODE, "Set Level", 40, "")  # Stop
    assert _mode_unit(st).nValue == 40


def test_oncommand_optimistic_value_persists_no_confirm_fetch():
    # The myenergi cloud is eventually-consistent: reading status right after a
    # successful write can still return the stale pre-change value. onCommand
    # must not fetch status at all on a write success, so a stale reconcile can
    # never snap the widget back; the next heartbeat (honoring
    # reconcile_suppress) is the source of truth once the cloud catches up.
    st = _setup()

    class _StaleStatusClient:
        def __init__(self):
            self.calls = []
            self.fetch_status_called = False
            self.base_url = "https://s18.myenergi.net"

        def set_zappi_mode(self, serial, mode):
            self.calls.append(("mode", serial, mode))
            return {"status": 0}

        def fetch_status(self):
            self.fetch_status_called = True
            return {"zappi": [{"sno": 10000001, "zmo": 1, "lck": 0}]}

    st.client = _StaleStatusClient()
    st.zappi_serial = "10000001"

    plugin.onCommand("myenergi_hub1", UNIT_MODE, "Set Level", 40, "")  # Stop

    assert _mode_unit(st).nValue == 40
    assert st.client.fetch_status_called is False


def _boost_kwh_unit(st):
    did = plugin.domoticz_api.device_id(plugin._hardware_id())
    return Domoticz.Devices[did].Units[UNIT_BOOST_KWH]


def _boost_time_unit(st):
    did = plugin.domoticz_api.device_id(plugin._hardware_id())
    return Domoticz.Devices[did].Units[UNIT_BOOST_TIME]


def test_oncommand_persists_boost_kwh_selector_without_cloud_write():
    st = _setup()
    plugin.onCommand("myenergi_hub1", UNIT_BOOST_KWH, "Set Level", 40, "")  # level 40 -> 20 kWh
    assert _boost_kwh_unit(st).sValue == "40"
    assert st.client.calls == []


def test_oncommand_persists_boost_time_selector_without_cloud_write():
    st = _setup()
    plugin.onCommand("myenergi_hub1", UNIT_BOOST_TIME, "Set Level", 80, "")  # level 80 -> 07:00
    assert _boost_time_unit(st).sValue == "80"
    assert st.client.calls == []


_DIGEST_ARTIFACTS = ("Authorization", "WWW-Authenticate", "nonce=", "realm=", "qop=", "cnonce=")


def test_oncommand_write_never_leaks_authorization_or_digest_artifacts():
    # Security requirement: nothing in the onCommand write path (dispatch,
    # optimistic apply) may ever log the digest Authorization header or any of
    # its handshake artifacts, on either a rejected or a successful write.
    # Complements the api_key sentinel test above.
    st = _setup()
    plugin.onCommand("myenergi_hub1", UNIT_MODE, "Set Level", 10, "")
    assert st.client.calls == [("mode", "10000001", 1)]
    for line in Domoticz._log:
        for artifact in _DIGEST_ARTIFACTS:
            assert artifact not in line


def test_oncommand_rejected_write_never_leaks_authorization_or_digest_artifacts():
    st = plugin._state
    st.config = Config("10000001", "k", "English", 20, 6, 25.0, 0, allow_control=True)

    class _RejectingClient:
        def __init__(self):
            self.calls = []
            self.base_url = "https://s18.myenergi.net"

        def set_zappi_mode(self, serial, mode):
            self.calls.append(("mode", serial, mode))
            return {"status": 1, "error": "denied"}

    st.client = _RejectingClient()
    st.zappi_serial = "10000001"

    plugin.onCommand("myenergi_hub1", UNIT_MODE, "Set Level", 10, "")

    assert st.client.calls == [("mode", "10000001", 1)]
    for line in Domoticz._log:
        for artifact in _DIGEST_ARTIFACTS:
            assert artifact not in line


def test_oncommand_mode_write_logs_verbose_debug_without_leaking_api_key():
    sentinel = "sk-myenergi-secret-9f3d2a1b"
    st = _setup()
    st.config = Config("10000001", sentinel, "English", 20, 6, 25.0, 0, allow_control=True)

    plugin.onCommand("myenergi_hub1", UNIT_MODE, "Set Level", 10, "")

    assert st.client.calls == [("mode", "10000001", 1)]
    assert any("onCommand unit=12 command=Set Level level=10" in line for line in Domoticz._log)
    assert any("control write ok kind=mode" in line for line in Domoticz._log)
    assert not any(sentinel in line for line in Domoticz._log)


def test_oncommand_storm_coalescing_marks_timestamp_even_on_dispatch_failure():
    st = _setup()

    class _RaisingClient:
        base_url = "https://s18.myenergi.net"

        def set_zappi_mode(self, serial, mode):
            raise ConnectionError("network unreachable")

    st.client = _RaisingClient()
    st.last_any_write_ts = 0.0

    plugin.onCommand("myenergi_hub1", UNIT_MODE, "Set Level", 10, "")

    assert st.last_any_write_ts > 0.0
    assert any("myenergi onCommand error" in line for line in Domoticz._log)
