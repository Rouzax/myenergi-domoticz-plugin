from sanitize import clean_label, clean_serial, validate_asn_host


def test_clean_label_strips_and_caps():
    assert clean_label("Solar A") == "Solar A"
    assert clean_label("bad<img>\nx") == "badimgx"
    assert clean_label("x" * 100, max_len=10) == "x" * 10


def test_clean_serial():
    assert clean_serial("10000001") == "10000001"
    assert clean_serial(10000001) == "10000001"
    assert clean_serial("12ab") is None
    assert clean_serial("") is None


def test_validate_asn_host_accepts_myenergi():
    assert validate_asn_host("s18.myenergi.net") == "s18.myenergi.net"
    assert validate_asn_host("S18.MyEnergi.NET") == "s18.myenergi.net"


def test_validate_asn_host_rejects_hostile():
    for bad in [
        "attacker.com",
        "myenergi.net.attacker.com",
        "s18.myenergi.net:8080",
        "user@s18.myenergi.net",
        "https://s18.myenergi.net",
        "10.0.0.5",
        "s18.myenergi.net/path",
        "",
    ]:
        assert validate_asn_host(bad) is None, bad
    assert validate_asn_host(None) is None
    assert validate_asn_host(42) is None
