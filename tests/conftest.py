import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from tests import domoticz_stub

# Install at IMPORT (collection) time so `import Domoticz` resolves while pytest
# imports the test modules and the modules they pull in (domoticz_api, plugin).
# Without this, collection fails with ModuleNotFoundError before any fixture runs.
domoticz_stub.install()


@pytest.fixture(autouse=True)
def domoticz():
    """Reset the fake Domoticz + Devices (and plugin state) before every test."""
    mod = domoticz_stub.install()
    if "plugin" in sys.modules:
        sys.modules["plugin"]._state = sys.modules["plugin"]._PluginState()
    return mod
