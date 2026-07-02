import Domoticz

from domoticz_api import log_redacted


def test_redacts_secret_in_message():
    log_redacted(Domoticz.Log, "auth failed for key=SEKRET123", "SEKRET123")
    assert Domoticz._log[-1] == "auth failed for key=***"


def test_empty_secret_is_safe():
    log_redacted(Domoticz.Log, "plain message", "")
    assert Domoticz._log[-1] == "plain message"


def test_none_secret_is_safe():
    log_redacted(Domoticz.Log, "plain message", None)
    assert Domoticz._log[-1] == "plain message"
