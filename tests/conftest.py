import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from tests import domoticz_stub

# Install at IMPORT (collection) time so `import Domoticz` resolves while pytest
# imports the test modules and the modules they pull in (domoticz_api, plugin).
# Without this, collection fails with ModuleNotFoundError before any fixture runs.
domoticz_stub.install()

# onStart imports the project modules only after its Python version check; tests drive
# onHeartbeat/onCommand directly, so the modules are loaded once here.
import plugin  # noqa: E402

plugin._load_modules()


@pytest.fixture(autouse=True)
def domoticz():
    """Reset the fake Domoticz + Devices (and plugin state) before every test."""
    mod = domoticz_stub.install()
    plugin._state = plugin._PluginState()
    plugin.Devices = mod.Devices
    return mod
