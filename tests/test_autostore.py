"""autostore tests."""

from collections.abc import Iterator

import numpy as np
import pytest
from automol import Geometry
from qcio import Results

from autostore import Calculation, Database, read, write
from autostore.models import CalculationRow, GeometryRow


@pytest.fixture
def database() -> Iterator[Database]:
    """In-memory database fixture."""
    db = Database(":memory:")
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def water() -> Geometry:
    """Water geometry fixture."""
    return Geometry(
        symbols=["O", "H", "H"],
        coordinates=[[0, 0, 0], [1, 0, 0], [0, 1, 0]],  # ty:ignore[invalid-argument-type]
    )


@pytest.fixture
def xtb_calculation() -> Calculation:
    """XTB calculation fixture."""
    return Calculation(program="crest", method="gfn2")


@pytest.fixture
def water_xtb_energy_results() -> Results:
    """Water energy calculation results fixture."""
    return Results.model_validate(
        {
            "input_data": {
                "structure": {
                    "symbols": ["O", "H", "H"],
                    "geometry": [
                        [0.0, 0.0, 0.0],
                        [1.8897261259082012, 0.0, 0.0],
                        [0.0, 1.8897261259082012, 0.0],
                    ],
                    "charge": 0,
                    "multiplicity": 1,
                },
                "model": {"method": "gfn2", "basis": None},
                "calctype": "energy",
            },
            "success": True,
            "data": {"energy": -5.062316802835694},
            "provenance": {"program": "crest", "program_version": "3.0.2"},
        }
    )


def test_energy(
    water: Geometry,
    xtb_calculation: Calculation,
    water_xtb_energy_results: Results,
    database: Database,
) -> None:
    """Test writing and reading of the energy."""
    final_energy = water_xtb_energy_results.data.energy
    geo_row = GeometryRow.from_results(water_xtb_energy_results)
    calc_row = CalculationRow.from_results(water_xtb_energy_results)
    write.energy(geo_row, calc_row, value=final_energy, db=database)
    energy = read.energy(water, xtb_calculation, db=database, hash_name="minimal")
    assert energy is not None
    assert np.isclose(energy, -5.062316802835694), f"{energy = }"
