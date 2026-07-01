from model import FeedOverride, parse_feed_mapping


def test_parse_valid_mapping():
    overrides, warnings = parse_feed_mapping(
        "10000001=Solar Inverter A:solar\n20000002=House:grid",
        valid_serials={"10000001", "20000002"},
    )
    assert overrides["10000001"] == FeedOverride(name="Solar Inverter A", role="solar")
    assert overrides["20000002"] == FeedOverride(name="House", role="grid")
    assert warnings == []


def test_parse_skips_bad_lines_with_warnings():
    overrides, warnings = parse_feed_mapping(
        "\n".join(
            [
                "10000001=Good:solar",
                "garbage-line",
                "99999999=Unknown:solar",
                "10000001=Dup:grid",
                "10000001=BadRole:banana",
            ]
        ),
        valid_serials={"10000001"},
    )
    assert overrides["10000001"] == FeedOverride(name="Dup", role="grid")
    assert len(warnings) == 3  # garbage, unknown serial, bad role


def test_parse_enforces_line_cap():
    text = "\n".join(f"1000000{i}=N:solar" for i in range(70))
    _, warnings = parse_feed_mapping(text, valid_serials=set())
    assert any("line cap" in w for w in warnings)
