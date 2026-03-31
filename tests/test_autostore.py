"""autostore tests."""

from collections.abc import Iterator

import numpy as np
import pytest
from automol import Geometry
from qcio import Results

from autostore import Calculation, Database, fetch, qc, write


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
    calc_row, geo_row = qc.results.res_to_rows(water_xtb_energy_results)
    write.energy(final_energy, calc_row=calc_row, geo_row=geo_row, db=database)
    energy = fetch.energy(water, xtb_calculation, hash_name="minimal", db=database)
    assert energy is not None
    assert np.isclose(energy.value, -5.062316802835694), f"{energy = }"
