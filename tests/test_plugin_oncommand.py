import Domoticz

import plugin
from config import Config
from control import UNIT_MODE


class _FakeClient:
    def __init__(self):
        self.calls = []
        self.base_url = "https://s18.myenergi.net"

    def set_zappi_mode(self, serial, mode):
        self.calls.append(("mode", serial, mode))
        return {"status": 0}

    def fetch_status(self):
        return {"zappi": [{"sno": 10000001, "zmo": 1, "lck": 0}]}


def _setup(allow_control=True):
    st = plugin._state
    st.config = Config("10000001", "k", "English", 20, 6, 25.0, 0, allow_control=allow_control)
    st.client = _FakeClient()
    st.zappi_serial = "10000001"
    return st


def test_oncommand_mode_write(monkeypatch):
    st = _setup()
    plugin.onCommand("myenergi_hub1", UNIT_MODE, "Set Level", 0, "")
    assert st.client.calls == [("mode", "10000001", 1)]


def test_oncommand_blocked_when_control_off():
    st = _setup(allow_control=False)
    plugin.onCommand("myenergi_hub1", UNIT_MODE, "Set Level", 0, "")
    assert st.client.calls == []


def test_oncommand_fail_closed_without_serial():
    st = _setup()
    st.zappi_serial = None
    plugin.onCommand("myenergi_hub1", UNIT_MODE, "Set Level", 0, "")
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

        def fetch_status(self):
            return {"zappi": []}

    st.client = _RejectingClient()
    st.zappi_serial = "10000001"

    plugin.onCommand("myenergi_hub1", UNIT_MODE, "Set Level", 0, "")

    assert st.client.calls == [("mode", "10000001", 1)]
    assert not any(sentinel in line for line in Domoticz._log)
    assert any("myenergi write rejected" in line for line in Domoticz._log)
