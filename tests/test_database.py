"""Test for database module."""

import pytest

from autostore import CalculationRow, Database


def test__add(blank_database: Database, calc_row: CalculationRow) -> None:
    """Test add to database."""
    calc_row_id = blank_database.add(row=calc_row)
    assert calc_row_id is not None


def test__invalid_add(blank_database: Database, calc_row: CalculationRow) -> None:
    """Test invalid add to database."""
    calc_row.program = None  # ty:ignore[invalid-assignment]
    with pytest.raises(RuntimeError):
        blank_database.add(row=calc_row)


def test__get(filled_database: Database) -> None:
    """Test get from database."""
    calc_row = filled_database.get(model=CalculationRow, row_id=1)
    assert calc_row is not None


def test__invalid_get(blank_database: Database) -> None:
    """Test invalid get from database."""
    # database.get should throw a LookupError if row_id not present in database
    with pytest.raises(LookupError):
        blank_database.get(model=CalculationRow, row_id=1)


def test__delete(filled_database: Database) -> None:
    """Test delete from database."""
    filled_database.delete(model=CalculationRow, row_id=1)


def test__invalid_delete(blank_database: Database) -> None:
    """Test invalid delete from database."""
    with pytest.raises(LookupError):
        blank_database.delete(model=CalculationRow, row_id=1)


def test__query(filled_database: Database) -> None:
    """Test query from database."""
    row_ids = filled_database.query(model=CalculationRow, method="b3lyp")
    assert row_ids == [1]
