"""Fixtures for tests."""

from collections.abc import Iterator

import numpy as np
import pytest
from automol import Geometry

from autostore import (
    Calculation,
    CalculationRow,
    Database,
    GeometryRow,
    StationaryPointRow,
)


@pytest.fixture
def calc() -> Calculation:
    """Fixture for sample Calculation."""
    return Calculation(
        program="psi4",
        program_keywords={"dft_functional": "b3lyp", "scf_type": "df"},
        method="b3lyp",
        calc_type="energy",
    )


@pytest.fixture
def dual_calc() -> Calculation:
    """Fixture for sample Calculation."""
    return Calculation(
        program="psi4",
        program_keywords={"dft_functional": "b3lyp", "scf_type": "df"},
        super_program="geomeTRIC",
        super_keywords={
            "constraints": {
                "freeze": [{"type": "distance", "indices": [0, 1], "value": 1.5}]
            }
        },
        method="b3lyp",
        calc_type="energy",
    )


@pytest.fixture
def calc_row(calc: Calculation) -> CalculationRow:
    """Fixture for sample CalculationRow."""
    return CalculationRow.from_calculation(calc=calc)


@pytest.fixture
def dual_calc_row(dual_calc: Calculation) -> CalculationRow:
    """Fixture for sample CalculationRow with DualProgramInput attributes."""
    return CalculationRow.from_calculation(calc=dual_calc)


@pytest.fixture
def geo() -> Geometry:
    """Fixture for sample Geometry."""
    return Geometry(
        symbols=["O", "H", "H"],
        coordinates=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]]),
        charge=0,
        spin=0,
    )


@pytest.fixture
def geo_row(geo: Geometry) -> GeometryRow:
    """Fixture for sample GeometryRow."""
    return GeometryRow.from_geometry(geo)


@pytest.fixture
def stationary_row() -> StationaryPointRow:
    """Fixture for sample StationaryRow."""
    return StationaryPointRow(calculation_id=2, geometry_id=1, order=0, is_pseudo=False)


@pytest.fixture
def blank_database() -> Iterator[Database]:
    """In-memory blank database fixture."""
    db = Database(":memory:")
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def filled_database(
    calc_row: CalculationRow, geo_row: GeometryRow, stationary_row: StationaryPointRow
) -> Iterator[Database]:
    """In-memory database with rows fixture."""
    db = Database(":memory:")
    db.add(row=calc_row)
    db.add(row=geo_row)
    db.add(row=stationary_row)
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def geo_in_database(geo_row: GeometryRow) -> Iterator[Database]:
    """In-memory database with geometry row fixture."""
    db = Database(":memory:")
    db.add(row=geo_row)
    try:
        yield db
    finally:
        db.close()
