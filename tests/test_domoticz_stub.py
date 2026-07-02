import Domoticz


def test_create_and_access_device():
    Domoticz.Unit(Name="X", DeviceID="hub1", Unit=1, TypeName="kWh").Create()
    unit = Domoticz.Devices["hub1"].Units[1]
    assert unit.Name == "X" and unit.TypeName == "kWh"
    unit.sValue = "1;2.0"
    unit.Update(Log=False)
    assert Domoticz.Devices["hub1"].Units[1].sValue == "1;2.0"


def test_configuration_roundtrip_and_heartbeat():
    Domoticz.Configuration({"a": "1"})
    assert Domoticz.Configuration()["a"] == "1"
    Domoticz.Heartbeat(20)
    assert Domoticz._heartbeat == 20
