import queue

import Domoticz
import pytest

import domoticz_api
import plugin
import update_check


class _FakeClient:
    def __init__(self, serial, api_key, writes_enabled=False):
        self.base_url = None

    def discover_from_director(self):
        raise OSError("offline")


class _FakeChecker:
    def __init__(self, current, channel, results):
        self.current, self.channel, self.results = current, channel, results
        self.started = self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


@pytest.fixture
def made(monkeypatch):
    made = []

    def _checker(current, channel, results):
        made.append(_FakeChecker(current, channel, results))
        return made[-1]

    monkeypatch.setattr(plugin, "MyEnergiClient", _FakeClient)
    monkeypatch.setattr(plugin, "_new_update_checker", _checker)
    return made


@pytest.fixture
def sent(monkeypatch):
    sent = []
    monkeypatch.setattr(Domoticz, "SendNotification", lambda *a: sent.append(a), raising=False)
    return sent


def _start(**params):
    plugin.Parameters = {"Username": "20000002", "ApiKey": "k", "Version": "1.1.0", **params}
    plugin.onStart()


def _post(result):
    plugin._state.updates.put_nowait(result)
    plugin.onHeartbeat()


URL = "https://github.com/Rouzax/myenergi-domoticz-plugin/releases/tag/v1.2.0"


def test_onstart_starts_the_checker_with_version_and_channel(made):
    _start(UpdateCheck="stable")
    (checker,) = made
    assert checker.started
    assert (checker.current, checker.channel) == ("1.1.0", "stable")
    assert checker.results is plugin._state.updates


def test_channel_defaults_to_auto(made):
    _start()
    assert made[0].channel == "auto"


@pytest.mark.parametrize("params", [{"UpdateCheck": "off"}, {"Version": ""}])
def test_no_checker_when_off_or_without_version(made, params):
    _start(**params)
    assert made == []
    assert plugin._state.checker is None


def test_onstop_and_restart_stop_the_running_checker(made):
    _start()
    _start()
    assert made[0].stopped and not made[1].stopped
    plugin.onStop()
    assert made[1].stopped
    assert plugin._state.checker is None


def test_checker_that_fails_to_start_does_not_block_onstart(monkeypatch):
    monkeypatch.setattr(plugin, "MyEnergiClient", _FakeClient)

    def _boom(*_a):
        raise RuntimeError("no threads")

    monkeypatch.setattr(plugin, "_new_update_checker", _boom)
    _start()
    assert plugin._state.checker is None
    assert plugin._state.config is not None


def test_new_version_is_announced_once_even_while_myenergi_is_unreachable(made, sent):
    _start()
    assert plugin._state.client.base_url is None  # discovery failed
    _post(update_check.UpdateResult("1.2.0", URL))
    assert sent == [
        (
            "myenergi Monitor plugin 1.2.0 is available",
            f"You run 1.1.0. What changed and how to update: {URL}",
            0,
            "",
            "",
            "",
        )
    ]
    assert any("myenergi Monitor 1.2.0 is available (running 1.1.0)" in m for m in Domoticz._log)
    assert domoticz_api.load_state().update_notified == "1.2.0"

    _post(update_check.UpdateResult("1.2.0", URL))
    _start()  # the announced version survives a restart
    _post(update_check.UpdateResult("1.2.0", URL))
    assert len(sent) == 1

    _post(update_check.UpdateResult("1.3.0", URL))
    assert len(sent) == 2
    assert domoticz_api.load_state().update_notified == "1.3.0"


def test_announcement_keeps_the_rest_of_the_saved_state(made, sent):
    domoticz_api.save_state(
        domoticz_api.load_state().__class__(unit_alloc={"22000001": 20}, control_shown=True)
    )
    _start()
    _post(update_check.UpdateResult("1.2.0", URL))
    saved = domoticz_api.load_state()
    assert saved.unit_alloc == {"22000001": 20}
    assert saved.control_shown


def test_dutch_notification_text(made, sent):
    _start(Language="Nederlands")
    _post(update_check.UpdateResult("1.2.0", URL))
    subject, body = sent[0][:2]
    assert subject == "myenergi Monitor-plugin 1.2.0 is beschikbaar"
    assert body == f"Je gebruikt 1.1.0. Wat er veranderd is en hoe je bijwerkt: {URL}"


@pytest.mark.parametrize(
    "result", [update_check.UpdateResult(None), update_check.UpdateResult(None, error="URLError")]
)
def test_no_announcement_for_up_to_date_or_failed_check(made, sent, result):
    _start()
    _post(result)
    assert sent == []
    assert domoticz_api.load_state().update_notified == ""
    if result.error:
        assert "update check failed: URLError" in Domoticz._log


def test_without_sendnotification_the_log_line_is_all(made, monkeypatch):
    monkeypatch.delattr(Domoticz, "SendNotification", raising=False)
    _start()
    _post(update_check.UpdateResult("1.2.0", URL))
    assert any("myenergi Monitor 1.2.0 is available" in m for m in Domoticz._log)
    assert domoticz_api.load_state().update_notified == "1.2.0"


def test_failing_notification_is_still_remembered(made, monkeypatch):
    def _fail(*_a):
        raise RuntimeError("no notifier")

    monkeypatch.setattr(Domoticz, "SendNotification", _fail, raising=False)
    _start()
    _post(update_check.UpdateResult("1.2.0", URL))
    assert "update notification failed: RuntimeError" in Domoticz._log
    assert domoticz_api.load_state().update_notified == "1.2.0"


def test_announcement_error_never_reaches_the_framework(made, monkeypatch):
    _start()

    def _broken():
        raise ValueError("corrupt state")

    monkeypatch.setattr(domoticz_api, "load_state", _broken)
    _post(update_check.UpdateResult("1.2.0", URL))
    assert "update announcement failed: ValueError" in Domoticz._log


def test_real_checker_is_built_for_this_repository():
    checker = plugin._new_update_checker("1.1.0", "auto", queue.Queue())
    assert checker._repo == plugin.REPOSITORY
    assert checker.daemon
    assert not checker.is_alive()
