"""Calculation specification tests."""

import pytest
from automol import Geometry
from qcio import CalcType

from autostore import Calculation, calcn
from autostore.calcn import hash_registry


@pytest.fixture
def water() -> Geometry:
    """Water geometry fixture."""
    return Geometry(
        symbols=["O", "H", "H"],
        coordinates=[[0, 0, 0], [1, 0, 0], [0, 1, 0]],  # ty:ignore[invalid-argument-type]
    )


@pytest.fixture
def calc() -> Calculation:
    """Define calculation fixture."""
    return Calculation(
        program="p",
        method="m",
        keywords={"a": {"c": "x", "d": "y"}, "b": {"c": "x", "d": "y"}},
    )


@pytest.fixture
def calc_reordered() -> Calculation:
    """Define calculation fixture.

    Same as `calc` but with different field and keyword order.
    Should match for any hash.
    """
    return Calculation(
        keywords={"b": {"d": "y", "c": "x"}, "a": {"d": "y", "c": "x"}},
        method="m",
        program="p",
    )


@pytest.fixture
def calc_keyword_change() -> Calculation:
    """Define calculation fixture.

    Same as `calc` but with one nested keyword changed ('d' in keyword 'b').
    Should match for minimal hash, but not for full hash.
    Should also match for projected hash against `template`.
    """
    return Calculation(
        program="p",
        method="m",
        keywords={"a": {"c": "x", "d": "y"}, "b": {"c": "x", "d": "z"}},
    )


@hash_registry.register("user_defined")
def user_defined_hash(calc: Calculation) -> str:
    """User-defined hash function for testing."""
    template = Calculation(
        program="P",
        method="M",
        keywords={"a": {"c": "X", "d": "Y"}, "b": {"c": "X"}},
    )
    return calcn.projected_hash(calc, template)


def test__qcio_program_input_conversion(calc: Calculation, water: Geometry) -> None:
    """Test conversion from QCIO ProgramInput to Calculation."""
    prog_input = calc.to_qcio_program_input(water, CalcType.energy)
    calc_roundtrip = Calculation.from_qcio_program_input(prog_input, prog=calc.program)
    # CalcType was not in original, so set it to None for comparison
    calc_roundtrip.calctype = None
    hash1 = calcn.calculation_hash(calc, name="full")
    hash2 = calcn.calculation_hash(calc_roundtrip, name="full")
    assert hash1 == hash2, "Hashes differ after QCIO ProgramInput conversion"


def test__hash_registry() -> None:
    """Test hash registry functionality.

    Check that registered hash functions are available.
    """
    available = hash_registry.available()
    assert "full" in available
    assert "minimal" in available
    assert "user_defined" in available


@pytest.mark.parametrize(
    "hash_name",
    hash_registry.available(),
)
def test__reordered(
    calc: Calculation, calc_reordered: Calculation, hash_name: str
) -> None:
    """Test that reordering fields does not change hash."""
    hash1 = calcn.calculation_hash(calc, hash_name)
    hash2 = calcn.calculation_hash(calc_reordered, hash_name)
    assert hash1 == hash2, f"Hashes differ for type '{hash_name}'"


@pytest.mark.parametrize(
    ("hash_name", "should_match"),
    [
        ("full", False),
        ("minimal", True),
        ("user_defined", True),
    ],
)
def test__keyword_change(
    calc: Calculation,
    calc_keyword_change: Calculation,
    hash_name: str,
    *,
    should_match: bool,
) -> None:
    """Test that reordering fields does not change hash."""
    hash1 = calcn.calculation_hash(calc, hash_name)
    hash2 = calcn.calculation_hash(calc_keyword_change, hash_name)
    assert (hash1 == hash2) == should_match, f"Hashes differ for type '{hash_name}'"
