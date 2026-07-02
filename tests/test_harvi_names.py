from model import parse_harvi_names


def test_parse_newline_and_semicolon():
    out = parse_harvi_names("21460322=SolarEdge\n21460323=Solis")
    assert out == {"21460322": "SolarEdge", "21460323": "Solis"}
    assert parse_harvi_names("21460322=SolarEdge;21460323=Solis") == out


def test_parse_ignores_malformed_and_empty():
    assert parse_harvi_names("") == {}
    assert parse_harvi_names("garbage\n=noserial\n99=  ") == {}
