import pytest

from allocation import BLOCK_SIZE, UnitExhaustionError, allocate_blocks


def test_first_allocation_is_stable_and_sorted():
    result = allocate_blocks(["20000002", "10000001"], existing={})
    assert result == {"10000001": 1, "20000002": 1 + BLOCK_SIZE}


def test_existing_assignments_are_preserved_regardless_of_order():
    existing = {"20000002": 1, "10000001": 1 + BLOCK_SIZE}
    result = allocate_blocks(["10000001", "20000002"], existing=existing)
    assert result == existing  # no shifting


def test_new_serial_gets_next_free_block():
    existing = {"10000001": 1}
    result = allocate_blocks(["10000001", "30000003"], existing=existing)
    assert result["10000001"] == 1
    assert result["30000003"] == 1 + BLOCK_SIZE


def test_exhaustion_raises():
    existing = {str(i): 1 + i * BLOCK_SIZE for i in range(10)}  # fills to >255
    with pytest.raises(UnitExhaustionError):
        allocate_blocks([str(i) for i in range(10)] + ["999"], existing=existing)
